#!/usr/bin/env python3
"""路线地图 · 地图 App 式整屏界面（2026-10-18）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/map_app_check.py build/site [--shots DIR] [--only M1,M3] [--live]
    python3 tests/map_app_check.py build/site --inject 名字      # 反向自检，每个名字都必须变红（名字见 INJ，共 29 种）

手势全部是 CDP 合成触摸（tests/map_touch.py，走浏览器真实输入管线），不是在页面里伪造事件。OpenFreeMap 的瓦片 / 索引请求被拦成空瓦片（自托管的样式、sprite、西文字形走本地站），不依赖外网；--live 才真联网冒烟一次。

M1  一步直达整屏：点一次进入；覆盖整个视口；占一条历史，history.back() 关闭并回到原滚动位置；“×”也行；页面里没有内嵌地图
M2  手势：单指拖动改变中心；双指缩放以手指中心（落在站点方块上也一样）；双击放大；双指轻点缩小；旋转默认关；cooperativeGestures 关；
    不滚页面、不缩页面（scrollY 不变、visualViewport.scale 恒为 1、滚轮也不行）；touch-action:none；点空白取消选中
M3  底部面板：默认档（高屏半屏 / 矮屏收起）；三档吸附；快速划走下一档；半屏时地图可见 ≥ 视口 45%；拉满后列表自己滚、滚到顶继续下拉才收起；
    标签条选中整块反白且始终在可视范围、横向可滑；信息头红色衬线大数字；站点行 = 序号 + 名字 + 一句话 + 小标签 + 到下一站多久；只有一个墨色主按钮
M4  联动：点标记 → 地图飞过去（落点在露出来的地图中央、缩放 12–15）+ 面板换成站点卡片；点列表同；卡片左右滑切上 / 下一站；点空白回列表；
    整屏期间页面 scrollY 不变；关闭后页面滚到刚才那一站并高亮；灰点“顺路可去”：卡片有“+N 分钟”和“加到这天”（可撤销）；改行程后图自己重画
M5  控件：全部 ≥44×44、在视口里、没被盖住；底部没有固定栏；拉满时右侧控件让开；署名默认收起；指北针只在旋转后出现；回到视野；放大缩小到头置灰
M6  加载：点开 300ms 内就有示意图 + 线路 + 面板；有进度提示；瓦片全失败 → 示意图 + 重试（重试真能再来一次）；样式取不到 → 示意图；断网直接示意图；联网自动重试
M7  点开前零请求；点开后才取；空闲预取只在 4g / wifi 且非省流量（省流量 / 3g / 不明时按规则少取或不取）
M8  长线（105 天）：标记 / 线的重画耗时和帧率采样（软件渲染下以“我们自己的耗时”为准，帧率只记录）
M9  暗色模式：地图滤镜、色板换成暗色版、不溢出；无控制台报错（Env 统一记账）
M10 存成图片 · 导航：存图 1080 宽不空白、只存面板上方那块；导航分段（GCJ-02 / WGS84、每段途经点、首尾相接）、分段层方形按钮、断网置灰
M11 样式：加载进地图的样式里边界 / 国家 / 省级图层全是 none（运行时读 map.getLayer）；字形走系统字体（不请求中文 glyph 包）
"""
import json, math, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

INJ = {
    # —— routemap.js 行为 ——
    'coop_on': ('assets/routemap.js', "cooperativeGestures: false,", "cooperativeGestures: true,"),                                  # 整屏里又要两根手指
    'snap_off': ('assets/routemap.js', "      snapTo(inst, best, true);\n      if (inst.mode === 'list')", "      setSheet(inst, inst.sheetH, false);\n      if (inst.mode === 'list')"),                  # 松手不吸附
    'half_tall': ('assets/routemap.js', "var c = grab + tabs + sum + sb, full = H - inst.st - 64, half = Math.round(H * .5);", "var c = grab + tabs + sum + sb, full = H - inst.st - 64, half = Math.round(H * .78);"),   # 半屏太高，地图只剩 22%
    'no_handoff': ('assets/routemap.js', "if (g.list && inst.snap === d.length - 1 && inst.bodyEl.scrollTop <= 0 && y > g.lastY + 1) {", "if (false) {"),     # 列表滚到顶继续下拉不收面板
    'fly_off': ('assets/routemap.js', "    inst.view.fly(cam, 650);\n  }", "  }"),                                                  # 点站点地图不飞过去
    'row_back_off': ('assets/routemap.js', "    p.row.classList.add('flash'); setTimeout(function () { p.row.classList.remove('flash'); }, 1600);\n  }\n  function closeInst", "  }\n  function closeInst"),   # 关闭后页面不滚到那一站
    'no_lock': ('assets/site.css', "body.rm-lock{position:fixed;left:0;right:0;width:100%;overflow:hidden}", "body.rm-lock{}"),                                    # 整屏时页面还能滚（锁滚动的样式没了；起步壳和 routemap.js 两处都加类，所以注入点放在 CSS）
    'retry_off': ('assets/routemap.js', "      if (t.closest('.rm-rt')) { retry(inst); return; }\n", ""),                                       # 重试按钮不起作用
    'card_swipe_off': ('assets/routemap.js', "      if (inst.progScroll || !(down || now() < until)) return; clearTimeout(t);", "      return; clearTimeout(t);"),                      # 卡片左右滑不换站
    'blank_keeps': ('assets/routemap.js', "    if (!c.length) { closeAt(inst); if (inst.cur || inst.curG || inst.curH) deselect(inst); return; }", "    if (!c.length) { closeAt(inst); return; }"),   # 点空白不取消选中
    'rot_on': ('assets/routemap.js', "if (!rot) map.touchZoomRotate.disableRotation();", ""),                                             # 双指旋转默认开
    'cjk_net': ('assets/routemap.js', "localIdeographFontFamily: CJK_FONT,", ""),                                                         # 中文字形又去下载
    'pinch_page': ('assets/site.css', ".rm.rm-fs{position:fixed;left:0;top:0;right:0;bottom:0;z-index:45;background:var(--card);overflow:hidden;touch-action:none;", ".rm.rm-fs{position:fixed;left:0;top:0;right:0;bottom:0;z-index:45;background:var(--card);overflow:hidden;touch-action:auto;"),   # 整屏层不禁手势（页面能缩放 / 滚）
    'x_small': ('assets/site.css', ".rm .rm-x{left:8px;top:calc(8px + env(safe-area-inset-top,0px));", ".rm .rm-x{width:30px;height:30px;left:8px;top:calc(8px + env(safe-area-inset-top,0px));"),   # 关闭键缩小
    'dock_show': ('assets/site.css', "body.rmap-on .dock{display:none}", ""),                                                          # 底部固定栏还在
    'col_full': ('assets/site.css', ".rm.rm-sfull .rm-col,.rm.rm-sfull .rm-at{opacity:0;visibility:hidden;pointer-events:none}", ""),   # 拉满时右侧控件不让开
    'mk_auto': ('assets/site.css', ".rm .rm-pts>*{position:absolute;left:0;top:0;pointer-events:none}", ".rm .rm-pts>*{position:absolute;left:0;top:0;pointer-events:auto}"),   # 标记又抢手指
    'tap_radius': ('assets/routemap.js', "if (d <= (m.small ? 20 : 26)) c.push({ m: m, d: d });", "if (d <= (m.small ? 4 : 6)) c.push({ m: m, d: d });"),                    # 点按范围缩成几个像素
    'no_dense': ('assets/routemap.js', "m.small = tight; m.el.classList.toggle('rm-sm', tight);", "m.small = false;"),                                        # 挤在一起也不缩小
    'no_merge': ('assets/routemap.js', "var t = k.g.length > 1 ? rangeLabel(k.g) : String(k.m.day + 1)", "var t = String(k.m.day + 1)"),                          # 总览合并的天不写范围
    'adj_small': ('assets/site.css', ".r .s .adj:after,.adj:after{inset:-14px -10px}", ".r .s .adj:after,.adj:after{inset:0}"),                              # “调整”点击区缩回去
    'nav_off_pg': ('assets/site.js', "function navBtns(){var off=navigator.onLine===false;", "function navBtns(){var off=false;"),                           # 页面里的导航按钮断网不置灰
    # —— site.js（起步壳 / 入口 / 预取）——
    'boot_blank': ('assets/site.js', "if(d.length>1){var pts=d.map(function(p){return P(p).join(',')}).join(' ');svg+='<polyline", "if(false){var pts=d.map(function(p){return P(p).join(',')}).join(' ');svg+='<polyline"),   # 起步壳没有线路
    'prefetch_saver': ('assets/site.js', "if(c.saveData)return;var t=c.effectiveType;", "var t=c.effectiveType;"),                         # 省流量也预取
    'prefetch_slow': ('assets/site.js', "if(t&&t!=='4g')return;var big=", "var big="),                                                 # 3g 也预取
    'warm_off': ('assets/site.js', "mlTag();warm(b);      // 起步壳已经塞进 DOM", "mlTag();      // 起步壳已经塞进 DOM"),   # 点开不并行预热
    # —— sw.js ——
    'sw_tiles_off': ('sw.js', "if (/\\/planet\\/[^/]+\\/\\d+\\/\\d+\\/\\d+\\.pbf$|\\/natural_earth\\/|\\/fonts\\//.test(u.pathname)) swr(e, r, TILES, TILE_MAX);", "if (false) swr(e, r, TILES, TILE_MAX);"),   # 瓦片不进缓存（注意要保持语法有效：删掉整行会让后面的 else if 变成语法错误，SW 装不上，测试会一直等 serviceWorker.ready）
    'sw_tiles_inf': ('sw.js', "const TILE_MAX = 500;", "const TILE_MAX = 0;"),                                                              # 瓦片缓存不限条数（和 data_checks 一起红）
    # —— 样式 ——
    'border_on': ('assets/map/style.json', '"visibility":"none"', '"visibility":"visible"'),                                              # 边界图层没隐藏
}
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
LIVE = '--live' in sys.argv


def want(k): return ONLY is None or k in ONLY


class Stub:
    """OpenFreeMap 的请求：瓦片索引 / 瓦片 / 栅格 / 非自托管范围的字形。mode: ok | tiles（瓦片全挂）| hang（瓦片挂起不回）"""
    def __init__(self, c, mode='ok'):
        self.mode = mode; self.n = {'pbf': 0, 'tilejson': 0, 'other': 0}; self.urls = []
        def planet(r):
            self.n['tilejson'] += 1; self.urls.append(r.request.url)
            r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
        def pbf(r):
            self.n['pbf'] += 1; self.urls.append(r.request.url)
            if self.mode == 'tiles': return r.abort()
            if self.mode == 'hang': return
            r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        def other(r):
            self.n['other'] += 1; self.urls.append(r.request.url)
            if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
            elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
            else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


def mk(br, mode='ok', dark=False, ua=None, w=390, h=844, storage=None, **kw):
    ukw = {'user_agent': ua} if ua else {}
    c = new_ctx(br, None, w=w, h=h, dark=dark, storage=storage, **ukw, **kw)
    return c, Stub(c, mode)


def ready(pg, timeout=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=timeout)
def tiles(pg, timeout=12000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().tiles>0", timeout=timeout)
def cur(pg, expr): return pg.evaluate("(function(){var r=ZRM.cur();return r?(" + expr + "):null})()")


def open_ov(pg, wait_tiles=True):
    pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})")
    pg.click('.mapgo'); ready(pg)
    if wait_tiles: tiles(pg)


def open_day(pg, n, wait_tiles=True):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n); ready(pg)
    if wait_tiles: tiles(pg)


def state(pg):
    return pg.evaluate("""(function(){var z=ZRM.cur();if(!z)return null;var c=z.view.cam();
      return {tiles:z.tiles,sel:z.sel,cur:z.cur,curG:z.curG,curH:z.curH,mode:z.mode,sh:z.sheetH,snap:z.snap,z:c.z,lng:c.lng,lat:c.lat,sy:window.scrollY,vv:visualViewport.scale,vh:z.vh,failed:!!z.failed,why:z.why||'',kind:z.view.kind,top:parseFloat(document.body.style.top||'0'),n:z.days.length,
        bearing:z.view.kind==='ml'?z.map.getBearing():0}})()""")


def mark_px(pg, n):
    return pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='n'&&m.n===%d)return [m.px,m.py]}return null})()" % n)


def snap_wait(pg, ms=700): pg.wait_for_timeout(ms)


def hit(pg, sel):
    """elementFromPoint 命中自己（没被别的盖住）+ 尺寸"""
    return pg.evaluate("""(sel)=>{var e=document.querySelector(sel);if(!e)return null;var r=e.getBoundingClientRect();if(r.width<1)return null;
      var x=r.left+r.width/2,y=r.top+r.height/2,t=document.elementFromPoint(x,y);return {w:Math.round(r.width*10)/10,h:Math.round(r.height*10)/10,l:r.left,t:r.top,r:r.right,b:r.bottom,ok:!!t&&(t===e||e.contains(t)),vis:getComputedStyle(e).visibility}}""", sel)


def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


def rgb(s):
    m = re.findall(r'[\d.]+', s)[:3]; return [float(x) for x in m]


def gcj(lat, lng):
    if not (73.5 < lng < 135.1 and 3.8 < lat < 53.6): return lat, lng
    a, ee = 6378245.0, 0.00669342162296594323
    def tl(x, y): return -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * math.sqrt(abs(x)) + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0 + (20.0 * math.sin(y * math.pi) + 40.0 * math.sin(y / 3.0 * math.pi)) * 2.0 / 3.0 + (160.0 * math.sin(y / 12.0 * math.pi) + 320 * math.sin(y * math.pi / 30.0)) * 2.0 / 3.0
    def tg(x, y): return 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(abs(x)) + (20.0 * math.sin(6.0 * x * math.pi) + 20.0 * math.sin(2.0 * x * math.pi)) * 2.0 / 3.0 + (20.0 * math.sin(x * math.pi) + 40.0 * math.sin(x / 3.0 * math.pi)) * 2.0 / 3.0 + (150.0 * math.sin(x / 12.0 * math.pi) + 300.0 * math.sin(x / 30.0 * math.pi)) * 2.0 / 3.0
    dl, dg = tl(lng - 105.0, lat - 35.0), tg(lng - 105.0, lat - 35.0); rl = lat / 180.0 * math.pi; mg = 1 - ee * math.sin(rl) ** 2; sm = math.sqrt(mg)
    dl = (dl * 180.0) / ((a * (1 - ee)) / (mg * sm) * math.pi); dg = (dg * 180.0) / (a / sm * math.cos(rl) * math.pi)
    return lat + dl, lng + dg


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()      # 预热 GPU 进程（第一个 WebGL 上下文在软件渲染下要几百毫秒到一秒；单跑某一节时它会被算进第一个场景的“300ms 内出现”里）

    # ─────────── M1 一步直达整屏
    if want('M1'):
        with guard('M1'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            pg.evaluate("window.scrollTo({top:900,behavior:'instant'})"); pg.wait_for_timeout(300)
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(200)
            y0 = pg.evaluate("window.scrollY"); h0 = pg.evaluate("history.length")
            pg.click('.mapgo')      # 就这一次点击
            pg.wait_for_selector('.rm.rm-fs', timeout=3000); ready(pg)
            r = pg.evaluate("""(function(){var e=document.querySelector('.rm'),b=e.getBoundingClientRect();return {l:b.left,t:b.top,w:b.width,h:b.height,iw:innerWidth,ih:innerHeight,par:e.parentNode===document.body,pos:getComputedStyle(e).position,
              lock:document.body.classList.contains('rm-lock'),nrm:document.querySelectorAll('.rm').length,hist:history.length,inline:!!document.querySelector('main .rm,article .rm,.rm-dayh,.rm-ovh'),type:ZRM.cur().type}})()""")
            check('M1a 点一次“看路线图”就进整屏地图：图层铺满视口（%dx%d@%d,%d）、fixed、挂在 body 上、类型 ov' % (r['w'], r['h'], r['l'], r['t']), r['pos'] == 'fixed' and r['par'] and abs(r['w'] - r['iw']) < 1 and abs(r['h'] - r['ih']) < 1 and r['l'] == 0 and r['t'] == 0 and r['type'] == 'ov' and r['nrm'] == 1, r)
            check('M1b 占一条历史（%d → %d）、页面锁住（rm-lock）' % (h0, r['hist']), r['hist'] == h0 + 1 and r['lock'], r)
            check('M1c 页面里没有内嵌地图（.rm 不在 main / article 里，没有 .rm-dayh / .rm-ovh）', not r['inline'], r)
            shot(pg, 'half_ov.png')
            pg.go_back(); pg.wait_for_timeout(700)
            r2 = pg.evaluate("({layer:!!document.querySelector('.rm'),lock:document.body.classList.contains('rm-lock'),pk:document.body.classList.contains('pk-open'),sy:window.scrollY,url:location.pathname})")
            check('M1d 手机返回键（history.back）：地图关掉、解锁、回到原来的滚动位置（%d → %d）、还在本页（%s）' % (y0, r2['sy'], r2['url']), not r2['layer'] and not r2['lock'] and not r2['pk'] and abs(r2['sy'] - y0) <= 2 and r2['url'] == '/trip/xa3/', r2)
            # 本日地图：一步直达 + “×”关闭
            pg.evaluate("window.scrollTo({top:2200,behavior:'instant'})"); pg.wait_for_timeout(200)
            pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(200); y1 = pg.evaluate("window.scrollY")
            pg.evaluate("document.querySelector('#d2 .rm-open').click()"); ready(pg)      # 用脚本点：真鼠标点之前 Playwright 会为躲吸顶标签条再滚一下，进入时的位置就不是 y1 了
            st = state(pg)
            check('M1e 每天的“本日地图”也一步直达整屏，直接停在那一天（sel=%s，type=day）' % st['sel'], st['sel'] == 1 and cur(pg, 'r.type') == 'day', st)
            pg.click('.rm-x'); pg.wait_for_timeout(700)
            r3 = pg.evaluate("({layer:!!document.querySelector('.rm'),lock:document.body.classList.contains('rm-lock'),sy:window.scrollY})")
            check('M1f 左上“×”关闭：回到原页面原滚动位置（%d → %d）' % (y1, r3['sy']), not r3['layer'] and not r3['lock'] and abs(r3['sy'] - y1) <= 2, r3)
            # 关闭后再次打开、再返回：历史不乱（再点 × 后 history.length 不增长）
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg); pg.click('.rm-x'); pg.wait_for_timeout(600)
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg); pg.click('.rm-x'); pg.wait_for_timeout(600)
            check('M1g 开关两次后页面、历史还在（本页 %s）' % pg.evaluate("location.pathname"), pg.evaluate("location.pathname") == '/trip/xa3/' and not pg.evaluate("!!document.querySelector('.rm')"), pg.evaluate("history.length"))
            c.close()

    # ─────────── M2 手势（CDP 触摸）
    if want('M2'):
        with guard('M2'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_ov(pg)
            pg.wait_for_timeout(600)
            check('M2a cooperativeGestures 关（单指就能拖）：handler 未启用、页面里没有合作手势提示层', pg.evaluate("!ZRM.cur().map.cooperativeGestures.isEnabled()&&!document.querySelector('.maplibregl-cooperative-gesture-screen')"))
            sty = pg.evaluate("(function(){var s=getComputedStyle(document.querySelector('.rm-stage')),r=getComputedStyle(document.querySelector('.rm')),b=getComputedStyle(document.body);return {ta:s.touchAction,tar:r.touchAction,ob:r.overscrollBehaviorY,bp:b.position}})()")
            check('M2b touch-action:none（舞台 / 整屏层）、overscroll-behavior:contain、body fixed（%s）' % sty, sty['ta'] == 'none' and sty['tar'] == 'none' and sty['ob'] == 'contain' and sty['bp'] == 'fixed', sty)
            s0 = state(pg)
            T.drag(260, 360, 130, 300); pg.wait_for_timeout(700); s1 = state(pg)
            pxs = pg.evaluate("(function(){var z=ZRM.cur(),a=z.view.project([%f,%f]),b=z.view.project([%f,%f]);return [a.x-b.x,a.y-b.y]})()" % (s0['lat'], s0['lng'], s1['lat'], s1['lng']))
            check('M2c 单指拖动改变中心（屏幕上移了 %.0f,%.0f px；手指走了 -130,-60）' % (pxs[0], pxs[1]), pxs[0] < -80 and pxs[1] < -30, pxs)
            z0 = s1['z']; q0 = pg.evaluate("(function(){var z=ZRM.cur().map,p=z.unproject([300,260]);return [p.lng,p.lat]})()")
            T.pinch(300, 260, 50, 170); pg.wait_for_timeout(900); s2 = state(pg)
            q1 = pg.evaluate("(function(){var z=ZRM.cur().map,p=z.project([%f,%f]);return [p.x,p.y]})()" % (q0[0], q0[1]))
            check('M2d 双指张开缩放：层级增加（%.2f → %.2f）、手指中心下的那个地点基本没动（偏 %.0f,%.0f px）' % (z0, s2['z'], q1[0] - 300, q1[1] - 260), s2['z'] > z0 + .8 and abs(q1[0] - 300) < 40 and abs(q1[1] - 260) < 40, (z0, s2['z'], q1))
            T.pinch(195, 260, 220, 80); pg.wait_for_timeout(800); s3 = state(pg)
            check('M2e 双指捏合：层级减少（%.2f → %.2f）' % (s2['z'], s3['z']), s3['z'] < s2['z'] - .6, (s2['z'], s3['z']))
            T.double_tap(190, 240); pg.wait_for_timeout(800); s4 = state(pg)
            check('M2f 双击放大（%.2f → %.2f）' % (s3['z'], s4['z']), s4['z'] > s3['z'] + .6, (s3['z'], s4['z']))
            T.two_finger_tap(190, 240); pg.wait_for_timeout(800); s5 = state(pg)
            check('M2g 双指轻点缩小（%.2f → %.2f）' % (s4['z'], s5['z']), s5['z'] < s4['z'] - .6, (s4['z'], s5['z']))
            b0 = state(pg)['bearing']
            cx, cy = 195, 240; steps = 12
            T._send('touchStart', [(cx - 60, cy), (cx + 60, cy)])
            for i in range(1, steps + 1):
                a = math.radians(40 * i / steps); T._send('touchMove', [(cx - 60 * math.cos(a), cy - 60 * math.sin(a)), (cx + 60 * math.cos(a), cy + 60 * math.sin(a))]); time.sleep(.016)
            T._send('touchEnd', []); pg.wait_for_timeout(500); s6 = state(pg)
            check('M2h 双指旋转默认关：方位角仍是 0（%.1f），指北针按钮没出现' % s6['bearing'], abs(s6['bearing']) < .5 and pg.evaluate("document.querySelector('.rm-cp').hidden"), s6['bearing'])
            # 起点落在站点方块上的双指缩放：缩放的是地图、不是页面
            mp = mark_px(pg, 1) if cur(pg, "r.sel") is not None and cur(pg, "r.sel") >= 0 else None
            sv0 = state(pg); zz = sv0['z']
            T.pinch(190, 300, 60, 200); pg.wait_for_timeout(700); sv1 = state(pg)
            check('M2i 双指缩放不触发页面缩放（visualViewport.scale=%s）、页面没滚（scrollY=%s）' % (sv1['vv'], sv1['sy']), sv1['vv'] == 1 and sv1['sy'] == 0 == s0['sy'], sv1)
            pg.mouse.move(190, 300); pg.mouse.wheel(0, 600); pg.wait_for_timeout(300)
            check('M2j 滚轮 / 页面滚动不动页面（scrollY=%s，body.top 不变 %s）' % (pg.evaluate("window.scrollY"), state(pg)['top']), pg.evaluate("window.scrollY") == 0 and state(pg)['top'] == s0['top'], (pg.evaluate("window.scrollY"), state(pg)['top'], s0['top']))
            # 点在标记上缩放（标记不接收手指）
            pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(1200)
            mp = mark_px(pg, 1); z_a = state(pg)['z']
            if mp:      # 一根手指正好按在站点方块上，另一根从旁边拉开
                T._send('touchStart', [(mp[0], mp[1]), (mp[0] - 50, mp[1])])
                for i in range(1, 13): T._send('touchMove', [(mp[0], mp[1]), (mp[0] - 50 - 12 * i, mp[1])]); time.sleep(.016)
                T._send('touchEnd', []); pg.wait_for_timeout(700)
            check('M2k 双指起点落在站点方块上：缩放的是地图（%.2f → %.2f）不是整页（scale=%s）' % (z_a, state(pg)['z'], state(pg)['vv']), bool(mp) and state(pg)['z'] > z_a + .5 and state(pg)['vv'] == 1, (mp, z_a, state(pg)))
            c.close()

    # ─────────── M3 底部面板
    if want('M3'):
        with guard('M3a'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xb96a/', 900)
            open_ov(pg, False); pg.wait_for_timeout(700)
            s = state(pg); H = s['vh']
            check('M3a 高屏（%d）默认半屏（snap=1，高度 %d ≈ 视口一半）、地图可见 %d%% ≥ 45%%' % (H, s['sh'], round((H - s['sh']) * 100 / H)), s['snap'] == 1 and abs(s['sh'] - H * .5) <= 3 and (H - s['sh']) >= H * .45, s)
            shot(pg, 'ov105_half.png')
            T.drag(200, 470, 200, 470 - 60, steps=10, dt=0.08, hold=0.15); pg.wait_for_timeout(700); s1 = state(pg)
            check('M3b 慢拖 60px 松手：吸附回最近一档（半屏 %d → %d）' % (s['sh'], s1['sh']), s1['snap'] == 1 and abs(s1['sh'] - s['sh']) <= 3, s1)
            T.drag(200, 470, 200, 150, steps=14, dt=0.08, hold=0.15); pg.wait_for_timeout(800); s2 = state(pg)
            check('M3c 慢拖到顶：吸附到拉满（snap=%d，高度 %d）' % (s2['snap'], s2['sh']), s2['snap'] == 2 and s2['sh'] > H * .8, s2)
            shot(pg, 'ov105_full.png')
            T.drag(200, 120, 200, 520, steps=14, dt=0.08, hold=0.15); pg.wait_for_timeout(800); s3 = state(pg)
            check('M3d 在标题条慢拖下来：回到半屏（snap=%d，高度 %d）' % (s3['snap'], s3['sh']), s3['snap'] == 1, s3)
            T.drag(200, 470, 200, 760, steps=12, dt=0.08, hold=0.15); pg.wait_for_timeout(800); s4 = state(pg)
            check('M3e 再往下拖：收起（snap=%d，高度 %d：只露标签条 + 一条）' % (s4['snap'], s4['sh']), s4['snap'] == 0 and s4['sh'] < 150, s4)
            shot(pg, 'ov105_collapsed.png')
            T.drag(200, 760, 200, 640, steps=3, dt=0.005); pg.wait_for_timeout(800); s5 = state(pg)
            check('M3f 快速上划（只划了 120px 但很快）：直接到下一档（snap %d → %d）' % (s4['snap'], s5['snap']), s5['snap'] >= 1, s5)
            # 拉满以后：列表自己滚；滚到顶继续下拉才收起
            T.drag(200, 560, 200, 150, steps=8, dt=0.012); pg.wait_for_timeout(800)
            if state(pg)['snap'] != 2: T.drag(200, 560, 200, 150, steps=8, dt=0.012); pg.wait_for_timeout(800)
            pg.evaluate("document.querySelector('.rm-body').scrollTop=300"); pg.wait_for_timeout(200)
            sc0 = pg.evaluate("document.querySelector('.rm-body').scrollTop")
            T.drag(200, 300, 200, 360, steps=8, dt=0.08, hold=0.1); pg.wait_for_timeout(600)
            st_ = state(pg); sc1 = pg.evaluate("document.querySelector('.rm-body').scrollTop")
            check('M3g 拉满、列表没滚到顶时下拉：列表往回滚（%d → %d），面板不动（snap=%d）' % (sc0, sc1, st_['snap']), st_['snap'] == 2 and sc1 < sc0, (sc0, sc1, st_))
            pg.evaluate("document.querySelector('.rm-body').scrollTop=0"); pg.wait_for_timeout(200)
            T.drag(200, 300, 200, 760, steps=14, dt=0.08, hold=0.1); pg.wait_for_timeout(900); st2 = state(pg)
            check('M3h 列表在顶部继续下拉：面板收下来（snap 2 → %d，高度 %d）' % (st2['snap'], st2['sh']), st2['snap'] < 2, st2)
            pg.evaluate("document.querySelector('.rm-body').scrollTop=0")
            T.drag(200, 500, 200, 100, steps=10, dt=0.08, hold=0.1); pg.wait_for_timeout(800)
            pg.evaluate("document.querySelector('.rm-body').scrollTop=250"); pg.wait_for_timeout(200)
            sc0 = pg.evaluate("document.querySelector('.rm-body').scrollTop")
            T.drag(200, 300, 200, 260, steps=6, dt=0.08, hold=0.1); pg.wait_for_timeout(500)
            sc1 = pg.evaluate("document.querySelector('.rm-body').scrollTop"); st3 = state(pg)
            check('M3i 拉满时上划：列表往下滚（%d → %d），面板仍是拉满（snap=%d）' % (sc0, sc1, st3['snap']), st3['snap'] == 2 and sc1 > sc0, (sc0, sc1, st3))
            # 同一次手势里接力：列表只滚了一点，一路下拉 → 先滚回顶、再接着把面板收下来
            pg.evaluate("document.querySelector('.rm-body').scrollTop=70"); pg.wait_for_timeout(200)
            T.drag(200, 300, 200, 780, steps=16, dt=0.08, hold=0.1); pg.wait_for_timeout(1000)
            st4 = state(pg); sc4 = pg.evaluate("document.querySelector('.rm-body').scrollTop")
            check('M3i2 拉满、列表只滚了 70px 时一路下拉（一次手势）：列表先滚回顶（%d），到顶以后继续下拉就把面板收下来（snap 2 → %d）' % (sc4, st4['snap']), sc4 == 0 and st4['snap'] < 2, (sc4, st4))
            c.close()
        with guard('M3b'):
            c, sb = mk(br, h=640); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)
            open_ov(pg, False); pg.wait_for_timeout(500); s = state(pg)
            check('M3j 矮屏（%d）默认收起（snap=%d），地图主体可见（%d%%）' % (s['vh'], s['snap'], round((s['vh'] - s['sh']) * 100 / s['vh'])), s['snap'] == 0 and (s['vh'] - s['sh']) >= s['vh'] * .75, s)
            c.close()
        with guard('M3c'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xb96a/', 900)
            open_ov(pg, False); pg.wait_for_timeout(500)
            pg.evaluate("ZRM.selectDay(59)"); pg.wait_for_timeout(900)
            o = pg.evaluate("""(function(){var t=document.querySelector('.rm-tabs'),on=document.querySelector('.rm-tb.on'),tr=t.getBoundingClientRect(),r=on.getBoundingClientRect(),cs=getComputedStyle(on),ink=getComputedStyle(document.documentElement).getPropertyValue('--ink').trim();
              var probe=document.createElement('i');probe.style.color=ink;document.body.appendChild(probe);var inkc=getComputedStyle(probe).color;probe.remove();
              return {txt:on.textContent,inView:r.left>=tr.left-1&&r.right<=tr.right+1,bg:cs.backgroundColor,ink:inkc,scrollable:t.scrollWidth>t.clientWidth+10,nOn:t.querySelectorAll('.rm-tb.on').length,tabs:t.querySelectorAll('.rm-tb').length}})()""")
            check('M3k 105 天：选第 60 天后标签 “%s” 整块反白（%s）、在标签条可视范围里、条可横向滑（%d 个标签）、只有一个选中' % (o['txt'], o['bg'] == o['ink'], o['tabs']), o['txt'] == '60' and o['bg'] == o['ink'] and o['inView'] and o['scrollable'] and o['nOn'] == 1 and o['tabs'] == 106, o)
            c.close()
        with guard('M3d'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 2); pg.wait_for_timeout(600)
            o = pg.evaluate("""(function(){var cs=function(s){var e=document.querySelector(s);return e?getComputedStyle(e):null},no=cs('.rm-hd .rm-no'),t=cs('.rm-hd b'),red=getComputedStyle(document.documentElement).getPropertyValue('--red').trim();
              var probe=document.createElement('i');probe.style.color=red;document.body.appendChild(probe);var redc=getComputedStyle(probe).color;probe.remove();
              var rows=[].slice.call(document.querySelectorAll('.rm-row[data-n]')),r0=rows[0];
              return {noFont:no.fontFamily,noColor:no.color,red:redc,noSize:parseFloat(no.fontSize),tFont:t.fontFamily,ld:(document.querySelector('.rm-ld')||{}).textContent||'',nrows:rows.length,
                idx:getComputedStyle(r0.querySelector('b')).fontFamily,idxColor:getComputedStyle(r0.querySelector('b')).color,name:r0.querySelector('strong').textContent,one:r0.querySelector('small').textContent,
                tags:[].map.call(document.querySelectorAll('.rm-row .rm-r em'),function(e){return e.textContent}),legs:[].map.call(document.querySelectorAll('.rm-row .rm-r i'),function(e){return e.textContent}),
                nav:(document.querySelector('.rm-navd')||{}).textContent,navBg:getComputedStyle(document.querySelector('.rm-navd')).backgroundColor,
                hasAdjText:/调整/.test(document.querySelector('.rm-body').textContent)}})()""")
            check('M3l 信息头：红色衬线大数字（%s %spx，%s）+ 衬线标题 + “今天：…”（%s）' % (o['noFont'][:20], o['noSize'], o['noColor'], o['ld'][:20]), 'Serif' in o['noFont'] and o['noColor'] == o['red'] and o['noSize'] >= 36 and 'Serif' in o['tFont'] and o['ld'].startswith('今天：'), o)
            check('M3m 站点行：红色衬线序号 + 名字（%s）+ 一句话（%s）+ 小标签 %s + 到下一站多久 %s' % (o['name'], o['one'][:20], o['tags'][:3], o['legs'][:2]), 'Serif' in o['idx'] and o['idxColor'] == o['red'] and bool(o['name']) and bool(o['one']) and '要预约' in o['tags'] and any(re.search(r'(步行|打车|开车|自驾)', x) for x in o['legs']) and not o['hasAdjText'], o)
            ink = pg.evaluate("(function(){var probe=document.createElement('i');probe.style.color=getComputedStyle(document.documentElement).getPropertyValue('--ink').trim();document.body.appendChild(probe);var c=getComputedStyle(probe).color;probe.remove();return c})()")
            btns = pg.evaluate("[].filter.call(document.querySelectorAll('.rm-sht button,.rm-sht a.btn'),function(b){var r=b.getBoundingClientRect(),y=getComputedStyle(b);return r.width>0&&r.height>0&&y.backgroundColor==='%s'&&b.closest('.rm-tabs')===null}).map(function(b){return b.textContent.trim()})" % ink)
            check('M3n 底部只有一个墨色方形主按钮“导航这一天”（%s）' % btns, btns == ['导航这一天 ›'] and o['navBg'] == ink, (btns, o['navBg'], ink))
            shot(pg, 'day2_half.png')
            c.close()

    # ─────────── M4 联动
    if want('M4'):
        with guard('M4a'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            pg.evaluate("window.scrollTo({top:1500,behavior:'instant'})"); pg.wait_for_timeout(300)
            open_day(pg, 1); pg.wait_for_timeout(1200)
            s0 = state(pg); names = pg.evaluate("ZRM.cur().days[ZRM.cur().sel].pts.map(function(p){return p.name})")
            mp = mark_px(pg, 2)
            T.tap(mp[0], mp[1]); pg.wait_for_timeout(1700); s1 = state(pg)
            cname = pg.evaluate("(document.querySelector('.rm-card[data-n=\"2\"] .rm-cname')||{}).textContent")
            pos = pg.evaluate("(function(){var z=ZRM.cur(),p=z.days[z.sel].pts[1],q=z.view.project(p.ll);return {x:q.x,y:q.y}})()")
            vis_b = 844 - s1['sh'] - 20; cy_ = 60 + (vis_b - 60) / 2; cx_ = 195 + (36 - 88) / 2
            check('M4a 点地图上第 2 站的方块：面板换成该站卡片（cur=%d，mode=%s，标题“%s”）' % (s1['cur'], s1['mode'], cname), s1['cur'] == 2 and s1['mode'] == 'card' and cname == names[1], (s1, cname))
            check('M4b 地图平滑飞到该站：落点在露出来的地图中央（偏 %.0f,%.0f px）、缩放 %.1f 在 12–15' % (pos['x'] - cx_, pos['y'] - cy_, s1['z']), abs(pos['x'] - cx_) < 45 and abs(pos['y'] - cy_) < 70 and 11.99 <= s1['z'] <= 15.01, (pos, cx_, cy_, s1['z']))
            check('M4c 联动期间页面不动（scrollY=%s，body.top %s → %s）' % (s1['sy'], s0['top'], s1['top']), s1['sy'] == 0 and s0['top'] == s1['top'] and s0['top'] < -100, (s0, s1))
            card = pg.evaluate("""(function(){var c=document.querySelector('.rm-card[data-n="2"]');return {name:c.querySelector('.rm-cname').textContent,one:(c.querySelector('.rm-c1')||{}).textContent||'',tags:[].map.call(c.querySelectorAll('.rm-c2 em'),function(e){return e.textContent}),legs:(c.querySelector('.rm-c3')||{}).textContent||'',go:c.querySelector('.rm-go').textContent,adj:c.querySelector('.rm-adj2').textContent,back:c.querySelector('.rm-cb').textContent}})()""")
            check('M4d 卡片内容：名字 / 一句话 / 小标签 / 距上一站·下一站的路程 / 导航到这里 / 调整这一站 / 全部站点（%s）' % card, bool(card['one']) and '上一站' in card['legs'] and '下一站' in card['legs'] and '直线' in card['legs'] and card['go'] == '导航到这里' and card['adj'] == '调整这一站' and card['back'] == '全部站点', card)
            shot(pg, 'card.png')
            T.drag(320, 740, 60, 740, steps=8, dt=0.012); pg.wait_for_timeout(1700); s2 = state(pg)
            pos3 = pg.evaluate("(function(){var z=ZRM.cur(),p=z.days[z.sel].pts[2],q=z.view.project(p.ll);return {x:q.x,y:q.y}})()")
            check('M4e 卡片向左滑：切到下一站（cur %d → %d），地图跟着飞（该站落点偏 %.0f,%.0f px）' % (s1['cur'], s2['cur'], pos3['x'] - cx_, pos3['y'] - cy_), s2['cur'] == 3 and abs(pos3['x'] - cx_) < 60 and abs(pos3['y'] - cy_) < 80, (s2, pos3))
            T.drag(60, 740, 330, 740, steps=8, dt=0.012); pg.wait_for_timeout(1500); s3 = state(pg)
            check('M4f 卡片向右滑：回到上一站（cur → %d）' % s3['cur'], s3['cur'] == 2, s3)
            # 点列表同理
            T.tap(80, 180); pg.wait_for_timeout(1000); s4 = state(pg)       # 点空白 → 回到列表
            check('M4g 点地图空白处：取消选中、面板回到列表（cur=%d，mode=%s，高度 %d = 进卡片前的半屏）' % (s4['cur'], s4['mode'], s4['sh']), s4['cur'] == 0 and s4['mode'] == 'list' and s4['snap'] == 1, s4)
            pg.click('.rm-row[data-n="3"]'); pg.wait_for_timeout(1700); s5 = state(pg)
            pos3 = pg.evaluate("(function(){var z=ZRM.cur(),p=z.days[z.sel].pts[2],q=z.view.project(p.ll);return {x:q.x,y:q.y}})()")
            check('M4h 点列表第 3 行：同样切到卡片、地图飞过去（cur=%d，偏 %.0f,%.0f px）' % (s5['cur'], pos3['x'] - cx_, pos3['y'] - cy_), s5['cur'] == 3 and s5['mode'] == 'card' and abs(pos3['x'] - cx_) < 45 and abs(pos3['y'] - cy_) < 70, (s5, pos3))
            # 关闭后页面滚到那一站
            pg.click('.rm-x'); pg.wait_for_timeout(900)
            r = pg.evaluate("""(function(){var rows=[].filter.call(document.querySelectorAll('#d1 .tl > .r[data-ll]'),function(r){return !r.hidden}),r=rows[2],b=r.getBoundingClientRect();return {top:b.top,ih:innerHeight,flash:r.classList.contains('flash'),sy:scrollY}})()""")
            check('M4i 关闭后页面滚到刚才选中的第 3 站那一行（离视口顶 %d px）并高亮（flash=%s）' % (r['top'], r['flash']), 0 <= r['top'] < r['ih'] - 40 and r['flash'], r)
            c.close()
        with guard('M4b'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 3); pg.wait_for_timeout(600)
            n0 = pg.evaluate("document.querySelectorAll('#d3 .tl > .r[data-ll]:not([hidden])').length")
            try: pg.wait_for_function("document.querySelectorAll('.rm-pts .rm-gy').length>0", timeout=9000)
            except Exception: pass
            ng = cur(pg, "document.querySelectorAll('.rm-pts .rm-gy').length")
            check('M4j 第 3 天有顺路候选：图上出现灰点（%s 个）' % ng, bool(ng), ng)
            if ng:
                gi = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='g'&&m.px>20&&m.px<370&&m.py>80&&m.py<380)return [m.px,m.py,m.gi]}return null})()")
                if not gi:
                    pg.evaluate("ZRM.cur().view.zoomBy(-2)"); pg.wait_for_timeout(800)
                    gi = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='g'&&m.px>20&&m.px<370&&m.py>80&&m.py<380)return [m.px,m.py,m.gi]}return null})()")
                if gi:
                    T.tap(gi[0], gi[1]); pg.wait_for_timeout(1200)
                    gc = pg.evaluate("(function(){var c=document.querySelector('.rm-gcard');return c?c.innerText:''})()")
                    check('M4k 点灰点：卡片写名字、“+N 分钟”、有“加到这天”（%s）' % gc.replace('\n', ' ')[:60], bool(re.search(r'\+\d+ 分钟', gc)) and pg.evaluate("!!document.querySelector('.rm-go[data-act=\"addg\"]')"), gc)
                    shot(pg, 'gray_card.png')
                    pg.click('.rm-go[data-act="addg"]'); pg.wait_for_timeout(900)
                    n1 = pg.evaluate("document.querySelectorAll('#d3 .tl > .r[data-ll]:not([hidden])').length")
                    check('M4l 加到这天：页面多一行（%d → %d），图的列表同步（%d 行）' % (n0, n1, pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length")), n1 == n0 + 1 and pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length") == n1, (n0, n1))
                    pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(800)
                    n2 = pg.evaluate("document.querySelectorAll('#d3 .tl > .r[data-ll]:not([hidden])').length")
                    check('M4m 撤销：回到 %d 行（图 %d 行）' % (n0, pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length")), n2 == n0 and pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length") == n0, (n0, n2))
                else: check('M4k 灰点在视野里（没找到可点的灰点）', False, ng)
            c.close()
        with guard('M4c'):
            # 改行程后图重画：调整这一站 → 去掉 → 撤销
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 1); pg.wait_for_timeout(700)
            n0 = pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length")
            pg.click('.rm-row[data-n="2"]'); pg.wait_for_timeout(1200)
            pg.click('.rm-adj2'); pg.wait_for_selector('.pk [data-x]');
            t = pg.evaluate("document.querySelector('.pk .pk-h b').textContent")
            pg.click('.pk [data-x]'); pg.wait_for_timeout(900)
            n1 = pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length"); m1 = cur(pg, "r.marks.filter(function(m){return m.kind==='n'}).length")
            check('M4n 卡片“调整这一站”打开原来的调整层（标题“%s”）；去掉一站后图的列表 / 标记同步重画（%d → 列表 %d、标记 %d）' % (t, n0, n1, m1), t == '改这一站' and n1 == n0 - 1 and m1 == n1, (t, n0, n1, m1))
            pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(900)
            check('M4o 撤销：列表回到 %d' % n0, pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length") == n0, pg.evaluate("document.querySelectorAll('.rm-row[data-n]').length"))
            c.close()

    # ─────────── M5 控件
    if want('M5'):
        with guard('M5a'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 2); pg.wait_for_timeout(800)
            bad = []
            def grab_y(): return pg.evaluate("(function(){var r=document.querySelector('.rm-grab').getBoundingClientRect();return r.top+r.height/2})()")
            for snap_, label in ((1, '半屏'), (0, '收起'), (2, '拉满')):
                if snap_ == 0: g0 = grab_y(); T.drag(200, g0, 200, g0 + 420, steps=12, dt=0.08, hold=0.12)
                if snap_ == 2: g0 = grab_y(); T.drag(200, g0, 200, 60, steps=14, dt=0.08, hold=0.12)
                pg.wait_for_timeout(900); st = state(pg)
                if st['snap'] != snap_: bad.append((label, '没到这一档', st['snap']))
                for sel in ('.rm-x', '.rm-sv', '.rm-rs', '.rm-zi', '.rm-zo', '.rm-ai'):
                    h = hit(pg, sel)
                    if snap_ == 2 and sel in ('.rm-rs', '.rm-zi', '.rm-zo', '.rm-ai'):
                        if h and h['vis'] != 'hidden': bad.append((label, sel, '拉满时应让开', h))
                        continue
                    if not h or h['w'] < 43.9 or h['h'] < 43.9 or not h['ok'] or h['l'] < 0 or h['t'] < 0 or h['r'] > 390.5 or h['b'] > 844.5: bad.append((label, sel, h))
                sht = pg.evaluate("document.querySelector('.rm-sht').getBoundingClientRect().top")
                for sel in ('.rm-rs', '.rm-zi', '.rm-zo', '.rm-ai'):
                    h = hit(pg, sel)
                    if h and h['vis'] != 'hidden' and h['b'] > sht + 1: bad.append((label, sel, '盖在面板里', h['b'], sht))
                if snap_ == 2: shot(pg, 'controls_full.png')
                if snap_ == 0: shot(pg, 'controls_collapsed.png')
            check('M5a 三档里 × / 存图 / 回到视野 / + / − / i 都 ≥44×44、在视口内、没被盖住（elementFromPoint 命中自己）；拉满时右侧控件让开（没有盖进面板）', not bad, bad[:4])
            # 回到半屏再测底部没有固定栏
            g0 = grab_y(); T.drag(200, g0, 200, g0 + 360, steps=14, dt=0.08, hold=0.12); pg.wait_for_timeout(900)
            fx = pg.evaluate("""(function(){var out=[];[].forEach.call(document.querySelectorAll('body *'),function(e){var cs=getComputedStyle(e);if(cs.position==='fixed'&&cs.display!=='none'&&cs.visibility!=='hidden'){var r=e.getBoundingClientRect();if(r.width>0&&r.height>0)out.push(e.className.toString().slice(0,30)+'|'+Math.round(r.top)+'-'+Math.round(r.bottom))}});
              var dock=document.querySelector('.dock');return {fixed:out,dock:dock?getComputedStyle(dock).display:'none'}})()""")
            check('M5b 底部没有任何固定栏：.dock 隐藏（%s），整屏期间可见的 fixed 元素只有地图层本身（%s）' % (fx['dock'], fx['fixed']), fx['dock'] == 'none' and all(x.startswith('rm rm-fs') for x in fx['fixed']), fx)
            css = open(os.path.join(env.site, 'assets', 'site.css'), encoding='utf-8').read()
            check('M5c 所有贴边的控件 / 面板都用 env(safe-area-inset-*)（× / 存图 / 进度 / 提示条用 top，面板用 bottom）', css.count('env(safe-area-inset-top') >= 5 and '.rm .rm-sht{' in css and 'padding-bottom:env(safe-area-inset-bottom' in css.split('.rm .rm-sht{')[1].split('}')[0], css.count('env(safe-area-inset-top'))
            # 署名
            at = pg.evaluate("(function(){var x=document.querySelector('.rm-atx'),i=document.querySelector('.rm-ai').getBoundingClientRect(),sht=document.querySelector('.rm-sht').getBoundingClientRect();return {hidden:x.hidden,w:i.width,h:i.height,r:i.right,b:i.bottom,sht:sht.top}})()")
            check('M5d 署名默认收起：只有右下一个 44×44 的 i（贴着面板上沿：i 底 %.0f、面板顶 %.0f）' % (at['b'], at['sht']), at['hidden'] and at['w'] == 44 and at['h'] == 44 and at['r'] >= 380 and 0 <= at['sht'] - at['b'] <= 12, at)
            pg.click('.rm-ai'); pg.wait_for_timeout(200)
            tx = pg.evaluate("(document.querySelector('.rm-atx')||{}).innerText||''")
            vis = pg.evaluate("(function(){var x=document.querySelector('.rm-atx');return !x.hidden&&x.getBoundingClientRect().height>=44})()")
            check('M5e 点 i：展开一行小字（含 OpenFreeMap / OpenStreetMap，带 ×）（%s）' % tx.replace('\n', ' ')[:50], vis and 'OpenFreeMap' in tx and 'OpenStreetMap' in tx and pg.evaluate("!!document.querySelector('.rm-ax')"), tx)
            shot(pg, 'attr_open.png')
            pg.click('.rm-ax'); pg.wait_for_timeout(150)
            check('M5f 点 ×：署名又收起', pg.evaluate("document.querySelector('.rm-atx').hidden"))
            # 回到视野：拖开后点
            s0 = state(pg); T.drag(250, 300, 120, 200); pg.wait_for_timeout(600); s1 = state(pg)
            pg.click('.rm-rs'); pg.wait_for_timeout(900); s2 = state(pg)
            d1 = abs(s1['lng'] - s0['lng']) + abs(s1['lat'] - s0['lat']); d2 = abs(s2['lng'] - s0['lng']) + abs(s2['lat'] - s0['lat'])
            check('M5g 拖开以后点“回到视野”：回到当天取景（偏离 %.4f → %.4f）' % (d1, d2), d1 > .01 and d2 < d1 * .3, (d1, d2))
            for _ in range(14):
                if pg.is_disabled('.rm-zi'): break
                pg.click('.rm-zi'); pg.wait_for_timeout(260)
            pg.wait_for_timeout(400); zmax = state(pg)['z']
            pg.evaluate("document.querySelector('.rm-zi').disabled=false"); pg.click('.rm-zi'); pg.wait_for_timeout(450)
            check('M5h 放大到头（%.2f）+ 置灰，再点不再放大（%.2f）' % (zmax, state(pg)['z']), zmax <= 17.01 and state(pg)['z'] - zmax < .05, (zmax, state(pg)['z']))
            c.close()
        with guard('M5b'):
            # 旋转打开时：指北针出现，点一下转回正北
            c, sb = mk(br, storage={'zouni_map_rot': '1'}); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_ov(pg); pg.wait_for_timeout(500)
            cx, cy = 195, 240
            T._send('touchStart', [(cx - 60, cy), (cx + 60, cy)])
            for i in range(1, 13):
                a = math.radians(50 * i / 12); T._send('touchMove', [(cx - 60 * math.cos(a), cy - 60 * math.sin(a)), (cx + 60 * math.cos(a), cy + 60 * math.sin(a))]); time.sleep(.016)
            T._send('touchEnd', []); pg.wait_for_timeout(500)
            b1 = state(pg)['bearing']; vis = pg.evaluate("!document.querySelector('.rm-cp').hidden")
            check('M5i 打开旋转后：双指旋转出现方位角（%.1f°），指北针按钮出现' % b1, abs(b1) > 10 and vis, (b1, vis))
            if vis:
                pg.click('.rm-cp'); pg.wait_for_timeout(700)
                check('M5j 点指北针：转回正北（%.1f°）、按钮收起' % state(pg)['bearing'], abs(state(pg)['bearing']) < .5 and pg.evaluate("document.querySelector('.rm-cp').hidden"), state(pg)['bearing'])
            c.close()

    # ─────────── M6 加载体验
    if want('M6'):
        with guard('M6a'):
            env.delays['assets/routemap.js'] = 2.5; env.delays['assets/maplibre/maplibre-gl.js'] = 3.5
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            pg.evaluate("(function(){var c=document.createElement('canvas');c.width=c.height=256;var x=c.getContext('2d');x.fillRect(0,0,99,99);c.style.cssText='position:fixed;left:0;top:0';document.body.appendChild(c);setTimeout(function(){c.remove()},100)})()"); pg.wait_for_timeout(800)      # 先让这个渲染进程把 canvas / 光栅化的第一次初始化做掉（软件渲染下第一次要几百毫秒，真机 ~10ms；它不是“点开”的成本）
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(200)
            pg.evaluate("window.__t0=performance.now();window.__seen=null;(function f(){var r=document.querySelector('.rm');if(r&&r.getBoundingClientRect().height>=150&&document.querySelector('.rm .rm-bsvg')&&document.querySelector('.rm .rm-sht')){window.__seen=performance.now()-window.__t0}else requestAnimationFrame(f)})();document.querySelector('.mapgo').click()")
            pg.wait_for_function("window.__seen!==null", timeout=3000)
            seen = pg.evaluate("window.__seen")
            o = pg.evaluate("""(function(){var r=document.querySelector('.rm');return {boot:r.classList.contains('rm-boot'),lines:document.querySelectorAll('.rm-bl').length,marks:document.querySelectorAll('.rm-bm').length,tabs:document.querySelectorAll('.rm-tb').length,load:(document.querySelector('.rm-load')||{}).textContent||'',x:document.querySelector('.rm-x').getBoundingClientRect().width,sh:document.querySelector('.rm-sht').getBoundingClientRect().height,pw:document.querySelector('.rm-prog i').style.width,ml:!!window.maplibregl,zrm:!!window.ZRM}})()""")
            shot(pg, 'boot.png')
            check('M6a 点开 %.0fms 内（网络一个字节都没回）就有示意图 + 线路（%d 条线、%d 个方块）+ 半屏面板框（%d 个标签、高 %dpx）+ “×”（%dpx）+ 加载提示“%s”' % (seen, o['lines'], o['marks'], o['tabs'], o['sh'], o['x'], o['load']), seen <= 300 and o['boot'] and o['lines'] >= 1 and o['marks'] >= 1 and o['tabs'] == 4 and o['sh'] > 300 and o['x'] >= 44 and '街道地图加载中' in o['load'] and not o['zrm'], (seen, o))
            pg.wait_for_function("window.ZRM&&ZRM.cur()&&!document.querySelector('.rm-boot')", timeout=8000); pg.wait_for_timeout(150)
            o2 = pg.evaluate("({boot:!!document.querySelector('.rm-boot'),rows:document.querySelectorAll('.rm-row').length,load:!document.querySelector('.rm-load').hidden,pw:document.querySelector('.rm-prog i').style.width,ml:!!window.maplibregl})")
            check('M6b routemap.js 到了以后无缝接手：起步壳被换掉、列表出现（%d 行）、仍有“加载中”和进度条（%s）' % (o2['rows'], o2['pw']), not o2['boot'] and o2['rows'] >= 3 and o2['load'] and o2['pw'] not in ('', '0%'), o2)
            pg.wait_for_function("ZRM.cur().tiles>0", timeout=12000); pg.wait_for_timeout(900)
            o3 = pg.evaluate("({in_:document.querySelector('.rm-map').classList.contains('rm-in'),load:document.querySelector('.rm-load').hidden,note:document.querySelector('.rm-note').hidden,failed:ZRM.cur().failed})")
            check('M6c 街道底图到了：淡入覆盖示意图（rm-in）、加载提示收起、没有失败提示', o3['in_'] and o3['load'] and o3['note'] and not o3['failed'], o3)
            env.delays.clear(); c.close()
        with guard('M6b'):
            c, sb = mk(br, mode='tiles'); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            t0 = time.time(); pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg)
            pg.wait_for_function("ZRM.cur().failed", timeout=14000); dt = time.time() - t0
            o = pg.evaluate("""(function(){var n=document.querySelector('.rm-note'),b=document.querySelector('.rm-rt'),r=b.getBoundingClientRect();return {why:ZRM.cur().why,note:n.querySelector('span').textContent,vis:!n.hidden,bw:r.width,bh:r.height,kind:ZRM.cur().view.kind,lines:document.querySelectorAll('.rm-pts .rm-mk').length,txt:b.textContent}})()""")
            check('M6d 瓦片全失败：%.1f 秒内退回示意图（why=%s），提示“%s”，重试按钮 %dx%d' % (dt, o['why'], o['note'], o['bw'], o['bh']), dt < 12 and o['why'] == 'tiles' and o['note'] == '街道地图加载失败，已改用示意图' and o['vis'] and o['bh'] >= 44 and o['kind'] == 'sch' and o['txt'] == '重试', (dt, o))
            shot(pg, 'failed.png')
            # 示意图版也能拖、缩放、点站点
            T = Touch(c, pg); s0 = state(pg)
            T.drag(250, 300, 150, 260); pg.wait_for_timeout(300); s1 = state(pg)
            T.pinch(190, 260, 60, 180); pg.wait_for_timeout(300); s2 = state(pg)
            check('M6e 示意图版：单指能拖（中心 %.4f→%.4f）、双指能缩放（%.2f→%.2f）' % (s0['lng'], s1['lng'], s1['z'], s2['z']), abs(s1['lng'] - s0['lng']) > 1e-4 and s2['z'] > s1['z'] + .5, (s0, s1, s2))
            mk0 = pg.evaluate("ZRM.cur().marks.filter(function(k){return k.kind==='n'||k.kind==='day'}).map(function(k){return [Math.round(k.px),Math.round(k.py)]})")
            g0 = pg.evaluate("document.querySelector('.rm-grab').getBoundingClientRect().top+10"); T.drag(200, g0, 200, g0 + 40, steps=6, dt=0.08, hold=0.1); pg.wait_for_timeout(900)
            mk1 = pg.evaluate("ZRM.cur().marks.filter(function(k){return k.kind==='n'||k.kind==='day'}).map(function(k){return [Math.round(k.px),Math.round(k.py)]})"); gm = pg.evaluate("ZRM.cur().mb")
            dm = max([abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(mk0, mk1)] or [999]) if len(mk0) == len(mk1) else 999
            check('M6n 示意图版里一拖面板：容器长到整屏（mb=%s）、示意图摄像机跟着补偿，方块没跳（最大位移 %d px ≤ 8）' % (gm, dm), gm == 0 and dm <= 8, (mk0, mk1, gm))
            sb.mode = 'ok'; pg.click('.rm-rt'); pg.wait_for_timeout(400)
            st = state(pg)
            check('M6f 点“重试”：失败提示立刻收起、重新加载（failed=%s）' % st['failed'], not st['failed'] and pg.evaluate("document.querySelector('.rm-note').hidden"), st)
            try: tiles(pg, 12000)
            except Exception: pass
            check('M6g 重试后瓦片到了、回到街道底图（kind=%s，tiles=%s）' % (state(pg)['kind'], state(pg)['tiles']), state(pg)['kind'] == 'ml' and state(pg)['tiles'] > 0 and not state(pg)['failed'], state(pg))
            c.close()
        with guard('M6e'):
            # 地图容器刚开时只到面板上沿（半屏时瓦片 6 → 4 块，慢网省一半字节）；一往下拖面板就长到整屏，内容不跳
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 1); pg.wait_for_timeout(1500)
            r0 = pg.evaluate("(function(){var m=document.querySelector('.rm-map').getBoundingClientRect(),z=ZRM.cur();return {h:m.height,top:m.top,mb:z.mb,sh:z.sheetH,vh:z.vh,mk:z.marks.filter(function(k){return k.kind==='n'}).map(function(k){return [Math.round(k.px),Math.round(k.py)]})}})()")
            nt0 = sb.n['pbf']
            check('M6l 刚打开：地图容器高 %d = 视口 %d − 面板 %d（只到面板上沿；半屏取到 %d 块瓦片，整屏要 6 块）' % (r0['h'], r0['vh'], r0['sh'], nt0), abs(r0['h'] - (r0['vh'] - r0['sh'])) <= 2 and r0['top'] == 0 and nt0 <= 5, (r0, nt0))
            g0 = pg.evaluate("document.querySelector('.rm-grab').getBoundingClientRect().top+10")
            T.drag(200, g0, 200, g0 + 40, steps=6, dt=0.08, hold=0.1); pg.wait_for_timeout(1000)
            r1 = pg.evaluate("(function(){var m=document.querySelector('.rm-map').getBoundingClientRect(),z=ZRM.cur();return {h:m.height,mb:z.mb,mk:z.marks.filter(function(k){return k.kind==='n'}).map(function(k){return [Math.round(k.px),Math.round(k.py)]})}})()")
            dm = max(abs(a[0] - b[0]) + abs(a[1] - b[1]) for a, b in zip(r0['mk'], r1['mk'])) if r0['mk'] and len(r0['mk']) == len(r1['mk']) else 999
            check('M6m 一拖面板：地图容器长到整屏（%d），方块没跳（最大位移 %d px ≤ 8）' % (r1['h'], dm), r1['h'] >= r0['vh'] - 2 and r1['mb'] == 0 and dm <= 8, (r0['mk'], r1['mk']))
            c.close()
        with guard('M6c'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            c.route(re.compile(r'.*/assets/map/style\.json.*'), lambda r: r.abort())
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg)
            pg.wait_for_function("ZRM.cur().failed", timeout=14000)
            check('M6h 样式取不到：退示意图（why=%s）并提示' % state(pg)['why'], state(pg)['why'] == 'style' and not pg.evaluate("document.querySelector('.rm-note').hidden"), state(pg))
            c.close()
        with guard('M6d'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            open_ov(pg); pg.click('.rm-x'); pg.wait_for_timeout(500)
            c.set_offline(True); pg.wait_for_timeout(200)
            t0 = time.time(); pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg)
            pg.wait_for_function("ZRM.cur().failed", timeout=5000); dt = time.time() - t0
            o = pg.evaluate("({why:ZRM.cur().why,note:document.querySelector('.rm-note span').textContent,lines:document.querySelectorAll('.rm-pts .rm-mk').length,load:document.querySelector('.rm-load').hidden,nav:document.querySelector('.rm-navd').hidden})")
            check('M6i 断网：直接示意图（%.1f 秒）、提示“%s”、没有“加载中”' % (dt, o['note']), o['why'] == 'offline' and '没有网络' in o['note'] and dt < 3 and o['load'], (dt, o))
            pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(500)
            navs = pg.evaluate("(function(){var b=document.querySelector('.rm-navd');return {txt:b.textContent,off:b.classList.contains('off')}})()")
            pg.click('.rm-navd', force=True); pg.wait_for_timeout(300)
            check('M6j 断网时地图里的“导航这一天”置灰写“没网，暂时不能导航”（%s），点它不弹分段层' % navs['txt'], navs['off'] and '没网' in navs['txt'] and not pg.evaluate("!!document.querySelector('.rm-sheet.rm-dyn')"), navs)
            c.set_offline(False); pg.evaluate("window.dispatchEvent(new Event('online'))"); pg.wait_for_timeout(300)
            try: tiles(pg, 12000)
            except Exception: pass
            check('M6k 联网后自动重试：回到街道底图（kind=%s）' % state(pg)['kind'], state(pg)['kind'] == 'ml' and not state(pg)['failed'], state(pg))
            c.close()

    # ─────────── M7 点开前零请求；空闲预取的条件
    if want('M7'):
        with guard('M7a'):
            c, sb = mk(br); pg = new_page(env, c); reqs = []
            pg.on('request', lambda r: reqs.append(r.url))
            goto(env, pg, '/trip/xa3/', 900)
            pre = [u for u in reqs if re.search(r'maplibre|routemap|openfreemap|/assets/map/', u)]
            check('M7a 打开行程页后 0.9 秒：没有请求 maplibre / routemap / 样式 / openfreemap（点开前零请求）', not pre, pre[:3])
            n0 = len(reqs); open_ov(pg)
            post = [u for u in reqs[n0:] if re.search(r'maplibre|routemap|/assets/map/style', u)]
            check('M7b 点开后才取 routemap.js / maplibre js + css / 样式（%d 个）' % len(post), any('routemap.js' in u for u in post) and any('maplibre-gl.js' in u for u in post) and any('maplibre-gl.css' in u for u in post) and any('map/style.json' in u for u in post), post[:6])
            c.close()
        with guard('M7c'):
            env.delays['assets/maplibre/maplibre-gl.js'] = 2.5
            c, sb = mk(br); pg = new_page(env, c); reqs = []
            pg.on('request', lambda r: reqs.append(r.url)); goto(env, pg, '/trip/xa3/', 600); n0 = len(reqs)
            pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.evaluate("document.querySelector('.mapgo').click()"); pg.wait_for_timeout(1000)
            got = [u for u in reqs[n0:]]
            check('M7c 点开的同一刻就并行发出样式 / sprite / 字形 / 瓦片索引 / 瓦片（地图脚本 2.5 秒才到，1 秒时这些已经发出：sprite %s、字形 %s、瓦片索引 %d、瓦片 %d；脚本还没到 %s）' % (any('sprite/ofm' in u for u in got), any('/fonts/Noto' in u for u in got), sb.n['tilejson'], sb.n['pbf'], not pg.evaluate("!!window.maplibregl")), any('sprite/ofm' in u for u in got) and any('/fonts/Noto' in u for u in got) and any('map/style.json' in u for u in got) and sb.n['tilejson'] >= 1 and sb.n['pbf'] >= 1 and not pg.evaluate("!!window.maplibregl"), (len(got), sb.n))
            env.delays.clear(); c.close()
        def idle_case(tag, init_js, want_big, want_small, wait=8500):
            c, sb = mk(br)
            if init_js: c.add_init_script(init_js)
            pg = new_page(env, c); reqs = []
            pg.on('request', lambda r: reqs.append(r.url))
            goto(env, pg, '/trip/xa3/', 300); pg.wait_for_timeout(wait)
            small = [u for u in reqs if 'routemap.js' in u]; big = [u for u in reqs if re.search(r'maplibre-gl\.(js|css)|map/style\.json', u)]
            pre = pg.evaluate("[].map.call(document.querySelectorAll('link[rel=preconnect]'),function(l){return l.href})")
            check('M7%s 空闲预取（%s）：routemap.js %s、maplibre+样式 %s（实际 %d / %d 个请求）' % (tag[0], tag[1], '会取' if want_small else '不取', '会取' if want_big else '不取', len(small), len(big)), bool(small) == want_small and bool(big) == want_big, (small[:2], big[:2]))
            c.close()
        with guard('M7d'):
            idle_case(('d', '4g 且没开省流量'), "Object.defineProperty(navigator,'connection',{value:{effectiveType:'4g',saveData:false,type:'wifi'},configurable:true});", True, True)
        with guard('M7e'):
            idle_case(('e', '开了省流量'), "Object.defineProperty(navigator,'connection',{value:{effectiveType:'4g',saveData:true},configurable:true});", False, False)
        with guard('M7f'):
            idle_case(('f', '3g'), "Object.defineProperty(navigator,'connection',{value:{effectiveType:'3g',saveData:false},configurable:true});", False, False)
        with guard('M7g'):
            idle_case(('g', '不报网络类型（iOS Safari 就是这样）：只取小的 routemap.js'), "Object.defineProperty(navigator,'connection',{value:undefined,configurable:true});", False, True)

    # ─────────── M8 长线（105 天）重画耗时 + 帧率采样（用真 GPU：Apple Metal；没有真 GPU 的机器退回软件渲染，只记录、不判 fps）
    if want('M8'):
        with guard('M8'):
            gpu_args = ['--use-gl=angle', '--use-angle=metal', '--ignore-gpu-blocklist', '--enable-gpu']
            try: brg = p.chromium.launch(args=gpu_args)
            except Exception: brg = None
            real = False
            if brg:
                tp = brg.new_page(); tp.goto('about:blank')
                rend = tp.evaluate("(function(){var c=document.createElement('canvas'),g=c.getContext('webgl');if(!g)return 'nogl';var e=g.getExtension('WEBGL_debug_renderer_info');return e?g.getParameter(e.UNMASKED_RENDERER_WEBGL):'?'})()"); tp.close()
                real = 'swiftshader' not in rend.lower() and rend != 'nogl'
            if not real:
                if brg: brg.close()
                brg = br; rend = '软件渲染'
            c, sb = mk(brg); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xb96a/', 1200)
            open_ov(pg); pg.wait_for_timeout(1200)
            pg.evaluate("""window.__fr=0;window.__on=true;(function f(){if(window.__on){window.__fr++;requestAnimationFrame(f)}})();ZRM.cur().pf={n:0,ms:0,max:0}""")
            t0 = time.time()
            for i in range(2):
                T.drag(300, 300, 90, 360, steps=30, dt=0.016); T.drag(90, 360, 300, 300, steps=30, dt=0.016)
                T.pinch(195, 300, 60, 240, steps=24, dt=0.016); T.pinch(195, 300, 240, 60, steps=24, dt=0.016)
            dt = time.time() - t0; fr = pg.evaluate("window.__on=false;window.__fr"); pf = pg.evaluate("ZRM.cur().pf")
            avg = pf['ms'] / max(1, pf['n']); fps = fr / dt
            nmk = pg.evaluate("ZRM.cur().marks.length")
            env.note('105 天总览拖动 / 缩放（%s）：采样 %.1f 秒、%d 帧（%.0f fps）；叠层重画 %d 次，平均 %.2f ms、最长 %.1f ms；DOM 标记 %d 个' % (rend[:50], dt, fr, fps, pf['n'], avg, pf['max'], nmk))
            check('M8a 105 天总览：线和点画在一张 canvas 上，DOM 标记只有天数章（%d 个 ≤ 120），每次重画平均 %.2f ms ≤ 6ms（60fps 的预算 16ms，叠层不能吃掉一半）' % (nmk, avg), nmk <= 120 and avg <= 6.0 and pf['n'] > 60, (nmk, avg, pf))
            check('M8b 拖动 / 缩放帧率 %.0f fps（%s）：真 GPU 上 ≥50；软件渲染下只要求叠层最长一次重画 %.1f ms < 40' % (fps, rend[:30], pf['max']), (fps >= 50 if real else pf['max'] < 40), (fps, rend, pf))
            c.close()
            if real: brg.close()

    # ─────────── M9 暗色
    if want('M9'):
        with guard('M9'):
            c, sb = mk(br, dark=True); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 2); pg.wait_for_timeout(900)
            o = pg.evaluate("""(function(){var f=getComputedStyle(document.querySelector('.rm-map canvas')).filter,z=ZRM.cur(),sht=getComputedStyle(document.querySelector('.rm-sht')),b=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();
              var probe=document.createElement('i');probe.style.color=b;document.body.appendChild(probe);var bg=getComputedStyle(probe).color;probe.remove();
              return {filter:f,pal:z.pal[0],shbg:sht.backgroundColor,bg:bg,ow:document.documentElement.scrollWidth,iw:innerWidth,mk:getComputedStyle(document.querySelector('.rm-mk i')).backgroundColor}})()""")
            check('M9a 暗色：底图滤镜反色（%s）、色板换成暗色版（%s，不是亮色的 #a63d27）、面板底色是暗色（%s）、不溢出（%d≤%d）' % (o['filter'][:30], o['pal'], o['shbg'], o['ow'], o['iw']), 'invert' in o['filter'] and o['pal'].lower() != '#a63d27' and o['shbg'] == o['bg'] and o['ow'] <= o['iw'], o)
            shot(pg, 'dark_day.png')
            c.close()

    # ─────────── M10 存图 · 导航
    if want('M10'):
        with guard('M10a'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 2); pg.wait_for_timeout(1500)
            pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=8000); pg.wait_for_timeout(400)
            info = pg.evaluate("""(function(){var im=document.querySelector('.rm-shot img');return new Promise(function(res){var i=new Image();i.onload=function(){var c=document.createElement('canvas');c.width=i.width;c.height=i.height;var x=c.getContext('2d');x.drawImage(i,0,0);var d=x.getImageData(0,0,i.width,i.height).data,seen={},n=0;for(var k=0;k<d.length;k+=4*997){var key=d[k]+','+d[k+1]+','+d[k+2];if(!seen[key]){seen[key]=1;n++}}res({w:i.width,h:i.height,colors:n,title:document.querySelector('.rm-shot .shotp').textContent.slice(0,40)})};i.src=im.src})})()""")
            check('M10a 存图：1080 宽、不是空白（%d 种颜色）、高 %d' % (info['colors'], info['h']), info['w'] == 1080 and info['colors'] > 8 and info['h'] > 800, info)
            shot(pg, 'save_img.png')
            pg.click('.rm-shot .hz-x'); pg.wait_for_timeout(300)
            check('M10b 关掉存图层后地图还在、层栈只剩 [map]（2026-10-18 层栈：不再靠“地图 × 暂时摘掉 / 恢复 pk-x”）', pg.evaluate("!!document.querySelector('.rm')&&ZL.kinds().join()==='map'&&!document.querySelector('.rm-x').classList.contains('pk-x')"))
            c.close()
        with guard('M10b'):
            c, sb = mk(br)
            hits = []
            c.route(re.compile(r'https://(uri\.amap\.com|www\.google\.com/maps)/.*'), lambda r: (hits.append(r.request.url), r.fulfill(status=204, body=''))[1])
            pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            open_day(pg, 1); pg.wait_for_timeout(600)
            segs = pg.evaluate("ZRM.segs(document.getElementById('d1'))")
            rows = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('#d1 .tl > .r[data-ll]:not([hidden])'),function(r){return r.getAttribute('data-ll')})")
            sp = pg.evaluate("document.getElementById('d1').getAttribute('data-sp')"); ep = pg.evaluate("document.getElementById('d1').getAttribute('data-ep')")
            want_ = [sp] + rows + [ep]; npts = len(want_)
            from urllib.parse import urlparse, parse_qs
            parsed = []
            for u in segs:
                q = parse_qs(urlparse(u).query); parsed.append(([x for x in q['from'][0].split(',')[:2]], [x.split(',')[:2] for x in q.get('via', [])], [x for x in q['to'][0].split(',')[:2]]))
            check('M10c 国内（高德）第 1 天：%d 个点 → %d 段，每段 ≤1 个途经点，相邻段首尾相接' % (npts, len(segs)), len(segs) == math.ceil((npts - 1) / 2) and len(segs) >= 2 and all(len(v) <= 1 for _, v, _ in parsed) and all(parsed[i][2] == parsed[i + 1][0] for i in range(len(parsed) - 1)), (npts, len(segs)))
            seq = []
            for f, v, t in parsed:
                if not seq: seq.append(f)
                seq += v + [t]
            bad = []
            for (lng, lat), w in zip(seq, want_):
                wl = [float(x) for x in w.split(',')]; g = gcj(wl[0], wl[1])
                if abs(float(lat) - g[0]) > 2e-6 or abs(float(lng) - g[1]) > 2e-6: bad.append((w, lat, lng, g))
            check('M10d 国内坐标是 GCJ-02（和独立算的一致，全部 %d 个点）、和 WGS84 不同、是高德导航链接' % npts, len(seq) == npts and not bad and all('uri.amap.com/navigation' in u and 'mode=car' in u and 'callnative=1' in u for u in segs) and all(abs(float(lat) - float(w.split(',')[0])) > 0.0008 for (lng, lat), w in zip(seq, want_)), bad[:2] or (len(seq), npts))
            # 地图里的“导航这一天”
            pg.wait_for_selector('.rm-navd:not([hidden])'); pg.click('.rm-navd'); pg.wait_for_selector('.rm-sheet.rm-dyn'); pg.wait_for_timeout(300)
            links = pg.evaluate("Array.prototype.map.call(document.querySelectorAll('.rm-sheet a.rm-seg'),function(a){return a.getAttribute('href')})")
            note = pg.inner_text('.rm-sheet .xnote'); shot(pg, 'nav_sheet.png')
            segbtn = pg.evaluate("(function(){var a=document.querySelector('.rm-sheet a.rm-seg'),r=a.getBoundingClientRect(),cs=getComputedStyle(a);return {h:r.height,bw:cs.borderTopWidth,txt:a.textContent,x:document.querySelector('.rm-x').classList.contains('pk-x')}})()")
            check('M10e 地图里点“导航这一天”：分段层（整屏界面之上）列出 %d 段、链接和 ZRM.segs 一致、写清“分 N 段 … 按顺序点”（%s）' % (len(links), note[:30]), links == segs and '按顺序点' in note and ('分 %d 段' % len(segs)) in note, (len(links), len(segs), note))
            check('M10f 分段是方形按钮（高 %d≥56、有边框 %s、写明“用高德打开”）、起点不叫“出发地”；分段层打开时返回键先关它（地图 × 没有 pk-x 的临时替换：%s）' % (segbtn['h'], segbtn['bw'], not segbtn['x']), segbtn['h'] >= 55 and segbtn['bw'] != '0px' and '用高德打开' in segbtn['txt'] and '出发地' not in segbtn['txt'] and not segbtn['x'], segbtn)
            hits.clear(); pg.click('.rm-sheet a.rm-seg >> nth=0'); pg.wait_for_timeout(500)
            check('M10g 点第 1 段：真发出同一条高德链接', hits and hits[0] == segs[0], hits[:1])
            pg.go_back(); pg.wait_for_timeout(600)
            st_ = pg.evaluate("({sheet:!!document.querySelector('.rm-sheet.rm-dyn'),layer:!!document.querySelector('.rm')})")
            check('M10h 返回键先关分段层、地图还在（%s）' % st_, not st_['sheet'] and st_['layer'], st_)
            pg.go_back(); pg.wait_for_timeout(600)
            check('M10i 再按返回：地图关闭', not pg.evaluate("!!document.querySelector('.rm')"))
            c.close()
        for ua, lim, tag, rid in ((IPHONE, 3, '手机', 'tk4'), ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36', 9, '电脑', 'tk4')):
            with guard('M10c-' + tag):
                c, sb = mk(br, ua=ua); pg = new_page(env, c); goto(env, pg, '/trip/%s/' % rid, 700)
                pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); ready(pg)
                ndays = pg.evaluate("document.querySelectorAll('section.day').length"); info = []; allok = True
                for i in range(1, ndays + 1):
                    segs = pg.evaluate("ZRM.segs(document.getElementById('d%d'))" % i)
                    if not segs: continue
                    sp = pg.evaluate("document.getElementById('d%d').getAttribute('data-sp')" % i)
                    from urllib.parse import urlparse, parse_qs, unquote
                    q0 = parse_qs(urlparse(segs[0]).query)
                    ok = 'google.com/maps/dir' in segs[0] and 'travelmode=driving' in segs[0] and all(len(parse_qs(urlparse(u).query).get('waypoints', [''])[0].split('|')) <= lim for u in segs)
                    o = q0['origin'][0].split(','); w = sp.split(',')
                    ok = ok and abs(float(o[0]) - float(w[0])) < 1e-6 and abs(float(o[1]) - float(w[1])) < 1e-6 and all(len(u) < 2048 for u in segs)
                    allok = allok and ok; info.append((i, len(segs)))
                check('M10j 国外（%s，%s）：谷歌地图、WGS84 原坐标、每段途经点 ≤%d、链接 <2048、起点 = data-sp（%d 天，分段 %s）' % (rid, tag, lim, ndays, info[:4]), allok and bool(info), info)
                c.close()

    # ─────────── M11 样式 / 字形
    if want('M11'):
        with guard('M11'):
            c, sb = mk(br); pg = new_page(env, c); reqs = []
            pg.on('request', lambda r: reqs.append(r.url))
            goto(env, pg, '/trip/xa3/', 700); open_ov(pg); pg.wait_for_timeout(1500)
            o = pg.evaluate("""(function(){var m=ZRM.cur().map,st=m.getStyle(),bad=[],hid=0;st.layers.forEach(function(l){if(/boundary|country|state|disputed/.test(l.id)){var v=m.getLayoutProperty(l.id,'visibility');if(v==='none')hid++;else bad.push(l.id)}});
              var txt=0,zh=0;st.layers.forEach(function(l){if(l.type==='symbol'&&l.layout&&l.layout['text-field']&&!/shield/.test(l.id)&&m.getLayoutProperty(l.id,'visibility')!=='none'){txt++;var t=JSON.stringify(m.getLayoutProperty(l.id,'text-field'));if(t.indexOf('name:zh-Hans')>0)zh++}});
              return {hid:hid,bad:bad,txt:txt,zh:zh,sprite:st.sprite,glyphs:st.glyphs,pr:m.getPixelRatio()}})()""")
            check('M11a 地图里实际加载的样式：边界 / 国家 / 省级 / 争议图层全部 visibility:none（隐藏 %d 个，没隐藏 %s）；显示着的标注图层 %d 个里 %d 个中文优先' % (o['hid'], o['bad'], o['txt'], o['zh']), o['hid'] >= 4 and not o['bad'] and o['txt'] > 10 and o['zh'] == o['txt'], o)
            check('M11b 样式的 sprite / glyphs 在本站（%s）、没去 openfreemap 取样式' % o['sprite'].split('/')[2], o['sprite'].startswith(env.B) and o['glyphs'].startswith(env.B) and not any('openfreemap.org/styles' in u or 'openfreemap.org/sprites' in u for u in reqs), (o['sprite'], [u for u in reqs if 'openfreemap' in u][:4]))
            cjk = [u for u in reqs if re.search(r'/fonts/.*/(1[0-9]{4,}|[2-6][0-9]{4})-\d+\.pbf', u)]
            lf = cur(pg, "r.map._localIdeographFontFamily") or ''
            check('M11c 中文字形走系统字体：地图的 localIdeographFontFamily 是苹方 / 微软雅黑 / Noto CJK 那一串（%s）、没有请求 CJK 范围的 glyph 包（%d 个）' % (lf[:40], len(cjk)), 'PingFang' in lf and 'Microsoft YaHei' in lf and 'Noto Sans CJK' in lf and not cjk, (lf, cjk[:3]))
            c.close()

    # ─────────── M13 旧“第二轮”判据里还成立的：入口在第一屏 / 密集标记 / 点按范围 / “调整”点击区 / 加一天去掉一天后的同步
    if want('M13'):
        with guard('M13a'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)
            go = pg.evaluate("(function(){var e=document.querySelector('.mapgo');if(!e)return null;var r=e.getBoundingClientRect();return {top:Math.round(r.top+scrollY),h:Math.round(r.height),ih:innerHeight}})()")
            check('M13a “看路线图”入口在第一屏（离页顶 %spx，视口 %spx，高 %spx ≥44）' % (go and go['top'], go and go['ih'], go and go['h']), bool(go) and go['top'] + go['h'] <= go['ih'] - 8 and go['h'] >= 44, go)
            h = pg.evaluate(HIT, pg.query_selector('#d1 .r .s .adj'))
            check('M13b 每站的“调整”小标签点击区 ≥44×44（实测 %s×%s，视觉 %s×%s）' % (h and h['w'], h and h['h'], h and h['bw'], h and h['bh']), bool(h) and h['w'] >= 44 and h['h'] >= 44, h)
            c.close()
        with guard('M13b'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 600)
            dense = None
            for n in (1, 2, 3):
                open_day(pg, n); pg.wait_for_timeout(700)
                sm = cur(pg, "r.marks.filter(function(m){return m.el.classList.contains('rm-sm')}).length")
                if sm: dense = (n, sm); break
                pg.click('.rm-x'); pg.wait_for_timeout(500)
            check('M13c 有标记相距 <30px 的一天：挤在一起的标记缩成 22px（第 %s 天，%s 个）' % (dense and dense[0], dense and dense[1]), bool(dense), dense)
            if dense:
                w = pg.evaluate("(function(){var e=document.querySelector('.rm-mk.rm-sm i');return Math.round(e.getBoundingClientRect().width)})()")
                n_ = cur(pg, "r.marks.filter(function(m){return m.el.classList.contains('rm-sm')&&m.kind==='n'})[0].n")
                mp = mark_px(pg, n_); T.tap(mp[0], mp[1]); pg.wait_for_timeout(1500)
                tg = pg.evaluate("(function(){var t=document.querySelector('.rm-tg span');return t?t.textContent:null})()"); nm = cur(pg, "r.days[r.sel].pts[%d].name" % (n_ - 1))
                check('M13d 缩小后宽 %dpx（22）；选中一个挤在一起的标记：旁边出现名字小标签（%s）' % (w, tg), w == 22 and tg == nm, (w, tg, nm))
                cur(pg, "r.view.map.jumpTo({zoom:5})"); pg.wait_for_timeout(900); pg.evaluate("ZRM.cur().view.zoomBy(0)")
                cen = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.kind==='n'});return [m[0].px,m[0].py,m.length]})()")
                T.tap(cen[0], cen[1]); pg.wait_for_timeout(600)
                pk = pg.evaluate("[].slice.call(document.querySelectorAll('.rm-pi')).map(function(b){return b.textContent})")
                check('M13e 缩得很小时点同一位置的多个站：弹出列表让人选（%d 项）' % len(pk), len(pk) >= 2, pk)
                if len(pk) >= 2:
                    pg.click('.rm-pi >> nth=1'); pg.wait_for_timeout(700)
                    check('M13f 从列表里选第 2 项：选中的就是它（cur=%s，卡片 %s）' % (cur(pg, 'r.cur'), cur(pg, 'r.mode')), bool(cur(pg, 'r.cur')) and cur(pg, 'r.mode') == 'card', cur(pg, 'r.cur'))
            c.close()
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/hss1a/', 800)
            open_ov(pg); pg.wait_for_timeout(900)
            lab = cur(pg, "r.marks.filter(function(m){return m.badge&&m.el.style.visibility!=='hidden'}).map(function(m){return m.el.textContent})")
            check('M13g 总览里位置相同的几天合并成一个章并写范围（%s）' % lab, any(('–' in x or '·' in x) for x in lab), lab)
            mg = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.badge&&m.el.style.visibility!=='hidden'&&/[–·]/.test(m.el.textContent)})[0];return m?[m.px,m.py]:null})()")
            if mg:
                T.tap(mg[0], mg[1]); pg.wait_for_timeout(600)
                pk = pg.evaluate("[].slice.call(document.querySelectorAll('.rm-pi')).map(function(b){return b.textContent})")
                check('M13h 点合并的天数章：弹列表列出被合并的每一天（%d 项），选其中一天：切到那一天' % len(pk), len(pk) >= 2 and all(re.match(r'^第 \d+ 天', x) for x in pk), pk)
                if pk: pg.click('.rm-pi >> nth=1'); pg.wait_for_timeout(700); check('M13i 选其中一天后 sel=%s' % cur(pg, 'r.sel'), cur(pg, 'r.sel') >= 1, cur(pg, 'r.sel'))
            else: check('M13h 点合并的天数章', False, '没有合并的章')
            c.close()
        with guard('M13c'):
            c, sb = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 600)
            open_day(pg, 2); pg.wait_for_timeout(800)
            cur(pg, "r.view.map.jumpTo({zoom:r.view.map.getZoom()+1.5,center:[r.days[r.sel].pts[0].ll[1],r.days[r.sel].pts[0].ll[0]]})"); pg.wait_for_timeout(500)
            cur(pg, "(function(){var q=r.view.project(r.days[r.sel].pts[0].ll);r.view.map.panBy([q.x-150,q.y-230],{animate:false})})()"); pg.wait_for_timeout(700)      # 把第一站挪到面板上方露出来的那块地图里（屏幕 150,230）
            ms = cur(pg, "r.marks.filter(function(m){return m.kind==='n'}).map(function(m){return[m.n,m.px,m.py]})")
            allm = cur(pg, "r.marks.filter(function(m){return m.kind}).map(function(m){return[m.kind+(m.n||''),m.px,m.py]})")
            iso = [m for m in ms if all(o[0] == 'n' + str(m[0]) or abs(o[1] - m[1]) + abs(o[2] - m[2]) > 70 for o in allm) and 40 < m[1] < 300 and 90 < m[2] < 380]
            got = []
            for n_, x_, y_ in iso[:2]:
                for dx, dy in ((18, 0), (0, -18), (-15, 15)):
                    cur(pg, "r.view.map.jumpTo({zoom:r.view.map.getZoom()})"); pg.evaluate("ZRM.cur().mode='list';ZRM.cur().cur=0;ZRM.selectDay(ZRM.cur().sel)"); pg.wait_for_timeout(900)
                    cur(pg, "r.view.map.jumpTo({zoom:12.5,center:[r.days[r.sel].pts[%d].ll[1],r.days[r.sel].pts[%d].ll[0]]})" % (n_ - 1, n_ - 1)); cur(pg, "(function(){var q=r.view.project(r.days[r.sel].pts[%d].ll);r.view.map.panBy([q.x-150,q.y-230],{animate:false})})()" % (n_ - 1)); pg.wait_for_timeout(700)
                    mp = mark_px(pg, n_); T.tap(mp[0] + dx, mp[1] + dy); pg.wait_for_timeout(500); got.append((n_, dx, dy, cur(pg, 'r.cur')))
            check('M13j 点在标记中心 ≤22px 的范围内都点中这个标记（%s）' % got[:6], bool(got) and all(g[3] == g[0] for g in got), got)
            c.close()
        with guard('M13d'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xj10/', 700)
            pg.evaluate("document.querySelector('#d5 .dayadj').scrollIntoView({block:'center',behavior:'instant'})"); pg.locator('#d5 .dayadj').click(); pg.wait_for_selector('.pk [data-a="after"]'); pg.click('.pk [data-a="after"]'); pg.wait_for_selector('.pk [data-rid]'); pg.wait_for_timeout(300)
            pg.locator('.pk .xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
            open_ov(pg, False); pg.wait_for_timeout(700)
            n1 = cur(pg, 'r.days.length'); sc = pg.evaluate("document.querySelectorAll('section.day').length"); t1 = pg.evaluate("document.querySelectorAll('.rm-tb').length")
            check('M13k 加一天后打开地图：天数 %s = 页面 %d 天、标签条 %d 个（全程 + 每天）；新加的那天也有“本日地图”入口' % (n1, sc, t1), n1 == sc and t1 == sc + 1 and pg.evaluate("document.querySelectorAll('section.day').length") == sc, (n1, sc, t1))
            c.close()
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)
            pg.evaluate("document.querySelector('#d2 .dayadj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .dayadj'); pg.wait_for_selector('.pk .rmgo'); pg.click('.pk .rmgo')
            pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
            open_ov(pg, False); pg.wait_for_timeout(600)
            n2 = cur(pg, 'r.days.length'); t2 = pg.evaluate("document.querySelectorAll('.rm-tb').length")
            check('M13l 去掉一天后打开地图：总览 %s 天（原 3 天）、标签条 %d 个（全程 + %s 天）' % (n2, t2, n2), n2 == 2 and t2 == 3, (n2, t2))
            c.close()
        with guard('M13e'):
            c, sb = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
            c.set_offline(True); pg.wait_for_timeout(250)
            navs = pg.evaluate("[].map.call(document.querySelectorAll('.rm-nb'),function(b){return [b.textContent,b.disabled,b.classList.contains('off')]})")
            check('M13m 断网：每天的“导航这一天”（页面里的）置灰写“没网，暂时不能导航”（%d 个）' % len(navs), bool(navs) and all('没网' in t and d and o for t, d, o in navs), navs[:2])
            c.set_offline(False); pg.wait_for_timeout(250)
            navs = pg.evaluate("[].map.call(document.querySelectorAll('.rm-nb'),function(b){return [b.textContent,b.disabled]})")
            check('M13n 联网后恢复为“导航这一天 ›”', all(t == '导航这一天 ›' and not d for t, d in navs), navs[:2])
            c.close()

    # ─────────── M12 Service Worker：带指纹的地图文件先用缓存；瓦片先用缓存、后台更新、最多 500 块
    if want('M12'):
        sw_ok = True
        with guard('M12'):
            c, sb = mk(br, storage={'zouni_dev_sw': '1'}); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600)      # 本地 http 默认不注册 SW，zouni_dev_sw=1 才注册（site.js 第 12 行）
            pg.evaluate("Promise.race([navigator.serviceWorker.ready.then(function(){return 1}),new Promise(function(r){setTimeout(r,8000)})])"); pg.wait_for_timeout(800)
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(600)
            ctl = pg.evaluate("!!navigator.serviceWorker.controller")
            try: open_ov(pg)
            except Exception:
                sw_ok = False; check('M12a SW 接管后点开地图：瓦片没来（SW 的瓦片规则坏了？）', False, 'open_ov 超时'); c.close(); raise
            pg.wait_for_timeout(1200)
            keys = pg.evaluate("caches.keys()")
            vkeys = pg.evaluate("caches.open('zouni-v3').then(function(c){return c.keys()}).then(function(ks){return ks.map(function(k){return new URL(k.url).pathname+new URL(k.url).search})})")
            tk = pg.evaluate("caches.open('zouni-tiles-v1').then(function(c){return c.keys()}).then(function(ks){return ks.map(function(k){return k.url}).filter(function(u){return /\\.pbf$/.test(u)})})")      # 只数瓦片（瓦片索引也在这个缓存里，不算）
            check('M12a 页面被 SW 接管（controller=%s）；点开后：带 ?v= 的 maplibre js / css / routemap.js / 样式进了缓存（%d 条），瓦片进了单独的缓存（%d 块，缓存名 %s）' % (ctl, len([k for k in vkeys if '?v=' in k and re.search(r'maplibre|routemap|style\.json', k)]), len(tk), keys), ctl and len([k for k in vkeys if re.search(r'maplibre-gl\.js\?v=', k)]) == 1 and len([k for k in vkeys if re.search(r'routemap\.js\?v=', k)]) == 1 and len([k for k in vkeys if re.search(r'map/style\.json\?v=', k)]) == 1 and len(tk) > 0 and 'zouni-tiles-v1' in keys, (keys, vkeys[:6], len(tk)))
            h0 = dict(env.hits); pg.click('.rm-x'); pg.wait_for_timeout(500)
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(600); open_ov(pg); pg.wait_for_timeout(1000)
            ml = [k for k in env.hits if 'maplibre-gl.js' in k]; rm = [k for k in env.hits if k.endswith('routemap.js')]; sy = [k for k in env.hits if k.endswith('map/style.json')]
            check('M12b 第二次点开：maplibre-gl.js（%s → %s）、routemap.js（%s → %s）、样式（%s → %s）一次都没再请求本站（SW 先用缓存）' % (h0.get(ml[0]), env.hits.get(ml[0]), h0.get(rm[0]), env.hits.get(rm[0]), h0.get(sy[0]), env.hits.get(sy[0])), env.hits.get(ml[0]) == h0.get(ml[0]) and env.hits.get(rm[0]) == h0.get(rm[0]) and env.hits.get(sy[0]) == h0.get(sy[0]), (h0.get(ml[0]), env.hits.get(ml[0]), h0.get(rm[0]), env.hits.get(rm[0])))
            pg.evaluate("""(function(){var a=[];for(var i=0;i<540;i++)a.push(fetch('https://tiles.openfreemap.org/planet/t/14/'+i+'/7.pbf',{mode:'cors'}).then(function(r){return r.arrayBuffer()}).catch(function(){}));return Promise.race([Promise.all(a),new Promise(function(r){setTimeout(r,8000)})])})()""")      # 最多等 8 秒（没有 SW 接管时这些请求可能一直挂着，不能让测试卡死）
            pg.wait_for_timeout(1500)
            n = pg.evaluate("caches.open('zouni-tiles-v1').then(function(c){return c.keys()}).then(function(ks){return ks.length})")
            check('M12c 瓦片缓存最多 500 块（塞了 540 块以后是 %d 块，超了删最早的）' % n, 0 < n <= 500, n)
            c.close()

        def fav_case(tag, init_js, want_tiles):
            c, sb = mk(br, storage={'zouni_dev_sw': '1'})
            if init_js: c.add_init_script(init_js)
            pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 600); pg.evaluate("Promise.race([navigator.serviceWorker.ready.then(function(){return 1}),new Promise(function(r){setTimeout(r,8000)})])"); pg.wait_for_timeout(800)
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(500)
            n0 = sb.n['pbf']; pg.evaluate("document.querySelector('.fav').click()"); pg.wait_for_timeout(3500)
            got = sb.n['pbf'] - n0
            tk = pg.evaluate("caches.open('zouni-tiles-v1').then(function(c){return c.keys()}).then(function(ks){return ks.length})")
            check('M12%s 收进行程时预取取景范围的低缩放瓦片（%s）：取了 %d 块（%s）、进缓存 %d 块' % (tag, '4g / 没开省流量' if want_tiles else '省流量或慢网不做', got, '1–24 块' if want_tiles else '0 块', tk), (1 <= got <= 24 and tk >= 1) if want_tiles else (got == 0), (got, tk))
            c.close()
        with guard('M12d'): fav_case('d', "", True) if sw_ok else None
        with guard('M12e'): fav_case('e', "Object.defineProperty(navigator,'connection',{value:{effectiveType:'4g',saveData:true},configurable:true});", False) if sw_ok else None
        with guard('M12f'): fav_case('f', "Object.defineProperty(navigator,'connection',{value:{effectiveType:'3g',saveData:false},configurable:true});", False) if sw_ok else None
    if LIVE:
        with guard('LIVE-style'):
            import subprocess
            r = subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'map_assets.py'), '--check'], cwd=ROOT, capture_output=True, text=True)
            check('LIVE 样式对照：线上 liberty 样式里命中隐藏规则的图层，在自托管样式里全部 visibility:none（%s）' % (r.stdout.strip().splitlines() or [r.stderr[-100:]])[-1][:120], r.returncode == 0, r.stdout + r.stderr)
        with guard('LIVE'):
            c = new_ctx(br, None); pg = new_page(env, c)
            goto(env, pg, '/trip/xa3/', 700); open_ov(pg, False)
            pg.wait_for_function("ZRM.cur().tiles>0||ZRM.cur().failed", timeout=30000)
            check('LIVE 联网冒烟：真 OpenFreeMap 瓦片到了（tiles=%s，failed=%s）' % (state(pg)['tiles'], state(pg)['failed']), state(pg)['tiles'] > 0 and not state(pg)['failed'], state(pg))
            c.close()
    br.close()
env.finish('map_app_check')
