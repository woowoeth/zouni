#!/usr/bin/env python3
"""Slow 3G 冷启动测量 + 断言（2026-10-17）：首页和一条行程页，从空缓存打开，到“第一次能点”要多久。

用法（项目根目录；先建好站）：
    python3 tests/slow3g_check.py build/site                    # 打印数字；超过上限退出码 1
    python3 tests/slow3g_check.py build/site_base --report      # 只打印不判定（比较改动前后用）
    python3 tests/slow3g_check.py build/site --inject big       # 反向自检：故意让首页多出 1MB 的无用标记，必须变红
    python3 tests/slow3g_check.py build/site --inject no_home_fonts   # 反向自检：把首页专用小字体摘掉（又回到 45 个切片、2.8MB），必须变红

怎么量：
  - 本地静态服务按 Accept-Encoding 现场 gzip（和 GitHub Pages 一致），因为 Slow 3G 限的是传输字节，不是解压后的字节
  - Chromium 用 CDP Network.emulateNetworkConditions：下行 400 Kbps、上行 400 Kbps、往返 400 ms（DevTools 的 “Slow 3G” 同量级；
    再单独用往返 2000 ms 量一次最坏的）
  - 每次新开一个无缓存的 context（冷启动）
  - 指标：
      html     页面 HTML 原始字节 / gzip 字节
      fcp      首次绘制（PerformanceObserver paint）
      ready    site.js 跑完（site.js 末尾打的 performance.mark('zouni:ready')）：按钮从这一刻起有反应
      click    ready 之后真点一下首页日期条 / 行程页的“改”，日期面板确实弹出来了，才算“能点”
      fonts    （2026-10-17 加）点得动之后，等 document.fonts 连续 2 秒都是 loaded（字体全部到位）的时间，和 .woff2 的个数、字节数
  - 断言（只对 --report 以外的模式）：首页 HTML 原始 <= 400KB；首页 gzip <= 80KB；首页 ready <= 25s；首页 click 成功；行程页 click 成功；
    首页字体 <= 600KB、全部到位 <= 40s（Slow 3G）
"""
import functools, gzip, http.server, json, os, re, socketserver, sys, threading, time
from playwright.sync_api import sync_playwright

site = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.abspath('build/site')
REPORT = '--report' in sys.argv
INJ = sys.argv[sys.argv.index('--inject') + 1] if '--inject' in sys.argv else None
GZ = {'.html', '.js', '.css', '.svg', '.json', '.xml', '.webmanifest', '.txt'}

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self):                       # 现场 gzip（标准库的静态服务不压缩）
        p = self.translate_path(self.path.split('?')[0].split('#')[0])
        if os.path.isdir(p): p = os.path.join(p, 'index.html')
        ext = os.path.splitext(p)[1].lower()
        if not os.path.isfile(p): return super().send_head()
        data = open(p, 'rb').read()
        if INJ == 'no_home_fonts' and p == os.path.join(site, 'index.html'): data = re.sub(rb'<link rel="(stylesheet|preload)"[^>]*home[^>]*>', b'', data)
        if INJ == 'no_home_fonts' and p.endswith('home.css'): data = b''
        if INJ == 'big' and p == os.path.join(site, 'index.html'): data = data.replace(b'</body>', b'<div hidden>' + b'<a href="/x/">x</a>' * 60000 + b'</div></body>')
        if p.endswith(os.path.join('assets', 'site.js')) and b'zouni:ready' not in data: data += b"\n;try{performance.mark('zouni:ready')}catch(e){}\n"      # 改动前的站没有这个标记：现场补一个，前后才能比
        enc = 'gzip' in (self.headers.get('Accept-Encoding') or '') and ext in GZ
        if enc: data = gzip.compress(data, 6)
        self.send_response(200)
        self.send_header('Content-Type', self.guess_type(p) + ('; charset=utf-8' if ext in ('.html', '.js', '.css') else ''))
        if enc: self.send_header('Content-Encoding', 'gzip')
        self.send_header('Content-Length', str(len(data))); self.end_headers()
        import io
        return io.BytesIO(data)

socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{srv.server_address[1]}'

PROF = {'3g': dict(latency=400, down=400), '3g-worst': dict(latency=2000, down=400)}

def measure(br, path, prof, click_sel):
    c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, service_workers='block')
    pg = c.new_page()
    pg.route(re.compile(r'.*(open-meteo|amap|baidu|googletagmanager|hm\.baidu|google).*'), lambda r: r.abort())
    cdp = c.new_cdp_session(pg)
    cdp.send('Network.enable')
    P = PROF[prof]
    cdp.send('Network.emulateNetworkConditions', {'offline': False, 'latency': P['latency'], 'downloadThroughput': P['down'] * 1024 / 8, 'uploadThroughput': 400 * 1024 / 8})
    sizes = {'html': 0, 'wire': 0, 'n': 0}
    def on_resp(r):
        pass
    t0 = time.time()
    pg.add_init_script("""(function(){window.__fcp=null;try{new PerformanceObserver(function(l){l.getEntries().forEach(function(e){if(e.name==='first-contentful-paint')window.__fcp=Math.round(e.startTime)})}).observe({type:'paint',buffered:true})}catch(e){}})()""")
    pg.goto(B + path, wait_until='commit', timeout=120000)
    ready = None
    deadline = time.time() + 120
    while time.time() < deadline:
        try:
            r = pg.evaluate("(()=>{const m=performance.getEntriesByName('zouni:ready')[0];return m?Math.round(m.startTime):null})()")
        except Exception: r = None
        if r is not None: ready = r; break
        time.sleep(0.25)
    fcp = pg.evaluate('window.__fcp')
    clicked = False
    if ready is not None:
        try:
            pg.click(click_sel, timeout=15000, no_wait_after=True)
            pg.wait_for_selector('.pk[role=dialog]', timeout=15000); clicked = True
        except Exception: clicked = False
    fonts_t = None; stable = 0; dl = time.time() + 150
    while time.time() < dl:
        try: st_ = pg.evaluate("document.fonts.status")
        except Exception: st_ = None
        if st_ == 'loaded':
            stable += 1
            if stable >= 4: fonts_t = pg.evaluate("Math.round(performance.now())") - 2000; break
        else: stable = 0
        time.sleep(0.5)
    nav = pg.evaluate("(()=>{const n=performance.getEntriesByType('navigation')[0];return {html:n.decodedBodySize,wire:n.encodedBodySize}})()")
    res = pg.evaluate("(()=>{const rs=performance.getEntriesByType('resource');return {n:rs.length,wire:rs.reduce((a,r)=>a+(r.encodedBodySize||0),0)}})()")
    fr = pg.evaluate("(()=>{const rs=performance.getEntriesByType('resource').filter(r=>/\\.woff2/.test(r.name));return {n:rs.length,wire:rs.reduce((a,r)=>a+(r.encodedBodySize||0),0)}})()")
    c.close()
    return dict(html=nav['html'], html_gz=nav['wire'], fcp=fcp, ready=ready, click=clicked, res_n=res['n'], res_wire=res['wire'] + nav['wire'], fonts_n=fr['n'], fonts_wire=fr['wire'], fonts_t=fonts_t)

fails = []
out = {}
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, path, sel in (('首页', '/', '.hdt'), ('行程页 xa3', '/trip/xa3/', '.glance .dt')):
        for prof in (('3g', '3g-worst') if name == '首页' else ('3g',)):
            m = measure(br, path, prof, sel)
            out[f'{name} · {prof}'] = m
            f = lambda v: '—' if v is None else f'{v/1000:.1f}s'
            print(f'{name:8s} {prof:9s} HTML {m["html"]/1024:7.0f}KB（gzip {m["html_gz"]/1024:5.0f}KB） · 请求 {m["res_n"]} 个 共 {m["res_wire"]/1024:5.0f}KB · 首次绘制 {f(m["fcp"])} · 脚本就绪 {f(m["ready"])} · 点得动 {"是" if m["click"] else "否"} · 字体 {m["fonts_n"]} 个 {m["fonts_wire"]/1024:5.0f}KB 全部到位 {f(m["fonts_t"])}')
    br.close()
if not REPORT:
    h = out['首页 · 3g']; t = out['行程页 xa3 · 3g']
    if h['html'] > 400 * 1024: fails.append(f'首页 HTML {h["html"]/1024:.0f}KB > 400KB')
    if h['html_gz'] > 80 * 1024: fails.append(f'首页 gzip {h["html_gz"]/1024:.0f}KB > 80KB')
    if h['ready'] is None or h['ready'] > 25000: fails.append(f'首页脚本就绪 {h["ready"]} ms > 25s')
    if not h['click']: fails.append('首页 Slow 3G 下日期条点不动')
    if h['fonts_wire'] > 600 * 1024: fails.append(f'首页字体 {h["fonts_n"]} 个共 {h["fonts_wire"]/1024:.0f}KB > 600KB（首页专用小字体没生效？）')
    if h['fonts_t'] is None or h['fonts_t'] > 40000: fails.append(f'首页字体全部到位 {h["fonts_t"]} ms > 40s')
    if not t['click']: fails.append('行程页 Slow 3G 下改日期点不动')
    json.dump(out, open('build/slow3g_last.json', 'w'), ensure_ascii=False, indent=1)
    if fails:
        print('红：'); [print('  -', x) for x in fails]; sys.exit(1)
    print('Slow 3G 冷启动断言通过')
