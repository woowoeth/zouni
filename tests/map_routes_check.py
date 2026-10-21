#!/usr/bin/env python3
"""路线地图 · 各类线路“像真实用户一样走一遍”（2026-10-20，用户手测长线 g318 总览挤成一团、天标签条超出屏幕后补的）。会红。

之前的地图判据（map_app / map_anchor / map_polish）几乎都只开 xa3（3 天国内短线）。这份把长线、105 天线、国外线、h* 线都加进来，
每条线：开总览 → 切天（含靠后的天）→ 点站 → 在行程里看 → 关闭回到原位 → 放大缩小 → 暗色。

用法（项目根目录；先 bash build/pipe.sh build/site_ml，或改了 site_src 后 python3 tools/build_site.py build/site_ml）：
    python3 tests/map_routes_check.py build/site_ml [--shots DIR] [--only R1,R2] [--inject 名字]      # 反向自检：每个名字必须变红

R1  长线总览（g318 14 天 / xl3a 24 天 / xbdh30 30 天 / xb96a 105 天）：有一条首尾相连的主线（粗实线 + 行进方向箭头）；地名方块的落脚点在每天结束的地方（2026-10-21 D34：方块从数字章改成地名，合并 / 避让 / 点击见 map_names_check.py）；
    可见的名字方块互不重叠、不压控件；每个落脚城镇有方块或小点；取景贴着路线包围盒（不留大片空白）且居中
R2  天标签条（天数 ≥ 10）：标签紧凑（≥40 宽、44 高）；选中某天（点标签 / 点图上的章 / 从页面“本日地图”进 / 站点卡回当天）后选中的那个完整落在条内；
    两头还有内容时边上渐隐（有遮罩）；点“全程”回到最左
R3  各类线路遍历（g318 / xb96a / xl3a / xv612a / tk4 / bkk3 / hsg1 / hjgs1 / xa3）：每天的站都在可视区内且不被控件盖住、标签条里选中的在视野；
    点站出卡片（名字完整、前后车程不是“去车站或机场…”、博物馆有“博物馆”标）；“在行程里看”关地图并让那一行进视野；× / 返回键关闭回到原来的滚动位置
R4  105 天线：切天到画面稳定 < 150ms（取 4 天的中位数）
R5  375 / 414 宽、横屏：长线总览同样不重叠、取景贴合；暗色：序号章（字色 / 底色）对比度 ≥ 3
R6  国外线：加载进地图的样式里地名有“拉丁字母兜底”（name:latin 在本地名 name 之前）；脚本慢的时候起步壳立刻有（加载中提示 + 标签条 + 长线的主线），选中的天已滚进标签条
R8  存图：长线总览存下来的图上有主线（不是每天各画各的）
R7  站名很长（xa3 “秦始皇帝陵博物院 · 兵马俑”、xb96a “乌拉特后旗巴音宝力格镇”）：卡片里不从中间截成省略号
"""
import json, math, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(ROOT, 'build', 'site')

INJ = {
    # R3
    'tap_gray': ('assets/routemap.js', "if (real.length && real.length < c.length) c = real;", ""),      # 灰色的前后天标记和这一天的站挤在一起时也弹“选哪个”（R3 xb96a 第 2 天第 1 站）
    # R1
    'trunk_off': ('assets/routemap.js', "if (LG && inst.trunk && inst.trunk.length > 1) paintTrunk(inst, c, dbg);", ""),                                      # 不画主线
    'long_off': ('assets/routemap.js', "var LONG_N = 8;", "var LONG_N = 9999;"),                                                                         # 长线总览回到老样子（每天第一站的章，各画各的）
    'no_cull': ('assets/routemap.js', "if (inst.sel < 0) { cullNames(inst); sights(inst); }", "if (inst.sel < 0) { inst.marks.forEach(function (m) { if (m.badge) { m.el.style.transform = 'translate(' + Math.round(m.px) + 'px,' + Math.round(m.py) + 'px)'; m.el.style.visibility = 'visible'; m.box = null; } }); }"),      # 名字方块不避让（全叠在落脚点上）
    'at_first': ('assets/routemap.js', "at = LG ? (anchorOf(d) || d.pts[0].ll) : d.pts[0].ll, g = null", "at = d.pts[0].ll, g = null"),      # 方块放在每天第一站，不在落脚点
    'fit_loose': ('assets/routemap.js', "var pad = { t: inst.st + 56, b: 28, l: 40, r: 40 }", "var pad = { t: inst.st + 56, b: 28, l: 130, r: 130 }"),     # 取景留一大圈边
    'thin_trunk': ('assets/routemap.js', "c.globalAlpha = dim ? .3 : .95; c.strokeStyle = col; c.lineWidth = dim ? 2 : 3;", "c.globalAlpha = dim ? .3 : .95; c.strokeStyle = col; c.lineWidth = dim ? 2 : 1;"),   # 主线细成 1px（总览看不清）
    # R2
    'tab_noscroll': ('assets/routemap.js', "    if (!on || !tb.clientWidth) return;\n    var m = tb.scrollWidth", "    return;\n    var m = tb.scrollWidth"),                                    # 选中的标签不自动滚进视野
    'tab_nofade': ('assets/routemap.js', "if (tb.className !== c) tb.className = c;", "if (tb.className !== inst.tabsCls) tb.className = inst.tabsCls;"),     # 没有渐隐提示
    'xl_off': ('assets/routemap.js', "(n >= 10 ? ' xl' : '')", "''"),                                                                                      # 标签不收紧
    # R3
    'leg_tail': ('assets/routemap.js', "function legOk(l) { return !!l && !!l.txt && !/提前|去车站|前往机场|开车回城/.test(l.txt); }", "function legOk(l) { return !!l; }"),   # 卡片把“去车站或机场…”当成距下一站
    # R6
    'shell_noscroll': ('assets/site.js', "tbs.scrollLeft=Math.max(0,tbs.scrollLeft+(r1.left-r0.left)-(tbs.clientWidth-r1.width)/2)", "0"),                 # 起步壳里选中的标签不滚进视野
    'shell_notrunk': ('assets/site.js', "if(lg){for(i=1;i<tr.length;i++){", "if(false){for(i=1;i<tr.length;i++){"),                                          # 起步壳里长线没有主线
    # R8
    'save_old': ('assets/routemap.js', "var LGO = isLong(inst) && inst.sel < 0;", "var LGO = false;"),                                                           # 存图还是每天各画各的（没有主线）
    # R7
    'c3_nowrap': ('assets/site.css', [".rm .rm-c3{margin:2px 0 0;display:flex;flex-wrap:wrap;", ".rm .rm-c3 span{overflow:hidden;text-overflow:ellipsis}"], [".rm .rm-c3{margin:2px 0 0;display:flex;flex-wrap:nowrap;", ".rm .rm-c3 span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}"]),   # 前后车程又回到一行省略
    'name_clip': ('assets/routemap.js', "(String(p.name).length > 9 ? ' rm-cn2' : '')", "''"),                                                           # 长名字不缩不换行，截成省略号
}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
def want(k): return ONLY is None or k in ONLY


def stub(c):
    def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
    def pbf(r): r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
    def other(r):
        if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
        elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


def mk(br, w=390, h=844, dark=False):
    c = new_ctx(br, None, w=w, h=h, dark=dark); stub(c); return c


def ready(pg, t=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=t)
def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


def open_ov(pg):
    pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})")
    y = pg.evaluate("scrollY"); pg.click('.mapgo'); ready(pg); pg.wait_for_timeout(900); return y


def open_day(pg, n):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    y = pg.evaluate("scrollY"); pg.click('#d%d .rm-open' % n); ready(pg); pg.wait_for_timeout(900); return y


def route(br, rid, w=390, h=844, dark=False):
    c = mk(br, w, h, dark); pg = new_page(env, c); goto(env, pg, '/trip/%s/' % rid, 400); return c, pg


def last_btn_day(pg):      # 页面里最后一个有“本日地图”入口的天（不足 2 个有坐标的站的天没有入口）
    return pg.evaluate("(function(){var a=[].slice.call(document.querySelectorAll('section.day')),k=0;a.forEach(function(s,i){if(s.querySelector('.rm-open'))k=i+1});return k})()")


def open_sel(pg):
    return pg.evaluate("document.body.classList.contains('rmap-on')")


# 总览几何：长线主线的屏幕点、章盒子、可用区
OVG = """(function(){var z=ZRM.cur(),st=z.stage.getBoundingClientRect(),n=z.days.length;
 function R(e){var r=e.getBoundingClientRect();return {l:r.left-st.left,t:r.top-st.top,r:r.right-st.left,b:r.bottom-st.top}}
 var bd=[],all=[];
 z.marks.forEach(function(m){ if(!m.badge) return; var e=m.el, vis=e.style.visibility!=='hidden', i=e.firstElementChild, r=R(i); all.push({day:m.day,vis:vis,n:(m.days||[]).length,px:m.px,py:m.py,ll:m.ll}); if(vis) bd.push({day:m.day,txt:i.textContent,box:r,n:(m.days||[]).length,px:m.px,py:m.py}) });
 var tp=(z.trunk||[]).map(function(t){var q=z.view.project(t.ll);return [q.x,q.y]});
 var ctrl=z.ctrl.map(function(c){return {l:c.l,t:c.t,r:c.r,b:c.b}});
 var dbg=z.dbg||{}; return {n:n,bd:bd,all:all,tp:tp,ctrl:ctrl,dbg:dbg,sw:z.sw,mh:z.mh,st:z.st,tl:(z.trunk||[]).length,cam:z.view.cam(),
   anchors:z.days.map(function(d){var a=d.ep||(d.pts.length?d.pts[d.pts.length-1].ll:null);return a}),marks:z.marks.filter(function(m){return m.badge}).map(function(m){return {ll:m.ll,day:m.day}})}})()"""


def ovg(pg): return pg.evaluate(OVG)
def overlap(a, b, pad=0): return a['l'] < b['r'] + pad and a['r'] > b['l'] - pad and a['t'] < b['b'] + pad and a['b'] > b['t'] - pad


def ov_checks(tag, g, rid):
    """总览（长线）的静态判据：主线 / 章位置 / 不重叠 / 取景贴合居中"""
    n = g['n']; d = g['dbg']
    check('%s 主线：落脚点连成 %d 段（≥ 天数一半 %d），线宽 %s、不透明 %s，行进箭头 %s 个' % (tag, g['tl'] - 1, n // 2, d.get('tlw'), d.get('talpha'), d.get('tarrows')),
          g['tl'] - 1 >= n // 2 and d.get('trunk', 0) >= n // 2 and d.get('tlw', 0) >= 2.5 and d.get('talpha', 0) >= .9 and d.get('tarrows', 0) >= 1, (g['tl'], d))
    bad_at = [m['day'] + 1 for m in g['marks'] if g['anchors'][m['day']] and (abs(g['anchors'][m['day']][0] - m['ll'][0]) > 1e-6 or abs(g['anchors'][m['day']][1] - m['ll'][1]) > 1e-6)]
    check('%s 名字方块的落脚点是这一堆第一天结束的地方（住的位置 / 最后一站），不在每天第一站（不对的天 %s）' % (tag, bad_at[:6]), not bad_at, bad_at[:6])
    hits = []
    for i, a in enumerate(g['bd']):
        for b in g['bd'][i + 1:]:
            if overlap(a['box'], b['box']): hits.append((a['txt'], b['txt']))
        for c in g['ctrl']:
            if overlap(a['box'], c): hits.append((a['txt'], 'ctrl'))
    check('%s 可见的章互不重叠、不压控件（%d 个章，重叠 %s）' % (tag, len(g['bd']), hits[:4]), not hits and len(g['bd']) >= 1, hits[:4])
    # 每个落脚城镇：名字方块看得见，或者（让开了）在落脚点上有一个小点——不会整个城镇从图上消失
    check('%s 每个落脚城镇都有标记：名字方块 %d 个看得见，其余 %d 个在落脚点上画了小点（小点共 %s 个 = 城镇数 %d）' % (tag, len(g['bd']), len(g['all']) - len(g['bd']), g['dbg'].get('dots'), len(g['all'])), g['dbg'].get('dots') == len(g['all']) and len(g['all']) >= 1, (g['dbg'].get('dots'), len(g['all'])))
    # 取景：主线包围盒要贴满可用区（左右各 40、上 st+56、下 28，再扣右侧控件列在下半屏的情况下不另算），并居中
    xs = [p[0] for p in g['tp']]; ys = [p[1] for p in g['tp']]
    if xs:
        aw = g['sw'] - 80; ah = g['mh'] - (g['st'] + 56) - 28
        fill = max((max(xs) - min(xs)) / aw, (max(ys) - min(ys)) / ah)
        cx = (max(xs) + min(xs)) / 2 - g['sw'] / 2; cy = (max(ys) + min(ys)) / 2 - (g['st'] + 56 + g['mh'] - 28) / 2
        check('%s 取景贴着路线包围盒（长边占可用区 %.0f%%，≥ 80%%），且居中（偏 %.0f / %.0f px，≤ 40）' % (tag, fill * 100, cx, cy), fill >= .8 and abs(cx) <= 40 and abs(cy) <= 40, (fill, cx, cy))
        inside = [i for i, p in enumerate(g['tp']) if p[0] < 4 or p[0] > g['sw'] - 4 or p[1] < g['st'] or p[1] > g['mh']]
        check('%s 主线每个落脚点都在屏幕里（出界 %s）' % (tag, inside[:5]), not inside, inside[:5])


def strip_state(pg):
    return pg.evaluate("""(function(){var z=ZRM.cur(),tb=z.tabs,on=tb.querySelector('.rm-tb.on'),r1=on.getBoundingClientRect(),r0=tb.getBoundingClientRect(),cs=getComputedStyle(tb);
      return {sl:tb.scrollLeft,sw:tb.scrollWidth,cw:tb.clientWidth,cls:tb.className,mask:cs.webkitMaskImage||cs.maskImage||'none',inview:r1.left>=r0.left-1&&r1.right<=r0.right+1,onTxt:on.textContent,sel:z.sel,
        widths:[].slice.call(tb.querySelectorAll('.rm-tb')).map(function(b){var r=b.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})}})()""")


MARKS_BAD = """(function(){var z=ZRM.cur(),bad=[];
  z.marks.forEach(function(m){ if(m.kind!=='n'&&m.kind!=='hm') return; var q=z.view.project(m.ll),h=18;
    if(q.x<h||q.x>z.sw-h||q.y<z.st+h||q.y>z.mh-h) bad.push([m.kind,m.n,Math.round(q.x),Math.round(q.y)]);
    else z.ctrl.forEach(function(c){ if(q.x+h>c.l&&q.x-h<c.r&&q.y+h>c.t&&q.y-h<c.b) bad.push(['ctrl',m.n]) }) });
  return bad})()"""
LONGS = [('g318', 14), ('xl3a', 24), ('xbdh30', 30), ('xb96a', 105)]
WALK = ['g318', 'xb96a', 'xl3a', 'xv612a', 'tk4', 'bkk3', 'hsg1', 'hjgs1', 'xa3']
if '--routes' in sys.argv:      # 只跑这几条线（排查 / 反向注入时省时间）
    _only = set(sys.argv[sys.argv.index('--routes') + 1].split(','))
    LONGS = [x for x in LONGS if x[0] in _only]; WALK = [x for x in WALK if x in _only]

with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()

    # ─────────── R1 长线总览
    if want('R1'):
        for rid, nd in LONGS:
            with guard('R1 ' + rid):
                c, pg = route(br, rid); T = Touch(c, pg); open_ov(pg); g = ovg(pg)
                check('R1 %s 天数 %d' % (rid, nd), g['n'] == nd, g['n'])
                ov_checks('R1 %s' % rid, g, rid); shot(pg, 'r1_%s.png' % rid)
                # （放大后冒出来的名字、点名字 / 点小点：见 tests/map_names_check.py N4 / N5）
                c.close()

    # ─────────── R2 天标签条
    if want('R2'):
        for rid, nd in LONGS:
            with guard('R2 ' + rid):
                c, pg = route(br, rid); T = Touch(c, pg); open_ov(pg); s0 = strip_state(pg)
                wd = s0['widths']; avg = sum(w for w, h in wd) / len(wd)
                check('R2 %s 标签紧凑：%d 个标签最窄 %d、最矮 %d（≥40 宽、≥44 高），平均宽 %.0f（≤ 43，且带 xl 类）' % (rid, len(wd), min(w for w, h in wd), min(h for w, h in wd), avg), min(w for w, h in wd) >= 40 and min(h for w, h in wd) >= 44 and avg <= 43 and ' xl' in s0['cls'], wd[:5])
                check('R2 %s 全程态：在最左，右边还有标签 → 右侧渐隐（类 %s，遮罩 %s），左侧不渐隐' % (rid, s0['cls'], s0['mask'][:30]), s0['sl'] < 2 and ' fr' in s0['cls'] and ' fl' not in s0['cls'] and s0['mask'] not in ('none', ''), s0)
                k = nd - 1
                # 路 1：点标签（先把条划到最右，像用户一样）
                pg.evaluate("ZRM.cur().tabs.scrollLeft=99999"); pg.wait_for_timeout(200); s1 = strip_state(pg)
                check('R2 %s 划到最右：左侧渐隐、右侧不渐隐（类 %s）' % (rid, s1['cls']), ' fl' in s1['cls'] and ' fr' not in s1['cls'], s1['cls'])
                pg.evaluate("ZRM.cur().tabs.scrollLeft=%d" % (s1['sw'] // 2 - s1['cw'] // 2)); pg.wait_for_timeout(200); s1m = strip_state(pg)
                check('R2 %s 划到中间：两侧都渐隐（类 %s）' % (rid, s1m['cls']), ' fl' in s1m['cls'] and ' fr' in s1m['cls'], s1m['cls'])
                pg.locator('.rm-tb[data-i="%d"]' % k).click(); pg.wait_for_timeout(900); s2 = strip_state(pg)
                check('R2 %s 点“%d”标签：选中的完整在条内（sel %s，在视野 %s）' % (rid, nd, s2['sel'], s2['inview']), s2['sel'] == k and s2['inview'], s2)
                shot(pg, 'r2_%s_last.png' % rid)
                # 路 2：回全程 → 回最左
                pg.locator('.rm-tb[data-i="-1"]').click(); pg.wait_for_timeout(900); s3 = strip_state(pg)
                check('R2 %s 点“全程”：标签条回到最左（scrollLeft %d）、全程在视野' % (rid, s3['sl']), s3['sl'] < 2 and s3['inview'] and s3['sel'] == -1, s3)
                # 路 3：点图上的章 / ZRM.selectDay（中段的天）
                mid = nd // 2
                pg.evaluate("ZRM.selectDay(%d)" % mid); pg.wait_for_timeout(900); s4 = strip_state(pg)
                check('R2 %s 从图上选第 %d 天：选中的在条内' % (rid, mid + 1), s4['sel'] == mid and s4['inview'], s4)
                # 路 4：点站 → 卡片（条隐藏）→ 回当天：条回来时选中的仍在视野
                pg.evaluate("ZRM.select(1)"); pg.wait_for_timeout(700); pg.evaluate("document.querySelector('.rm-cb').click()"); pg.wait_for_timeout(900); s5 = strip_state(pg)
                check('R2 %s 点站出卡片再“回当天”：选中的天还在条内' % rid, s5['sel'] == mid and s5['inview'], s5)
                c.close()
                # 路 5：从页面第 N 天的“本日地图”进（起步壳 → 接手），靠后的天
                c, pg = route(br, rid); kd = last_btn_day(pg); open_day(pg, kd); s6 = strip_state(pg)
                check('R2 %s 从页面第 %d 天“本日地图”进（靠后的天）：选中的在条内（sel %s）' % (rid, kd, s6['sel']), s6['sel'] == kd - 1 and s6['inview'] and kd >= nd - 2, s6)
                c.close()

    # ─────────── R3 各类线路遍历
    if want('R3'):
        for rid in WALK:
            with guard('R3 ' + rid):
                c, pg = route(br, rid); T = Touch(c, pg); y0 = open_ov(pg)
                n = pg.evaluate("ZRM.cur().days.length")
                days = list(range(n)) if n <= 16 else sorted({0, 1, n // 3, n // 2, n - 2, n - 1})
                bad_pos, bad_tab, bad_title = [], [], []
                for d in days:
                    pg.evaluate("ZRM.selectDay(%d)" % d); pg.wait_for_timeout(750)
                    r = pg.evaluate("""(function(){var z=ZRM.cur(),bad=[];
                      z.marks.forEach(function(m){ if(m.kind!=='n'&&m.kind!=='hm') return; var q=z.view.project(m.ll),h=18;
                        if(q.x<h||q.x>z.sw-h||q.y<z.st+h||q.y>z.mh-h) bad.push([m.kind,m.n,Math.round(q.x),Math.round(q.y)]);
                        else z.ctrl.forEach(function(c){ if(q.x+h>c.l&&q.x-h<c.r&&q.y+h>c.t&&q.y-h<c.b) bad.push(['ctrl',m.n]) }) });
                      var tb=z.tabs,on=tb.querySelector('.rm-tb.on'),r1=on.getBoundingClientRect(),r0=tb.getBoundingClientRect(),ld=z.root.querySelector('.rm-ld b'),ln=z.root.querySelector('.rm-ln');
                      return {bad:bad,tabIn:r1.left>=r0.left-1&&r1.right<=r0.right+1,tl:ld?ld.getClientRects().length:0,over:ld?ld.scrollWidth>ld.clientWidth+1:false,lnTxt:ln?ln.textContent:''}})()""")
                    if r['bad']: bad_pos.append((d + 1, r['bad'][:2]))
                    if not r['tabIn']: bad_tab.append(d + 1)
                    if re.search(r'分 \d+ 小时', r['lnTxt']): bad_title.append((d + 1, r['lnTxt']))
                check('R3 %s %d 天（查 %d 天）：每天的站 / 住都在可视区内且不被控件盖住（问题 %s）' % (rid, n, len(days), bad_pos[:3]), not bad_pos, bad_pos[:3])
                check('R3 %s 每天选中后标签条里选中的在视野（不在的天 %s）' % (rid, bad_tab[:5]), not bad_tab, bad_tab[:5])
                check('R3 %s 每天信息条里的数字没有“分 小时”颠倒（%s）' % (rid, bad_title[:2]), not bad_title, bad_title[:2])
                # 回到总览 → 点第一个有站的天的第一站出卡片
                pg.evaluate("ZRM.selectDay(%d)" % days[min(1, len(days) - 1)]); pg.wait_for_timeout(800)
                pt = pg.evaluate("(function(){var z=ZRM.cur(),d=z.days[z.sel],m=z.marks.filter(function(m){return m.kind==='n'&&m.n===1})[0];return m?{x:m.px,y:m.py,name:d.pts[0].name}:null})()")
                if pt:
                    T.tap(pt['x'], pt['y']); pg.wait_for_timeout(1100)
                    cd = pg.evaluate("""(function(){var z=ZRM.cur(),c=document.querySelector('.rm-card[data-n="1"]'); if(!c) return null; var nm=c.querySelector('.rm-cname'),btn=[].slice.call(c.querySelectorAll('button')).map(function(b){var r=b.getBoundingClientRect();return [b.textContent,Math.round(r.height)]});
                      return {mode:z.mode,name:nm.textContent,clipW:nm.scrollWidth>nm.clientWidth+1,clipH:nm.scrollHeight>nm.clientHeight+1,legs:(c.querySelector('.rm-c3 span')||{}).textContent||'',btn:btn,tags:[].slice.call(c.querySelectorAll('em')).map(function(e){return e.textContent}),w:c.scrollWidth,cw:c.clientWidth,
                      tall:c.scrollHeight>c.clientHeight+1,legClip:(function(){var s=c.querySelector('.rm-c3 span'),c3=c.querySelector('.rm-c3');return !!s&&(s.scrollWidth>s.clientWidth+1||c3.scrollHeight>c3.clientHeight+1)})()}})()""")
                    check('R3 %s 点第 1 站“%s”出卡片：有名字、两个按钮 ≥44 高、卡片内没有横向溢出（%s）' % (rid, pt['name'][:12], (cd or {}).get('btn')), bool(cd) and cd['name'] and all(h >= 44 for t_, h in cd['btn'] if '回当天' not in t_ and t_) and cd['w'] <= cd['cw'] + 1, cd)
                    if cd: check('R3 %s 卡片装得下：高度不超（%s）、前后车程文字没被省略号截掉（%s）' % (rid, not cd['tall'], not cd['legClip']), not cd['tall'] and not cd['legClip'], cd)
                    if cd: check('R3 %s 卡片里“距…站”不是“去车站或机场”之类的行程尾巴（%s）' % (rid, cd['legs']), not re.search(r'提前|去车站|前往机场|开车回城|分 \d+ 小时', cd['legs']), cd['legs'])
                    # 在行程里看 → 地图关了，页面那一行进视野
                    pg.locator('.rm-card[data-n="1"] .rm-adj2').click(); pg.wait_for_timeout(1200)
                    on = open_sel(pg); row = pg.evaluate("(function(){var f=document.querySelector('.r.flash'),r=f&&f.getBoundingClientRect();return r?{t:r.top,b:r.bottom,h:innerHeight}:null})()")
                    check('R3 %s“在行程里看 ›”：地图关闭、页面那一行高亮并进视野（%s）' % (rid, row), not on and bool(row) and 0 <= row['t'] and row['b'] <= row['h'], (on, row))
                else:
                    check('R3 %s 第 %d 天有可点的第 1 站' % (rid, days[1] + 1), False, pt)
                c.close()
                c, pg = route(br, rid); open_ov(pg)      # 最后一天的最后一站：它后面那一格是“去车站或机场…”，卡片不能把它写成“距下一站”
                lp = pg.evaluate("(function(){var z=ZRM.cur(),k=z.days.length-1;while(k>0&&!z.days[k].pts.length)k--;return [k,z.days[k].pts.length]})()")
                pg.evaluate("ZRM.selectDay(%d)" % lp[0]); pg.wait_for_timeout(700); pg.evaluate("ZRM.select(%d)" % lp[1]); pg.wait_for_timeout(900)
                lg = pg.evaluate("(function(){var c=document.querySelector('.rm-card[data-n=\"%d\"]');return c?(c.querySelector('.rm-c3 span')||{}).textContent||'':null})()" % lp[1])
                check('R3 %s 最后一天最后一站的卡片：不把行程尾巴写成“距下一站”（%s）' % (rid, lg), lg is not None and not re.search(r'提前|去车站|前往机场|开车回城|分 \d+ 小时', lg), lg)
                c.close()
                if rid in ('hsg1', 'hjgs1', 'xa3'):      # 博物馆站的卡片：有“博物馆”小标、有一句话、名字完整
                    c, pg = route(br, rid); open_ov(pg)
                    mu = pg.evaluate("(function(){var z=ZRM.cur(),r=null;z.days.forEach(function(d,i){d.pts.forEach(function(p){if(!r&&p.mk==='mu')r=[i,p.n,p.name]})});return r})()")
                    if mu:
                        pg.evaluate("ZRM.selectDay(%d)" % mu[0]); pg.wait_for_timeout(700); pg.evaluate("ZRM.select(%d)" % mu[1]); pg.wait_for_timeout(1000)
                        cd = pg.evaluate("(function(){var c=document.querySelector('.rm-card[data-n=\"%d\"]');return c?{tags:[].slice.call(c.querySelectorAll('em')).map(function(e){return e.textContent}),one:(c.querySelector('.rm-c1')||{}).textContent||'',leg:(c.querySelector('.rm-c3 span')||{}).textContent||''}:null})()" % mu[1])
                        check('R3 %s 博物馆站“%s”的卡片：有“博物馆”小标、有一句话（%s）、有车程（%s）' % (rid, mu[2][:10], (cd or {}).get('one', '')[:14], (cd or {}).get('leg', '')[:16]), bool(cd) and '博物馆' in cd['tags'] and len(cd['one']) >= 6 and bool(cd['leg']), cd)
                    else: check('R3 %s 有博物馆站可查' % rid, False, mu)
                    c.close()
                # 关闭回到原来的滚动位置：从页面深处（最后一天）开地图 → × ；再开 → 返回键
                c, pg = route(br, rid); T = Touch(c, pg); nlast = last_btn_day(pg); y1 = open_day(pg, nlast)
                pg.click('.rm-x'); pg.wait_for_timeout(900); y2 = pg.evaluate("scrollY")
                check('R3 %s 从第 %d 天（页面深处 y=%d）开地图，× 关闭回到原位（%d，差 %d ≤ 3）' % (rid, nlast, y1, y2, abs(y2 - y1)), abs(y2 - y1) <= 3 and not open_sel(pg), (y1, y2))
                y3 = open_day(pg, nlast); pg.go_back(); pg.wait_for_timeout(1000); y4 = pg.evaluate("scrollY")
                check('R3 %s 返回键关闭回到原位（%d → %d，差 %d ≤ 3）' % (rid, y3, y4, abs(y4 - y3)), abs(y4 - y3) <= 3 and not open_sel(pg), (y3, y4))
                # 放大缩小
                y5 = open_ov(pg); z0 = pg.evaluate("ZRM.cur().view.zoom()"); pg.click('.rm-zi'); pg.wait_for_timeout(500); z1 = pg.evaluate("ZRM.cur().view.zoom()"); pg.click('.rm-zo'); pg.click('.rm-zo'); pg.wait_for_timeout(500); z2 = pg.evaluate("ZRM.cur().view.zoom()")
                check('R3 %s +/−：放大 +%.1f，缩小 %.1f（+≥0.8，−≥0.8；到头会置灰）' % (rid, z1 - z0, z1 - z2), z1 - z0 >= .8 and (z1 - z2 >= .8 or pg.evaluate("document.querySelector('.rm-zo').disabled")), (z0, z1, z2))
                c.close()

    # ─────────── R4 105 天线切天速度
    if want('R4'):
        with guard('R4'):
            c, pg = route(br, 'xb96a'); open_ov(pg); ts = []
            for d in (3, 40, 70, 100):
                ts.append(pg.evaluate("new Promise(function(r){var t=performance.now();ZRM.selectDay(%d);requestAnimationFrame(function(){requestAnimationFrame(function(){r(performance.now()-t)})})})" % d)); pg.wait_for_timeout(700)
            ts.sort(); med = (ts[1] + ts[2]) / 2
            check('R4 105 天线：选天到下一帧画好，中位数 %.0f ms（< 150）；各次 %s' % (med, [round(x) for x in ts]), med < 150, ts)
            ts2 = []
            for d in (-1, 50, -1, 60):
                ts2.append(pg.evaluate("new Promise(function(r){var t=performance.now();ZRM.selectDay(%d);requestAnimationFrame(function(){requestAnimationFrame(function(){r(performance.now()-t)})})})" % d)); pg.wait_for_timeout(700)
            check('R4 105 天线：回全程 / 再选天同样 < 150ms（%s）' % [round(x) for x in ts2], sorted(ts2)[1] < 150, ts2)
            c.close()

    # ─────────── R5 其它尺寸 / 暗色
    if want('R5'):
        for (w, h, tag) in ((375, 812, '375'), (414, 896, '414'), (844, 390, '横屏')):
            for rid in ('g318', 'xl3a'):
                with guard('R5 %s %s' % (tag, rid)):
                    c, pg = route(br, rid, w, h); open_ov(pg); g = ovg(pg); ov_checks('R5 %s %s' % (tag, rid), g, rid)
                    s = strip_state(pg); pg.evaluate("ZRM.selectDay(%d)" % (g['n'] - 2)); pg.wait_for_timeout(900); s2 = strip_state(pg)
                    bd = pg.evaluate(MARKS_BAD)
                    check('R5 %s %s 靠后的天里每个站 / 住都在可视区内、不被控件盖住（%s）' % (tag, rid, bd[:3]), not bd, bd[:3])
                    check('R5 %s %s 靠后的天（第 %d 天）选中后标签在条内' % (tag, rid, g['n'] - 1), s2['inview'] and s2['sel'] == g['n'] - 2, s2)
                    shot(pg, 'r5_%s_%s.png' % (tag, rid)); c.close()
        for dark in (False, True):
            with guard('R5 dark %s' % dark):
                c, pg = route(br, 'g318', dark=dark); open_ov(pg)
                cr = pg.evaluate("""(function(){function P(s){var m=s.match(/[\\d.]+/g).map(Number);return m.slice(0,3)}function L(c){var a=c.map(function(v){v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)});return .2126*a[0]+.7152*a[1]+.0722*a[2]}
                  var z=ZRM.cur(),o=[];z.marks.forEach(function(m){if(!m.badge)return;var i=m.el.firstElementChild,cs=getComputedStyle(i),f=P(cs.color),b=P(cs.backgroundColor),l1=L(f),l2=L(b),r=(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05);o.push([m.day+1,+r.toFixed(2)])});return o})()""")
                lo = [x for x in cr if x[1] < 3]
                check('R5 %s 模式：长线总览序号章字色 / 底色对比度都 ≥ 3（最低 %.2f，不够的天 %s）' % ('暗色' if dark else '浅色', min(x[1] for x in cr), lo[:4]), not lo and len(cr) >= 10, lo[:4])
                shot(pg, 'r5_%s.png' % ('dark' if dark else 'light')); c.close()

    # ─────────── R6 国外线样式 + 起步壳
    if want('R6'):
        for rid in ('xv612a', 'tk4', 'bkk3'):
            with guard('R6 ' + rid):
                c, pg = route(br, rid); open_ov(pg); pg.wait_for_timeout(800)
                st = pg.evaluate("""(function(){var z=ZRM.cur(),m=z.map; if(!m) return null; var o={n:0,bad:[]};m.getStyle().layers.forEach(function(l){var tf=l.layout&&l.layout['text-field'];if(tf&&l.type==='symbol'&&l.id.indexOf('shield')<0&&l.layout.visibility!=='none'){o.n++;var s=JSON.stringify(tf),a=s.indexOf('name:latin'),b=s.lastIndexOf('"name"]');if(a<0||b<0||a>b)o.bad.push(l.id)}});return o})()""")
                check('R6 %s 国外线加载进地图的样式：%s 个标注图层地名都有拉丁字母兜底（name:latin 在 name 之前；不合格 %s）' % (rid, st and st['n'], st and st['bad'][:3]), bool(st) and st['n'] >= 8 and not st['bad'], st)
                c.close()
        with guard('R6 shell'):
            env.delays['routemap.js'] = 2.5
            c, pg = route(br, 'g318'); pg.evaluate("document.querySelector('#d12 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d12 .rm-open'); pg.wait_for_timeout(500)
            sh = pg.evaluate("""(function(){var r=document.querySelector('.rm-boot'); if(!r) return null; var tb=r.querySelector('.rm-tabs'),on=tb.querySelector('.rm-tb.on'),r1=on.getBoundingClientRect(),r0=tb.getBoundingClientRect(),ld=r.querySelector('.rm-load');
              return {load:ld&&getComputedStyle(ld).display!=='none'&&ld.textContent,tabs:tb.querySelectorAll('.rm-tb').length,inview:r1.left>=r0.left-1&&r1.right<=r0.right+1,on:on.textContent,lines:r.querySelectorAll('.rm-bl').length,xl:/\\bxl\\b/.test(tb.className)}})()""")
            check('R6 点开后 0.5 秒（脚本还在路上）：起步壳已显示、有“加载中”提示、标签条 %s 个、选中的“12”在条内（%s）、紧凑（xl %s）' % (sh and sh['tabs'], sh and sh['inview'], sh and sh['xl']), bool(sh) and bool(sh['load']) and sh['tabs'] == 15 and sh['inview'] and sh['xl'], sh)
            pg.wait_for_timeout(500); c.close(); env.delays.clear()
            env.delays['routemap.js'] = 2.5
            c, pg = route(br, 'g318'); pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); pg.wait_for_timeout(500)
            sh = pg.evaluate("(function(){var r=document.querySelector('.rm-boot');return r?{lines:r.querySelectorAll('.rm-bl').length,badges:r.querySelectorAll('.rm-bm:not(.rm-bn)').length}:null})()")
            check('R6 g318 总览的起步壳：长线只画主线（%s 段）、不画每天的数字章（%s 个；起点 / 终点的地名方块不算，见 map_names_check N8）' % (sh and sh['lines'], sh and sh['badges']), bool(sh) and sh['lines'] >= 7 and sh['badges'] == 0, sh)
            shot(pg, 'r6_shell.png'); pg.wait_for_timeout(500); c.close(); env.delays.clear()

    # ─────────── R7 长站名
    if want('R7'):
        with guard('R7'):
            c, pg = route(br, 'xa3'); T = Touch(c, pg); open_day(pg, 2)
            pg.evaluate("ZRM.select(1)"); pg.wait_for_timeout(1000)
            cd = pg.evaluate("(function(){var c=document.querySelector('.rm-card[data-n=\"1\"]'),nm=c.querySelector('.rm-cname'),r=nm.getBoundingClientRect(),cb=c.querySelector('.rm-cb').getBoundingClientRect();return {t:nm.textContent,clipH:nm.scrollHeight>nm.clientHeight+1,clipW:nm.scrollWidth>nm.clientWidth+1,h:r.height,cls:nm.className,fs:getComputedStyle(nm).fontSize,over:r.right>cb.left+1}})()")
            check('R7 xa3 第 2 天第 1 站“%s”（%d 字）：卡片里完整显示（不省略、不压到右边按钮；%s）' % (cd['t'], len(cd['t']), cd), not cd['clipH'] and not cd['clipW'] and not cd['over'] and cd['h'] <= 44, cd)
            c3 = pg.evaluate("(function(){var c=document.querySelector('.rm-card[data-n=\"1\"]'),s=c.querySelector('.rm-c3 span'),c3=c.querySelector('.rm-c3');return {t:s.textContent,tags:[].slice.call(c3.querySelectorAll('em')).length,clip:s.scrollWidth>s.clientWidth+1||c3.scrollHeight>c3.clientHeight+1,tall:c.scrollHeight>c.clientHeight+1,h:c3.clientHeight}})()")
            check('R7 xa3 同一张卡：%d 个小标签 + 前后车程“%s”放得下（两行以内，不省略；卡片不超高）' % (c3['tags'], c3['t'][:24]), c3['tags'] >= 1 and len(c3['t']) >= 20 and not c3['clip'] and not c3['tall'], c3)
            shot(pg, 'r7_longname.png'); c.close()
            c, pg = route(br, 'xb96a'); T = Touch(c, pg); open_day(pg, 66)
            pg.evaluate("ZRM.select(1)"); pg.wait_for_timeout(1000)
            cd = pg.evaluate("(function(){var c=document.querySelector('.rm-card[data-n=\"1\"]'),nm=c.querySelector('.rm-cname');return {t:nm.textContent,clipH:nm.scrollHeight>nm.clientHeight+1,clipW:nm.scrollWidth>nm.clientWidth+1}})()")
            check('R7 xb96a 第 66 天第 1 站“%s”（%d 字）：卡片里完整显示' % (cd['t'], len(cd['t'])), not cd['clipH'] and not cd['clipW'], cd)
            c.close()
    # ─────────── R8 存图（长线总览）
    if want('R8'):
        with guard('R8'):
            c, pg = route(br, 'g318'); open_ov(pg)
            seg = pg.evaluate("""(function(){var z=ZRM.cur(),T=z.trunk,best=null;for(var k=1;k<T.length;k++){var a=z.view.project(T[k-1].ll),b=z.view.project(T[k].ll),L=Math.hypot(a.x-b.x,a.y-b.y);if(!best||L>best.L)best={L:L,x:(a.x+b.x)/2,y:(a.y+b.y)/2,day:T[k].day}}return {x:best.x,y:best.y,day:best.day,sw:z.sw,vis:z.sh2-z.sheetH}})()""")
            pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=8000); pg.wait_for_timeout(400)
            px = pg.evaluate("""(function(seg){var im=document.querySelector('.rm-shot img'),cv=document.createElement('canvas');cv.width=im.naturalWidth;cv.height=im.naturalHeight;var x=cv.getContext('2d');x.drawImage(im,0,0);
              var k=im.naturalWidth/seg.sw,X=Math.round(seg.x*k),Y=Math.round(190+seg.y*k),d=x.getImageData(X-3,Y-3,7,7).data,bg=x.getImageData(20,cv.height-20,1,1).data,n=0;
              for(var i=0;i<d.length;i+=4){var dd=Math.abs(d[i]-bg[0])+Math.abs(d[i+1]-bg[1])+Math.abs(d[i+2]-bg[2]); if(dd>60)n++}
              return {w:im.naturalWidth,h:im.naturalHeight,ink:n,of:d.length/4}})(%s)""" % json.dumps(seg))
            check('R8 g318 长线总览存图：图宽 1080；最长一段主线中点（%d,%d）在图上有线（有色像素 %d/%d ≥ 40%%）' % (seg['x'], seg['y'], px['ink'], px['of']), px['w'] == 1080 and px['ink'] >= px['of'] * .4, px)
            shot(pg, 'r8_save.png'); c.close()
    br.close()

env.finish('map_routes_check')
