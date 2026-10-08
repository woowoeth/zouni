#!/usr/bin/env python3
"""数据和页面的会红的判据（2026-10 用户体验会话查出来的几类错误，固化成检查）。

用法（在项目根目录）：
    python3 tools/build_catalog.py build/catalog.js && python3 tools/build_routes_js.py build/routes.js && python3 tools/compile_itineraries.py build/routes.js
    python3 tools/build_site.py /tmp/zsite
    python3 tests/data_checks.py /tmp/zsite          # 第二个参数是建好的站；不给就只查数据

检查项（任一不过：退出码 1，并把具体的线和天打出来）：
 1 坐标隐含车速：作者写的去程时间（via）和坐标算出的距离对不上（>110 公里/小时），坐标多半错（万绿湖被解析到广州就是这样发现的）
 2 城市中心：每个目的地的“城市中心”键离所属目的地基准点过远（大安→自贡、黄陂→广州、室韦→威海）
 3 站点离城市中心：站点坐标离它所属城市中心超过 400 公里（利马纬度写反、木兰天池命中香港）
 4 缺城市中心键：编译器会回退成整个目的地的基准点，当天距离全错
 5 站点纬度符号：南半球国家里纬度不能为正
 6 页面：每页都有 data-n0 / data-start；默认出发日晚于今天；天数和 section 数一致；默认日期不让“周一闭馆”的那天落在周一
 7 串线：被串线闸拒绝的（build/denies.txt）不得出现在页面里（抽查几条已知案例）
"""
import datetime, glob, json, math, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
P = json.load(open('data/geo/pois.json', encoding='utf-8'))
I = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
DEST = {d['id']: d for k in ('domestic', 'asia', 'world') for d in json.load(open('data/destinations.json', encoding='utf-8'))[k]}
GEODEST = json.load(open('data/geo/destinations.json', encoding='utf-8'))
fails = []
DOMESTIC = {d['id'] for d in json.load(open('data/destinations.json', encoding='utf-8'))['domestic']}


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def vm(s):
    h = re.search(r'(\d+) 小时', s or ''); m = re.search(r'(\d+) 分钟', s or '')
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def pt(k):
    g = P.get(k)
    return (g['lat'], g['lng']) if g and g.get('lat') is not None else None


ROAD = ('包车', '自驾', '开车', '打车', '大巴', '公交', '客车', '班车', '汽车', '巴士')
NOTROAD = ('飞机', '高铁', '火车', '动车', '渡轮', '缆车', '轮渡', '地铁', '步行')

# 1 坐标隐含车速（只查“连续两站”和“当天从住处出发的第一站”，后者要求前一天住在同一座城，免得把搬家日当成坐标错）
bad = []
for rid, v in I.items():
    city = v['city']; prev_city = None; prev_stay = None
    for di, d in enumerate(v['days']):
        c = d.get('city', city); prev = pt(c + '|' + c) if (di == 0 or (c == prev_city and d.get('stay') == prev_stay)) else None
        for s in d['stops']:
            q = pt(c + '|' + s['q']); via = s.get('via') or ''
            if q and prev and via and any(k in via for k in ROAD) and not any(k in via for k in NOTROAD):
                m = vm(via)
                if m >= 20:
                    d_ = km(prev, q) * 1.25
                    if d_ / (m / 60) > 110: bad.append(f'{rid} 第{di + 1}天 {s["name"]}：写的 {via}，坐标算出约 {round(d_)} 公里（{round(d_ / (m / 60))} 公里/小时）')
            prev = q or prev
        prev_city, prev_stay = c, d.get('stay')
if bad: fails.append(('坐标隐含车速超过 110 公里/小时（坐标多半错了）', bad))

# 2 城市中心离目的地基准点过远（大省放宽）
BIG = ('xinjiang', 'xizang', 'qinghai', 'neimenggu', 'yunnan', 'sichuan', 'gansu', 'heilongjiang')
bad = []
for rid, v in I.items():
    g0 = GEODEST.get(v['dest']) or {}
    if g0.get('lat') is None: continue
    for c in {v['city']} | {d.get('city') for d in v['days'] if d.get('city')}:
        g = pt(c + '|' + c)
        if not g: continue
        lim = 2500 if v['dest'] in BIG else 1500
        if v['dest'] not in DOMESTIC: continue      # 国外多岛国、跨大陆的目的地，城市离基准点远是正常的，只查国内
        if len(v['days']) <= 6 and km((g0['lat'], g0['lng']), g) > lim: bad.append(f'{rid} 城市「{c}」中心 {g} 离目的地 {v["dest"]} 基准 {round(km((g0["lat"], g0["lng"]), g))} 公里')
if bad: fails.append(('城市中心离目的地基准点过远（同名地名被解析到外地）', sorted(set(bad))))

# 3 站点离城市中心
bad = []
for k, v in P.items():
    if not v or k.endswith('#tried') or '|' not in k: continue
    c, q = k.split('|', 1)
    if q == c: continue
    cc = P.get(c + '|' + c)
    # 人工写的远点（茶卡、唐古拉山口）不算，只查在线查询得来的
    if cc and v.get('src') != 'curated' and km((cc['lat'], cc['lng']), (v['lat'], v['lng'])) > 400:
        bad.append(f'{k} 离城市中心 {round(km((cc["lat"], cc["lng"]), (v["lat"], v["lng"])))} 公里')
if bad: fails.append(('站点坐标离它所属城市中心超过 400 公里', bad))

# 4 缺城市中心键
bad = []
for rid, v in I.items():
    for c in {v['city']} | {d.get('city') for d in v['days'] if d.get('city')}:
        if not pt(c + '|' + c): bad.append(f'{rid} 缺城市中心键「{c}|{c}」')
if bad: fails.append(('缺城市中心键（编译器会回退成整个目的地的基准点）', bad))

# 5 南半球纬度符号
SOUTH = {'peru', 'southafrica', 'australia', 'newzealand'}
bad = []
for rid, v in I.items():
    if v['dest'] not in SOUTH: continue
    for d in v['days']:
        c = d.get('city', v['city'])
        for s in d['stops']:
            g = pt(c + '|' + s['q'])
            if g and g[0] > 0: bad.append(f'{rid} {s["name"]} 纬度 {g[0]}（南半球应为负）')
if bad: fails.append(('南半球国家的站点纬度为正', bad))

# 5b 低平的国家和省份不会有 ≥3000 米的天（按地名补海拔时“塞拉萨里”误含“拉萨”、“松花湖”误含“花湖”就是这样发现的）
LOW = {'finland', 'norway', 'germany', 'netherlands', 'belgium', 'croatia', 'czech', 'uk', 'ireland', 'portugal', 'spain', 'greece', 'egypt', 'thailand', 'vietnam', 'malaysia', 'singapore', 'cambodia', 'laos', 'japan', 'korea',
       'jilin', 'heilongjiang', 'liaoning', 'shandong', 'jiangsu', 'zhejiang', 'fujian', 'guangdong', 'hainan', 'shanghai', 'tianjin', 'anhui', 'jiangxi', 'hunan', 'henan', 'guangxi', 'chongqing', 'beijing', 'hongkong', 'macau'}
bad = []
for rid, v in I.items():
    if v['dest'] in LOW:
        for i, d in enumerate(v['days']):
            if (d.get('elev') or 0) >= 3000 and not (rid == 'hbel8' or rid == 'wgs2'): bad.append(f'{rid} 第{i + 1}天 海拔 {d["elev"]}（{v["dest"]} 不该有 ≥3000 米）')
if bad: fails.append(('低平地区出现 ≥3000 米的天（海拔补错了）', bad))

# 5c site.js：注释（//）后面不能还跟着代码——写在同一行末尾的注释会吞掉后面的代码（这轮犯过四次，其中一次让首页“4–5 天”“一周以上”的筛选失效）
bad = []
for n, l in enumerate(open('site_src/site.js', encoding='utf-8').read().split('\n'), 1):
    s_ = re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\\n]|\\.)*`", lambda m: 'S' * len(m.group(0)), l)
    s_ = re.sub(r"/(?:[^/\\\n]|\\.)+/[gimsuy]*(?=[.,;)])", lambda m: 'R' * len(m.group(0)), s_)
    m_ = re.search(r'(?<![:\w])//', s_)
    if m_ and re.search(r'\belse\s*(if\s*\(|\{)|\}\s*else\b|\bfunction\s*\w*\s*\(|\)\s*\{|;\s*\w+\s*\(\w*', s_[m_.end():]): bad.append(f'site_src/site.js 第 {n} 行：注释后面还有代码（会被吞掉）：{l.strip()[:90]}')
if bad: fails.append(('site.js 里注释吞掉了后面的代码', bad))

# 6/7 页面
site = sys.argv[1] if len(sys.argv) > 1 else None
if site:
    today = datetime.date.today(); bad = []; bad7 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        m = re.search(r'data-n0="(\d+)" data-mon="([^"]*)" data-start="([^"]+)"', h)
        if not m: bad.append(f'{rid} 缺 data-n0/data-mon/data-start'); continue
        n0 = int(m.group(1)); st = datetime.date.fromisoformat(m.group(3)); mons = [int(x) for x in m.group(2).split(',') if x]
        if st <= today: bad.append(f'{rid} 默认出发日 {st} 不晚于今天')
        if len(re.findall(r'<section class="day"', h)) != n0: bad.append(f'{rid} 天数 {n0} 与页面里的天数不一致')
        if 'data-app="google"' in h:        # 国外线：必须有护照事项；自驾的必须有驾照提示（“订了机票才发现不能入境/不能租车”）
            _t = re.sub(r'<[^>]+>', ' ', h)
            if '护照' not in _t: bad.append(f'{rid} 国外线“出发前”里没有护照/签证事项')
            _deps = ' '.join(re.sub(r'<[^>]+>', ' ', x) for x in re.findall(r'<li class="r dep"[^>]*>(.*?)</li>', h, flags=re.S))      # 只看时间轴里的“出发 →”行
            if re.search(r'→[^自开]{0,30}(自驾约|开车约|自驾 |开车 )', _deps) and not re.search(r'驾照|国际驾', _t): bad.append(f'{rid} 国外自驾线没有驾照提示')
        dt = re.search(r'class="dtw dt"[^>]*>([^<]*)', h)
        if st.year > today.year and dt and '明年' not in dt.group(1): bad.append(f'{rid} 默认出发日在明年（{st}）但页头没写“明年”')
        # 文案里写了“海拔 N 米 / 海拔三千多米”（N≥3000）的页面，必须有氧气/高反提示（天标没给海拔时靠这条兜底；“水洞长三千多米”这种长度不算）
        _txt = re.sub(r'<[^>]+>', ' ', re.sub(r'<p class="alt">.*?</p>', '', h, flags=re.S))
        _CN = {'一': 1, '两': 2, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
        for _m in re.finditer(r'海拔[^。，；、]{0,8}?(?:(\d[\d,]*)\s*米|([一二两三四五六七八九])千[多余]?米)', _txt):
            _n = int(_m.group(1).replace(',', '')) if _m.group(1) else _CN[_m.group(2)] * 1000
            if _n >= 3000 and '氧气' not in h: bad.append(f'{rid} 文案写了“{_m.group(0)}”但页面里没有氧气/高反提示'); break
        if re.search(r'行程最高到 ([\d,]+) 米', h):
            top = int(re.search(r'行程最高到 ([\d,]+) 米', h).group(1).replace(',', ''))
            if top >= 3000 and '氧气' not in h: bad.append(f'{rid} 最高到 {top} 米但页面里没有氧气/高反提示')
        if mons and any((st + datetime.timedelta(days=i)).weekday() == 0 for i in mons): bad.append(f'{rid} 默认出发日 {st} 让周一闭馆的那天落在周一')
    if bad: fails.append(('页面不变量', bad))
    deny = os.path.join(ROOT, 'build', 'denies.txt')
    if os.path.exists(deny):
        # 抽查：串线闸拒绝的“文案 → 线”，页面里不得再出现该文案的原文
        SIGHT = {}
        src = open('tools/build_site.py', encoding='utf-8').read()
        import ast
        for n in ast.parse(src).body:
            if isinstance(n, ast.Assign) and any(getattr(t, 'id', None) == 'SIGHT' for t in n.targets): SIGHT = ast.literal_eval(n.value)
        for line in open(deny, encoding='utf-8'):
            m = re.match(r'SIGHT 「(.+?)」拒绝 (\S+)（', line)
            if not m: continue
            k, rid = m.groups(); txt = SIGHT.get(k); p = os.path.join(site, 'trip', rid, 'index.html')
            if txt and os.path.exists(p):
                body = re.sub(r'<[^>]+>', ' ', open(p, encoding='utf-8').read())
                if txt in body: bad7.append(f'{rid} 页面里仍有被拒绝的一句话（{k}）：{txt}')
    if bad7: fails.append(('串线：被闸拒绝的文案仍出现在页面里', bad7))

# 8 编译结果（build/routes.js）：返程车程、页头最长车程
RJS = os.path.join(ROOT, 'build', 'routes.js')
if os.path.exists(RJS):
    R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', open(RJS, encoding='utf-8').read()).group(1))
    def mins(x):
        m = re.search(r'约 (\d+) 小时(?: (\d+) 分)?', x or '')
        if m: return int(m.group(1)) * 60 + int(m.group(2) or 0)
        m = re.search(r'约 (\d+) 分', x or ''); return int(m.group(1)) if m else None
    LONG_BACK_OK = {'xhg3', 'xzlz7', 'asw4', 'syd6', 'nzs7', 'prg4', 'xm4'}      # 回程 >2.5 小时、人工确认过确实那么远的当天往返
    bad = []; bad2 = []; bad3 = []
    for rid, r in R.items():
        mx = 0
        for i, d in enumerate(r['days']):
            deps = [w for w in d['rows'] if w['type'] == 'dep']
            back = [w for w in deps if (w.get('how') or '').startswith('回住处')]
            withdur = [w for w in deps if (w.get('to') == '住处') and mins(w.get('how')) and mins(w.get('how')) >= 60]
            if len(withdur) > 1: bad.append(f'{rid} 第{i + 1}天：两段“出发→住处”都带 1 小时以上车程')
            if back:
                bm = mins(back[0]['how']); out = [mins(w.get('how')) for w in deps if (w.get('how') or '').startswith(('包车', '自驾', '开车', '火车', '大巴', '高铁'))]; out = [x for x in out if x]
                if bm and out and not (0.5 <= bm / max(out) <= 2): bad.append(f'{rid} 第{i + 1}天：回住处 {bm} 分钟，去程最长 {max(out)} 分钟（比值超出 0.5–2）')
                if bm and bm > 150 and rid not in LONG_BACK_OK: bad.append(f'{rid} 第{i + 1}天：回住处 {bm} 分钟 > 2.5 小时，不在人工确认的名单里（多半是坐标不对）')
            drive = sum((mins(w.get('how')) or 0) for w in deps if (w.get('how') or '').startswith(('包车', '自驾', '开车', '回住处 · 包车', '回住处 · 自驾', '回住处 · 开车')))
            mx = max(mx, drive)
        m = re.search(r'最长一天 ([\d.]+) 小时', r.get('driveSub') or '')
        if m and mx >= 120 and float(m.group(1)) * 60 < 0.6 * mx: bad2.append(f'{rid} 页头“最长一天 {m.group(1)} 小时”，实际某天开车约 {round(mx / 60, 1)} 小时')
    if bad: fails.append(('回程车程不自洽（同一天两段回程、去回时间比、过长回程）', bad))
    if bad2: fails.append(('页头“最长一天”比实际车程短太多', bad2))
    # 价格：去掉任意一天后，价格上下限都不得上升（用页面里的费用明细按网页的公式算）
    if site:
        bad = []
        for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
            rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
            mc = re.search(r'data-cost=\'([^\']*)\'', h); mn = re.search(r'data-n0="(\d+)"', h)
            if not mc or not mc.group(1) or not mn: continue
            import html as _h
            C = json.loads(_h.unescape(mc.group(1))); n0 = int(mn.group(1))
            def price(dn, N=2):
                rd = dn / n0; rn = max(dn - 1, 0) / (n0 - 1) if n0 > 1 else 1
                rooms = math.ceil(N / 2); car = math.ceil(N / 4) * C['carTotal'] / N if C.get('perCar') else C.get('tollsPP', 0); lodge = C['lodgeRoom'] * rooms / N
                loc = (C['tixPP'] + C['foodPP'] + car) * rd + lodge * rn
                return loc + C['trans'][0], loc + C['trans'][1]
            full = price(n0)
            for dn in range(1, n0):
                lo, hi = price(dn)
                if lo > full[0] + 1 or hi > full[1] + 1: bad.append(f'{rid} 去掉到 {dn} 天价格反而上升'); break
        if bad: fails.append(('价格不单调：去掉一天后价格上升', bad))

if fails:
    for title, items in fails:
        print(f'✗ {title}：{len(items)} 处')
        for x in items[:30]: print('   ', x)
    sys.exit(1)
print('数据和页面检查全部通过' + ('' if site else '（没给站目录，页面项未查）'))
