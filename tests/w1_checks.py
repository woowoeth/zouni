#!/usr/bin/env python3
"""第 1 波（2026-10-20，“数据与逻辑真实性”）新增的闸。每道闸 = 一个纯函数 check_xxx(输入) → 问题列表 + 一个反向自检（往输入里注入那个缺陷，闸必须红；
好稿必须不红）。`python3 tests/w1_checks.py [站目录]`：不给站目录只跑数据类；`--selftest` 只跑反向自检；data_checks.py 第 37 项每次都会跑自检 + 正式检查。

  S1 住处点：每天的“住”标记（data-ep）离次日出发点（data-sp）≤25 公里；并且离“当晚住的那座城”的中心 ≤40 公里（和 sp 无关的第二把尺，防止两头一起错）
  S2 路上时间：正文写“行车约 N 小时 / 约 N 公里”，页头 data-drv（路上分钟）不能比它少一半以上
  S3 同一路段：不同线路里“自驾 / 包车”的同一对站点（0.1° 格点），时间相差 ≥40% 且 ≥30 分钟
  S4 气温：页面每天的 data-clim（往年月均）和同一城市的 ERA5 月均（data/climate_era5.json）差 ≤6℃；没有 ERA5 的城市只统计数量，不判定
  S5 餐食：国内线每顿饭的菜如果只出自别的省（且不是这座城的招牌菜），红；任何线路都不得把甜点 / 配汤当一顿饭
  S6 季节：有“能走季节”的线路页必须带 .swarn（data-ok 与 trips.json 一致）；冬季线（能走季节整个落在窗口里）里的极夜 / 流冰 / 雪胎句子必须包进 .sw；“N 月上旬”句子必须包进 .mw
  S7 酒店卡：只有档位词没有酒店名的卡（div.stays.gen）里不得出现地图 / 点评 / 小红书 / YouTube 图标；住山顶的天不得推荐城里的三家
  S8 首页推荐标签：有一天走路 >150 分钟的线路，首页卡片标签必须含“走路多”（带老人孩子才不会推荐、不会写“没有长爬坡和台阶”）
  S10 “相传”后面紧跟传记 / 史载 / 据…简介 / 学界 / 一般认为
  S11 “回住处 N 公里”与最后一站 → 住处点的直线距离对得上
  S9 机场 / 车站用时：国外线首尾日写了 air_min 的，必须在 5–180 之间；用模板值（没写 air_min）的线数只统计、写进报告
"""
import copy, glob, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def ll(s):
    try: a, b = (s or '').split(','); return (float(a), float(b))
    except Exception: return None


# ———————————————— 页面解析（只认 section.day 的属性和 lead）
SEC = re.compile(r'<section class="day"([^>]*)>(.*?)(?=<section class="day"|<div class="addday|</article>)', re.S)


def attr(a, k):
    m = re.search(r'\b' + k + r'="([^"]*)"', a); return m.group(1) if m else None


def page_days(html):
    out = []
    for m in SEC.finditer(html):
        a, body = m.group(1), m.group(2)
        lead = re.search(r'<p class="lead"[^>]*>(.*?)</p>', body, re.S)
        clim = re.search(r"data-clim='([^']*)'", body)
        out.append(dict(city=attr(a, 'data-city'), stay=attr(a, 'data-stay'), sp=ll(attr(a, 'data-sp')), ep=ll(attr(a, 'data-ep')), drv=int(attr(a, 'data-drv') or 0) if attr(a, 'data-drv') is not None else None,
                        lead=re.sub(r'<[^>]+>', '', lead.group(1)) if lead else '', clim=clim.group(1) if clim else ''))
    return out


def load_pages(site):
    return {os.path.basename(os.path.dirname(f)): open(f, encoding='utf-8').read() for f in sorted(glob.glob(os.path.join(site, 'trip', '*', 'index.html')))}


# ———————————————— S1 住处点
GENERIC = re.compile(r'(附近|市区|县城|老城|古城|市中心|城里|边上|一带|营地|客栈|民宿|县|市|镇)$')


def check_stay(pages_days, geo, lg=None):
    """pages_days: {rid: [day dict]}；geo: pois.json。返回 [(rid, 第几天, 说明)]"""
    bad = []
    for rid, D in pages_days.items():
        for i in range(len(D) - 1):
            ep, sp = D[i]['ep'], D[i + 1]['sp']
            if not ep: continue
            if sp and km(ep, sp) > 25: bad.append((rid, i + 1, f'住处点离次日出发点 {km(ep, sp):.0f} 公里'))
            if lg is not None and not lg.get(rid): continue      # 第二把尺只对长线：data-stay 在长线里才是“当晚住的城”，别的线它是当天所在城
            nm = (D[i]['stay'] or '').strip(); core = GENERIC.sub('', nm).strip(); core = core if len(core) >= 2 else nm
            ref = None
            for key in (nm + '|' + nm, core + '|' + core, (D[i + 1]['city'] or '') + '|' + (D[i + 1]['city'] or '')):
                g = geo.get(key)
                if g and g.get('lat') is not None:
                    ref = (g['lat'], g['lng'])
                    if key.split('|')[0] in (core, nm): break
            if ref and km(ep, ref) > 40: bad.append((rid, i + 1, f'住处点离“{core or nm}”城中心 {km(ep, ref):.0f} 公里'))
    return bad


# ———————————————— S2 路上时间
H_RE = re.compile(r'(?:行车|开车|车程|自驾|驱车)[^，。；（）0-9]{0,4}约?\s*(\d+(?:\.\d+)?)\s*(?:个半)?\s*(小时|个半小时)')
HB_RE = re.compile(r'(?:行车|开车|车程|自驾|驱车)[^，。；0-9]{0,4}约\s*(\d+)\s*个半小时')
KM_RE = re.compile(r'(?:全天|全程|今天|共|约)\s*约?\s*(\d{2,4})\s*公里')


def check_drive(pages_days):
    bad = []
    for rid, D in pages_days.items():
        for i, d in enumerate(D):
            if d['drv'] is None: continue
            t = d['lead']; hrs = None
            mb = HB_RE.search(t)
            if mb: hrs = int(mb.group(1)) + .5
            else:
                mh = H_RE.search(t)
                if mh: hrs = float(mh.group(1))
            mk = KM_RE.search(t); k = int(mk.group(1)) if mk else None
            if hrs is not None and hrs >= 1.5 and d['drv'] < hrs * 60 * .6: bad.append((rid, i + 1, f'正文写行车约 {hrs:g} 小时，页头路上只有 {d["drv"]} 分钟'))
            elif k is not None and k >= 100 and d['drv'] < k / 90 * 60 * .6: bad.append((rid, i + 1, f'正文写约 {k} 公里，页头路上只有 {d["drv"]} 分钟（按 90 公里/小时也要 {k / 90 * 60:.0f} 分钟）'))
    return bad


# ———————————————— S3 同一路段
def vm(s):
    h = re.search(r'(\d+) 小时', s or ''); m = re.search(r'(\d+) 分', s or '')
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def check_segments(IT, geo):
    seg = {}
    for rid, it in IT.items():
        for di, d in enumerate(it['days']):
            c = d.get('city', it['city']); prev = None
            for s in d['stops']:
                q = s.get('q') or s['name']; g = geo.get(c + '|' + q)
                cc = (round(g['lat'] * 10) / 10, round(g['lng'] * 10) / 10) if g and g.get('lat') is not None else None; via = s.get('via') or ''
                if prev and cc and prev != cc and re.search('自驾|包车|开车', via) and vm(via) >= 40: seg.setdefault((prev, cc), []).append((rid, di + 1, vm(via), s['name']))
                prev = cc
    bad = []
    for k, v in seg.items():
        if len({x[0] for x in v}) < 2: continue
        ts = [x[2] for x in v]
        if max(ts) >= 1.4 * min(ts) and max(ts) - min(ts) >= 30: bad.append((k, v))
    return bad


# ———————————————— S4 气温
def era_tab():
    p = os.path.join(ROOT, 'data/climate_era5.json')
    if not os.path.exists(p): return {}
    d = json.load(open(p, encoding='utf-8'))
    return {c: d['cells'][k] for c, k in d['cities'].items() if k in d['cells']}


def check_climate(pages_days, era, tol=6):
    bad = []; covered = uncovered = 0
    for rid, D in pages_days.items():
        for i, d in enumerate(D):
            c = d['city']
            if not d['clim'] or not c: continue
            if c not in era: uncovered += 1; continue
            covered += 1
            try: cl = json.loads(d['clim'].replace('&quot;', '"'))
            except Exception: continue
            for m, v in cl.items():
                e = era[c].get(m)
                if e and (abs(v[0] - e[0]) > tol or abs(v[1] - e[1]) > tol): bad.append((rid, i + 1, f'{c} {m} 月 页面 {v[0]}/{v[1]}℃，ERA5 {e[0]}/{e[1]}℃')); break
    return bad, covered, uncovered


# ———————————————— S5 餐食
NOTMEAL_W = ('铜锣烧', '鲷鱼烧', '今川烧', '大福', '团子', '味噌汤', '杭白菊', '石斛')
import geo_prov as _gp
NATIONWIDE = _gp.NATIONWIDE
DN = lambda c: re.sub(r'[（(].*$', '', c.split('、')[0]).strip()


def check_meals(R, IT, DM, prov_of, dishprov, cityfood):
    bad = []
    for rid, r in R.items():
        it = IT.get(rid)
        if not it: continue
        dom = it['dest'] in DM and it['dest'] not in ('hongkong', 'macau', 'taiwan')
        for di, d in enumerate(r['days']):
            pv = prov_of(d.get('city')) if dom else None
            cf = {DN(x) for x in (cityfood.get(d.get('city')) or [])}      # 只认“今天所在城市”自己的招牌菜；路线出发城市的不算（dbdh24 在曲阜吃北京涮羊肉就是这么漏掉的）
            for w in d['rows']:
                if w['type'] != 'eat' or not w.get('dish'): continue
                h = DN(w['dish'])
                if any(x in h for x in NOTMEAL_W) or h in ('葡萄', '哈密瓜', '西瓜', '水果'): bad.append((rid, di + 1, f'{d.get("city")} {w["slot"]}“{w["dish"]}”不是一顿饭')); continue
                s = None if h in NATIONWIDE else dishprov.get(h)
                if pv and s and pv not in s and h not in cf and not (w.get('place') and w['place'] != '附近' and False):
                    bad.append((rid, di + 1, f'{d.get("city")}（{pv}）{w["slot"]}“{w["dish"]}”只出自 {"/".join(sorted(s)[:3])}'))
    return bad


# ———————————————— S6 季节（静态：构建产物里有没有包好）
def _days_of(a, b):
    import datetime
    f = lambda x: datetime.date(2025, int(x[:2]), int(x[3:])).timetuple().tm_yday
    x, y = f(a), f(b); return set(range(x, y + 1)) if x <= y else set(range(x, 366)) | set(range(1, y + 1))


SW_WIN = {'polar': ('11-20', '01-20'), 'ice': ('01-15', '03-25'), 'winter': ('11-01', '04-20')}
SW_RE = {'polar': re.compile(r'极夜|太阳不升|头灯|星星灯|蓝调|蓝紫色'), 'ice': re.compile(r'流冰|冰瀑'), 'winter': re.compile(r'雪胎|冬季轮胎|冰爪|防滑底|结冰|积雪|冬季封闭|雪铲|雪地|黑冰|冬季风|冬季自驾|冬季驾驶|冰面|雪盖|封路')}
MW_RE = re.compile(r'(\d{1,2})[\s\u00a0]月(上旬|中旬|下旬|初|底|中)')


def check_season(pages, trips):
    bad = []
    for rid, h in pages.items():
        t = trips.get(rid)
        if not t: continue
        ok = None if t.get('anytime') else (t.get('season') or {}).get('ok')
        m = re.search(r'<p class="swarn"[^>]*data-ok="([^"]*)"', h)
        if ok and len(ok) == 2:
            if not m or m.group(1) != ','.join(ok): bad.append((rid, 0, f'缺 .swarn 或 data-ok 不一致（应为 {ok}）'))
        elif m: bad.append((rid, 0, '没有能走季节的线路不该有 .swarn'))
        kinds = [k for k, (a, b) in SW_WIN.items() if ok and len(ok) == 2 and _days_of(*ok) <= _days_of(a, b)]
        # 去掉 script / style / 已包好的 span 之后，句子级别扫：句子里有关键词又没被 span.sw 包住 = 缺
        body = re.sub(r'<script.*?</script>|<style.*?</style>|<svg.*?</svg>|<head>.*?</head>', '', h, flags=re.S)
        for blk in re.findall(r'<p class="lead"[^>]*>.*?</p>|<aside class="story">.*?</aside>|<li class="tip[^"]*"><span>.*?</span>', body, flags=re.S):
            for sen in re.split(r'(?<=。)', blk):
                inner_wrapped = re.fullmatch(r'.*?<span class="[^"]*\b(sw|mw)\b[^"]*"[^>]*>.*', sen, flags=re.S)
                plain = re.sub(r'<[^>]+>', '', sen)
                if MW_RE.search(plain) and 'class="mw' not in sen and 'mw sw' not in sen and not re.search(r'<span class="[^"]*mw', sen): bad.append((rid, 0, '月份句子没包 .mw：' + MW_RE.search(plain).group(0)))
                for k in kinds:
                    if SW_RE[k].search(plain) and not re.search(r'<span class="[^"]*\bsw\b', sen) and '<b>' not in sen: bad.append((rid, 0, f'冬季句子没包 .sw（{k}）：' + SW_RE[k].search(plain).group(0)))
    return bad


# ———————————————— S7 酒店卡
def check_stay_cards(pages):
    bad = []
    for rid, h in pages.items():
        for m in re.finditer(r'<div class="stays gen"[^>]*>(.*?)</div></div>', h, flags=re.S):
            if re.search(r'class="icg"', m.group(1)): bad.append((rid, 0, '只有档位词的住宿卡里出现地图 / 点评 / 小红书 / YouTube 图标'))
        for m in re.finditer(r'<div class="stays[^"]*" data-area="([^"]*)">(.*?)</ul>', h, flags=re.S):
            if re.search(r'山顶|山上|峰顶', m.group(1)) and re.search(r'class="tg">[^<]*(酒店|宾馆)', m.group(2)) and 'class="stays gen"' not in m.group(0)[:30]:
                if not re.search(r'神憩|天街', m.group(2)): bad.append((rid, 0, f'住「{m.group(1)}」却推荐了别处的酒店'))
    return bad


# ———————————————— S8 首页标签
LOAD_SH = {'pk': .5, 'st': .6, 'tn': .5, 'lk': .4, 'bc': .4, 'tp': .4, 'nt': .4, 'sg': .3, 'ms': .25, 'cl': .3, 'fn': .3}      # 同 build_site.LOAD_SH / site.js ZLSH


def _zmin(t):
    h = re.search(r'(\d+)\s*小时', t or ''); m = re.search(r'(\d+)\s*分', t or '')
    return ((int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)) if (h or m) else 0


def day_walk(sec):
    """一天的走路分钟（build_site.day_load_html 的走路那一半：步行行 + 景点停留 × 步行占比）"""
    walk = 0.0
    for m in re.finditer(r'<li class="r (\w+)"([^>]*)>(.*?)</li>', sec, re.S):
        ty, at, body = m.groups()
        sm = re.search(r'<p class=s>(.*?)</p>', body, re.S); sub = sm.group(1) if sm else ''
        if ty == 'dep':
            tx = re.sub(r'<[^>]+>', '', sub); tx = re.sub(r'^回住处\s*·\s*', '', tx).split('·')[0].strip()
            if tx.startswith('步行') and not re.search(r'→\s*回程\s*$', re.sub(r'<[^>]+>', '', (re.search(r'<p class="m">(.*?)</p>', body, re.S) or [0, ''])[1])): walk += _zmin(tx)
        elif ty in ('see', 'fun') and sm:
            top = re.sub(r'<(span|em|a|b|button)\b[^>]*>.*?</\1>', '', sub, flags=re.S); top = re.sub(r'<[^>]+>', '', top)
            if re.search(r'\d+ (小时|分)', top):
                seg = next((x for x in re.split(r'<[^>]+>', re.sub(r'<(span|em|a|b|button)\b[^>]*>.*?</\1>', '<>', sub, flags=re.S)) if re.search(r'\d+ (小时|分)', x)), '')
                t_ = re.search(r'data-ty="(\w+)"', at); walk += _zmin(seg) * LOAD_SH.get(t_.group(1) if t_ else '', .3)
    return int(walk + .5)


def home_tags(site):
    """{线路: 标签列表}：首页 HTML 里的 data-h + data-tg，和 home-a/b.js 里每条数组的第 24 项（用 | 连起来的标签）"""
    out = {}
    txt = open(os.path.join(site, 'index.html'), encoding='utf-8').read()
    for m in re.finditer(r'data-h="/trip/([^/"]+)/"[^>]*?data-tg="([^"]*)"', txt): out[m.group(1)] = m.group(2).split('|')
    for f in ('home-a.js', 'home-b.js'):
        p = os.path.join(site, 'assets', f)
        if not os.path.exists(p): continue
        t = open(p, encoding='utf-8').read(); dec = json.JSONDecoder()
        for m in re.finditer(r'\["([a-z0-9]+)","', t):
            try: arr, _ = dec.raw_decode(t[m.start():])
            except Exception: continue
            if len(arr) > 23 and isinstance(arr[23], str): out[arr[0]] = arr[23].split('|')
    return out


def check_tags(tags, walks):
    """tags：{rid: [标签]}；walks：{rid: [每天走路分钟]}。有一天走路 >150 分钟（site.js 的“对老人孩子偏累”）→ 首页标签必须有“偏累”"""
    bad = []
    for rid, ws in walks.items():
        if any(w > 150 for w in ws) and rid in tags and '偏累' not in tags[rid]: bad.append((rid, 0, f'最长一天走路 {max(ws)} 分钟，首页标签 {tags[rid]} 没有“偏累”（带老人孩子会推荐）'))
    return bad


# ———————————————— S9 机场用时
def check_air(IT, ASIA):
    bad = []; template = []
    for rid, it in IT.items():
        if it['dest'] not in ASIA: continue
        for di in (0, len(it['days']) - 1):
            v = it['days'][di].get('air_min')
            if v is None: template.append((rid, di + 1))
            elif not (5 <= v <= 180): bad.append((rid, di + 1, f'air_min={v}'))
    return bad, template


# ———————————————— S10 “相传”用错
XC_RE = re.compile(r'相传(?:传记|史载|据载|据年谱|据[^，。；<]{0,8}(?:简介|介绍)|学界|一般认为|传统上)')


def check_xiangchuan(pages):
    """“相传”只给传说。后面紧跟“传记 / 史载 / 据…简介 / 学界 / 一般认为”的是“有记载但有争议”，不是传说（hxz1 莫高窟 / 玉门关 / 锁阳城、hlugq2 砖壁旧址）"""
    return [(rid, 0, XC_RE.search(re.sub(r'<[^>]+>', '', h)).group(0)) for rid, h in pages.items() if XC_RE.search(re.sub(r'<[^>]+>', '', h))]


# ———————————————— S11 “回住处 · … N 公里”和地图上的两个点对得上
BACK_RE = re.compile(r'回住处\s*·[^<]*?·\s*(\d+) 公里')


S11_WAIVE = {('xo3d', 3): '数据自相矛盾：第 3 天 stay 写安卡拉，第 4 天却从戈尔迪翁一带出发（stay_fix 判成住在戈尔迪翁附近，编译器按写明的安卡拉算了 100 公里）。拿不准住哪，写进 06 待办，不硬改'}      # 人工确认过的例外，写明原因


def check_back_dist(pages):
    """每天“回住处 · 自驾约 N · M 公里”的 M 不能比“它前一个有坐标的站 → 住处点（data-ep）”的直线距离大太多（山路绕湖的路程系数可到 2.4：≤2.5 倍再加 15 公里）。
    第一版 move_leg 在站点没有坐标时拿城市中心当起点（旅顺 → 营口 256 公里）、晚饭后又从城市中心重算（五台山 1 公里 → 34 公里），文字和地图上的点差 20 倍，S1 / S2 都看不出来"""
    bad = []
    for rid, h in pages.items():
        for di, m in enumerate(SEC.finditer(h)):
            a, body = m.group(1), m.group(2)
            ep = ll(attr(a, 'data-ep'))
            if not ep: continue
            last = None
            for rm in re.finditer(r'<li class="r ([\w ]*?)"([^>]*)>(.*?)</li>', body, flags=re.S):
                cls, at, inner = rm.groups(); pt = ll(attr(at, 'data-ll'))
                if pt and re.match(r'(see|fun|eat)', cls): last = pt; continue
                bm = BACK_RE.search(re.sub(r'<[^>]+>', ' ', inner))
                if bm and last and (rid, di + 1) not in S11_WAIVE and int(bm.group(1)) > 2.5 * km(last, ep) + 15: bad.append((rid, di + 1, f'“回住处 {bm.group(1)} 公里”，前一个站到住处点直线只有 {km(last, ep):.0f} 公里'))
    return bad


# ———————————————— 加载 + 主流程
def load_all(site=None):
    geo = json.load(open(os.path.join(ROOT, 'data/geo/pois.json'), encoding='utf-8'))
    IT = json.load(open(os.path.join(ROOT, 'data/itineraries.json'), encoding='utf-8'))['itineraries']
    trips = {t['id']: t for t in json.load(open(os.path.join(ROOT, 'data/catalog/trips.json'), encoding='utf-8'))['trips']}
    dests = json.load(open(os.path.join(ROOT, 'data/destinations.json'), encoding='utf-8'))
    DM = {d['id'] for d in dests['domestic']}
    ASIA = {d['id'] for k in ('asia', 'world') for d in dests[k]} | {'taiwan'}
    R = None
    rp = os.path.join(ROOT, 'build/routes.js')
    if os.path.exists(rp): R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', open(rp, encoding='utf-8').read()).group(1))
    pages = load_pages(site) if site else {}
    return dict(geo=geo, IT=IT, trips=trips, DM=DM, ASIA=ASIA, R=R, pages=pages)


def run(site=None):
    import geo_prov
    X = load_all(site); out = []; info = []
    pd = {rid: page_days(h) for rid, h in X['pages'].items()}
    out.append(('S3 同一路段在不同线路里时间不一致（≥40% 且 ≥30 分钟）', [f'{k}: {v}' for k, v in check_segments(X['IT'], X['geo'])]))
    b9, tpl = check_air(X['IT'], X['ASIA']); out.append(('S9 air_min 超出 5–180 分钟', [str(x) for x in b9])); info.append(f'S9 机场用时仍是模板值的国外线首尾日：{len(tpl)} 个（{len({x[0] for x in tpl})} 条线）')
    if X['R']:
        dp = geo_prov.dish_provs(); cf = json.load(open(os.path.join(ROOT, 'data/catalog/city_food.json'), encoding='utf-8'))
        out.append(('S5 餐食只出自别的省 / 甜点当正餐', [str(x) for x in check_meals(X['R'], X['IT'], X['DM'], geo_prov.prov_of, dp, cf)]))
    if site:
        out.append(('S1 住处点离次日出发点 >25 公里 / 离当晚住的城 >40 公里', [str(x) for x in check_stay(pd, X['geo'], {rid: 'data-lg="1"' in h for rid, h in X['pages'].items()})]))
        out.append(('S2 正文写的行车时间 / 公里数与页头“路上”对不上', [str(x) for x in check_drive(pd)]))
        b4, cov, unc = check_climate(pd, era_tab()); out.append(('S4 气温表与同城 ERA5 差 >6℃', [str(x) for x in b4]))
        info.append(f'S4 ERA5 覆盖：{cov} 个“线路-天”有同城 ERA5 并已核对，{unc} 个没有 ERA5（沿用目的地级的表，额度恢复后跑 tools/fix_climate.py 补）')
        out.append(('S6 季节措辞没跟日期（缺 .swarn / .sw / .mw）', [str(x) for x in check_season(X['pages'], X['trips'])]))
        out.append(('S7 住宿卡（无酒店名的卡不放图标 / 山顶住宿不推荐城里的酒店）', [str(x) for x in check_stay_cards(X['pages'])]))
        walks = {rid: [day_walk(m.group(0)) for m in re.finditer(r'<section class="day".*?</section>', h, re.S)] for rid, h in X['pages'].items()}
        out.append(('S10 “相传”后面紧跟出处词（有记载的事被写成传说）', [str(x) for x in check_xiangchuan(X['pages'])]))
        out.append(('S11 “回住处 N 公里”比最后一站到住处点的直线距离大太多（起点算错）', [str(x) for x in check_back_dist(X['pages'])]))
        out.append(('S8 走路超 2.5 小时的线路，首页标签没有“偏累”', [str(x) for x in check_tags(home_tags(site), walks)]))
    return [(t, v) for t, v in out], info


# ———————————————— 反向自检：往好稿里注入缺陷，闸必须红；好稿必须不红
def selftest():
    errs = []
    geo = {'甲|甲': {'lat': 30.0, 'lng': 100.0}, '乙|乙': {'lat': 31.0, 'lng': 101.0}}
    D = {'r': [dict(city='甲', stay='乙', sp=(30.0, 100.0), ep=(31.0, 101.0), drv=60, lead='', clim=''),
               dict(city='乙', stay='乙', sp=(31.0, 101.0), ep=(31.0, 101.0), drv=60, lead='', clim='')]}
    if check_stay(D, geo): errs.append('S1 好稿被判红：' + str(check_stay(D, geo)))
    D1 = copy.deepcopy(D); D1['r'][0]['ep'] = (30.5, 100.5); D1['r'][1]['sp'] = (30.5, 100.5)      # 两头一起错（sp 跟着 ep 走）：只有第二把尺（离当晚住的城中心）能抓到
    if not check_stay(D1, geo, {'r': True}): errs.append('S1 反向注入（ep 与 sp 一起偏离住的城 70 公里）没变红')
    D2 = copy.deepcopy(D); D2['r'][0]['ep'] = (30.0, 100.0)      # xl8a 的缺陷：住处点落在昨晚的城
    if not check_stay(D2, geo): errs.append('S1 反向注入（住处点退回昨晚的城）没变红')
    D3 = copy.deepcopy(D); D3['r'][1]['sp'] = (30.2, 100.0)
    if not check_stay(D3, geo): errs.append('S1 反向注入（次日出发点错位）没变红')
    ok = {'r': [dict(city='甲', stay='乙', sp=None, ep=None, drv=480, lead='今天行车约 8 小时，全程约 420 公里。', clim='')]}
    if check_drive(ok): errs.append('S2 好稿被判红')
    ok['r'][0]['drv'] = 10
    if not check_drive(ok): errs.append('S2 反向注入（路上只有 10 分钟）没变红')
    ok['r'][0]['lead'] = '今天全程约 330 公里。'; ok['r'][0]['drv'] = 40
    if not check_drive(ok): errs.append('S2 反向注入（只写公里数）没变红')
    IT = {'a': {'city': '甲', 'days': [{'stops': [{'name': 'P', 'via': '步行 5 分钟'}, {'name': 'Q', 'via': '自驾约 2 小时'}]}]},
          'b': {'city': '甲', 'days': [{'stops': [{'name': 'P', 'via': '步行 5 分钟'}, {'name': 'Q', 'via': '自驾约 2 小时'}]}]}}
    g2 = {'甲|P': {'lat': 30.0, 'lng': 100.0}, '甲|Q': {'lat': 31.0, 'lng': 101.0}}
    if check_segments(IT, g2): errs.append('S3 好稿被判红')
    IT['b']['days'][0]['stops'][1]['via'] = '自驾约 50 分钟'
    if not check_segments(IT, g2): errs.append('S3 反向注入（同一路段 2 小时 vs 50 分钟）没变红')
    era = {'乙': {'12': [-2, -7]}}
    pdc = {'r': [dict(city='乙', stay='', sp=None, ep=None, drv=0, lead='', clim='{"12": [-1, -6]}')]}
    if check_climate(pdc, era)[0]: errs.append('S4 好稿被判红')
    pdc['r'][0]['clim'] = '{"12": [5, 1]}'      # 特罗姆瑟 12 月写成 5/1（实际 -2/-7）
    if not check_climate(pdc, era)[0]: errs.append('S4 反向注入（偏暖 7℃）没变红')
    R = {'x': {'days': [{'city': '甲', 'rows': [{'type': 'eat', 'slot': '晚饭', 'dish': '卤煮火烧', 'place': '附近'}]}]}}
    ITm = {'x': {'dest': 'd1', 'city': '甲'}}
    if not check_meals(R, ITm, {'d1'}, lambda c: '福建', {'卤煮火烧': {'北京'}}, {}): errs.append('S5 反向注入（福建吃卤煮火烧）没变红')
    if check_meals(R, ITm, {'d1'}, lambda c: '北京', {'卤煮火烧': {'北京'}}, {}): errs.append('S5 好稿被判红')
    R['x']['days'][0]['rows'][0]['dish'] = '铜锣烧'
    if not check_meals(R, ITm, {'d1'}, lambda c: None, {}, {}): errs.append('S5 反向注入（铜锣烧当晚饭）没变红')
    trips = {'t': {'season': {'ok': ['11-25', '12-31']}}}
    good = '<p class="swarn" role="alert" hidden data-ok="11-25,12-31"></p><p class="lead"><span class="sw" data-sw="polar">这是极夜季节。</span><span class="sw" data-sw="winter">租雪胎。</span></p>'
    if check_season({'t': good}, trips): errs.append('S6 好稿被判红：' + str(check_season({'t': good}, trips)))
    if not check_season({'t': good.replace('<p class="swarn" role="alert" hidden data-ok="11-25,12-31"></p>', '')}, trips): errs.append('S6 反向注入（去掉红字行）没变红')
    if not check_season({'t': good.replace('<span class="sw" data-sw="winter">租雪胎。</span>', '租雪胎。')}, trips): errs.append('S6 反向注入（冬季句子不包 .sw）没变红')
    pm = '<p class="lead">9 月上旬雨季尾声。</p>'
    if not check_season({'t': pm}, {'t': {'season': {'ok': ['05-10', '10-10']}}}) or True:
        pass
    if not check_season({'t': '<p class="swarn" hidden data-ok="05-10,10-10"></p>' + pm}, {'t': {'season': {'ok': ['05-10', '10-10']}}}): errs.append('S6 反向注入（“9 月上旬”不包 .mw）没变红')
    if check_stay_cards({'t': '<div class="stays gen" data-area="x"><ul><li><b class="tg">四星</b></li></ul></div></div>'}): errs.append('S7 好稿被判红')
    if not check_stay_cards({'t': '<div class="stays gen" data-area="x"><ul><li><b class="tg">四星</b><span class="icg"><a></a></span></li></ul></div></div>'}): errs.append('S7 反向注入（档位卡带图标）没变红')
    if not check_stay_cards({'t': '<div class="stays" data-area="泰山顶"><ul><li><b class="tg">泰安泰山天外村希尔顿欢朋酒店</b></li></ul>'}): errs.append('S7 反向注入（山顶推荐山下酒店）没变红')
    if check_xiangchuan({'a': '<p>相传是玄奘讲经的阿育王寺，学界有此看法</p>'}): errs.append('S10 好稿被判红')
    if not check_xiangchuan({'a': '<p>相传传记记玄奘出玉门关</p>'}): errs.append('S10 反向注入（相传传记记…）没变红')
    _sec = '<section class="day" data-ep="31.0,101.0"><ol class="tl"><li class="r see" data-ll="30.9,101.0"><p class=s>x</p></li><li class="r dep"><p class=s>回住处 · 自驾约 1 小时 · 14 公里</p></li></ol></section></article>'
    if check_back_dist({'a': _sec.replace('</ol>', '<li class="r see" data-ll="39.9,116.3"><p class=s>晚上的站</p></li></ol>')}): errs.append('S11 好稿被判红（晚上还有别的站不该算）')
    if check_back_dist({'a': _sec}): errs.append('S11 好稿被判红')
    if not check_back_dist({'a': _sec.replace('14 公里', '256 公里')}): errs.append('S11 反向注入（回住处 256 公里，实际 11 公里）没变红')
    if check_tags({'a': ['偏累']}, {'a': [200]}): errs.append('S8 好稿被判红')
    if not check_tags({'a': ['古城']}, {'a': [200]}): errs.append('S8 反向注入（走路 200 分钟却没标走路多）没变红')
    if check_tags({'a': ['古城']}, {'a': [100]}): errs.append('S8 好稿被判红（走路不多）')
    if check_air({'a': {'dest': 'j', 'days': [{'air_min': 30}, {'air_min': 30}]}}, {'j'})[0]: errs.append('S9 好稿被判红')
    if not check_air({'a': {'dest': 'j', 'days': [{'air_min': 300}, {}]}}, {'j'})[0]: errs.append('S9 反向注入（air_min=300）没变红')
    return errs


if __name__ == '__main__':
    a = sys.argv[1:]
    site = os.path.abspath(a[0]) if a and not a[0].startswith('--') else None
    errs = selftest()
    if errs:
        print('✗ 闸自检失败：'); [print('   ', e) for e in errs]; sys.exit(1)
    print('✓ 反向自检通过（好稿不红、每个注入都红）')
    if '--selftest' in a: sys.exit(0)
    res, info = run(site); rc = 0
    for t, v in res:
        if v:
            rc = 1; print(f'✗ {t}：{len(v)} 处'); [print('   ', x) for x in v[:40]]
        else: print(f'✓ {t}')
    for i in info: print('  ·', i)
    sys.exit(rc)
