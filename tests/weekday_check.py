#!/usr/bin/env python3
"""页面里凡是“周几”的说法必须来自所选出发日期的实际星期（2026-10-18，用户反馈 P0）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/weekday_check.py build/site [--n 100] [--seed 7]
    python3 tests/weekday_check.py build/site --inject static_claim|top_off|top_stale|row_generic|dated_stale   # 反向自检，必须变红

W1  静态：全站每个线路页里，没有“这条线哪天是周几”的静态说法（“本线三天是周二到周四”“这天是周二”“第一天是周日”“出发日是…周二，…不落在周一”）——
    场馆自己的闭馆日（“某馆周一闭馆”）、赶集 / 夜市这类固定星期的事实不算
W2  静态：每个馆行里不再重复“多数馆周一休馆，热门馆要提前订票，以官网为准”；整页最多一句通用提醒
W3  浏览器：随机 N 个主题线路页（h 开头）× 随机出发日期（localStorage 写入，和用户在页面里选的一样）：
      a. 每天标题里的“M/D 周X”和那天的真实星期一致
      b. 页面里每个“周X”的说法：要么是这条线某天的真实星期（日期标题、“这天是周X”红字、顶部提醒里的“M/D 周X”），要么是场馆自己的闭馆日说法；其余一律红
      c. 顶部提醒（“这天出发会遇到闭馆”）出现与否 = 这些日期里是否真有“周一闭馆的馆落在周一 / 国外固定闭馆日落在那天”，里面写的每个星期都对
W4  浏览器：改日期后旧句子不残留——先选一个会撞周一的日期（顶部提醒出现、那天有红字），再在日历里改成不撞的，提醒和红字都消失，且页面里没有任何和新日期星期对不上的说法
W5  浏览器：选会撞上闭馆日的日期时，顶部（“出发前”区块里第一条）有提醒“这天出发会遇到闭馆”，写着第几天、哪个馆，并给出建议日期
"""
import datetime, json, os, random, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'top_off': ('assets/site.js', "run();monday();holiday();closeTop();var inp", "run();monday();holiday();var inp"),                                          # 顶部提醒没了（改日期后也不重算）
    'top_stale': ('assets/site.js', "var old=ul.querySelector('.clnote');if(old)old.remove();", ""),                                                              # 改日期后旧的顶部提醒不清
    'dated_stale': ('assets/site.js', "[].slice.call(sec.querySelectorAll('.clw')).forEach(function(x){x.remove()});", ""),                                       # 改日期后行内红字不清
    'row_generic': None,                                                                                                                                              # 页面文本里塞回每馆行的通用句（测试自己改读到的 HTML）
    'static_claim': None,                                                                                                                                             # 页面文本里塞回写死的星期说法（测试自己改读到的 HTML）
}
FAKE = None      # 这两个注入改的是测试读到的页面文本（磁盘上的站不动），验证“判据本身”会红
if '--inject' in sys.argv and sys.argv[sys.argv.index('--inject') + 1] in ('static_claim', 'row_generic'):
    i_ = sys.argv.index('--inject'); FAKE = sys.argv[i_ + 1]; del sys.argv[i_:i_ + 2]
env = Env({k: v for k, v in INJ.items() if v})
if FAKE: env.inject = FAKE
ARGS = sys.argv[1:]
N = int(ARGS[ARGS.index('--n') + 1]) if '--n' in ARGS else 100
SEED = int(ARGS[ARGS.index('--seed') + 1]) if '--seed' in ARGS else 7
check, guard = env.check, env.guard
WD = r'周[一二三四五六日]'
WN = '一二三四五六日'
# 和 tools/wd_scrub.py 不是同一份：这里用另一套更宽的“断言口吻”判据，两边互相查
CLAIM = [re.compile(p) for p in (
    r'(?:是|为|排在|落在|避开了?|分别|定在|没有排在|不落在|不排在|依次)[^，。；、\n]{0,8}?' + WD + r'(?![^，。；\n]{0,3}(?:闭馆|休馆|闭园|休园|闭|休|不开放|开放))',
    WD + r'[^，。；\n]{0,4}(?:出发|落在|是赶路)',
    r'第\s*[一二三四五六七八九十\d]+\s*天[^，。；\n]{0,12}' + WD,
    r'\d+\s*月\s*\d+\s*日[^，。；\n]{0,3}' + WD,
    r'[今当]天[^，。；\n]{0,3}' + WD,
)]
ALLOWED = re.compile(r'闭馆|休馆|休园|开放|关门|赶集|夜市|改期|不是' + WD + r'|别把|多休|闭园|不开|营业')       # 场馆自己的事实 / 对用户改日期的建议


def clean(h):
    h = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    h = re.sub(r'<p class="dnote"[^>]*>.*?</p>', '', h)
    h = re.sub(r'<small>[^<]*\d+/\d+ ' + WD + r'</small>', '', h)
    h = re.sub(r'<(div class="dock"|nav class="daynav)[^>]*>.*?</(div|nav)>', '', h, flags=re.S)
    return h


def claims_in(html):
    out = []
    t = re.sub(r'<[^>]+>', '\n', clean(html))
    for line in t.split('\n'):
        for cl in re.split(r'[。；;]', line):
            if any(p.search(cl) for p in CLAIM) and not ALLOWED.search(cl): out.append(cl.strip()[:80])
    return out


site = env.site
trips = sorted(d for d in os.listdir(os.path.join(site, 'trip')) if os.path.exists(os.path.join(site, 'trip', d, 'index.html')))
hist = [t for t in trips if re.match(r'^h[a-z]', t)]
GEN = '多数馆周一休馆，热门馆要提前订票，以官方网站为准'

# ───────── W1 / W2 静态
bad, gen_rows, gen_pages = {}, 0, 0
for t in trips:
    h = open(os.path.join(site, 'trip', t, 'index.html'), encoding='utf-8').read()
    if FAKE == 'static_claim' and t == 'hjgs1': h = h.replace('<section class="pre">', '<section class="pre"><ul><li>本线三天是周二到周四，没有排在周一</li></ul>', 1)
    if FAKE == 'row_generic' and t == 'hjgs1': h = h.replace('<p class=s>2 小时', '<p class=s>2 小时 · <span class="tix">多数馆周一休馆，热门馆要提前订票，以官网为准</span>', 1)
    c = claims_in(h)
    if c: bad[t] = c[:2]
    n = len(re.findall(r'多数馆周一休馆，热门馆要提前订票', h)); gen_rows += n
    gt = len(re.findall(r'多数博物馆、纪念馆周一休馆，热门馆要提前订票', h))
    if gt > 1: gen_pages += 1
check('W1 全站 %d 个线路页：没有“这条线哪天是周几”的静态说法' % len(trips), not bad, list(bad.items())[:4])
check('W2a 每个馆行里不再有“多数馆周一休馆，热门馆要提前订票，以官网为准”（共 %d 处）' % gen_rows, gen_rows == 0, gen_rows)
check('W2b 整页最多一句通用提醒（超过一句的页 %d 个）' % gen_pages, gen_pages == 0, gen_pages)

# ───────── W3 / W4 / W5 浏览器
rnd = random.Random(SEED)
pick = rnd.sample(hist, min(N, len(hist)))
today = datetime.date.today()
PAGE_JS = """()=>{
  const art=document.querySelector('article.trip'); if(!art) return null;
  const days=[...document.querySelectorAll('section.day')].map(s=>{const sm=s.querySelector('header small');return sm?sm.textContent.trim():''});
  const clone=art.cloneNode(true);
  clone.querySelectorAll('script,.dnote,.dock,.daynav,header small,.glance,.hero').forEach(e=>e.remove());
  return {days, text: clone.innerText, top: (document.querySelector('.pre:not(.go) .clnote')||{}).textContent||'', mons: [...document.querySelectorAll('.fc.mon')].map(e=>e.textContent), clw:[...document.querySelectorAll('.clw')].map(e=>e.textContent)}
}"""


def run_page(br, tid, date):
    c = new_ctx(br, None); pg = new_page(env, c)
    iso = date.isoformat(); t = str(int(datetime.datetime.now().timestamp() * 1000))
    pg.add_init_script('try{localStorage.setItem("zouni_start_%s","%s");localStorage.setItem("zouni_startt_%s","%s")}catch(e){}' % (tid, iso, tid, t))
    pg.goto(env.B + '/trip/%s/' % tid, wait_until='load'); pg.wait_for_timeout(450)
    d = pg.evaluate(PAGE_JS)
    return c, pg, d


def judge(tid, date, d):
    errs = []
    for i, s in enumerate(d['days']):
        m = re.search(r'(\d+)/(\d+) 周(.)', s)
        if not m: errs.append('第%d天标题没有日期：%s' % (i + 1, s)); continue
        want = date + datetime.timedelta(days=i)
        if (int(m.group(1)), int(m.group(2)), m.group(3)) != (want.month, want.day, WN[want.weekday()]): errs.append('第%d天标题 %s ≠ %s' % (i + 1, s, '%d/%d 周%s' % (want.month, want.day, WN[want.weekday()])))
    txt = d['text']
    # 顶部提醒里写的每个“M/D 周X”都要对
    for m in re.finditer(r'(\d+)/(\d+) 周(.)', d['top']):
        ok = any((date + datetime.timedelta(days=i)).month == int(m.group(1)) and (date + datetime.timedelta(days=i)).day == int(m.group(2)) and WN[(date + datetime.timedelta(days=i)).weekday()] == m.group(3) for i in range(len(d['days'])))
        ok = ok or (today <= date)   # 建议日期（不是这条线某天的日期）只要求星期和日期对得上
        try:
            # 建议日期可能在所选日期之前或之后（跨年也可能）：取离所选日期最近的那一年算星期
            cands = [datetime.date(date.year + k, int(m.group(1)), int(m.group(2))) for k in (-1, 0, 1)]
            dd = min(cands, key=lambda x: abs((x - date).days))
            ok = WN[dd.weekday()] == m.group(3)
        except Exception: ok = False
        if not ok: errs.append('顶部提醒里的日期星期不对：' + m.group(0))
    # 红字：这天是周X
    for i, s in enumerate(d['mons'] + d['clw']):
        m = re.search(r'这天是周(.)', s)
        if m:
            want = [WN[(date + datetime.timedelta(days=k)).weekday()] for k in range(len(d['days']))]
            if m.group(1) not in want: errs.append('红字星期不是这条线任何一天：' + s[:30])
    # 静态说法
    for line in txt.split('\n'):
        for cl in re.split(r'[。；;]', line):
            if '这天出发会遇到闭馆' in cl: continue
            if re.search(r'这天是周', cl): continue          # 动态红字
            if any(p.search(cl) for p in CLAIM) and not ALLOWED.search(cl): errs.append('静态说法：' + cl.strip()[:60])
    return errs


with sync_playwright() as p:
    br = p.chromium.launch()
    # W3：随机 N 个页 × 随机日期
    with guard('W3'):
        fails, tops_ok, with_top, n_run = [], 0, 0, 0
        for tid in pick:
            date = today + datetime.timedelta(days=rnd.randint(2, 380))
            try:
                c, pg, d = run_page(br, tid, date)
            except Exception as e:
                fails.append((tid, 'load: ' + str(e)[:60])); continue
            n_run += 1
            errs = judge(tid, date, d)
            # c. 顶部提醒的出现 = 真有撞上的闭馆日
            has_clw = bool(d['clw']) or any('这天是周' in x for x in d['mons'])
            if has_clw and not d['top'] and any('闭馆' in x and '这类博物馆有' not in x for x in d['clw'] + d['mons']): errs.append('当天有闭馆红字但顶部没有提醒')   # 软提示（没标周一闭馆的馆）只在当天，不上页头
            if d['top']: with_top += 1
            if errs: fails.append((tid, date.isoformat(), errs[:2]))
            c.close()
        check('W3 随机 %d 个主题页 × 随机出发日期（种子 %d）：日期标题的星期都对、页面里没有和日期对不上的“周X”说法' % (n_run, SEED), n_run >= min(N, len(hist)) - 2 and not fails, fails[:4])
        check('W3c 这 %d 次里有 %d 次出现了顶部闭馆提醒（防空转：要 >0）' % (n_run, with_top), with_top > 0, with_top)
    # W5 / W4：周一撞馆的日期 → 顶部提醒 → 改日期后消失
    with guard('W5'):
        tid = 'hjgs1'
        mon = today + datetime.timedelta(days=(0 - today.weekday()) % 7 + 14)      # 两周后的周一：第 1 天就是周一，井冈山革命博物馆周一闭馆
        c, pg, d = run_page(br, tid, mon)
        first = pg.evaluate("(function(){var li=document.querySelector('.pre:not(.go) ul > li');return li?{cls:li.className,txt:li.textContent}:null})()")
        check('W5a 周一出发：“出发前”里第一条就是闭馆提醒（%s）' % ((first or {}).get('txt') or '')[:60], bool(first) and 'clnote' in first['cls'] and '这天出发会遇到闭馆' in first['txt'], first)
        check('W5b 提醒写了第几天、哪个馆和星期（第 1 天（%d/%d 周一）…）' % (mon.month, mon.day), bool(first) and '第 1 天' in first['txt'] and '周一' in first['txt'] and re.search(r'「[^」]+」', first['txt']) is not None, first)
        m = re.search(r'建议把出发日期改到 (\d+)/(\d+)（?[^）]*周(.)', (first or {}).get('txt') or '')
        alt = None
        if m:
            alt = datetime.date(mon.year if int(m.group(1)) >= mon.month else mon.year + 1, int(m.group(1)), int(m.group(2)))
        check('W5c 提醒里给了建议日期且星期写对（%s）' % (m.group(0) if m else None), bool(m) and alt is not None and WN[alt.weekday()] == m.group(3) and alt > today, m and m.group(0))
        vis = pg.evaluate("(function(){var li=document.querySelector('.pre:not(.go) .clnote');if(!li)return null;var r=li.getBoundingClientRect(),cs=getComputedStyle(li),h=document.querySelector('.glance').getBoundingClientRect();return {disp:cs.display,h:Math.round(r.height),y:Math.round(r.top+scrollY),glanceBottom:Math.round(h.bottom+scrollY),inHidden:!!li.closest('[hidden],details:not([open])')}})()")
        check('W5d 顶部提醒看得见（不在折叠 / 隐藏块里），离页顶 %spx（在“建议出发”那一块下面 %spx 内）' % (vis and vis['y'], vis and vis['glanceBottom']), bool(vis) and vis['disp'] != 'none' and vis['h'] > 30 and not vis['inHidden'] and vis['y'] < vis['glanceBottom'] + 1400, vis)
        mons_before = pg.evaluate("document.querySelectorAll('.fc.mon,.clw').length")
        # W4 在日历里改成建议的日期
        if alt:
            pg.click('.dtw'); pg.wait_for_selector('.pk .pk-g')
            # 翻到目标月
            for _ in range(14):
                sel = pg.query_selector('.pk .pk-g button[data-v="%s"]' % alt.isoformat())
                if sel: break
                pg.click('.pk .pk-n'); pg.wait_for_timeout(80)
            pg.click('.pk .pk-g button[data-v="%s"]' % alt.isoformat()); pg.wait_for_timeout(600)
            after = pg.evaluate("(function(){return {top:(document.querySelector('.pre:not(.go) .clnote')||{}).textContent||'',mons:document.querySelectorAll('.fc.mon,.clw').length,days:[].slice.call(document.querySelectorAll('section.day header small')).map(function(e){return e.textContent})}})()")
            check('W4a 改日期后旧的顶部提醒不残留（前：%d 条行内提示；后：顶部“%s”，行内 %d 条）' % (mons_before, after['top'][:20], after['mons']), after['top'] == '' and after['mons'] == 0 and mons_before > 0, (mons_before, after))
            bad_days = [s for i, s in enumerate(after['days']) if not re.search(r'%d/%d 周%s' % ((alt + datetime.timedelta(days=i)).month, (alt + datetime.timedelta(days=i)).day, WN[(alt + datetime.timedelta(days=i)).weekday()]), s)]
            check('W4b 改日期后每天标题的日期和星期都跟着变了', not bad_days and len(after['days']) > 0, bad_days[:2])
            d2 = pg.evaluate(PAGE_JS); e2 = judge(tid, alt, d2)
            check('W4c 改日期后页面里没有和新日期对不上的“周X”说法', not e2, e2[:3])
        c.close()
    br.close()
env.finish('周几说法')
