#!/usr/bin/env python3
"""路线地图（2026-10-17，site_src/routemap.js + 自托管 MapLibre + OpenFreeMap 街道底图）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/route_map_check.py build/site [--shots DIR] [--base build/site_b0] [--live]
    python3 tests/route_map_check.py build/site --inject zoom_dead|attr_open|border_on|fs_nolock|no_fallback|nav_nogcj|sync_off|no_scroll|sticky_off|nav_via2   # 反向自检，必须变红

底图瓦片请求全部被拦截、换成固定的小瓦片（tests/fixtures/ofm_liberty_style.json 是 2026-10-17 从 OpenFreeMap 取的样式），所以不依赖外网；--live 才真的联网冒烟一次（默认跳过）。
--base 给改动前的站目录：比较首页 / 行程页 HTML 字节、site.js 增量（没给就只查“没有任何地图请求”）。

M1  点开地图出现 MapLibre canvas；+ 放大 zoom 增加、− 缩小 zoom 减少、到极限不再变（按钮置灰）
M2  全屏：铺满视口、背景不滚动（页面元素位置不动）、退出后回到原来的滚动位置；关闭按钮 / Esc / 返回键都能退；iOS UA 走“伪全屏”（没有 Fullscreen API 也行）
M3  署名：默认收起（整块 ≤44px 高，不含署名字），点开出现含 OpenStreetMap 的一行（带关闭），再点收起；没有 maplibre 自带的署名控件
M4  样式里所有 boundary / country / state / disputed 图层都隐藏，标注 text-field 改成中文优先
M5  每天小图默认折叠；打开后吸顶；点图上站点→页面对应行高亮并滚到位；点页面行→图上点高亮
M6  改行程（去掉一站 / 撤销 / 顺路加一站 / 撤销）后图上点数 = 页面可见带坐标的行数
M7  兜底：断网 / 瓦片全挂 / 样式取不到 / 没有 WebGL → 退回自画示意图（总览用页面里的静态图），写“街道地图需要联网”
M8  导航这一天：国内 GCJ-02（和独立算的一致、和 WGS84 不同）、国外 WGS84；途经点超限分段（高德每段 ≤1 个，谷歌手机 ≤3 个），相邻段首尾相接；点击会发出同样的链接；文案写明会分几段
M9  触控目标 ≥44×44；暗色模式不溢出、标记文字对比 ≥4.5；无控制台报错
M10 首屏：maplibre / routemap 点开前一个字节都不请求；点开后才取；HTML 字节不增加
M11 存成图片：出图 1080 宽、不是空白；总览（全程 + 第 N 天）、长线 105 天不糊成一团（DOM 点数、标签条可横滑）
"""
import json, os, re, sys, time, math
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'zoom_dead': ('assets/routemap.js', "      zoomBy: function (d) { map.zoomTo(", "      zoomBy: function (d) { return; map.zoomTo("),                           # 缩放按钮失效
    'attr_open': ('assets/routemap.js', '<p class="rm-atx" hidden>', '<p class="rm-atx">'),                                             # 署名默认展开
    'border_on': ('assets/routemap.js', "if (HIDE_RE.test(l.id)) {", "if (false) {"),                                                  # 边界图层没隐藏
    'fs_nolock': ('assets/routemap.js', "B.classList.add('rm-lock');", ""),                                                           # 全屏后背景滚动不锁
    'no_fallback': ('assets/routemap.js', "if (!inst.alive || inst.failed) return; inst.failed = true;", "return; inst.failed = true;"),   # 瓦片失败不兜底
    'nav_nogcj': ('assets/routemap.js', "function gcj(ll) { var f = W.zGcj; return f ? f(ll[0], ll[1]) : ll; }", "function gcj(ll) { return ll; }"),   # 导航坐标不转换
    'sync_off': ('assets/routemap.js', "    if (s0 === s1) return;\n    inst.days = days;", "    return;\n    inst.days = days;"),                    # 改行程后图不同步
    'no_scroll': ('assets/routemap.js', "    jump(Math.max(0, top)); p.row.classList.add('flash'); setTimeout(function () { p.row.classList.remove('flash'); }, 1600);\n  }\n  function rowTop0", "    p.row.classList.add('flash');\n  }\n  function rowTop0"),   # 点图上站点不滚页面
    'sticky_off': ('assets/site.css', ".rm-dayh{position:sticky;", ".rm-dayh{position:static;"),                                       # 每天小图不吸顶
    'nav_via2': ('assets/routemap.js', "function viaMax() { return APP === 'google' ? (mobileUA() ? 3 : 9) : 1; }", "function viaMax() { return APP === 'google' ? (mobileUA() ? 3 : 9) : 2; }"),   # 高德塞 2 个途经点
}
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
STYLE = open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read()
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
LIVE = '--live' in sys.argv
BASE = os.path.abspath(sys.argv[sys.argv.index('--base') + 1]) if '--base' in sys.argv else None


def stub(c, mode='ok', counter=None):
    """拦截所有 OpenFreeMap 请求：样式用 fixture，瓦片返回空（合法的空矢量瓦片）。mode: ok | tiles（瓦片全挂）| style（样式取不到）"""
    counter = counter if counter is not None else {}
    def style(r):
        counter['style'] = counter.get('style', 0) + 1
        if mode == 'style': return r.abort()
        r.fulfill(status=200, content_type='application/json', headers=CORS, body=STYLE)
    def planet(r):
        r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
    def pbf(r):
        counter['pbf'] = counter.get('pbf', 0) + 1
        if mode == 'tiles': return r.abort()
        r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
    def ne(r): r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
    def spr(r):
        if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
        else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
    c.route('https://tiles.openfreemap.org/styles/liberty', style)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/natural_earth/.+'), ne)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/sprites/.+'), spr)
    return counter


def mk_ctx(br, ua=None, dark=False, mode='ok', w=390, h=844, touch=True):
    kw = {'user_agent': ua} if ua else {}
    c = new_ctx(br, None, w=w, h=h, dark=dark, **kw)
    cnt = stub(c, mode)
    return c, cnt


def ready(pg, timeout=15000):
    pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=timeout)


def tiles(pg, timeout=12000):
    pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().tiles>0", timeout=timeout)


def cur(pg, expr):
    return pg.evaluate("(function(){var r=ZRM.cur();return r?(" + expr + "):null})()")


def open_day(pg, n, wait_tiles=True):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n)
    ready(pg)
    if wait_tiles: tiles(pg)


def open_ov(pg, wait_tiles=True):
    pg.evaluate("document.querySelector('.mapfold').scrollIntoView({block:'center',behavior:'instant'})")
    pg.click('.mapfold')
    ready(pg)
    if wait_tiles: tiles(pg)


def row_count(pg, n):
    return pg.evaluate("document.querySelectorAll('#d%d .tl > .r[data-ll]:not([hidden])').length" % n)


def mark_count(pg):
    return cur(pg, "document.querySelectorAll('.rm-pts .rm-mk[data-n]').length") or 0


def wait_marks(pg, want, timeout=6000):
    t0 = time.time()
    while time.time() - t0 < timeout / 1000:
        if mark_count(pg) == want: return True
        pg.wait_for_timeout(120)
    return mark_count(pg) == want


def contrast(a, b):
    def lum(c):
        c = [x / 255 for x in c]; c = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in c]; return .2126 * c[0] + .7152 * c[1] + .0722 * c[2]
    la, lb = lum(a), lum(b)
    if la < lb: la, lb = lb, la
    return (la + .05) / (lb + .05)


def rgb(s):
    m = re.findall(r'[\d.]+', s)[:3]; return [float(x) for x in m]


# 独立的 WGS84→GCJ-02（不用页面里的）
def gcj(lat, lng):
    if not (73.5 < lng < 135.1 and 3.8 < lat < 53.6): return lat, lng
    a, ee = 6378245.0, 0.00669342162296594323
    def tl(x, y): return -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x)) + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0 + (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0 + (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    def tg(x, y): return 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x)) + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0 + (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0 + (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    dl, dg = tl(lng - 105.0, lat - 35.0), tg(lng - 105.0, lat - 35.0); rl = lat / 180.0 * math.pi; mg = 1 - ee * math.sin(rl) ** 2; sm = math.sqrt(mg)
    dl = (dl * 180.0) / ((a * (1 - ee)) / (mg * sm) * math.pi); dg = (dg * 180.0) / (a / sm * math.cos(rl) * math.pi)
    return lat + dl, lng + dg


def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)

    # ─────────── M10 首屏：点开前不请求任何地图的东西（先做，用网络日志证明）
    with guard('M10'):
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        reqs = []
        pg.on('request', lambda r: reqs.append(r.url))
        goto(env, pg, '/trip/xa3/', 800)
        pre = [u for u in reqs if re.search(r'maplibre|routemap|openfreemap', u)]
        check('M10a 打开行程页：没有请求 maplibre / routemap / openfreemap（点开前一个字节都不取）', not pre, pre[:3])
        n0 = len(reqs)
        pg.evaluate("document.querySelector('.mapfold').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapfold'); ready(pg); tiles(pg)
        post = [u for u in reqs[n0:] if re.search(r'maplibre|routemap|openfreemap', u)]
        check('M10b 点“看路线图”后才取 routemap.js 和 maplibre（js + css）和样式', any('routemap.js' in u for u in post) and any('maplibre-gl.js' in u for u in post) and any('maplibre-gl.css' in u for u in post) and any('styles/liberty' in u for u in post), post[:6])
        # 首页也不请求
        pg2 = new_page(env, c); reqs2 = []; pg2.on('request', lambda r: reqs2.append(r.url)); goto(env, pg2, '/', 600)
        check('M10c 首页：没有请求 maplibre / routemap / openfreemap', not [u for u in reqs2 if re.search(r'maplibre|routemap|openfreemap', u)])
        # 和改动前的站比：HTML 字节（行程页、首页）不增加
        if BASE:
            for path in ('trip/xa3/index.html', 'trip/xl9a/index.html', 'index.html'):
                a, b = os.path.join(env.site, path), os.path.join(BASE, path)
                if os.path.exists(a) and os.path.exists(b):
                    check('M10d %s HTML 字节不增加（%d → %d）' % (path, os.path.getsize(b), os.path.getsize(a)), os.path.getsize(a) <= os.path.getsize(b), '')
            ja, jb = os.path.getsize(os.path.join(env.site, 'assets/site.js')), os.path.getsize(os.path.join(BASE, 'assets/site.js'))
            env.note('site.js 字节 %d → %d（+%d，只放入口；routemap.js %d、maplibre js %d + css %d 都点开才取）' % (jb, ja, ja - jb, os.path.getsize(os.path.join(env.site, 'assets/routemap.js')), os.path.getsize(os.path.join(env.site, 'assets/maplibre/maplibre-gl.js')), os.path.getsize(os.path.join(env.site, 'assets/maplibre/maplibre-gl.css'))))
            check('M10e site.js 增量 ≤ 4KB（入口代码）', ja - jb <= 4096, ja - jb)
        c.close()

    # ─────────── M1 / M3 / M4 / M2 总览（xa3）
    with guard('M1'):
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        check('M1a 默认：没有地图实例、没有 canvas', pg.evaluate("!document.querySelector('.rm')&&!window.maplibregl"))
        open_ov(pg)
        check('M1b 点开：出现 MapLibre canvas', pg.evaluate("!!document.querySelector('.rm .maplibregl-canvas')"))
        z0 = cur(pg, 'r.view.zoom()')
        pg.click('.rm-zi'); pg.wait_for_timeout(500)
        z1 = cur(pg, 'r.view.zoom()')
        check('M1c 点 +：zoom 增加（%.2f → %.2f）' % (z0, z1), z1 > z0 + .5, (z0, z1))
        pg.click('.rm-zo'); pg.wait_for_timeout(500); pg.click('.rm-zo'); pg.wait_for_timeout(500)
        z2 = cur(pg, 'r.view.zoom()')
        check('M1d 点 − 两次：zoom 减少（%.2f → %.2f）' % (z1, z2), z2 < z1 - 1, (z1, z2))
        for _ in range(16):
            if pg.is_disabled('.rm-zi'): break
            pg.click('.rm-zi'); pg.wait_for_timeout(260)
        pg.wait_for_timeout(400)
        zmax = cur(pg, 'r.view.zoom()'); dis = pg.is_disabled('.rm-zi')
        pg.evaluate("document.querySelector('.rm-zi').disabled=false"); pg.click('.rm-zi'); pg.wait_for_timeout(450)
        zmax2 = cur(pg, 'r.view.zoom()')
        check('M1e 到最大层级不再放大（%.2f → %.2f，+ 置灰）' % (zmax, zmax2), dis and zmax2 <= 17.01 and zmax2 - zmax < .05, (zmax, zmax2, dis))
        for _ in range(20):
            if pg.is_disabled('.rm-zo'): break
            pg.click('.rm-zo'); pg.wait_for_timeout(260)
        pg.wait_for_timeout(400)
        zmin = cur(pg, 'r.view.zoom()')
        pg.evaluate("document.querySelector('.rm-zo').disabled=false"); pg.click('.rm-zo'); pg.wait_for_timeout(450)
        zmin2 = cur(pg, 'r.view.zoom()')
        check('M1f 到最小层级不再缩小（%.2f → %.2f，− 置灰）' % (zmin, zmin2), zmin2 >= 1.99 and zmin - zmin2 < .05, (zmin, zmin2))
        pg.click('.rm-rs'); pg.wait_for_timeout(700)
        zr = cur(pg, 'r.view.zoom()')
        check('M1g 回到全程视野：zoom 回到合适层级（%.2f）' % zr, 6 < zr < 14, zr)
        # M3 署名
        box = pg.evaluate("(function(){var r=document.querySelector('.rm .rm-at').getBoundingClientRect();return [r.width,r.height]})()")
        check('M3a 署名默认收起：整块 ≤44px 高（%dx%d）' % (box[0], box[1]), box[1] <= 44.5 and box[0] <= 44.5, box)
        check('M3b 收起时署名文字不可见', not pg.is_visible('.rm .rm-atx'))
        check('M3c 没有 maplibre 自带的署名控件', pg.evaluate("document.querySelectorAll('.maplibregl-ctrl-attrib').length===0"))
        bt = pg.evaluate("(function(){var r=document.querySelector('.rm .rm-ai').getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})()")
        check('M3d 署名按钮 44×44', bt == [44, 44], bt)
        pg.click('.rm-ai'); pg.wait_for_timeout(100)
        shot(pg, 'ov_attr_open.png')
        tx = pg.inner_text('.rm .rm-atx') if pg.is_visible('.rm .rm-atx') else ''
        check('M3e 点开：出现含 OpenStreetMap 的一行（OpenFreeMap © OpenMapTiles Data from OpenStreetMap）', 'OpenStreetMap' in tx and 'OpenFreeMap' in tx and 'OpenMapTiles' in tx, tx)
        pg.click('.rm-ai'); pg.wait_for_timeout(100)
        check('M3f 再点收起', not pg.is_visible('.rm .rm-atx'))
        pg.click('.rm-ai'); pg.click('.rm-ax'); pg.wait_for_timeout(100)
        check('M3g 展开后点“×”也能收起', not pg.is_visible('.rm .rm-atx'))
        # M4 样式
        st = cur(pg, "(function(){var L=r.map.getStyle().layers,hit=[],vis=[];L.forEach(function(l){if(/boundary|country|state|disputed/.test(l.id)){hit.push(l.id);if((l.layout||{}).visibility!=='none')vis.push(l.id)}});var lab=L.filter(function(l){return l.id==='label_city'})[0];return {hit:hit,vis:vis,tf:JSON.stringify(lab&&lab.layout['text-field'])}})()")
        check('M4a 样式里有边界 / 国家 / 省级图层（%d 个，防空转）' % len(st['hit']), len(st['hit']) >= 5, st['hit'])
        check('M4b 这些图层一个都没有显示（visible: %s）' % st['vis'], not st['vis'], st['vis'])
        check('M4c 标注 text-field 中文优先（name:zh-Hans → name:zh → name）', 'name:zh-Hans' in st['tf'] and 'coalesce' in st['tf'], st['tf'])
        # M2 全屏（桌面浏览器路径：Fullscreen API）
        pg.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        y0 = pg.evaluate("(function(){document.querySelector('.rm').scrollIntoView({block:'start',behavior:'instant'});window.scrollBy({top:-100,behavior:'instant'});return window.scrollY})()")     # 留出吸顶标签条的位置，免得 playwright 点击前自己再滚一下
        pg.evaluate("document.addEventListener('click',function(){window.__y0=scrollY;window.__h0=document.querySelector('.hero').getBoundingClientRect().top},true)")     # 记下点击那一刻的位置（playwright 点之前可能自己再滚一下）
        pg.click('.rm-fsb'); pg.wait_for_timeout(700)      # 真点击 = 用户手势，走 Fullscreen API
        y0 = pg.evaluate("window.__y0"); el0 = pg.evaluate("window.__h0")
        shot(pg, 'ov_fullscreen.png')
        fs = pg.evaluate("(function(){var r=document.querySelector('.rm'),b=r.getBoundingClientRect();return {cls:r.classList.contains('rm-fs'),l:b.left,t:b.top,w:b.width,h:b.height,iw:innerWidth,ih:innerHeight,pos:getComputedStyle(document.body).position,api:!!document.fullscreenElement}})()")
        check('M2a 全屏：铺满视口（%dx%d，视口 %dx%d）' % (fs['w'], fs['h'], fs['iw'], fs['ih']), fs['cls'] and abs(fs['w'] - fs['iw']) < 2 and abs(fs['h'] - fs['ih']) < 2 and fs['l'] == 0 and fs['t'] == 0, fs)
        check('M2b 全屏时背景锁住（body 固定）', fs['pos'] == 'fixed', fs['pos'])
        pg.mouse.move(200, 300); pg.mouse.wheel(0, 500); pg.keyboard.press('PageDown'); pg.wait_for_timeout(300)
        el1 = pg.evaluate("document.querySelector('.hero').getBoundingClientRect().top")
        check('M2c 全屏时滚轮 / 翻页键不会让背景页面动（hero 位置 %.0f → %.0f）' % (el0, el1), abs(el1 - el0) < 2 or abs(el1 - (-y0)) < 2, (el0, el1, y0))
        vis = pg.evaluate("(function(){function v(s){var e=document.querySelector('.rm '+s);if(!e)return false;var r=e.getBoundingClientRect();return r.height>10&&r.bottom<=innerHeight+1&&r.top>=0}return {tabs:v('.rm-tabs'),panel:v('.rm-panel'),nav:v('.rm-navd')||document.querySelector('.rm-navd').hidden}})()")
        check('M2d 全屏时仍能看到天数标签条和站点列表', vis['tabs'] and vis['panel'], vis)
        pg.click('.rm-tb[data-i="1"]'); pg.wait_for_timeout(500)
        nv = pg.evaluate("(function(){var e=document.querySelector('.rm .rm-navd');if(!e||e.hidden)return null;var r=e.getBoundingClientRect();return {t:r.top,b:r.bottom,ih:innerHeight}})()")
        check('M2e 全屏时选一天后“导航这一天”在视口里', bool(nv) and nv['b'] <= nv['ih'] + 1 and nv['t'] >= 0, nv)
        pg.evaluate("document.querySelector('.rm-fsb').click()"); pg.wait_for_timeout(500)
        y1 = pg.evaluate("window.scrollY")
        check('M2f 点按钮退出后回到原来的滚动位置（%d → %d）' % (y0, y1), abs(y1 - y0) <= 2 and not pg.evaluate("document.body.classList.contains('rm-lock')"), (y0, y1))
        pg.evaluate("document.querySelector('.rm-fsb').click()"); pg.wait_for_timeout(500); pg.keyboard.press('Escape'); pg.wait_for_timeout(600)
        y2 = pg.evaluate("window.scrollY")
        check('M2g Esc 退出，位置还原（%d）' % y2, not pg.evaluate("document.querySelector('.rm').classList.contains('rm-fs')") and abs(y2 - y0) <= 2, y2)
        pg.evaluate("document.querySelector('.rm-fsb').click()"); pg.wait_for_function("document.querySelector('.rm.rm-fs')&&history.state&&history.state.zov"); pg.wait_for_timeout(300); pg.go_back(); pg.wait_for_timeout(900)
        y3 = pg.evaluate("window.scrollY")
        check('M2h 返回键先退全屏（不离开页面），位置还原（%d）' % y3, '/trip/xa3' in pg.url and not pg.evaluate("document.querySelector('.rm')&&document.querySelector('.rm').classList.contains('rm-fs')") and abs(y3 - y0) <= 2, (pg.url, y3))
        shot(pg, 'ov_open.png')
        c.close()

    # ─────────── M2 iOS 伪全屏
    with guard('M2ios'):
        c, cnt = mk_ctx(br, ua=IPHONE); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_ov(pg)
        pg.evaluate("document.querySelector('.rm').scrollIntoView({block:'start',behavior:'instant'});window.scrollBy({top:-100,behavior:'instant'})"); y0 = pg.evaluate("window.scrollY")
        pg.evaluate("document.querySelector('.rm-fsb').click()"); pg.wait_for_timeout(600)
        fs = pg.evaluate("(function(){var r=document.querySelector('.rm'),b=r.getBoundingClientRect();return {cls:r.classList.contains('rm-fs'),w:b.width,h:b.height,iw:innerWidth,ih:innerHeight,api:!!document.fullscreenElement,pos:getComputedStyle(document.body).position,native:ZRM.cur().native}})()")
        check('M2i iOS（UA 模拟）走伪全屏：不用 Fullscreen API，铺满视口（%dx%d）' % (fs['w'], fs['h']), fs['cls'] and not fs['api'] and not fs['native'] and abs(fs['w'] - fs['iw']) < 2 and abs(fs['h'] - fs['ih']) < 2 and fs['pos'] == 'fixed', fs)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
        check('M2j iOS 伪全屏：Esc 退出并还原滚动位置', not pg.evaluate("document.querySelector('.rm').classList.contains('rm-fs')") and abs(pg.evaluate("window.scrollY") - y0) <= 2)
        c.close()

    # ─────────── M5 / M6 每天小图（xa3）
    with guard('M5'):
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        check('M5a 每天小图默认折叠：没有地图，按钮 aria-expanded=false', pg.evaluate("!document.querySelector('.rm-dayh .rm')&&document.querySelector('#d2 .rm-open').getAttribute('aria-expanded')==='false'"))
        open_day(pg, 2)
        shot(pg, 'day_open.png')
        n = row_count(pg, 2)
        check('M5b 打开后图上点数 = 页面带坐标的行数（%d）' % n, wait_marks(pg, n), (mark_count(pg), n))
        # 吸顶
        sec_top = pg.evaluate("document.getElementById('d2').getBoundingClientRect().top+scrollY")
        nvh = pg.evaluate("(function(){var e=document.querySelector('.daynav');return e?e.offsetHeight:0})()")
        pg.evaluate("window.scrollTo({top:%d,behavior:'instant'})" % (sec_top + 900)); pg.wait_for_timeout(300)
        t = pg.evaluate("document.querySelector('#d2 .rm-dayh').getBoundingClientRect().top")
        inside = pg.evaluate("(function(){var s=document.getElementById('d2').getBoundingClientRect();return s.bottom>400})()")
        check('M5c 往下滚时图吸顶（离顶 %.0fpx，标签条 %dpx）' % (t, nvh), inside and nvh - 2 <= t <= nvh + 3, (t, nvh, inside))
        shot(pg, 'day_sticky.png')
        # 滚动联动：图上高亮的是当前读到的那一行（把第 k 行滚到地图下面一点）
        def row_to(jj, gap=34):
            pg.evaluate("(function(){var r=document.querySelectorAll('#d2 .tl > .r[data-ll]:not([hidden])')[%d],m=document.querySelector('#d2 .rm').getBoundingClientRect();window.scrollTo({top:r.getBoundingClientRect().top+scrollY-m.bottom-%d,behavior:'instant'})})()" % (jj - 1, gap)); pg.wait_for_timeout(500)
        k = min(3, n)
        row_to(k)
        sy = cur(pg, "(function(){var m=document.querySelector('.rm-pts .rm-cur');return m?+m.getAttribute('data-n'):0})()")
        check('M5d 把第 %d 行滚到地图下面，图上高亮第 %d 个点（高亮 %s）' % (k, k, sy), sy == k, sy)
        # 点图上站点 → 页面行高亮并滚到位
        pg.evaluate("window.scrollTo({top:%d,behavior:'instant'})" % (sec_top + 200)); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('#d2 .rm-pts .rm-mk[data-n=\"%d\"]').click()" % k); pg.wait_for_timeout(500)
        rr = pg.evaluate("(function(){var r=document.querySelectorAll('#d2 .tl > .r[data-ll]:not([hidden])')[%d],b=r.getBoundingClientRect(),m=document.querySelector('#d2 .rm').getBoundingClientRect();return {flash:r.classList.contains('flash'),top:b.top,mb:m.bottom,ih:innerHeight}})()" % (k - 1))
        check('M5e 点图上站点 %d → 页面对应行高亮（flash）' % k, rr['flash'], rr)
        check('M5f 点图上站点 → 页面滚到那一行（在地图下面、不被吸顶的图盖住）', rr['top'] >= rr['mb'] - 4 and rr['top'] < rr['ih'] - 20, rr)
        # 点页面行 → 图上点高亮
        pg.wait_for_timeout(1800)
        j = 1 if k != 1 else 2
        row_to(j, 60)
        pos = pg.evaluate("(function(){var r=document.querySelectorAll('#d2 .tl > .r[data-ll]:not([hidden])')[%d];var m=r.querySelector('.m');var b=m.getBoundingClientRect();return [b.left+12,b.top+b.height/2]})()" % (j - 1))
        pg.mouse.click(pos[0], pos[1]); pg.wait_for_timeout(300)
        hl = cur(pg, "(function(){var m=document.querySelector('.rm-pts .rm-cur');return m?+m.getAttribute('data-n'):0})()")
        check('M5g 点页面第 %d 行 → 图上第 %d 个点高亮（%s）' % (j, j, hl), hl == j, hl)
        # 页面行编号章（CSS ::before / ::after，不进文字）
        bg = pg.evaluate("(function(){var r=document.querySelector('#d2 .tl > .r[data-ll]');var a=getComputedStyle(r,'::after');return {c:a.content,w:a.width,d:getComputedStyle(r.querySelector('.dot')).opacity,html:r.outerHTML.indexOf('data-n')>=0}})()")
        check('M5h 页面行首有对应编号章（CSS 计数器，不写进行文字：%s）' % bg, 'counter(rmn)' in bg['c'] and bg['w'] == '20px' and bg['d'] == '0' and not bg['html'], bg)
        # 折叠
        pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})")
        pg.click('#d2 .rm-open'); pg.wait_for_timeout(200)
        check('M5i 再点“收起本日地图”：地图拆掉、编号章消失', pg.evaluate("!document.querySelector('.rm')&&!document.getElementById('d2').classList.contains('rm-on')"))
        # 同时只开一张
        open_day(pg, 1, False); open_day(pg, 3, False)
        check('M5j 同一时间只有一张地图（开第 3 天时第 1 天的收掉）', pg.evaluate("document.querySelectorAll('.rm').length===1&&!document.querySelector('#d1 .rm')&&!!document.querySelector('#d3 .rm')"))
        c.close()

    with guard('M6'):
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 1)
        n0 = row_count(pg, 1)
        check('M6a 起点：图上 %d 个点 = 页面 %d 行' % (mark_count(pg), n0), wait_marks(pg, n0))
        # 去掉一站
        pg.evaluate("document.querySelector('#d1 .tl .r.see .adj').scrollIntoView({block:'center',behavior:'instant'})")
        pg.evaluate("window.scrollBy({top:150,behavior:'instant'})")
        pg.click('#d1 .tl .r.see .adj >> nth=0'); pg.wait_for_selector('.pk [data-x]'); pg.click('.pk [data-x]'); pg.wait_for_timeout(300)
        n1 = row_count(pg, 1)
        check('M6b 去掉一站：图上点数跟着变（%d → %d，页面 %d）' % (n0, mark_count(pg), n1), n1 == n0 - 1 and wait_marks(pg, n1), (n0, n1, mark_count(pg)))
        pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(400)
        check('M6c 撤销：图上点数回来（%d）' % mark_count(pg), wait_marks(pg, n0), (n0, mark_count(pg)))
        c.close()
        # 顺路灰点 → 加到这天（第 3 天有候选）
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 3)
        n0 = row_count(pg, 3)
        try:
            pg.wait_for_selector('.rm-pts .rm-gy', timeout=9000)
        except Exception:
            pass
        ng = cur(pg, "document.querySelectorAll('.rm-pts .rm-gy').length")
        check('M6d 第 3 天有顺路候选：图上出现灰点（%s 个）、图例有“顺路可去”' % ng, bool(ng) and '顺路可去' in pg.inner_text('#d3 .rm-leg'), ng)
        shot(pg, 'day_gray.png')
        if ng:
            pg.evaluate("document.querySelector('#d3 .rm-pts .rm-gy').click()"); pg.wait_for_timeout(300)
            pop = pg.inner_text('#d3 .rm-pop') if pg.is_visible('#d3 .rm-pop') else ''
            check('M6e 点灰点：弹出名字和“+N 分钟”和“加到这天”（%s）' % pop.replace('\n', ' '), bool(re.search(r'\+\d+ 分钟', pop)) and '加到这天' in pop, pop)
            shot(pg, 'day_gray_pop.png')
            pg.click('#d3 .rm-pb[data-act="add"]'); pg.wait_for_timeout(600)
            n1 = row_count(pg, 3)
            check('M6f 加到这天：页面多一行（%d → %d）、图上点数同步（%d）' % (n0, n1, mark_count(pg)), n1 == n0 + 1 and wait_marks(pg, n1), (n0, n1, mark_count(pg)))
            pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(500)
            check('M6g 撤销加站：回到 %d（图 %d）' % (n0, mark_count(pg)), row_count(pg, 3) == n0 and wait_marks(pg, n0), (n0, row_count(pg, 3), mark_count(pg)))
        else:
            check('M6e/f/g 灰点交互（没有候选，没法测）', False, '第 3 天没有顺路候选')
        c.close()

    with guard('M6h'):
        # 加一天：总览开着，在第 5 天后面加一天 → 标签条和图跟着多一天（新加的那天也有“本日地图”入口）
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xj10/', 600); open_ov(pg, False)
        n0 = cur(pg, 'r.days.length'); t0 = pg.evaluate("document.querySelectorAll('.rm-tb').length")
        pg.evaluate("document.querySelector('#d5 .addafter').scrollIntoView({block:'center',behavior:'instant'})"); pg.locator('#d5 .addafter').click(); pg.wait_for_timeout(500)
        pg.locator('.pk .xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
        n1 = cur(pg, 'r.days.length'); t1 = pg.evaluate("document.querySelectorAll('.rm-tb').length"); sc = pg.evaluate("document.querySelectorAll('section.day').length")
        check('M6h 加一天：总览里天数 %s → %s（页面 %d 天）、标签条 %d → %d、新的一天有“本日地图”入口' % (n0, n1, sc, t0, t1), n1 == n0 + 1 == sc and t1 == t0 + 1 and pg.evaluate("document.querySelectorAll('#d6 .rm-row2').length") == 1, (n0, n1, sc, t0, t1))
        c.close()
        # 去掉一天：确认后页面重载，再打开总览少一天
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600); open_ov(pg, False)
        n0 = cur(pg, 'r.days.length')
        pg.evaluate("document.querySelector('#d2 .rmorig').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rmorig'); pg.wait_for_selector('.pk .rmgo'); pg.click('.pk .rmgo')
        pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
        open_ov(pg, False)
        n1 = cur(pg, 'r.days.length'); t1 = pg.evaluate("document.querySelectorAll('.rm-tb').length")
        check('M6i 去掉一天：重载后总览 %s → %s 天、标签条 %d 个（全程 + %s 天）' % (n0, n1, t1, n1), n1 == n0 - 1 and t1 == n1 + 1 and pg.evaluate("!document.querySelector('#d%d')" % (n0)), (n0, n1, t1))
        c.close()

    # ─────────── M7 兜底
    with guard('M7'):
        # a. 总览：断网（routemap.js 已加载过）→ 静态示意图 + 说明
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_ov(pg); pg.click('.mapfold'); pg.wait_for_timeout(200)
        c.set_offline(True)
        pg.click('.mapfold'); pg.wait_for_timeout(600)
        st = pg.evaluate("(function(){var h=document.querySelector('.hmap'),r=h.getBoundingClientRect(),n=h.querySelector('.rm-fbn');return {vis:r.height>50,svg:!!h.querySelector('svg'),note:n?n.textContent:'',rm:!!document.querySelector('.rm')}})()")
        check('M7a 断网点“看路线图”：退回自画示意图 + “街道地图需要联网”', st['vis'] and st['svg'] and st['note'] == '街道地图需要联网' and not st['rm'], st)
        shot(pg, 'ov_offline_fallback.png')
        c.set_offline(False); c.close()
        # b. 总览：routemap.js 从来没加载过 + 断网
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        c.set_offline(True)
        pg.evaluate("document.querySelector('.mapfold').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapfold'); pg.wait_for_timeout(800)
        st = pg.evaluate("(function(){var h=document.querySelector('.hmap'),n=h.querySelector('.rm-fbn');return {vis:h.getBoundingClientRect().height>50,note:n?n.textContent:''}})()")
        check('M7b 脚本都没取到（断网）：仍显示静态示意图和“街道地图需要联网”', st['vis'] and st['note'] == '街道地图需要联网', st)
        c.set_offline(False); c.close()
        # c. 每天的图：断网 → 示意图版（纸色底 + 线 + 编号点）
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 2); pg.click('#d2 .rm-open'); pg.wait_for_timeout(200)
        c.set_offline(True)
        pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rm-open'); ready(pg); pg.wait_for_timeout(400)
        d = pg.evaluate("(function(){var r=document.querySelector('#d2 .rm');return {sch:r.classList.contains('rm-sch'),cv:!!r.querySelector('canvas'),note:r.querySelector('.rm-note').textContent,vis:!r.querySelector('.rm-note').hidden,marks:r.querySelectorAll('.rm-mk[data-n]').length,lines:r.querySelectorAll('.rm-ln').length,why:ZRM.cur().why}})()")
        n = row_count(pg, 2)
        check('M7c 每天的图断网：示意图版（无底图 canvas）、写“街道地图需要联网”、点和线都在（%s）' % d, d['sch'] and not d['cv'] and d['note'] == '街道地图需要联网' and d['vis'] and d['marks'] == n and d['lines'] >= 1, d)
        shot(pg, 'day_offline_fallback.png')
        c.set_offline(False); c.close()
        # d. 瓦片请求全部失败
        c, cnt = mk_ctx(br, mode='tiles'); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rm-open')
        pg.wait_for_timeout(500)
        try:
            pg.wait_for_function("(function(){var r=window.ZRM&&ZRM.cur();return r&&r.failed})()", timeout=9000)
        except Exception:
            pass
        d = pg.evaluate("(function(){var r=document.querySelector('#d2 .rm');var c=window.ZRM&&ZRM.cur();return {sch:!!r&&r.classList.contains('rm-sch'),note:r&&r.querySelector('.rm-note').textContent,why:c&&c.why}})()")
        check('M7d 瓦片请求全部失败：自动退回示意图并写说明（原因 %s）' % d.get('why'), d['sch'] and d['note'] == '街道地图需要联网' and d['why'] == 'tiles', d)
        c.close()
        # e. 样式取不到
        c, cnt = mk_ctx(br, mode='style'); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rm-open'); pg.wait_for_timeout(1500)
        d = pg.evaluate("(function(){var c=window.ZRM&&ZRM.cur();return {why:c&&c.why,sch:!!document.querySelector('#d2 .rm.rm-sch')}})()")
        check('M7e 样式取不到：退回示意图（原因 %s）' % d['why'], d['sch'] and d['why'] == 'style', d)
        c.close()
        # f. 没有 WebGL
        c, cnt = mk_ctx(br); c.add_init_script("(function(){var g=HTMLCanvasElement.prototype.getContext;HTMLCanvasElement.prototype.getContext=function(t){if(/webgl/.test(t))return null;return g.apply(this,arguments)}})();")
        pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)
        pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rm-open'); pg.wait_for_timeout(1000)
        d = pg.evaluate("(function(){var c=window.ZRM&&ZRM.cur();return {why:c&&c.why,sch:!!document.querySelector('#d2 .rm.rm-sch')}})()")
        check('M7f 没有 WebGL：退回示意图（原因 %s）' % d['why'], d['sch'] and d['why'] == 'nogl', d)
        c.close()
        # g. 149 条“没有静态图”的线路：也有总览入口，打开有图（断网时是示意图版）
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/aqb3/', 600)
        check('M7g 原来没有路线图的线路（aqb3）也有“看路线图”入口', pg.evaluate("!document.querySelector('.hmap')&&!!document.querySelector('.mapfold')"))
        open_ov(pg)
        m = cur(pg, "{z:r.view.zoom(),marks:r.marks.length}")
        check('M7h aqb3 总览打开后有图、跨度很小也放大到合适层级（zoom %.1f）' % m['z'], m['marks'] > 0 and 10 <= m['z'] <= 16.01, m)
        shot(pg, 'ov_nostatic.png')
        c.close()

    # ─────────── M8 导航
    with guard('M8'):
        c, cnt = mk_ctx(br)
        hits = []
        c.route(re.compile(r'https://(uri\.amap\.com|www\.google\.com/maps)/.*'), lambda r: (hits.append(r.request.url), r.fulfill(status=204, body=''))[1])
        pg = c.new_page(); pg.set_default_timeout(12000)
        pg.on('pageerror', lambda e: env.errs.append('pageerror: ' + str(e)[:200]))
        pg.route(re.compile(r'.*(open-meteo|googletagmanager|hm\.baidu).*'), lambda r: r.abort())
        goto(env, pg, '/trip/xa3/', 600)
        pg.evaluate("document.querySelector('#d1 .rm-nb').scrollIntoView({block:'center',behavior:'instant'})")
        pg.click('#d1 .rm-nb'); pg.wait_for_selector('.rm-sheet'); pg.click('.rm-sheet .pk-x'); pg.wait_for_timeout(200)     # 第一次点会加载 routemap.js
        segs = pg.evaluate("ZRM.segs(document.getElementById('d1'))")
        rows = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#d1 .tl > .r[data-ll]:not([hidden])'),function(r){return r.getAttribute('data-ll')})")
        sp = pg.evaluate("document.getElementById('d1').getAttribute('data-sp')"); ep = pg.evaluate("document.getElementById('d1').getAttribute('data-ep')")
        want = [sp] + rows + [ep]; npts = len(want)
        check('M8a 国内（高德）第 1 天：%d 个点 → %d 段（每段 ≤3 个点：起点 + 1 个途经点 + 终点）' % (npts, len(segs)), len(segs) == math.ceil((npts - 1) / 2) and len(segs) >= 2, (npts, len(segs)))
        from urllib.parse import urlparse, parse_qs, unquote
        parsed = []
        for u in segs:
            q = parse_qs(urlparse(u).query)
            f = [x for x in q['from'][0].split(',')[:2]]; t = [x for x in q['to'][0].split(',')[:2]]; v = [x.split(',')[:2] for x in q.get('via', [])]
            parsed.append((f, v, t, q))
        check('M8b 每段最多 1 个途经点', all(len(v) <= 1 for _, v, _, _ in parsed), [len(v) for _, v, _, _ in parsed])
        chain = all(parsed[i][2] == parsed[i + 1][0] for i in range(len(parsed) - 1))
        check('M8c 相邻两段首尾相接（上一段终点 = 下一段起点）', chain)
        seq = []
        for f, v, t, q in parsed:
            if not seq: seq.append(f)
            seq += v + [t]
        okg = len(seq) == npts
        bad = []
        for (lng, lat), w in zip(seq, want):
            wl = [float(x) for x in w.split(',')]; g = gcj(wl[0], wl[1])
            if abs(float(lat) - g[0]) > 2e-6 or abs(float(lng) - g[1]) > 2e-6: bad.append((w, lat, lng, g))
        check('M8d 国内坐标是 GCJ-02（和独立算的一致，全部 %d 个点）' % npts, okg and not bad, bad[:2] or (len(seq), npts))
        rawdiff = all(abs(float(lat) - float(w.split(',')[0])) > 0.0008 for (lng, lat), w in zip(seq, want))
        check('M8e GCJ 坐标和原始 WGS84 不同（不是原样传）', rawdiff)
        check('M8f 链接是高德导航（uri.amap.com/navigation，mode=car，callnative=1）', all('uri.amap.com/navigation' in u and 'mode=car' in u and 'callnative=1' in u for u in segs))
        # 点“导航这一天”：多段 → 选择层，里面是同样的链接；点一段发出同样的链接
        pg.evaluate("document.querySelector('#d1 .rm-nb').scrollIntoView({block:'center',behavior:'instant'})")
        pg.click('#d1 .rm-nb'); pg.wait_for_selector('.rm-sheet'); pg.wait_for_timeout(200)
        links = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.rm-sheet a.rm-seg'),function(a){return a.getAttribute('href')})")
        note = pg.inner_text('.rm-sheet .xnote')
        check('M8g 多段：弹出选择层，列出 %d 段，链接和 ZRM.segs 一致' % len(links), links == segs, (len(links), len(segs)))
        check('M8h 文案写清分几段：%s' % note[:60], '最多带 1 个途经点' in note and '超过 3 个点' in note and re.search(r'分 %d 段' % len(segs), note) is not None, note)
        shot(pg, 'nav_sheet.png')
        hits.clear(); pg.click('.rm-sheet a.rm-seg >> nth=0'); pg.wait_for_timeout(500)
        check('M8i 点第 1 段：真发出同一条高德链接', hits and hits[0] == segs[0], hits[:1])
        c.close()
        # 国外：谷歌，WGS84，手机 ≤3 个途经点；电脑 ≤9 个
        for ua, lim, tag, rid in ((IPHONE, 3, '手机', 'tk4'), (IPHONE, 3, '手机', 'zash'), ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36', 9, '电脑', 'zash')):
            c, cnt = mk_ctx(br, ua=ua) if ua else mk_ctx(br)
            pg = new_page(env, c); goto(env, pg, '/trip/%s/' % rid, 600)
            tot = pg.evaluate("document.querySelectorAll('section.day').length")
            pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); ready(pg, 15000); pg.click('#d1 .rm-open')    # 加载 routemap.js
            allok = True; info = []
            for di in range(1, tot + 1):
                segs = pg.evaluate("ZRM.segs(document.getElementById('d%d'))" % di)
                rows = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#d%d .tl > .r[data-ll]:not([hidden])'),function(r){return r.getAttribute('data-ll')})" % di)
                sp = pg.evaluate("document.getElementById('d%d').getAttribute('data-sp')" % di); ep = pg.evaluate("document.getElementById('d%d').getAttribute('data-ep')" % di)
                want = [x for x in [sp] + rows + [ep] if x]
                # 和相邻重复点合并后的数量（<30 米）
                def d_(a, b):
                    a = [float(x) for x in a.split(',')]; b = [float(x) for x in b.split(',')]; return math.hypot((a[0] - b[0]) * 111, (a[1] - b[1]) * 111 * math.cos(math.radians(a[0])))
                ded = []
                for w in want:
                    if not ded or d_(ded[-1], w) >= .03: ded.append(w)
                seq = []
                prevt = None
                for u in segs:
                    q = parse_qs(urlparse(u).query)
                    o = q['origin'][0]; de = q['destination'][0]; wp = q.get('waypoints', [''])[0].split('|') if q.get('waypoints') else []
                    if len(wp) > lim: allok = False; info.append(('waypoints', di, len(wp)))
                    if prevt is not None and prevt != o: allok = False; info.append(('chain', di))
                    if not seq: seq.append(o)
                    seq += wp + [de]; prevt = de
                    if len(u) >= 2048: allok = False; info.append(('len', di, len(u)))
                    if 'travelmode=driving' not in u: allok = False; info.append(('mode', di))
                if len(ded) >= 2:
                    if len(seq) != len(ded): allok = False; info.append(('count', di, len(seq), len(ded)))
                    for s_, w in zip(seq, ded):
                        a = [float(x) for x in s_.split(',')]; b = [float(x) for x in w.split(',')]
                        if abs(a[0] - b[0]) > 1.5e-5 or abs(a[1] - b[1]) > 1.5e-5: allok = False; info.append(('coord', di, s_, w)); break
            check('M8j 国外 %s（谷歌，%s）每天：WGS84 原坐标、途经点 ≤%d、分段首尾相接、URL<2048' % (rid, tag, lim), allok and tot >= 2, info[:3])
            if tag == '手机' and rid == 'zash':
                mx = max(len(pg.evaluate("ZRM.segs(document.getElementById('d%d'))" % di)) for di in range(1, tot + 1))
                check('M8k 国外 zash 有超过 5 个点的天会分段（最多 %d 段）' % mx, mx >= 2, mx)
            c.close()

    # ─────────── M9 触控目标 / 暗色 / 报错（亮、暗各一遍）
    for dark in (False, True):
        tag = '暗色' if dark else '亮色'
        with guard('M9' + tag):
            c, cnt = mk_ctx(br, dark=dark); pg = new_page(env, c)
            goto(env, pg, '/trip/xa3/', 600)
            open_day(pg, 2)
            small0 = []
            for sel in ('#d2 .rm-open', '#d2 .rm-nb', '.mapfold'):      # 页面里的入口按钮（本日地图 / 导航这一天 / 看路线图）
                h = pg.evaluate(HIT, pg.locator(sel).first.element_handle())
                if not h or h['w'] < 43 or h['h'] < 43: small0.append((sel, h))
            check('M9z %s：页面里的入口按钮（本日地图、导航这一天、看路线图）点击区 ≥44×44' % tag, not small0, small0)
            pg.evaluate("document.querySelector('#d2 .rm-fsb').click()"); pg.wait_for_timeout(700)
            small = []
            for sel in ('.rm-rs', '.rm-fsb', '.rm-zi', '.rm-zo', '.rm-sv', '.rm-ai', '.rm-tb', '.rm-hd', '.rm-row', '.rm-navd', '.rm-pts .rm-mk[data-n]'):
                for i in range(min(pg.locator('.rm ' + sel).count(), 3)):
                    h = pg.evaluate(HIT, pg.locator('.rm ' + sel).nth(i).element_handle())
                    if sel.endswith('.rm-mk[data-n]'):      # 标记：自己的盒子 44×44；点击区会被紧挨着的另一个标记盖住一部分，那不算“点击区太小”（两点离得近是地理决定的）
                        if not h or h['bw'] < 44 or h['bh'] < 44 or h['w'] < 30: small.append((sel, h))
                    elif not h or h['w'] < 43 or h['h'] < 43: small.append((sel, h))
            check('M9a %s：地图上所有可点元素 ≥44×44（实测点击区）' % tag, not small, small[:3])
            col = pg.evaluate("""(function(){var out=[];['rm-c0','rm-c1','rm-c2'].forEach(function(a){['rm-s0','rm-s1','rm-s2'].forEach(function(b){var e=document.createElement('div');e.className='rm '+a+' '+b;e.innerHTML='<div class="rm-pts"><button class="rm-mk"><i>1</i></button></div>';document.body.appendChild(e);var i=e.querySelector('i'),cs=getComputedStyle(i);out.push([a+' '+b,cs.backgroundColor,cs.color]);e.remove()})});return out})()""")
            bad = [(n, round(contrast(rgb(bg), rgb(fg)), 2)) for n, bg, fg in col if contrast(rgb(bg), rgb(fg)) < 4.5]
            check('M9b %s：9 种天色的标记数字对比 ≥4.5' % tag, not bad, bad)
            ov = pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1&&document.querySelector('.rm').scrollWidth<=innerWidth+1")
            check('M9c %s：全屏时没有横向溢出' % tag, ov)
            shot(pg, ('fs_dark.png' if dark else 'fs_light.png'))
            pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
            ov = pg.evaluate("document.documentElement.scrollWidth<=innerWidth+1")
            check('M9d %s：退出后页面没有横向溢出' % tag, ov)
            if dark:
                f = pg.evaluate("getComputedStyle(document.querySelector('.rm .maplibregl-canvas')).filter")
                check('M9e 暗色：底图有深色滤镜（%s）' % f[:30], 'invert' in f, f)
            c.close()

    # ─────────── M11 存成图片 / 长线 / 总览分天
    with guard('M11'):
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_ov(pg)
        pg.click('.rm-tb[data-i="1"]'); pg.wait_for_timeout(500)
        dim = pg.evaluate("document.querySelectorAll('.rm-svg .rm-ln.rm-dim').length")
        mk = pg.evaluate("document.querySelectorAll('.rm-pts .rm-mk[data-n]').length")
        check('M11a 总览点“第 2 天”：聚焦那一天（%d 个编号点），其余天的线变淡（%d 条）' % (mk, dim), mk == row_count(pg, 2) and dim == 2, (mk, dim))
        check('M11b 面板显示第 2 天的信息头（红色大数字 02 + 标题 + 今天：…）', pg.evaluate("(function(){var n=document.querySelector('.rm-hd .rm-no');return !!n&&n.textContent==='02'&&/今天：/.test(document.querySelector('.rm-panel').innerText)})()"))
        shot(pg, 'ov_day2.png')
        pg.evaluate("document.querySelector('.rm-sv').scrollIntoView({block:'center',behavior:'instant'})")
        pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=10000); pg.wait_for_timeout(300)
        im = pg.evaluate("""new Promise(function(res){var i=document.querySelector('.rm-shot img'),a=new Image();a.onload=function(){var c=document.createElement('canvas');c.width=a.width;c.height=a.height;var x=c.getContext('2d');x.drawImage(a,0,0);var d=x.getImageData(0,0,c.width,c.height).data,s={},n=0;for(var k=0;k<d.length;k+=4*997){s[d[k]+','+d[k+1]+','+d[k+2]]=1;n++}var dark=0;for(var y=c.height-190;y<c.height;y+=4)for(var xx=0;xx<c.width;xx+=4){var p=x.getImageData(xx,y,1,1).data;if(p[0]<60&&p[1]<60&&p[2]<60)dark++}res({w:a.width,h:a.height,colors:Object.keys(s).length,dark:dark,src:i.src.slice(0,22)})};a.src=i.src})""")
        check('M11c 存图：1080 宽的 PNG、不是空白（%s）' % im, im['w'] == 1080 and im['h'] > 1000 and im['colors'] > 8 and im['src'].startswith('data:image/png') and im['dark'] > 200, im)
        shot(pg, 'save_shot.png')
        pg.click('.rm-shot .hz-x'); pg.wait_for_timeout(200)
        check('M11d 关掉存图层后地图还在', pg.evaluate("!!document.querySelector('.rm')&&!document.querySelector('.rm-shot')"))
        c.close()
        # 105 天长线
        c, cnt = mk_ctx(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xb96a/', 900)
        t0 = time.time(); open_ov(pg, False); pg.wait_for_timeout(500)
        info = cur(pg, "{days:r.days.length,marks:r.marks.length,tabs:document.querySelectorAll('.rm-tb').length,lg:document.querySelector('.rm-tabs').className,vis:Array.prototype.filter.call(document.querySelectorAll('.rm-pts .rm-db'),function(b){return b.style.visibility!=='hidden'}).length,sw:document.querySelector('.rm-tabs').scrollWidth,cw:document.querySelector('.rm-tabs').clientWidth}")
        check('M11e 105 天长线：总览一屏里天数章不糊成一团（可见 %s 个，共 %s 个）、标签条可横滑' % (info['vis'], info['days']), info['days'] >= 100 and info['vis'] <= 45 and 'long' in info['lg'] and info['sw'] > info['cw'], info)
        check('M11f 105 天长线：DOM 点数可控（%s 个）、打开 <10 秒（%.1fs，别的进程在跑时会慢）' % (info['marks'], time.time() - t0), info['marks'] <= 600 and time.time() - t0 < 10, info)
        pg.evaluate("document.querySelector('.rm-tb[data-i=\"4\"]').click()"); pg.wait_for_timeout(500)
        d = pg.evaluate("(function(){var ds=ZRM.cur().days;return {num:document.querySelectorAll('.rm-pts .rm-mk[data-n]').length,dim:document.querySelectorAll('.rm-svg .rm-ln.rm-dim').length,others:ds.filter(function(x,i){return i!==4&&x.pts.length>=2}).length,pts:ds[4].pts.length}})()")
        check('M11g 长线选第 5 天：只给这一天编号（%d 个），其余 %d 天的线淡化' % (d['num'], d['dim']), d['num'] == d['pts'] and d['dim'] == d['others'] and d['dim'] > 50, d)
        shot(pg, 'ov_long_day5.png')
        c.close()

    # ─────────── 可选：联网冒烟（真 OpenFreeMap）
    if LIVE:
        with guard('LIVE'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)
            open_day(pg, 2, False)
            pg.wait_for_function("ZRM.cur()&&(ZRM.cur().tiles>0||ZRM.cur().failed)", timeout=30000); pg.wait_for_timeout(2500)
            r = cur(pg, "{tiles:r.tiles,failed:r.failed,why:r.why}")
            check('LIVE 联网：真的从 OpenFreeMap 取到瓦片、没有退回示意图（%s）' % r, r['tiles'] > 0 and not r['failed'], r)
            st = cur(pg, "(function(){var L=r.map.getStyle().layers,hit=[],vis=[];L.forEach(function(l){if(/boundary|country|state|disputed/.test(l.id)){hit.push(l.id);if((l.layout||{}).visibility!=='none')vis.push(l.id)}});return {hit:hit.length,vis:vis,n:L.length}})()")
            check('LIVE 线上样式：边界 / 国家 / 省级图层 %d 个全部隐藏（线上共 %d 层；fixture 过期了这里会红）' % (st['hit'], st['n']), st['hit'] >= 5 and not st['vis'], st)
            shot(pg, 'live_day2.png'); c.close()
    else:
        env.note('联网冒烟（--live）：这次没跑')
    br.close()

env.finish('路线地图 route_map_check')
