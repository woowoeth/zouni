#!/usr/bin/env python3
"""第三轮收尾小项 A1–A9（2026-10-18，来自 5 位模拟用户的报告）。会红，每一项都有反向自检。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/a_batch3_check.py build/site [--shots DIR] [--only A1,A5]
    python3 tests/a_batch3_check.py build/site --inject 名字     # 只改送到浏览器的 site.js / site.css / routemap.js / sans.css（磁盘不动），对应判据必须变红

A1  “累不累”同源：每天的“走路约 / 开车约（不开车线写路上约）”、开车/路上那一格、页头“最长一天”、对比表、时间表里的移动行，是同一个数；
    不开车的线（郑和 hzh1）火车、打车也算进去，页头写“路上最长 X 小时”，不再是只有“不开车”
A2  “出发前”：说明（没有复选框、不加粗）和待办（复选框）分开；一条里说明和待办混着的按分句拆开，不会有一条几十字的粗体复选框
A3  “调整这一天”层里的“去掉这一天”：墨色实心方形主按钮，没有确认层和取消键（点一下执行，5 秒内可撤销）
A4  /follow/ 主题页年表“看其余 N 条”展开状态记在本机（按主题、7 天过期）
A5  点时间线行本体：高亮这一行；没开地图只高亮、不弹地图、不弹“改这一站”（2026-10-18 地图 App 化：整屏地图盖住页面，不再有“页面行 ↔ 内嵌地图”的联动，改成：地图里选的站，关闭后页面滚到那一行——判据在 map_app_check M4）
A6  sans.css 每个字体块都是 font-display: swap，且是不挡渲染的（media=print onload）；serif.css 仍是 block
A7  慢网：脚本 + 样式各自要十几秒、地图建好后瓦片很快到 → 不能退示意图（以收到的瓦片数为准，不是从点开算总时间）
A8  跟谁走的线路每天的“影视和美食里的这一带”默认折叠；选了“带老人孩子”的人，别的线路也折
A9  首页搜索：输入时下面即时出现前 5 条（人物 / 目的地 / 线路），人物名排第一，点一下直接进，回车才跳 /where/
"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

ROOT_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INJ = {
    'road_old': ('assets/site.js', "if(/^(步行|徒步)/.test(tx))walk+=mn;else drive+=mn}", "if(/^(步行|徒步)/.test(tx))walk+=mn;else if(/^(打车|包车|自驾|开车|大巴)/.test(tx))drive+=mn}"),
    'label_old': ('assets/site.js', "(sv_&&own>0&&own>=drive-.5?'开车约 ':'路上约 ')", "'开车约 '"),
    'confirm_grey': ('assets/site.css', ".xd .rmgo{background:var(--ink);color:var(--bg);min-height:48px}", ".xd .rmgo{min-height:48px}"),
    'ftl_forget': ('assets/site.js', "if(o&&o.t&&Date.now()-o.t<7*864e5)d.open=true;", "if(0)d.open=true;"),
    'ftl_forever': ('assets/site.js', "Date.now()-o.t<7*864e5", "Date.now()-o.t<7000*864e5"),
    'row_nohl': ('assets/site.js', "if(li.classList.contains('dep'))return;li.classList.add('rsel');", "if(li.classList.contains('dep'))return;"),
    'sans_block': ('assets/fonts/sans.css', "font-display: swap", "font-display: block"),
    'hard_total': ('assets/routemap.js', ["      arm(); setProg(inst, .3);\n      getStyle(", "        arm(); setProg(inst, .5);\n        var map, cam"], ["      setProg(inst, .3);\n      getStyle(", "        setProg(inst, .5);\n        var map, cam"]),
    'sj_open': ('assets/site.js', "var w=(JSON.parse(localStorage.getItem('zouni_pick')||'{}')||{}).w;if(w!=='o')return;", "var w=(JSON.parse(localStorage.getItem('zouni_pick')||'{}')||{}).w;if(w!=='x')return;"),
    'sug_off': ('assets/site.js', "inp.addEventListener('input',show);", ""),
    'sug_order': ('assets/site.js', "th.slice(0,3).forEach(function(x){out.push(['/follow/'+x[0]+'/',x[1],'人物和事件 · '+x[3]+' 条线路'])});", ""),
}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT_, 'tests', 'fixtures')
STYLE = open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read(); PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read(); CORS = {'access-control-allow-origin': '*'}


def stub(c):
    """OpenFreeMap 的瓦片索引 / 瓦片 / 栅格（样式、sprite、西文字形已自托管，走本地站）"""
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), lambda r: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b''))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), lambda r: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG))


def want(k): return ONLY is None or k in ONLY


def zmin(t):
    h = re.search(r'(\d+)\s*小时', t or ''); m = re.search(r'(\d+)\s*分', t or '')
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)

    def shot(pg, name):
        if env.shots: pg.screenshot(path=os.path.join(env.shots, name))

    # ───────── A1 “累不累”同源
    if want('A1'):
        with guard('A1'):
            c = new_ctx(br, None); pg = new_page(env, c)
            for rid, drive in (('hzh1', False), ('hcz4', True), ('xl9a', True), ('sh5d', False)):
                goto(env, pg, '/trip/%s/' % rid, 500)
                pg.wait_for_function("document.querySelectorAll('.day > .dload').length===document.querySelectorAll('section.day').length", timeout=8000)
                d = pg.evaluate("""()=>{var sv=document.querySelector('article.trip').dataset.sv==='1';
                  return {sv:sv,gd:document.querySelector('.glance [data-gd]').innerText.replace(/\\s+/g,' '),
                  days:[].map.call(document.querySelectorAll('section.day'),function(s){var ld=s.querySelector(':scope > .dload'),fx=[].filter.call(s.querySelectorAll('.facts .fx:not([hidden]) small'),function(x){return x.textContent==='开车'||x.textContent==='路上'})[0],
                    deps=[].slice.call(s.querySelectorAll('.tl > .r.dep:not([hidden]) .s')).map(function(p){return p.textContent.replace(/^回住处\\s*·\\s*/,'').split('·')[0].trim()}).filter(function(t){return!/^(步行|徒步)/.test(t)&&/\\d/.test(t)});
                    return {txt:ld?ld.textContent:'',d:ld?+ld.dataset.d:-1,drv:+s.dataset.drv,fx:fx?fx.parentNode.querySelector('b').textContent:'',allown:deps.length>0&&deps.every(function(t){return /^(自驾|开车|包车)/.test(t)})}})}}""")
                days = d['days']; lab = '开车约' if d['sv'] else '路上约'
                check('A1a %s 每天的数 = 建站时算好的（data-drv）；2026-10-18 起“开车/路上”那一格去掉了（同一天只写一次）' % rid,
                      all(x['d'] == x['drv'] and x['fx'] == '' for x in days), [(x['d'], x['drv'], x['fx']) for x in days])
                check('A1b %s 每天那一行：不开车线写“路上约”；有自驾段的线路，当天全是自驾才写“开车约”，混着高铁 / 打车写“路上约”（sv=%s）' % (rid, d['sv']), d['sv'] == drive and all((x['d'] < 10) or (('开车约' in x['txt']) == (d['sv'] and x['allown'])) for x in days), [(x['txt'][:18], x['allown']) for x in days][:3])
                mx = max(x['d'] for x in days)
                m = re.search(r'(\d+(?:\.\d)?) 小时', d['gd'])
                check('A1c %s 页头“最长一天”(%s) = 每天里最大的那个(%d 分 = %.1f 小时)' % (rid, d['gd'], mx, mx / 60), (not m and mx < 45) or (bool(m) and abs(float(m.group(1)) - mx / 60) < .06), (d['gd'], mx))
            # 不开车的线：火车、打车也算进去
            goto(env, pg, '/trip/hzh1/', 500)
            g = pg.inner_text('.glance [data-gd]')
            check('A1d 郑和 hzh1（不开车）页头不是只有“不开车”：写出“路上最长 X 小时”（火车、打车算进去）（%s）' % g.replace('\n', ' '), '不开车' in g and re.search(r'路上最长 \d+(\.\d)? 小时', g) is not None, g)
            ids = pg.evaluate("[].map.call(document.querySelectorAll('section.day'),function(s){return +s.querySelector(':scope > .dload').dataset.d})")
            check('A1e hzh1 第 2 天（坐火车）路上 ≥2 小时，不是 0（%s）' % ids, len(ids) >= 2 and ids[1] >= 120, ids)
            # 对比表（cmp.js）同一个数
            cm = pg.evaluate("fetch('/assets/cmp.js').then(r=>r.text())")
            mm = re.search(r'"hzh1":\[(\d+),"[^"]*",(\d+),(\d+),', cm)
            check('A1f 对比表里 hzh1 最长一天路上 = 页头（%s vs %s）' % (mm and mm.group(3), max(ids)), bool(mm) and int(mm.group(3)) == max(ids), mm and mm.groups())

    # ───────── A2 出发前：说明和待办分开
    if want('A2'):
        with guard('A2'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 500)
            def probe():
                return pg.evaluate("""()=>{var o={todo:[],tip:[],boldTip:0,tipBox:0};[].forEach.call(document.querySelectorAll('section.pre:not(.go) li'),function(li){var x=li.querySelector('input[type=checkbox]'),sp=li.querySelector('span');if(!sp)return;
                  if(x)o.todo.push(sp.textContent.trim());else{o.tip.push(sp.textContent.trim());if(+getComputedStyle(sp).fontWeight>=600)o.boldTip++;if(li.querySelector('input'))o.tipBox++}});return o}""")
            def verdict(o):
                longbox = [t for t in o['todo'] if len(t) > 64]
                mixed = [t for t in o['todo'] if '；' in t or ('，' in t and re.search(r'要先坐|约两小时|转车', t))]
                return not longbox and not mixed and o['boldTip'] == 0 and o['tipBox'] == 0 and bool(o['todo']) and any('南京到浏河' in t for t in o['tip']), (longbox, mixed, o['boldTip'], o['tipBox'])
            o = probe(); ok, why = verdict(o)
            check('A2a 郑和线：待办只有真要办的事（%s）、“南京到浏河要先坐火车…”是说明（无复选框、不加粗）' % [t[:18] for t in o['todo']], ok, (why, o['tip'][:3]))
            if env.inject is None or True:
                # 反向：把说明塞回待办的那一条（模拟没拆分）→ 判据必须红
                pg.evaluate("""()=>{var li=[].filter.call(document.querySelectorAll('section.pre:not(.go) li'),function(l){return l.querySelector('input[type=checkbox]')})[0];var sp=li.querySelector('span');sp.textContent='南京到浏河要先坐火车到太仓再转车，第三天去上海临港约两小时；'+sp.textContent}""")
                ok2, _ = verdict(probe())
                check('A2b 反向：把说明塞回待办的那一条，判据会红', not ok2)

    # ───────── A3 去掉这一天：“调整这一天”层里的“去掉这一天”是墨色实心方形主按钮（2026-10-18：确认层和“算了”取消键都没了，点一下直接执行，5 秒内可撤销）
    if want('A3'):
        with guard('A3'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 500)
            pg.evaluate("document.querySelector('.dayadj').scrollIntoView({block:'center',behavior:'instant'})")
            pg.click('.dayadj'); pg.wait_for_selector('.xd .rmgo'); pg.wait_for_timeout(300)
            st = pg.evaluate("""()=>{var g=document.querySelector('.xd .rmgo'),cs=getComputedStyle(g),ink=getComputedStyle(document.documentElement).getPropertyValue('--ink').trim();
              var tmp=document.createElement('i');tmp.style.color=ink;document.body.appendChild(tmp);var inkRgb=getComputedStyle(tmp).color;tmp.remove();
              var r=g.getBoundingClientRect();return {bg:cs.backgroundColor,ink:inkRgb,fg:cs.color,h:r.height,rad:cs.borderRadius,cancel:document.querySelectorAll('.pk-cancel').length}}""")
            check('A3a “去掉这一天”是墨色实心（背景 %s = 墨色 %s）、方形、≥44 高' % (st['bg'], st['ink']), st['bg'] == st['ink'] and st['rad'] in ('0px', '0') and st['h'] >= 44, st)
            check('A3b 没有“算了”取消键（只有右上 ×）', st['cancel'] == 0, st)
            shot(pg, 'a3_dayadj.png')

    # ───────── A4 年表展开状态
    if want('A4'):
        with guard('A4'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/follow/sushi/', 400)
            if pg.locator('details.ftlm').count() == 0: goto(env, pg, '/follow/zhenghe/', 400)
            url = pg.url.replace(env.B, '')
            check('A4a 默认是收起的', pg.evaluate("!document.querySelector('details.ftlm').open"))
            pg.click('details.ftlm > summary'); pg.wait_for_timeout(200)
            tid = pg.evaluate("document.querySelector('article.ftp').dataset.id")
            check('A4b 展开后存在本机（zouni_follow… 键、按主题 id %s）' % tid, pg.evaluate("(k)=>!!localStorage.getItem(k)", 'zouni_ftl_' + tid))
            goto(env, pg, '/', 300); goto(env, pg, url, 400)
            check('A4c 返回再进来仍是展开的', pg.evaluate("document.querySelector('details.ftlm').open"))
            pg.evaluate("(k)=>localStorage.setItem(k,JSON.stringify({t:Date.now()-8*864e5}))", 'zouni_ftl_' + tid); goto(env, pg, url, 400)
            check('A4d 8 天前展开的：已过期，又是收起的，旧记录被清掉', pg.evaluate("!document.querySelector('details.ftlm').open") and pg.evaluate("(k)=>!localStorage.getItem(k)", 'zouni_ftl_' + tid))
            pg.click('details.ftlm > summary'); pg.wait_for_timeout(200)
            check('A4e 过期后重新点开：又记上（新时间戳）', pg.evaluate("(k)=>{var o=JSON.parse(localStorage.getItem(k)||'null');return !!o&&Date.now()-o.t<5000}", 'zouni_ftl_' + tid))

    # ───────── A5 点行：高亮 + 聚焦地图
    if want('A5'):
        with guard('A5'):
            c = new_ctx(br, None); stub(c); pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 600)
            HL = "(i)=>{var rs=[].filter.call(document.querySelectorAll('#d1 .tl > li.r.see'),function(r){return r.hasAttribute('data-ll')});return rs[i]}"
            n_rows = pg.evaluate("[].filter.call(document.querySelectorAll('#d1 .tl > li.r.see'),function(r){return r.hasAttribute('data-ll')}).length")
            # 地图没开：只高亮
            row = pg.evaluate_handle(HL, 1).as_element(); row.scroll_into_view_if_needed(); row.click(position={'x': 6, 'y': 6}); pg.wait_for_timeout(400)
            st = pg.evaluate("({hl:document.querySelectorAll('.tl > li.r.rsel').length,map:document.querySelectorAll('.rm').length,sheet:document.querySelectorAll('.pk-mask,.pk').length,adj:!!document.querySelector('.xd .rmgo,.npk')})")
            check('A5a 地图没开：点行本体 → 高亮这一行（%d 行）、不弹地图（%d）、不弹“改这一站”/层（%d）' % (st['hl'], st['map'], st['sheet']), st['hl'] == 1 and st['map'] == 0 and st['sheet'] == 0, st)
            # 打开本日地图（整屏）后按返回：页面回到原位置
            row.scroll_into_view_if_needed(); y0 = pg.evaluate("window.scrollY")
            pg.evaluate("document.querySelector('#d1 .rm-open').click()"); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=15000); pg.wait_for_timeout(500)
            pg.go_back(); pg.wait_for_timeout(700)
            check('A5b 开本日地图（整屏）再按返回：页面回到原来的位置（%d → %d）、点过的行高亮还在（%d）' % (y0, pg.evaluate("window.scrollY"), pg.evaluate("document.querySelectorAll('.tl > li.r.rsel').length")), abs(pg.evaluate("window.scrollY") - y0) <= 2 and pg.evaluate("document.querySelectorAll('.tl > li.r.rsel').length") == 1, y0)

    # ───────── A6 sans.css swap
    if want('A6'):
        with guard('A6'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 300)
            sans = pg.evaluate("fetch('/assets/fonts/sans.css').then(r=>r.text())"); serif = pg.evaluate("fetch('/assets/fonts/serif.css').then(r=>r.text())")
            nf = len(re.findall(r'@font-face', sans)); ns = len(re.findall(r'font-display:\s*swap', sans))
            check('A6a sans.css %d 个字体块全是 font-display: swap（swap %d 个）' % (nf, ns), nf > 100 and nf == ns, (nf, ns))
            check('A6b serif.css 仍是 block（每次切页标题不先显示系统字再跳）', len(re.findall(r'@font-face', serif)) == len(re.findall(r'font-display:\s*block', serif)) > 100)
            html = open(os.path.join(env.site, 'trip', 'hzh1', 'index.html'), encoding='utf-8').read()
            check('A6c 黑体样式表不挡渲染（media=print + onload 换 all）', re.search(r'<link rel="stylesheet" href="/assets/fonts/sans\.css" media="print" onload="this\.media=\'all\'">', html) is not None)

    # ───────── A7 慢网：以收到的瓦片数为准
    if want('A7'):
        with guard('A7'):
            # 地图脚本 14 秒才到；瓦片被扣住直到第 24 秒才放（>20 秒：如果超时是“从点开算一个总时间”，早就退示意图了）；每一步各自有窗口、瓦片还在路上就继续等
            env.delays['assets/maplibre/maplibre-gl.js'] = 14
            c = new_ctx(br, None); held = []; go = {'on': False}
            def tile(r):
                if go['on']: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
                else: held.append(r)
            c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
            c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), tile)
            c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), lambda r: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG))
            pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 500)
            pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); t0 = time.time()
            while time.time() - t0 < 24: pg.wait_for_timeout(500)
            mid = pg.evaluate("(function(){var c=window.ZRM&&ZRM.cur();return c?{failed:!!c.failed,why:c.why||'',tiles:c.tiles||0}:null})()")
            go['on'] = True
            for r in held:
                try: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
                except Exception: pass
            ok = True
            try: pg.wait_for_function("window.ZRM&&ZRM.cur()&&(ZRM.cur().failed||ZRM.cur().tiles>0)", timeout=15000)
            except Exception: ok = False
            dt = time.time() - t0
            r = pg.evaluate("(function(){var c=window.ZRM&&ZRM.cur();return c?{failed:!!c.failed,why:c.why||'',tiles:c.tiles||0}:null})()")
            check('A7 脚本 14 秒才到、瓦片 24 秒才到（%.0f 秒时）：24 秒时还没退示意图（%s），瓦片到了以后正常显示（%s）' % (dt, mid, r), ok and bool(mid) and not mid['failed'] and bool(r) and not r['failed'] and r['tiles'] > 0, (mid, r))
            env.delays.clear()

    # ───────── A8 影视美食挂钩行折叠
    if want('A8'):
        with guard('A8'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/hzh1/', 500)
            r = pg.evaluate("({det:document.querySelectorAll('.day > details.sjd').length,open:document.querySelectorAll('.day > details.sjd[open]').length,vis:[].filter.call(document.querySelectorAll('.day p.sjn'),function(p){return p.getBoundingClientRect().height>0&&!p.closest('details:not([open])')}).length,tot:document.querySelectorAll('.day p.sjn').length})")
            check('A8a 跟谁走的线路（hzh1）：影视美食行在折叠里（折叠 %d 个、展开 %d、看得见的 %d、共 %d）' % (r['det'], r['open'], r['vis'], r['tot']), r['tot'] > 0 and r['det'] > 0 and r['open'] == 0 and r['vis'] == 0, r)
            pg.click('.day > details.sjd > summary'); pg.wait_for_timeout(150)
            check('A8b 点“影视和美食里的这一带”能展开看到', pg.evaluate("[].some.call(document.querySelectorAll('.day p.sjn'),function(p){return p.getBoundingClientRect().height>0&&!p.closest('details:not([open])')})"))
            plain = None
            for f in sorted(os.listdir(os.path.join(env.site, 'trip'))):
                h = open(os.path.join(env.site, 'trip', f, 'index.html'), encoding='utf-8').read()
                if 'class="sjn"' in h and 'class="fbn"' not in h and 'class="sjd"' not in h: plain = f; break
            check('A8c 找得到一条不是跟谁走、带影视美食行的普通线路（%s）' % plain, bool(plain))
            if plain:
                goto(env, pg, '/trip/%s/' % plain, 400)
                n0 = pg.evaluate("[].filter.call(document.querySelectorAll('.day p.sjn'),function(p){return p.getBoundingClientRect().height>0&&!p.closest('details:not([open])')}).length")
                c2 = new_ctx(br, None, storage={'zouni_pick': json.dumps({'w': 'o'})}); pg2 = new_page(env, c2); goto(env, pg2, '/trip/%s/' % plain, 500)
                r2 = pg2.evaluate("({det:document.querySelectorAll('.day > details.sjd').length,open:document.querySelectorAll('.day > details.sjd[open]').length,vis:[].filter.call(document.querySelectorAll('.day p.sjn'),function(p){return p.getBoundingClientRect().height>0&&!p.closest('details:not([open])')}).length})")
                check('A8d 普通线路默认能看到影视美食行（%d 行）；选了“带老人孩子”的人这条线也折叠（折叠 %d、看得见 %d）' % (n0, r2['det'], r2['vis']), n0 > 0 and r2['det'] > 0 and r2['vis'] == 0 and r2['open'] == 0, (n0, r2))

    # ───────── A9 首页搜索即时建议
    if want('A9'):
        with guard('A9'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/', 500)
            for q, want_txt in (('苏轼', '苏轼'), ('长征', '长征'), ('乾隆', '乾隆')):
                pg.fill('form.hsearch input', ''); pg.fill('form.hsearch input', q)
                try: pg.wait_for_function("document.querySelectorAll('.hsug li').length>0&&!document.querySelector('.hsug').hidden", timeout=8000)
                except Exception: pass
                r = pg.evaluate("[].map.call(document.querySelectorAll('.hsug li a'),function(a){return {h:a.getAttribute('href'),t:a.textContent,ht:a.getBoundingClientRect().height}})")
                check('A9a 输入“%s”：下面即时出现 1–5 条建议，第一条是主题页（%s）' % (q, r[:1]), 1 <= len(r) <= 5 and r[0]['h'].startswith('/follow/') and want_txt in r[0]['t'], r)
                check('A9b 每条建议 ≥44 高', bool(r) and all(x['ht'] >= 44 for x in r), [x['ht'] for x in r])
            pg.fill('form.hsearch input', '苏轼'); pg.wait_for_function("document.querySelectorAll('.hsug li').length>0", timeout=8000)
            shot(pg, 'a9_suggest.png')
            pg.click('.hsug li a >> nth=0'); pg.wait_for_load_state('networkidle')
            check('A9c 点一条建议直接进主题页（%s）' % pg.url, '/follow/' in pg.url and '/where/' not in pg.url, pg.url)
            goto(env, pg, '/', 400); pg.fill('form.hsearch input', '苏轼'); pg.press('form.hsearch input', 'Enter'); pg.wait_for_load_state('networkidle')
            check('A9d 回车才跳 /where/（%s）' % pg.url, '/where/' in pg.url and 'q=' in pg.url, pg.url)

    br.close()
env.finish('a_batch3_check')
