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
 22 长线检索 /long/：trips.json 里每条 days>=15 的线路都在页面里、首页有入口、搜“105”命中 xb96a、没有悬空链接
 7 串线：被串线闸拒绝的（build/denies.txt）不得出现在页面里（抽查几条已知案例）
23 SIGHT/DEEP 字典不得有重复键（ast 扫 tools/build_site.py；不需要建好的站）
25 顺路加一站的候选池质量闸（先重建池再跑 tests/nearby_pool_check.py；退出码 1、2 都算红）
26 车程模型三方一致（tests/nearby_parity.py；退出码 1、2 都算红）
27 site.js 里的 NP_LIM 和 np_model.js 的三个硬规则上限一致
28 页面行属性覆盖率、dep 行 data-mode、分片和模型文件、版本指纹含 np_model.js / routemap.js / maplibre（要建好的站）
32 「跟谁走」专栏数据闸（tests/follow_data_checks.py：线路与页面都在、notes 键等于 stop.name、src 不外泄、评价性词表、/follow/ 含全部 follow 线路、注释落页、museum 站带周一挂点；缺纪念馆类站点只警告）
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
        for si_, s in enumerate(d['stops']):
            q = pt(c + '|' + s['q']); via = s.get('via') or ''
            if di == 0 and si_ == 0 and (rid == 'xv03a' or (v['dest'] not in DOMESTIC and v['dest'] != 'taiwan')): prev = None      # xv03a 首日从玛多出发（路线 city 是曲麻莱）；      # 国外线到达日第一站是从机场或出发城市过来的（坐标里没有），不能拿基地城市中心当起点；国内线还是查（万绿湖就是这样查出来的）
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
            if (d.get('elev') or 0) >= 3000 and not (rid in ('hbel8', 'wgs2', 'xw65a', 'xz411a', 'xb96a')): bad.append(f'{rid} 第{i + 1}天 海拔 {d["elev"]}（{v["dest"]} 不该有 ≥3000 米）')
if bad: fails.append(('低平地区出现 ≥3000 米的天（海拔补错了）', bad))

# 5c site.js：注释（//）后面不能还跟着代码——写在同一行末尾的注释会吞掉后面的代码（这轮犯过四次，其中一次让首页“4–5 天”“一周以上”的筛选失效）
bad = []
for n, l in enumerate(open('site_src/site.js', encoding='utf-8').read().split('\n'), 1):
    s_ = re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"|`(?:[^`\\\n]|\\.)*`", lambda m: 'S' * len(m.group(0)), l)
    s_ = re.sub(r"/(?:[^/\\\n]|\\.)+/[gimsuy]*(?=[.,;)])", lambda m: 'R' * len(m.group(0)), s_)
    m_ = re.search(r'(?<![:\w])//', s_)
    if m_ and re.search(r'\belse\s*(if\s*\(|\{)|\}\s*else\b|\bfunction\s*\w*\s*\(|\)\s*\{|;\s*\w+\s*\(\w*', s_[m_.end():]): bad.append(f'site_src/site.js 第 {n} 行：注释后面还有代码（会被吞掉）：{l.strip()[:90]}')
if bad: fails.append(('site.js 里注释吞掉了后面的代码', bad))

# 23 SIGHT/DEEP 重复键（2026-10-16）：Python 字典后写的悄悄覆盖前面的，前面的文案丢了，还可能把别处的文案盖到现在的位置上
#    （镇国寺：河内的、高邮的、平遥的三条互相盖；红石峡：榆林的盖掉云台山的）。同名但在不同城市的景点，用“限定词|景点名”的键（限定词用 / 分隔，
#    出现在当天上下文里任一个即可，见 build_site.sight_of），不要写成两个同名键。用 ast 扫源码，不 import（build_site 一 import 就开始建站）。
import ast, collections
bad = []
for n_ in ast.parse(open('tools/build_site.py', encoding='utf-8').read()).body:
    if isinstance(n_, ast.Assign) and isinstance(n_.value, ast.Dict) and any(getattr(t_, 'id', None) in ('SIGHT', 'DEEP') for t_ in n_.targets):
        nm_ = next(t_.id for t_ in n_.targets if getattr(t_, 'id', None) in ('SIGHT', 'DEEP')); seen_ = collections.defaultdict(list)
        for k_ in n_.value.keys:
            if isinstance(k_, ast.Constant): seen_[k_.value].append(k_.lineno)
            if isinstance(k_, ast.Constant) and '|' in k_.value and not all(x_.strip() for x_ in k_.value.split('|', 1)[0].split('/') + [k_.value.split('|', 1)[1]]): bad.append(f'{nm_}「{k_.value}」第 {k_.lineno} 行：限定词或景点名是空的')
        bad += [f'{nm_}「{k_}」重复 {len(v_)} 次（第 {"、".join(map(str, v_))} 行）：合并成一条；同名不同城市改用“限定词|景点名”' for k_, v_ in seen_.items() if len(v_) > 1]
if bad: fails.append(('SIGHT/DEEP 字典里有重复键（后面的悄悄覆盖前面的）', bad))

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
        # 日期写法（2026-10-17 起）：不出现“明年”；默认日期是建议值，页头底栏和说明行都写“建议”；跨年的写完整“2027 年 M/D”
        dk_ = re.search(r'<div class="dock"><div><b>([^<]*)</b>', h); dn_ = re.search(r'<p class="dnote"[^>]*>([^<]*)</p>', h)
        if '明年' in (dk_.group(1) if dk_ else '') or ('明年' in (dn_.group(1) if dn_ else '') and not re.search(r'明年 \d+/\d+（距今 \d+\s天）', dn_.group(1))): bad.append(f'{rid} 日期里写着“明年”但不是“明年 M/D（距今 N 天）”的格式')
        # 2026-10-18：日期只在页头日期条（.glance .dt）写一次；说明行（.dnote）不再重复月日、不写“建议”，只写“最好 M/D–M/D”、往年气温，跨年的写“2027 年出发”；底栏照旧“建议 M/D 出发”（滚过页头才显示、整块可点改日期）
        if not (dk_ and dk_.group(1).startswith('建议 ')): bad.append(f'{rid} 默认日期没写“建议”（底栏）')
        if dn_ and (re.search(r'\d+/\d+\s*周|建议|一年四季', dn_.group(1))): bad.append(f'{rid} 说明行又写了一遍出发日期 / “建议” / “一年四季都能去”：{dn_.group(1)[:40]}')
        if st.year > today.year and not (dn_ and re.search(f'明年 {st.month}/{st.day}（距今 {(st - today).days}\\s天）', dn_.group(1))): bad.append(f'{rid} 默认出发日在明年（{st}）但说明行没写“明年 {st.month}/{st.day}（距今 {(st - today).days} 天）”')   # 底栏窄，只写 M/D
        # 文案里写了“海拔 N 米 / 海拔三千多米”（N≥3000）的页面，必须有氧气/高反提示（天标没给海拔时靠这条兜底；“水洞长三千多米”这种长度不算）
        _txt = re.sub(r'<[^>]+>', ' ', re.sub(r'<p class="alt[^"]*">.*?</p>', '', h, flags=re.S))
        _CN = {'一': 1, '两': 2, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9}
        for _m in re.finditer(r'海拔[^。，；、]{0,8}?(?:(\d[\d,]*)\s*米|([一二两三四五六七八九])千[多余]?米)', _txt):
            _n = int(_m.group(1).replace(',', '')) if _m.group(1) else _CN[_m.group(2)] * 1000
            if _n >= 3000 and '氧气' not in h: bad.append(f'{rid} 文案写了“{_m.group(0)}”但页面里没有氧气/高反提示'); break
        if re.search(r'行程最高到 ([\d,]+) 米', h):
            top = int(re.search(r'行程最高到 ([\d,]+) 米', h).group(1).replace(',', ''))
            if top >= 3000 and '氧气' not in h: bad.append(f'{rid} 最高到 {top} 米但页面里没有氧气/高反提示')
        if mons and any((st + datetime.timedelta(days=i)).weekday() == 0 for i in mons): bad.append(f'{rid} 默认出发日 {st} 让周一闭馆的那天落在周一')
    if bad: fails.append(('页面不变量', bad))
    # 8 热门馆名单：行程里出现这些馆，那一行必须有“要预约”徽标（漏掉的后果是白跑）；名字里带“阿布扎比”的是另一座馆，不算
    MUST_BOOK = ['故宫博物院', '颐和园', '慕田峪长城', '八达岭长城', '卢浮宫', '梵高博物馆', '安妮之家', '阿尔罕布拉宫', '圣家堂', '梵蒂冈博物馆', '乌菲兹美术馆', '新天鹅堡', '马丘比丘', '埃菲尔铁塔', '凡尔赛宫', '奥赛博物馆', '罗马斗兽场', '塞维利亚王宫']
    bad8 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for li in re.findall(r'<li class="r (?:see|fun)"[^>]*>(.*?)</li>', h, flags=re.S):
            tx = re.sub(r'<[^>]+>', ' ', re.sub(r'<p class="fnote">.*?</p>', '', li, flags=re.S))      # 跟谁走的站点小字（p.fnote）里会提到别的馆（“颐和园谐趣园”），不算这一行的名字
            for k in MUST_BOOK:
                if k in tx.split('·')[0] and '阿布扎比' not in tx and '国立故宫' not in tx and '沈阳故宫' not in tx and 'class="bkn' not in li: bad8.append(f'{rid} 「{k}」那一行没有“要预约”徽标')
    if bad8: fails.append(('热门馆缺预约徽标', sorted(set(bad8))))
    # 9 当天要坐船/渡轮（路上一行写了轮渡/渡轮/快艇/长尾船/船约）：那一天必须有“班次以当天为准”的提醒
    bad9 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]; tx = re.sub(r'<[^>]+>', ' ', sec)
            if re.search(r'轮渡|渡轮|快艇|快船|长尾船|(?<!门票 )[坐加搭乘]船(?![游看穿进过从在])|船约|船回', tx) and 'alt ferry' not in sec:
                bad9.append(f'{rid} ' + re.search(r'id="(d\d+)"', sec).group(1) + ' 要坐船但没有班次/停航提醒')
    if bad9: fails.append(('坐船当天缺班次提醒', sorted(set(bad9))))
    # 10 国外去处每周闭馆日：表里的馆出现在行程里，那一行要带 data-cw；默认出发日不能让那一天落在闭馆日
    FC = {'卢浮宫': 1, '奥赛博物馆': 0, '凡尔赛宫': 0, '乌菲兹美术馆': 0, '梵蒂冈博物馆': 6, '托普卡帕宫': 1, '景福宫': 1, '昌德宫': 0, '无忧宫': 0, '国家人类学博物馆': 0}
    bad10 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        if 'data-app="amap"' in h.split('>')[0] + h[:4000] and '<article class="trip" data-app="amap"' in h: continue
        m = re.search(r'data-start="([^"]+)" data-cl="([^"]*)"', h)
        if not m: bad10.append(f'{rid} 缺 data-cl'); continue
        st = datetime.date.fromisoformat(m.group(1)); cl = [tuple(map(int, z.split(':'))) for z in m.group(2).split(',') if z]
        for i, js in cl:
            if (st + datetime.timedelta(days=i)).isoformat() and ((st + datetime.timedelta(days=i)).weekday() + 1) % 7 == js: bad10.append(f'{rid} 默认出发日 {st} 让第 {i + 1} 天落在闭馆日')
        for m2 in re.finditer(r'<li class="r (?:see|fun)"([^>]*)><time>[^<]*</time><span class="dot"></span><div class="rb"><p class="m">([^<]+)', h):
            nm = m2.group(2).strip(); has = 'data-cw=' in m2.group(1)
            if nm in FC and not has: bad10.append(f'{rid} 「{nm}」没有闭馆日标记')
            if has and nm not in FC: bad10.append(f'{rid} 「{nm}」不该有闭馆日标记')
    if bad10: fails.append(('国外闭馆日', sorted(set(bad10))))
    # 11 清真寺：表里的清真寺出现在哪一天，那一天必须有“清真寺”着装/可否入内提醒
    MOS = ['蓝色清真寺', '圣索菲亚', '布特拉清真寺', '库图比亚清真寺', '卡鲁因清真寺', '亚庇市立清真寺', '朱玛清真寺', '比比哈努姆清真寺', '东关清真大寺']
    bad11 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]
            for li in re.findall(r'<li class="r (?:see|fun)"[^>]*>(.*?)</li>', sec, flags=re.S):
                nm = re.sub(r'<[^>]+>', ' ', li.split('<p class="m">')[1].split('</p>')[0]).strip() if '<p class="m">' in li else ''
                if nm in MOS and 'alt mosque' not in sec: bad11.append(f'{rid} ' + re.search(r'id="(d\d+)"', sec).group(1) + f' 「{nm}」那天没有清真寺提醒')
    if bad11: fails.append(('清真寺缺提醒', sorted(set(bad11))))
    # 12 转场日：17:00 以后才出发、路上 ≥2 小时，到站后就不能再排景点（深夜到了还逛；该把长途挪到下午、晚饭在目的地）
    bad12 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]; dn = re.search(r'id="(d\d+)"', sec).group(1)
            rows = []
            for li in sec.split('<li class="r ')[1:]:
                ty = li.split('"')[0]; tm = re.search(r'<time>(\d\d):(\d\d)</time>', li)
                sub = re.sub(r'<[^>]+>', ' ', li.split('<p class=s>')[1].split('</p>')[0]) if '<p class=s>' in li else ''
                rows.append((ty, int(tm.group(1)) * 60 + int(tm.group(2)) if tm else None, sub))
            for i, (ty, tm, sub) in enumerate(rows[:-1]):
                m = re.search(r'约\s*(?:(\d+)\s*小时)?\s*(?:(\d+)\s*分钟?)?', sub)
                if ty == 'dep' and tm is not None and tm >= 17 * 60 and m and (int(m.group(1) or 0) * 60 + int(m.group(2) or 0)) >= 120 and rows[i + 1][0] in ('see', 'fun') and '回住处' not in sub:
                    bad12.append(f'{rid} {dn} {tm // 60:02d}:{tm % 60:02d} 才出发、路上 ≥2 小时，到站还排了景点')
    if bad12: fails.append(('转场日晚出发还排景点', sorted(set(bad12))))
    # 13 天标题里的景点（城堡/宫/教堂/博物馆/寺/塔…）必须和当天时间表对得上（kry4 标题写“黑石城堡”，时间表是“布拉尼城堡”）。去掉后缀后核心词没有任何 2 字片段出现就红；简称（陕历博）不带后缀，不在范围内
    SUF = '城堡|宫殿|宫|教堂|大教堂|博物馆|美术馆|寺|塔|古堡|要塞|修道院'
    bad13 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]; dn = re.search(r'id="(d\d+)"', sec).group(1)
            title = re.sub(r'<[^>]+>', '', re.search(r'<h2>(.*?)</h2>', sec, flags=re.S).group(1))
            blob = ' '.join(re.sub(r'<[^>]+>', '', m).strip() for m in re.findall(r'<p class="m">(.*?)</p>', sec, flags=re.S))
            for tok in re.split(r'\s*·\s*', title):
                mm_ = re.match(r'^(.{2,})(' + SUF + ')$', tok)
                if not mm_ or tok.startswith(('去', '回', '到')): continue
                core = mm_.group(1)
                if core in blob or tok in blob or any(core[i:i + 2] in blob for i in range(len(core) - 1)): continue
                bad13.append(f'{rid} {dn} 标题里的「{tok}」在当天时间表里找不到')
    if bad13: fails.append(('天标题和时间表对不上', sorted(set(bad13))))
    # 14 “出发前”里写了节日窗口（“10 月 31 日到 11 月 2 日是亡灵节”）：默认出发日起的行程必须把整段窗口盖住
    bad14 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        ms = re.search(r'data-n0="(\d+)".*?data-start="([^"]+)"', h)
        if not ms: continue
        n0, st = int(ms.group(1)), datetime.date.fromisoformat(ms.group(2))
        for w in re.finditer(r'(\d+)\s*月\s*(\d+)\s*日到\s*(\d+)\s*月\s*(\d+)\s*日是([^，。<]+)', h):
            a = datetime.date(st.year, int(w.group(1)), int(w.group(2))); b = datetime.date(st.year, int(w.group(3)), int(w.group(4)))
            if not (st <= a and b <= st + datetime.timedelta(days=n0 - 1)): bad14.append(f'{rid} 默认 {st} 起 {n0} 天，没盖住{w.group(5)}（{a}–{b}）')
    if bad14: fails.append(('节日窗口没盖住', sorted(set(bad14))))
    # 15 晚饭后“出发 → 住处”不能是 ≥2 小时的火车/高铁（把白天转场的高铁抄到了晚上：slgt8、hngt6 到住处过了午夜）
    bad15 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]; dn = re.search(r'id="(d\d+)"', sec).group(1)
            for li in sec.split('<li class="r dep"')[1:]:
                tm = re.search(r'<time>(\d\d):(\d\d)</time>', li); sub = re.sub(r'<[^>]+>', ' ', li.split('<p class=s>')[1].split('</p>')[0]) if '<p class=s>' in li else ''
                to_home = '出发 → 住处' in re.sub(r'<[^>]+>', '', li)
                mh = re.search(r'约\s*(?:(\d+)\s*小时)?\s*(?:(\d+)\s*分钟?)?', sub)
                if to_home and tm and int(tm.group(1)) >= 17 and re.search(r'高铁|动车|火车', sub) and mh and (int(mh.group(1) or 0) * 60 + int(mh.group(2) or 0)) >= 120:
                    bad15.append(f'{rid} {dn} {tm.group(0)[6:11]} 晚上才坐 ≥2 小时的车回住处')
    if bad15: fails.append(('晚上坐长途火车回住处', sorted(set(bad15))))
    # 16 夜游/夜市/夜景类站点：必须在所属城市中心 40 公里内（珠江夜游曾命中南沙一家摩托车厂，白写“包车 1 小时 10 分”）
    bad16 = []
    for k, v in P.items():
        if not v or k.endswith('#tried') or '|' not in k: continue
        city, q = k.split('|', 1)
        if re.search(r'夜游|夜市|夜景|夜钓', q) and (city + '|' + city) in P and P[city + '|' + city]:
            cc_ = P[city + '|' + city]
            if km((cc_['lat'], cc_['lng']), (v['lat'], v['lng'])) > 40: bad16.append(f'{k} 离城市中心 {round(km((cc_["lat"], cc_["lng"]), (v["lat"], v["lng"])))} 公里')
    if bad16: fails.append(('夜游类站点离城市太远', bad16))
    # 17 靠天吃饭的去处（蓝洞、峡湾）：那天必须有“看天气”提醒
    bad17 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        for sec in h.split('<section class="day"')[1:]:
            sec = sec.split('</section>')[0]
            for li in re.findall(r'<li class="r (?:see|fun)"[^>]*>(.*?)</li>', sec, flags=re.S):
                nm = re.sub(r'<[^>]+>', ' ', li.split('<p class="m">')[1].split('</p>')[0]).strip() if '<p class="m">' in li else ''
                if nm in ('卡普里蓝洞', '米尔福德峡湾', '贝纳吉尔海蚀洞') and 'alt wx' not in sec: bad17.append(f'{rid} 「{nm}」那天没有看天气提醒')
    if bad17: fails.append(('靠天吃饭的去处缺提醒', sorted(set(bad17))))
    # 18 默认出发日不能落进法定假日出行高峰（价格贵、车票紧、限流），线路自己为假日做的（出发前写了节日名）除外；表和 build_site.HOLIDAYS 一致
    HOL = [('元旦', '2027-01-01', '2027-01-03'), ('春节', '2027-02-04', '2027-02-14'), ('清明', '2027-04-03', '2027-04-05'), ('五一', '2027-05-01', '2027-05-05'), ('端午', '2027-06-09', '2027-06-11'),
           ('中秋', '2027-09-15', '2027-09-17'), ('国庆', '2027-10-01', '2027-10-07'), ('元旦', '2028-01-01', '2028-01-03'), ('春节', '2028-01-24', '2028-02-03'), ('清明', '2028-04-04', '2028-04-06'),
           ('五一', '2028-05-01', '2028-05-05'), ('端午', '2028-05-27', '2028-05-29'), ('国庆', '2028-10-01', '2028-10-07')]
    bad18 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; h = open(f, encoding='utf-8').read()
        ms = re.search(r'data-n0="(\d+)".*?data-start="([^"]+)"', h)
        if not ms: continue
        n0, st = int(ms.group(1)), datetime.date.fromisoformat(ms.group(2)); en = st + datetime.timedelta(days=n0 - 1)
        pre = re.sub(r'<[^>]+>', '', h.split('<h2>出发前</h2>')[1].split('</section>')[0]) if '<h2>出发前</h2>' in h else ''
        for nm, a, b in HOL:
            if datetime.date.fromisoformat(a) <= en and st <= datetime.date.fromisoformat(b) and nm not in pre: bad18.append(f'{rid} 默认 {st} 起 {n0} 天，落进{nm}假期（{a}–{b}）')
    if bad18: fails.append(('默认出发日落进法定假日', sorted(set(bad18))))
    # 19 国外线“今晚住”的高级档价格必须按国家的住宿估价算（房价 = 每人 × 2），不能是国内价格表（夏威夷威基基四星写成 ¥400–700）
    _ns = {}; exec(re.search(r'^ASIA_STAY = \{.*\}$', open('tools/estimate_prices.py', encoding='utf-8').read(), re.M).group(0), _ns); AS_ = _ns['ASIA_STAY']
    DEST_OF = {t_['id']: t_['dest'] for t_ in json.load(open('data/catalog/trips.json', encoding='utf-8'))['trips']}
    DSCOPE = {d_['id']: d_['scope'] for d_ in json.load(open('data/catalog/destinations.json', encoding='utf-8'))['destinations']}
    R_ = lambda x: f'{int(round(x / 100.0)) * 100:,}' if x >= 1000 else f'{int(round(x / 50.0)) * 50}'
    bad19 = []
    for f in glob.glob(os.path.join(site, 'trip', '*', 'index.html')):
        rid = f.split('/')[-2]; dst = DEST_OF.get(rid)
        if not dst or DSCOPE.get(dst) == 'domestic': continue
        h = open(f, encoding='utf-8').read(); lo_, hi_ = AS_.get(dst, (180, 380)); want = f'¥{R_(lo_ * 2)}–{R_(hi_ * 2)}'
        for m in re.finditer(r'<span class="tier">高级</span>.*?参考价 (¥[\d,]+–[\d,]+)/晚', h, flags=re.S):
            if m.group(1) != want: bad19.append(f'{rid} 高级档写 {m.group(1)}，按 {dst} 住宿估价应是 {want}'); break
    if bad19: fails.append(('国外住宿三档价格不对', sorted(set(bad19))))
    # 20 site.js 语法：node --check（行内注释吞掉后面的代码这类错，字符串 lint 抓不全：2026-10 又吞了一次，整个页面脚本报错）
    import subprocess, shutil as _sh
    if _sh.which('node'):
        for _f in ('site.js', 'np_model.js'):      # np_model.js：顺路加一站的车程模型（site.js 点开才懒加载它，语法错了只有点开才爆）
            _p = subprocess.run(['node', '--check', os.path.join(ROOT, 'site_src', _f)], capture_output=True, text=True)
            if _p.returncode: fails.append((_f + ' 语法错误', [next((l for l in _p.stderr.splitlines() if 'Error' in l and 'Node.js' not in l), 'node --check 失败')]))
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
                body = ' '.join(re.findall(r'<span class="sn2">(.*?)</span>', open(p, encoding='utf-8').read(), re.S))      # 只看“景点一句话”（SIGHT 渲染出来的 span.sn2）：线路作者自己写的当天文字（story）碰巧有同一句话不算串线
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
    LONG_BACK_OK = {'xy303b', 'xw89a', 'xw95a', 'xv03a', 'xv10a', 'xhg3', 'xzlz7', 'asw4', 'syd6', 'nzs7', 'prg4', 'xm4', 'xb96a', 'xl3a'}      # 回程 >2.5 小时、人工确认过确实那么远的当天往返
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

    # 21 纪录片：只有一季（或查不到多季）的片子页面里不得出现“第几季”（2026-10 用户指出：没有多季的也写了第一季）
    if site:
        bad = []
        for pth in ('hexi', 'shuben', 'changjiang', 'sichou', 'yingxiang', 'silu'):
            f = os.path.join(site, pth, 'index.html')
            if not os.path.exists(f): bad.append(f'{pth} 页面不存在'); continue
            n = len(re.findall(r'第[一二三四五六七八九十]季', open(f, encoding='utf-8').read()))
            if n: bad.append(f'/{pth}/ 里出现 {n} 处“第几季”')
        if bad: fails.append(('单季纪录片页面写了“第几季”', bad))


# 22 长线检索 /long/（2026-10-16）：从 trips.json 出发反向查，每条 days>=15 的线路都得在 /long/ 里；首页要有入口；搜 105 得到 xb96a；不得有不存在的 trip 链接
if site:
    bad = []
    TJ = json.load(open('data/catalog/trips.json', encoding='utf-8'))['trips']
    longs = [t for t in TJ if (t.get('days') or 0) >= 15]
    lf = os.path.join(site, 'long', 'index.html')
    if not longs: bad.append('trips.json 里没有 days>=15 的线路（判据本身失效）')
    if not os.path.exists(lf): bad.append('/long/ 页面不存在')
    else:
        lh = open(lf, encoding='utf-8').read()
        cards = re.findall(r'<li class="lc"[^>]*?data-n="(\d+)"[^>]*?data-q="([^"]*)">\s*<a href="/trip/([^/"]+)/"', lh)
        ids = [c[2] for c in cards]
        for t in longs:
            if t['id'] not in ids: bad.append(f'{t["id"]}（{t["days"]} 天）不在 /long/ 页面里')
        if len(ids) != len(set(ids)): bad.append('/long/ 里有重复的卡片')
        for i_ in ids:
            if not os.path.exists(os.path.join(site, 'trip', i_, 'index.html')): bad.append(f'/long/ 链到不存在的 /trip/{i_}/')
        for i_ in re.findall(r'href="/trip/([^/"]+)/"', lh):
            if i_ not in ids: bad.append(f'/long/ 里有卡片之外的 trip 链接 {i_}')
        hit = [c for c in cards if '105' in c[1] and c[2] == 'xb96a']
        if 'xb96a' in [t['id'] for t in longs] and not hit: bad.append('/long/ 里搜“105”命不中 xb96a（卡片 data-q 里没有 105 天）')
        mm = [c for c in cards if '边境' in c[1] and c[2] == 'xb96a']
        if 'xb96a' in [t['id'] for t in longs] and not mm: bad.append('/long/ 里搜“边境”命不中 xb96a')
    hf = os.path.join(site, 'index.html')
    # 首页进 /long/ 只留频道那一格（页脚里也有 /long/ 链接，所以不能只数 href）；.longbar 和天数 chip 末尾的链接是重复入口，2026-10-16 去掉，不许回来
    hh = open(hf, encoding='utf-8').read() if os.path.exists(hf) else ''
    chan = re.search(r'<nav class="chan2"[^>]*>(.*?)</nav>', hh, re.S)
    if not chan or 'href="/long/"' not in chan.group(1): bad.append('首页频道（.chan2）里没有“长线自驾”那一格（指向 /long/）')
    if 'class="longbar"' in hh: bad.append('首页又出现了 .longbar（长线自驾重复入口）')
    if re.search(r'<div class="dchips".*?</div>', hh, re.S) and 'href="/long/"' in re.search(r'<div class="dchips".*?</div>', hh, re.S).group(0): bad.append('首页天数 chip 里又出现了指向 /long/ 的链接')
    n_lg = hh.count('href="/long/"')
    if n_lg > 2: bad.append(f'首页指向 /long/ 的链接有 {n_lg} 处（频道一格 + 页脚一处，多了就是重复入口）')
    for pth in ('where', ):
        f = os.path.join(site, pth, 'index.html')
        if not os.path.exists(f) or 'href="/long/"' not in open(f, encoding='utf-8').read(): bad.append(f'/{pth}/ 没有指向 /long/ 的链接')
    ti = os.path.join(site, 'assets', 'tidx.js')
    if not os.path.exists(ti): bad.append('线路搜索索引 assets/tidx.js 不存在')
    else:
        IDX = json.loads(open(ti, encoding='utf-8').read().split('=', 1)[1].split(';\nwindow.ZTFOL=')[0].rstrip().rstrip(';'))      # tidx.js 里还有第二个变量 ZTFOL（跟谁走的主题），只取 ZTIDX 这一段
        if not any(x[0] == 'xb96a' and '105天' in x[5] and '边境线' in x[5] for x in IDX): bad.append('线路搜索索引里 xb96a 搜不到“105天”“边境线”')
    if bad: fails.append(('长线检索 /long/ 不完整', bad))

# 24 假长车程（2026-10-16）：页面写了 ≥60 公里的包车/自驾，用 pois 坐标重算却不到一半（住处坐标被在线地名解析到外地、站点坐标落在别的城市）
if site:
    import subprocess as _sp
    _r = _sp.run([sys.executable, 'tools/check_fake_legs.py', 'build/routes.js'], capture_output=True, text=True, cwd=ROOT)
    if _r.returncode: fails.append(('假长车程（写的公里数与坐标重算对不上）', [l for l in (_r.stdout + _r.stderr).splitlines() if l.strip()][:20]))

# 25-26 「顺路加一站 / 换一站」的候选池和车程模型（2026-10-16；设计 docs/handoff/design-nearby-stops.md）
#   25 候选池质量闸：先重建池（确定性、约 2 秒），再跑 tests/nearby_pool_check.py。退出码 1 = 池有问题，2 = 没有 node（闸没法跑）——两种都算红，不当跳过
#   26 Python ↔ JS ↔ compile_itineraries.leg 三方一致性：tests/nearby_parity.py（同样 1、2 都算红）
import subprocess as _sp2
_r0 = _sp2.run([sys.executable, 'tools/build_nearby_pool.py', '--quiet'], capture_output=True, text=True, cwd=ROOT)
if _r0.returncode: fails.append(('候选池构建失败（tools/build_nearby_pool.py）', [l for l in (_r0.stdout + _r0.stderr).splitlines() if l.strip()][-8:]))
else:
    for _title, _cmd in (('候选池质量闸不过（tests/nearby_pool_check.py；退出码 2 = 没 node，也算红）', 'tests/nearby_pool_check.py'), ('车程模型三方不一致（tests/nearby_parity.py；退出码 2 = 没 node，也算红）', 'tests/nearby_parity.py')):
        _r1 = _sp2.run([sys.executable, _cmd], capture_output=True, text=True, cwd=ROOT)
        if _r1.returncode != 0: fails.append((_title + f'，退出码 {_r1.returncode}', [l for l in (_r1.stdout + _r1.stderr).splitlines() if l.strip() and ('红' in l or '不一致' in l or 'node' in l or '没有' in l or 'Error' in l)][:12] or [(_r1.stdout + _r1.stderr)[-400:]]))

# 27 site.js 里复制的三个硬规则数字（弹层里看“这天是不是排满”时模型还没加载，用的是同样的数）必须和 np_model.js 一致
_nm = open('site_src/np_model.js', encoding='utf-8').read(); _sj = open('site_src/site.js', encoding='utf-8').read()
_lim = re.search(r'NP_LIM=\{MAX:(\d+),END:(\d+),SPAN:(\d+),CAP:(\d+),EXTRA:(\d+)\}', _sj)
_mx = re.search(r'MAX_NONMEAL:\s*(\d+)', _nm); _en = re.search(r'END_LIMIT:\s*(\d+)\s*\*\s*60\s*\+\s*(\d+)', _nm); _sp = re.search(r'SPAN_LIMIT:\s*(\d+)\s*\*\s*60', _nm)
_cp = re.search(r'DAY_CAP:\s*(\d+)\s*\*\s*60', _nm); _ex = re.search(r'END_EXTRA:\s*(\d+)', _nm)      # 2026-10-18 加的：当天结束上限 = min(23:00, max(21:30, 原结束 + 30 分钟))
if not (_lim and _mx and _en and _sp and _cp and _ex): fails.append(('site.js 的 NP_LIM 或 np_model.js 的五个上限找不到', ['格式变了，改这条判据']))
elif tuple(int(x) for x in _lim.groups()) != (int(_mx.group(1)), int(_en.group(1)) * 60 + int(_en.group(2)), int(_sp.group(1)) * 60, int(_cp.group(1)) * 60, int(_ex.group(1))):
    fails.append(('site.js 的 NP_LIM 和 np_model.js 的上限（非吃饭站 / 结束时间 / 首尾分钟 / 23:00 封顶 / 多出的 30 分钟）不一致', [f'site.js {_lim.groups()} ≠ np_model.js {(_mx.group(1), int(_en.group(1)) * 60 + int(_en.group(2)), int(_sp.group(1)) * 60, int(_cp.group(1)) * 60, _ex.group(1))}']))

# 28a sw.js 的缓存策略：.js 必须“先走网络、断网才用缓存”。候选分片（assets/np/*.js）和 np_model.js 靠这一条保证不会永远旧；有人把 .js 改成“先用缓存”，这里就红
_sw = open('site_src/sw.js', encoding='utf-8').read()
if not re.search(r"\\\.\(css\|js\|webmanifest\)\$/\.test\(u\.pathname\)", _sw) or 'fresh(r)' not in _sw: fails.append(('sw.js 不再对 .js 先走网络（候选分片会被缓存成旧的）', ['site_src/sw.js 里 /\\.(css|js|webmanifest)$/ 那一条不见了']))

# 28b 微信老内核（X5）只认 ES5：np_model.js 和 site.js 里顺路加一站那一块（从“⑧ 顺路加一站”到“⑦ 带老人孩子”）不许用 => 模板字符串 ?. ?? flatMap .at() let const 展开 Object.assign includes startsWith Array.from find
_np_js = [('site_src/np_model.js', open('site_src/np_model.js', encoding='utf-8').read())]
_i0 = _sj.find('// ⑧ 顺路加一站'); _i1 = _sj.find('// ⑦ 带老人孩子')
if _i0 < 0 or _i1 < _i0: fails.append(('site.js 里找不到“⑧ 顺路加一站”到“⑦ 带老人孩子”这一块', ['标记注释被改了，改这条判据']))
else: _np_js.append(('site_src/site.js 顺路加一站块', _sj[_i0:_i1]))
_badsyn = []
for _nm_, _src in _np_js:
    for _pat, _what in ((r'=>', '箭头函数'), (r'`', '模板字符串'), (r'\?\.', '?.'), (r'\?\?', '??'), (r'flatMap', 'flatMap'), (r'\.at\(', '.at()'), (r'(?<![\w.$])(?:let|const)\s', 'let/const'), (r'\.\.\.', '展开/剩余'), (r'Object\.assign|\.includes\(|\.startsWith\(|\.endsWith\(|Array\.from|\.find\(|\.findIndex\(|\.padStart\(|\.repeat\(', 'ES6 方法')):
        for _m in re.finditer(_pat, re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"", lambda m: 'S' * len(m.group(0)), re.sub(r'/\*.*?\*/', '', _src, flags=re.S))):
            _badsyn.append(f'{_nm_}：{_what}')
            break
if _badsyn: fails.append(('顺路加一站的 JS 用了 ES5 之外的语法（微信老内核会整页脚本报错）', _badsyn))

# 28 页面和资源（要建好的站）：行属性覆盖率、dep 行 data-mode 和当天 data-lm 一致、分片和模型文件在、版本指纹含 np_model.js、没有把 pool.json/stats.json 发布出去
if site:
    import hashlib as _hl2
    _bad = []; _tot = _cov = 0
    for _f in sorted(glob.glob(os.path.join(site, 'trip', '*', 'index.html'))):
        _h = open(_f, encoding='utf-8').read(); _rid = _f.split('/')[-2]
        for _sec in _h.split('<section class="day"')[1:]:
            _sec = _sec.split('</section>')[0]
            _lm = re.search(r'data-lm="(\w+)"', _sec)
            if not _lm: _bad.append(f'{_rid}：有一天没有 data-lm'); break
            for _m in re.finditer(r'<li class="r (see|fun)"([^>]*)><time>[^<]*</time><span class="dot"></span><div class="rb"><p class="m">([^<]+)', _sec):
                if '沿途' in _m.group(3): continue
                _tot += 1; _cov += ('data-ll="' in _m.group(2) and 'data-dm="' in _m.group(2) and 'data-pid="' in _m.group(2))
            for _m in re.finditer(r'<li class="r dep"([^>]*)>', _sec):
                _dm = re.search(r'data-mode="(\w+)"', _m.group(1))
                if not _dm or _dm.group(1) != _lm.group(1): _bad.append(f'{_rid}：dep 行 data-mode={_dm and _dm.group(1)} ≠ 当天 data-lm={_lm.group(1)}'); break
    if _tot and _cov / _tot < 0.98: _bad.append(f'看点/玩的行里带坐标、停留、id 的只有 {_cov}/{_tot}（{100 * _cov / _tot:.1f}%），低于 98%')
    _np = os.path.join(site, 'assets', 'np')
    if not os.path.exists(os.path.join(_np, '_index.js')): _bad.append('assets/np/_index.js 不存在（点开“换成/加一个”会永远“没网”）')
    else:
        _cells = re.findall(r'"(\d+_\d+)"', open(os.path.join(_np, '_index.js'), encoding='utf-8').read())
        _miss = [c_ for c_ in _cells if not os.path.exists(os.path.join(_np, c_ + '.js'))]
        if _miss: _bad.append(f'_index.js 里的格缺分片文件：{_miss[:5]}')
        _big = [(f_, os.path.getsize(os.path.join(_np, f_))) for f_ in os.listdir(_np) if os.path.getsize(os.path.join(_np, f_)) > 36 * 1024]
        if _big: _bad.append(f'分片超过 36 KB：{_big[:3]}')
        _extra = [f_ for f_ in os.listdir(_np) if not f_.endswith('.js')]
        if _extra: _bad.append(f'assets/np 里有不该发布的文件：{_extra}')
    if not os.path.exists(os.path.join(site, 'assets', 'np_model.js')): _bad.append('assets/np_model.js 不存在')
    elif open(os.path.join(site, 'assets', 'np_model.js'), encoding='utf-8').read() != open('site_src/np_model.js', encoding='utf-8').read(): _bad.append('站里的 assets/np_model.js 和 site_src/np_model.js 不一样（建站后改过源码，没重建）')
    _ver = _hl2.md5((open('site_src/site.css', encoding='utf-8').read() + open('site_src/site.js', encoding='utf-8').read() + open('site_src/np_model.js', encoding='utf-8').read() + open('site_src/routemap.js', encoding='utf-8').read() + open('site_src/maplibre/maplibre-gl.js', encoding='utf-8').read() + open('site_src/maplibre/maplibre-gl.css', encoding='utf-8').read() + open('site_src/map/style.json', encoding='utf-8').read()).encode()).hexdigest()[:8]
    _pg = open(os.path.join(site, 'trip', 'xa3', 'index.html'), encoding='utf-8').read()
    if f'/assets/site.js?v={_ver}' not in _pg: _bad.append(f'xa3 页面里的 site.js 版本指纹不是源码（site.css + site.js + np_model.js + routemap.js + maplibre js/css + map/style.json）的哈希 {_ver}：线上跑的是不是这一版看不出来')
    if _bad: fails.append(('顺路加一站：页面属性 / 资源 / 版本指纹', _bad[:30]))

# 29 site.js 全文件 ES5（微信老内核 X5）：不许 => 模板字符串 ?. ?? flatMap .at() let const 展开（2026-10-17：整文件扫，不只顺路那一块；修掉了两处 [...NodeList]）
_san = re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"", lambda m: 'S' * len(m.group(0)), re.sub(r'/\*.*?\*/', '', _sj, flags=re.S))
_san = re.sub(r'//[^\n]*', '', _san)
_bad29 = []
for _pat, _what in ((r'=>', '箭头函数'), (r'`', '模板字符串'), (r'\?\.[A-Za-z_\[(]', '?.'), (r'\?\?', '??'), (r'flatMap', 'flatMap'), (r'\.at\(', '.at()'), (r'(?<![\w.$])(?:let|const)\s', 'let/const'), (r'\.\.\.[A-Za-z\[(]', '展开/剩余')):
    if re.search(_pat, _san): _bad29.append(_what)
if _bad29: fails.append(('site.js 用了 ES5 之外的语法（微信老内核会整页脚本报错）', _bad29))

# 30 离线与缓存：sw.js 的缓存名、预存清单、没存过的页面给离线页、第一次安装不刷新；site.js 里“收进行程”存进的是同一个缓存名；offline.html 在站里且有该有的字和入口
_V = re.search(r"const V = '([^']+)'", _sw); _bad30 = []
if not _V: _bad30.append('sw.js 里找不到 const V')
else:
    if f"caches.open('{_V.group(1)}')" not in _sj: _bad30.append(f'site.js 里“收进行程”存缓存用的名字不是 sw.js 的 {_V.group(1)}：存进去的页面 sw 读不到')
for _u in ('/offline.html', '/manifest.webmanifest', '/img/icon-192.png', '/img/icon-512.png', '/img/apple-touch-icon.png', '/img/favicon.svg'):
    if f"'{_u}'" not in _sw.split('self.addEventListener')[0]: _bad30.append(f'sw.js 预存清单缺 {_u}')
if "caches.match('/offline.html')" not in _sw: _bad30.append('sw.js 没存过的页面不给 /offline.html（会悄悄变首页）')
if 'upgrade' not in _sw or 'c.navigate(c.url)' in _sw.split('upgrade ?')[0]: _bad30.append('sw.js 第一次安装也会刷新页面（应只在从旧版升级时刷新）')
if site:
    _off = os.path.join(site, 'offline.html')
    if not os.path.exists(_off): _bad30.append('站里没有 offline.html')
    else:
        _o = open(_off, encoding='utf-8').read()
        for _w in ('还没存到手机里', '回首页', '已存的行程', 'zouni_fav'):
            if _w not in _o: _bad30.append(f'offline.html 里没有“{_w}”')
        if 'href="/"' not in _o: _bad30.append('offline.html 没有回首页的链接')
    for _u in ('/manifest.webmanifest', '/img/icon-192.png', '/img/icon-512.png', '/img/apple-touch-icon.png', '/offline.html'):
        if not os.path.exists(os.path.join(site, _u.lstrip('/'))): _bad30.append(f'预存清单里的 {_u} 在站里不存在')
if _bad30: fails.append(('离线与缓存', _bad30))

# 31 首页体积与数据：首页 HTML ≤ 400KB、“现在去正好”只有 8 张卡的 HTML、home-a.js 在 site.js 前面且 defer、A+B+8 = 全部卡片、每条线路在目录里有链接、sitemap 里的行程都在目录里
if site:
    import gzip as _gz
    _hp = open(os.path.join(site, 'index.html'), encoding='utf-8').read(); _bad31 = []
    if len(_hp.encode('utf-8')) > 400 * 1024: _bad31.append(f'首页 HTML {len(_hp.encode("utf-8")) // 1024}KB > 400KB')
    _now = _hp[_hp.index('id="now"'):]; _now = _now[:_now.index('</section>')]
    if len(re.findall(r'<li data-band=', _now)) != 8: _bad31.append(f'“现在去正好”首屏 HTML 里卡片 {len(re.findall(r"<li data-band=", _now))} 张，应为 8')
    _ia, _isj = _hp.find('/assets/home-a.js'), _hp.find('/assets/site.js')
    if not (0 < _ia < _isj): _bad31.append('home-a.js 没放在 site.js 前面（site.js 读不到数据）')
    if not re.search(r'<script src="/assets/home-a\.js\?v=\w+" defer[^>]*data-b="/assets/home-b\.js\?v=\w+"', _hp): _bad31.append('home-a.js 的 script 标签不对（要 defer，带 data-b 指向 home-b.js）')
    if not re.search(r'<script src="/assets/site\.js\?v=\w+" defer', _hp): _bad31.append('site.js 不是 defer')
    try:
        _A = json.loads(open(os.path.join(site, 'assets', 'home-a.js'), encoding='utf-8').read().split('window.ZHA=')[1].rsplit(';', 1)[0])
        _Bd = json.loads(open(os.path.join(site, 'assets', 'home-b.js'), encoding='utf-8').read().split('window.ZHB=')[1].rsplit(';', 1)[0])
        _cnt = int(re.search(r'<small class="ns">(\d+) 条', _hp).group(1)) - 1      # 2026-10-19：天数键没有“全部”了，总数写在标题行（含封面那一条）
        if len(_A) + 8 != _cnt: _bad31.append(f'A 组 {len(_A)} + 8 ≠ 页面上写的“{_cnt + 1} 条”（减封面）')
        if any(len(r) != 26 for r in _A + _Bd): _bad31.append('A/B 数据行不是 26 列')
        _ids = {r[0] for r in _A + _Bd} | set(re.findall(r'href="/trip/([^/"]+)/"', _now))
        _ap = open(os.path.join(site, 'all', 'index.html'), encoding='utf-8').read() if os.path.exists(os.path.join(site, 'all', 'index.html')) else ''
        _idx = set(re.findall(r'href="/trip/([^/"]+)/"', _ap))
        _miss = [i for i in _ids if i not in _idx]
        if _miss: _bad31.append(f'首页上出现过的 {len(_miss)} 条线路在 /all/ 里没链接：{_miss[:5]}')
    except Exception as _e: _bad31.append(f'读不了 home-a/b.js：{_e}')
    _sm = set(re.findall(r'/trip/([^/<]+)/', open(os.path.join(site, 'sitemap.xml'), encoding='utf-8').read()))
    if '全部线路目录' in _hp or 'allidx' in _hp: _bad31.append('首页上不该再有“全部线路目录”（只留 /all/ 给搜索引擎）')
    _smt = open(os.path.join(site, 'sitemap.xml'), encoding='utf-8').read()
    if '/all/</loc>' not in _smt: _bad31.append('sitemap.xml 里没有 /all/')
    if '/all/' not in open(os.path.join(site, 'llms.txt'), encoding='utf-8').read(): _bad31.append('llms.txt 里没有 /all/')
    _ap = open(os.path.join(site, 'all', 'index.html'), encoding='utf-8').read() if os.path.exists(os.path.join(site, 'all', 'index.html')) else ''
    if not _ap: _bad31.append('没有 /all/index.html')
    elif re.search(r'<meta name="robots"[^>]*noindex', _ap): _bad31.append('/all/ 不该 noindex')
    # 从 trips.json 出发：每条在站里有行程页的线路，/all/ 里都要有链接（缺一条就红）
    _allids = set(re.findall(r'href="/trip/([^/"]+)/"', _ap))
    _tj = json.load(open('data/catalog/trips.json', encoding='utf-8'))['trips']
    _tids = {(t_.get('engineRoute') or (re.match(r'Route\.dc\.html#(\w+)', t_.get('page') or '') or [None, t_['id']])[1]) for t_ in _tj}
    _have = {i for i in _tids if os.path.exists(os.path.join(site, 'trip', i, 'index.html'))}
    if len(_have) < 1000: _bad31.append(f'trips.json 对得上行程页的只有 {len(_have)} 条，判据可能失效')
    if _have - _allids: _bad31.append(f'trips.json 里有 {len(_have - _allids)} 条有行程页的线路不在 /all/：{sorted(_have - _allids)[:5]}')
    _disk = {d_ for d_ in os.listdir(os.path.join(site, 'trip')) if os.path.exists(os.path.join(site, 'trip', d_, 'index.html'))}
    if _disk - _allids: _bad31.append(f'站里有 {len(_disk - _allids)} 个行程页不在 /all/：{sorted(_disk - _allids)[:5]}')
    if _sm - _allids: _bad31.append(f'sitemap 里有 {len(_sm - _allids)} 条线路不在 /all/：{sorted(_sm - _allids)[:5]}')
    if _bad31: fails.append(('首页体积与数据补齐', _bad31))

# 32 「跟谁走」专栏的数据闸（2026-10-17；判据和反向自检都在 tests/follow_data_checks.py）：线路和页面都在、注释的站点名对得上 stop.name、src 不外泄、评价性词表、/follow/ 含全部 follow 线路、注释落到页面上、museum 站带周一提醒挂点；⑥ 缺纪念馆类站点只警告
import subprocess as _sp3
_rf = _sp3.run([sys.executable, 'tests/follow_data_checks.py'] + ([site] if site else []), capture_output=True, text=True, cwd=ROOT)
_fol_out = [l for l in (_rf.stdout + _rf.stderr).splitlines() if l.strip()]
if _rf.returncode != 0: fails.append(('跟谁走数据闸不过（tests/follow_data_checks.py）', _fol_out[:40]))
else:
    for _l in _fol_out:
        if _l.startswith('警告'): print(_l)

# 33 路线地图（2026-10-17；2026-10-18 地图 App 化：样式自托管；行为判据在 tests/map_app_check.py / map_perf.py）：自托管的 maplibre 在站里且和源码一致、进版本指纹；
#    边界 / 国家 / 省级图层在自托管样式里全部 visibility:none、标注 text-field 中文优先（tools/map_assets.py 的规则 + site_src/map/style.json 的结果 + 站里的副本）；署名文字、固定的样式地址在；
#    routemap.js 全文件 ES5；点开才取（首页 / 行程页 HTML 里没有它们）；断网存进缓存的清单里有 routemap.js；不用要 Key 的服务；整屏图层不用合作手势、中文字形走系统字体；sw.js 的“先用缓存”只限带指纹的地图文件
_bad33 = []
_rm = open('site_src/routemap.js', encoding='utf-8').read()
for _w in ('maplibre-gl.js', 'maplibre-gl.css', 'LICENSE.txt'):
    if not os.path.exists('site_src/maplibre/' + _w): _bad33.append(f'site_src/maplibre/{_w} 不存在')
if os.path.exists('site_src/maplibre/LICENSE.txt') and 'BSD' not in open('site_src/maplibre/LICENSE.txt', encoding='utf-8').read(): _bad33.append('maplibre 的许可证文件不是 BSD（没带对）')
_ma = open('tools/map_assets.py', encoding='utf-8').read()
_mh = re.search(r"HIDE_RE = re\.compile\(r'([^']+)'\)", _ma)
if not _mh or not all(w_ in _mh.group(1) for w_ in ('boundary', 'country', 'state', 'disputed')): _bad33.append('tools/map_assets.py 里没有隐藏 boundary|country|state|disputed 图层的 HIDE_RE')
if not re.search(r"if HIDE_RE\.search\(l\['id'\]\):\s*l\.setdefault\('layout', \{\}\)\['visibility'\] = 'none'", _ma): _bad33.append('tools/map_assets.py 的 tune 没有把边界 / 国家 / 省级图层设成 visibility none')
if "['get', 'name:zh-Hans']" not in _ma or "ZH_TEXT = ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh'], ['get', 'name:ja'], ['get', 'name:latin'], ['get', 'name']]" not in _ma: _bad33.append('tools/map_assets.py 的标注没改成中文优先（name:zh-Hans → name:zh → name:ja → name:latin → name：国外地名用拉丁字母，不留泰文 / 阿拉伯文 / 韩文给中国用户）')
_mh2 = re.search(r"var HIDE_RE = /([^/]+)/;", _rm)
if not _mh2 or not all(w_ in _mh2.group(1) for w_ in ('boundary', 'country', 'state', 'disputed')): _bad33.append('routemap.js 里没有隐藏 boundary|country|state|disputed 图层的 HIDE_RE（运行时核对样式用）')
if 'styleOk(j)' not in _rm: _bad33.append('routemap.js 拿到样式后没有核对“边界图层都隐藏了”（styleOk）：样式被换成没隐藏的也会照画')
def _chk_style(path_, what_):
    if not os.path.exists(path_): _bad33.append(f'{what_} 不存在'); return
    st_ = json.load(open(path_, encoding='utf-8')); hid_ = 0
    for l_ in st_['layers']:
        if re.search(r'boundary|country|state|disputed', l_['id']):
            if (l_.get('layout') or {}).get('visibility') == 'none': hid_ += 1
            else: _bad33.append(f'{what_} 里图层 {l_["id"]} 没隐藏（边界 / 国家 / 省级）')
        elif l_.get('type') == 'symbol' and (l_.get('layout') or {}).get('text-field') and 'shield' not in l_['id']:
            if (l_['layout']['text-field'] or [None])[:2] != ['coalesce', ['get', 'name:zh-Hans']]: _bad33.append(f'{what_} 里标注图层 {l_["id"]} 的 text-field 不是中文优先')
            elif ['get', 'name:latin'] not in l_['layout']['text-field'] or l_['layout']['text-field'].index(['get', 'name:latin']) > l_['layout']['text-field'].index(['get', 'name']): _bad33.append(f'{what_} 里标注图层 {l_["id"]} 的 text-field 没有“拉丁字母兜底”（name:latin 要排在本地名 name 前面：国外地名中国用户读不了本地文字）')
    if hid_ < 4: _bad33.append(f'{what_} 里只有 {hid_} 个边界类图层被隐藏（线上有 8 个；少于 4 个说明规则没命中）')
    if st_.get('sprite', '').startswith('http') or st_.get('glyphs', '').startswith('http'): _bad33.append(f'{what_} 的 sprite / glyphs 还指向外站（应自托管）')
_chk_style('site_src/map/style.json', 'site_src/map/style.json')
if site: _chk_style(os.path.join(site, 'assets', 'map', 'style.json'), '站里的 assets/map/style.json')
for _w in ('OpenFreeMap', 'OpenMapTiles', 'OpenStreetMap', 'Data from'):
    if _w not in _rm: _bad33.append(f'routemap.js 里没有署名文字“{_w}”')
if "var STYLE_URL = '/assets/map/style.json';" not in _rm: _bad33.append('样式地址不是自托管的 /assets/map/style.json')
if re.search(r'[?&](key|api_?key|access_?token|token|apikey)=', _rm, re.I): _bad33.append('routemap.js 里有带 Key / token 的地址（不许用要 Key 的服务）')
if re.search(r'mapbox|maptiler|stadia|amap\.com/maps|webapi\.amap|api\.map\.baidu|googleapis\.com/maps', _rm, re.I): _bad33.append('routemap.js 引用了要 Key / 付费的地图服务')
_san33 = re.sub(r"'(?:[^'\\\n]|\\.)*'|\"(?:[^\"\\\n]|\\.)*\"", lambda m_: 'S' * len(m_.group(0)), re.sub(r'/\*.*?\*/', '', _rm, flags=re.S))
_san33 = re.sub(r'(?<![:\w/"\'])//[^\n]*', '', _san33)
_es33 = [w_ for pat_, w_ in ((r'=>', '箭头函数'), (r'`', '模板字符串'), (r'\?\.[A-Za-z_\[(]', '?.'), (r'\?\?', '??'), (r'flatMap', 'flatMap'), (r'\.at\(', '.at()'), (r'(?<![\w.$])(?:let|const)\s', 'let/const'), (r'\.\.\.[A-Za-z\[(]', '展开/剩余')) if re.search(pat_, _san33)]
if _es33: _bad33.append('routemap.js 用了 ES5 之外的语法：' + '、'.join(_es33))
if 'cooperativeGestures: false' not in _rm or 'CooperativeGesturesHandler' in _rm: _bad33.append('routemap.js 的整屏地图必须 cooperativeGestures: false（整屏图层里单指就该能拖，不要“用两根手指移动地图”的提示）')
if 'localIdeographFontFamily' not in _rm: _bad33.append('routemap.js 没用 localIdeographFontFamily（中文字形会去下载 glyph 包）')
if "'/assets/routemap.js'+q" not in _sj: _bad33.append("site.js 的“收进行程”存缓存清单里没有 /assets/routemap.js（断网看不了每天的示意图）")
if 'window.zGcj=npGcj' not in _sj or 'window.zNpMap=' not in _sj or 'window.ZRM_HOST=' not in _sj: _bad33.append('site.js 没有给路线地图留的出口（zGcj / zNpMap / ZRM_HOST）：导航会退回不转坐标、灰点没有')
_cs33 = open('site_src/site.css', encoding='utf-8').read()
if not re.search(r'\.rm\.rm-fs\{[^}]*touch-action:none', _cs33) or not re.search(r'\.rm\.rm-fs\{[^}]*overscroll-behavior:contain', _cs33): _bad33.append('site.css 的 .rm.rm-fs 没有 touch-action:none + overscroll-behavior:contain（整屏层里手势会漏给页面）')
if not re.search(r'body\.rm-lock\{position:fixed', _cs33): _bad33.append('site.css 没有 body.rm-lock{position:fixed…}（整屏层打开时页面还能滚）')
_swp = _sw.split('self.addEventListener')
if not re.search(r"const TILE_MAX = (\d+);", _sw) or int(re.search(r"const TILE_MAX = (\d+);", _sw).group(1)) > 500: _bad33.append('sw.js 瓦片缓存条数上限没写或超过 500')
if "u.search.indexOf('v=') >= 0 && /\\/assets\\/(maplibre\\/|routemap\\.js|map\\/style\\.json)/.test(u.pathname)" not in _sw: _bad33.append('sw.js “先用缓存”的范围不是“带 ?v= 指纹的 maplibre / routemap.js / 样式”（范围放宽会让别的 .js 变成永远旧的）')
if site:
    for _u in ('assets/routemap.js', 'assets/maplibre/maplibre-gl.js', 'assets/maplibre/maplibre-gl.css', 'assets/maplibre/LICENSE.txt', 'assets/map/style.json', 'assets/map/sprite/ofm.json', 'assets/map/sprite/ofm@2x.png', 'assets/map/fonts/Noto Sans Regular/0-255.pbf'):
        _sp_ = os.path.join(site, _u); _src_ = 'site_src/' + _u.replace('assets/', '', 1)
        if not os.path.exists(_sp_): _bad33.append(f'站里没有 {_u}')
        elif open(_sp_, 'rb').read() != open(_src_, 'rb').read(): _bad33.append(f'站里的 {_u} 和源码不一样（建站后改过源码，没重建）')
    import hashlib as _hl3
    _v_old = _hl3.md5((open('site_src/site.css', encoding='utf-8').read() + open('site_src/site.js', encoding='utf-8').read() + open('site_src/np_model.js', encoding='utf-8').read()).encode()).hexdigest()[:8]
    _pg33 = open(os.path.join(site, 'trip', 'xa3', 'index.html'), encoding='utf-8').read()
    if f'/assets/site.js?v={_v_old}' in _pg33: _bad33.append('版本指纹没带上 routemap.js / maplibre / 样式（改了它们手机上的旧缓存不会失效）')
    for _pp in ('trip/xa3/index.html', 'trip/xb96a/index.html', 'index.html', 'where/index.html'):
        if os.path.exists(os.path.join(site, _pp)):
            _t_ = open(os.path.join(site, _pp), encoding='utf-8').read()
            if re.search(r'maplibre|routemap|openfreemap', _t_, re.I): _bad33.append(f'{_pp} 的 HTML 里出现了 maplibre / routemap / openfreemap（应该只在点开后才取；空闲预取由 site.js 在 4g / wifi 且非省流量时才发）')
if _bad33: fails.append(('路线地图：资源 / 合规处理 / 署名 / ES5 / 点开才取', _bad33))

# 34 行程标题（2026-10-19，tests/title_check.py 有 --selftest 反向自检）：不得以“N天(…)”开头、同一目的地下 label 不重名
import importlib.util as _iu
_sp = _iu.spec_from_file_location('title_check', os.path.join(ROOT, 'tests', 'title_check.py')); _tc = _iu.module_from_spec(_sp); _sp.loader.exec_module(_tc)
_bad34 = _tc.check(*_tc.load())
if _bad34: fails.append(('行程标题（N天(…) 开头 / label 重名）', _bad34))

# 35 站名带专名（某某门/寺/塔/馆/庙/宫/殿/祠/观/陵/楼/阁/庵）时，q 必须含这个专名的区分部分（2026-10-19）：
#    “西安城墙 · 永宁门” 的 q 写成泛称“西安城墙”，地图标点就落在城墙别处。存量见 data/geo/q_term_baseline.json（已审、新增不许）；
#    判据和自检在 tools/audit_pois.py（term_violations / selftest；自检每次都跑：好稿不红、注入缺陷红）
_sp = _iu.spec_from_file_location('audit_pois', os.path.join(ROOT, 'tools', 'audit_pois.py')); _ap = _iu.module_from_spec(_sp); _sp.loader.exec_module(_ap)
_bad35 = ['闸自检失败：' + e for e in _ap.selftest()]
_base35 = set(json.load(open(_ap.BASELINE, encoding='utf-8'))['keys']) if os.path.exists(_ap.BASELINE) else set()
_bad35 += _ap.term_violations(I, _base35)
if _bad35: fails.append(('站名专名不在 q 里（q 只写了泛称，坐标会落到别处）', _bad35))

# 36 时长文字不许颠倒（2026-10-20）：“自驾约 30 分 3 小时”（应是“3 小时 30 分”）——编译器解析 via 里“3 小时 30 分”时只认“分钟”，30 分丢在文字里、小时又补在后面；
#    页面每一行、地图卡片的“从出发点 / 距上一站”都带着它。判据：任何页面里不得出现“N 分 M 小时”（要建好的站）
_bad36 = []
if site:
    for _f36 in sorted(glob.glob(os.path.join(site, 'trip', '*', 'index.html'))):
        _m36 = re.search(r'[^<>]{0,10}\d+ 分 \d+ 小时', open(_f36, encoding='utf-8').read())
        if _m36: _bad36.append(os.path.basename(os.path.dirname(_f36)) + '：' + _m36.group(0).strip())
if _bad36: fails.append(('时长文字颠倒（“N 分 M 小时”，应是“M 小时 N 分”）', _bad36))

if fails:
    for title, items in fails:
        print(f'✗ {title}：{len(items)} 处')
        for x in items[:30]: print('   ', x)
    sys.exit(1)
print('数据和页面检查全部通过' + ('' if site else '（没给站目录，页面项未查）'))
