#!/usr/bin/env python3
"""2026-10-19 可用性审计第一轮修复（heur#1–#5 / a11y 低成本项 / 营地日）的带断言检查。会红，每项都有 --inject 反向自检。

用法（项目根目录；先 bash build/pipe.sh build/site_fx 建好站）：
    python3 tests/fx_check.py build/site_fx [--only F1,F2,…] [--inject 名字] [--shots DIR]
    --inject 的名字见 INJ：只改送到浏览器的 site.js / site.css / 页面 HTML（磁盘不动），对应判据必须变红；旧串找不到 = 注入没生效 = 也算红

判据
  F1  “在这之后加一个…”：按钮可点 ⇒ 点开一定有候选；没有候选的站在弹层里就置灰并写清原因（不新增控件）。xa3 / tk4 / hss1a / hcz1 全部站点逐个点
  F2  “路上”口径：回程“提前到车站 / 机场”缓冲不计入路上（data-drv 与 ZD.facts 一致），页头“最长一天”= 每天“路上约”里最大的那个；小时写法全站“N 小时 M 分”
  F3  去掉站点 / 去掉一天后页面一致：导语不复述旧标题、标题只留还在的站名、“回：第 N 天”读实际序号、出发前清单按剩下的天重算、复制整条行程不带旧标题
  F4  “加一天”候选里含本行程已排过站点的，灰字写“X已排过”并排到末尾
  F5  默认出发日：没有季节限制的线路 = 今天起最近的合理日（不跨年）；跨年才写“明年 M/D（距今 N 天）”
  F6  g318 第 1 天不再写 3,649 米高反
  F7  可访问性：弹层 / 地图接管焦点并在关闭时还给触发按钮；日期选择器 Esc 后焦点回触发处；展开按钮 aria-expanded；深色“出发前查”对比度；小字链接点击区
  F8  营地 / 山屋 / 垭口 / 蒙古包日不出酒店卡与“出发 → 住处”行；自驾线最后一天回程写“开车回城”
"""
import json, os, re, sys, datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    # F1：入口上不再先算候选数
    'precheck_off': ('assets/site.js', "main();precheck();\n", "main();\n"),
    # F2：ZD 把回程“提前到车站 / 机场”的缓冲又算进路上
    'ret_buffer': ('assets/site.js', "if(/→\\s*回程\\s*$/.test(x.name)){var am", "if(false){var am"),
    # F3：去站以后不重拼标题 / 不隐藏导语；去掉一天以后不改“回：第 N 天”、不隐藏出发前条目
    'retitle_off': ('assets/site.js', "zDayLoad(sec);zRetitle(sec);", "zDayLoad(sec);"),
    'lead_keep': ('assets/site.js', "if(ld&&ld.hidden!==stale)ld.hidden=stale;", ""),
    'ret_stale': ('assets/site.js', "gw.textContent=gw.textContent.replace(/回：第[\\s\\S]*$/,", "gw.textContent=gw.textContent.replace(/NEVER_MATCH/,"),
    'pre_stale': ('assets/site.js', "li.hidden=true})}", "li.hidden=false})}"),
    # F4：加一天候选不标“已排过”、不排到末尾
    'ov_off': ('assets/site.js', "已排过</span>':'')", "</span>':'')"),
    'ov_sort': ('assets/site.js', "((a.ov&&a.ov.length?1:0)-(b.ov&&b.ov.length?1:0))||", ""),
    # F5：跨年的日期不写“明年”
    'ny_off': ('assets/site.js', "return d.getFullYear()>n.getFullYear()?'明年 '+fmt(d)", "return false?'明年 '+fmt(d)"),
    'ny_mine': ('assets/site.js', "(d.getFullYear()>nn.getFullYear()?'明年 ':'')+", ""),
    # F6：g318 第 1 天又出现高反提示
    'g318_alt': ('trip/g318/index.html', '<section class="day" id="d1"', '<section class="day" id="d1"><p class="alt"><b>海拔 3,649 米</b></p>'),
    # F7：焦点
    'no_focus': ('assets/site.js', "      focusIn(L);\n", "\n"),
    'no_restore': ('assets/site.js', "try{L.trig.focus({preventScroll:true})}catch(e){}}return true}", "}return true}"),
    'no_trap': ('assets/site.js', "if(e.key==='Tab'){var T=top()", "if(false){var T=top()"),
    'amb_hard': ('assets/site.css', ".st.check{color:var(--amb);box-shadow:inset 0 0 0 1px var(--amb)}", ".st.check{color:#8a5a00;box-shadow:inset 0 0 0 1px #8a5a00}"),
    'hit_off': ('assets/site.css', "inset:-6px -4px}", "inset:0}"),
    'exp_off': ('assets/site.js', "pp.setAttribute('aria-expanded',box.hidden?'false':'true');", ""),
    # F8：营地日又出酒店卡
    'camp_hotel': ('trip/xv29a/index.html', '<ol class="tl">', '<div class="stays" data-area="x"><div class="sh">今晚住</div></div><ol class="tl">'),
}
INJ_TARGET = {'g318_alt': 'g318', 'camp_hotel': 'xv29a'}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
def want(k): return ONLY is None or k in ONLY


def trip(br, rid, storage=None, wait=700, dark=False):
    c = new_ctx(br, None, storage=storage, dark=dark); pg = new_page(env, c)
    goto(env, pg, '/trip/%s/' % rid, wait)
    return c, pg


ADJ = "section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj"

with sync_playwright() as p:
    br = p.chromium.launch(args=['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])

    if want('F1'):
        for rid in ['xa3', 'tk4', 'hss1a', 'hcz1']:
            with guard('F1 ' + rid):
                c, pg = trip(br, rid, wait=800)
                n = pg.evaluate("document.querySelectorAll(%r).length" % ADJ)
                en = dis = bad_open = bad_reason = 0; reasons = {}
                for i in range(n):
                    pg.evaluate("(i)=>{const b=document.querySelectorAll(%r)[i];b.scrollIntoView({block:'center',behavior:'instant'});b.click()}" % ADJ, i)
                    pg.wait_for_selector('.pk')
                    ins = pg.locator('.pk [data-np="ins"]')
                    if not ins.count(): pg.evaluate("history.back()"); pg.wait_for_timeout(100); continue
                    try: pg.wait_for_function("(()=>{const b=document.querySelector('.pk [data-np=\"ins\"]');return b&&(b.disabled||b.getAttribute('data-chk'))})()", timeout=(3000 if env.inject else 20000))
                    except Exception: bad_open += 1
                    if ins.first.is_disabled():
                        dis += 1; tx = pg.inner_text('.pk [data-np="ins"] small') if pg.locator('.pk [data-np="ins"] small').count() else ''
                        reasons[tx[:12]] = reasons.get(tx[:12], 0) + 1
                        if not re.search(r'超过|排满|已有|附近没有|关门|已排到|闭馆', tx): bad_reason += 1
                    else:
                        en += 1
                        ins.first.click(); pg.wait_for_selector('.pk .npc, .pk .npe', timeout=20000)
                        if not pg.locator('.pk .npc').count(): bad_open += 1
                    pg.evaluate("history.back()"); pg.wait_for_timeout(100)
                check('F1 %s：%d 个站，可点 %d（点开都有候选）· 置灰 %d（都写了原因 %s）· 点开却空 / 超时 %d' % (rid, n, en, dis, list(reasons)[:3], bad_open), n > 0 and bad_open == 0 and bad_reason == 0, (bad_open, bad_reason))
                c.close()
        with guard('F1 xa3 第 1 天默认状态'):
            c, pg = trip(br, 'xa3', wait=800)
            pg.evaluate("document.querySelector('#d1 .tl .adj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .tl .adj >> nth=0'); pg.wait_for_selector('.pk')
            pg.wait_for_function("(()=>{const b=document.querySelector('.pk [data-np=\"ins\"]');return b&&(b.disabled||b.getAttribute('data-chk'))})()", timeout=20000)
            st = pg.evaluate("(()=>{const b=document.querySelector('.pk [data-np=\"ins\"]');return {d:b.disabled,t:(b.querySelector('small')||{}).textContent||'',chk:b.getAttribute('data-chk')}})()")
            check('F1 xa3 第 1 天（默认排到 22:10）进弹层就置灰并写原因：%s' % st, st['d'] and ('已排到' in st['t'] or '排满' in st['t'] or '附近没有' in st['t']), st)
            c.close()


    # ———————————————— F2 “路上”口径 ————————————————
    if want('F2'):
        def zlf(m):
            if m < 60: return '%d 分钟' % (int(m / 5 + .5) * 5 or 5)
            h = int(m // 60); r = int((m % 60) / 10 + .5) * 10
            if r == 60: h += 1; r = 0
            return '%d 小时' % h + (' %d 分' % r if r else '')
        for rid in ['xa3', 'bkk3', 'tk4', 'g318']:
            if env.inject == 'ret_buffer' and rid != 'xa3': continue
            with guard('F2 ' + rid):
                c, pg = trip(br, rid, wait=800)
                o = pg.evaluate("(()=>{const d=ZD.days().filter(x=>x.oi>=0).map(x=>({f:ZD.facts(x).drive,drv:+x.sec.dataset.drv,dl:+x.sec.querySelector(':scope > .dload').dataset.d,txt:x.sec.querySelector(':scope > .dload').textContent}));return {d:d,gd:document.querySelector('.glance [data-gd] small').textContent}})()")
                bad = [(i + 1, x) for i, x in enumerate(o['d']) if not (x['f'] == x['drv'] == x['dl'])]
                check('F2 %s 每天：ZD 路上 = 建站 data-drv = 每天那一行（%s）' % (rid, [x['drv'] for x in o['d']][:5]), not bad, bad[:2])
                mx = max(x['drv'] for x in o['d'])
                m = re.search(r'(最长一天|路上最长) (.*)$', o['gd'])
                check('F2 %s 页头“%s”= 最大的一天 %s 且写“N 小时 M 分”' % (rid, o['gd'], zlf(mx)), (mx < 45) or (bool(m) and m.group(2) == zlf(mx)), (o['gd'], mx))
                if rid == 'xa3': check('F2 xa3 最后一天（回程缓冲 160 分钟）路上只有打车的 30 分钟，不是 190：%s' % [x['drv'] for x in o['d']], o['d'][-1]['drv'] == 30 and 'xx' not in o['gd'] and mx == 80, o['d'])
                if rid == 'bkk3': check('F2 bkk3 最后一天：只算打车 35 + 前往机场 60 = 95 分钟（不含“提前 3 小时到”）：%s' % [x['drv'] for x in o['d']], o['d'][-1]['drv'] == 95, o['d'])
                c.close()
        if not env.inject:
            import glob
            bad = []
            for f in glob.glob(os.path.join(env.site, 'trip', '*', 'index.html')):
                h = open(f, encoding='utf-8').read()
                m = re.search(r'<div data-gd="1"><b>[^<]*</b><small>([^<]*)</small>', h)
                if m and re.search(r'\d\.\d 小时', m.group(1)): bad.append(os.path.basename(os.path.dirname(f)))
                if re.search(r'路上约 \d\.\d 小时|要坐 \d\.\d 小时', h): bad.append(os.path.basename(os.path.dirname(f)) + '(faq)')
            check('F2 全站 %s 个页头 / 常见问题里没有“3.2 小时”这种小数写法' % len(glob.glob(os.path.join(env.site, 'trip', '*', 'index.html'))), not bad, bad[:5])

    # ———————————————— F3 改完以后页面一致 ————————————————
    if want('F3'):
        with guard('F3 去掉一站'):
            c, pg = trip(br, 'xa3', wait=800)
            t0 = pg.evaluate("document.querySelector('#d1 h2').textContent.trim()")
            check('F3 前提：xa3 第 1 天原标题含“城墙”且导语可见（%s）' % t0, '城墙' in t0 and pg.evaluate("!document.querySelector('#d1 > .lead').hidden"), t0)
            pg.evaluate("(()=>{const r=[...document.querySelectorAll('#d1 .tl > .r.see')].find(x=>/城墙/.test(x.textContent));r.querySelector('.adj').scrollIntoView({block:'center',behavior:'instant'});r.querySelector('.adj').click()})()")
            pg.wait_for_selector('.pk'); pg.click('.pk [data-x]'); pg.wait_for_timeout(500)
            o = pg.evaluate("({t:document.querySelector('#d1 h2').textContent.trim(),lead:document.querySelector('#d1 > .lead').hidden,ov:document.querySelectorAll('.overview ol li')[0].querySelector('.ot strong').textContent.trim()})")
            check('F3 去掉“西安城墙”后标题不再有“城墙”、保留还在的“钟鼓楼”（%s → %s）' % (t0, o['t']), '城墙' not in o['t'] and '钟鼓楼' in o['t'], o)
            check('F3 复述原标题的导语不再显示', o['lead'] is True, o)
            check('F3 总览里这一天的标题和天标题一致（%s）' % o['ov'], o['ov'] == o['t'], o)
            # 复制整条行程不带旧标题
            pg.evaluate("navigator.clipboard.writeText=function(){return Promise.reject(new Error('x'))};0")
            pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="copy"]'); pg.wait_for_selector('.pk textarea')
            tx = pg.input_value('.pk textarea')
            check('F3 复制整条行程里没有旧标题“%s”，有新标题“%s”' % (t0, o['t']), t0 not in tx and o['t'] in tx, tx[:300])
            pg.evaluate("history.back()"); pg.wait_for_timeout(300)
            # 刷新后还是新的
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(600)
            t1 = pg.evaluate("document.querySelector('#d1 h2').textContent.trim()")
            check('F3 刷新后标题仍是新的（%s）' % t1, t1 == o['t'], t1)
            # 朋友打开分享链接（干净环境）看到的也是新标题
            pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="link"]'); pg.wait_for_timeout(500)
            link = pg.evaluate("window.__clip||''")
            if link:
                c2 = new_ctx(br, None); pg2 = new_page(env, c2); pg2.goto(link.replace(re.sub(r'^(https?://[^/]+).*', r'\1', link), env.B), wait_until='networkidle'); pg2.wait_for_timeout(800)
                t2 = pg2.evaluate("document.querySelector('#d1 h2').textContent.trim()"); l2 = pg2.evaluate("document.querySelector('#d1 > .lead').hidden")
                check('F3 分享链接在干净环境打开：标题 = 改后的、导语不显示（%s）' % t2, t2 == o['t'] and l2 is True, (t2, l2, link[:80]))
                c2.close()
            else: check('F3 拿到分享链接', False, '没有 __clip')
            pg.keyboard.press('Escape'); pg.wait_for_timeout(200)
            # 恢复 → 原样
            pg.evaluate("document.querySelector('#d1 .latewarn .reset').scrollIntoView({block:'center',behavior:'instant'});document.querySelector('#d1 .latewarn .reset').click()"); pg.wait_for_timeout(500)
            o3 = pg.evaluate("({t:document.querySelector('#d1 h2').textContent.trim(),lead:document.querySelector('#d1 > .lead').hidden})")
            check('F3 点“恢复”后标题和导语回到原样', o3['t'] == t0 and o3['lead'] is False, o3)
            c.close()
        with guard('F3 去掉一天'):
            c, pg = trip(br, 'xa3', wait=800)
            txt0 = pg.evaluate("document.querySelector('.pre.go .gw span').textContent")
            pre0 = pg.evaluate("[...document.querySelectorAll('section.pre:not(.go) li')].filter(l=>!l.hidden&&!l.querySelector('li')).map(l=>l.textContent)")
            check('F3 前提：去之前“回：第 3 天”、出发前里有兵马俑条目（%s）' % pre0[:3], '回：第 3' in txt0.replace(' ', ' ') and any('兵马俑' in x for x in pre0), (txt0[-60:], pre0))
            pg.evaluate("document.querySelector('#d2 .dayadj').scrollIntoView({block:'center',behavior:'instant'});document.querySelector('#d2 .dayadj').click()"); pg.wait_for_selector('.pk')
            pg.click('.pk [data-a="rm"]'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1200)
            txt1 = pg.evaluate("document.querySelector('.pre.go .gw span').textContent").replace(' ', ' ')
            n = pg.evaluate("document.querySelectorAll('.day').length")
            m = re.search(r'回：第 (\d+) 天', txt1)
            check('F3 去掉一天后剩 %d 天，“回：第 N 天”读实际最后一天（%s）' % (n, txt1[-70:]), n == 2 and m and int(m.group(1)) == 2, txt1[-80:])
            pre1 = pg.evaluate("[...document.querySelectorAll('section.pre:not(.go) li')].filter(l=>!l.hidden&&!l.querySelector('li')).map(l=>l.textContent)")
            pg.click('.todoall'); pg.wait_for_selector('.tv.todo'); todo = pg.inner_text('.tv.todo')
            check('F3 出发前页内和“出发前要办的事”清单里都没有已去掉那天的兵马俑条目', not any('兵马俑' in x for x in pre1) and '兵马俑' not in todo, (pre1, todo[:200]))
            check('F3 清单里还有留下来的那天的陕西历史博物馆预约', '陕西历史博物馆' in todo, todo[:200])
            c.close()

    # ———————————————— F4 加一天：已排过的站 ————————————————
    if want('F4'):
        with guard('F4'):
            import glob
            cand = None
            for rid in ['xa3', 'bj3', 'cd3', 'hz3', 'sh3', 'gz3', 'nj3', 'cq3', 'wh3', 'cs3']:
                f = os.path.join(env.site, 'trip', rid, 'index.html')
                if not os.path.exists(f): continue
                h = open(f, encoding='utf-8').read(); m = re.search(r'<script type="application/json" id="cands">(.*?)</script>', h, re.S)
                cs = json.loads(m.group(1).replace('<\\/', '</')) if m else []
                if any(x.get('ov') for x in cs) and any(not x.get('ov') for x in cs): cand = rid; break
            check('F4 前提：找到一条“加一天”候选里既有已排过站点、也有没有的线路（%s）' % cand, cand is not None)
            if cand:
                c, pg = trip(br, cand, wait=800)
                pg.evaluate("document.querySelector('.addday .add').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.addday .add'); pg.wait_for_selector('.pk')
                items = pg.evaluate("[...document.querySelectorAll('.pk [data-rid]')].map(b=>({t:b.querySelector('b').textContent,ov:(b.querySelector('.xov')||{}).textContent||''}))")
                flags = [bool(x['ov']) for x in items]
                check('F4 %s：有 %d 条标了“X已排过”（%s）' % (cand, sum(flags), [x['ov'] for x in items if x['ov']][:2]), any(flags) and all(re.search(r'^ · .+已排过$', x['ov']) for x in items if x['ov']), items[:4])
                check('F4 %s：标了的都排在没标的后面（%s）' % (cand, ''.join('○' if not f else '●' for f in flags)), flags == sorted(flags), flags)
                page_txt = pg.evaluate("document.querySelector('article.trip').textContent")
                nm = [re.sub(r'^ · |已排过$', '', x['ov']).split('、') for x in items if x['ov']]
                check('F4 %s：写出的“已排过”站名真在本行程里' % cand, all(n in page_txt for g in nm for n in g), nm)
                c.close()

    # ———————————————— F5 默认出发日 ————————————————
    if want('F5'):
        with guard('F5'):
            import glob
            T = datetime.date.today()
            tr = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'trips.json'), encoding='utf-8')); tr = tr if isinstance(tr, list) else tr['trips']
            any_ = {t['id'] for t in tr if t.get('anytime') or not (t.get('season') or {}).get('best')}
            bad, n, ny_bad, ny_n = [], 0, [], 0
            for f in glob.glob(os.path.join(env.site, 'trip', '*', 'index.html')):
                rid = os.path.basename(os.path.dirname(f)); h = open(f, encoding='utf-8').read()
                m = re.search(r'data-start="([\d-]+)"', h)
                if not m: continue
                d = datetime.date.fromisoformat(m.group(1))
                if rid in any_:
                    n += 1
                    if not (T < d <= T + datetime.timedelta(days=14) and d.year == T.year): bad.append((rid, m.group(1)))
                if d.year > T.year:
                    ny_n += 1; dn = re.search(r'<p class="dnote"[^>]*>([^<]*)</p>', h)
                    if not (dn and ('明年 %d/%d（距今 %d 天）' % (d.month, d.day, (d - T).days)) in dn.group(1).replace('\xa0', ' ')): ny_bad.append((rid, m.group(1)))
            check('F5 没有季节限制的 %d 条线：默认出发日 = 明天起 14 天内、不跨年（例外 %s）' % (n, bad[:3]), n >= 20 and not bad, bad[:5])
            check('F5 默认日期落在明年的 %d 条线：说明行写“明年 M/D（距今 N 天）”，N 算对（例外 %s）' % (ny_n, ny_bad[:3]), not ny_bad, ny_bad[:5])
            c = new_ctx(br, None, storage={'zouni_fav': json.dumps([{'id': 'xa3', 'label': '西安 3 天', 'title': '三天', 'n': 3, 'sd': (T + datetime.timedelta(days=370)).isoformat()}], ensure_ascii=False)}); pg = new_page(env, c)
            goto(env, pg, '/', 600); pg.click('.minebtn'); pg.wait_for_timeout(600)
            tx = pg.evaluate("document.body.innerText")
            check('F5 “我的行程”里跨年的建议日期写“明年 M/D …”', '建议 明年 ' in tx, [l for l in tx.split('\n') if '建议' in l][:2])
            c.close()
            far = (T + datetime.timedelta(days=370)).isoformat()
            c = new_ctx(br, None, storage={'zouni_start_xa3': far, 'zouni_startt_xa3': '1'}); pg = new_page(env, c)
            goto(env, pg, '/trip/xa3/', 800); dn = pg.inner_text('.dnote').replace('\xa0', ' ')
            fd = datetime.date.fromisoformat(far)
            check('F5 自己选了明年的日期：说明行写“明年 %d/%d（距今 %d 天）”（%s）' % (fd.month, fd.day, (fd - T).days, dn), ('明年 %d/%d（距今 %d 天）' % (fd.month, fd.day, (fd - T).days)) in dn, dn)
            c.close()

    # ———————————————— F6 g318 ————————————————
    if want('F6'):
        with guard('F6'):
            c, pg = trip(br, 'g318', wait=800)
            o = pg.evaluate("(()=>{const s=document.querySelector('#d1');return {t:s.textContent,alt:!!s.querySelector('.alt'),fx:[...s.querySelectorAll('.facts .fx small')].map(x=>x.textContent)}})()")
            check('F6 g318 第 1 天（成都 → 雅安）没有“3,649”、没有高反提示、facts 里没有海拔格（%s）' % o['fx'], '3,649' not in o['t'] and not o['alt'] and not any('海拔' in x for x in o['fx']), o['fx'])
            c.close()
        if not env.inject:
            src = open(os.path.join(ROOT, 'tools', 'build_site.py'), encoding='utf-8').read(); cm = open(os.path.join(ROOT, 'tools', 'compile_itineraries.py'), encoding='utf-8').read()
            miss = [k for k, v in {'太白山': 3767, '神农顶': 3105, '哈希勒根达坂': 3400, '喀拉库勒湖': 3600, '白沙湖': 3200}.items() if ("'%s': %d" % (k, v)) not in src]
            check('F6 PASS_ELEV 五个山口 / 湖已补（缺 %s）' % miss, not miss, miss)
            check("F6 compile_itineraries 不再无条件回退到目的地基准海拔", "d.get('elev', dest['base']['elev'])" not in cm, '')

    # ———————————————— F7 可访问性 ————————————————
    if want('F7'):
        FOCUS_IN = "(sel)=>{const a=document.activeElement;return !!a&&!!a.closest(sel)}"
        with guard('F7 焦点：弹层'):
            c, pg = trip(br, 'xa3', wait=800)
            for name, sel in [('调整这一站', '#d1 .tl .adj'), ('调整这一天', '#d1 .dayadj'), ('分享', '.share')]:
                pg.evaluate("(s)=>{const e=document.querySelector(s);e.scrollIntoView({block:'center',behavior:'instant'});e.focus()}", sel)
                pg.keyboard.press('Enter'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(150)
                role = pg.evaluate("(()=>{const k=document.querySelector('.pk');return [k.getAttribute('role'),k.getAttribute('aria-modal'),!!k.getAttribute('aria-label')]})()")
                check('F7 %s：打开后焦点在弹层里，弹层有 role=dialog / aria-modal / 名字（%s）' % (name, role), pg.evaluate(FOCUS_IN, '.pk') and role == ['dialog', 'true', True], role)
                outs = 0
                for i in range(14):
                    pg.keyboard.press('Tab')
                    if not pg.evaluate(FOCUS_IN, '.pk'): outs += 1
                check('F7 %s：连按 14 次 Tab 焦点没跑出弹层（跑出 %d 次）' % (name, outs), outs == 0, outs)
                pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
                back = pg.evaluate("(s)=>document.activeElement===document.querySelector(s)", sel)
                check('F7 %s：Esc 关闭后焦点回到触发按钮' % name, back, pg.evaluate("document.activeElement.className||document.activeElement.tagName"))
            c.close()
        with guard('F7 焦点：日期选择器'):
            c, pg = trip(br, 'xa3', wait=800)
            pg.evaluate("document.querySelector('.glance .dt').focus()"); pg.keyboard.press('Enter'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(150)
            check('F7 日期选择器：焦点在里面', pg.evaluate(FOCUS_IN, '.pk'))
            pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
            check('F7 日期选择器：Esc 后焦点回到“改出发日期”（不是 body）', pg.evaluate("document.activeElement===document.querySelector('.glance .dt')"), pg.evaluate("document.activeElement.tagName"))
            c.close()
        with guard('F7 焦点：地图'):
            c, pg = trip(br, 'xa3', wait=800)
            pg.evaluate("(()=>{const e=document.querySelector('.mapgo');e.scrollIntoView({block:'center',behavior:'instant'});e.focus()})()")
            exp0 = pg.evaluate("document.querySelector('.mapgo').getAttribute('aria-expanded')")
            pg.keyboard.press('Enter'); pg.wait_for_selector('.rm', timeout=15000); pg.wait_for_timeout(600)
            outs = 0
            ins0 = pg.evaluate(FOCUS_IN, '.rm')
            for i in range(30):
                pg.keyboard.press('Tab')
                if not pg.evaluate(FOCUS_IN, '.rm'): outs += 1
            exp1 = pg.evaluate("document.querySelector('.mapgo').getAttribute('aria-expanded')")
            check('F7 地图：打开后焦点在地图里、连按 30 次 Tab 没跑出去（跑出 %d 次）；展开状态 %s → %s' % (outs, exp0, exp1), ins0 and outs == 0 and exp0 == 'false' and exp1 == 'true', (ins0, outs, exp0, exp1))
            pg.keyboard.press('Escape'); pg.wait_for_timeout(600)
            check('F7 地图：Esc 关闭后焦点回到“看路线图”，aria-expanded 回 false', pg.evaluate("document.activeElement===document.querySelector('.mapgo')&&document.querySelector('.mapgo').getAttribute('aria-expanded')==='false'"), pg.evaluate("document.activeElement.className"))
            c.close()
        with guard('F7 aria-expanded'):
            c, pg = trip(br, 'xa3', wait=800)
            pg.evaluate("document.querySelector('.pp').scrollIntoView({block:'center',behavior:'instant'})")
            a0 = pg.evaluate("document.querySelector('.pp').getAttribute('aria-expanded')"); pg.click('.pp'); pg.wait_for_timeout(150); a1 = pg.evaluate("document.querySelector('.pp').getAttribute('aria-expanded')")
            check('F7 “2 人 · 每人”展开按钮 aria-expanded：%s → %s' % (a0, a1), a0 == 'false' and a1 == 'true', (a0, a1))
            pg.evaluate("document.querySelector('.todoall').scrollIntoView({block:'center',behavior:'instant'})")
            t0 = pg.evaluate("document.querySelector('.todoall').getAttribute('aria-expanded')"); pg.click('.todoall'); pg.wait_for_selector('.tv.todo'); t1 = pg.evaluate("document.querySelector('.todoall').getAttribute('aria-expanded')")
            pg.evaluate("history.back()"); pg.wait_for_timeout(300); t2 = pg.evaluate("document.querySelector('.todoall').getAttribute('aria-expanded')")
            check('F7 “出发前要办的事”aria-expanded：%s → %s → %s' % (t0, t1, t2), (t0, t1, t2) == ('false', 'true', 'false'), (t0, t1, t2))
            c.close()
        with guard('F7 深色对比度'):
            c, pg = trip(br, 'xa3', wait=300, dark=True); goto(env, pg, '/d/shaanxi/', 500)
            r = pg.evaluate("""(()=>{const e=document.querySelector('.st.check');if(!e)return null;
              const rgb=s=>{const m=s.match(/[\\d.]+/g).map(Number);return m};const lum=c=>{const f=v=>{v/=255;return v<=.03928?v/12.92:Math.pow((v+.055)/1.055,2.4)};return .2126*f(c[0])+.7152*f(c[1])+.0722*f(c[2])};
              let b=null;for(let n=e;n;n=n.parentElement){const c=rgb(getComputedStyle(n).backgroundColor);if(c.length<4||c[3]>0){b=c;break}}b=b||[22,23,20];
              const f=rgb(getComputedStyle(e).color),l1=lum(f),l2=lum(b);return {ratio:(Math.max(l1,l2)+.05)/(Math.min(l1,l2)+.05),fg:getComputedStyle(e).color,bg:b.join(',')}})()""")
            check('F7 深色模式“出发前查”标签对比度 ≥ 4.5（%s）' % r, r is not None and r['ratio'] >= 4.5, r)
            c.close()
        with guard('F7 小字链接点击区'):
            for path, sel in [('/pian/', '.chan .pm a'), ('/d/shaanxi/', '.sjd a')]:
                c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, path, 500)
                pg.evaluate("[...document.querySelectorAll('details.sjd')].forEach(d=>d.open=true)")      # 2026-10-19：目的地页的影视挂钩收成了折叠
                hs = pg.evaluate("(()=>{const H=%s;return [...document.querySelectorAll(%r)].slice(0,8).map(e=>{const r=H(e);return r?r.h:null})})()" % (HIT, sel))
                hs2 = [h for h in hs if h is not None]
                check('F7 %s %s：点击区高度都 ≥ 24px（%s）' % (path, sel, hs2[:6]), len(hs2) >= 1 and min(hs2) >= 24, hs)
                c.close()

    # ———————————————— F8 营地日 / 自驾回城 ————————————————
    if want('F8'):
        with guard('F8 营地日'):
            for rid, di in [('xv29a', 1), ('gobi4', 2), ('bdjl3', 1)]:
                if env.inject == 'camp_hotel' and rid != 'xv29a': continue
                c, pg = trip(br, rid, wait=400)
                o = pg.evaluate("(d)=>{const s=document.querySelector('#d'+d);return {stays:!!s.querySelector('.stays'),toStay:[...s.querySelectorAll('.tl > .r.dep')].filter(r=>/→\\s*住处/.test(r.textContent)).length,stay:!!s.querySelector('.tl > .r.stay')}}", di)
                check('F8 %s 第 %d 天（营地）：没有酒店卡、没有“出发 → 住处”行，“住 · …”一行还在（%s）' % (rid, di, o), not o['stays'] and o['toStay'] == 0 and o['stay'], o)
                c.close()
            c, pg = trip(br, 'xa3', wait=400)
            o = pg.evaluate("({stays:document.querySelectorAll('.stays').length,toStay:[...document.querySelectorAll('.tl > .r.dep')].filter(r=>/→\\s*住处/.test(r.textContent)).length})")
            check('F8 对照：普通城市线 xa3 照旧有酒店卡和“出发 → 住处”（%s）' % o, o['stays'] >= 1 and o['toStay'] >= 1, o)
            c.close()
        if not env.inject:
            import glob
            it = json.load(open(os.path.join(ROOT, 'data', 'itineraries.json'), encoding='utf-8'))['itineraries']
            asia = {x['id'] for k_ in ('asia', 'world') for x in json.load(open(os.path.join(ROOT, 'data', 'destinations.json'), encoding='utf-8')).get(k_, [])}
            loops = [k for k, v in it.items() if v.get('drive') and v.get('loop') and v['dest'] not in asia and os.path.exists(os.path.join(env.site, 'trip', k, 'index.html'))]
            bad = []
            for k in loops:
                h = open(os.path.join(env.site, 'trip', k, 'index.html'), encoding='utf-8').read()
                last = re.findall(r'<section class="day".*?</section>', h, re.S)[-1]
                m = re.search(r'<p class="m">出发 → 回程</p><p class=s>(.*?)</p>', last)
                if not (m and m.group(1) == '开车回城'): bad.append((k, m and m.group(1)))
            check('F8 国内自驾环线 %d 条：最后一天“出发 → 回程”写“开车回城”（例外 %s）' % (len(loops), bad[:3]), len(loops) >= 10 and not bad, bad[:5])
            h = open(os.path.join(env.site, 'trip', 'g318', 'index.html'), encoding='utf-8').read()
            check('F8 对照：单程自驾 g318 最后一天仍是“去车站或机场”', '去车站或机场' in re.findall(r'<section class="day".*?</section>', h, re.S)[-1], '')
            h = open(os.path.join(env.site, 'trip', loops[0], 'index.html'), encoding='utf-8').read()
            check('F8 “怎么去、怎么回”里写“开车回城”（%s）' % loops[0], '开车回城' in re.search(r'<section class="pre go".*?</section>', h, re.S).group(0), '')

    br.close()
env.finish('fx_check')
