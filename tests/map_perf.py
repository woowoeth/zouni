#!/usr/bin/env python3
"""地图加载性能测量（2026-10-18）：点开地图 → 首次可见内容 / 街道底图首批瓦片 / 整屏瓦片 / 可交互，毫秒数 + 请求瀑布。

用法（项目根目录）：
    python3 tests/map_perf.py --target live  --label before          # 打到线上 https://zouni.app（真联网，CDP 限速）
    python3 tests/map_perf.py --target local --site build/site       # 本地 build/site 经本地 gzip 静态服务；OpenFreeMap 真联网（CDP 限速）
    python3 tests/map_perf.py --target fixture --site build/site     # 稳定版：站点和 OpenFreeMap 都在本机（后者是 TLS 假服务 + host-resolver 重定向），
                                                                      #   带宽 / 往返用同一条“共享链路”模型模拟，不依赖外网，每次数字可复现
    选项：--profiles none,4g,3g（默认全跑）  --modes cold,warm,idle（默认 cold,warm；idle = 冷缓存但页面先空闲 8 秒再点，量空闲预取的收益）
          --cases 4g:cold,4g:warm,3g:cold（只跑这几组，代替 --profiles / --modes 的全组合；Slow 3G 每组要几分钟，套件里只跑必要的）
          --path /trip/xa3/（默认）  --reps 1  --out build/map_perf/<label>-<target>.json  --assert（按验收目标判定，退出码 1）
          --inject slow_boot（反向自检，见 INJ：只改送到浏览器的文件，`--assert` 必须变红；只对 fixture / local 有效）

定义（与实现无关：改版前后同一把尺）：
    t_click   点“看路线图”（.mapgo）的 click 事件那一刻
    t_vis     首次可见内容：页面里出现 .rm 根节点、在视口内、高度 ≥ 150px、可见（示意图 / 加载提示 / 面板任何一个都算）
    t_tile1   街道底图首批瓦片：ZRM.cur().tiles > 0（第一块矢量瓦片已解码、可绘制）
    t_loaded  整屏瓦片：ZRM.cur().map.loaded() 为真且 tiles > 0（当前视野的瓦片全部到齐并画完）
    t_inter   可交互：地图实例已建好（ZRM.cur().view 存在；之后的拖动 / 缩放手势就是真的）
条件：none 不限速；4g ≈ 9Mbps / 往返 170ms；3g = Slow 3G 400kbps / 往返 400ms。
    cold：新开无缓存的浏览器环境，页面在同一限速下载入，载入完成后立刻点；warm：同一环境里点开过一次再重载页面、再点（HTTP 缓存 / Service Worker 都在）；
    idle：同 cold，但载入后空闲 8 秒再点。
"""
import functools, gzip, http.server, json, os, re, socketserver, ssl, struct, subprocess, sys, threading, time, urllib.request
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = sys.argv[1:]
def opt(n, d=None): return A[A.index(n) + 1] if n in A else d
TARGET = opt('--target', 'local'); LABEL = opt('--label', 'run'); SITE = os.path.abspath(opt('--site', os.path.join(ROOT, 'build', 'site')))
PROFILES = opt('--profiles', 'none,4g,3g').split(','); MODES = opt('--modes', 'cold,warm').split(','); PATH = opt('--path', '/trip/xa3/'); REPS = int(opt('--reps', '1'))
CASES = [tuple(x.split(':')) for x in opt('--cases').split(',')] if opt('--cases') else None
OUT = opt('--out', os.path.join(ROOT, 'build', 'map_perf', '%s-%s.json' % (LABEL, TARGET))); ASSERT = '--assert' in A; INJECT = opt('--inject')
PROF = {'none': None, '4g': dict(latency=170, down=9 * 1024 * 1024 / 8), '3g': dict(latency=400, down=400 * 1024 / 8)}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
INJ = {   # 反向自检：把送到浏览器的文件弄坏某一处，--assert 必须红（只对 fixture / local 有效）
    'slow_boot': ('assets/site.js', "B.style.top=(-y)+'px';B.classList.add('rm-lock','rmap-on','pk-open');B.appendChild(root);", "B.style.top=(-y)+'px';B.classList.add('rm-lock','rmap-on','pk-open');setTimeout(function(){B.appendChild(root)},900);"),      # 起步壳晚 0.9 秒才出现：首次可见内容必须超标
    'no_warm': ('assets/site.js', "mlTag();warm(b);      // 起步壳已经塞进 DOM", "mlTag();      // 起步壳已经塞进 DOM"),      # 点开时不并行预热：首批瓦片变慢（4g 冷缓存 / 慢网才看得出来，不一定过线，所以只记录不判）
}
GROUPS = [('maplibre js', r'maplibre-gl\.js'), ('maplibre css', r'maplibre-gl\.css'), ('routemap.js', r'routemap\.js'), ('style', r'/styles/liberty|map/style\.json|/style\.json'),
          ('tilejson', r'/planet$|/planet\?'), ('sprite', r'sprite'), ('glyph', r'/fonts/|glyph'), ('tiles(pbf)', r'\.pbf'), ('raster', r'natural_earth|\.png'), ('其他', r'.')]


def group_of(u):
    for n, rx in GROUPS:
        if re.search(rx, u): return n
    return '其他'


# ——— 共享链路模型（fixture 用）：所有连接共用一条 bw 字节/秒的链路，每个响应先等一个往返再按链路排队发送 ———
class Link:
    def __init__(self): self.free = 0.0; self.lock = threading.Lock(); self.rtt = 0; self.bw = None
    def set(self, p):
        self.rtt = (p['latency'] / 1000) if p else 0; self.bw = p['down'] if p else None; self.free = 0.0
    def send(self, wfile, data):
        time.sleep(self.rtt)
        if not self.bw: wfile.write(data); return
        for i in range(0, len(data), 8192):
            ch = data[i:i + 8192]
            with self.lock:
                now = time.time(); self.free = max(self.free, now) + len(ch) / self.bw; wait = self.free - now
            time.sleep(max(0, wait)); wfile.write(ch)
LINK = Link()
GZ = {'.html', '.js', '.css', '.svg', '.json', '.xml', '.webmanifest', '.txt'}


class SiteH(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self): return None
    def do_GET(self):
        p = self.translate_path(self.path.split('?')[0].split('#')[0])
        if os.path.isdir(p): p = os.path.join(p, 'index.html')
        if not os.path.isfile(p): self.send_error(404); return
        data = open(p, 'rb').read(); ext = os.path.splitext(p)[1].lower()
        if INJECT and INJECT in INJ and p.endswith(os.sep + INJ[INJECT][0].replace('/', os.sep)):
            data = data.decode('utf-8').replace(INJ[INJECT][1], INJ[INJECT][2]).encode('utf-8')
        enc = 'gzip' in (self.headers.get('Accept-Encoding') or '') and ext in GZ
        if enc: data = gzip.compress(data, 6)
        self.send_response(200); self.send_header('Content-Type', self.guess_type(p) + ('; charset=utf-8' if ext in ('.html', '.js', '.css') else ''))
        if enc: self.send_header('Content-Encoding', 'gzip')
        self.send_header('Cache-Control', 'max-age=600'); self.send_header('Content-Length', str(len(data))); self.end_headers()
        LINK.send(self.wfile, data)


def pbf_tile(z, x, y):
    """合法的矢量瓦片：没有图层，外加一个未知字段当“体积”（protobuf 解码器忽略未知字段），大小随缩放级别：低级别小、城区大"""
    n = 6000 if z <= 6 else (22000 if z <= 10 else 45000)
    body = b'\x00' * n
    def varint(v):
        o = b''
        while True:
            b = v & 0x7f; v >>= 7
            if v: o += bytes([b | 0x80])
            else: o += bytes([b]); return o
    return b'\xfa\x06' + varint(len(body)) + body      # 字段号 99、wire type 2


class OfmH(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        u = self.path; ct, data = 'application/octet-stream', b''
        FX = os.path.join(ROOT, 'tests', 'fixtures')
        if u.startswith('/styles/liberty'): ct, data = 'application/json', open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read()
        elif re.match(r'^/planet/?$', u.split('?')[0]): ct, data = 'application/json', json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}).encode()
        elif u.startswith('/planet/'):
            m = re.search(r'/(\d+)/(\d+)/(\d+)\.pbf', u); ct, data = 'application/x-protobuf', pbf_tile(*(int(g) for g in m.groups())) if m else b''
        elif u.startswith('/fonts/'): ct, data = 'application/x-protobuf', b'\xfa\x06' + bytes([0x80, 0x40]) + b'\x00' * 8192      # 空字形块 + 8KB 体积
        elif u.startswith('/sprites/'): ct, data = ('application/json', b'{}') if u.split('?')[0].endswith('.json') else ('image/png', open(os.path.join(FX, 'ofm_blank.png'), 'rb').read())
        elif u.startswith('/natural_earth/'): ct, data = 'image/png', open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
        else: self.send_error(404); return
        if ct == 'application/json': data = gzip.compress(data, 6); enc = 'gzip'
        else: enc = None
        self.send_response(200); self.send_header('Content-Type', ct); self.send_header('Access-Control-Allow-Origin', '*'); self.send_header('Cache-Control', 'max-age=3600')
        if enc: self.send_header('Content-Encoding', enc)
        self.send_header('Content-Length', str(len(data))); self.end_headers(); LINK.send(self.wfile, data)


def start_servers(need_ofm):
    socketserver.TCPServer.allow_reuse_address = True
    s1 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(SiteH, directory=SITE)); threading.Thread(target=s1.serve_forever, daemon=True).start()
    s2 = None
    if need_ofm:
        d = os.path.join(ROOT, 'build', 'map_perf')      # 自签证书放这里（30 天，不进库）
        os.makedirs(d, exist_ok=True); crt, key = os.path.join(d, 'ofm.crt'), os.path.join(d, 'ofm.key')
        if not os.path.exists(crt):
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-keyout', key, '-out', crt, '-days', '30', '-subj', '/CN=tiles.openfreemap.org', '-addext', 'subjectAltName=DNS:tiles.openfreemap.org'], check=True, capture_output=True)
        s2 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), OfmH)
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); ctx.load_cert_chain(crt, key); s2.socket = ctx.wrap_socket(s2.socket, server_side=True)
        threading.Thread(target=s2.serve_forever, daemon=True).start()
    return s1, s2


POLL = """(function(){
  window.__pf={t0:null,vis:null,tile1:null,loaded:null,inter:null};
  document.addEventListener('click',function(e){if(window.__pf.t0===null&&e.target.closest&&e.target.closest('.mapgo'))window.__pf.t0=performance.now()},true);
  function vis(){var r=document.querySelector('.rm');if(!r)return false;var b=r.getBoundingClientRect(),cs=getComputedStyle(r);
    return b.height>=150&&b.width>=100&&b.bottom>0&&b.top<innerHeight&&cs.visibility!=='hidden'&&cs.display!=='none'&&parseFloat(cs.opacity||1)>0}
  function tick(){var p=window.__pf;if(p.t0!==null){var now=performance.now(),Z=window.ZRM&&ZRM.cur&&ZRM.cur();
    if(p.vis===null&&vis())p.vis=now;
    if(Z){if(p.inter===null&&Z.view)p.inter=now;if(p.tile1===null&&Z.tiles>0)p.tile1=now;
      if(p.loaded===null&&Z.tiles>0&&Z.map&&Z.map.loaded&&Z.map.loaded())p.loaded=now}}
    requestAnimationFrame(tick)}
  requestAnimationFrame(tick)})();"""


def one(br, host, prof, mode, cdp_throttle):
    """一次测量。返回 dict。host = 站点根；cdp_throttle：用 CDP 限速（live/local 用，fixture 用链路模型）"""
    c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, locale='zh-CN', timezone_id='Asia/Shanghai')
    pg = c.new_page(); pg.set_default_timeout(120000)
    # 不用 page.route 拦天气 / 统计：Playwright 一开请求拦截就把 HTTP 缓存关了，“热缓存”就测不出来。改用 Chromium 的 --host-resolver-rules 把这几个域名解析成“找不到”（见 main）
    pg.add_init_script(POLL)
    if not cdp_throttle and prof != 'none': pg.add_init_script("Object.defineProperty(navigator,'connection',{value:{effectiveType:'%s',saveData:false,downlink:%s,rtt:%d},configurable:true});" % ('3g' if prof == '3g' else '4g', '0.4' if prof == '3g' else '9', 400 if prof == '3g' else 170))
    cdp = c.new_cdp_session(pg); cdp.send('Network.enable')
    reqs = []      # 用 Playwright 的 context 级事件：能抓到 Web Worker 里发的请求（maplibre 的瓦片是 worker 取的，页面的 CDP 会话看不到）
    def on_fin(rq):
        try:
            t = rq.timing; sz = rq.sizes()
            reqs.append({'url': rq.url, 'start': t['startTime'], 'end': (t['startTime'] + t['responseEnd']) if t.get('responseEnd', -1) >= 0 else None, 'bytes': (sz.get('responseBodySize') or 0) + (sz.get('responseHeadersSize') or 0), 'fail': False})
        except Exception: pass
    def on_fail(rq):
        try: reqs.append({'url': rq.url, 'start': rq.timing['startTime'], 'end': None, 'bytes': 0, 'fail': True})
        except Exception: pass
    c.on('requestfinished', on_fin); c.on('requestfailed', on_fail)
    def throttle(on):
        P = PROF[prof]
        if cdp_throttle:
            if P and on: cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': P['latency'], 'downloadThroughput': P['down'], 'uploadThroughput': P['down'], 'connectionType': 'cellular3g' if prof == '3g' else 'cellular4g'})      # 带 connectionType：navigator.connection.effectiveType 才和真手机一样跟着变（站里的预取 / 预热看它）
            else: cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 0, 'downloadThroughput': -1, 'uploadThroughput': -1})
        else: LINK.set(P if on else None)
    def load(settle=True):
        throttle(True); pg.goto(host + PATH, wait_until='load', timeout=180000)
        if not settle: pg.wait_for_timeout(300); return      # 冷缓存：load 一结束就点（空闲预取要在 load 之后 2 秒才开始，这时还没发；等 networkidle 的话预取会在点之前跑完，“冷”就不冷了）
        try: pg.wait_for_load_state('networkidle', timeout=60000)
        except Exception: pass
    def click_and_wait(limit=75):
        pg.evaluate("window.__pf.t0=null;window.__pf.vis=window.__pf.tile1=window.__pf.loaded=window.__pf.inter=null")
        pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(150)
        reqs[:] = []; pg.click('.mapgo')
        t0 = time.time()
        while time.time() - t0 < limit:
            r = pg.evaluate("window.__pf")
            if r['loaded'] is not None: break
            pg.wait_for_timeout(100)
        pg.wait_for_timeout(800)
        pf = pg.evaluate("window.__pf"); why = pg.evaluate("(function(){var z=window.ZRM&&ZRM.cur&&ZRM.cur();return z?{failed:!!z.failed,why:z.why||null,tiles:z.tiles||0}:null})()")
        epoch0 = pg.evaluate("performance.timeOrigin") + pf['t0']
        o = {k: (None if pf[k] is None or pf['t0'] is None else round(pf[k] - pf['t0'])) for k in ('vis', 'tile1', 'loaded', 'inter')}
        o['state'] = why
        agg = {}
        for r in reqs:
            if r['start'] < epoch0 - 50: continue
            g = group_of(r['url']); a = agg.setdefault(g, {'n': 0, 'bytes': 0, 'first': None, 'last': None, 'cache': 0, 'fail': 0})
            a['n'] += 1; a['bytes'] += r['bytes'] or 0; a['fail'] += 1 if r['fail'] else 0
            s_ = r['start'] - epoch0; e_ = (r['end'] - epoch0) if r['end'] else None
            a['first'] = s_ if a['first'] is None else min(a['first'], s_)
            if e_ is not None: a['last'] = e_ if a['last'] is None else max(a['last'], e_)
        o['waterfall'] = {g: {'n': a['n'], 'KB': round(a['bytes'] / 1024, 1), 'from_ms': round(a['first']), 'to_ms': round(a['last']) if a['last'] is not None else None, 'failed': a['fail']} for g, a in agg.items()}
        o['total_KB'] = round(sum(a['bytes'] for a in agg.values()) / 1024, 1); o['req_n'] = sum(a['n'] for a in agg.values())
        return o
    try:
        load(settle=(mode == 'idle'))
        if mode == 'idle': pg.wait_for_timeout(8000)
        out = click_and_wait()
        if mode == 'warm':
            pg.reload(wait_until='load');
            try: pg.wait_for_load_state('networkidle', timeout=60000)
            except Exception: pass
            pg.wait_for_timeout(1500); out = click_and_wait()
        return out
    finally:
        c.close()


def fmt(v): return '   -  ' if v is None else '%6d' % v


def main():
    live = TARGET == 'live'; need_ofm = TARGET == 'fixture'
    srvs = None; host = 'https://zouni.app'
    if not live: srvs = start_servers(need_ofm); host = 'http://127.0.0.1:%d' % srvs[0].server_address[1]
    args = list(LAUNCH)
    BLOCK = ','.join('MAP %s ~NOTFOUND' % h for h in ('api.open-meteo.com', 'archive-api.open-meteo.com', 'geocoding-api.open-meteo.com', 'restapi.amap.com', 'uri.amap.com', 'hm.baidu.com', 'www.googletagmanager.com', 'static.cloudflareinsights.com'))
    args.append('--host-resolver-rules=' + BLOCK)
    if need_ofm:
        # 用 SPKI 白名单而不是 --ignore-certificate-errors：后者让 Chrome 把整条 HTTPS 响应当“证书有问题”，不进 HTTP 缓存，热缓存就测不出来
        d = os.path.join(ROOT, 'build', 'map_perf')
        pub = subprocess.run(['openssl', 'x509', '-in', os.path.join(d, 'ofm.crt'), '-pubkey', '-noout'], capture_output=True).stdout
        der = subprocess.run(['openssl', 'pkey', '-pubin', '-outform', 'der'], input=pub, capture_output=True).stdout
        import hashlib, base64
        spki = base64.b64encode(hashlib.sha256(der).digest()).decode()
        args[-1] += ',MAP tiles.openfreemap.org 127.0.0.1:%d' % srvs[1].server_address[1]; args += ['--ignore-certificate-errors-spki-list=' + spki]
    res = []
    with sync_playwright() as p:
        plan = CASES or [(pf_, md_) for pf_ in PROFILES for md_ in MODES]
        if '--no-warmup' not in A:      # 先丢掉一个样本：每次跑的第一个浏览器进程要做软件渲染 / 光栅化的第一次初始化（几百毫秒），会把第一行数字（不限速·冷缓存）拉高
            try:
                _b = p.chromium.launch(args=args); one(_b, host, 'none', 'cold', cdp_throttle=not need_ofm); _b.close()
            except Exception: pass
        for prof, mode in plan:
            if True:
                for i in range(REPS):
                    br = p.chromium.launch(args=args)      # 每个样本一个新浏览器进程：Chromium 的 HTTP 缓存在同一进程的多个 context 之间是共享的，冷缓存必须新进程
                    try: o = one(br, host, prof, mode, cdp_throttle=not need_ofm)
                    except Exception as e: o = {'error': '%s: %s' % (type(e).__name__, str(e)[:160])}
                    try: br.close()
                    except Exception: pass
                    o.update(profile=prof, mode=mode, rep=i); res.append(o)
                    print('%-5s %-5s  可见 %s  首批瓦片 %s  整屏 %s  可交互 %s   请求 %s 个 / %s KB  %s' % (prof, mode, fmt(o.get('vis')), fmt(o.get('tile1')), fmt(o.get('loaded')), fmt(o.get('inter')), o.get('req_n', '-'), o.get('total_KB', '-'), o.get('error', '') or json.dumps(o.get('state'), ensure_ascii=False)), flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({'target': TARGET, 'label': LABEL, 'path': PATH, 'host': host, 'results': res}, open(OUT, 'w'), ensure_ascii=False, indent=1)
    print('\n瀑布（点击以来；from/to 是该组请求第一个发出 / 最后一个完成的毫秒数）：')
    for o in res:
        if 'waterfall' not in o: continue
        print('── %s %s' % (o['profile'], o['mode']))
        for g, a in sorted(o['waterfall'].items(), key=lambda kv: kv[1]['from_ms']): print('   %-12s %3d 个 %8.1f KB  %6s → %6s ms  失败 %d' % (g, a['n'], a['KB'], a['from_ms'], a['to_ms'], a['failed']))
    print('已写 ' + OUT)
    bad = []
    if ASSERT:
        def get(prof, mode, k):
            for o in res:
                if o.get('profile') == prof and o.get('mode') == mode and o.get(k) is not None: return o[k]
        want = [('4g', 'cold', 'vis', 300), ('4g', 'cold', 'tile1', 3000), ('4g', 'warm', 'tile1', 1000), ('3g', 'cold', 'vis', 500)]
        for prof, mode, k, lim in want:
            if (prof, mode) in plan:
                v = get(prof, mode, k)
                if v is None or v > lim: bad.append('%s %s %s = %s ms（目标 < %d）' % (prof, mode, k, v, lim))
        print('\n判定：' + ('全部达标' if not bad else '未达标 ' + '；'.join(bad)))
    sys.exit(1 if bad else 0)


main()
