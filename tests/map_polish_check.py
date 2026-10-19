#!/usr/bin/env python3
"""路线地图 · 细节打磨一轮（2026-10-19，用户用手机 390 宽走了一遍线上 /trip/xa3/ 的地图后列的 8 条）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site_mp，或改了 site_src 后 python3 tools/build_site.py build/site_mp）：
    python3 tests/map_polish_check.py build/site_mp [--shots DIR] [--only P1,P2] [--inject 名字]      # 反向自检：每个名字必须变红

P1  站名标签：方块旁边有站名小标签（纸色底、一行、≤6 字截断），互相 / 和方块 / 和控件不重叠，选中的优先，放大后全部出现；“住”在方块下面（z-index 更低），盖不到数字
P2  视野居中：390 / 375 / 414 宽 + 横屏，每个站点方块完整落在可视区内（扣掉底部条、右侧控件列、× 和存图）且有余量，且大致居中；
    切天 / 关闭站点卡回当天 / “回到视野” / 刚打开 四条路到的视野一样；已经在视野里时“回到视野”置灰，拖开后亮起
P3  底图退后：样式文件里道路盾牌、村名整层隐藏，区名 / 路名 / POI 字号压小、颜色换成浅灰；运行时加载进地图的样式一样；站点方块 / 标签在底图画布之上（DOM 层级）
P4  底部条文案：两行分明（标题一行 / 数字一行），数字块（“走路约 2 小时 10 分”）任何宽度下都不从中间断，没有“今天：”；说明句只在当天视图出现一次、更小更淡；全程态同样排版
P5  全程视图：每天一个形 + 色（实心方 / 实心圆 / 空心方），章更小；挤在一起的 ≤3 天并排摆开都看得见，更多的合成“1–5”
P6  进度条：街道图出现后一定收掉（哪怕有几块瓦片一直挂着不回），收了以后拖地图不再冒出来；失败走“重试”
P7  线：更细更淡、有先后小箭头、A→B→A 的往返只画一条
P8  其它：点击区 ≥44、回到视野置灰、拖地图时底部条一个字都不重绘、暗色模式标签对比度、横屏底部条收成 104、卡片切换有动画（尊重减弱动效）、安全区
"""
import json, math, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

SITE = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.join(ROOT, 'build', 'site')


def _style_variant(fn):
    """从站里的样式文件算出一个“被改坏的版本”，给反向注入用（整个文件替换）"""
    f = os.path.join(SITE, 'assets', 'map', 'style.json')
    if not os.path.exists(f): return ('assets/map/style.json', 'X', 'Y')
    old = open(f, encoding='utf-8').read(); st = json.loads(old); fn(st)
    return ('assets/map/style.json', old, json.dumps(st, ensure_ascii=False, separators=(',', ':')))


def _shield_on(st):
    for l in st['layers']:
        if 'shield' in l['id']: l['layout']['visibility'] = 'visible'
def _village_on(st):
    for l in st['layers']:
        if l['id'] == 'label_village': l['layout']['visibility'] = 'visible'
def _black(st):
    for l in st['layers']:
        if l.get('type') == 'symbol' and 'text-color' in l.get('paint', {}): l['paint']['text-color'] = '#000000'
def _big(st):
    for l in st['layers']:
        if l['id'] == 'label_town': l['layout']['text-size'] = 18


INJ = {
    # P1
    'lab_overlap': ('assets/routemap.js', "      var j; if (x < 4 || x + w > W_ - 4 || y < T_ || y + h > B_) return true;", "      return false; var j;"),                         # 标签不做避让
    'lab_trunc': ('assets/routemap.js', "    return r.length > 6 ? r.slice(0, 6) + '…' : r;\n  }", "    return r;\n  }"),                                                   # 不截断
    'hm_above': ('assets/site.css', ".rm .rm-mk.rm-hm{z-index:2}", ".rm .rm-mk.rm-hm{z-index:9}"),                                                    # 住盖在数字上
    # P2
    'pad_asym': ('assets/routemap.js', "var pad = { t: inst.st + 56, b: 28, l: 40, r: 40 }", "var pad = { t: inst.st + 56, b: 28, l: 4, r: 130 }"),   # 视野偏一边
    'no_refit': ('assets/routemap.js', "paintTagsAndMarks(inst); fitView(inst, true);      // 关掉站点卡回当天", "paintTagsAndMarks(inst);      // 关掉站点卡回当天"),   # 关闭卡片不回当天视野
    'rs_enabled': ('assets/routemap.js', "if (rs && rs.disabled !== c) { rs.disabled = c;", "if (rs && rs.disabled !== false) { rs.disabled = false;"),   # 回到视野永远亮着
    # P3
    'shield_on': _style_variant(_shield_on), 'village_on': _style_variant(_village_on), 'text_black': _style_variant(_black), 'text_big': _style_variant(_big),
    # P4
    'nw_off': ('assets/site.css', ".rm .rm-ln .nw{white-space:nowrap}", ".rm .rm-ln .nw{white-space:normal}"),                               # 数字块允许从中间断
    'today_back': ('assets/routemap.js', "<b>第 ' + (d.i + 1) + ' 天 · ' + esc(d.title) + '</b><span class=\"rm-ln\">'", "<b>第 ' + (d.i + 1) + ' 天 · ' + esc(d.title) + '</b><span class=\"rm-ln\">今天：'"),   # 又写“今天：”
    'hint_big': ('assets/site.css', "font-size:10.5px;line-height:14px;color:var(--mute);", "font-size:13px;line-height:14px;color:var(--ink);"),      # 说明句又大又黑
    # P5
    'no_fan': ('assets/routemap.js', "var fan = n <= 3 && j > 0, hide = n > 3 && j > 0,", "var fan = false, hide = j > 0,"),                                # 挤在一起的天全部合并
    'shape_same': ('assets/site.css', ".rm .rm-db.rm-dk1 i{border-radius:12px}", ""),                                                       # 每天同一个形
    # P6
    'prog_stuck': ('assets/routemap.js', "    if (inst.loaded) return; clearTimeout(inst.pfin); clearTimeout(inst.pcap);", "    return; clearTimeout(inst.pfin); clearTimeout(inst.pcap);"),   # hideLoad 失效（只剩 idle 的老路：idle 不来就停在半截）
    'prog_revive': ('assets/routemap.js', "function setProg(inst, v) { if (!inst.prog || inst.loaded) return;", "function setProg(inst, v) { if (!inst.prog) return;"),   # 收了以后瓦片一来又冒出来
    # P7
    'dup_lines': ('assets/routemap.js', "if (seen[ka + '>' + kb] || seen[kb + '>' + ka]) continue;", ""),                                     # 往返画两条
    'thick': ('assets/routemap.js', "c.strokeStyle = col; c.lineWidth = 1.8; c.stroke();", "c.strokeStyle = col; c.lineWidth = 3; c.stroke();"),          # 线又粗了
    'no_arrow': ('assets/routemap.js', "if (L < 60) continue;", "continue;"),                                                                 # 没有箭头
    # P8
    'bar_repaint': ('assets/routemap.js', "    if (zi.disabled !== a) zi.disabled = a; if (zo.disabled !== b) zo.disabled = b;", "    inst.bodyEl.innerHTML = inst.bodyEl.innerHTML; if (zi.disabled !== a) zi.disabled = a; if (zo.disabled !== b) zo.disabled = b;"),   # 拖地图时底部条每帧重画
    'land_tall': ('assets/site.css', "  .rm .rm-sht{height:calc(104px + env(safe-area-inset-bottom,0px))}", "  .rm .rm-sht{height:calc(168px + env(safe-area-inset-bottom,0px))}"),   # 横屏底部条不收
    'card_still': ('assets/site.css', ".rm .rm-card{animation:rm-card-in .18s ease-out;", ".rm .rm-card{"),                                    # 卡片切换没有动画
}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
def want(k): return ONLY is None or k in ONLY


class Stub:
    """mode: ok | tiles（瓦片全挂）| hang_most（(x+y) 为奇数的瓦片永远不回——'idle' 永远不会来）"""
    def __init__(self, c, mode='ok'):
        self.mode = mode; self.n = 0
        def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
        def pbf(r):
            self.n += 1
            if self.mode == 'tiles': return r.abort()
            if self.mode == 'hang_most':      # 按瓦片坐标奇偶：(x+y) 偶数的正常，奇数的永远不回——一屏里两种都有，所以“有的到了、有的一直挂着”，idle 永远不来（不能按请求先后：预热 / 预取会抢掉前几个名额）
                m = re.search(r'/(\d+)/(\d+)/(\d+)\.pbf', r.request.url)
                if m and (int(m.group(2)) + int(m.group(3))) % 2 == 1: return
            r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        def other(r):
            if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
            elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
            else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


def mk(br, mode='ok', w=390, h=844, dark=False, **kw):
    c = new_ctx(br, None, w=w, h=h, dark=dark, **kw); Stub(c, mode); return c


def ready(pg, t=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=t)
def tiles(pg, t=12000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().tiles>0", timeout=t)
def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


def open_day(pg, n, wait=True, path=None):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n); ready(pg)
    if wait: tiles(pg)
    pg.wait_for_timeout(700)


def open_ov(pg, wait=True):
    pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg)
    if wait: tiles(pg)
    pg.wait_for_timeout(700)


# 标记 / 标签 / 控件的几何（地图舞台坐标）
GEO = """(function(){var z=ZRM.cur(),st=z.stage.getBoundingClientRect();function R(e){var r=e.getBoundingClientRect();return {l:r.left-st.left,t:r.top-st.top,r:r.right-st.left,b:r.bottom-st.top,w:r.width,h:r.height}}
 var mk=[],lb=[],hm=null,ctrl=[];
 z.marks.forEach(function(m){ if(m.tag||!m.kind) return; var e=m.el; if(m.kind==='lb'){ if(e.style.visibility!=='hidden') lb.push({n:m.n,box:R(e.firstElementChild||e),txt:e.textContent,cur:e.classList.contains('rm-cur')}); return }
   var i=e.firstElementChild||e, r=R(i), cs=getComputedStyle(e); if(m.kind==='n'||m.kind==='day') mk.push({k:m.kind,n:m.n,day:m.day,box:r,z:+cs.zIndex||0,vis:cs.visibility,fan:m.fan||0}); if(m.kind==='hm') hm={box:r,z:+cs.zIndex||0} });
 ['.rm-x','.rm-sv','.rm-col','.rm-ai'].forEach(function(s){var e=z.root.querySelector(s);if(e&&!e.hidden){var r=R(e);if(r.w>0)ctrl.push({s:s,box:r})}});
 var bar=R(z.root.querySelector('.rm-sht')); return {mk:mk,lb:lb,hm:hm,ctrl:ctrl,bar:bar,sw:z.sw,mh:z.mh,sh2:z.sh2,st:z.st,nlab:z.marks.filter(function(m){return m.kind==='lb'}).length}})()"""


def geo(pg): return pg.evaluate(GEO)
def ov(a, b, pad=0): return a['l'] < b['r'] + pad and a['r'] > b['l'] - pad and a['t'] < b['b'] + pad and a['b'] > b['t'] - pad


def center_of(mk):
    xs = [(m['box']['l'] + m['box']['r']) / 2 for m in mk]; ys = [(m['box']['t'] + m['box']['b']) / 2 for m in mk]; return xs, ys


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()

    # ─────────── P1 站名标签
    if want('P1'):
        with guard('P1'):
            c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 1)
            g = geo(pg); L = g['lb']
            check('P1a 第 1 天 %d 站：每站一个标签（DOM %d 个），默认视野下至少显示 %d 个' % (len(g['mk']), g['nlab'], len(L)), g['nlab'] == len(g['mk']) == 5 and len(L) >= 3, (g['nlab'], len(L)))
            bad_len = [l['txt'] for l in L if len(l['txt']) > 7 or (len(l['txt']) > 6 and not l['txt'].endswith('…'))]
            multi = pg.evaluate("[].slice.call(document.querySelectorAll('.rm-nm span')).filter(function(e){return e.getClientRects().length>1||e.offsetHeight>22}).length")
            check('P1b 标签一行、≤6 字（超出的是“6 字 + …”）：%s' % [l['txt'] for l in L], not bad_len and not multi, (bad_len, multi))
            bg = pg.evaluate("(function(){var e=document.querySelector('.rm-nm span'),b=getComputedStyle(document.documentElement).getPropertyValue('--bg').trim();return [getComputedStyle(e).backgroundColor,getComputedStyle(e).pointerEvents,getComputedStyle(e.parentNode).pointerEvents]})()")
            check('P1c 标签是纸色底（不透明）、不接手指（%s）' % bg, bg[0] not in ('rgba(0, 0, 0, 0)', 'transparent') and bg[2] == 'none', bg)
            hits = []
            for i, a in enumerate(L):
                for j, b in enumerate(L):
                    if i < j and ov(a['box'], b['box']): hits.append(('lb-lb', a['txt'], b['txt']))
                for m in g['mk']:
                    mb = {'l': m['box']['l'] - 2, 't': m['box']['t'] - 2, 'r': m['box']['r'] + 2, 'b': m['box']['b'] + 2}
                    if ov(a['box'], mb): hits.append(('lb-mk', a['txt'], m['n']))
                for ct in g['ctrl']:
                    if ov(a['box'], ct['box']): hits.append(('lb-ctrl', a['txt'], ct['s']))
                if g['hm'] and ov(a['box'], g['hm']['box']): hits.append(('lb-住', a['txt']))
                if a['box']['l'] < 0 or a['box']['r'] > g['sw'] or a['box']['t'] < g['st'] or a['box']['b'] > g['mh']: hits.append(('lb-出界', a['txt']))
            check('P1d 显示出来的标签：互相不重叠、不压方块 / 住 / 控件、不出界（%d 个标签）' % len(L), not hits, hits[:5])
            zi = pg.evaluate("(function(){var z=ZRM.cur(),m=z.marks.filter(function(m){return m.kind==='n'&&m.n===1})[0],hm=z.marks.filter(function(m){return m.kind==='hm'})[0];return [+getComputedStyle(hm.el).zIndex,+getComputedStyle(m.el).zIndex]})()")
            check('P1e “住”的层级（%s）低于站点方块（%s）：盖不到数字' % (zi[0], zi[1]), zi[0] < zi[1], zi)
            pg.evaluate("ZRM.select(3)"); pg.wait_for_timeout(1500); g2 = geo(pg)
            cur = [l for l in g2['lb'] if l['cur']]
            check('P1f 选中第 3 站：它的标签一定显示（墨底）：%s' % [l['txt'] for l in cur], len(cur) == 1 and cur[0]['n'] == 3 and pg.evaluate("getComputedStyle(document.querySelector('.rm-nm.rm-cur span')).backgroundColor") != pg.evaluate("getComputedStyle(document.querySelector('.rm-nm:not(.rm-cur) span')).backgroundColor"), g2['lb'])
            pg.evaluate("(function(){var z=ZRM.cur(),p=z.days[z.sel].pts[2];z.map.jumpTo({center:[p.ll[1],p.ll[0]],zoom:16})})()"); pg.wait_for_timeout(600); g3 = geo(pg)
            inside = [m for m in g3['mk'] if 0 <= m['box']['l'] and m['box']['r'] <= g3['sw'] and g3['st'] <= m['box']['t'] and m['box']['b'] <= g3['mh']]
            check('P1g 放大后（z16）屏幕里的站标签全部出现（站 %d 个在屏幕内，标签 %d 个）' % (len(inside), len(g3['lb'])), len(inside) >= 1 and len(g3['lb']) >= len(inside), (len(inside), len(g3['lb'])))
            shot(pg, 'p1_day1.png')
            c.close()
            c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
            g = geo(pg); long_ = pg.evaluate("ZRM.cur().days[1].pts.map(function(p){return p.name})")
            check('P1h 第 2 天长名字（%s）也缩成 ≤6 字：%s' % (long_[:2], [l['txt'] for l in g['lb']]), all(len(l['txt']) <= 6 or (len(l['txt']) == 7 and l['txt'].endswith('…')) for l in g['lb']) and len(g['lb']) >= 2, g['lb'])
            c.close()

    # ─────────── P2 视野居中 / 同一套留边 / 回到视野
    if want('P2'):
        with guard('P2'):
            for (w, h) in ((390, 844), (375, 812), (414, 896), (844, 390)):
                for day in (1, 2, 3):
                    c = mk(br, w=w, h=h); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, day)
                    g = geo(pg); xs, ys = center_of(g['mk'])
                    bad = [m['n'] for m in g['mk'] if m['box']['l'] < 8 or m['box']['r'] > g['sw'] - 8 or m['box']['t'] < g['st'] + 8 or m['box']['b'] > g['mh'] - 8 or any(ov(m['box'], ct['box']) for ct in g['ctrl'])]
                    cx = (min(xs) + max(xs)) / 2 - g['sw'] / 2; cy = (min(ys) + max(ys)) / 2 - (g['st'] + g['mh']) / 2
                    ok_c = abs(cx) <= 34 and abs(cy) <= 60
                    check('P2a %dx%d 第 %d 天：%d 个方块完整在可视区内（离边 ≥8px）、没压控件%s；站点包围盒中心偏 (%.0f,%.0f)px' % (w, h, day, len(g['mk']), ('，越界 ' + str(bad)) if bad else '', cx, cy), not bad and ok_c and len(g['mk']) >= 2, (bad, cx, cy))
                    if (w, h) == (390, 844) and day == 1: shot(pg, 'p2_390_day1.png')
                    c.close()
            # 全程
            for (w, h) in ((390, 844), (375, 812), (414, 896)):
                c = mk(br, w=w, h=h); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_ov(pg)
                g = geo(pg); pts = pg.evaluate("(function(){var z=ZRM.cur(),a=[];z.days.forEach(function(d){d.pts.forEach(function(p){var q=z.view.project(p.ll);a.push([q.x,q.y])})});return a})()")
                xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
                bad = [q for q in pts if q[0] < 20 or q[0] > g['sw'] - 20 or q[1] < g['st'] + 20 or q[1] > g['mh'] - 20]
                cx = (min(xs) + max(xs)) / 2 - g['sw'] / 2
                check('P2b %dx%d 全程：所有站（%d 个）都在可视区里（离边 ≥20px），整体左右居中（偏 %.0fpx）' % (w, h, len(pts), cx), not bad and abs(cx) <= 34, (bad[:3], cx))
                if (w, h) == (390, 844): shot(pg, 'p2_390_ov.png')
                c.close()
            # 四条路到的视野一样 + 回到视野置灰
            c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 2)
            def sig():
                return pg.evaluate("(function(){var z=ZRM.cur();return z.days[z.sel].pts.map(function(p){var q=z.view.project(p.ll);return [Math.round(q.x),Math.round(q.y)]})})()")
            a0 = sig(); rs0 = pg.evaluate("document.querySelector('.rm-rs').disabled")
            T.drag(250, 400, 120, 300, dt=0.01); pg.wait_for_timeout(900); rs1 = pg.evaluate("document.querySelector('.rm-rs').disabled")
            pg.click('.rm-rs'); pg.wait_for_timeout(1200); a1 = sig(); rs2 = pg.evaluate("document.querySelector('.rm-rs').disabled")
            pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(1000); pg.click('.rm-tb[data-i="1"]'); pg.wait_for_timeout(1300); a2 = sig()
            pg.evaluate("ZRM.select(2)"); pg.wait_for_timeout(1400); rs3 = pg.evaluate("document.querySelector('.rm-rs').disabled")
            pg.click('.rm-cb'); pg.wait_for_timeout(1400); a3 = sig()
            d = lambda x, y: max(max(abs(p[0] - q[0]), abs(p[1] - q[1])) for p, q in zip(x, y))
            check('P2c 刚打开 / 拖开后点“回到视野” / 切天 / 点站后“回当天”：方块位置一致（最大差 %d / %d / %d px）' % (d(a0, a1), d(a0, a2), d(a0, a3)), d(a0, a1) <= 3 and d(a0, a2) <= 3 and d(a0, a3) <= 3, (a0, a1, a2, a3))
            check('P2d “回到视野”：在视野里置灰（%s）→ 拖开后亮起（%s）→ 点了又置灰（%s）；选中一站飞过去后亮着（%s）' % (rs0, rs1, rs2, rs3), rs0 is True and rs1 is False and rs2 is True and rs3 is False, (rs0, rs1, rs2, rs3))
            c.close()

    # ─────────── P3 底图退后
    if want('P3'):
        with guard('P3'):
            c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1)
            st = pg.evaluate("""(function(){var s=ZRM.cur().map.getStyle(),out={shield:[],village:null,big:[],dark:[],n:0};
              function lum(c){var m=String(c).match(/[\\d.]+/g);if(!m)return 1;if(String(c)[0]==='#'){var h=c.slice(1);if(h.length===3)h=h.replace(/./g,'$&$&');return (parseInt(h.slice(0,2),16)*.3+parseInt(h.slice(2,4),16)*.59+parseInt(h.slice(4,6),16)*.11)/255}return (+m[0]*.3+ +m[1]*.59+ +m[2]*.11)/255}
              var caps={label_town:11,label_other:10,label_city:14,label_city_capital:15,'highway-name-major':11,'highway-name-minor':10.5,poi_r1:10,poi_r7:10,poi_r20:10};
              s.layers.forEach(function(l){var v=l.layout&&l.layout.visibility; if(/shield/.test(l.id)){ if(v!=='none')out.shield.push(l.id) } if(l.id==='label_village')out.village=v;
                if(l.type==='symbol'&&l.layout&&l.layout['text-field']&&v!=='none'){out.n++; var tc=l.paint&&l.paint['text-color']; if(!tc||lum(tc)<.4)out.dark.push(l.id+':'+tc);
                  var ts=l.layout['text-size'],mx=typeof ts==='number'?ts:(Array.isArray(ts)?Math.max.apply(null,ts.filter(function(x,i){return i>=4&&i%2===0&&typeof x==='number'})):0); if(caps[l.id]&&mx>caps[l.id]+.01)out.big.push(l.id+':'+mx)}});
              out.q=(s.metadata||{}).zouni_quiet;return out})()""")
            check('P3a 运行时加载进地图的样式：道路盾牌整层隐藏（未隐藏 %s）、村名隐藏（%s）' % (st['shield'], st['village']), not st['shield'] and st['village'] == 'none', st)
            check('P3b 标注（%d 层）颜色都是浅灰（没有黑 / 深色：%s）、字号压在上限内（超限：%s）、带“底图退后”记号（%s）' % (st['n'], st['dark'][:3], st['big'][:3], st['q']), st['n'] >= 10 and not st['dark'] and not st['big'] and st['q'] == 1, st)
            z = pg.evaluate("""(function(){var r=ZRM.cur().root,m=r.querySelector('.rm-map'),p=r.querySelector('.rm-pts'),mc=getComputedStyle(m),pc=getComputedStyle(p);
              var order=[].indexOf.call(m.parentNode.children,m)<[].indexOf.call(p.parentNode.children,p);return {order:order,pe:pc.pointerEvents,mk:getComputedStyle(r.querySelector('.rm-mk')).position}})()""")
            check('P3c 站点方块和名字标签是 DOM 层、排在底图画布之后（永远在底图文字之上）', z['order'], z)
            shot(pg, 'p3_quiet.png')
            c.close()

    # ─────────── P4 底部条文案
    if want('P4'):
        with guard('P4'):
            for w, h in ((390, 844), (375, 812), (414, 896), (320, 640)):
                c = mk(br, w=w, h=h); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1, wait=False)
                o = pg.evaluate("""(function(){var l=document.querySelector('.rm-ld'),b=l.querySelector('b'),n=l.querySelector('.rm-ln'),nw=[].slice.call(n.querySelectorAll('.nw')),hint=document.querySelector('.rm-hint'),
                  br=b.getBoundingClientRect(),dl=document.querySelector('#d1 .dload');
                  return {txt:l.textContent,bh:br.height,bl:b.getClientRects().length,nwN:nw.length,nwBroken:nw.filter(function(e){return e.getClientRects().length>1}).length,
                    lines:Math.round(n.getBoundingClientRect().height/(parseFloat(getComputedStyle(n).lineHeight)||19.5)),num:n.textContent,page:dl?dl.textContent.trim():'',hint:hint.hidden?'':hint.textContent,hfs:parseFloat(getComputedStyle(hint).fontSize),hcol:getComputedStyle(hint).color,sub:getComputedStyle(n).color,nh:document.querySelectorAll('.rm-hint:not([hidden])').length}})()""")
                check('P4a %dx%d 当天条：标题一行（高 %.0f）+ 数字一行（%d 行）；数字块 %d 个都没从中间断；没有“今天：”；数字 = 页面那一行（“%s”）' % (w, h, o['bh'], o['lines'], o['nwN'], o['num']), o['bh'] <= 24 and o['lines'] <= 2 and o['nwN'] >= 2 and o['nwBroken'] == 0 and '今天' not in o['txt'] and o['num'] == o['page'], o)
                check('P4b %dx%d 说明句“%s”只出现一次、%.1fpx（小于 11）、颜色比数字淡（%s / %s）' % (w, h, o['hint'][:12], o['hfs'], o['hcol'], o['sub']), o['nh'] == 1 and o['hint'].startswith('图上的线是站与站之间的直线示意') and o['hfs'] < 11 and o['hcol'] != o['sub'], o)
                if (w, h) == (390, 844): shot(pg, 'p4_bar.png')
                # 长数字（要早起 + 对老人孩子偏累）：只能在块之间换行
                pg.evaluate("window.__lt=ZD.loadText;ZD.loadText=function(){return '走路约 3 小时 40 分 · 路上约 4 小时 20 分 · 要早起（06:30 出发） · 对老人孩子偏累'};ZRM.selectDay(0)"); pg.wait_for_timeout(400)
                o2 = pg.evaluate("(function(){var n=document.querySelector('.rm-ln'),nw=[].slice.call(n.querySelectorAll('.nw'));return {nw:nw.length,broken:nw.filter(function(e){return e.getClientRects().length>1}).length,h:n.getBoundingClientRect().height,body:document.querySelector('.rm-body').getBoundingClientRect().height,foot:document.querySelector('.rm-foot').getBoundingClientRect().bottom,bar:document.querySelector('.rm-sht').getBoundingClientRect().bottom}})()")
                check('P4c %dx%d 长数字（4 块）：块内不断（断 %d 处），只在块与块之间换行，条里的东西没溢出（按钮底 %.0f ≤ 条底 %.0f）' % (w, h, o2['broken'], o2['foot'], o2['bar']), o2['nw'] == 4 and o2['broken'] == 0 and o2['foot'] <= o2['bar'] + 0.5, o2)
                c.close()
            c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1, wait=False)
            pg.click('.rm-tb[data-i="-1"]'); pg.wait_for_timeout(500)
            o = pg.evaluate("(function(){var l=document.querySelector('.rm-ld'),n=l.querySelector('.rm-ln'),b=l.querySelector('b');return {t:b.textContent,n:n.textContent,nw:n.querySelectorAll('.nw').length,hint:document.querySelectorAll('.rm-hint:not([hidden])').length,bh:b.getBoundingClientRect().height,nh:n.getBoundingClientRect().height}})()")
            check('P4d 全程态：标题“%s”一行 + “%s”一行（同样的排版），没有说明句（%d）' % (o['t'], o['n'], o['hint']), o['bh'] <= 24 and o['nh'] <= 24 and o['nw'] == 1 and o['hint'] == 0 and '点上面的天数' in o['n'], o)
            shot(pg, 'p4_ov_bar.png')
            pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(500); pg.evaluate("ZRM.select(2)"); pg.wait_for_timeout(900)
            check('P4e 站点卡片里没有说明句（说明句只在当天视图出现）', pg.evaluate("[].every.call(document.querySelectorAll('.rm-hint'),function(e){return !e.offsetHeight})"))
            c.close()

    # ─────────── P5 全程视图：每天一个形 + 色
    if want('P5'):
        with guard('P5'):
            c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_ov(pg)
            o = pg.evaluate("""(function(){var z=ZRM.cur(),a=z.marks.filter(function(m){return m.badge}).map(function(m){var i=m.el.firstElementChild,cs=getComputedStyle(i),r=i.getBoundingClientRect();return {day:m.day,w:r.width,h:r.height,rad:cs.borderTopLeftRadius,bg:cs.backgroundColor,bd:cs.borderTopColor,col:cs.color,vis:getComputedStyle(m.el).visibility,x:r.left+r.width/2,y:r.top+r.height/2,fan:m.fan||0}});return a})()""")
            vis = [b for b in o if b['vis'] != 'hidden']
            shapes = set((b['rad'] if b['rad'] != '0px' else 'sq') + ('/hollow' if b['bg'] == b['col'] or b['bg'] != b['bd'] and b['bg'] == o[0]['col'] else '') for b in o)
            tall = max(b['h'] for b in o)
            paper = 'rgb(244, 242, 236)'; kinds = set(('round' if float(b['rad'].replace('px', '') or 0) >= 10 else 'sq') + ('-hollow' if b['bg'] == paper else '') for b in o)
            check('P5a 全程：章 ≤24px（最高 %.0f）；3 天里有 %d 种形（%s）：实心方 / 实心圆 / 空心方各不同' % (tall, len(kinds), sorted(kinds)), tall <= 24 and len(kinds) == 3, o)
            shot(pg, 'p5_ov_xa3.png')
            c.close()
            c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/ys5/', 400); open_ov(pg)
            o = pg.evaluate("(function(){var z=ZRM.cur();return z.marks.filter(function(m){return m.badge}).map(function(m){var r=m.el.firstElementChild.getBoundingClientRect();return {day:m.day,fan:m.fan||0,vis:getComputedStyle(m.el).visibility,x:r.left+r.width/2,y:r.top+r.height/2}})})()")
            vis = [b for b in o if b['vis'] != 'hidden']; fans = [b for b in o if b['fan']]
            pairs = [(a['day'], b['day'], round(math.hypot(a['x'] - b['x'], a['y'] - b['y']))) for i, a in enumerate(vis) for b in vis[i + 1:]]
            close_ = [q for q in pairs if q[2] < 22]
            check('P5b 玉树 5 天：挤在一起的天（≤3）并排摆开：%d 个并排的章、%d 个章都看得见（共 %d），互相 ≥22px（太近：%s）' % (len(fans), len(vis), len(o), close_), len(fans) >= 1 and len(vis) == len(o) and not close_, (o, close_))
            shot(pg, 'p5_ov_ys5.png')
            pg.evaluate("(function(){var z=ZRM.cur();for(var i=1;i<5;i++)z.days[i].pts[0].ll=z.days[0].pts[0].ll.slice();ZRM.selectDay(-1)})()"); pg.wait_for_timeout(800)
            o = pg.evaluate("(function(){var z=ZRM.cur(),a=z.marks.filter(function(m){return m.badge}).map(function(m){return {t:m.el.textContent,v:getComputedStyle(m.el).visibility}});return a})()")
            vis = [b for b in o if b['v'] != 'hidden']
            check('P5c 5 天挤在同一处（>3）：只留一个章，写成“1–5”（%s）' % o, len(vis) == 1 and vis[0]['t'] in ('1–5',), o)
            c.close()

    # ─────────── P6 进度条
    if want('P6'):
        with guard('P6'):
            for mode, nm in (('ok', '瓦片正常'), ('hang_most', '一半瓦片永远挂起（idle 永远不来）')):
                c = mk(br, mode=mode); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 400)
                pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); ready(pg); tiles(pg, 20000)
                t0 = time.time(); seen = 0
                while time.time() - t0 < 9:
                    s = pg.evaluate("(function(){var p=document.querySelector('.rm-prog'),i=p.firstElementChild,z=ZRM.cur();return {w:parseFloat(i.style.width)||0,o:+getComputedStyle(p).opacity,pend:p.classList.contains('rm-pend'),load:!document.querySelector('.rm-load').hidden,loaded:!!z.loaded}})()")
                    if s['pend'] and s['o'] < .05: break
                    pg.wait_for_timeout(300)
                dt = time.time() - t0
                s = pg.evaluate("(function(){var p=document.querySelector('.rm-prog'),i=p.firstElementChild;return {w:parseFloat(i.style.width)||0,o:+getComputedStyle(p).opacity,load:!document.querySelector('.rm-load').hidden}})()")
                gone = (s['o'] < .05 or s['w'] == 0) and not s['load']
                check('P6a %s：街道图出现后 %.1fs 内进度条收掉（透明度 %.2f，宽 %s%%，“加载中”提示 %s）' % (nm, dt, s['o'], s['w'], s['load']), gone and dt < 8, s)
                T.drag(250, 400, 120, 300, dt=0.01); pg.wait_for_timeout(1500); T.pinch(200, 300, 60, 200); pg.wait_for_timeout(1500)
                s2 = pg.evaluate("(function(){var p=document.querySelector('.rm-prog'),i=p.firstElementChild;return {w:parseFloat(i.style.width)||0,o:+getComputedStyle(p).opacity}})()")
                check('P6b %s：拖动 / 缩放（又在取瓦片）以后进度条不再冒出来（透明度 %.2f，宽 %s%%）' % (nm, s2['o'], s2['w']), s2['w'] == 0, s2)
                c.close()
            c = mk(br, mode='tiles'); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400)
            pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); ready(pg); pg.wait_for_function("ZRM.cur().failed", timeout=20000); pg.wait_for_timeout(800)
            s = pg.evaluate("(function(){var p=document.querySelector('.rm-prog'),i=p.firstElementChild;return {o:+getComputedStyle(p).opacity,w:parseFloat(i.style.width)||0,note:!document.querySelector('.rm-note').hidden,rt:!!document.querySelector('.rm-rt').offsetHeight,load:!document.querySelector('.rm-load').hidden}})()")
            check('P6c 瓦片全失败：进度条收掉、出现“重试”（%s）' % s, (s['o'] < .05 or s['w'] == 0) and s['note'] and s['rt'] and not s['load'], s)
            c.close()

    # ─────────── P7 线
    if want('P7'):
        with guard('P7'):
            c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1)
            if pg.evaluate("!ZRM.cur().dbg"): pg.evaluate("ZRM.cur().map.jumpTo({zoom:ZRM.cur().map.getZoom()+.001})"); pg.wait_for_timeout(300)
            o = pg.evaluate("(function(){var d=ZRM.cur().dbg;return d||null})()")
            check('P7a 画线参数：线宽 %s ≤2、不透明度 %s <1（又细又淡）、有 %s 个先后箭头（≥1）' % (o and o['lw'], o and o['alpha'], o and o['arrows']), bool(o) and o['lw'] <= 2 and o['alpha'] < 1 and o['arrows'] >= 1, o)
            # A→B→A、A→B→C→B：往返重复段只画一条
            pg.evaluate("""(function(){var z=ZRM.cur(),d=z.days[z.sel],a=d.pts[0],b=d.pts[1],c2=d.pts[2];d.pts=[a,b,a,c2,b];z.map.jumpTo({zoom:z.map.getZoom()+.001})})()"""); pg.wait_for_timeout(400)
            o = pg.evaluate("ZRM.cur().dbg"); n_before = pg.evaluate("ZRM.cur().days[ZRM.cur().sel].pts.length")
            check('P7b 站序 A→B→A→C→B（%d 个点，4 段）：不重复的只有 A–B、A–C、C–B 三条，画了 %s 条（返程不叠第二条）' % (n_before, o['segs']), o['segs'] == 3, o)
            c.close()

    # ─────────── P8 其它细节
    if want('P8'):
        with guard('P8'):
            c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1)
            sz = pg.evaluate("""(function(){var z=ZRM.cur(),bad=[];[].slice.call(z.root.querySelectorAll('.rm-mk,.rm-tb,.rm-b,.rm-go,.rm-adj2,.rm-navd')).forEach(function(e){var r=e.getBoundingClientRect();if(r.width>0&&(r.width<43.5||r.height<43.5))bad.push(e.className+':'+r.width+'x'+r.height)});return bad})()""")
            check('P8a 地图里所有能点的东西（方块 / 标签条 / 按钮）点击区 ≥44×44（不够的：%s）' % sz[:4], not sz, sz)
            # 拖地图时底部条一个字都不重绘
            pg.evaluate("window.__mut=0;(function(){var o=new MutationObserver(function(r){window.__mut+=r.length});o.observe(document.querySelector('.rm-sht'),{subtree:true,childList:true,attributes:true,characterData:true})})()")
            T.drag(250, 400, 120, 300, dt=0.012); pg.wait_for_timeout(500); T.pinch(200, 300, 60, 200); pg.wait_for_timeout(900)
            m = pg.evaluate("window.__mut")
            check('P8b 拖动 / 缩放地图期间底部条里的 DOM 变动 %d 次（=0：不闪）' % m, m == 0, m)
            # 卡片动画
            pg.evaluate("ZRM.select(2)"); pg.wait_for_timeout(300)
            an = pg.evaluate("getComputedStyle(document.querySelector('.rm-card')).animationName")
            check('P8c 站点卡片出现时有一个短动画（%s）；开了“减弱动效”就没有' % an, an == 'rm-card-in', an)
            c.close()
            c = mk(br, reduced_motion='reduce'); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1, wait=False); pg.evaluate("ZRM.select(2)"); pg.wait_for_timeout(300)
            an2 = pg.evaluate("getComputedStyle(document.querySelector('.rm-card')).animationName")
            check('P8c2 减弱动效下没有卡片动画（%s）' % an2, an2 == 'none', an2)
            c.close()
            # 暗色
            c = mk(br, dark=True); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1)
            o = pg.evaluate("""(function(){function rgb(s){return (s.match(/[\\d.]+/g)||[0,0,0]).slice(0,3).map(Number)}function L(c){return c.map(function(v){v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)}).reduce(function(a,v,i){return a+v*[.2126,.7152,.0722][i]},0)}
              function cr(a,b){var x=L(a),y=L(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
              var s=document.querySelector('.rm-nm span'),cs=getComputedStyle(s),cur=document.querySelector('.rm-nm.rm-cur span');
              var mk=document.querySelector('.rm-mk i'),mc=getComputedStyle(mk);return {lb:cr(rgb(cs.color),rgb(cs.backgroundColor)),mk:cr(rgb(mc.color),rgb(mc.backgroundColor)),bg:cs.backgroundColor,fl:getComputedStyle(document.querySelector('.rm-map canvas')).filter}})()""")
            check('P8d 暗色：站名标签对比度 %.1f、方块数字对比度 %.1f（≥4.5），底图是反色滤镜（%s）' % (o['lb'], o['mk'], o['fl'][:30]), o['lb'] >= 4.5 and o['mk'] >= 3 and 'invert' in o['fl'], o)
            shot(pg, 'p8_dark.png')
            c.close()
            # 横屏
            c = mk(br, w=844, h=390); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 400); open_day(pg, 1)
            g = geo(pg); bar = pg.evaluate("(function(){var z=ZRM.cur(),r=z.root.querySelector('.rm-sht').getBoundingClientRect();return {h:r.height,sh:z.sheetH,navd:z.root.querySelector('.rm-navd').getBoundingClientRect().bottom,vis:z.root.querySelector('.rm-tabs').getBoundingClientRect().height}})()")
            check('P8e 横屏 844×390：底部条 %dpx（=104+safe），地图可见高度 %d（≥280），导航按钮在条内（%.0f ≤ %.0f）' % (bar['h'], g['mh'], bar['navd'], g['bar']['b']), bar['h'] == 104 and g['mh'] >= 280 and bar['navd'] <= g['bar']['b'] + .5, (bar, g['mh']))
            bad = [m['n'] for m in g['mk'] if m['box']['l'] < 8 or m['box']['r'] > g['sw'] - 8 or m['box']['t'] < g['st'] + 8 or m['box']['b'] > g['mh'] - 8]
            check('P8f 横屏里方块都在可视区内（越界 %s）' % bad, not bad, bad)
            shot(pg, 'p8_landscape.png')
            c.close()
            # 安全区（headless 里没有刘海，只核样式表：左右控件用 max(8px, env(safe-area-inset-*))）
            css = open(os.path.join(SITE, 'assets', 'site.css'), encoding='utf-8').read()
            check('P8g 控件避开刘海：×、存图、右侧控件列都用 max(8px,env(safe-area-inset-left/right))；底部条加 safe-area-inset-bottom', all(re.search(k, css) for k in (r"\.rm \.rm-x\{left:max\(8px,env\(safe-area-inset-left", r"\.rm \.rm-sv\{right:max\(8px,env\(safe-area-inset-right", r"\.rm \.rm-col\{[^}]*right:max\(8px,env\(safe-area-inset-right", r"\.rm \.rm-sht\{[^}]*safe-area-inset-bottom")))
    br.close()

env.finish('map_polish_check')
sys.exit(1 if (env.fails or [e for e in env.errs if e.startswith('INJECT-NOT-APPLIED') or not env.inject]) else 0)
