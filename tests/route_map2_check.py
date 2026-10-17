#!/usr/bin/env python3
"""路线地图第二轮（2026-10-18，5 位模拟用户在手机 390 宽实测后的 P1 问题）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/route_map2_check.py build/site [--shots DIR]
    python3 tests/route_map2_check.py build/site --inject 名字     # 反向自检，每个名字都必须变红（名字见 INJ）

底图瓦片全部被拦截 / 挂起（不依赖外网，和 route_map_check.py 同一套 fixture）。

R1  慢网：点开立刻出现“地图加载中”小条（不遮地图：≤30px 高）；瓦片一直不回 → 12 秒（从地图建好算）退示意图，提示写“街道地图加载失败，已改用示意图”（不写“需要联网”），
    提示在地图里面、看得见、没被底部栏盖住
R2  示意图版：自动取景到当天站点（站点占满图、不是空白）、有站名标签和比例尺、放大后编号章都在可视区里、能拖动
R3  地图打开期间底部固定栏收起；存图 / i / + / − / 全屏 全都点得到（elementFromPoint 命中自己）；关掉地图后固定栏回来
R4  双指起点落在站点方块上：缩放的是地图（visualViewport.scale 仍是 1、地图层级变了），不是整页
R5  全屏名副其实：地图铺满视口；天标签条是底部抽屉、默认只露一条；退出是左上带“关上”字的按钮，位置和进入按钮不同；Esc 也能退
R6  断网：每天的“导航这一天”和地图里的“导航这一天”置灰写“没网，暂时不能导航”，点它不弹分段层；联网后恢复
R7  导航分段是方形按钮（“第 N 段：… 用高德打开 ›”，≥44 高、有边框），起点不叫“出发地”（写“昨晚住处”或具体名）
R8  地图下面有“站点之间是直线示意，不是行车路线”
R9  密集站点：挤在一起的标记缩成 22px、选中有名字标签；同一位置多个点按弹列表选；总览里同位置的天合并成“2–5”且点得到
R10 “看路线图”入口在第一屏；点开后地图（到标签条）进第一屏
R11 每天标题的“调整”点击区 ≥44×44
R12 点站点方块：离中心 ≤22px（44×44 的方块范围）都算点中它
"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'slow25': ('assets/routemap.js', "var SLOW_MS = 12000, HARD_MS = 20000;", "var SLOW_MS = 25000, HARD_MS = 40000;"),            # 兜底又拖到 25 秒
    'load_off': ('assets/routemap.js', "function showLoad(inst) { if (inst.load) {", "function showLoad(inst) { if (false) {"),          # 没有“加载中”
    'note_old': ('assets/routemap.js', "var NOTE_OFF = '街道地图加载失败，已改用示意图';", "var NOTE_OFF = '街道地图需要联网';"),                 # 措辞又写“需要联网”
    'sch_noclamp': ('assets/routemap.js', "if (sch && !m.dot) { x = Math.max(24", "if (false && !m.dot) { x = Math.max(24"),          # 示意图编号章可以跑出可视区
    'sch_nodrag': ('assets/routemap.js', "function wireDrag(inst) {\n    var st = null;", "function wireDrag(inst) {\n    return; var st = null;"),                    # 示意图不能拖
    'dock_stay': ('assets/site.css', "body.rmap-on .dock{display:none}", ""),                                                          # 地图打开时底部栏还在
    'mk_auto': ('assets/site.css', ".rm .rm-pts>*{pointer-events:none}", ".rm .rm-pts>*{pointer-events:auto}"),                       # 标记又抢手指（双指落在标记上缩放整页）
    'fs_half': ('assets/site.css', ".rm.rm-fs .rm-stage{position:absolute;left:0;top:0;right:0;bottom:0;height:auto;min-height:0;touch-action:none}", ".rm.rm-fs .rm-stage{position:relative;height:340px;touch-action:none}"),   # 全屏又变半屏
    'exit_icon': ('assets/routemap.js', '<span class="rm-xt">关上</span>', ''),                                                         # 退出按钮没有字
    'nav_off_pg': ('assets/site.js', "function navBtns(){var off=navigator.onLine===false;", "function navBtns(){var off=false;"),       # 页面里的导航按钮断网不置灰
    'nav_off_map': ('assets/routemap.js', "if (!inst || !inst.navd) return; var off = navigator.onLine === false;", "if (!inst || !inst.navd) return; var off = false;"),   # 地图里的导航按钮断网不置灰
    'seg_plain': ('assets/routemap.js', "var who = APP === 'google' ? '用谷歌地图打开 ›' : '用高德打开 ›';", "var who = '';"),                  # 分段按钮没写用什么打开
    'sp_old': ('assets/routemap.js', "push(d.spName || '昨晚住处', d.sp);", "push('出发地', d.sp);"),                                  # 起点又叫“出发地”
    'no_straight': ('assets/routemap.js', "h += '<span class=\"rm-lg2 rm-st\">站点之间是直线示意，不是行车路线</span>';", ""),         # 没有“直线示意”说明
    'no_dense': ('assets/routemap.js', "m.small = tight; m.el.classList.toggle('rm-sm', tight);", "m.small = false;"),                    # 挤在一起也不缩小
    'no_tag': ('assets/routemap.js', "function paintTag(inst, quiet) {", "function paintTag(inst, quiet) {\n    return;"),               # 选中没有名字标签
    'no_merge': ('assets/routemap.js', "var t = k.g.length > 1 ? rangeLabel(k.g) : String(k.m.day + 1)", "var t = String(k.m.day + 1)"),   # 总览合并的天不写范围
    'tap_first': ('assets/routemap.js', "if (c.length === 1 || c[1].d - c[0].d > 12) { c[0].m.el.click(); return true; }", "if (true) { c[0].m.el.click(); return true; }"),   # 同位置多个点只取第一个
    'go_hidden': ('assets/site.css', ".mapgo{display:flex;", ".mapgo{display:none;"),                                                  # 第一屏没有入口
    'no_reveal': ('assets/routemap.js', "function reveal(inst) {\n    setTimeout(function () {", "function reveal(inst) {\n    return; setTimeout(function () {"),    # 点开后不把地图带进视野
    'tap_radius': ('assets/routemap.js', "if (d <= (m.small ? 20 : 26)) c.push({ m: m, d: d });", "if (d <= (m.small ? 4 : 6)) c.push({ m: m, d: d });"),                                            # 点按范围缩成几个像素
    'adj_small': ('assets/site.css', ".r .s .adj:after,.adj:after{inset:-14px -10px}", ".r .s .adj:after,.adj:after{inset:0}"),         # “调整”点击区缩回去
}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
STYLE = open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read()
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard


def stub(c, mode='ok'):
    """mode: ok（空瓦片）| tiles（瓦片全挂）| hang（瓦片一直不回）"""
    def style(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=STYLE)
    def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
    def pbf(r):
        if mode == 'tiles': return r.abort()
        if mode == 'hang': return          # 不回应
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


def mk(br, mode='ok', dark=False):
    c = new_ctx(br, None, dark=dark); stub(c, mode); return c


def ready(pg, timeout=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=timeout)
def tiles(pg, timeout=12000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().tiles>0", timeout=timeout)
def cur(pg, expr): return pg.evaluate("(function(){var r=ZRM.cur();return r?(" + expr + "):null})()")


def open_day(pg, n, wait_tiles=True):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n); ready(pg)
    if wait_tiles: tiles(pg)


def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


def stage_rect(pg): return pg.evaluate("(function(){var r=document.querySelector('.rm-stage').getBoundingClientRect();return {l:r.left,t:r.top,w:r.width,h:r.height}})()")


def tap_mark(pg, kind, key):
    """用真实鼠标点在某个标记的位置上（标记自己不接收指针，点按走舞台的“最近标记”）"""
    p = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.kind==='%s'&&(%s)})[0];return m?[m.px,m.py]:null})()" % (kind, key))
    sr = stage_rect(pg)
    pg.mouse.click(sr['l'] + p[0], sr['t'] + p[1]); return p


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)

    # ─────────── R1 慢网：加载中 + 12 秒兜底 + 提示看得见
    with guard('R1'):
        c = mk(br, 'hang'); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'start',behavior:'instant'})")
        t0 = time.time(); pg.click('.mapgo'); ready(pg)
        pg.wait_for_timeout(800)
        ld = pg.evaluate("(function(){var l=document.querySelector('.rm-load');if(!l)return null;var r=l.getBoundingClientRect(),s=document.querySelector('.rm-stage').getBoundingClientRect();return {vis:!l.hidden&&r.height>0,txt:l.textContent,h:Math.round(r.height),sh:Math.round(s.height),w:Math.round(r.width)}})()")
        check('R1a 点开不到 1 秒：出现“地图加载中”（%s）' % (ld or {}).get('txt'), bool(ld) and ld['vis'] and '地图加载中' in ld['txt'], ld)
        check('R1b 加载小条不遮地图（高 %spx，地图 %spx）' % (ld and ld['h'], ld and ld['sh']), bool(ld) and 0 < ld['h'] <= 30 and ld['h'] / max(1, ld['sh']) < .1, ld)
        shot(pg, 'r1_loading.png')
        pg.wait_for_function("ZRM.cur()&&ZRM.cur().failed", timeout=18000)
        dt = time.time() - t0
        check('R1c 瓦片一直不回：退到示意图用了 %.1f 秒（要 ≤16 秒，其中 12 秒是兜底计时，其余是取脚本和样式；原来 25 秒）' % dt, dt <= 16, dt)
        st = pg.evaluate("(function(){var n=document.querySelector('.rm-note'),l=document.querySelector('.rm-load');var r=n.getBoundingClientRect();var e=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {txt:n.textContent,vis:!n.hidden&&r.height>0,inView:r.top>=0&&r.bottom<=innerHeight,top:e===n||n.contains(e),loadHidden:!!l.hidden,why:ZRM.cur().why}})()")
        check('R1d 兜底提示写“街道地图加载失败，已改用示意图”，不写“需要联网”（%s）' % st['txt'], st['txt'] == '街道地图加载失败，已改用示意图' and '联网' not in st['txt'], st)
        check('R1e 提示在地图里面、看得见、没被别的盖住；加载小条已收起', st['vis'] and st['inView'] and st['top'] and st['loadHidden'], st)
        shot(pg, 'r1_fallback.png')
        c.close()

    # ─────────── R2 / R8 示意图版（瓦片全挂 → 秒退）
    with guard('R2'):
        c = mk(br, 'tiles'); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 2, False); pg.wait_for_function("ZRM.cur().failed", timeout=8000); pg.wait_for_timeout(500)
        sr = stage_rect(pg)
        mk_ = cur(pg, "r.marks.filter(function(m){return m.kind==='n'}).map(function(m){return[m.px,m.py]})")
        xs = [a[0] for a in mk_]; ys = [a[1] for a in mk_]
        spread = max((max(xs) - min(xs)) / sr['w'], (max(ys) - min(ys)) / sr['h'])
        check('R2a 示意图自动取景到当天站点：%d 个站占满图（跨度占 %.0f%%，不是空白一角）' % (len(mk_), spread * 100), len(mk_) >= 3 and spread >= .4, (spread, mk_))
        check('R2b 编号章都在可视区里', all(0 <= x <= sr['w'] and 0 <= y <= sr['h'] for x, y in mk_), mk_)
        lbn = pg.evaluate("document.querySelectorAll('.rm-lb').length"); sc = pg.evaluate("(document.querySelector('.rm-sc')||{}).textContent||''")
        check('R2c 示意图上有站名标签（%d 个）、比例尺和北向（%s）' % (lbn, sc), lbn >= 2 and ('公里' in sc or '米' in sc) and '北' in sc and re.search(r'\d', sc), (lbn, sc))
        for _ in range(4):
            if pg.is_disabled('.rm-zi'): break
            pg.click('.rm-zi'); pg.wait_for_timeout(150)
        z = cur(pg, 'r.view.zoom()')
        mk2 = cur(pg, "r.marks.filter(function(m){return m.kind==='n'}).map(function(m){return[m.px,m.py]})")
        check('R2d 放大到顶（层级 %s，+ 置灰）：编号章仍全在可视区里，不会跑到屏幕外' % z, pg.is_disabled('.rm-zi') and z <= 2 and all(0 <= x <= sr['w'] and 0 <= y <= sr['h'] for x, y in mk2), (z, mk2))
        c0 = cur(pg, '[r.view.st.cx,r.view.st.cy]')
        sr = stage_rect(pg)
        pg.mouse.move(sr['l'] + 200, sr['t'] + 100); pg.mouse.down(); pg.mouse.move(sr['l'] + 140, sr['t'] + 100, steps=6); pg.mouse.move(sr['l'] + 90, sr['t'] + 90, steps=6); pg.mouse.up(); pg.wait_for_timeout(200)
        c1 = cur(pg, '[r.view.st.cx,r.view.st.cy]')
        check('R2e 示意图能拖动（视图中心 %s → %s）' % (c0, c1), abs(c1[0] - c0[0]) > 1e-6, (c0, c1))
        leg = pg.inner_text('.rm-leg')
        check('R8a 本日地图下有“站点之间是直线示意，不是行车路线”', '站点之间是直线示意，不是行车路线' in leg, leg)
        shot(pg, 'r2_sch_day.png')
        c.close()

    # ─────────── R3 底部栏让位 + 控件点得到 / R10 入口和进入第一屏
    with guard('R3'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        dk = pg.evaluate("(function(){var d=document.querySelector('.dock');var r=d.getBoundingClientRect();return {disp:getComputedStyle(d).display,top:r.top}})()")
        check('R3a 没开地图时底部固定栏在（%s）' % dk['disp'], dk['disp'] != 'none', dk)
        go = pg.evaluate("(function(){var b=document.querySelector('.mapgo');if(!b)return null;var r=b.getBoundingClientRect();return {top:Math.round(r.top),h:Math.round(r.height),ih:innerHeight,txt:b.textContent}})()")
        check('R10a “看路线图”入口在第一屏（离页顶 %spx、视口 %spx，高 %s）' % (go and go['top'], go and go['ih'], go and go['h']), bool(go) and go['top'] + go['h'] <= go['ih'] - 8 and go['h'] >= 44, go)
        pg.click('.mapgo'); ready(pg); tiles(pg); pg.wait_for_timeout(500)
        r = pg.evaluate("""(function(){var q=function(s){var e=document.querySelector(s);if(!e)return null;var r=e.getBoundingClientRect();var h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);return {in:r.top>=0&&r.bottom<=innerHeight,hit:h===e||e.contains(h)}};
          var d=document.querySelector('.dock');var tb=document.querySelector('.rm-tabs').getBoundingClientRect();
          return {dock:getComputedStyle(d).display,sv:q('.rm-sv'),ai:q('.rm-ai'),zi:q('.rm-zi'),zo:q('.rm-zo'),fs:q('.rm-fsb'),rs:q('.rm-rs'),tabBottom:Math.round(tb.bottom),ih:innerHeight,st:Math.round(document.querySelector('.rm-stage').getBoundingClientRect().top)}})()""")
        check('R3b 地图打开期间底部固定栏收起（display:%s）' % r['dock'], r['dock'] == 'none', r)
        bad = [k for k in ('sv', 'ai', 'zi', 'zo', 'fs', 'rs') if not (r[k] and r[k]['in'] and r[k]['hit'])]
        check('R3c 存图 / i / + / − / 全屏 / 回到全程 全都在视口里且点得到（%s）' % (('不行：' + ','.join(bad)) if bad else '全部可点'), not bad, r)
        check('R10b 点开后地图和标签条都进了第一屏（地图顶 %spx，标签条底 %spx，视口 %spx）' % (r['st'], r['tabBottom'], r['ih']), 0 <= r['st'] < r['ih'] - 200 and r['tabBottom'] <= r['ih'], r)
        shot(pg, 'r3_open.png')
        pg.click('.mapgo'); pg.wait_for_timeout(400)
        check('R3d 关掉地图后底部固定栏回来', pg.evaluate("getComputedStyle(document.querySelector('.dock')).display") != 'none')
        # 很长的页面也一样（长线 xl9a）
        pg.goto(env.B + '/trip/xl9a/', wait_until='networkidle'); pg.wait_for_timeout(500)
        go = pg.evaluate("(function(){var b=document.querySelector('.mapgo');if(!b)return null;var r=b.getBoundingClientRect();return {top:Math.round(r.top),h:r.height,ih:innerHeight}})()")
        check('R10c 长线页（xl9a）入口也在第一屏（离页顶 %spx）' % (go and go['top']), bool(go) and go['top'] + go['h'] <= go['ih'] - 8, go)
        c.close()

    # ─────────── R4 双指手势起点落在站点方块上：缩放的是地图
    with guard('R4'):
        c = mk(br); pg = new_page(env, c)
        cdp = c.new_cdp_session(pg)
        goto(env, pg, '/trip/xl9a/', 600)
        pg.click('.mapgo'); ready(pg); tiles(pg); pg.wait_for_timeout(600)
        # 站点方块：总览里的天数章（button.rm-mk），取一个看得见的
        mkp = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.badge&&m.el.style.visibility!=='hidden'})[0];return m?[m.px,m.py]:null})()")
        sr = stage_rect(pg); x0, y0 = sr['l'] + mkp[0], sr['t'] + mkp[1]
        hit = pg.evaluate("(function(x,y){var e=document.elementFromPoint(x,y);return e?e.className+'|'+getComputedStyle(e).pointerEvents:''})(%f,%f)" % (x0, y0))
        z0 = cur(pg, 'r.view.zoom()'); vs0 = pg.evaluate("visualViewport.scale")
        # 第一指就按在方块中心，第二指在下方 60px，然后两指拉开
        def touch(t, pts): cdp.send('Input.dispatchTouchEvent', {'type': t, 'touchPoints': pts})
        touch('touchStart', [{'x': x0, 'y': y0, 'id': 1}, {'x': x0, 'y': y0 + 60, 'id': 2}])
        for k in range(1, 13):
            touch('touchMove', [{'x': x0, 'y': y0 - k * 4, 'id': 1}, {'x': x0, 'y': y0 + 60 + k * 8, 'id': 2}]); pg.wait_for_timeout(30)
        touch('touchEnd', []); pg.wait_for_timeout(700)
        z1 = cur(pg, 'r.view.zoom()'); vs1 = pg.evaluate("visualViewport.scale")
        check('R4a 手指落在站点方块上（命中 %s）' % hit, 'rm-mk' not in hit.split('|')[0] or 'none' in hit, hit)
        check('R4b 双指拉开：整页没有被放大（visualViewport.scale %.2f → %.2f）' % (vs0, vs1), abs(vs1 - 1) < .02, (vs0, vs1))
        check('R4c 双指拉开：地图缩放了（层级 %.2f → %.2f）' % (z0, z1), z1 > z0 + .3, (z0, z1))
        c.close()

    # ─────────── R5 全屏名副其实
    with guard('R5'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 2)
        pg.evaluate("window.scrollBy({top:0,behavior:'instant'})")
        enter = pg.evaluate("(function(){var r=document.querySelector('.rm-fsb').getBoundingClientRect();return {l:Math.round(r.left),t:Math.round(r.top)}})()")
        pg.click('.rm-fsb'); pg.wait_for_timeout(900)
        fs = pg.evaluate("""(function(){var st=document.querySelector('.rm-stage').getBoundingClientRect(),dr=document.querySelector('.rm-drw').getBoundingClientRect(),tb=document.querySelector('.rm-tabs').getBoundingClientRect(),pn=document.querySelector('.rm-panel'),x=document.querySelector('.rm-fsb').getBoundingClientRect();
          return {sw:Math.round(st.width),sh:Math.round(st.height),iw:innerWidth,ih:innerHeight,drh:Math.round(dr.height),drb:Math.round(dr.bottom),tbv:tb.height>=40&&tb.bottom<=innerHeight+1,panel:getComputedStyle(pn).display,xl:Math.round(x.left),xt:Math.round(x.top),xw:Math.round(x.width),xh:Math.round(x.height),xtxt:document.querySelector('.rm-fsb').textContent.trim()}})()""")
        check('R5a 全屏时地图铺满整个视口（%dx%d，视口 %dx%d）' % (fs['sw'], fs['sh'], fs['iw'], fs['ih']), abs(fs['sw'] - fs['iw']) <= 1 and abs(fs['sh'] - fs['ih']) <= 1, fs)
        check('R5b 天标签条是底部抽屉，默认只露一条（抽屉高 %dpx，列表 display:%s）' % (fs['drh'], fs['panel']), fs['tbv'] and fs['drh'] <= 60 and fs['panel'] == 'none', fs)
        check('R5c 退出按钮是带“关上”字的方形按钮（%s，%dx%d），在左上角（%d,%d），不在进入按钮的位置（%d,%d）' % (fs['xtxt'], fs['xw'], fs['xh'], fs['xl'], fs['xt'], enter['l'], enter['t']),
              '关上' in fs['xtxt'] and fs['xh'] >= 44 and fs['xw'] >= 44 and fs['xl'] <= 8 and fs['xt'] <= 8 and abs(fs['xl'] - enter['l']) > 100, (fs, enter))
        shot(pg, 'r5_fullscreen.png')
        pg.click('.rm-tl'); pg.wait_for_timeout(500)
        op = pg.evaluate("(function(){var p=document.querySelector('.rm-panel'),r=p.getBoundingClientRect();return {d:getComputedStyle(p).display,h:Math.round(r.height),b:Math.round(document.querySelector('.rm-drw').getBoundingClientRect().height),ih:innerHeight}})()")
        check('R5d 上拉抽屉：站点列表出来（高 %dpx），抽屉不超过视口的 2/3（%dpx）' % (op['h'], op['b']), op['d'] != 'none' and op['h'] > 60 and op['b'] <= op['ih'] * .67, op)
        shot(pg, 'r5_drawer_open.png')
        # 抽屉上面的“存图”“i”不被抽屉盖住
        cov = pg.evaluate("(function(){var o={};['.rm-sv','.rm-ai'].forEach(function(s){var e=document.querySelector(s),r=e.getBoundingClientRect(),h=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);o[s]=h===e||e.contains(h)});return o})()")
        check('R5e 全屏抽屉打开时“存图”“i”仍点得到', all(cov.values()), cov)
        pg.click('.rm-fsb'); pg.wait_for_timeout(500)
        check('R5f 点“关上”退出全屏', not pg.evaluate("document.querySelector('.rm').classList.contains('rm-fs')"))
        pg.click('.rm-fsb'); pg.wait_for_timeout(500); pg.keyboard.press('Escape'); pg.wait_for_timeout(500)
        check('R5g Esc 也能退出', not pg.evaluate("!!document.querySelector('.rm')&&document.querySelector('.rm').classList.contains('rm-fs')"))
        c.close()

    # ─────────── R6 / R7 导航：断网置灰、分段按钮
    with guard('R6'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        c.set_offline(True); pg.wait_for_timeout(500)
        nb = pg.evaluate("(function(){var b=document.querySelector('#d1 .rm-nb');return {dis:b.disabled,txt:b.textContent,off:b.classList.contains('off')}})()")
        check('R6a 断网：每天的“导航这一天”置灰并写“没网，暂时不能导航”（%s）' % nb['txt'], nb['dis'] and nb['txt'] == '没网，暂时不能导航', nb)
        pg.evaluate("document.querySelector('#d1 .rm-nb').click()"); pg.wait_for_timeout(300)
        check('R6b 断网点它：不弹分段层', pg.evaluate("document.querySelectorAll('.rm-sheet').length===0"))
        c.set_offline(False); pg.wait_for_timeout(500)
        nb = pg.evaluate("(function(){var b=document.querySelector('#d1 .rm-nb');return {dis:b.disabled,txt:b.textContent}})()")
        check('R6c 联网后恢复“导航这一天 ›”', not nb['dis'] and nb['txt'] == '导航这一天 ›', nb)
        # 地图面板里的
        pg.click('.mapgo'); ready(pg); tiles(pg)
        pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(500)
        c.set_offline(True); pg.wait_for_timeout(500)
        nd = pg.evaluate("(function(){var b=document.querySelector('.rm-navd');return {txt:b.textContent,off:b.classList.contains('off'),aria:b.getAttribute('aria-disabled')}})()")
        check('R6d 断网：地图里的“导航这一天”也置灰（%s）' % nd['txt'], nd['off'] and nd['txt'] == '没网，暂时不能导航' and nd['aria'] == 'true', nd)
        pg.evaluate("document.querySelector('.rm-navd').click()"); pg.wait_for_timeout(300)
        check('R6e 地图里断网点它：不弹分段层', pg.evaluate("document.querySelectorAll('.rm-sheet').length===0"))
        c.set_offline(False)
        c.close()
    with guard('R7'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        res = {}
        for n in (1, 2):
            pg.evaluate("document.querySelector('#d%d .rm-nb').scrollIntoView({block:'center',behavior:'instant'})" % n)
            pg.click('#d%d .rm-nb' % n); pg.wait_for_timeout(400)
            res[n] = pg.evaluate("""(function(){var s=document.querySelector('.rm-sheet');if(!s)return null;var as=[].slice.call(s.querySelectorAll('a.rm-seg'));
              return {n:as.length,txt:s.innerText,segs:as.map(function(a){var r=a.getBoundingClientRect(),c=getComputedStyle(a);return {h:Math.round(r.height),bw:c.borderTopWidth,t:a.innerText.replace(/\\n/g,' ')}})}})()""")
            if res[n]:
                pg.evaluate("document.querySelector('.rm-sheet .pk-x').click()"); pg.wait_for_timeout(200)
        r1 = res[1]
        check('R7a 分段层里每一段是明显的方形按钮：≥44 高、有边框、写“用高德打开 ›”（%s）' % (r1 and [s['t'][:40] for s in r1['segs']][:2]), bool(r1) and r1['n'] >= 2 and all(s['h'] >= 44 and s['bw'] != '0px' and '用高德打开 ›' in s['t'] and re.match(r'^第 \d 段：', s['t']) for s in r1['segs']), r1)
        check('R7b 起点不叫“出发地”（第 1 天写“起点（城市）”，第 2 天起写“昨晚住处”）', bool(r1) and '出发地' not in r1['txt'] and re.sub(r'\s+', '', r1['segs'][0]['t']).startswith('第1段：起点') and bool(res[2]) and '出发地' not in res[2]['txt'] and '昨晚住处' in res[2]['txt'], (r1 and r1['segs'][0]['t'], res[2] and res[2]['txt'][:80]))
        c.close()

    # ─────────── R9 密集站点
    with guard('R9'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        # 找一天标记挤在一起的（xa3 第 1 天 3、4、5 号和“住”）
        dense_day = None
        for n in (1, 2, 3):
            open_day(pg, n); pg.wait_for_timeout(500)
            sm = cur(pg, "r.marks.filter(function(m){return m.el.classList.contains('rm-sm')}).length")
            if sm: dense_day = (n, sm); break
        check('R9a 有标记相距 <30px 的一天：挤在一起的标记缩成 22px（第 %s 天，%s 个）' % (dense_day and dense_day[0], dense_day and dense_day[1]), bool(dense_day), dense_day)
        if dense_day:
            w = pg.evaluate("(function(){var e=document.querySelector('.rm-mk.rm-sm i');return Math.round(e.getBoundingClientRect().width)})()")
            check('R9b 缩小后的标记宽 %dpx（22）' % w, w == 22, w)
            # 点其中一个 → 名字标签
            n_ = cur(pg, "r.marks.filter(function(m){return m.el.classList.contains('rm-sm')&&m.kind==='n'})[0].n")
            pg.click('.rm-fsb'); pg.wait_for_timeout(900)      # 全屏里点标记不会触发“页面滚到那一行”再把选中改掉
            sr = stage_rect(pg); tap_mark(pg, 'n', 'm.n===%d' % n_); pg.wait_for_timeout(500)
            tg = pg.evaluate("(function(){var t=document.querySelector('.rm-tg span');return t?t.textContent:null})()")
            nm = cur(pg, "r.days[r.sel].pts[%d].name" % (n_ - 1))
            check('R9c 选中一个挤在一起的标记：旁边出现名字小标签（%s）' % tg, tg == nm, (tg, nm))
            # 缩到很小：同一位置多个点 → 弹列表
            cur(pg, "r.map.jumpTo({zoom:5})"); pg.wait_for_timeout(700)
            cen = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.kind==='n'});return [m[0].px,m[0].py,m.length]})()")
            sr = stage_rect(pg); pg.mouse.click(sr['l'] + cen[0], sr['t'] + cen[1]); pg.wait_for_timeout(500)
            pk = pg.evaluate("(function(){return [].slice.call(document.querySelectorAll('.rm-pi')).map(function(b){return b.textContent})})()")
            check('R9d 点同一位置的多个站：弹出列表让人选（%d 项）' % len(pk), len(pk) >= 2, pk)
            if len(pk) >= 2:
                pg.click('.rm-pi >> nth=1'); pg.wait_for_timeout(500)
                cs = cur(pg, 'r.cur')
                check('R9e 从列表里选第 2 项：选中的就是它（cur=%s）' % cs, cs and cs >= 1, cs)
        c.close()
        # 总览里同一位置的天合并成范围、点得到
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/hss1a/', 800)
        pg.click('.mapgo'); ready(pg); tiles(pg); pg.wait_for_timeout(700)
        lab = cur(pg, "r.marks.filter(function(m){return m.badge&&m.el.style.visibility!=='hidden'}).map(function(m){return m.el.textContent})")
        check('R9f 总览里位置相同的几天合并成一个章并写范围，不再是无编号的黑点（%s）' % lab, any(('–' in x or '·' in x) for x in lab), lab)
        shot(pg, 'r9_overview_merged.png')
        mg = cur(pg, "(function(){var m=r.marks.filter(function(m){return m.badge&&m.el.style.visibility!=='hidden'&&/[–·]/.test(m.el.textContent)})[0];return m?[m.px,m.py]:null})()")
        if mg:
            sr = stage_rect(pg); pg.mouse.click(sr['l'] + mg[0], sr['t'] + mg[1]); pg.wait_for_timeout(500)
            pk = pg.evaluate("(function(){return [].slice.call(document.querySelectorAll('.rm-pi')).map(function(b){return b.textContent})})()")
            check('R9g 点合并的天数章：弹列表列出被合并的每一天（%d 项）' % len(pk), len(pk) >= 2 and all(re.match(r'^第 \d+ 天', x) for x in pk), pk)
            if pk:
                pg.click('.rm-pi >> nth=1'); pg.wait_for_timeout(500)
                check('R9h 选其中一天：切到那一天', cur(pg, 'r.sel') >= 1, cur(pg, 'r.sel'))
        else:
            check('R9g 点合并的天数章', False, '没有合并的章')
        c.close()

    # ─────────── R12 点按范围
    with guard('R12'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        open_day(pg, 2); pg.click('.rm-fsb'); pg.wait_for_timeout(900)
        cur(pg, "r.map.jumpTo({zoom:r.map.getZoom()+1.5,center:[r.days[r.sel].pts[0].ll[1],r.days[r.sel].pts[0].ll[0]]})"); pg.wait_for_timeout(700)      # 放大一点，让标记散开
        ms = cur(pg, "r.marks.filter(function(m){return m.kind==='n'}).map(function(m){return[m.n,m.px,m.py]})")
        allm = cur(pg, "r.marks.filter(function(m){return m.kind}).map(function(m){return[m.kind+(m.n||''),m.px,m.py]})")      # 住、灰点也算邻居
        iso = [m for m in ms if all(o[0] == 'n' + str(m[0]) or abs(o[1] - m[1]) + abs(o[2] - m[2]) > 70 for o in allm) and 30 < m[1] < 360 and 60 < m[2] < 700]
        got = []
        for n_, x_, y_ in iso[:2]:
            sr = stage_rect(pg)
            for dx, dy in ((18, 0), (0, -18), (-15, 15)):
                cur(pg, "(r.cur=0,0)"); pg.mouse.click(sr['l'] + x_ + dx, sr['t'] + y_ + dy); pg.wait_for_timeout(350)
                got.append((n_, dx, dy, cur(pg, 'r.cur')))
                sr = stage_rect(pg)
        check('R12 点在标记中心 ≤22px 的范围内都点中这个标记（%s）' % got[:6], bool(got) and all(g[3] == g[0] for g in got), got)
        c.close()

    # ─────────── R11 “调整”点击区
    with guard('R11'):
        c = mk(br); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/', 600)
        h = pg.evaluate(HIT, pg.query_selector('#d1 .r .s .adj'))
        check('R11 每站的“调整”小标签点击区 ≥44×44（实测 %s×%s，视觉 %s×%s）' % (h and h['w'], h and h['h'], h and h['bw'], h and h['bh']), bool(h) and h['w'] >= 44 and h['h'] >= 44, h)
        c.close()
    br.close()

env.finish('路线地图第二轮')
