#!/usr/bin/env python3
"""把 tests/home_matrix_browser.js（首页“替我挑三条”666 组矩阵）在 chromium 里跑一遍（2026-10-17：首页第 9 条起的卡片改成数据补出来，要等 <html data-hb> 才齐）。

用法：python3 tests/home_matrix_run.py build/site        # 失败列表为空退出码 0；否则打印前 20 条并退出码 1
"""
import functools, http.server, json, os, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright
site = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath('build/site')
class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site)); threading.Thread(target=srv.serve_forever, daemon=True).start()
js = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'home_matrix_browser.js'), encoding='utf-8').read()
with sync_playwright() as p:
    br = p.chromium.launch(); c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, service_workers='block'); pg = c.new_page(); pg.set_default_timeout(60000)
    pg.route(re.compile(r'.*(open-meteo|googletagmanager|hm\.baidu).*'), lambda r: r.abort())
    pg.goto('http://127.0.0.1:%d/' % srv.server_address[1], wait_until='networkidle')
    pg.wait_for_function("document.documentElement.getAttribute('data-hb')||!document.querySelector('script[data-b]')", timeout=30000)      # 改动前的站没有数据补齐，直接放行
    res = pg.evaluate(js)
    br.close()
bad = res.get('失败') or res.get('错误')
print('组数', res.get('组数'), '失败', len(res.get('失败') or []), '中位数', json.dumps(res.get('中位数'), ensure_ascii=False)[:200] if res.get('中位数') else '')
for x in (res.get('失败') or [])[:20]: print('  ✗', x)
sys.exit(1 if bad else 0)
