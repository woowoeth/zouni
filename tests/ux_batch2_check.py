#!/usr/bin/env python3
"""第二批用户反馈（6 位模拟用户上一轮剩下的问题，2026-10-17）带断言的检查。会红，每组都有 --inject 反向自检。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/ux_batch2_check.py build/site [--shots DIR] [--only G1,G2,…]
    python3 tests/ux_batch2_check.py build/site --inject 名字        # 故意改坏，对应判据必须变红

  G1 向导选择带到线路页：首页选的出发地、和谁 → 线路页的人数、出发地（可改）、“怎么去”文字、票价估算；“带孩子要多停几次”只对带老人孩子
     （首页挑“两个人/自己或朋友”的不出现；没挑过的照旧出现）；线路页改出发地 → 全站默认（首页向导也变）；人数和出发日期同一规则（谁新听谁的）
     注入：origin_swallow（改写文字的那段又被注释吞掉）| n_ignored（人数不读首页的）| kid_always（提示总出现）| fare_ignored（票价不随出发地）
  G2 每天负荷：每天标题下“今天：走路约…· 开车约…· 要不要早起”；随机 ≥100 天，页面上的分钟数 = 独立重算（dep 行 + 景点停留×步行占比）；
     改出发时间、去掉一站后跟着变；带老人孩子时走路>2.5h/开车>3h 才变色，情侣不变色；cmp.js（Python 算的）的最大值 = 页面（JS 算的）最大值
     注入：load_walk_x2 | load_no_hook（改了时间表不刷新）| load_warn_always
  G3 预约落到景点行、闭馆红字：门票表里写“要预约”的馆（不在 BOOK 名单里的）行里有小标签；当天正好闭馆（周一闭馆、卢浮宫周二）的行里出红字，
     其它天没有；顺路候选里的“要预约”标签在第二行最前面、没被截断
     注入：clw_off | tag_last（候选标签又放回最后）
  G4 国外线时间表常识（数据层，不用浏览器）：晚饭（欧洲 19:30，西班牙/意大利 20:00，作者写的定点不动）、到达日第一行、回国日最后一行、
     “A 进 B 出”开口程提示、瑞士奥地利的山里不自动配打车
     注入（改内存里的数据）：eu_dinner | arr_missing | alp_taxi | oj_missing
  G5 分享与我的行程：对比视图（选 2 条才亮，数字 = 各线路页）、分享图二维码解码 = 线路页网址且与底部网址一致且不带修改状态、
     清单去重（同一个地方连住只列一条、重复的准备事项只列一次）、长线筛选选了月份后“不限/本月能出发”仍在屏幕里
     注入：cmp_always | qr_long | stay_dup | chips_scroll
  G6 离线补全：断网时路线图下有“断网中”说明、点地图图标有“地图需要联网”；走哪儿的地图没有底图时明说；“收进行程”一并存候选分片（所在 3° 格及相邻格）、
     模型、索引；首页专用小字体已接上
     注入：offhint_off | no_extras
"""
import datetime, json, math, os, random, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'origin_swallow': ('assets/site.js', "if(o&&!GO.fx){var gn=goNow();", "if(false){var gn=goNow();"),
    'n_ignored': ('assets/site.js', "function zNEff(id){try{", "function zNEff(id){return 2;try{"),
    'kid_always': ('assets/site.js', "if(w&&w!=='o')[].slice.call(", "if(false)[].slice.call("),
    'fare_ignored': ('assets/site.js', "window.zFareDelta=function(){", "window.zFareDelta=function(){return[0,0];"),
    'load_walk_x2': ('assets/site.js', "if(/^(步行|徒步)/.test(tx))walk+=mn;else{", "if(/^(步行|徒步)/.test(tx))walk+=mn*2;else{"),
    'load_no_hook': ('assets/site.js', "if(window.zDayLoad)window.zDayLoad(sec);", ""),
    'load_warn_always': ('assets/site.js', "warn:zWho()==='o'&&(walk>150||drive>180)", "warn:(walk>150||drive>180)"),
    'clw_off': ('assets/site.js', "if(wk===1)sureR.forEach(", "if(false)sureR.forEach("),
    'tag_last': ('assets/site.js', ["""<small>'+(tag?'<em class="npg">'+tag+'</em> · ':'')+'约 '""","""(c.s?' · '+npEsc(c.s):'')+'</small></button>'}"""], ["""<small>约 '""", """(c.s?' · '+npEsc(c.s):'')+(tag?' · '+tag:'')+'</small></button>'}"""]),
    'cmp_always': ('assets/site.js', "var on=cmpSel.length===2;", "var on=cmpSel.length>=1;"),
    'qr_long': ('assets/site.js', "q.addData(location.origin+location.pathname);", "q.addData(location.origin+location.pathname+'#m=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ');"),
    'stay_dup': ('assets/site.js', "if(pv&&key&&pv.key===key&&i0<=pv.end)", "if(false)"),
    'chips_scroll': ('assets/site.css', ".lpg .lfix{flex:none;display:flex;gap:4px}", ".lpg .lfix{flex:none;display:flex;gap:4px;margin-left:-300px}"),
    'offhint_off': ('assets/site.js', "n.textContent='断网中：路线图是示意图，能看；点地图、导航图标要联网才能打开地图 App。';f.appendChild(n)", "n=null"),
    'no_extras': ('assets/site.js', ".then(function(){return offlineExtras(c)})", ".then(function(){return 0})"),
}
DATA_INJ = {'eu_dinner', 'arr_missing', 'alp_taxi', 'oj_missing'}
INJECT = sys.argv[sys.argv.index('--inject') + 1] if '--inject' in sys.argv else None
if INJECT in DATA_INJ: sys.argv.remove('--inject'); sys.argv.remove(INJECT)       # 数据层注入不改 site.js，也不让 Env 认
env = Env({k: v for k, v in INJ.items()})
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
check, guard = env.check, env.guard
NOW = str(int(time.time() * 1000))
WD = '日一二三四五六'


def want(g): return ONLY is None or g in ONLY


def seed(pick=None, org=None, hn=None, hnt=None, extra=None):
    st = {}
    if pick is not None: st['zouni_pick'] = json.dumps(pick, ensure_ascii=False)
    if org: st['zouni_org'] = org
    if hn: st['zouni_home_n'] = str(hn); st['zouni_home_nt'] = hnt or NOW
    st.update(extra or {})
    return st


def ctx(br, p, storage=None, **kw):
    c = new_ctx(br, p, storage=storage, **kw); pg = new_page(env, c); return c, pg


def hav(a, b):
    r = math.pi / 180; x = (b[1] - a[1]) * r * math.cos((a[0] + b[0]) / 2 * r); y = (b[0] - a[0]) * r
    return round(math.sqrt(x * x + y * y) * 6371)


def jround(x): return int(math.floor(x + 0.5))      # JS Math.round


ZORIG = {'成都': (30.66, 104.07), '上海': (31.23, 121.47), '乌鲁木齐': (43.83, 87.62), '北京': (39.90, 116.40), '广州': (23.13, 113.26)}


def go_way(g, o, km):
    """独立重写一份“怎么去”的文字（国内、不出国的分支）"""
    if km < 60: return f'就在{o}附近，当天过去就行'
    if g.get('drv'): return f'从{o}开过去约 {max(1, jround(km * 1.25 / 80))} 小时；也可以坐高铁或飞机到了再租车'
    if g.get('nh') and km > 900: return f'从{o}坐飞机，约 {max(1, jround(km / 700 + 1))} 小时'
    if g.get('nh') and km > 250: return f'从{o}坐火车约 {max(2, jround(km * 1.25 / 90))} 小时，或者坐飞机'
    if g.get('car') and km <= 600: return f'从{o}坐车约 {max(1, jround(km * 1.3 / 70))} 小时，包车或坐大巴'
    if km <= 1200: return f'从{o}坐高铁约 {max(1, jround(km / 230 + 0.5))} 小时'
    return f'从{o}坐飞机最省事，飞行约 {max(1, jround(km / 700 + 1))} 小时'


def fare(km):
    return (0, 0) if km < 60 else (200, 500) if km < 300 else (500, 1200) if km < 1000 else (1000, 2000) if km < 2000 else (1500, 3000)


def kfmt(v):
    k = jround(v / 100) / 10
    return ('%g' % round(k, 1)) if k < 100 else str(jround(k))


def price_expect(C, N, trans_delta):
    rooms = math.ceil(N / 2)
    car = math.ceil(N / 4) * C['carTotal'] / N if C.get('perCar') else C['tollsPP']
    lodge = C['lodgeRoom'] * rooms / N
    loc = C['tixPP'] + C['foodPP'] + car + lodge
    lo = max(0, loc + C['trans'][0] + trans_delta[0]); hi = max(0, loc + C['trans'][1] + trans_delta[1])
    return '¥%sK–%sK' % (kfmt(lo), kfmt(hi))


def trip_state(pg):
    return pg.evaluate("""()=>{const g=document.querySelector('section.go'),GO=g?JSON.parse(g.dataset.go):null,pr=document.querySelector('.price[data-cost]');
      const q=s=>{const e=document.querySelector(s);return e?e.innerText.trim():null};
      return {go:GO,cost:pr&&pr.dataset.cost?JSON.parse(pr.dataset.cost):null,price:q('.glance .price'),pp:q('.pp'),ppl:q('.ppl b'),dock:q('.dock small'),way:q('.gw span'),
        sel:(()=>{const o=document.querySelector('.ogsel');return o?o.value:null})(),faq:(()=>{const dt=[...document.querySelectorAll('.faq dt')].find(d=>/怎么去/.test(d.textContent));return dt&&dt.nextElementSibling?dt.nextElementSibling.textContent:null})()}}""")


# ——— 每天负荷：从页面里取每天的原始行（独立重算用） ———
DAYS_JS = """()=>[...document.querySelectorAll('.day')].map(sec=>{const rows=[...sec.querySelectorAll('.tl > .r')].filter(r=>!r.hidden).map(r=>{
   const s=r.querySelector(':scope > .rb > p.s'),cls=r.classList.contains('dep')?'dep':(r.classList.contains('see')||r.classList.contains('fun'))?'see':'o';
   let tn='';if(s&&cls==='see'){for(const n of s.childNodes){if(n.nodeType===3&&/\\d+ (小时|分)/.test(n.textContent)){tn=n.textContent;break}}}
   return {c:cls,s:s?s.textContent:'',m:(r.querySelector(':scope > .rb > p.m')||{}).textContent||'',tn:tn,ty:r.dataset.ty||'',t:(r.querySelector('time')||{}).textContent||''}});
  const d=sec.querySelector(':scope > .dload');return {rows:rows,w:d?d.dataset.w:null,d:d?d.dataset.d:null,txt:d?d.innerText:null,cls:d?d.className:null}})"""
SH = {'pk': .5, 'st': .6, 'tn': .5, 'lk': .4, 'bc': .4, 'tp': .4, 'nt': .4, 'sg': .3, 'ms': .25, 'cl': .3, 'fn': .3}      # 这张表在 site.js、build_site.py 各有一份；改一处，这里就红


def mins(t):
    h = re.search(r'(\d+)\s*小时', t or ''); m = re.search(r'(\d+)\s*分', t or '')
    return ((int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)) if (h or m) else 0


def day_expect(rows):
    walk = drive = 0.0
    for r in rows:
        if r['c'] == 'dep':
            tx = re.sub(r'^回住处\s*·\s*', '', r['s']).split('·')[0].strip()
            if re.search(r'→\s*回程\s*$', r.get('m', '')):      # 2026-10-19：回程的“提前到车站 / 机场”是候车缓冲，不算路上；只有“前往机场约 N 分钟”算
                am = re.search(r'前往机场约\s*(\d+)\s*分', tx); drive += int(am.group(1)) if am else 0
            elif tx.startswith('步行'): walk += mins(tx)
            elif not tx.startswith('徒步'): drive += mins(tx)      # 2026-10-18：路上 = 除步行外所有带分钟的移动（火车、地铁、飞机也算）
        elif r['c'] == 'see' and r['tn']:
            walk += mins(r['tn']) * SH.get(r['ty'], .3)
    return int(math.floor(walk + .5)), int(drive)


def day_own(rows):
    """当天自驾 / 开车 / 包车的分钟（2026-10-18：整条线有自驾段时，当天所有非步行移动都是自驾才写“开车约”，混着高铁、打车写“路上约”）"""
    own = 0.0
    for r in rows:
        if r['c'] == 'dep':
            tx = re.sub(r'^回住处\s*·\s*', '', r['s']).split('·')[0].strip()
            if re.match(r'(自驾|开车|包车)', tx): own += mins(tx)
    return own


def lf(m):
    if m < 60: return '%d 分钟' % (jround(m / 5) * 5 or 5)
    h = m // 60; r = jround((m % 60) / 10) * 10
    if r == 60: h += 1; r = 0
    return '%d 小时' % h + (' %d 分' % r if r else '')


def load_routes():
    s = open(os.path.join(ROOT, 'build', 'routes.js'), encoding='utf-8').read()
    return json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', s).group(1))


def read_trip(rid): return open(os.path.join(env.site, 'trip', rid, 'index.html'), encoding='utf-8').read()


def next_wd(start_iso, wd_js, after=14):
    d = datetime.date.fromisoformat(start_iso) + datetime.timedelta(days=after)
    while int(d.strftime('%w')) != wd_js: d += datetime.timedelta(days=1)
    return d.isoformat()


def start_seed(rid, iso): return {'zouni_start_' + rid: iso, 'zouni_startt_' + rid: NOW}


with sync_playwright() as p:
    br = p.chromium.launch()
    TODAY = datetime.date.today().isoformat()

    # ———————————————————— G1 ————————————————————
    if want('G1'):
        with guard('G1'):
            c, pg = ctx(br, p, seed({'o': '成都', 'd': 'm', 'w': 'o'}, '成都', 3))
            goto(env, pg, '/trip/xa3/'); S = trip_state(pg); g = S['go']
            check('G1.1 首页选了“带老人孩子”（3 人）→ 线路页人数是 3 人（人数按钮、人数框、底栏）', S['pp'].startswith('3 人') and S['ppl'] == '3 人' and S['dock'].startswith('3 人'), (S['pp'], S['ppl'], S['dock']))
            km = hav(ZORIG['成都'], (g['lat'], g['lng']))
            exp = go_way(g, '成都', km)
            check('G1.2 “怎么去”按首页选的出发地成都改写（独立重算：%s）' % exp, (S['way'] or '').startswith(exp + '。'), S['way'])
            check('G1.2 常见问题里“怎么去”也跟着', S['faq'] is None or S['faq'] == exp + '。', S['faq'])
            check('G1.3 线路页有出发地选择，当前是成都', S['sel'] == '成都', S['sel'])
            fd = [a - b for a, b in zip(fare(km), fare(g['km']))]
            pe = price_expect(S['cost'], 3, fd)
            check('G1.4 票价按出发地和人数重算（独立重算：%s）' % pe, S['price'] == pe, S['price'])
            # 改出发地：全站默认
            pg.select_option('.ogsel', '乌鲁木齐'); pg.wait_for_timeout(300); S2 = trip_state(pg)
            km2 = hav(ZORIG['乌鲁木齐'], (g['lat'], g['lng'])); exp2 = go_way(g, '乌鲁木齐', km2)
            pick = json.loads(ls(pg, 'zouni_pick') or '{}')
            check('G1.5 线路页改出发地 → “怎么去”马上改写（%s）' % exp2, (S2['way'] or '').startswith(exp2 + '。'), S2['way'])
            check('G1.5 存成全站默认：zouni_pick.o / zouni_org，向导里其它项（天数、和谁）不丢', pick.get('o') == '乌鲁木齐' and ls(pg, 'zouni_org') == '乌鲁木齐' and pick.get('d') == 'm' and pick.get('w') == 'o', (pick, ls(pg, 'zouni_org')))
            fd2 = [a - b for a, b in zip(fare(km2), fare(g['km']))]
            check('G1.5 票价跟着变（%s，和成都那次 %s 不同）' % (price_expect(S['cost'], 3, fd2), S['price']), S2['price'] == price_expect(S['cost'], 3, fd2) and S2['price'] != S['price'], (S2['price'], S['price']))
            if env.shots: pg.screenshot(path=os.path.join(env.shots, 'G1_trip_origin.png'))
            goto(env, pg, '/'); pg.click('.pkh'); pg.wait_for_timeout(200)
            on = pg.inner_text('.pkr[data-k="o"] button.on')
            check('G1.6 回首页：向导里出发地也是乌鲁木齐（同一个默认）', on == '乌鲁木齐', on)
            pg.click('.pkr[data-k="w"] button[data-v="c"]'); pg.wait_for_timeout(150)
            check('G1.7 向导点“两个人”→ 全站默认 2 人', ls(pg, 'zouni_home_n') == '2' and bool(ls(pg, 'zouni_home_nt')), (ls(pg, 'zouni_home_n'), ls(pg, 'zouni_home_nt')))
            pg.click('.pkr[data-k="w"] button[data-v="o"]'); pg.wait_for_timeout(150)
            check('G1.7 向导点“带老人孩子”→ 全站默认 3 人', ls(pg, 'zouni_home_n') == '3', ls(pg, 'zouni_home_n'))
            goto(env, pg, '/trip/ash2/')
            vis = pg.evaluate("[...document.querySelectorAll('.pre li.kid')].map(l=>!l.hidden&&getComputedStyle(l).display!=='none')")
            check('G1.8 “带孩子要多停几次”：带老人孩子时出现（%s）' % vis, len(vis) >= 1 and all(vis), vis)
            c.close()
            for who, label in (('c', '两个人'), ('f', '自己或朋友')):
                c, pg = ctx(br, p, seed({'o': '上海', 'd': 'm', 'w': who}, '上海'))
                goto(env, pg, '/trip/ash2/')
                vis = pg.evaluate("[...document.querySelectorAll('.pre li.kid')].map(l=>!l.hidden&&getComputedStyle(l).display!=='none')")
                n_kid = pg.evaluate("document.querySelectorAll('.pre li.kid').length")
                check('G1.8 选了“%s”：线路页不出现“带孩子…”（共 %d 句，可见 %s）' % (label, n_kid, vis), n_kid >= 1 and not any(vis), vis)
                c.close()
            c, pg = ctx(br, p, {}); goto(env, pg, '/trip/ash2/')
            vis = pg.evaluate("[...document.querySelectorAll('.pre li.kid')].map(l=>!l.hidden&&getComputedStyle(l).display!=='none')")
            check('G1.8 没选过的人：照旧出现（不丢信息）', len(vis) >= 1 and all(vis), vis)
            goto(env, pg, '/trip/xa3/'); S = trip_state(pg)
            check('G1.9 什么都没选过：人数 2 人、出发地选择框是“按附近大城市”、“怎么去”还是页面上写的', S['pp'].startswith('2 人') and S['sel'] == '' and (S['way'] or '').startswith('就在西安附近'), (S['pp'], S['sel'], S['way']))
            c.close()
            c, pg = ctx(br, p, seed({'o': '成都', 'd': 'm', 'w': 'o'}, '成都', 3, str(int(NOW) - 5000)))
            goto(env, pg, '/trip/xa3/'); pg.click('.pp'); pg.click('.ppl button[data-d="1"]'); pg.wait_for_timeout(200)
            check('G1.10 线路页点 +：存这条线自己的人数和时间戳', ls(pg, 'zouni_n_xa3') == '4' and bool(ls(pg, 'zouni_nt_xa3')), (ls(pg, 'zouni_n_xa3'), ls(pg, 'zouni_nt_xa3')))
            goto(env, pg, '/trip/xa3/'); check('G1.10 刷新还是 4 人（比首页那次新）', trip_state(pg)['pp'].startswith('4 人'), trip_state(pg)['pp'])
            pg.evaluate("localStorage.setItem('zouni_home_nt',String(Date.now()+60000));0")
            goto(env, pg, '/trip/xa3/'); check('G1.10 首页后来又选了 → 听首页的 3 人', trip_state(pg)['pp'].startswith('3 人'), trip_state(pg)['pp'])
            c.close()
            c, pg = ctx(br, p, {'zouni_n_xa3': '5'}); goto(env, pg, '/trip/xa3/')
            check('G1.11 老数据：只有这条线自己存的 5 人（没有时间戳）→ 照旧 5 人', trip_state(pg)['pp'].startswith('5 人'), trip_state(pg)['pp']); c.close()

    # ———————————————————— G2 ————————————————————
    if want('G2'):
        with guard('G2'):
            R = load_routes(); ids = sorted(R); random.Random(7).shuffle(ids)
            c, pg = ctx(br, p, {}); n_days = 0; bad = []; per_route = {}
            for rid in ids[:80]:
                goto(env, pg, '/trip/%s/' % rid, 150)
                sv = pg.evaluate("document.querySelector('article.trip').dataset.sv==='1'")
                days = pg.evaluate(DAYS_JS)
                for i, d in enumerate(days):
                    if d['w'] is None: bad.append((rid, i + 1, '没有 .dload')); continue
                    ew, ed = day_expect(d['rows']); n_days += 1
                    if (int(d['w']), int(d['d'])) != (ew, ed): bad.append((rid, i + 1, (d['w'], d['d']), (ew, ed)))
                    own = day_own(d['rows'])
                    exp_txt = ('走路约 ' + lf(ew) if ew >= 15 else '几乎不用走') + ' · ' + (('开车约 ' if (sv and own > 0 and own >= ed - .5) else '路上约 ') + lf(ed) if ed >= 10 else ('不开车' if sv else '路上很短'))      # 2026-10-18：去掉“今天：”前缀
                    if not (d['txt'] or '').startswith(exp_txt): bad.append((rid, i + 1, d['txt'], exp_txt))
                per_route[rid] = (max(int(d['w']) for d in days if d['w']), max(int(d['d']) for d in days if d['d']))
                if n_days >= 160: break
            check('G2.1 随机 %d 天：页面上的走路/开车分钟 = 独立重算（dep 行写的分钟之和；景点停留×步行占比），文字格式一致' % n_days, n_days >= 100 and not bad, bad[:4])
            cm = pg.evaluate("fetch('/assets/cmp.js').then(r=>r.text())")
            Z = json.loads(re.search(r'window.ZCMP=(.*);', cm).group(1))
            diff = [(k, v, Z[k][2:4]) for k, v in per_route.items() if list(v) != Z[k][2:4]]
            check('G2.2 cmp.js 里 Python 算的“最长一天走路/开车”= 页面上 JS 算的（%d 条线路）' % len(per_route), not diff, diff[:3])
            c.close()
            c, pg = ctx(br, p, {'zouni_st_xa3': json.dumps({'0': '06:30'})}); goto(env, pg, '/trip/xa3/')
            t = pg.inner_text('#d1 .dload')
            check('G2.3 把第一天改成 06:30 出发 → 写“要早起（06:30 出发）”（%s）' % t, '要早起（06:30 出发）' in t, t); c.close()
            c, pg = ctx(br, p, {}); goto(env, pg, '/trip/xa3/')
            d0 = pg.evaluate(DAYS_JS)[0]; k_see = pg.evaluate("(()=>{const r=[...document.querySelectorAll('#d1 .tl > .r.see')].find(r=>r.dataset.k!=null);return r?+r.dataset.k:null})()")
            c.close()
            c, pg = ctx(br, p, {'zouni_drop_xa3': json.dumps({'0': [k_see]})}); goto(env, pg, '/trip/xa3/')
            d1 = pg.evaluate(DAYS_JS)[0]; ew, ed = day_expect(d1['rows'])
            check('G2.4 去掉第一天的一站（重新排时间表）：走路 %s → %s 分钟，且等于独立重算 %s' % (d0['w'], d1['w'], ew), int(d1['w']) < int(d0['w']) and int(d1['w']) == ew, (d0['w'], d1['w'], ew)); c.close()
            c, pg = ctx(br, p, {}); goto(env, pg, '/trip/xa3/')
            a0 = pg.evaluate(DAYS_JS)[0]
            pg.locator('#d1 .adj').first.click(); pg.wait_for_selector('.pk'); pg.locator('.pk [data-d="30"]').first.click(force=True); pg.wait_for_timeout(500)
            a1 = pg.evaluate(DAYS_JS)[0]; ew, ed = day_expect(a1['rows'])
            check('G2.4b 用调整里的“多待 30 分钟”改时间表（页面里现场重排，不是重载）：走路 %s → %s，数字跟着变且等于独立重算 %s' % (a0['w'], a1['w'], ew), int(a1['w']) != int(a0['w']) and int(a1['w']) == ew, (a0['w'], a1['w'], ew)); c.close()
            c, pg = ctx(br, p, seed({'o': '北京', 'd': 'm', 'w': 'o'}, '北京')); goto(env, pg, '/trip/ash2/')
            days = pg.evaluate(DAYS_JS); warn = [d for d in days if 'warn' in (d['cls'] or '')]
            col = pg.evaluate("(()=>{const e=document.querySelector('.dload.warn'),n=document.querySelector('.dload:not(.warn)');return e?[getComputedStyle(e).color,n?getComputedStyle(n).color:null]:null})()")
            ok_w = all((int(d['w']) > 150 or int(d['d']) > 180) == ('warn' in (d['cls'] or '')) for d in days)
            check('G2.5 带老人孩子：走路>2.5 小时或开车>3 小时的天有 warn（%d 天），其它没有；颜色和普通的不同（%s）' % (len(warn), col), ok_w and len(warn) >= 1 and col and col[0] != col[1], (ok_w, col))
            check('G2.5 提示是温和的文字，没有弹层', pg.locator('.pk,.toast').count() == 0, '')
            if env.shots: pg.locator('#d1').screenshot(path=os.path.join(env.shots, 'G2_day_load.png'))
            c.close()
            c, pg = ctx(br, p, seed({'o': '北京', 'd': 'm', 'w': 'c'}, '北京')); goto(env, pg, '/trip/ash2/')
            check('G2.6 情侣：同一条线一天都不变色', pg.locator('.dload.warn').count() == 0, pg.locator('.dload.warn').count()); c.close()

    # ———————————————————— G3 ————————————————————
    if want('G3'):
        with guard('G3'):
            tix = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'tickets.json'), encoding='utf-8'))
            bk_src = open(os.path.join(ROOT, 'tools', 'build_site.py'), encoding='utf-8').read()
            book_keys = set(re.findall(r"'([^']+)': '[^']*要[^']*'", bk_src[bk_src.index('BOOK = {'):bk_src.index('BOOK_URL')]))
            need = [k for k, v in tix.items() if re.search(r'要(实名)?预约', v.get('t', '')) and not any(b in k or k in b for b in book_keys)]
            miss = []; left = []; n_checked = 0
            for rid in sorted(load_routes()):
                h = read_trip(rid)
                for m in re.finditer(r'<li class="r (?:see|fun)"[^>]*>(.*?)</li>', h, re.S):
                    body = m.group(1); mm_ = re.search(r'<p class="m">(.*?)</p>', body, re.S)
                    nm = re.sub(r'<[^>]+>', '', mm_.group(1)) if mm_ else ''
                    if re.search(r'<span class="tix">[^<]*要(实名)?预约', body): left.append((rid, nm[:12]))
                    for k in need:
                        if k in nm and 'class="bkn' not in body and not re.search(r'沿途|附近', nm): miss.append((rid, k, nm[:14]))
                        if k in nm and 'class="bkn' in body: n_checked += 1
            check('G3.1 门票表里写了“要预约”、不在 BOOK 名单里的馆（%d 个：%s…）：出现在行程里的 %d 行都有小标签' % (len(need), '、'.join(need[:4]), n_checked), len(need) >= 8 and n_checked >= 5 and not miss, miss[:4])
            check('G3.1 门票那句里不再留下“（要预约）”（标签已经写了，不重复）', not left, left[:4])
            iso = next_wd(TODAY, 0, 14)       # 周日：nj3 第 1 天周日，第 2 天（中山陵）周一
            c, pg = ctx(br, p, start_seed('nj3', iso)); goto(env, pg, '/trip/nj3/')
            got = pg.evaluate("[...document.querySelectorAll('.day')].map((s,i)=>[i,[...s.querySelectorAll('.r .clw')].map(e=>e.closest('.r').querySelector('.m').childNodes[0].textContent.trim()+'｜'+e.textContent)])")
            exp_rows = pg.evaluate("[...document.querySelectorAll('.day')].map((s,i)=>[i,[...s.querySelectorAll('.tl > .r')].filter(r=>/周一(陵寝)?闭馆/.test(r.innerText.replace(/这天是周一，周一(陵寝)?闭馆/,''))).map(r=>r.querySelector('.m').childNodes[0].textContent.trim())])")
            wk = lambda i: (datetime.date.fromisoformat(iso) + datetime.timedelta(days=i)).weekday()      # 周一 = 0
            exp = {i: sorted(names) for i, names in exp_rows if wk(i) == 0 and names}
            gotn = {i: sorted(x.split('｜')[0] for x in v) for i, v in got if v}
            check('G3.2 起点是周日：恰好周一的那天（中山陵）行里出红字；别的天没有（期望 %s，实际 %s）' % (exp, gotn), bool(exp) and exp == gotn, (exp, gotn))
            txt = [x for i, v in got for x in v]
            check('G3.2 红字写“这天是周一，周一闭馆”（中山陵写“周一陵寝闭馆”）', txt and all(re.search(r'这天是周一，周一(陵寝)?闭馆$', x) for x in txt), txt)
            col = pg.evaluate("(()=>{const e=document.querySelector('.clw');return e?getComputedStyle(e).color:null})()")
            check('G3.2 红字是红色（%s）' % col, col == 'rgb(166, 61, 39)', col)
            if env.shots: pg.locator('#d2').screenshot(path=os.path.join(env.shots, 'G3_closed_row.png'))
            c.close()
            iso2 = next_wd(TODAY, 2, 14)      # 周二起：三天是周二、三、四
            c, pg = ctx(br, p, start_seed('nj3', iso2)); goto(env, pg, '/trip/nj3/')
            check('G3.3 起点是周二（三天都不是周一）：没有任何红字', pg.locator('.clw').count() == 0, pg.locator('.clw').count()); c.close()
            par = read_trip('par5'); cw = re.findall(r'data-cw="(\d)"', par)
            c, pg = ctx(br, p, {}); goto(env, pg, '/trip/par5/')
            first = pg.evaluate("(()=>{const ds=[...document.querySelectorAll('.day')];for(let i=0;i<ds.length;i++){const r=ds[i].querySelector('.tl > .r[data-cw]');if(r)return [i,+r.dataset.cw]}return null})()")
            c.close()
            iso3 = next_wd(TODAY, (first[1] - first[0]) % 7 if first else 2, 14)       # 让带 data-cw 的那一天正好落在它闭馆的星期
            c, pg = ctx(br, p, start_seed('par5', iso3)); goto(env, pg, '/trip/par5/')
            gotf = pg.evaluate("[...document.querySelectorAll('.day')].map((s,i)=>[i,[...s.querySelectorAll('.r .clw')].map(e=>e.closest('.r').querySelector('.m').childNodes[0].textContent.trim()+'｜'+e.textContent)])")
            expf = pg.evaluate("[...document.querySelectorAll('.day')].map((s,i)=>[i,[...s.querySelectorAll('.tl > .r[data-cw]')].map(r=>[r.dataset.cw,r.querySelector('.m').childNodes[0].textContent.trim()])])")
            wkj = lambda i: int((datetime.date.fromisoformat(iso3) + datetime.timedelta(days=i)).strftime('%w'))
            exp_f = {i: sorted(n for cwv, n in rows if int(cwv) == wkj(i)) for i, rows in expf}; exp_f = {i: v for i, v in exp_f.items() if v}
            got_f = {i: sorted(x.split('｜')[0] for x in v) for i, v in gotf if v}
            check('G3.4 国外（巴黎 5 天）：起点让奥赛/卢浮宫那天正好落在它的闭馆日，行里出红字“这天是周X，周X闭馆”，别的天没有（期望 %s，实际 %s）' % (exp_f, got_f), bool(cw) and bool(exp_f) and exp_f == got_f, (exp_f, got_f))
            c.close()
            found = None
            c, pg = ctx(br, p, {})
            for rid in ('bj3', 'bj2', 'bj4', 'xa3', 'sh3', 'cd3'):
                if not os.path.exists(os.path.join(env.site, 'trip', rid, 'index.html')): continue
                goto(env, pg, '/trip/%s/' % rid, 300)
                n_day = pg.locator('.day').count()
                for di in range(min(n_day, 4)):
                    pg.locator('.day').nth(di).locator('.adj').first.click(); pg.wait_for_selector('.pk', timeout=8000)
                    if pg.locator('.pk [data-np="ins"]').count() == 0:
                        pg.locator('.pk .pk-x').click(); continue
                    pg.locator('.pk [data-np="ins"]').first.click(force=True); pg.wait_for_timeout(1500)
                    info = pg.evaluate("""[...document.querySelectorAll('.pk .npc')].map(b=>{const sm=b.querySelector('small'),e=sm.querySelector('em.npg'),txt=sm.textContent;
                        const tail=/ · (要预约|周一闭馆|就在旁边)$/.test(txt);if(!e)return tail?{t:'(标签在最后)',first:false,inside:false,txt:txt}:null;
                        const r=sm.getBoundingClientRect(),q=e.getBoundingClientRect();return {t:e.textContent,first:sm.firstChild===e,inside:q.left>=r.left-0.5&&q.right<=r.right+0.5&&q.width>0,txt:txt}}).filter(Boolean)""")
                    if info: found = (rid, di, info); break
                    if pg.locator('.pk .pk-x').count(): pg.locator('.pk .pk-x').click()
                    pg.wait_for_timeout(200)
                if found: break
            if found:
                check('G3.5 顺路候选里的标签（要预约/周一闭馆/就在旁边）在第二行最前面、完整显示（%s 第 %d 天，%d 条带标签：%s）' % (found[0], found[1] + 1, len(found[2]), sorted({x['t'] for x in found[2]})), all(x['first'] and x['inside'] and x['t'] in ('要预约', '周一闭馆', '就在旁边') for x in found[2]), found[2][:2])
                if env.shots: pg.screenshot(path=os.path.join(env.shots, 'G3_cand_tag.png'))
            else:
                check('G3.5 （试了北京/西安/上海/成都的前几天都没遇到带“要预约”的候选，只能查标签生成代码里标签在第二行最前面）', """<small>'+(tag?'<em class="npg">'""" in open(os.path.join(env.site, 'assets', 'site.js'), encoding='utf-8').read(), 'no cand')
            c.close()

    # ———————————————————— G4 数据层 ————————————————————
    if want('G4'):
        with guard('G4'):
            R = load_routes()
            IT = json.load(open(os.path.join(ROOT, 'data', 'itineraries.json'), encoding='utf-8'))['itineraries']
            W = json.load(open(os.path.join(ROOT, 'data', 'destinations.json'), encoding='utf-8'))
            ABROAD = {x['id'] for k in ('asia', 'world') for x in W[k]} | {'taiwan'}
            EU = {x['id'] for x in W['world'] if x.get('region') == '欧洲'}
            if INJECT == 'eu_dinner':
                for rid, r in R.items():
                    if IT.get(rid) and IT[rid]['dest'] == 'france':
                        for d in r['days']:
                            for w in d['rows']:
                                if w['type'] == 'eat' and w.get('slot') == '晚饭' and not w.get('poi'): w['t'] = '18:30'; break
                        break
            if INJECT == 'arr_missing':
                rid = next(k for k, v in IT.items() if v['dest'] == 'japan'); R[rid]['days'][0]['rows'] = [w for w in R[rid]['days'][0]['rows'] if not w.get('arr')]
            if INJECT == 'alp_taxi':
                for rid, r in R.items():
                    if IT.get(rid) and IT[rid]['dest'] in ('switzerland', 'austria'):
                        for d in r['days']:
                            for w in d['rows']:
                                if w['type'] == 'dep' and w.get('how', '').startswith('火车或缆车'): w['how'] = '打车 25 分钟'
            bad = []; n_eu = 0; n_es = 0
            for rid, r in R.items():
                it = IT.get(rid)
                if not it or it['dest'] not in EU: continue
                lim = '20:00' if it['dest'] in ('spain', 'italy') else '19:30'
                for di, d in enumerate(r['days']):
                    for w in d['rows']:
                        if w['type'] == 'eat' and w.get('slot') == '晚饭' and not w.get('poi'):
                            n_eu += 1; n_es += it['dest'] in ('spain', 'italy')
                            if w['t'] < lim: bad.append((rid, di + 1, w['t'], lim))
            check('G4.1 欧洲线默认晚饭 ≥19:30、西班牙/意大利 ≥20:00（%d 顿，其中西意 %d）：没有更早的' % (n_eu, n_es), n_eu > 100 and n_es > 10 and not bad, bad[:4])
            lost = []
            for rid, it in IT.items():
                r = R[rid]
                for di, d in enumerate(it['days']):
                    for st in d['stops']:
                        if st.get('at') and st.get('type') != 'food':      # 吃饭的站（food）行里不带 at，只按它排钟点
                            if not any(w.get('at') == st['at'] and (w.get('name') or '') == st['name'] for w in r['days'][di]['rows']): lost.append((rid, di + 1, st['name'], st['at']))
            check('G4.2 作者在数据里明写的时间（at）一条没丢、没改', not lost, lost[:4])
            late = [(rid, w['t']) for rid, r in R.items() if IT.get(rid) and IT[rid]['dest'] not in EU for d in r['days'] for w in d['rows'] if w['type'] == 'eat' and w.get('slot') == '晚饭' and not w.get('poi') and w['t'] >= '19:30']
            nonlate = sum(1 for rid, r in R.items() if IT.get(rid) and IT[rid]['dest'] not in EU for d in r['days'] for w in d['rows'] if w['type'] == 'eat' and w.get('slot') == '晚饭' and not w.get('poi'))
            check('G4.3 非欧洲线的默认晚饭仍在 18:00–19:30 一带（>19:30 的只占 %.1f%%，是晚点回来顺延的）' % (100.0 * len(late) / max(nonlate, 1)), len(late) / max(nonlate, 1) < 0.1, (len(late), nonlate))
            bad = []; n_ab = 0
            for rid, r in R.items():
                it = IT.get(rid)
                if not it: continue
                ab = it['dest'] in ABROAD
                r0 = r['days'][0]['rows']; rl = r['days'][-1]['rows'][-1]
                if ab:
                    n_ab += 1
                    m = re.match(r'^抵达后从机场到住处约 (\d+) 分钟$', r0[0].get('how') or '')
                    if not (r0[0].get('arr') == 1 and r0[0]['type'] == 'dep' and m and int(m.group(1)) in (30, 45, 60, 75)): bad.append((rid, '到达日第一行', r0[0]))
                    elif r0[0]['t'] != (it['days'][0].get('start') or '09:00'): bad.append((rid, '到达日第一行钟点', r0[0]['t']))
                    elif len(r0) > 1 and r0[1]['type'] == 'dep' and r0[1]['t'] < '%02d:%02d' % divmod(int(r0[0]['t'][:2]) * 60 + int(r0[0]['t'][3:]) + int(m.group(1)), 60): bad.append((rid, '到达日第二行没顺延', r0[1]['t']))
                    if not re.match(r'^前往机场约 \d+ 分钟，提前 3 小时到$', rl.get('how') or '') or rl.get('to') != '回程': bad.append((rid, '回国日最后一行', rl))
                else:
                    if any(w.get('arr') for w in r0): bad.append((rid, '国内线不该有抵达行'))
                    if not (rl.get('how') or '').startswith('开车回城' if (it.get('drive') and it.get('loop')) else '去车站或机场：高铁提前 40 分钟到') or rl.get('to') != '回程': bad.append((rid, '国内回程行', rl))      # 2026-10-19：国内自驾环线最后一天开车回城
            check('G4.4 国外线 %d 条：到达日第一行“抵达后从机场到住处约 N 分钟”（后面顺延）、回国日最后一行“前往机场约 N 分钟，提前 3 小时到”；国内线最后一行“提前到车站”、没有抵达行' % n_ab, n_ab > 300 and not bad, bad[:4])
            geo = json.load(open(os.path.join(ROOT, 'data', 'geo', 'pois.json'), encoding='utf-8'))
            bad = []; n_oj = 0; n_no = 0
            for rid, r in R.items():
                it = IT.get(rid)
                if not it: continue
                h = read_trip(rid)
                if INJECT == 'oj_missing': h = h.replace('机票可以订开口程', '')
                has = '机票可以订开口程' in h
                c0, c1 = r['days'][0].get('city') or '', r['days'][-1].get('city') or ''
                exp_oj = False
                if it['dest'] in ABROAD and len(r['days']) >= 2 and c0 and c1 and c0 != c1:
                    g0, g1 = geo.get(c0 + '|' + c0), geo.get(c1 + '|' + c1)
                    exp_oj = bool(g0 and g1 and g0.get('lat') is not None and g1.get('lat') is not None and hav((g0['lat'], g0['lng']), (g1['lat'], g1['lng'])) >= 250)
                n_oj += exp_oj; n_no += (not exp_oj)
                if has != exp_oj: bad.append((rid, c0, c1, has, exp_oj))
                elif has and not re.search(r'这条线是 %s 进、%s 出' % (re.escape(c0), re.escape(c1)), h): bad.append((rid, '文字', c0, c1))
            check('G4.5 “A 进 B 出”开口程提示：该有的 %d 条都有、不该有的 %d 条（同城进出、国内线、两地相距不到 250 公里或查不到坐标）都没有' % (n_oj, n_no), n_oj > 15 and not bad, bad[:4])
            MOUNT = re.compile(r'缆车|齿轨|索道|登山|山顶|少女峰|铁力士|马特洪|皮拉图斯|里吉|格拉特|冰川|山$|峰$|观景台'); bad = []; chg = []
            for rid, r in R.items():
                it = IT.get(rid)
                if not it or it['dest'] not in ('switzerland', 'austria'): continue
                via = {st['name'] for d in it['days'] for st in d['stops'] if st.get('via')}
                for di, d in enumerate(r['days']):
                    for w in d['rows']:
                        if w['type'] == 'dep' and w.get('to') and w['to'] not in via and MOUNT.search(w['to']):
                            if re.match(r'(打车|包车)', w.get('how') or ''): bad.append((rid, di + 1, w['to'], w['how']))
                            if (w.get('how') or '').startswith('火车或缆车'): chg.append((rid, di + 1, w['to'], w['how']))
            check('G4.6 瑞士/奥地利：没写交通的山、缆车、观景台，不再自动配“打车/包车”（改成“火车或缆车”的 %d 处）' % len(chg), not bad and len(chg) >= 1, bad[:4])
            env.note('G4.6 改成“火车或缆车”的：' + '；'.join('%s 第%d天 %s' % (a, b, c_) for a, b, c_, _ in chg))
            h = read_trip(next(k for k, v in IT.items() if v['dest'] == 'japan'))
            check('G4.7 国外线页面上到达日第一行写“抵达 → 住处”，不是“出发 → 住处”', re.search(r'<p class="m">抵达 → 住处</p>', h) is not None, '')

    # ———————————————————— G5 ————————————————————
    if want('G5'):
        with guard('G5-cmp'):
            FAV = []
            c0, pg0 = ctx(br, p, {})
            exps = {}
            for rid, lab in (('xa3', '西安 3 天'), ('ash2', '赤峰 2 天'), ('tk4', '东京 4 天')):
                goto(env, pg0, '/trip/%s/' % rid, 300)
                days = pg0.evaluate(DAYS_JS)
                st0 = pg0.evaluate("({n:document.querySelectorAll('.day').length,price:document.querySelector('.glance .price').innerText.trim(),start:document.querySelector('.dpk').value,bk:document.querySelectorAll('.tl .r .bkn').length,title:document.querySelector('.hero h1').innerText.trim()})")
                st0['w'] = max(int(d['w']) for d in days); st0['d'] = max(int(d['d']) for d in days); exps[rid] = st0
                FAV.append({'id': rid, 'label': lab, 'title': st0['title'], 'n': st0['n'], 'sd': st0['start']})
            c0.close()
            R = load_routes()
            c, pg = ctx(br, p, {'zouni_fav': json.dumps(FAV, ensure_ascii=False)}); goto(env, pg, '/')
            pg.click('.minebtn'); pg.wait_for_selector('.pk .mrc')
            btn = lambda: pg.evaluate("(()=>{const b=document.querySelector('.mcmp');return {on:b.classList.contains('on'),aria:b.getAttribute('aria-disabled'),txt:b.textContent}})()")
            b0 = btn(); check('G5.1 对比按钮：没选时是灰的（aria-disabled=true）', b0['aria'] == 'true' and not b0['on'], b0)
            pg.locator('.mrc').nth(0).click(); b1 = btn(); check('G5.1 选 1 条还是灰的', b1['aria'] == 'true' and not b1['on'], b1)
            pg.locator('.mrc').nth(1).click(); b2 = btn(); check('G5.1 选满 2 条才亮（on，aria-disabled=false）', b2['aria'] == 'false' and b2['on'], b2)
            pg.locator('.mrc').nth(2).click(); sel = pg.evaluate("[...document.querySelectorAll('.mrc.on')].map(b=>b.dataset.id)")
            check('G5.1 再选第 3 条：最早选的那条换下去，始终只有 2 条亮（%s）' % sel, sorted(sel) == ['ash2', 'tk4'], sel)
            for i in range(3):
                if pg.locator('.mrc').nth(i).get_attribute('aria-pressed') == 'true': pg.locator('.mrc').nth(i).click()
            pg.locator('.mrc').nth(0).click(); pg.locator('.mrc').nth(2).click()      # 西安 + 东京
            pg.click('.mcmp'); pg.wait_for_selector('.cmpt', timeout=8000); pg.wait_for_timeout(200)
            tb = pg.evaluate("[...document.querySelectorAll('.cmpt tbody tr')].map(tr=>[...tr.children].map(c=>c.innerText.trim()))")
            hd = pg.evaluate("[...document.querySelectorAll('.cmpt thead th')].map(c=>c.innerText.trim())")
            check('G5.2 对比表：表头是两条线路名、7 行（天数/出发日期/人均价/最长一天开车/走路/最高海拔/要预约）', hd[1:] == ['西安 3 天', '东京 4 天'] and [r[0] for r in tb] == ['天数', '出发日期', '人均价', '最长一天开车', '最长一天走路', '最高海拔', '要预约'], (hd, [r[0] for r in tb]))
            row = {r[0]: r[1:] for r in tb}
            ids = ['xa3', 'tk4']

            def hm(m): return '基本没有' if m < 10 else ('约 %d 分钟' % (jround(m / 5) * 5 or 5)) if m < 60 else '约 %s 小时' % ('%g' % (jround(m / 6) / 10))

            def dts(iso): d = datetime.date.fromisoformat(iso); return '建议 %d/%d 周%s' % (d.month, d.day, WD[int(d.strftime('%w'))])
            elev = lambda rid: R[rid].get('maxElev') or max([(d_.get('elev') or 0) for d_ in R[rid]['days']] + [0])
            exp_rows = {'天数': ['%d 天' % exps[i]['n'] for i in ids], '出发日期': [dts(exps[i]['start']) for i in ids], '人均价': [exps[i]['price'] for i in ids],
                        '最长一天开车': [hm(exps[i]['d']) for i in ids], '最长一天走路': [hm(exps[i]['w']) for i in ids],
                        '最高海拔': [('{:,} 米'.format(elev(i)) if elev(i) >= 1500 else '不到 1,500 米') for i in ids], '要预约': [('%d 处要预约' % exps[i]['bk']) if exps[i]['bk'] else '没有' for i in ids]}
            diff = {k: (row.get(k), v) for k, v in exp_rows.items() if row.get(k) != v}
            check('G5.2 每个格子的数 = 各自线路页上的（天数、日期、价格、开车、走路、海拔、预约数）', not diff, diff)
            if env.shots: pg.screenshot(path=os.path.join(env.shots, 'G5_compare.png'))
            pg.click('.cmpb'); pg.wait_for_timeout(200)
            check('G5.3 “回到我的行程”能回到列表，选中状态还在', pg.locator('.mrc').count() == 3 and pg.locator('.mrc.on').count() == 2 and pg.locator('.cmpt').count() == 0, (pg.locator('.mrc').count(), pg.locator('.mrc.on').count()))
            c.close()
        with guard('G5-qr'):
            import base64
            import cv2
            import numpy as np
            c, pg = ctx(br, p, {'zouni_adj_xa3': json.dumps({'0': {'1': 30, '3': -15}}), 'zouni_slow_xa3': '1', 'zouni_st_xa3': json.dumps({'0': '10:00', '1': '08:30'}), 'zouni_n_xa3': '4'})
            pg.add_init_script("(function(){window.__ft=[];var o=CanvasRenderingContext2D.prototype.fillText;CanvasRenderingContext2D.prototype.fillText=function(t){window.__ft.push(String(t));return o.apply(this,arguments)}})();")
            goto(env, pg, '/trip/xa3/', 600)
            pg.click('.hero .share'); pg.wait_for_selector('.pk [data-a="shot"]', timeout=8000); pg.click('.pk [data-a="shot"]')
            pg.wait_for_selector('.shotv img', timeout=15000); pg.wait_for_timeout(300)
            src = pg.evaluate("document.querySelector('.shotv img').src")
            im = cv2.imdecode(np.frombuffer(base64.b64decode(src.split(',', 1)[1]), np.uint8), cv2.IMREAD_COLOR)
            det = cv2.QRCodeDetector(); val, pts, _ = det.detectAndDecode(im)
            page_url = env.B + '/trip/xa3/'
            check('G5.4 分享图二维码解码出来的 = 线路页网址（不带修改状态）：%s' % val, val == page_url, (val, page_url))
            ft = pg.evaluate("window.__ft")
            foot = next((t for t in ft if t.startswith('走你 · ')), None)
            check('G5.4 底部网址文字和二维码一致（%s ↔ %s）' % (foot, val), foot is not None and val.split('://', 1)[-1] == foot[len('走你 · '):], (foot, val))
            check('G5.4 二维码里没有“#”修改状态（解码长度 %d ≤ 60）' % len(val or ''), '#' not in (val or '#') and len(val or '#' * 99) <= 60, val)
            if env.shots:
                with open(os.path.join(env.shots, 'G5_share.png'), 'wb') as f_: f_.write(base64.b64decode(src.split(',', 1)[1]))
            c.close()
        with guard('G5-dedupe'):
            for rid, name in (('xw71a', '横滨'), ('tk4', '东京')):
                c, pg = ctx(br, p, {}); goto(env, pg, '/trip/%s/' % rid, 300)
                pg.click('.todoall'); pg.wait_for_selector('.tv.todo .tdl'); pg.wait_for_timeout(200)
                groups = pg.evaluate("(()=>{const o={};let g='';for(const e of document.querySelectorAll('.tv.todo h3, .tv.todo .tdl li')){if(e.tagName==='H3'){g=e.textContent;o[g]=[]}else o[g].push(e.innerText.split('\\n')[0].trim())}return o})()")
                stays = groups.get('住宿', []); prep = groups.get('要准备的', [])
                stay_names = pg.evaluate("[...document.querySelectorAll('.day')].filter((s,i,a)=>i<a.length-1).map(s=>{const m=s.querySelector('.r.stay .m');return m?m.textContent.replace(/^\\s*住\\s*·\\s*/,'').split(/\\s*·\\s*/)[0].trim():''})")
                merged = [x for i, x in enumerate(stay_names) if x and (i == 0 or stay_names[i - 1] != x)]
                check('G5.5 %s：清单里的住宿条数 %d = 连着住的同一个地方并成一条后的 %d（%s）' % (rid, len(stays), len(merged), merged), len(stays) == len(merged), (stays, merged))
                check('G5.5 %s：“要准备的”里同一句话只出现一次（%d 条）' % (rid, len(prep)), len(prep) == len(set(prep)), prep)
                if name == '横滨':
                    hb = [s for s in stays if '横滨' in s]; check('G5.5 xw71a：横滨只列一次，写“连住 2 晚”（%s）' % hb, len(hb) == 1 and '连住 2 晚' in hb[0], hb)
                cnt = pg.evaluate("document.querySelector('.tvd').innerText"); tot = sum(len(v) for k, v in groups.items() if k != '要留意的')      # 2026-10-18：弹层末尾多了一组“要留意的”（页内放不下的提示，不能勾，不算进“已办 0/N”）
                check('G5.5 %s：顶上“已办 0/N”的 N = 清单总条数 %d（%s）' % (rid, tot, cnt), ('0/%d' % tot) in cnt, cnt)
                c.close()
        with guard('G5-chips'):
            c, pg = ctx(br, p, {}); goto(env, pg, '/long/', 300)
            for mon in ('12', '10', '3'):
                pg.click('.lchips[data-k="m"] button[data-m="%s"]' % mon); pg.wait_for_timeout(250)
                r = pg.evaluate("""()=>{const q=s=>[...document.querySelectorAll(s)].map(b=>{const r=b.getBoundingClientRect();return [Math.round(r.left),Math.round(r.right),b.textContent.trim()]});
                  const on=document.querySelector('.lchips[data-k="m"] button.on'),ch=document.querySelector('.lchips[data-k="m"]').getBoundingClientRect(),o=on.getBoundingClientRect();
                  return {fix:q('.lfix button'),vw:innerWidth,onIn:o.left>=ch.left-1&&o.right<=ch.right+1,on:on.textContent.trim(),ch:[Math.round(ch.left),Math.round(ch.right)]}}""")
                ok = all(0 <= a and b <= r['vw'] for a, b, _ in r['fix']) and r['onIn'] and [x[2] for x in r['fix']] == ['不限', '本月能出发']
                check('G5.6 选了 %s 月：“不限”“本月能出发”仍在屏幕里 %s，选中的月份在可见区里（%s）' % (mon, r['fix'], r['on']), ok, r)
            if env.shots: pg.screenshot(path=os.path.join(env.shots, 'G5_long_chips.png'))
            pg.click('.lfix button[data-m="now"]'); pg.wait_for_timeout(200)
            check('G5.6 点固定的“本月能出发”真起作用（它高亮）', pg.evaluate("document.querySelector('.lfix button[data-m=now]').classList.contains('on')"), '')
            c.close()

    # ———————————————————— G6 ————————————————————
    if want('G6'):
        with guard('G6-offline-map'):
            IPH = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
            c, pg = ctx(br, p, {}, user_agent=IPH); goto(env, pg, '/trip/xa3/', 300)
            check('G6.1 有网时路线图下没有“断网中”说明', pg.locator('figure.hmap .mapoff').count() == 0, '')
            c.set_offline(True); pg.wait_for_timeout(300)
            t = pg.locator('figure.hmap .mapoff')
            check('G6.1 断网后路线图下出现静态说明“断网中：路线图是示意图…要联网”', t.count() == 1 and '联网' in t.inner_text(), t.count())
            url0 = pg.url
            pg.evaluate("document.querySelector('a.ic.map').scrollIntoView()"); pg.locator('a.ic.map').first.click(force=True); pg.wait_for_timeout(300)
            check('G6.1 断网时点地图图标：提示“地图需要联网”，不跳走', pg.locator('.toast').count() == 1 and '地图需要联网' in pg.inner_text('.toast') and pg.url == url0, (pg.locator('.toast').count(), pg.url))
            c.set_offline(False); pg.wait_for_timeout(300)
            check('G6.1 恢复联网后说明消失', pg.locator('figure.hmap .mapoff').count() == 0, '')
            c.close()
            c, pg = ctx(br, p, {}); goto(env, pg, '/where/', 400)
            c.set_offline(True); pg.click('.mtog'); pg.wait_for_selector('.wmap svg', timeout=6000); pg.wait_for_timeout(1200)
            mn = pg.locator('.wmap .mapneed')
            check('G6.2 断网点“地图看”：底图没拿到，地图区写“地图需要联网”，不是空白', mn.count() == 1 and '地图需要联网' in (mn.text_content() or ''), mn.count())
            if env.shots: pg.screenshot(path=os.path.join(env.shots, 'G6_where_map_offline.png'))
            c.close()
        with guard('G6-precache'):
            DEV_SW = "try{localStorage.setItem('zouni_dev_sw','1')}catch(e){}"
            c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, service_workers='allow'); c.add_init_script(DEV_SW)
            pg = new_page(env, c); goto(env, pg, '/'); pg.wait_for_function("navigator.serviceWorker&&navigator.serviceWorker.controller", timeout=20000)
            goto(env, pg, '/trip/xa3/', 800)
            ll = pg.evaluate("[...document.querySelectorAll('.tl > .r[data-ll],.day')].map(e=>e.dataset.ll||e.dataset.sp||'').filter(Boolean)")
            cells = set()
            for t in ll:
                a, b = (float(x) for x in t.split(','))
                for i in (-1, 0, 1):
                    for j in (-1, 0, 1): cells.add('%d_%d' % (math.floor((a + 90) / 3) + i, math.floor((b + 180) / 3) + j))
            have = set(re.findall(r'"(\d+_\d+)"', open(os.path.join(env.site, 'assets', 'np', '_index.js'), encoding='utf-8').read()))
            want_cells = sorted(cells & have)
            pg.evaluate("caches.open('zouni-v3').then(c=>c.keys().then(ks=>Promise.all(ks.filter(k=>/assets\\/np/.test(k.url)).map(k=>c.delete(k)))))"); pg.wait_for_timeout(200)
            pg.click('.dock .fav'); pg.wait_for_function("document.querySelector('.fav').classList.contains('saved')", timeout=15000); pg.wait_for_timeout(2500)
            got = pg.evaluate("caches.open('zouni-v3').then(c=>c.keys()).then(ks=>ks.map(k=>new URL(k.url).pathname+new URL(k.url).search))")
            miss = [k for k in want_cells if '/assets/np/%s.js' % k not in got]
            check('G6.3 “收进行程”一并存了这条线所在 3° 格及相邻格的候选分片（需要 %s，缺 %s）' % (want_cells, miss), len(want_cells) >= 1 and not miss, miss)
            check('G6.3 也存了模型、分片索引', any(x.startswith('/assets/np_model.js') for x in got) and '/assets/np/_index.js' in got, [x for x in got if 'np' in x][:5])
            c.set_offline(True)
            pg.goto(env.B + '/trip/xa3/', wait_until='load'); pg.wait_for_timeout(1000)
            small = ''; okd = None
            for di in (2, 3, 1):      # 第 1 天排满了（回住处后 22:10），找一个“加一个”能点的
                for ai in (0, 1, 2):
                    loc = pg.locator('#d%d .adj' % di)
                    if loc.count() <= ai: continue
                    loc.nth(ai).click(); pg.wait_for_selector('.pk'); pg.wait_for_timeout(200)
                    ins = pg.locator('.pk [data-np="ins"]')
                    if ins.count() and ins.first.get_attribute('disabled') is None:
                        okd = (di, ai); small = pg.locator('.pk [data-np="ins"] small').first.inner_text() if pg.locator('.pk [data-np="ins"] small').count() else ''; break
                    pg.locator('.pk .pk-x').click(); pg.wait_for_timeout(150)
                if okd: break
            check('G6.3 断网后“在这之后加一个”入口不写“没网”（候选数据在手机里；第 %s 天第 %s 个）：%s' % (okd and okd[0], okd and okd[1], small[:30]), okd is not None and '没网' not in small, small)
            if okd:
                pg.locator('.pk [data-np="ins"]').first.click(force=True); pg.wait_for_timeout(2500)
                n_c = pg.locator('.pk .npc').count(); txt = pg.inner_text('.pk') if pg.locator('.pk').count() else ''
                check('G6.3 断网点开能列出候选（%d 个），不是“没网”' % n_c, n_c > 0 and '没网' not in txt, txt[:80])
            c.close()
        with guard('G6-fonts'):
            c, pg = ctx(br, p, {}); reqs = []
            pg.on('requestfinished', lambda r: reqs.append(r.url) if r.url.endswith('.woff2') else None)
            goto(env, pg, '/', 1500)
            home_css = pg.evaluate("[...document.styleSheets].some(s=>/home\\.css/.test(s.href||''))")
            pre = pg.evaluate("[...document.querySelectorAll('link[rel=preload][as=font]')].map(l=>l.href.split('/').pop())")
            core = [u for u in reqs if '/home-' in u]
            sz = sum(os.path.getsize(os.path.join(env.site, 'assets', 'fonts', u.rsplit('/', 1)[1])) for u in reqs)
            check('G6.4 首页接了专用小字体（home.css），而且没有 preload（preload 会和 serif.css、site.js 抢带宽，Slow 3G 脚本就绪 5.0s→9.4s）：%s' % pre, home_css and not pre, (home_css, pre))
            check('G6.4 首页打开：字体请求 %d 个共 %d KB（原来 45 个 2,784KB），其中小字体 %d 个' % (len(reqs), sz // 1024, len(core)), len(core) >= 2 and len(reqs) <= 12 and sz <= 600 * 1024, (len(reqs), sz // 1024))
            M = "[...document.querySelectorAll('main *')].filter(e=>[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())&&e.getClientRects().length).slice(0,80).map(e=>{const r=e.getBoundingClientRect();return [Math.round(r.width),Math.round(r.height)]})"
            m1 = pg.evaluate(M); c.close()
            c, pg = ctx(br, p, {}); pg.route(re.compile(r'.*home.*\.(css|woff2)'), lambda r: r.abort()); goto(env, pg, '/', 2500)
            m2 = pg.evaluate(M)
            dif = [(i, a, b) for i, (a, b) in enumerate(zip(m1, m2)) if abs(a[0] - b[0]) > 1 or abs(a[1] - b[1]) > 1]
            check('G6.4 有没有小字体，首页 %d 个元素的宽高一致（±1px）：字形同源，版面不动' % len(m1), len(m1) >= 20 and not dif, dif[:4])
            c.close()
    br.close()
env.finish('第二批用户反馈')
