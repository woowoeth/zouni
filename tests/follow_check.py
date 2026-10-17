#!/usr/bin/env python3
"""「跟谁走」专栏的带断言测试（2026-10-17，playwright chromium，390 宽）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站，并跑过 tools/ingest_history.py）：
    python3 tests/follow_check.py build/site [--shots DIR]
    python3 tests/follow_check.py build/site --inject chan_flat|banner_off|banner_small|fnote_hide|search_dead|mc_off|overflow    # 反向自检：只改送到浏览器的 site.js/site.css，必须变红

场景
  F1 首页进 /follow/ 一次点击（≤2 次）；首页频道是 2×2（走哪儿 / 跟片走 / 跟谁走 / 长线自驾），四格触控 ≥44
  F2 /follow/ 搜“苏轼”“长征”“乾隆”各命中对应主题卡、其余卡收起；清空恢复；/where/?q=苏轼 的“跟谁走”分组排在“线路”前面
  F3 点进主题页（苏轼）：名字、intro、年表（when·where·what）、线路卡片数 = 数据里的线路数；页面文字里没有任何 src 原文；有“只写有记载的事”那句
  F4 点线路 → 线路页：顶部横幅“这条线路跟着 苏轼 走”、横幅可点回主题页、有站点小字“苏轼：…”（可见）、没有 src；conf=medium 的小字里有“相传”
  F5 触控：搜索框、主题卡、线路卡、横幅、年表“看其余”≥44（elementFromPoint 实测）
  F6 博物馆周一：默认出发日这条线的博物馆行没有红字；把出发日改成周一，博物馆行出现红字“这天是周一…”（按线路出发日期算星期）
  F7 暗色：首页、/follow/、主题页、线路页无横向溢出，标题和卡片文字对比度 ≥4.5，背景是暗的
  F8 各页控制台没有报错
"""
import json, os, re, sys, datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'chan_flat': ('assets/site.css', ".chan2{display:flex;flex-wrap:wrap;", ".chan2{display:flex;flex-wrap:nowrap;"),
    'banner_off': ('assets/site.css', ".fbn{display:flex;", ".fbn{display:none;"),
    'banner_small': ('assets/site.css', ".fbn{display:flex;align-items:center;justify-content:space-between;min-height:44px;", ".fbn{display:flex;align-items:center;justify-content:space-between;min-height:24px;max-height:24px;overflow:hidden;"),
    'fnote_hide': ('assets/site.css', ".r .rb p.fnote{margin:2px 0 0;", ".r .rb p.fnote{display:none;margin:2px 0 0;"),
    'search_dead': ('assets/site.js', "inp.addEventListener('input',run);\n  var m=location.hash", "\n  var m=location.hash"),
    'mc_off': ('assets/site.js', "||r.dataset.mc==='1'}),sure=", "}),sure="),
    'overflow': ('assets/site.css', ".fpg .fintro{margin:0 20px 8px;", ".fpg .fintro{white-space:nowrap;margin:0 20px 8px;"),
}
env = Env(INJ)
check, guard = env.check, env.guard
ROOT_ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = {}
for f in sorted(os.listdir(os.path.join(ROOT_, 'data', 'history'))):
    if f.endswith('.json') and not f.startswith('_'):
        h = json.load(open(os.path.join(ROOT_, 'data', 'history', f), encoding='utf-8')); H[h['id']] = h
if not H: sys.exit('data/history 里没有主题：先 python3 tools/ingest_history.py')
SRCS = {s for h in H.values() for s in [v.get('src') for v in (h.get('notes') or {}).values()] + [x.get('src') for x in h.get('timeline') or []] if s and len(s) >= 4}
CT = ''.join([h.get('tagline') or '' for h in H.values()] + [h.get('intro') or '' for h in H.values()] + [(x.get('what') or '') + (x.get('where') or '') for h in H.values() for x in h.get('timeline') or []] + [v.get('line') or '' for h in H.values() for v in (h.get('notes') or {}).values()])
SRCS = {s for s in SRCS if s not in CT}      # 原文碰巧就是正文里的词（课文名、书名）的不算泄露
SU = H.get('sushi') or next(iter(H.values()))
LUM = """(c)=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return [0.2126*f(m[0])+0.7152*f(m[1])+0.0722*f(m[2]), m.length>3?m[3]:1]}"""
CONTRAST = """([sel])=>{const el=document.querySelector(sel);if(!el)return null;const L=%s;const fg=getComputedStyle(el).color;let n=el,bg=null;
  while(n){const c=getComputedStyle(n).backgroundColor;const [l,a]=L(c);if(a>0.5){bg=c;break}n=n.parentElement}
  if(!bg)bg=getComputedStyle(document.body).backgroundColor;const a=L(fg)[0],b=L(bg)[0];return {c:+((Math.max(a,b)+0.05)/(Math.min(a,b)+0.05)).toFixed(2),bgl:+L(bg)[0].toFixed(3)}}""" % LUM
NOSCROLL = "Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-390"      # 手机仿真下页面溢出时 innerWidth 会跟着变大，所以和固定的 390 比
name_of = lambda h: re.sub(r'[（(].*?[）)]', '', h.get('name') or h['id']).strip()


def next_monday():
    d = datetime.date.today() + datetime.timedelta(days=14)
    while d.weekday() != 0: d += datetime.timedelta(days=1)
    return d.isoformat()


with sync_playwright() as p:
    br = p.chromium.launch()

    def shot(pg, name):
        if env.shots: pg.screenshot(path=os.path.join(env.shots, name))

    # ———— F1 首页 → /follow/，2×2 ————
    with guard('F1'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/')
        hrefs = pg.evaluate("[...document.querySelectorAll('.chan2 a')].map(a=>a.getAttribute('href'))")
        check('F1 首页频道 = 走哪儿 / 跟片走 / 跟谁走 / 长线自驾', hrefs == ['/where/', '/pian/', '/follow/', '/long/'], hrefs)
        r = pg.evaluate("[...document.querySelectorAll('.chan2 a')].map(a=>{const b=a.getBoundingClientRect();return {l:b.left,t:b.top+scrollY,w:b.width,h:b.height,b:b.bottom+scrollY}})")
        check('F1 频道是 2×2（1、2 同行，3、4 在下一行，两列各自左对齐）', len(r) == 4 and abs(r[0]['t'] - r[1]['t']) < 1 and abs(r[2]['t'] - r[3]['t']) < 1 and r[2]['t'] >= r[0]['b'] - 1 and abs(r[0]['l'] - r[2]['l']) < 1 and abs(r[1]['l'] - r[3]['l']) < 1, r)
        check('F1 四格都落在首屏（390×844）', len(r) == 4 and all(x['b'] <= 844 for x in r), [x['b'] for x in r])
        for i in (1, 2, 3, 4):
            h_ = pg.evaluate(HIT, pg.locator(f'.chan2 a:nth-child({i})').element_handle())
            check(f'F1 频道第 {i} 格实际点击区 ≥44×44', h_ and h_['w'] >= 44 and h_['h'] >= 44, h_)
        shot(pg, 'F1_home_2x2.png')
        pg.click('.chan2 a[href="/follow/"]'); pg.wait_for_url('**/follow/'); pg.wait_for_timeout(500)
        check('F1 首页点一下（≤2 次）进到 /follow/', pg.url.rstrip('/').endswith('/follow'), pg.url)
        check('F1 /follow/ 标题是“跟谁走”', pg.inner_text('h1').strip() == '跟谁走', pg.inner_text('h1'))
        cats = pg.evaluate("[...document.querySelectorAll('.fgrp h2')].map(h=>h.childNodes[0].textContent.trim())")
        check('F1 /follow/ 按类别分组（至少 2 组，名字在归类表里）', len(cats) >= 2 and all(c_ in ('帝王', '文人与思想家', '行者与使者', '历史事件与工程', '红色线路') for c_ in cats), cats)
        n_cards = pg.locator('.fcd').count()
        check('F1 /follow/ 卡片数 = data/history 里有线路的主题数', n_cards == len([h for h in H.values() if h.get('routes')]), (n_cards, len(H)))
        card = pg.inner_text('.fcd >> nth=0')
        check('F1 每张卡有名字、一句话、“N 条线路 · a–b 天”', re.search(r'\d+ 条线路 · \d+(–\d+)? 天', card) is not None, card)
        shot(pg, 'F1_follow_index.png')
        c.close()

    # ———— F2 搜索 ————
    with guard('F2'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/follow/')
        total = pg.locator('.fcd').count()
        for q_, tid in (('苏轼', 'sushi'), ('长征', 'cz1'), ('乾隆', 'qianlong')):
            if tid not in H: check(f'F2 搜“{q_}”：data/history 里没有 {tid}', False); continue
            pg.fill('.fsearch input', q_); pg.wait_for_timeout(200)
            vis = pg.evaluate("[...document.querySelectorAll('.fcd')].filter(c=>!c.hidden).map(c=>c.querySelector('a').getAttribute('href'))")
            check(f'F2 搜“{q_}”命中 /follow/{tid}/', f'/follow/{tid}/' in vis, vis)
            check(f'F2 搜“{q_}”后别的卡收起（{len(vis)} < {total}）', 0 < len(vis) < total, vis)
        pg.fill('.fsearch input', '苏轼'); pg.wait_for_timeout(100); shot(pg, 'F2_follow_search.png')
        pg.fill('.fsearch input', '不存在的人xyz'); pg.wait_for_timeout(200)
        check('F2 搜不到时有一句话和去走哪儿的链接', pg.evaluate("!document.querySelector('.fempty').hidden") and pg.locator('.fempty a[href="/where/"]').count() == 1)
        pg.fill('.fsearch input', ''); pg.wait_for_timeout(200)
        check('F2 清空后卡片全回来', pg.evaluate("[...document.querySelectorAll('.fcd')].filter(c=>!c.hidden).length") == total)
        # /where/ 的站内搜索：主题排在线路前面
        goto(env, pg, '/where/?q=' + '苏轼', 1500)
        pg.wait_for_function("!document.querySelector('.wtf').hidden", timeout=8000)
        order = pg.evaluate("(()=>{const a=document.querySelector('.wtf'),b=document.querySelector('.wtr');return {af:a.getBoundingClientRect().top,bf:b.hidden?null:b.getBoundingClientRect().top,link:[...a.querySelectorAll('a')].map(x=>x.getAttribute('href')),dom:!!(a.compareDocumentPosition(b)&4)}})()")
        check('F2 /where/?q=苏轼：“跟谁走”分组出现，链到 /follow/sushi/', '/follow/sushi/' in order['link'], order)
        check('F2 /where/?q=苏轼：“跟谁走”排在“线路”前面（DOM 顺序和屏幕位置都是）', order['dom'] and (order['bf'] is None or order['af'] < order['bf']), order)
        c.close()

    # ———— F3 主题页 ————
    with guard('F3'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/follow/')
        pg.click(f'.fcd a[href="/follow/{SU["id"]}/"]'); pg.wait_for_url(f'**/follow/{SU["id"]}/'); pg.wait_for_timeout(500)
        check('F3 主题页 h1 = 名字', pg.inner_text('h1').strip() == name_of(SU), pg.inner_text('h1'))
        check('F3 主题页有一句话和 intro', SU['tagline'] in pg.inner_text('.deck') and SU['intro'][:20] in pg.inner_text('.fintro'))
        tl = pg.evaluate("[...document.querySelectorAll('.ftl li')].map(l=>[l.querySelector('time').textContent,l.querySelector('b').textContent,l.querySelector('span').textContent])")
        check('F3 年表条数 = 数据里的年表条数（含折起来的）', len(tl) == len(SU['timeline']) and all(a and b and c_ for a, b, c_ in tl), (len(tl), len(SU['timeline'])))
        check('F3 年表第一条的 when / where / what 就是数据里的', tl and tl[0][0] == SU['timeline'][0]['when'] and tl[0][2] == SU['timeline'][0]['what'], tl[:1])
        cards = pg.locator('.fl .lc').count()
        check('F3 线路卡片数 = 数据里的线路数', cards == len(SU['routes']), (cards, len(SU['routes'])))
        t0 = pg.inner_text('.fl .lc >> nth=0')
        check('F3 线路卡有天数、出发月份、人均价、难度标签', re.search(r'\d+\s*天', t0) and re.search(r'\d+[\s\xa0]月出发', t0) and '人均' in t0 and re.search(r'平路|山路多|上高原', t0), t0)
        body = pg.inner_text('body'); html_ = pg.content()
        leak = [s for s in SRCS if s in body or s in html_]
        check('F3 主题页里没有任何 src 原文', not leak, leak[:2])
        check('F3 有“只写有记载的事，传说会标明相传”', '只写有记载的事，传说会标明相传' in body)
        shot(pg, 'F3_topic.png')
        # F4 点线路
        first = pg.locator('.fl .lc a >> nth=0'); href = first.get_attribute('href'); rid = href.strip('/').split('/')[-1]
        first.click(); pg.wait_for_url('**' + href); pg.wait_for_timeout(800)
        ban = pg.locator('a.fbn')
        check('F4 线路页顶部有横幅“这条线路跟着 苏轼 走 ›”', ban.count() == 1 and re.sub(r'\s+', ' ', ban.inner_text()).strip() == f'这条线路跟着 {name_of(SU)} 走 ›', ban.inner_text() if ban.count() else None)
        check('F4 横幅链到 /follow/<主题>/', ban.count() == 1 and ban.get_attribute('href') == f'/follow/{SU["id"]}/')
        bb = ban.bounding_box() if ban.count() else None
        check('F4 横幅是细的（高 ≤56）又够点（≥44）', bb and 44 <= bb['height'] <= 56, bb)
        notes = pg.evaluate("[...document.querySelectorAll('.r .rb p.fnote')].map(p=>({t:p.textContent,v:p.getBoundingClientRect().height>0&&getComputedStyle(p).display!=='none'}))")
        check('F4 线路页有站点小字，且看得见', notes and all(n['v'] for n in notes), notes[:2])
        check('F4 小字都是“苏轼：…”', all(n['t'].startswith(name_of(SU) + '：') for n in notes), [n['t'][:20] for n in notes][:3])
        body = pg.inner_text('body'); html_ = pg.content()
        leak = [s for s in SRCS if s in body or s in html_]
        check('F4 线路页里没有任何 src 原文', not leak, leak[:2])
        # conf=medium（且句子里没有“相传”）的站点：找一条含它的线路页，小字前面要有“相传”
        ITm = json.load(open(os.path.join(ROOT_, 'data', 'itineraries.json'), encoding='utf-8'))['itineraries']
        medium = None
        for r_ in SU['routes']:
            names_ = {s_['name'] for d_ in ITm[r_]['days'] for s_ in d_['stops']}
            for k_, v_ in SU['notes'].items():
                if v_.get('conf') == 'medium' and '相传' not in v_['line'] and k_ in names_ and medium is None: medium = (r_, k_, v_['line'])
        if medium:
            pg.goto(env.B + f'/trip/{medium[0]}/', wait_until='networkidle'); pg.wait_for_timeout(500)
            texts = [re.sub(r'[\xa0\s]+', '', t_) for t_ in pg.evaluate("[...document.querySelectorAll('.r .rb p.fnote')].map(p=>p.textContent)")]
            want = re.sub(r'[\xa0\s]+', '', name_of(SU) + '：相传' + medium[2].strip().rstrip('。'))
            check(f'F4 conf=medium（{medium[1]}）的站点小字前面有“相传”', want in texts, (want[:30], texts[:2]))
        else: check('F4 数据里有 conf=medium 的站点注释（测试素材）', False)
        pg.goto(env.B + href, wait_until='networkidle'); pg.wait_for_timeout(500)
        if notes: pg.evaluate("document.querySelector('.r .rb p.fnote').scrollIntoView({block:'center'})"); pg.wait_for_timeout(200)
        shot(pg, 'F4_trip_banner_notes.png')
        pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(100); shot(pg, 'F4_trip_top.png')
        ban.click(); pg.wait_for_url(f'**/follow/{SU["id"]}/'); pg.wait_for_timeout(300)
        check('F4 点横幅回到主题页', pg.url.rstrip('/').endswith(f'/follow/{SU["id"]}'), pg.url)
        c.close()

    # ———— F5 触控 ————
    with guard('F5'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/follow/')
        for nm, sel in [('搜索框', '.fsearch input'), ('主题卡', '.fcd a >> nth=0'), ('页头返回', '.pagehead a.back')]:
            h_ = pg.evaluate(HIT, pg.locator(sel).element_handle())
            check(f'F5 /follow/ {nm} 实际点击区 ≥44×44', h_ and h_['h'] >= 44 and h_['w'] >= 44, h_)
        goto(env, pg, f'/follow/{SU["id"]}/')
        for nm, sel in [('线路卡', '.fl .lc a >> nth=0')] + ([('年表“看其余”', '.ftlm summary')] if pg.locator('.ftlm summary').count() else []):
            h_ = pg.evaluate(HIT, pg.locator(sel).element_handle())
            check(f'F5 主题页 {nm} 实际点击区 ≥44×44', h_ and h_['h'] >= 44 and h_['w'] >= 44, h_)
        rid0 = SU['routes'][0]
        goto(env, pg, f'/trip/{rid0}/')
        h_ = pg.evaluate(HIT, pg.locator('a.fbn').element_handle()) if pg.locator('a.fbn').count() else None
        check('F5 线路页横幅实际点击区 ≥44×44', h_ and h_['h'] >= 44 and h_['w'] >= 44, h_)
        c.close()

    # ———— F6 博物馆周一红字 ————
    with guard('F6'):
        # 找一条有 type=museum 站点的主题线路
        IT = json.load(open(os.path.join(ROOT_, 'data', 'itineraries.json'), encoding='utf-8'))['itineraries']
        pick = None
        for h in H.values():
            for r in h['routes']:
                for di, d in enumerate(IT[r]['days']):
                    for s in d['stops']:
                        if s.get('type') == 'museum' and pick is None: pick = (r, di, s['name'])
        check('F6 主题线路里有 type=museum 的站（测试素材）', pick is not None)
        if pick:
            rid_, di, nm = pick; mon = next_monday()
            c = new_ctx(br, p, storage={'zouni_start_' + rid_: mon}); pg = new_page(env, c)
            goto(env, pg, f'/trip/{rid_}/', 900)
            day0 = datetime.date.fromisoformat(pg.evaluate("document.querySelector('.dpk').value"))
            check('F6 出发日改成周一（测试前提）', day0.weekday() == 0, str(day0))
            red = pg.evaluate("(di)=>{const sec=document.querySelectorAll('.day')[di];return [...sec.querySelectorAll('.r[data-mc=\"1\"] .clw')].map(x=>x.textContent)}", di)
            # 周一落在第几天：day0 周一 → 第 di 天是周(1+di)%7；只有 di==0 时是周一。其余天用“把那一天对上周一”的出发日
            c.close()
            start = datetime.date.fromisoformat(mon) - datetime.timedelta(days=di)
            c = new_ctx(br, p, storage={'zouni_start_' + rid_: start.isoformat()}); pg = new_page(env, c)
            goto(env, pg, f'/trip/{rid_}/', 900)
            sd = pg.evaluate("document.querySelector('.dpk').value")
            wk = (datetime.date.fromisoformat(sd) + datetime.timedelta(days=di)).weekday()
            red = pg.evaluate("(di)=>{const sec=document.querySelectorAll('.day')[di];return [...sec.querySelectorAll('.r[data-mc=\"1\"] .clw')].map(x=>x.textContent)}", di)
            check(f'F6 {rid_} 第 {di + 1} 天落在周一时，博物馆行（{nm}）有红字“这天是周一…”', wk == 0 and len(red) >= 1 and all(t.startswith('这天是周一') for t in red), (sd, wk, red))
            col = pg.evaluate("(di)=>{const x=document.querySelectorAll('.day')[di].querySelector('.r[data-mc=\"1\"] .clw');return x?getComputedStyle(x).color:null}", di)
            check('F6 红字是红色（r 远大于 g、b）', col is not None and (lambda m: m[0] > 150 and m[1] < 90 and m[2] < 90)(list(map(int, re.findall(r'\d+', col)[:3]))), col)
            shot(pg, 'F6_museum_monday.png')
            c.close()
            # 默认出发日：数据里 museum 的那一天不落在周一
            c = new_ctx(br, p); pg = new_page(env, c)
            goto(env, pg, f'/trip/{rid_}/', 900)
            sd = pg.evaluate("document.querySelector('.dpk').value")
            wk = (datetime.date.fromisoformat(sd) + datetime.timedelta(days=di)).weekday()
            check(f'F6 {rid_} 默认出发日让 museum 那天（第 {di + 1} 天）不落在周一', wk != 0, (sd, wk))
            check(f'F6 {rid_} 默认出发日时 museum 行没有红字', pg.evaluate("document.querySelectorAll('.r[data-mc=\"1\"] .clw').length") == 0)
            c.close()

    # ———— F7 暗色 ————
    with guard('F7'):
        c = new_ctx(br, p, dark=True); pg = new_page(env, c)
        for path, sel in [('/', '.chan2 b'), ('/follow/', '.fcd b'), (f'/follow/{SU["id"]}/', '.fintro'), (f'/trip/{SU["routes"][0]}/', '.fbn')]:
            goto(env, pg, path, 700)
            ov = pg.evaluate(NOSCROLL)
            cc = pg.evaluate(CONTRAST, [sel])
            check(f'F7 暗色 {path} 无横向溢出', ov <= 0, ov)
            check(f'F7 暗色 {path} 文字对比度 ≥4.5，背景是暗的', cc and cc['c'] >= 4.5 and cc['bgl'] < 0.3, cc)
            if path.startswith('/follow/') and path != '/follow/': shot(pg, 'F7_dark_topic.png')
        c.close()
        # 亮色也量溢出（反向注入 overflow 靠它）
        c = new_ctx(br, p); pg = new_page(env, c)
        for path in ('/follow/', f'/follow/{SU["id"]}/', f'/trip/{SU["routes"][0]}/'):
            goto(env, pg, path, 500); ov = pg.evaluate(NOSCROLL)
            check(f'F7 亮色 {path} 无横向溢出', ov <= 0, ov)
        c.close()
    br.close()
env.finish('跟谁走 follow_check')
