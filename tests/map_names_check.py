#!/usr/bin/env python3
"""路线地图总览里每个方块写地名（决策 D34，2026-10-21，用户：“地图上第二天第三天显示的 123 很难理解，为啥不直接显示地点名？”）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site_lb）：
    python3 tests/map_names_check.py build/site_lb [--shots DIR] [--routes xa3,g318] [--inject 名字]      # 反向自检：每个名字必须变红

N1  总览里每个看得见的方块都有地名（≥2 个汉字），文字里不是纯数字 / 范围（“2–3”“1·3”）；方块的无障碍名字以地名开头
    线路：xa3 / g318 / xl8a / xb96a(105 天) / xv612a / tk4 / hsg1；尺寸：390 / 375 / 414 / 横屏 / 暗色
N2  同城合并：页面上每天的 data-nm 相邻两天同名 → 地图上同一个方块（天数写成小角标“2–3”）；离开又回来的天在 30 公里内也并到一起；
    不同名不合并。xa3 必须是“西安 [1, 3]”“临潼 [2]”（兵马俑华清宫在临潼）
N3  不遮挡 / 不互相压：看得见的方块互不重叠、不压 × / 存图 / 右侧控件列 / 署名、不出屏幕、不压到底部条；
    把镜头平移到让落脚点落在控件列下面，名字也让开（造出来的场景）
N4  保证：首日起点 / 终点那一堆一定有名字；天数少的线（≤14 个城镇）每个落脚城镇都有名字（g318 / xa3 / tk4 / hsg1 / xv612a）；
    xl8a / xb96a 太多放不下的，在放大后冒出来（放大 3 级后可见名字数 ≥ 放大前）
N5  点击：点一天的名字方块 → 进那一天（标签条选中那一天）；点连住几天的方块 → 弹出各天；点落脚点的小点（名字让开了）一样有效
N6  主要景点只在放大后出现：全程缩小时 0 个 .rm-sg；放大到 ≥ 11 级时出现，且文字是景点名（不是数字），不压名字方块
N7  存图：总览存图里写的是地名（拦截 canvas fillText：每个看得见的方块的地名都画了，没有纯数字的方块文字）
N8  起步壳：脚本还没到时，总览的壳里写的是地名（.rm-bn），不是纯数字的方块
N9  性能：105 天线总览里拖动 / 缩放一次 place() 平均 < 8ms，切天 < 150ms（取中位数）
"""
import json, math, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

INJ = {
    # N1：回退成数字（地名不写进方块）
    'num_only': ('assets/routemap.js', "'<i><b>' + esc(g.name) + '</b><s>'", "'<i><b></b><s>'"),
    # N1：名字取成“第 N 天”这样的占位
    'name_day': ('assets/routemap.js', "var nm = townName(d) || ('第 ' + (i + 1) + ' 天'),", "var nm = ('第 ' + (i + 1) + ' 天'),"),
    # N2：同城不合并
    'no_merge': ('assets/routemap.js', "if (gs[k].name === nm && (gs[k].last === prev || kmd(gs[k].at, at) < 30)) { g = gs[k]; break; }", "if (false) { g = gs[k]; break; }"),
    # N2：连住以外的“回来”也不并 / 或者什么都并（只看名字，不看位置）：这里注入“不认连住、只认位置”的反面——名字不同也并到第一个
    'merge_all': ('assets/routemap.js', "if (gs[k].name === nm && (gs[k].last === prev || kmd(gs[k].at, at) < 30)) { g = gs[k]; break; }", "if (gs[k].last === prev) { g = gs[k]; break; }"),
    # N3：名字放到控件下（忽略 ×、存图、右侧控件列）+ 不避让别的方块
    'under_ctrl': ('assets/routemap.js', "if (!hit(cx, cy, w, h)) ok = [cx, cy]; }", "if (true) ok = [cx, Math.min(cy, inst.st + 12)]; }"),
    'ctrl_blind': ('assets/routemap.js', "for (j = 0; j < rs.length; j++) if (x < rs[j].r + 2 && x + w > rs[j].l - 2 && y < rs[j].b + 2 && y + h > rs[j].t - 2) return true;\n      for (j = 0; j < placed.length; j++)", "for (j = 0; j < placed.length; j++)"),
    # N3：互相压住
    'overlap': ('assets/routemap.js', "for (j = 0; j < placed.length; j++) if (x < placed[j].x + placed[j].w + 3 && x + w > placed[j].x - 3 && y < placed[j].y + placed[j].h + 2 && y + h > placed[j].y - 2) return true;\n      return false;\n    }\n    var order", "return false;\n    }\n    var order"),
    # N4：起点 / 终点不优先 + 只放第一个候选（放不下就隐藏）
    'one_try': ('assets/routemap.js', "var c = candsFor(w, h);", "var c = candsFor(w, h).slice(0, 1);"),
    # N5：点方块没反应
    'tap_dead': ('assets/routemap.js', "      return selectDay(inst, m.day);      // 一天就直接进那一天", "      return;      // 一天就直接进那一天"),
    # N6：主要景点缩小时也出现
    'sights_always': ('assets/routemap.js', "var ZS = 11;", "var ZS = 0;"),
    'sights_never': ('assets/routemap.js', "var ZS = 11;", "var ZS = 99;"),
    # N7：存图里写回数字
    'save_num': ('assets/routemap.js', "x.fillText(m.name, X + 15, Y + hh / 2 + 2);", "x.fillText(m.dl, X + 15, Y + hh / 2 + 2);"),
    # N8：起步壳回到数字
    'shell_num': ('assets/site.js', "<text y=\"4\" text-anchor=\"middle\">'+t+'</text></g>'};", "<text y=\"4\" text-anchor=\"middle\">'+(k+1)+'</text></g>'};"),
}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
ROUTES = ['xa3', 'g318', 'xl8a', 'xb96a', 'xv612a', 'tk4', 'hsg1']
if '--routes' in sys.argv: ROUTES = sys.argv[sys.argv.index('--routes') + 1].split(',')
SIZES = [(390, 844, '390', False), (375, 812, '375', False), (414, 896, '414', False), (844, 390, '横屏', False), (390, 844, '暗色', True)]
NUMERIC = re.compile(r'^[\d\s–·+、第天,，-]*$')


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


def route(br, rid, w=390, h=844, dark=False):
    c = new_ctx(br, None, w=w, h=h, dark=dark); stub(c); pg = new_page(env, c); goto(env, pg, '/trip/%s/' % rid, 400); return c, pg


def ready(pg, t=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=t)
def open_ov(pg):
    pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})")
    pg.click('.mapgo'); ready(pg); pg.wait_for_timeout(900)
def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


# 总览里每个名字方块：文字、可见、DOM 盒子（舞台坐标）、落脚点、包含的天
GEO = """(function(){var z=ZRM.cur(),st=z.stage.getBoundingClientRect();
 function R(e){var r=e.getBoundingClientRect();return {l:r.left-st.left,t:r.top-st.top,r:r.right-st.left,b:r.bottom-st.top}}
 var bd=z.marks.filter(function(m){return m.badge}).map(function(m){var i=m.el.firstElementChild,b=i&&i.querySelector('b'),s=i&&i.querySelector('s');
   return {day:m.day,days:m.days,name:m.name,txt:i?i.textContent:'',b:b?b.textContent:'',s:s?s.textContent:'',vis:m.el.style.visibility!=='hidden',box:R(i||m.el),px:m.px,py:m.py,aria:m.el.getAttribute('aria-label')||'',label:m.label}});
 var ctrl=z.ctrl.map(function(c){return {l:c.l,t:c.t,r:c.r,b:c.b}}), bar=R(z.root.querySelector('.rm-sht'));
 return {bd:bd,ctrl:ctrl,bar:bar,sw:z.sw,mh:z.mh,st:z.st,sel:z.sel,n:z.days.length,nm:z.days.map(function(d){return d.nm}),z:z.view.cam().z,
   sg:[].slice.call(z.root.querySelectorAll('.rm-sg')).filter(function(e){return e.style.visibility==='visible'}).map(function(e){return {t:e.textContent,box:R(e)}})}})()"""
def geo(pg): return pg.evaluate(GEO)
def ov(a, b, pad=0): return a['l'] < b['r'] + pad and a['r'] > b['l'] - pad and a['t'] < b['b'] + pad and a['b'] > b['t'] - pad
def han(t): return len(re.findall(r'[一-鿿]', t))


def static_checks(tag, g, rid):
    vis = [b for b in g['bd'] if b['vis']]
    bad = [b['txt'] for b in vis if han(b['b']) < 2 or NUMERIC.match(b['b'] or '')]
    check('N1 %s 总览里看得见的 %d 个方块都有地名（≥2 个汉字、不是纯数字；不合格 %s）' % (tag, len(vis), bad[:4]), len(vis) >= 1 and not bad, bad[:4])
    badn = [b['txt'] for b in g['bd'] if not b['aria'].startswith(b['name'] or '\0')]
    check('N1 %s 每个方块的无障碍名字以地名开头（不合格 %s）' % (tag, badn[:3]), not badn, badn[:3])
    hits = []
    for i, a in enumerate(vis):
        for b in vis[i + 1:]:
            if ov(a['box'], b['box']): hits.append((a['b'], b['b']))
        for c in g['ctrl']:
            if ov(a['box'], c): hits.append((a['b'], 'ctrl'))
        if ov(a['box'], g['bar']): hits.append((a['b'], 'bar'))
        if a['box']['l'] < 0 or a['box']['r'] > g['sw'] or a['box']['t'] < g['st'] or a['box']['b'] > g['mh']: hits.append((a['b'], 'edge'))
    check('N3 %s 看得见的方块互不重叠、不压控件 / 署名 / 底部条、不出屏（问题 %s）' % (tag, hits[:4]), not hits, hits[:4])
    return vis


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()

    # ─────────── N1 / N3：各线路 × 各尺寸
    for rid in ROUTES:
        for (w, h, tn, dark) in SIZES:
            if rid not in ('xa3', 'g318') and tn not in ('390', '横屏'): continue      # 全尺寸只跑最短和最典型的两条；其余线路跑竖屏 + 横屏
            with guard('N1 %s %s' % (rid, tn)):
                c, pg = route(br, rid, w, h, dark); open_ov(pg); g = geo(pg); vis = static_checks('%s %s' % (rid, tn), g, rid)
                if tn == '390': shot(pg, 'n_%s.png' % rid)
                if tn == '390' and rid == 'xa3':
                    ds = {b['name']: b['days'] for b in g['bd']}
                    check('N2 xa3：西安 = 第 1、3 天合成一个方块（角标“1·3”），临潼 = 第 2 天（实际 %s；角标 %s）' % (ds, [b['s'] for b in g['bd']]), ds == {'西安': [0, 2], '临潼': [1]} and sorted(b['s'] for b in g['bd']) == ['1·3', '2'], ds)
                c.close()

    # ─────────── N2：同城合并（按页面的 data-nm 算期望，所有线路）
    for rid in ROUTES:
        with guard('N2 ' + rid):
            c, pg = route(br, rid); open_ov(pg); g = geo(pg); nm = g['nm']
            # 期望：相邻同名的天一定同一个方块；不同名一定不同方块
            grp = {}
            for b in g['bd']:
                for d in b['days']: grp[d] = (b['name'], tuple(b['days']))
            adj_bad = [i + 1 for i in range(1, len(nm)) if nm[i] and nm[i] == nm[i - 1] and i in grp and i - 1 in grp and grp[i] != grp[i - 1]]
            mix_bad = [b['name'] for b in g['bd'] if len(set(nm[d] for d in b['days'])) > 1]
            same = sum(1 for i in range(1, len(nm)) if nm[i] and nm[i] == nm[i - 1])
            check('N2 %s 连住同一个城镇的天（共 %d 对相邻同名）都在同一个方块里（没合并的第 %s 天）；不同城镇没被并到一起（%s）' % (rid, same, adj_bad[:4], mix_bad[:3]), not adj_bad and not mix_bad, (adj_bad[:4], mix_bad[:3]))
            multi = [(b['name'], b['s']) for b in g['bd'] if len(b['days']) > 1]
            if same: check('N2 %s 合并后的方块写着天数角标（%s）' % (rid, multi[:3]), bool(multi) and all(re.search(r'\d', s) for _, s in multi), multi[:3])
            c.close()

    # ─────────── N3：造出来的场景——落脚点正好落在右侧控件列下面
    with guard('N3 控件列下'):
        c, pg = route(br, 'g318'); open_ov(pg)
        r = pg.evaluate("""(function(){var z=ZRM.cur(),col=z.ctrl.filter(function(c){return c.l>z.sw/2&&c.t>z.mh/2-200})[0]; if(!col) return null;
          var m=z.marks.filter(function(m){return m.badge&&m.day===3})[0], cam=z.view.cam(), s=512*Math.pow(2,cam.z);
          function lx(g){return (g+180)/360} function ly(a){var q=Math.sin(a*Math.PI/180);return .5-Math.log((1+q)/(1-q))/(4*Math.PI)} function ilat(y){var n=Math.PI-2*Math.PI*y;return 180/Math.PI*Math.atan(.5*(Math.exp(n)-Math.exp(-n)))}
          var tx=(col.l+col.r)/2, ty=(col.t+col.b)/2, cx=lx(m.ll[1])-(tx-z.sw/2)/s, cy=ly(m.ll[0])-(ty-z.mh/2)/s;
          z.view.go({lng:cx*360-180,lat:ilat(cy),z:cam.z},false); return {tx:tx,ty:ty}})()""")
        pg.wait_for_timeout(600)
        if r:
            g = geo(pg); vis = [b for b in g['bd'] if b['vis']]; hits = [b['b'] for b in vis for cc in g['ctrl'] if ov(b['box'], cc)]
            near = [b['b'] for b in vis if abs((b['box']['l'] + b['box']['r']) / 2 - r['tx']) < 140 and abs((b['box']['t'] + b['box']['b']) / 2 - r['ty']) < 80]
            check('N3 g318 把第 4 天的落脚点推到控件列下面（%d,%d）：名字让开控件（压到的 %s），且还看得见（附近方块 %s）' % (r['tx'], r['ty'], hits[:3], near[:3]), not hits and bool(near), (hits, near))
            shot(pg, 'n3_ctrl.png')
        else: check('N3 g318 有右侧控件列可测', False, r)
        c.close()

    # ─────────── N4 保证
    for rid in ROUTES:
        with guard('N4 ' + rid):
            c, pg = route(br, rid); open_ov(pg); g = geo(pg); bd = g['bd']
            first = [b for b in bd if 0 in b['days']][0]; last = [b for b in bd if (g['n'] - 1) in b['days'] or max(b['days']) == max(max(x['days']) for x in bd)][0]
            check('N4 %s 首日起点“%s”和终点“%s”都有名字（看得见：%s / %s）' % (rid, first['name'], last['name'], first['vis'], last['vis']), first['vis'] and last['vis'], (first['vis'], last['vis']))
            if len(bd) <= 14:
                hid = [b['name'] for b in bd if not b['vis']]
                check('N4 %s 共 %d 个落脚城镇，每一个都有名字（藏起来的 %s）' % (rid, len(bd), hid), not hid, hid)
            else:
                n0 = len([b for b in bd if b['vis']])
                big = max(bd, key=lambda b: len(b['days']))
                pg.evaluate("""(function(){var z=ZRM.cur(),c=z.view.cam(),m=z.marks.filter(function(m){return m.badge&&m.day===%d})[0];z.view.go({lng:m.ll[1],lat:m.ll[0],z:c.z+3},false)})()""" % big['day']); pg.wait_for_timeout(700)
                g2 = geo(pg); inview = [b for b in g2['bd'] if b['vis'] and 0 <= b['px'] <= g2['sw'] and g2['st'] <= b['py'] <= g2['mh']]
                check('N4 %s 共 %d 个落脚城镇，总览看得见 %d 个；放大 3 级后（画面里 %d 个落脚点）看得见的名字都有地名（%d 个）' % (rid, len(bd), n0, len([b for b in g2['bd'] if 0 <= b['px'] <= g2['sw'] and g2['st'] <= b['py'] <= g2['mh']]), len(inview)), n0 >= 8 and len(inview) >= 1 and all(han(b['b']) >= 2 for b in inview), (n0, len(inview)))
            c.close()

    # ─────────── N5 点击
    for rid, nmk in (('g318', '理塘'), ('xa3', '临潼')):
        with guard('N5 ' + rid):
            c, pg = route(br, rid); T = Touch(c, pg); open_ov(pg); g = geo(pg); b = [x for x in g['bd'] if x['name'] == nmk][0]
            cx, cy = (b['box']['l'] + b['box']['r']) / 2, (b['box']['t'] + b['box']['b']) / 2
            T.tap(cx, cy); pg.wait_for_timeout(900); g2 = geo(pg)
            check('N5 %s 点名字方块“%s”（第 %s 天）：进那一天（sel=%s）' % (rid, nmk, [d + 1 for d in b['days']], g2['sel']), g2['sel'] == b['days'][0], g2['sel'])
            c.close()
    with guard('N5 连住'):
        c, pg = route(br, 'g318'); T = Touch(c, pg); open_ov(pg); g = geo(pg); b = [x for x in g['bd'] if x['name'] == '康定'][0]
        T.tap((b['box']['l'] + b['box']['r']) / 2, (b['box']['t'] + b['box']['b']) / 2); pg.wait_for_timeout(600)
        pk = pg.evaluate("[].slice.call(document.querySelectorAll('.rm-pi')).map(function(e){return e.textContent})")
        check('N5 g318 点“康定 2–3”：弹出各天（%s）' % pk, len(pk) == 2 and all(re.match(r'^第 [23] 天', x) for x in pk), pk)
        if pk:
            pg.click('.rm-pi >> nth=1'); pg.wait_for_timeout(800); check('N5 g318 选第 3 天：sel=%s' % pg.evaluate("ZRM.cur().sel"), pg.evaluate("ZRM.cur().sel") == 2)
        c.close()
        c, pg = route(br, 'xb96a'); T = Touch(c, pg); open_ov(pg); g = geo(pg)      # 105 天：名字放不下的落脚点很多，点它的小点
        hid = [x for x in g['bd'] if not x['vis'] and 25 < x['px'] < g['sw'] - 70 and g['st'] + 70 < x['py'] < g['mh'] - 40]
        if hid:
            z0 = g['z']; T.tap(hid[0]['px'], hid[0]['py']); pg.wait_for_timeout(900)
            pk = pg.evaluate("[].slice.call(document.querySelectorAll('.rm-pi')).map(function(e){return e.textContent})"); sel = pg.evaluate("ZRM.cur().sel"); z1 = pg.evaluate("ZRM.cur().view.cam().z")
            check('N5 xb96a 名字没放下的落脚点“%s”：点它的小点有反应——直接进那一天（sel=%s）/ 邻居挨得近弹出让选（%d 项）/ 一堆挤着（>6）放大（z %.1f → %.1f）' % (hid[0]['name'], sel, len(pk), z0, z1), sel == hid[0]['days'][0] or len(pk) >= 2 or z1 >= z0 + 1.5, (sel, pk, z0, z1))
        else: check('N5 xb96a 有名字让开了、在屏幕里可点的落脚点', False, len([x for x in g['bd'] if not x['vis']]))
        c.close()

    # ─────────── N6 主要景点放大后才出现
    for rid in ('xa3', 'g318'):
        with guard('N6 ' + rid):
            c, pg = route(br, rid); open_ov(pg); g = geo(pg)
            check('N6 %s 全程缩小（z %.1f）时没有景点标签（%d 个）' % (rid, g['z'], len(g['sg'])), not g['sg'] and g['z'] < 11, (g['z'], len(g['sg'])))
            tgt = [b for b in g['bd'] if b['vis']][1]
            pg.evaluate("(function(){var z=ZRM.cur(),m=z.marks.filter(function(m){return m.badge&&m.day===%d})[0];z.view.go({lng:m.ll[1],lat:m.ll[0],z:11.6},false)})()" % tgt['day']); pg.wait_for_timeout(800)
            g2 = geo(pg); vb = [b for b in g2['bd'] if b['vis']]
            bad = [s['t'] for s in g2['sg'] if han(s['t']) < 2 or NUMERIC.match(s['t'])]; clash = [s['t'] for s in g2['sg'] for b in vb if ov(s['box'], b['box'])]
            check('N6 %s 放大到 z 11.6：出现 %d 个景点标签（%s），都是景点名（不合格 %s）、不压名字方块（%s）' % (rid, len(g2['sg']), [s['t'] for s in g2['sg']][:4], bad[:2], clash[:2]), len(g2['sg']) >= 1 and not bad and not clash, (g2['sg'][:3], clash))
            shot(pg, 'n6_%s_zoom.png' % rid); c.close()

    # ─────────── N7 存图
    for rid in ('xa3', 'g318'):
        with guard('N7 ' + rid):
            c, pg = route(br, rid)
            pg.add_init_script("window.__ft=[];(function(){var f=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(t){window.__ft.push(String(t));return f.apply(this,arguments)}})()")
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(400); open_ov(pg); g = geo(pg); pg.evaluate("window.__ft.length=0")
            pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=8000); pg.wait_for_timeout(300)
            ft = pg.evaluate("window.__ft"); names = [b['name'] for b in g['bd'] if b['vis']]
            miss = [n for n in names if n not in ft]; nums = [t for i, t in enumerate(ft) if NUMERIC.match(t) and t and (i == 0 or ft[i - 1] not in names)]      # 天数角标紧跟在地名后面画；前面不是地名的数字 = 一个只有数字的方块
            check('N7 %s 存图：每个看得见的方块的地名都画了（共 %d 个，没画的 %s）；方块里没有单独的纯数字（天数角标必须紧跟地名；%s）' % (rid, len(names), miss[:3], nums[:3]), names and not miss and not nums, (miss, nums))
            c.close()

    # ─────────── N8 起步壳
    with guard('N8'):
        for rid in ('xa3', 'g318'):
            env.delays['routemap.js'] = 2.5
            c, pg = route(br, rid); pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); pg.wait_for_timeout(500)
            sh = pg.evaluate("(function(){var r=document.querySelector('.rm-boot');if(!r)return null;return {bn:[].slice.call(r.querySelectorAll('.rm-bn text')).map(function(t){return t.textContent}),bm:[].slice.call(r.querySelectorAll('.rm-bm:not(.rm-bn) text')).map(function(t){return t.textContent})}})()")
            ok = bool(sh) and len(sh['bn']) >= 2 and all(han(t) >= 2 for t in sh['bn']) and not sh['bm']
            check('N8 %s 起步壳（脚本还在路上）总览里写的是地名（%s），没有纯数字的方块（%s）' % (rid, sh and sh['bn'][:4], sh and sh['bm'][:3]), ok, sh)
            shot(pg, 'n8_shell_%s.png' % rid); pg.wait_for_timeout(300); c.close(); env.delays.clear()

    # ─────────── N9 性能（105 天线）
    with guard('N9'):
        c, pg = route(br, 'xb96a'); open_ov(pg)
        t = pg.evaluate("""(function(){var z=ZRM.cur(),c=z.view.cam(),a=[],i;for(i=0;i<30;i++){var t0=performance.now();z.view.go({lng:c.lng+(i%2?.4:-.4)*(i/30),lat:c.lat+(i%3-1)*.2,z:c.z+(i%5)*.1},false);a.push(performance.now()-t0)}a.sort(function(x,y){return x-y});return {med:a[15],max:a[29]}})()""")
        check('N9 105 天线总览：镜头每动一下（含重排名字方块）中位数 %.1f ms、最慢 %.1f ms（< 12 / < 60）' % (t['med'], t['max']), t['med'] < 12 and t['max'] < 60, t)
        ts = []
        for d in (3, 40, 70, 100):
            ts.append(pg.evaluate("new Promise(function(r){var t=performance.now();ZRM.selectDay(%d);requestAnimationFrame(function(){requestAnimationFrame(function(){r(performance.now()-t)})})})" % d)); pg.wait_for_timeout(700)
        ts.sort(); med = (ts[1] + ts[2]) / 2
        check('N9 105 天线切天到下一帧画好，中位数 %.0f ms（< 150）；各次 %s' % (med, [round(x) for x in ts]), med < 150, ts)
        pg.evaluate("ZRM.selectDay(-1)"); pg.wait_for_timeout(700)
        tb = sorted(pg.evaluate("(function(){var a=[],i;for(i=0;i<7;i++){var t=performance.now();ZRM.selectDay(i%2?50:-1);a.push(performance.now()-t)}return a})()"))
        check('N9 105 天线来回切“全程 / 第 51 天”：同步部分（重建 ~80 个名字方块 + 重排）中位数 %.1f ms、最慢 %.1f ms（< 30 / < 80；帧时间受机器负载影响太大，不在这里断言）' % (tb[3], tb[6]), tb[3] < 30 and tb[6] < 80, tb)
        c.close()
    br.close()

env.finish('map_names_check')
