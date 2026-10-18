#!/usr/bin/env python3
"""当天模型 ZD（2026-10-18）：行程只有页面时间轴这一份；整屏地图只读它（底部一条固定高度的条 + 站点卡片，没有任何列表）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/day_model_check.py build/site [--only D1,D2] [--shots DIR] [--inject 名字]
    python3 tests/day_model_check.py build/site --inject bar_list --only D1      # 反向自检：必须红
    python3 tests/day_model_inject_all.py build/site                              # 全部注入跑一遍（每种只跑它该红的那组）

D1  随机 50 条线路 × 3 天：地图读到的站（名字、坐标、顺序）= 页面时间轴里有位置的可见行；底部条的“第 N 天 · 标题 · 今天：…”= 页面每天那一行；地图层里没有任何列表（li / ol / ul / .rm-row 为 0）
D2  页面里改（去掉一站 / 撤销 / 改出发时间 / 顺路加一站 / 撤销）、地图开着：地图上的点线、底部条数字立刻跟上；卡片里的那一站被去掉 → 回到当天那一行
D3  数字：随机 200 天，走路 / 路上在 每天一行 / ZD / 建站时 data-drv / 对比表 cmp.js 里一样；改过之后页头最长一天、“这天要到 N 才结束”、复制行程里的提醒、改完小结 和 ZD 一样
D4  站点卡片：点图上站点 = 卡片（名字 = 页面这一行）；左右滑换站；“在行程里看 ›”= 关掉地图、页面滚到那一行并高亮、页面回到原来的状态；点空白回当天；底部条高度在 当天 / 卡片 / 全程 三种状态下一样；顺路灰点“加到这天”+ 撤销
D5  返回键一次只关最上面一层（导航分段层 → 地图 → 页面）
D7  按天看（.tv）、复制行程、日历读同一份：行数 / 时间 / 站名和页面可见行逐行一致（默认和改过之后）
D8  105 天长线：切天 < 100ms，地图层 DOM 节点很少
D9  触控 ≥ 44、暗色、无横向溢出、无控制台报错
D10 行 id 稳定：加 / 撤销顺路站之后，没动的行 data-zid 不变
"""
import json, math, os, random, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

R = 'assets/routemap.js'
S = 'assets/site.js'
INJ = {
    # —— D1：地图读的就是页面；没有列表 ——
    'bar_list': (R, "inst.bodyEl.innerHTML = h; inst.bodyEl.className = 'rm-body rm-day';", "inst.bodyEl.innerHTML = h + (d ? '<ol class=\"rm-tl\">' + d.pts.map(function (p) { return '<li class=\"rm-row\">' + esc(p.name) + '</li>'; }).join('') + '</ol>' : ''); inst.bodyEl.className = 'rm-body rm-day';"),      # 底部条里又放了站点列表
    'model_other': (R, "function readDays() { return W.ZD ? W.ZD.days() : []; }", "function readDays() { var a = W.ZD ? W.ZD.days() : []; a.forEach(function (d) { d.pts = d.pts.slice(1); }); return a; }"),                 # 地图读的站少一个（不是页面那份）
    # —— D2：同步 ——
    'bar_nosync': (R, "inst.off = ZD.on(function () { clearTimeout(inst.rft); inst.rft = setTimeout(function () { refresh(inst); }, 0); });", "inst.off = ZD.on(function () {});"),            # 页面里改了，地图不跟
    # —— D3：数字 ——
    'num_bar': (R, "　今天：' + esc(ZD.loadText(ZD.facts(d)))", "　今天：' + esc(ZD.loadText(ZD.facts(d))).replace('路上约', '开车约')"),                                                       # 底部条的数字另算
    'num_sum': (S, "，路上约 '+zLf(zf.drive||0)", "，路上约 '+zLf((zf.drive||0)+10)"),                                                                                             # “改完：…路上约”另算
    'num_glance': (S, "(mx/60).toFixed(1)+' 小时'}else{t=g0[0]", "(mx/60+.5).toFixed(1)+' 小时'}else{t=g0[0]"),                                                                         # 页头最长一天另算
    'num_end': (S, "这天要到 '+zf.endHm+' 才结束", "这天要到 '+ZD.hhmm(zf.end+30)+' 才结束"),                                                                                          # 结束时间另算
    # —— D4：卡片 / 在行程里看 ——
    'see_noop': (R, "if (act === 'see' && p) { closeInst(inst); return; }", "if (act === 'see' && p) { return; }"),                                                                       # “在行程里看”点了没反应
    'see_noscroll': (R, "inst.y = Math.max(0, r.top + inst.y - Math.round((W.innerHeight || 600) / 3));", "inst.y = inst.y;"),                                                           # 关了地图页面不滚到那一行
    'see_nohi': (R, "row.classList.add('flash'); setTimeout(function () { row.classList.remove('flash'); }, 1600);", ""),                                                             # 那一行不高亮
    'card_taller': ('assets/site.css', ".rm .rm-sht.m-card .rm-tabs,.rm .rm-sht.m-card .rm-foot{display:none}", ".rm .rm-sht.m-card .rm-tabs,.rm .rm-sht.m-card .rm-foot{display:none}.rm .rm-sht.m-card{height:calc(260px + env(safe-area-inset-bottom,0px))}"),   # 卡片时条变高
    'swipe_off': (R, "if (inst.progScroll || !(down || now() < until)) return; clearTimeout(t);", "return; clearTimeout(t);"),                                                      # 卡片左右滑不换站
    # —— D7：别的视图 ——
    'tv_other': (S, "var rows=dd.items,now=new Date()", "var rows=dd.items.slice(1),now=new Date()"),                                                       # 按天看少一行
    'copy_other': (S, "ZD.dayOf(d).items.forEach(function(x){   // 读当天模型", "ZD.dayOf(d).items.filter(function(x){return x.kind!=='eat'}).forEach(function(x){   // 读当天模型"),   # 复制行程没有吃饭
    'ics_other': (S, "rows=ZD.dayOf(sec).items.map(function(x){return x.t+' '+x.name});", "rows=ZD.dayOf(sec).items.filter(function(x){return x.kind!=='dep'}).map(function(x){return x.t+' '+x.name});"),   # 日历少了车程行
    # —— D10 ——
    'zid_unstable': (S, "if(!z||z.indexOf(dk+'.')!==0){if(k!=null)z=dk+'.'+k;", "if(true){if(k!=null)z=dk+'.'+j;"),                                                                  # 行 id 按位置给（插了站就变）
}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
def want(k): return ONLY is None or k in ONLY

LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}


def stub(c):
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), lambda r: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b''))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), lambda r: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG))


def mk(br, dark=False, w=390, h=844):
    c = new_ctx(br, None, w=w, h=h, dark=dark); stub(c); return c


def ready(pg, timeout=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=timeout)


def open_day(pg, n):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n); ready(pg); pg.wait_for_timeout(500)


def cur(pg, expr): return pg.evaluate("(function(){var r=ZRM.cur();return r?(" + expr + "):null})()")


# 页面这边：不经过 ZD，直接从 DOM 读（独立判据）
PAGE_ROWS = """(i)=>{var secs=[].slice.call(document.querySelectorAll('article.trip section.day')).filter(function(s){return !s.hidden}),sec=secs[i];if(!sec)return null;
 var n=function(t){return String(t==null?'':t).replace(/\\s+/g,' ').trim()};
 return [].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return !r.hidden}).map(function(r){var m=r.querySelector('.m'),s=r.querySelector('.s'),c=r.classList,
   kind=c.contains('dep')?'dep':c.contains('eat')?'eat':c.contains('stay')?'stay':c.contains('fun')?'fun':'see',clw=r.querySelector('.clw'),tix=r.querySelector('.tix');
   return {kind:kind,t:n(r.querySelector('time').textContent),name:n((m.childNodes[0]||m).textContent),leg:kind==='dep'&&s?n(s.textContent):'',book:!!r.querySelector('.bkn'),clw:clw?n(clw.textContent):'',tix:tix?n(tix.textContent):'',adj:!!r.querySelector('.adj'),
     added:r.getAttribute('data-np')==='v',zid:r.getAttribute('data-zid')||''}})}"""
def state(pg):
    return pg.evaluate("""(function(){var z=ZRM.cur();if(!z)return null;var c=z.view.cam(),sh=document.querySelector('.rm-sht').getBoundingClientRect();return {sel:z.sel,cur:z.cur,curG:z.curG,curH:z.curH,mode:z.mode,sh:Math.round(sh.height),z:c.z,sy:window.scrollY,top:document.body.style.top,vv:visualViewport.scale}})()""")


def map_pts(pg):
    """地图读到的站：[名字, 纬度, 经度]（独立于面板：直接读 ZRM 当前图层的模型）"""
    return pg.evaluate("(function(){var z=ZRM.cur(),d=z.days[z.sel];return d?d.pts.map(function(p){return [p.name,p.ll[0],p.ll[1]]}):null})()")


PAGE_PTS = """(i)=>{var secs=[].slice.call(document.querySelectorAll('article.trip section.day')).filter(function(s){return !s.hidden}),sec=secs[i];if(!sec)return null;
 return [].slice.call(sec.querySelectorAll('.tl > .r[data-ll]')).filter(function(r){return !r.hidden}).map(function(r){var m=r.querySelector('.m'),p=r.getAttribute('data-ll').split(',');return [String((m.childNodes[0]||m).textContent).replace(/\\s+/g,' ').trim(),parseFloat(p[0]),parseFloat(p[1])]})}"""


def same_pts(pg, i):
    a = map_pts(pg); b = pg.evaluate(PAGE_PTS, i)
    if a is None or b is None: return ['没有这一天']
    if len(a) != len(b): return ['站数 地图 %d / 页面 %d' % (len(a), len(b))]
    for k, (x, y) in enumerate(zip(a, b)):
        if x[0] != y[0] or abs(x[1] - y[1]) > 1e-6 or abs(x[2] - y[2]) > 1e-6: return ['第 %d 站 地图 %s / 页面 %s' % (k + 1, x[0], y[0])]
    return []


def wait_same(pg, i, tries=14):
    bad = ['?']
    for _ in range(tries):
        pg.wait_for_timeout(150); bad = same_pts(pg, i)
        if not bad: return bad
    return bad


def bar_text(pg): return pg.evaluate("(document.querySelector('.rm-ld')||{}).textContent||''")


def dload(pg, i):
    return pg.evaluate("(function(i){var s=[].slice.call(document.querySelectorAll('article.trip section.day')).filter(function(x){return !x.hidden})[i];var e=s&&s.querySelector('.dload');return e?e.textContent.trim():''})", i)


def route_days(pg):
    return pg.evaluate("ZD.days().map(function(d){return d.pts.length})")


def main():
    rnd = random.Random(20261018)
    routes = sorted(os.listdir(os.path.join(env.site, 'trip')))
    with sync_playwright() as p:
        br = p.chromium.launch(args=LAUNCH)
        _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()

        # ─────────── D1 地图读的就是页面；地图层里没有列表
        if want('D1'):
            with guard('D1'):
                c = mk(br); pg = new_page(env, c); n_days = 0; bad_all = []; head_bad = []; list_bad = []; cand = rnd.sample(routes, 200); done = 0
                for rid in cand:
                    if done >= 50 and n_days >= 150: break
                    goto(env, pg, '/trip/%s/' % rid, 450)
                    if not pg.evaluate("!!window.ZD&&document.querySelector('.rm-open')"): continue
                    pts = route_days(pg); ok = [i for i, k in enumerate(pts) if k >= 2]
                    if not ok: continue
                    done += 1; ds = rnd.sample(ok, min(3, len(ok)))
                    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % (ds[0] + 1))
                    pg.click('#d%d .rm-open' % (ds[0] + 1)); ready(pg); pg.wait_for_timeout(250)
                    for k, i in enumerate(ds):
                        if k: pg.click('.rm-tb[data-i="%d"]' % i); pg.wait_for_timeout(150)
                        n_days += 1; b = same_pts(pg, i)
                        if b: bad_all.append('%s 第%d天：%s' % (rid, i + 1, b[0]))
                        dl = dload(pg, i); bt = bar_text(pg)
                        if not bt.strip().endswith(dl) or ('第 %d 天' % (i + 1)) not in bt: head_bad.append('%s 第%d天 条“%s” 页面“%s”' % (rid, i + 1, bt[:60], dl))
                        nl = pg.evaluate("document.querySelectorAll('.rm li,.rm ol,.rm ul,.rm .rm-row,.rm .rm-tl').length")
                        if nl: list_bad.append('%s 第%d天 %d 个列表元素' % (rid, i + 1, nl))
                check('D1a 随机 %d 条线路 × 3 天（共 %d 天）：地图读到的站（名字 / 坐标 / 顺序）= 页面时间轴里有位置的可见行；不一致 %d 天%s' % (done, n_days, len(bad_all), ('：' + bad_all[0]) if bad_all else ''), done >= 50 and not bad_all and n_days >= 150, (done, n_days, bad_all[:3]))
                check('D1b 底部条“第 N 天 · 标题　今天：…”的数字 = 页面每天那一行（%d 天里不一致 %d）%s' % (n_days, len(head_bad), ('：' + head_bad[0]) if head_bad else ''), not head_bad, head_bad[:3])
                check('D1c 地图层里没有任何列表（li / ol / ul / .rm-row / .rm-tl 都是 0；%d 天里有 %d 天有）%s' % (n_days, len(list_bad), list_bad[:1]), not list_bad, list_bad[:3])
                c.close()

        # ─────────── D2 页面里改，地图开着，立刻跟上
        if want('D2'):
            with guard('D2'):
                c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
                open_day(pg, 2)
                b0 = same_pts(pg, 1); n0 = len(map_pts(pg)); t0 = bar_text(pg)
                check('D2a0 起点：地图读到的站 = 页面（%d 站，%s）' % (n0, b0), not b0 and n0 == 3, b0)
                pg.evaluate("[].slice.call(document.querySelectorAll('#d2 .tl > .r.see:not([hidden]) .adj'))[1].click()"); pg.wait_for_selector('.pk.npk [data-x]'); pg.click('.pk.npk [data-x]'); b1 = wait_same(pg, 1)
                n1 = len(map_pts(pg)); mk1 = pg.evaluate("ZRM.cur().marks.filter(function(m){return m.kind==='n'}).length")
                check('D2a1 页面里“去掉这一站”：地图上的站少一个（%d → %d，图上编号方块 %d），名字 / 坐标和页面一致%s；底部条数字 = 页面“%s”' % (n0, n1, mk1, b1, dload(pg, 1)), n1 == n0 - 1 and mk1 == n1 and not b1 and bar_text(pg).strip().endswith(dload(pg, 1)), (n0, n1, mk1, b1, bar_text(pg)))
                pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); b2 = wait_same(pg, 1)
                check('D2a2 页面里撤销：地图回到 %d 站%s' % (n0, b2), len(map_pts(pg)) == n0 and not b2 and bar_text(pg) == t0, (b2, bar_text(pg), t0))
                pg.evaluate("document.querySelector('#d2 .st').click()"); pg.wait_for_selector('.pk .stg button'); pg.click('.pk .stg button[data-v="11:00"]'); pg.wait_for_timeout(500)
                check('D2a3 页面里改出发 11:00：底部条里的数字 = 页面每天一行（%s）' % dload(pg, 1), bar_text(pg).strip().endswith(dload(pg, 1)) and not same_pts(pg, 1), (bar_text(pg), dload(pg, 1)))
                pg.evaluate("document.querySelector('#d2 .st').click()"); pg.wait_for_selector('.pk .stg button'); pg.click('.pk .stg button[data-v="09:00"]'); pg.wait_for_timeout(400)
                pg.evaluate("[].slice.call(document.querySelectorAll('#d2 .tl > .r.see:not([hidden]) .adj'))[0].click()"); pg.wait_for_selector('.pk.npk [data-np="ins"]')
                if pg.evaluate("!document.querySelector('.pk.npk [data-np=\"ins\"]').disabled"):
                    pg.click('.pk.npk [data-np="ins"]'); pg.wait_for_selector('.pk.npk .npc', timeout=15000); pg.click('.pk.npk .npc'); b4 = wait_same(pg, 1)
                    check('D2a4 页面里“在这之后加一个”：地图多一站（%d → %d）、一致%s' % (n0, len(map_pts(pg)), b4), len(map_pts(pg)) == n0 + 1 and not b4, b4)
                    pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); b5 = wait_same(pg, 1)
                    check('D2a5 页面里撤销加站：地图回到 %d 站%s' % (n0, b5), len(map_pts(pg)) == n0 and not b5, b5)
                else: check('D2a4 第 2 天能在页面里加顺路站', False, '置灰')
                # 卡片里那一站被页面去掉 → 回到当天那一行
                pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(600)
                mp = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='n'&&m.n===2)return [m.px,m.py]}return null})()")
                T = Touch(c, pg); T.tap(mp[0], mp[1]); pg.wait_for_timeout(1300); m1 = state(pg)['mode']
                pg.evaluate("[].slice.call(document.querySelectorAll('#d1 .tl > .r.see:not([hidden]) .adj'))[1].click()"); pg.wait_for_selector('.pk.npk [data-x]'); pg.click('.pk.npk [data-x]'); pg.wait_for_timeout(700)
                m2 = state(pg)
                check('D2b 卡片里那一站被页面去掉：底部条回到当天那一行（%s → %s，cur=%d）' % (m1, m2['mode'], m2['cur']), m1 == 'card' and m2['mode'] == 'day' and m2['cur'] == 0, (m1, m2))
                c.close()

        # ─────────── D3 数字
        if want('D3'):
            with guard('D3a'):
                c = mk(br); pg = new_page(env, c); cmp_js = open(os.path.join(env.site, 'assets', 'cmp.js'), encoding='utf-8').read()
                cm = json.loads(re.search(r'window\.ZCMP=(.*);', cmp_js).group(1)); tot = 0; bad = []; badmx = []; cand = rnd.sample(routes, 120)
                for rid in cand:
                    if tot >= 200: break
                    goto(env, pg, '/trip/%s/' % rid, 350)
                    if not pg.evaluate("!!window.ZD&&document.querySelectorAll('article.trip section.day').length"): continue
                    o = pg.evaluate("""(function(){var ds=ZD.days();return ds.map(function(d){var f=ZD.facts(d),dl=d.sec.querySelector(':scope > .dload');return {dl:dl?dl.textContent:'',w:dl?+dl.dataset.w:-1,d:dl?+dl.dataset.d:-1,zt:ZD.loadText(f),zw:f.walk,zd:f.drive,drv:+d.sec.dataset.drv||0}})})()""")
                    for i, x in enumerate(o):
                        tot += 1
                        if not (x['dl'] == x['zt'] and x['w'] == x['zw'] and x['d'] == x['zd'] and x['d'] == x['drv']): bad.append('%s 第%d天 %s' % (rid, i + 1, x))
                    if rid in cm:
                        mw = max(x['zw'] for x in o); md = max(x['zd'] for x in o)
                        if mw != cm[rid][2] or md != cm[rid][3]: badmx.append('%s 页面最长一天 走路 %d 路上 %d / cmp.js %s' % (rid, mw, md, cm[rid][2:4]))
                check('D3a 随机 %d 天（%d 条线）：每天一行的“走路 / 路上”= ZD 的算法 = 建站时算好的 data-drv；不一致 %d 天%s' % (tot, len(cand), len(bad), ('：' + bad[0]) if bad else ''), tot >= 200 and not bad, bad[:3])
                check('D3b 对比表（cmp.js）里每条线“最长一天走路 / 路上”= 页面（ZD）算出来的最长一天；不一致 %d 条%s' % (len(badmx), ('：' + badmx[0]) if badmx else ''), not badmx, badmx[:3])
                c.close()
            with guard('D3b'):      # 改过之后：页头、提醒、复制行程、地图底部条
                c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 800)
                g0 = pg.evaluate("document.querySelector('.glance [data-gd]').textContent")
                pg.evaluate("document.querySelector('#d3').scrollIntoView({behavior:'instant'})"); pg.wait_for_timeout(200)
                pg.evaluate("[].slice.call(document.querySelectorAll('#d3 .tl > .r.see:not([hidden]) .adj'))[0].click()"); pg.wait_for_selector('.pk.npk [data-x]'); pg.click('.pk.npk [data-x]'); pg.wait_for_timeout(500)
                o = pg.evaluate("""(function(){var ds=ZD.days(),mx=0;ds.forEach(function(d){var f=ZD.facts(d);if(f.drive>mx)mx=f.drive});var dls=[].map.call(document.querySelectorAll('.day > .dload'),function(e){return +e.dataset.d}),m2=Math.max.apply(null,dls);
                    return {gd:document.querySelector('.glance [data-gd]').textContent,mx:mx,m2:m2,txt:(mx/60).toFixed(1)}})()""")
                check('D3c 去掉一站后页头“最长一天”重算：%s（ZD 最长 %d 分 = 每天一行的最长 %d 分 → %s 小时；改前“%s”）' % (o['gd'], o['mx'], o['m2'], o['txt'], g0), o['mx'] == o['m2'] and o['txt'] + ' 小时' in o['gd'] and (o['gd'] != g0 or o['mx'] == 190), (o, g0))
                pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(500)
                check('D3d 撤销后页头回到原样（%s）' % pg.evaluate("document.querySelector('.glance [data-gd]').textContent"), pg.evaluate("document.querySelector('.glance [data-gd]').textContent") == g0, g0)
                pg.evaluate("document.querySelector('#d2 .st').click()"); pg.wait_for_selector('.pk .stg button'); pg.click('.pk .stg button[data-v="16:00"]'); pg.wait_for_timeout(500)
                o = pg.evaluate("""(function(){var d=ZD.days()[1],f=ZD.facts(d),w=d.sec.querySelector('.latewarn p:not(.sum):not(.gap)'),sm=d.sec.querySelector('.latewarn .sum');return {end:f.endHm,start:f.start,warn:w?w.textContent:'',sum:sm?sm.textContent:'',drive:ZD.fmt(f.drive),copy:window.zTripText()}})()""")
                m = re.search(r'这天要到 (\d\d:\d\d) 才结束', o['warn']); ms = re.search(r'这天 (\d\d:\d\d) 结束', o['sum']); mc = re.search(r'提醒：按 (\d\d:\d\d) 出发，这天要到 (\d\d:\d\d) 才结束', o['copy'])
                check('D3e 晚出发 16:00：页面“这天要到 %s 才结束”= ZD 结束时间 %s = “改完：这天 %s 结束”；复制行程里的提醒同一个时间（%s）' % (m and m.group(1), o['end'], ms and ms.group(1), mc and mc.group(2)), bool(m and ms and mc) and m.group(1) == o['end'] == ms.group(1) == mc.group(2) and mc.group(1) == o['start'], o)
                check('D3f “改完”那句的“路上约 %s”= 每天一行的路上（%s）' % (o['drive'], pg.evaluate("document.querySelector('#d2 .dload').textContent")), ('路上约 ' + o['drive']) in o['sum'] and ('路上约 ' + o['drive']) in pg.evaluate("document.querySelector('#d2 .dload').textContent"), o)
                c.close()

        # ─────────── D4 站点卡片 / 在行程里看 / 条高度
        if want('D4'):
            with guard('D4a'):
                c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
                pg.evaluate("window.scrollTo({top:1500,behavior:'instant'})"); pg.wait_for_timeout(250); sy0 = pg.evaluate("window.scrollY")
                open_day(pg, 1); pg.wait_for_timeout(500)
                s0 = state(pg)
                mp = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='n'&&m.n===2)return [m.px,m.py]}return null})()")
                T.tap(mp[0], mp[1]); pg.wait_for_timeout(1500); s1 = state(pg)
                nm = pg.evaluate("(document.querySelector('.rm-card[data-n=\"2\"] .rm-cname')||{}).textContent")
                pn = pg.evaluate(PAGE_PTS, 0)[1][0]
                btn = pg.evaluate("[].map.call(document.querySelectorAll('.rm-card[data-n=\"2\"] button[data-act]'),function(b){return b.textContent.trim()})")
                check('D4a 点图上第 2 站：底部条换成该站卡片（mode=%s，名字“%s”= 页面这一行“%s”），按钮 %s，页面没动（scrollY %s）' % (s1['mode'], nm, pn, btn, s1['sy']), s1['mode'] == 'card' and nm == pn and '在行程里看 ›' in btn and '导航到这里' in btn and s1['sy'] == 0 and s1['top'] == s0['top'], (s1, nm, pn, btn))
                check('D4b 底部条高度在 当天 / 卡片 两种状态一样（%d / %d）' % (s0['sh'], s1['sh']), s0['sh'] == s1['sh'], (s0['sh'], s1['sh']))
                nz = pg.evaluate("document.querySelectorAll('.rm li,.rm ol,.rm ul,.rm .rm-row').length"); check('D4c 卡片状态下地图层里也没有列表（%d）' % nz, nz == 0, nz)
                bt = pg.evaluate("(function(){var r=document.querySelector('.rm-sht').getBoundingClientRect();return [r.top+r.height*.45]})()")[0]
                T.drag(330, bt, 50, bt, steps=8, dt=0.012); pg.wait_for_timeout(1700); s2 = state(pg)
                check('D4d 卡片向左滑：切到下一站（cur %d → %d），底部条高度不变（%d）' % (s1['cur'], s2['cur'], s2['sh']), s2['cur'] == 3 and s2['sh'] == s0['sh'], (s1, s2))
                T.tap(60, 160); pg.wait_for_timeout(800); s3 = state(pg)
                check('D4e 点地图空白：回到当天那一行（mode=%s，cur=%d），条高度不变（%d）' % (s3['mode'], s3['cur'], s3['sh']), s3['mode'] == 'day' and s3['cur'] == 0 and s3['sh'] == s0['sh'], s3)
                pg.click('.rm-tb[data-i="-1"]'); pg.wait_for_timeout(500); s4 = state(pg)
                check('D4f 全程总览：底部条高度也一样（%d），没有列表' % s4['sh'], s4['sh'] == s0['sh'] and pg.evaluate("document.querySelectorAll('.rm li,.rm ol,.rm ul,.rm .rm-row').length") == 0, s4)
                pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(600)
                mp = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='n'&&m.n===3)return [m.px,m.py]}return null})()")
                zid = pg.evaluate("ZRM.cur().days[0].pts[2].zid"); T.tap(mp[0], mp[1]); pg.wait_for_timeout(1400)
                pg.click('.rm-card[data-n="3"] button[data-act="see"]'); pg.wait_for_timeout(1200)
                r = pg.evaluate("(function(z){var r=document.querySelector('[data-zid=\"'+z+'\"]'),b=r.getBoundingClientRect();return {top:b.top,ih:innerHeight,flash:r.classList.contains('flash'),map:!!document.querySelector('.rm'),kinds:ZL.kinds(),lock:document.body.classList.contains('rm-lock')}})", zid)
                check('D4g 卡片“在行程里看 ›”：地图关了（层栈 %s）、页面滚到第 1 天第 3 站那一行（离视口顶 %d px）并高亮（flash=%s）' % (r['kinds'], r['top'], r['flash']), not r['map'] and r['kinds'] == [] and not r['lock'] and 0 <= r['top'] < r['ih'] - 40 and r['flash'], r)
                c.close()
            with guard('D4b'):      # 顺路灰点：加到这天 + 撤销
                c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
                open_day(pg, 3)
                try: pg.wait_for_function("document.querySelectorAll('.rm-pts .rm-gy').length>0", timeout=9000)
                except Exception: pass
                gi = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='g'&&m.px>20&&m.px<370&&m.py>80&&m.py<380)return [m.px,m.py,m.gi]}return null})()")
                if not gi:
                    pg.evaluate("ZRM.cur().view.zoomBy(-2)"); pg.wait_for_timeout(800)
                    gi = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='g'&&m.px>20&&m.px<370&&m.py>80&&m.py<380)return [m.px,m.py,m.gi]}return null})()")
                check('D4h 第 3 天有可点的顺路灰点', bool(gi), gi)
                if gi:
                    n0 = len(map_pts(pg)); T.tap(gi[0], gi[1]); pg.wait_for_timeout(1000)
                    gc = pg.evaluate("(function(){var c=document.querySelector('.rm-gcard');return c?c.innerText:''})()")
                    check('D4i 灰点卡片：名字、“+N 分钟”、“加到这天”（%s）' % gc.replace('\n', ' ')[:50], bool(re.search(r'\+\d+ 分钟', gc)) and pg.evaluate("!!document.querySelector('.rm-go[data-act=\"addg\"]')"), gc)
                    pg.click('.rm-go[data-act="addg"]'); b1 = wait_same(pg, 2)
                    check('D4j 加到这天：页面和地图都多一站（%d → %d）%s' % (n0, len(map_pts(pg)), b1), len(map_pts(pg)) == n0 + 1 and not b1 and pg.evaluate("!!document.querySelector('#d3 .tl > .r[data-np=v]')"), b1)
                    pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); b2 = wait_same(pg, 2)
                    check('D4k 撤销：回到 %d 站%s' % (n0, b2), len(map_pts(pg)) == n0 and not b2, b2)
                c.close()

        # ─────────── D5 返回键一次只关一层
        if want('D5'):
            with guard('D5'):
                c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
                pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); y0 = pg.evaluate("window.scrollY")
                pg.click('#d2 .rm-open'); ready(pg); pg.wait_for_timeout(500)
                pg.click('.rm-navd'); pg.wait_for_selector('.pk.rm-sheet', timeout=4000); k1 = pg.evaluate("ZL.kinds()")
                pg.go_back(); pg.wait_for_timeout(600); k2 = pg.evaluate("ZL.kinds()"); still = pg.evaluate("!!document.querySelector('.rm')")
                check('D5a 地图之上开着“导航这一天”分段层（%s）：返回键只关它，地图还在（%s，地图在 %s）' % (k1, k2, still), k1 == ['map', 'nav'] and k2 == ['map'] and still, (k1, k2, still))
                pg.go_back(); pg.wait_for_timeout(900); k3 = pg.evaluate("ZL.kinds()")
                check('D5b 再按一次返回键：地图关了（%s），页面回到原来的位置（scrollY %s → %s）' % (k3, y0, pg.evaluate("window.scrollY")), k3 == [] and not pg.evaluate("!!document.querySelector('.rm')") and abs(pg.evaluate("window.scrollY") - y0) < 4, (k3, y0))
                c.close()

        # ─────────── D7 按天看 / 复制行程 / 日历 读同一份
        if want('D7'):
            with guard('D7'):
                c = mk(br); pg = new_page(env, c)
                for rid, label in (('xa3', '默认'), ('xa3', '去掉一站后'), ('xb96a', '长线')):
                    goto(env, pg, '/trip/%s/' % rid, 700)
                    if label == '去掉一站后':
                        pg.evaluate("[].slice.call(document.querySelectorAll('#d1 .tl > .r.see:not([hidden]) .adj'))[1].click()"); pg.wait_for_selector('.pk.npk [data-x]'); pg.click('.pk.npk [data-x]'); pg.wait_for_timeout(500)
                    pr = pg.evaluate(PAGE_ROWS, 0)
                    txt = pg.evaluate("window.zTripText()"); lines = txt.split('\n'); bad = []
                    hdr = [k for k, l in enumerate(lines) if l.startswith('第') and ' · ' in l]
                    seg = lines[hdr[0] + 1: hdr[1]] if len(hdr) > 1 else lines[hdr[0] + 1:]
                    seg = [l for l in seg if re.match(r'^  \d\d:\d\d  |^  晚上  ', l)]
                    if len(seg) != len(pr): bad.append('复制行程第 1 天行数 %d / 页面 %d' % (len(seg), len(pr)))
                    for k in range(min(len(seg), len(pr))):
                        if not seg[k].strip().startswith(pr[k]['t']) or pr[k]['name'] not in seg[k]: bad.append('第 %d 行 %s / %s' % (k + 1, seg[k].strip()[:30], pr[k]['name'])); break
                    check('D7a [%s %s] 复制行程第 1 天的每一行 = 页面可见行（%d 行）%s' % (rid, label, len(pr), bad), not bad, bad)
                    ics = pg.evaluate("(function(){var out='';var oc=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){};try{out=window.zIcs()}finally{HTMLAnchorElement.prototype.click=oc}return out})()")
                    unf = ics.replace('\r\n ', '').replace('\\n', '\n'); d1 = unf.split('BEGIN:VEVENT')[1]
                    miss = [r for r in pr if (r['t'] + ' ' + r['name']) not in d1]
                    check('D7b [%s %s] 日历第 1 天的描述里每一行（时间 + 名字）= 页面可见行，缺 %d 行' % (rid, label, len(miss)), not miss and len(pr) > 3, [m['name'] for m in miss][:3])
                    pg.evaluate("document.querySelector('.tvbtn').click()"); pg.wait_for_selector('.tv .tvl'); pg.wait_for_timeout(200)
                    tv = pg.evaluate("[].slice.call(document.querySelectorAll('.tv .tvl li')).map(function(l){return {t:l.querySelector('time').textContent.trim(),n:l.querySelector('b').textContent.replace(/\\s+/g,' ').trim()}})")
                    tvi = pg.evaluate("document.querySelector('.tv .tvtabs .on')&&[].indexOf.call(document.querySelectorAll('.tv .tvtabs button'),document.querySelector('.tv .tvtabs .on'))")
                    pr0 = pg.evaluate(PAGE_ROWS, tvi)
                    badt = [] if len(tv) == len(pr0) and all(a['t'] == b['t'] and a['n'] == b['name'] for a, b in zip(tv, pr0)) else ['按天看 %d 行 / 页面 %d 行' % (len(tv), len(pr0))]
                    check('D7c [%s %s] 按天看第 %d 天的每一行 = 页面可见行（%d 行）%s' % (rid, label, (tvi or 0) + 1, len(pr0), badt), not badt, badt)
                    pg.evaluate("document.querySelector('.tv .tvx').click()")
                c.close()

        # ─────────── D8 105 天长线
        if want('D8'):
            with guard('D8'):
                c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xb96a/', 1200)
                nd = pg.evaluate("ZD.days().length")
                pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg); pg.wait_for_timeout(500)
                nodes = pg.evaluate("document.querySelectorAll('.rm *').length")
                ms = []
                for i in rnd.sample(range(nd), 12):
                    ms.append(pg.evaluate("(function(i){var t=performance.now();ZRM.selectDay(i);return performance.now()-t})", i))
                check('D8a 105 天长线：切天（12 次随机）最慢 %.0f ms、平均 %.0f ms，都 < 100ms；地图层 DOM 节点 %d 个（< 600）' % (max(ms), sum(ms) / len(ms), nodes), max(ms) < 100 and nodes < 600 and nd >= 100, (ms, nodes, nd))
                t = pg.evaluate("(function(){var t=performance.now();var n=ZD.days().length;return performance.now()-t})()")
                check('D8b 105 天 ZD.days() 全部重读 %.0f ms < 60ms' % t, t < 60, t)
                c.close()

        # ─────────── D9 触控 / 暗色 / 溢出
        if want('D9'):
            with guard('D9'):
                c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 700)
                open_day(pg, 3); pg.wait_for_timeout(500); bad = []
                for sel in ('.rm-tb[data-i="1"]', '.rm-navd', '.rm-x', '.rm-sv'):
                    h = pg.evaluate(HIT, pg.query_selector(sel))
                    if not h or h['w'] < 43.9 or h['h'] < 43.9: bad.append((sel, h))
                mp = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='n'&&m.n===1)return [m.px,m.py]}return null})()")
                T.tap(mp[0], mp[1]); pg.wait_for_timeout(1200)
                for sel in ('.rm-card button[data-act="see"]', '.rm-card button[data-act="go"]', '.rm-card .rm-cb'):
                    h = pg.evaluate(HIT, pg.query_selector(sel))
                    if not h or h['w'] < 43.9 or h['h'] < 43.9: bad.append((sel, h))
                check('D9a 底部条和卡片里的按钮（天标签、导航这一天、在行程里看、导航到这里、回当天）点击区 ≥ 44×44（elementFromPoint 实测）%s' % bad, not bad, bad)
                ov = pg.evaluate("(function(){var b=document.querySelector('.rm-body');return {sw:b.scrollWidth,cw:b.clientWidth,dsw:document.documentElement.scrollWidth,iw:innerWidth}})()")
                check('D9b 底部条没有横向溢出（scrollWidth %d ≤ clientWidth %d；页面 %d ≤ %d）' % (ov['sw'], ov['cw'], ov['dsw'], ov['iw']), ov['sw'] <= ov['cw'] and ov['dsw'] <= ov['iw'], ov)
                c.close()
                c = mk(br, dark=True); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700)
                open_day(pg, 2); pg.wait_for_timeout(500)
                o = pg.evaluate("""(function(){var lum=function(c){var v=c.match(/[\\d.]+/g).map(Number);return(v[0]*.3+v[1]*.59+v[2]*.11)};return {bg:lum(getComputedStyle(document.querySelector('.rm-sht')).backgroundColor),txt:lum(getComputedStyle(document.querySelector('.rm-ld b')).color)}})()""")
                check('D9c 暗色：底部条底色是暗的（亮度 %.0f）、文字是亮的（%.0f）' % (o['bg'], o['txt']), o['bg'] < 90 and o['txt'] > 150, o)
                if env.shots: pg.screenshot(path=os.path.join(env.shots, 'dark_bar.png'))
                c.close()

        # ─────────── D10 行 id 稳定
        if want('D10'):
            with guard('D10'):
                c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 800)
                z0 = pg.evaluate("ZD.days()[1].items.map(function(x){return x.zid+'|'+x.name})")
                pg.evaluate("[].slice.call(document.querySelectorAll('#d2 .tl > .r.see:not([hidden]) .adj'))[0].click()"); pg.wait_for_selector('.pk.npk [data-np="ins"]')
                if pg.evaluate("!document.querySelector('.pk.npk [data-np=\"ins\"]').disabled"):
                    pg.click('.pk.npk [data-np="ins"]'); pg.wait_for_selector('.pk.npk .npc', timeout=15000); pg.click('.pk.npk .npc'); pg.wait_for_timeout(600)
                    z1 = pg.evaluate("ZD.days()[1].items.map(function(x){return x.zid+'|'+x.name})")
                    before = dict(x.split('|', 1)[::-1] for x in z0); after = dict(x.split('|', 1)[::-1] for x in z1)
                    moved = [n for n, z in before.items() if n in after and after[n] != z]
                    check('D10a 加了一站以后，原来每一行的 id 不变（%d 行里变了 %d：%s）' % (len(before), len(moved), moved[:2]), not moved and len(z1) > len(z0), (moved, z0[:3], z1[:3]))
                    pg.wait_for_selector('.toast-act'); pg.click('.toast-act'); pg.wait_for_timeout(500)
                    z2 = pg.evaluate("ZD.days()[1].items.map(function(x){return x.zid+'|'+x.name})")
                    check('D10b 撤销以后全部回到原来的 id（%d 行）' % len(z0), z2 == z0, (z0[:3], z2[:3]))
                else: check('D10a 能加顺路站', False, '置灰')
                c.close()
    env.finish('当天模型 day_model_check')


main()
