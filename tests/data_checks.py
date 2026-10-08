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

if fails:
    for title, items in fails:
        print(f'✗ {title}：{len(items)} 处')
        for x in items[:30]: print('   ', x)
    sys.exit(1)
print('数据和页面检查全部通过' + ('' if site else '（没给站目录，页面项未查）'))
