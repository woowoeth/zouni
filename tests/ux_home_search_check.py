#!/usr/bin/env python3
"""首页与搜索（2026-10-17，任务单第 7 组）+ 首页数据补齐不丢功能（第 8 组的功能面）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/ux_home_search_check.py build/site [--shots DIR]
    python3 tests/ux_home_search_check.py build/site --inject who_ignored|left14|cover_scrim|search_jump|mine_nodate    # 反向自检

  H1 替我挑三条：和谁去、出行方式真的改变结果
     - 带老人孩子：结果里没有高原、国外、要徒步爬山/走路多/台阶多/坡多的线；每条理由里写“带老人孩子：…”
     - 两个人：有海岛/温泉/古镇…的线排上来、理由写“两个人去：…”
     - 不开车：结果里没有要自己开车的线；理由写“不用自己开车”
     - 6 个出发城市 × 周末/4–5 天/一周以上：“带老人孩子”的前三条和“自己或朋友”的不一样的占比 ≥ 60%；“两个人”和“自己或朋友”不一样 ≥ 40%；“不开车”和“自驾也行”不一样 ≥ 25%
  H2 卡片上“最后 N 天”：只在真的剩 ≤2 天时才写；其余写“最好 M/D–M/D”；全表里写“最后”的不超过 5%
  H3 首页封面标题：把标题文字藏掉后截图，标题背后最亮的像素和字色（#f4f2ec）对比度 ≥ 4.5（亮、暗两种配色）
  H4 搜索：从首页提交 → /where/?q=土楼：落在“搜「土楼」· 符合的 N 个”这一行（吸顶栏下面 ≤ 40px），线路索引慢 3 秒到也不把落点顶走（位移 ≤2px）；
     线路按相关度排：名字里有的在前，只在正文里提到的收起来（点“再看”才展开）；西安：前几条名字里都有“西安”
  H5 我的行程：每行写“N 天 · M/D 周X 出发 · 还有 N 天”，没定日期的写“出发日期还没定”，右边有“打开 ›”；点了进到线路页
  H6 数据补齐：补齐后列表条数 ≥ 1400；首屏 HTML 里只有 8 条 + 其它区块；每条 li 的数据属性齐全；首页没有“全部线路目录”，/all/ 页有每条线路的链接（sitemap 也有），关掉 JS 首屏 8 张卡片仍在
"""
import itertools, json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from PIL import Image
import io

INJ = {
    'who_ignored': ('assets/site.js', "if(st.w==='o'){if(phys.length)return;", "if(false){if(phys.length)return;"),                       # 带老人孩子不再过滤徒步爬山
    'left14': ('assets/site.js', "lf.className='left'+(li._l<=2?' urgent':'');lf.textContent=li._l<=2?", "lf.className='left'+(li._l<=14?' urgent':'');lf.textContent=li._l<=14?"),   # 又是 14 天内都写“最后 N 天”
    'cover_scrim': ('assets/site.css', ".home .cover:after{inset:0;background:linear-gradient(to bottom,rgba(20,18,24,0) 18%,rgba(20,18,24,.62) 44%,rgba(20,18,24,.9) 66%,rgba(20,18,24,.96))}", ".home .cover:after{inset:0;background:none}"),   # 遮罩去掉
    'search_jump': ('assets/site.js', ["setTimeout(land,60);", "if(!moved)land()"], ["setTimeout(function(){zjump(Math.max(0,((document.querySelector('.wtr')||cnt).getBoundingClientRect().top+(window.pageYOffset||0))-130))},60);", "0"]),   # 又落在线路块上（字体就绪后的校正也拿掉）
    'mine_nodate': ('assets/site.js', "var when='<small class=\"mw\">'+esc(zWhen(x))+'</small>';", "var when='';"),                                           # 我的行程不写日期
}
env = Env(INJ)
check, guard = env.check, env.guard


def tops(pg):
    return pg.evaluate("[...document.querySelectorAll('.pkres li')].map(l=>({h:l.querySelector('a').getAttribute('href'),why:l.querySelector('small').innerText}))")


with sync_playwright() as p:
    br = p.chromium.launch()

    # ———— H6 数据补齐 ————
    with guard('H6'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/'); home_ready(pg)
        n = pg.evaluate("document.querySelectorAll('.now .items li').length")
        check('H6 补齐后“现在去正好”列表里 li 总数 %d ≥ 1400' % n, n >= 1400, n)
        miss = pg.evaluate("[...document.querySelectorAll('.now .items li')].filter(l=>!(l.dataset.band&&l.dataset.n&&l.dataset.h&&l.dataset.src&&'clim' in l.dataset&&'tg' in l.dataset&&l.querySelector('h3 a')&&l.querySelector('.tile'))).length")
        check('H6 每条 li 的数据属性、标题、小图都齐', miss == 0, miss)
        vis = pg.evaluate("document.querySelectorAll('.now .items li:not([hidden])').length")
        check('H6 补齐后首屏仍只露 8 条', vis == 8, vis)
        raw = pg.request.get(env.B + '/').text()
        check('H6 首页不再有“全部线路目录”', '全部线路目录' not in raw and 'allidx' not in raw, '')
        allp = pg.request.get(env.B + '/all/'); allt = allp.text()
        alinks = set(re.findall(r'href="/trip/([^/"]+)/"', allt))
        check('H6 /all/ 有 ≥1450 条线路链接（给搜索引擎）', allp.status == 200 and len(alinks) >= 1450, (allp.status, len(alinks)))
        check('H6 sitemap.xml 含 /all/', '/all/</loc>' in pg.request.get(env.B + '/sitemap.xml').text(), '')
        check('H6 首页 HTML 原始 ≤ 400KB', len(raw.encode('utf-8')) <= 400 * 1024, len(raw.encode('utf-8')))
        now_sec = raw[raw.index('id="now"'):]; now_sec = now_sec[:now_sec.index('</section>')]
        li_in_html = len(re.findall(r'<li data-band=', now_sec))
        check('H6 HTML 里“现在去正好”的卡片只有 8 张（%d）' % li_in_html, li_in_html == 8, li_in_html)
        c.close()
        c = new_ctx(br, p, java_script_enabled=False); pg2 = c.new_page(); pg2.goto(env.B + '/', wait_until='load')
        nl = pg2.evaluate("document.querySelectorAll('.now .items li:not([hidden]) a[href^=\"/trip/\"]').length")
        check('H6 关掉 JS：首屏 8 张卡片的线路链接都在（%d ≥ 8）' % nl, nl >= 8, nl)
        c.close()

    # ———— H1 替我挑三条 ————
    with guard('H1'):
        ORG = ['成都', '上海', '北京', '广州', '西安', '武汉']
        res = {}
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/'); home_ready(pg)
        meta = pg.evaluate("Object.fromEntries([...document.querySelectorAll('.toc .items li')].map(l=>[l.getAttribute('data-h'),{hi:l.dataset.hi,ab:l.dataset.ab,sd:l.dataset.sd,tg:l.dataset.tg||''}]))")
        for o, d, w, v in itertools.product(ORG, 'wml', 'fco', 'an'):
            pg.evaluate("(st)=>{localStorage.setItem('zouni_pick',JSON.stringify(st))}", {'o': o, 'd': d, 'w': w, 'v': v})
            pg.reload(wait_until='networkidle'); home_ready(pg)
            pg.click('.pkh'); pg.wait_for_timeout(120)
            res[(o, d, w, v)] = tops(pg)
        PHYS = {'徒步', '爬山', '走路多', '台阶多', '坡多'}
        bad_o = [(k, r['h']) for k, rs in res.items() if k[2] == 'o' for r in rs if meta.get(r['h'], {}).get('hi') == '1' or meta.get(r['h'], {}).get('ab') == '1' or (PHYS & set(meta.get(r['h'], {}).get('tg', '').split('|')))]
        check('H1 带老人孩子：结果里没有高原、国外、徒步爬山/走路多/台阶多/坡多的线（%d 条结果查过）' % sum(len(rs) for k, rs in res.items() if k[2] == 'o'), not bad_o, bad_o[:3])
        no_why = [(k, r['h']) for k, rs in res.items() if k[2] == 'o' for r in rs if '带老人孩子：' not in r['why']]
        check('H1 带老人孩子：每条结果都写了一句“带老人孩子：…”的理由', not no_why, no_why[:3])
        bad_n = [(k, r['h']) for k, rs in res.items() if k[3] == 'n' for r in rs if meta.get(r['h'], {}).get('sd') == '1']
        check('H1 不开车：结果里没有要自己开车的线', not bad_n, bad_n[:3])
        n_total_n = sum(len(rs) for k, rs in res.items() if k[3] == 'n')
        n_why_n = sum(1 for k, rs in res.items() if k[3] == 'n' for r in rs if '不用自己开车' in r['why'])
        check('H1 不开车：有些结果写了“不用自己开车”（%d/%d）' % (n_why_n, n_total_n), n_why_n > 0, n_why_n)
        n_why_c = sum(1 for k, rs in res.items() if k[2] == 'c' for r in rs if '两个人去：' in r['why'])
        check('H1 两个人：有结果写了“两个人去：有海岛/温泉/古镇…”（%d 条）' % n_why_c, n_why_c > 0, n_why_c)

        def frac(key_a, key_b):
            ks = [(o, d, w, v) for o, d, w, v in itertools.product(ORG, 'wml', 'fco', 'an') if w == key_a[0] and v == key_a[1]]
            diff = tot = 0
            for o, d, w, v in ks:
                a = [r['h'] for r in res[(o, d, w, v)]]; b = [r['h'] for r in res[(o, d, key_b[0], v)]]
                if not a and not b: continue
                tot += 1; diff += (set(a) != set(b))
            return diff, tot
        d1, t1 = frac(('f', 'a'), ('o', 'a')); d2, t2 = frac(('f', 'a'), ('c', 'a'))
        dv = tot_v = 0
        for o, d, w in itertools.product(ORG, 'wml', 'fco'):
            a = [r['h'] for r in res[(o, d, w, 'a')]]; b = [r['h'] for r in res[(o, d, w, 'n')]]
            if a or b: tot_v += 1; dv += (set(a) != set(b))
        env.note('前三条不一样的占比：带老人孩子 vs 自己或朋友 %d/%d；两个人 vs 自己或朋友 %d/%d；不开车 vs 自驾也行 %d/%d' % (d1, t1, d2, t2, dv, tot_v))
        check('H1 “带老人孩子”前三条和“自己或朋友”不同的占比 ≥ 60%%（%d/%d）' % (d1, t1), t1 and d1 >= 0.6 * t1, (d1, t1))
        check('H1 “两个人”前三条和“自己或朋友”不同的占比 ≥ 40%%（%d/%d）' % (d2, t2), t2 and d2 >= 0.4 * t2, (d2, t2))
        check('H1 “不开车”前三条和“自驾也行”不同的占比 ≥ 25%%（%d/%d）' % (dv, tot_v), tot_v and dv >= 0.25 * tot_v, (dv, tot_v))
        # 截图：成都 周末 带老人孩子
        pg.evaluate("(st)=>{localStorage.setItem('zouni_pick',JSON.stringify(st))}", {'o': '成都', 'd': 'w', 'w': 'o', 'v': 'a'}); pg.reload(wait_until='networkidle'); home_ready(pg); pg.click('.pkh'); pg.wait_for_timeout(300)
        if env.shots: pg.locator('.pick').screenshot(path=os.path.join(env.shots, 'H1_pick_old.png'))
        c.close()

    # ———— H2 最后 N 天 ————
    with guard('H2'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/'); home_ready(pg)
        lf = pg.evaluate("[...document.querySelectorAll('.now .items li')].filter(l=>l.querySelector('.left')&&!l.hidden||true).map(l=>l.querySelector('.left').textContent)")
        last = [t for t in lf if '最后' in t]
        ns = [int(re.search(r'最后 (\d+) 天', t).group(1)) if re.search(r'最后 (\d+) 天', t) else 0 for t in last]
        check('H2 全表里写“最后 N 天”的只占 %d/%d（≤5%%）' % (len(last), len(lf)), len(last) <= 0.05 * len(lf), (len(last), len(lf)))
        check('H2 写了“最后 N 天”的 N 都 ≤2', all(x <= 2 for x in ns), ns[:10])
        vis = pg.evaluate("[...document.querySelectorAll('.now .items li:not([hidden]) .left')].map(l=>l.textContent)")
        check('H2 首屏 8 张卡里没有“最后 3 天/4 天”这类（剩 >2 天写“最好 M/D–M/D”）', all(('最好' in t) or ('最后' in t and int(re.search(r'\d+', t).group()) <= 2 if re.search(r'\d+', t) else True) for t in vis), vis)
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'H2_home_cards.png'))
        c.close()

    # ———— H3 封面标题对比度 ————
    with guard('H3'):
        def lum(rgb):
            f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else (((v / 255 + 0.055) / 1.055) ** 2.4)
            return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2])
        for dark in (False, True):
            c = new_ctx(br, p, dark=dark); pg = new_page(env, c); goto(env, pg, '/', 800)
            pg.evaluate("scrollTo({top:0,behavior:'instant'})")
            pg.add_style_tag(content='.home .cv h2,.home .cv h2 *{color:transparent!important;text-shadow:none!important}.home .cv .chips,.home .cv .kick,.home .cv .go{visibility:hidden}')
            bb = pg.locator('.home .cv h2').bounding_box()
            png = pg.screenshot(clip={'x': bb['x'], 'y': bb['y'], 'width': bb['width'], 'height': bb['height']})
            im = Image.open(io.BytesIO(png)).convert('RGB'); px = list(im.getdata()); ls_ = sorted(lum(x) for x in px)
            p95 = ls_[int(len(ls_) * 0.95)]; fg = lum((244, 242, 236))
            ratio = (fg + 0.05) / (p95 + 0.05)
            check('H3 %s 封面标题背后最亮的 5%% 像素和字色对比度 %.1f ≥ 4.5' % ('暗色' if dark else '亮色', ratio), ratio >= 4.5, round(ratio, 2))
            env.note('封面标题背景亮度 p95=%.3f，对比度 %.1f（%s）' % (p95, ratio, '暗' if dark else '亮'))
            c.close()
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/', 800)
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'H3_home_cover.png'), clip={'x': 0, 'y': 0, 'width': 390, 'height': 340})
        c.close()

    # ———— H4 搜索 ————
    with guard('H4'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/'); home_ready(pg)
        pg.fill('.hsearch input', '土楼'); pg.click('.hsearch button'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1500)
        check('H4 从首页提交后到了 /where/?q=…', '/where/' in pg.url and 'q=' in pg.url, pg.url)
        d = pg.evaluate("(()=>{const a=document.querySelector('.orgnote:not([hidden])')||document.querySelector('.cnt'),s=document.querySelector('.stick');return {a:a.getBoundingClientRect().top,s:s?s.getBoundingClientRect().bottom:0,sy:scrollY,t:a.innerText}})()")
        gap = d['a'] - d['s']
        check('H4 落点：“搜「土楼」”这一行紧贴在吸顶栏下面（距离 %dpx，要求 0–40）' % gap, 0 <= gap <= 40, d)
        first = pg.evaluate("[...document.querySelectorAll('.wtr li b')].slice(0,3).map(b=>b.innerText)")
        check('H4 线路里前三条名字里都有“土楼”（%s）' % first, len(first) == 3 and all('土楼' in x for x in first), first)
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'H4_search_landing.png'))
        c.close()
        # 线路索引慢 3 秒：落点不被顶走
        c = new_ctx(br, p); pg = new_page(env, c)
        def slow(route):
            import time; time.sleep(3); route.continue_()
        pg.route(re.compile(r'.*/assets/tidx\.js.*'), slow)
        pg.goto(env.B + '/where/?q=%E5%9C%9F%E6%A5%BC', wait_until='commit'); pg.wait_for_selector('.orgnote', timeout=15000); pg.wait_for_timeout(1200)
        a0 = pg.evaluate("document.querySelector('.orgnote').getBoundingClientRect().top")
        pg.wait_for_function("!document.querySelector('.wtr').hidden", timeout=20000); pg.wait_for_timeout(600)
        a1 = pg.evaluate("document.querySelector('.orgnote').getBoundingClientRect().top")
        check('H4 线路索引晚到：落点不被顶走（位移 %.1fpx ≤2）' % abs(a1 - a0), abs(a1 - a0) <= 2, (a0, a1))
        c.close()
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/where/?q=%E8%A5%BF%E5%AE%89', 1800)
        names = pg.evaluate("[...document.querySelectorAll('.wtr li b')].map(b=>b.innerText)")
        head = [x for x in names[:6]]
        check('H4 搜“西安”：线路前 6 条名字里都有“西安”（%s）' % head, len(head) >= 3 and all('西安' in x for x in head), head)
        mb = pg.locator('.wtm')
        check('H4 搜“西安”：只在正文里提到的线路收起来，有“再看 N 条（含只在正文里提到的）”', mb.count() == 1 and not mb.is_hidden() and '只在正文里提到' in mb.inner_text(), mb.inner_text() if mb.count() else None)
        n0 = pg.locator('.wtr li').count(); mb.click(); pg.wait_for_timeout(300); n1 = pg.locator('.wtr li').count()
        check('H4 点“再看”后展开更多（%d → %d）' % (n0, n1), n1 > n0, (n0, n1))
        c.close()

    # ———— H5 我的行程 ————
    with guard('H5'):
        probe = new_ctx(br, p); pp = new_page(env, probe); goto(env, pp, '/'); mn = pp.evaluate("document.querySelector('.hdpk').dataset.min"); probe.close()
        import datetime as _dt
        sd = (_dt.date.fromisoformat(mn) + _dt.timedelta(days=20)).isoformat(); own = (_dt.date.fromisoformat(mn) + _dt.timedelta(days=45)).isoformat()
        fav = [{'id': 'xa3', 'label': '西安 3\u00a0天', 'title': '三天，在西安看一千年', 'n': 3, 'sd': sd}, {'id': 'tk4', 'label': '东京 4\u00a0天', 'title': '四天，东京'}]
        c = new_ctx(br, p, storage={'zouni_fav': json.dumps(fav, ensure_ascii=False), 'zouni_start_tk4': own}); pg = new_page(env, c)
        goto(env, pg, '/'); pg.click('.minebtn'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(200)
        rows = pg.evaluate("[...document.querySelectorAll('.pk .mrw')].map(r=>({t:r.innerText.replace(/\\n+/g,' | '),href:r.querySelector('a').getAttribute('href'),open:(r.querySelector('.mo')||{}).innerText}))")
        check('H5 我的行程每行写“N 天”（%s）' % rows[0]['t'], re.search(r'3\s*天', rows[0]['t']) and re.search(r'4\s*天', rows[1]['t']), rows)
        check('H5 每行写出发日期和还有几天（存过建议日期的写“建议 M/D 周X 出发 · 还有 N 天”，存过自己日期的不写“建议”）', ('建议' in rows[0]['t'] and re.search(r'\d+/\d+ 周. 出发 · 还有 20 天', rows[0]['t'])) and (re.search(r'4 天 · \d+/\d+ 周. 出发 · 还有 45 天', rows[1]['t']) and '建议' not in rows[1]['t']), rows)
        check('H5 每行右边有明确的“打开 ›”入口', all((r['open'] or '').strip() == '打开 ›' for r in rows), rows)
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'H5_mine.png'))
        pg.click('.pk .mrw a'); pg.wait_for_load_state('networkidle')
        check('H5 点进去到了线路页', '/trip/xa3/' in pg.url, pg.url)
        c.close()
        c = new_ctx(br, p, storage={'zouni_fav': json.dumps([{'id': 'xa3', 'label': '西安 3 天', 'title': '三天'}], ensure_ascii=False)}); pg = new_page(env, c)
        goto(env, pg, '/'); pg.click('.minebtn'); pg.wait_for_selector('.pk')
        t = pg.inner_text('.pk .mrw')
        check('H5 老收藏（没存过建议日期）写“出发日期还没定，点进去选”', '出发日期还没定' in t, t)
        c.close()
    br.close()
env.finish('首页与搜索')
