#!/usr/bin/env python3
"""总览截图（人眼验收用，不带断言）：python3 tests/map_shots.py build/site_lb 前缀 [路线,逗号]  → build/lb_shots/前缀_路线_尺寸.png
390×844 / 375×812 / 414×896 / 横屏 844×390 / 暗色 390，软件渲染，底图瓦片用空白桩（看的是叠层：名字方块 / 主线 / 控件）。"""
import json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
SITE = os.path.abspath(sys.argv[1]); PRE = sys.argv[2]; RT = (sys.argv[3] if len(sys.argv) > 3 else 'xa3,g318,xl8a,xb96a,xv612a,tk4,hsg1').split(',')
OUT = os.path.join(ROOT, 'build', 'lb_shots'); os.makedirs(OUT, exist_ok=True)
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
PNG = open(os.path.join(ROOT, 'tests', 'fixtures', 'ofm_blank.png'), 'rb').read(); CORS = {'access-control-allow-origin': '*'}
def stub(c):
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), lambda r: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b''))
    def other(r):
        if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
        elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)
env = Env({})
SIZES = [(390, 844, '390', False), (375, 812, '375', False), (414, 896, '414', False), (844, 390, 'land', False), (390, 844, 'dark', True)]
with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    for rid in RT:
        for (w, h, tag, dark) in SIZES:
            c = new_ctx(br, None, w=w, h=h, dark=dark); stub(c); pg = new_page(env, c); goto(env, pg, '/trip/%s/' % rid, 400)
            pg.evaluate("document.querySelector('.mapgo')&&document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})")
            try:
                pg.click('.mapgo'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=15000); pg.wait_for_timeout(1200)
                pg.screenshot(path=os.path.join(OUT, '%s_%s_%s.png' % (PRE, rid, tag)))
            except Exception as e: print('FAIL', rid, tag, str(e)[:100])
            c.close()
    print('errors:', env.errs[:3])
