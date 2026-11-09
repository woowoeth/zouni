#!/usr/bin/env python3
"""慢网冷启动“第一次看得清”（2026-10-29 第 2 波，slow.md #1/#2）。会红。

和 slow3g_check.py 的区别：那个量“点得动”；这个量“看得见字”——行程页标题（h1）、天数（.big）、价格（.price）
从什么时候起真的画在屏幕上（不是 DOM 里有，是像素里有），以及“看地图”“按天看”两个按钮在第一次绘制时有没有。

用法（项目根目录；先建好站）：
    python3 tests/w2_slow_check.py build/site_w2                  # 量 + 断言
    python3 tests/w2_slow_check.py build/site_w2_pre --report     # 只打印数字（改动前的站，写前后对比用）
    python3 tests/w2_slow_check.py build/site_w2 --inject block   # 反向自检：把行程页字体改回 font-display:block，必须变红
    python3 tests/w2_slow_check.py build/site_w2 --inject btn_js  # 反向自检：把静态 HTML 里的两个按钮摘掉（回到脚本才画），必须变红

怎么量“看得见”：每 300ms 取标题 / 天数 / 价格那块区域的截图 A，再把这几个元素的字设成透明取截图 B，A 和 B 有差别 = 字真的画出来了
（字体还在“块期”时浏览器画的是透明占位，A 和 B 一样）。
Slow 3G：下行 400 Kbps、往返 400 ms，本地服务按 Accept-Encoding 现场 gzip（同 slow3g_check.py）。
断言：标题 / 天数 / 价格在“首次绘制 + 1.5s”内看得见；两个按钮在第一次绘制时就在 DOM 里；字体块期不得是 block。
"""
import functools, gzip, http.server, io, json, os, re, socketserver, sys, threading, time
from playwright.sync_api import sync_playwright
from PIL import Image, ImageChops

args = [a for a in sys.argv[1:] if not a.startswith('--')]
site = os.path.abspath(args[0]) if args else os.path.abspath('build/site')
REPORT = '--report' in sys.argv
INJ = sys.argv[sys.argv.index('--inject') + 1] if '--inject' in sys.argv else None
if INJ not in (None, 'block', 'btn_js'): sys.exit('--inject 只认 block / btn_js')
GZ = {'.html', '.js', '.css', '.svg', '.json', '.xml', '.webmanifest', '.txt'}
HIT = []


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_head(self):
        p = self.translate_path(self.path.split('?')[0].split('#')[0])
        if os.path.isdir(p): p = os.path.join(p, 'index.html')
        ext = os.path.splitext(p)[1].lower()
        if not os.path.isfile(p): return super().send_head()
        data = open(p, 'rb').read()
        if INJ == 'block' and p.endswith(os.path.join('fonts', 'serif.css')): data = data.replace(b'font-display: fallback', b'font-display: block')
        if INJ == 'btn_js' and p.endswith('index.html') and os.sep + 'trip' + os.sep in p:
            n0 = len(data); data = re.sub(rb'<button type="button" class="mapgo".*?</button>', b'', data, flags=re.S); data = re.sub(rb'<button type="button" class="tvbtn".*?</button>', b'', data, flags=re.S)
            HIT.append(n0 - len(data))
        enc = 'gzip' in (self.headers.get('Accept-Encoding') or '') and ext in GZ
        if enc: data = gzip.compress(data, 6)
        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(p) + ('; charset=utf-8' if ext in ('.html', '.js', '.css') else ''))
        if enc: self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(data))); self.end_headers()
        return io.BytesIO(data)


socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{srv.server_address[1]}'

REG = """(function(){var o={};[['h1','.hero h1'],['big','.glance .big'],['price','.glance .price']].forEach(function(p){var e=document.querySelector(p[1]);if(e){var r=e.getBoundingClientRect();if(r.width>0&&r.height>0)o[p[0]]=[Math.max(0,r.left),Math.max(0,r.top),Math.min(390,r.width),r.height]}});return o})()"""
TRANSP = "(function(){var s=document.getElementById('__t');if(!s){s=document.createElement('style');s.id='__t';document.head.appendChild(s)}s.textContent='.hero h1,.glance .big,.glance .price{color:transparent!important;text-shadow:none!important}'})()"
UNTR = "(function(){var s=document.getElementById('__t');if(s)s.remove()})()"


def shot(cdp, clip):
    """CDP 直接截图：playwright 的 page.screenshot 会先等字体全部到位（慢网下要等一分钟），量不出“字体没到时看得见没有”"""
    import base64
    r = cdp.send('Page.captureScreenshot', {'format': 'png', 'clip': {'x': clip[0], 'y': clip[1], 'width': clip[2], 'height': clip[3], 'scale': 1}})
    return Image.open(io.BytesIO(base64.b64decode(r['data']))).convert('RGB')


def visible(pg, cdp, clip):
    a = shot(cdp, clip)
    pg.evaluate(TRANSP)
    b = shot(cdp, clip)
    pg.evaluate(UNTR)
    d = ImageChops.difference(a, b).convert('L').point(lambda v: 255 if v > 40 else 0)
    return d.getbbox() is not None


def measure(br, path):
    c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1, service_workers='block')
    pg = c.new_page()
    pg.route(re.compile(r'.*(open-meteo|amap|baidu|googletagmanager|hm\.baidu|google).*'), lambda r: r.abort())
    cdp = c.new_cdp_session(pg); cdp.send('Network.enable')
    cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': 400, 'downloadThroughput': 400 * 1024 / 8, 'uploadThroughput': 400 * 1024 / 8})
    pg.add_init_script("""window.__fcp=null;try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){if(e.name==='first-contentful-paint')window.__fcp=Math.round(e.startTime)})}).observe({type:'paint',buffered:true})}catch(e){}""")
    pg.goto(B + path, wait_until='commit', timeout=120000)
    T = {}; btn_at_fcp = None; dl = time.time() + 90; t0 = time.time()
    while time.time() < dl and len(T) < 3:
        try:
            fcp = pg.evaluate('window.__fcp')
            if fcp is not None and btn_at_fcp is None: btn_at_fcp = pg.evaluate("!!document.querySelector('.mapgo')&&!!document.querySelector('.tvbtn')")
            reg = pg.evaluate(REG)
            now = pg.evaluate('Math.round(performance.now())')
            for k, clip in reg.items():
                if k not in T and fcp is not None and visible(pg, cdp, clip): T[k] = now
        except Exception:
            pass
        time.sleep(0.15)
    fcp = pg.evaluate('window.__fcp')
    time.sleep(1)
    fr = pg.evaluate("(()=>{const rs=performance.getEntriesByType('resource').filter(r=>/\\.woff2/.test(r.name));return {n:rs.length,wire:rs.reduce((a,r)=>a+(r.encodedBodySize||0),0),at:Math.max.apply(null,[0].concat(rs.map(r=>r.responseEnd)))}})()")
    btn_now = pg.evaluate("[!!document.querySelector('.mapgo'),!!document.querySelector('.tvbtn')]")
    c.close()
    return dict(fcp=fcp, h1=T.get('h1'), big=T.get('big'), price=T.get('price'), btn_at_fcp=btn_at_fcp, btn_now=btn_now, fonts_n=fr['n'], fonts_wire=fr['wire'])


fails = []
f = lambda v: '—' if v is None else f'{v/1000:.1f}s'
with sync_playwright() as p:
    br = p.chromium.launch()
    for rid in ('xa3', 'zl4a'):
        m = measure(br, f'/trip/{rid}/')
        print(f'/trip/{rid}/ Slow 3G：首次绘制 {f(m["fcp"])} · 标题看得见 {f(m["h1"])} · 天数 {f(m["big"])} · 价格 {f(m["price"])} · 首次绘制时两个按钮已在 DOM：{m["btn_at_fcp"]} · 字体 {m["fonts_n"]} 个 {m["fonts_wire"]/1024:.0f}KB')
        if REPORT: continue
        fc = m['fcp']
        for k, nm in (('h1', '标题'), ('big', '天数'), ('price', '价格')):
            if m[k] is None or fc is None or m[k] > fc + 1500: fails.append(f'{rid} {nm}要到 {f(m[k])} 才看得见（首次绘制 {f(fc)} + 1.5s 以内才算）')
        if not m['btn_at_fcp']: fails.append(f'{rid} 首次绘制时“看地图”“按天看”还不在 DOM 里（要等脚本画）')
    br.close()
if INJ == 'btn_js' and not HIT: fails.append('INJECT-NOT-APPLIED btn_js')
if not REPORT:
    css = open(os.path.join(site, 'assets', 'fonts', 'serif.css'), encoding='utf-8').read()
    if 'font-display: block' in css and INJ is None: fails.append('serif.css 里还有 font-display: block')
    if fails:
        print('红：'); [print('  -', x) for x in fails]; sys.exit(1)
    print('慢网首次看得清断言通过')
