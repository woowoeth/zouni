#!/usr/bin/env python3
"""/follow/ 专栏页、线路页注释、日期选择与术语（2026-10-18，用户反馈 P2）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/follow2_check.py build/site [--shots DIR]
    python3 tests/follow2_check.py build/site --inject 名字     # 反向自检（只改送到浏览器的 site.js / site.css），必须变红

P1  /follow/ 顶部在搜索框下有类别快捷入口（方块 chip 横排，每类一个，≥44 高）：点一下滚到那一类并选中；选中项始终露在横条里；有的类搜索后被收起时 chip 也收起
P2  “常看”一行：取规则表（build_site.FOLLOW_HOT）前 6 个，每个链到存在的主题页，包含苏轼
P3  主题页：年表默认展开前 6 条、“看其余 N 条”是 44px 方形按钮（有边框）；年表日期不折行（页面字体下全站每条日期都放得进日期列）
P4  线路页每站注释字号 ≥14px、颜色对比 ≥4.5（亮 / 暗）
P5  日期选择里有“下个周末”按钮，日期是下一周的周六
P6  术语：“懂一点”→“背景”，“调整”弹层标题“改这一站”，“片区”→“大概位置”，“途经点”→“中途点”（页面、弹层、地图里都没有旧词）
"""
import datetime, json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'chip_hide': ('assets/site.css', ".fpg .fchips{display:flex;", ".fpg .fchips{display:none;"),
    'hot_hide': ('assets/site.css', ".fpg .fhot{display:flex;", ".fpg .fhot{display:none;"),
    'chip_noscroll': ('assets/site.js', "if(on)showChip(c)", "if(0)showChip(c)"),
    'ftl_narrow': ('assets/site.css', ".fpg .ftl time{flex:none;width:124px;white-space:nowrap;", ".fpg .ftl time{flex:none;width:76px;white-space:normal;"),
    'ftlm_small': ('assets/site.css', "justify-content:center;min-height:44px;margin:12px 20px 0;border:1px solid var(--line2);background:var(--bg);font:700 14px var(--sans);color:var(--ink);cursor:pointer;list-style:none}", "min-height:20px;margin:0 20px;border:0;font:700 14px var(--sans);color:var(--ink);cursor:pointer;list-style:none}"),
    'fnote_small': ('assets/site.css', ".r .rb p.fnote{margin:2px 0 0;font-size:14px;line-height:1.6;color:var(--ink2)}", ".r .rb p.fnote{margin:2px 0 0;font-size:12px;line-height:1.6;color:var(--mute)}"),
    'pick_old': ('assets/site.js', "['下个周末',sat(1)]", "['下周六',sat(1)]"),
    'adj_title_old': ('assets/site.js', "head('改这一站')", "head(nm(r))"),
    'term_old': ('assets/routemap.js', "<p class=\"rm-c1\">大概位置，不是酒店</p>", "<p class=\"rm-c1\">片区位置，不是酒店</p>"),
}
env = Env(INJ)
check, guard = env.check, env.guard
ROOT_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = {}
for f in sorted(os.listdir(os.path.join(ROOT_, 'data', 'history'))):
    if f.endswith('.json') and not f.startswith('_'):
        h = json.load(open(os.path.join(ROOT_, 'data', 'history', f), encoding='utf-8')); H[h['id']] = h
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT_, 'tests', 'fixtures')
STYLE = open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read(); PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read(); CORS = {'access-control-allow-origin': '*'}
LUM = """(c)=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return [0.2126*f(m[0])+0.7152*f(m[1])+0.0722*f(m[2]), m.length>3?m[3]:1]}"""
CONTRAST = """([sel])=>{const el=document.querySelector(sel);if(!el)return null;const L=%s;const fg=getComputedStyle(el).color;let n=el,bg=null;
  while(n){const c=getComputedStyle(n).backgroundColor;const [l,a]=L(c);if(a>0.5){bg=c;break}n=n.parentElement}
  if(!bg)bg=getComputedStyle(document.body).backgroundColor;const a=L(fg)[0],b=L(bg)[0];return {c:+((Math.max(a,b)+0.05)/(Math.min(a,b)+0.05)).toFixed(2),fs:parseFloat(getComputedStyle(el).fontSize)}}""" % LUM
HOT_TABLE = re.search(r"FOLLOW_HOT = (\[.*?\])", open(os.path.join(ROOT_, 'tools', 'build_site.py'), encoding='utf-8').read()).group(1)
HOT_IDS = [t for t in eval(HOT_TABLE) if t in H][:6]
SU = H.get('sushi') or next(iter(H.values()))


def stub(c):
    c.route('https://tiles.openfreemap.org/styles/liberty', lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=STYLE))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), lambda r: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b''))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites)/.+'), lambda r: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG) if not r.request.url.split('?')[0].endswith('.json') else r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}'))


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)

    def shot(pg, name):
        if env.shots: pg.screenshot(path=os.path.join(env.shots, name))

    with guard('P1'):
        c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/follow/')
        chips = pg.evaluate("[...document.querySelectorAll('.fchip')].map(b=>({t:b.textContent,c:b.dataset.c,h:b.getBoundingClientRect().height,vis:b.getBoundingClientRect().width>0}))")
        grps = pg.evaluate("[...document.querySelectorAll('.fgrp')].map(g=>g.id)")
        bar = pg.evaluate("(function(){var b=document.querySelector('.fchips');if(!b)return null;var r=b.getBoundingClientRect(),s=document.querySelector('.fsearch').getBoundingClientRect();return {top:r.top,stop:s.bottom,vis:r.width>0&&getComputedStyle(b).display!=='none',sw:b.scrollWidth,cw:b.clientWidth}})()")
        check('P1a 搜索框下面有类别快捷入口（%s）' % [x['t'] for x in chips], bool(bar) and bar['vis'] and len(chips) == len(grps) and len(chips) >= 4 and bar['top'] >= bar['stop'] - 1 and bar['top'] - bar['stop'] < 40, (bar, len(chips), len(grps)))
        check('P1b 每个 chip 方块、≥44 高、能横滑（条宽 %s > 视口 %s）' % (bar and bar['sw'], bar and bar['cw']), all(x['h'] >= 44 for x in chips) and bool(bar) and bar['sw'] > bar['cw'], [x['h'] for x in chips])
        shot(pg, 'p1_chips_top.png')
        ok_all, info = True, []
        for i in (2, 4, len(chips) - 1):
            if i >= len(chips): continue
            pg.evaluate("document.querySelector('.fchips').scrollLeft=0"); pg.evaluate("(i)=>document.querySelectorAll('.fchip')[i].click()", i); pg.wait_for_timeout(250)      # 用 .click()：Playwright 的 click 会自己把按钮横滚进视野，盖住“选中项露出来”的判据
            r = pg.evaluate("(function(i){var g=document.querySelectorAll('.fgrp')[i],c=document.querySelectorAll('.fchip')[i],b=document.querySelector('.fchips'),gr=g.getBoundingClientRect(),cr=c.getBoundingClientRect(),br=b.getBoundingClientRect();return {top:Math.round(gr.top),on:c.classList.contains('on'),inbar:cr.left>=br.left-1&&cr.right<=br.right+1}})(%d)" % i)
            info.append((chips[i]['t'], r)); ok_all = ok_all and -2 <= r['top'] <= 40 and r['on'] and r['inbar']
        check('P1c 点 chip：滚到那一类（离页顶 ≤40px）、该 chip 选中、且整个露在横条里（%s）' % info, ok_all, info)
        pg.evaluate("window.scrollTo({top:0,behavior:'instant'});document.querySelector('.fchips').scrollLeft=0"); pg.wait_for_timeout(200)
        pg.evaluate("(function(){var g=document.querySelectorAll('.fgrp');window.scrollTo({top:g[g.length-1].getBoundingClientRect().top+scrollY,behavior:'instant'})})()"); pg.wait_for_timeout(100); pg.evaluate("window.scrollBy({top:3,behavior:'instant'})"); pg.wait_for_timeout(500)
        r = pg.evaluate("(function(){var c=document.querySelectorAll('.fchip'),on=[...c].filter(x=>x.classList.contains('on')),b=document.querySelector('.fchips').getBoundingClientRect();var o=on[0];if(!o)return null;var r=o.getBoundingClientRect();return {last:o===c[c.length-1],inbar:r.left>=b.left-1&&r.right<=b.right+1,t:o.textContent}})()")
        check('P1d 滚动页面到最后一类：选中项跟着换到最后一个 chip，并始终露在横条里（%s）' % r, bool(r) and r['last'] and r['inbar'], r)
        pg.evaluate("window.scrollTo(0,0)"); pg.fill('.fsearch input', '苏轼'); pg.wait_for_timeout(300)
        vis = pg.evaluate("[...document.querySelectorAll('.fchip')].filter(c=>!c.hidden&&c.getBoundingClientRect().width>0).length")
        check('P1e 搜索后只剩有结果的类别 chip（%d 个）' % vis, 1 <= vis < len(chips), vis)
        c.close()
    with guard('P2'):
        c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/follow/')
        hot = pg.evaluate("[...document.querySelectorAll('.fhot a')].map(a=>[a.textContent,a.getAttribute('href'),a.getBoundingClientRect().height])")
        want = ['/follow/%s/' % t for t in HOT_IDS]
        check('P2a “常看”一行 = 规则表前 6 个（%s）' % [x[0] for x in hot], [x[1] for x in hot] == want and len(hot) == 6 and '苏轼' in [x[0] for x in hot], (hot, want))
        check('P2b 每个都够点（≥44 高）、有“常看”小标签', all(x[2] >= 44 for x in hot) and pg.inner_text('.fhot').startswith('常看'), hot)
        shot(pg, 'p2_hot.png')
        c.close()
    with guard('P3'):
        c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/follow/sushi/')
        vis6 = pg.evaluate("[...document.querySelectorAll('.ftl')][0].children.length")
        sm = pg.evaluate(HIT, pg.query_selector('.ftlm summary'))
        sty = pg.evaluate("(function(){var s=document.querySelector('.ftlm summary'),c=getComputedStyle(s);return {bw:c.borderTopWidth,h:Math.round(s.getBoundingClientRect().height),txt:s.textContent}})()")
        check('P3a 年表默认展开前 6 条（%d 条），“看其余 N 条”按钮（%s）' % (vis6, sty['txt']), vis6 == 6 and re.match(r'看其余 \d+ 条', sty['txt']), (vis6, sty))
        check('P3b 按钮是 44px 方形按钮：高 %s、有边框 %s、点击区 %sx%s' % (sty['h'], sty['bw'], sm and sm['w'], sm and sm['h']), sty['h'] >= 44 and sty['bw'] != '0px' and bool(sm) and sm['w'] >= 44 and sm['h'] >= 44, (sty, sm))
        pg.click('.ftlm summary'); pg.wait_for_timeout(200)
        LINES = "[...document.querySelectorAll('.ftl time')].filter(t=>{const r=document.createRange();r.selectNodeContents(t);const rs=[...r.getClientRects()];return new Set(rs.map(x=>Math.round(x.top))).size>1}).map(t=>t.textContent)"
        wraps = pg.evaluate(LINES)
        check('P3c 苏轼年表：日期一行放得下，不折行', not wraps, wraps)
        # 全站每条日期：在页面字体下放得进日期列
        pg.goto(env.B + '/follow/cz1/', wait_until='networkidle'); pg.wait_for_timeout(400)
        whens = []
        for h in H.values():
            for x in h.get('timeline') or []:
                w = (x.get('when') or '').strip(); m = re.match(r'^(.*?)\s*[（(]([^）)]*)[）)]\s*$', w)
                if m and len(w) > 13: w = m.group(1)
                whens.append(w)
        r = pg.evaluate("""(ws)=>{const t=document.querySelector('.ftl time');const cs=getComputedStyle(t),W=t.getBoundingClientRect().width;const s=document.createElement('span');s.style.cssText='position:absolute;visibility:hidden;white-space:nowrap;font:'+cs.font;document.body.appendChild(s);
          const bad=[];ws.forEach(w=>{s.textContent=w;if(s.getBoundingClientRect().width>W+0.5)bad.push([w,Math.round(s.getBoundingClientRect().width)])});return {W:Math.round(W),n:ws.length,bad:bad.slice(0,6),nb:bad.length,ws:cs.whiteSpace}}""", whens)
        check('P3d 全站 %d 条年表日期（括号说明已挪到正文）：每条一行放得进 %dpx 日期列（放不下的 %d 条 %s）' % (r['n'], r['W'], r['nb'], r['bad'][:3]), r['nb'] == 0 and r['ws'] == 'nowrap', r)
        pg.click('.ftlm summary') if pg.query_selector('.ftlm:not([open]) summary') else None
        wraps = pg.evaluate(LINES)
        check('P3e 长征年表（日期最长的主题之一）实测不折行', not wraps, wraps)
        shot(pg, 'p3_topic.png')
        c.close()
    with guard('P4'):
        for dark in (False, True):
            c = new_ctx(br, None, dark=dark); pg = new_page(env, c); goto(env, pg, '/trip/hjgs1/')
            r = pg.evaluate(CONTRAST, ['.r .rb p.fnote'])
            check('P4 %s：线路页站点注释字号 %spx（≥14）、对比 %s（≥4.5）' % ('暗色' if dark else '亮色', r and r['fs'], r and r['c']), bool(r) and r['fs'] >= 14 and r['c'] >= 4.5, r)
            c.close()
    with guard('P5'):
        c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/trip/xa3/')
        pg.click('.dtw'); pg.wait_for_selector('.pk-q')
        q = pg.evaluate("[...document.querySelectorAll('.pk-q button')].map(b=>[b.childNodes[0].textContent,b.querySelector('small').textContent,b.disabled])")
        t = datetime.date.today(); sat0 = t + datetime.timedelta(days=(5 - t.weekday()) % 7); nxt = sat0 + datetime.timedelta(days=7)
        want = '%d/%d' % (nxt.month, nxt.day)
        got = [x for x in q if x[0] == '下个周末']
        check('P5a 日期面板有“下个周末”按钮，日期是下一周的周六 %s（%s）' % (want, q), len(got) == 1 and got[0][1] == want and not got[0][2], q)
        pg.click('.pk-q button:has-text("下个周末")'); pg.wait_for_timeout(400)
        d0 = pg.evaluate("document.querySelector('.dpk').value")
        check('P5b 点“下个周末”：出发日期变成 %s（%s）' % (nxt.isoformat(), d0), d0 == nxt.isoformat(), d0)
        c.close()
    with guard('P6'):
        c = new_ctx(br, None); stub(c); pg = new_page(env, c); goto(env, pg, '/trip/xa3/')
        lbls = pg.evaluate("[...document.querySelectorAll('.lbl')].map(e=>e.textContent.trim())")
        html_ = pg.content()
        check('P6a 每天的小标题是“背景”，没有“懂一点”（%s）' % sorted(set(lbls)), '背景' in lbls and '懂一点' not in lbls and '懂一点' not in re.sub(r'<script.*?</script>', '', html_, flags=re.S), sorted(set(lbls)))
        pg.evaluate("document.querySelector('#d1 .r .s .adj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .r .s .adj'); pg.wait_for_timeout(400)
        ti = pg.evaluate("(function(){var h=document.querySelector('.pk .pk-h b'),n=document.querySelector('.pk .xnote .adjn');return {t:h?h.textContent:null,n:n?n.textContent:null}})()")
        check('P6b “调整”弹层标题是“改这一站”，站名在下面一行（%s）' % ti, ti['t'] == '改这一站' and bool(ti['n']), ti)
        pg.evaluate("document.querySelector('.pk .pk-x').click()"); pg.wait_for_timeout(200)
        pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=15000); pg.wait_for_timeout(600)
        pg.wait_for_timeout(600)      # 2026-10-18 地图 App 化：点开就是整屏，面板默认半屏，列表在 .rm-body 里
        hm_ = pg.evaluate("(function(){var z=ZRM.cur();for(var i=0;i<z.marks.length;i++){var m=z.marks[i];if(m.kind==='hm')return [m.px,m.py]}return null})()")      # 2026-10-18：地图下面没有列表了；点图上“住”的方块出“住”的卡片（挤在一起时弹“这里有几处”，选“住”）
        pg.mouse.click(hm_[0], hm_[1]); pg.wait_for_timeout(900)
        if pg.evaluate("!!document.querySelector('.rm-pk:not([hidden]) .rm-pi')"): pg.evaluate("[].slice.call(document.querySelectorAll('.rm-pi')).filter(function(b){return /^住/.test(b.textContent)})[0].click()"); pg.wait_for_timeout(900)
        tx = pg.inner_text('.rm-body')
        check('P6c 地图里“住”的卡片写“大概位置，不是酒店”，没有“片区”（%s）' % tx.replace('\n', ' ')[-30:], '大概位置，不是酒店' in tx and '片区' not in tx, tx[-60:])
        # 导航分段层（高德一次 1 个中途点）：说明里没有“途经点”
        pg.evaluate("document.querySelector('.rm-cb')&&document.querySelector('.rm-cb').click()"); pg.wait_for_timeout(300)      # 卡片 → 回当天（卡片状态下没有天标签）
        pg.click('.rm-tb[data-i="0"]'); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('.rm-navd').click()"); pg.wait_for_timeout(400)
        sheet = pg.evaluate("(document.querySelector('.rm-sheet')||{}).innerText||''")
        allt = pg.evaluate("document.body.innerText")
        check('P6d 页面、地图、导航层里没有“途经点”“片区位置”“懂一点”旧词；导航层说明里用“中途点”', not re.search(r'途经点|片区位置|懂一点', allt + sheet) and '中途点' in sheet, (re.findall(r'途经点|片区位置|懂一点', allt + sheet), sheet[:80]))
        c.close()
    br.close()
env.finish('专栏页与术语')
