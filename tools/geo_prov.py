"""城市 → 省（国内）。没有现成的省份字段，从两处推：
 1) data/geo/pois.json 里“城市|城市”的在线地名命中串（“…, 河北省, 中国”）；
 2) 单省短线路（≤10 天、dest 是省级目的地）里出现过的城市，按票数归省；
 3) 都没有：取最近的已知城市（≤150 公里）的省。
用途：餐食按所在省过滤（compile_itineraries.py）、tests/w1_checks.py 扫全站餐食与所在省不符。"""
import json, math, os, re, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PR = re.compile(r'(?:^|, )([^,]{2,8}(?:省|自治区))(?:, \d+)?(?:, 中国|$)')
_MU = re.compile(r'(?:^|, )(北京市|上海市|天津市|重庆市)(?:, \d+)?(?:, 中国|$)')
_STRIP = ('壮族自治区', '回族自治区', '维吾尔自治区', '自治区', '省', '市')
_C = {}


def _norm(p):
    for s in _STRIP:
        if p.endswith(s): return p[:-len(s)]
    return p


def _km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def _load():
    if _C: return
    GEO = json.load(open(os.path.join(ROOT, 'data/geo/pois.json'), encoding='utf-8'))
    IT = json.load(open(os.path.join(ROOT, 'data/itineraries.json'), encoding='utf-8'))['itineraries']
    DM = {d['id']: d['name'] for d in json.load(open(os.path.join(ROOT, 'data/destinations.json'), encoding='utf-8'))['domestic']}
    city_prov = {}
    votes = collections.defaultdict(collections.Counter)
    for rid, it in IT.items():
        if it['dest'] in DM and len(it['days']) <= 10 and not it.get('history') and not rid.startswith('h') and it['dest'] not in ('hongkong', 'macau', 'taiwan'):
            for c in {it['city']} | {d.get('city') for d in it['days'] if d.get('city')}: votes[c][DM[it['dest']]] += 1
    for c, v in votes.items(): city_prov[c] = v.most_common(1)[0][0]
    for k, v in GEO.items():
        if '|' not in k or '#' in k or not v: continue
        c, q = k.split('|', 1)
        if c != q: continue
        m = _PR.search(v.get('hit') or '') or _MU.search(v.get('hit') or '')
        if m: city_prov[c] = _norm(m.group(1))
    pts = [(GEO[c + '|' + c]['lat'], GEO[c + '|' + c]['lng'], p) for c, p in city_prov.items() if GEO.get(c + '|' + c) and GEO[c + '|' + c].get('lat') is not None]
    _C.update(geo=GEO, city=city_prov, pts=pts)


def prov_of(city, pt=None):
    """省名（“河北”“新疆”），不知道返回 None"""
    _load()
    if city in _C['city']: return _C['city'][city]
    if pt is None:
        g = _C['geo'].get(city + '|' + city)
        if g and g.get('lat') is not None: pt = (g['lat'], g['lng'])
    if pt is None: return None
    best = min(((_km(pt, (a, b)), p) for a, b, p in _C['pts']), default=None)
    return best[1] if best and best[0] <= 150 else None


def dish_provs():
    """{菜名头: {出自的省或国家}}：PROV_FOOD + 节目里拍过的 REGION_FOOD + 国内目的地的 eat。compile_itineraries.py 里有同口径的 DISH_PROV，tests/w1_checks.py 的餐食闸用这一份独立再算一遍"""
    cat = os.path.join(ROOT, 'data/catalog')
    dn = lambda c: re.sub(r'[（(].*$', '', c.split('、')[0]).strip()
    out = collections.defaultdict(set)
    pf = json.load(open(os.path.join(cat, 'prov_food.json'), encoding='utf-8'))
    for pv, ds in pf.items():
        for d in ds: out[dn(d)].add(pv)
    for f in ('shejian', 'fengwei', 'docs_more', 'docs_more2', 'docs_travel'):
        p = os.path.join(cat, f + '.json')
        if not os.path.exists(p): continue
        for x in json.load(open(p, encoding='utf-8')):
            if (x.get('show') or '舌尖上的中国') in ('舌尖上的中国', '风味人间', '风味原产地', '人生一串', '宵夜江湖', '老广的味道', '街头美食') and x.get('food') and x['food'] != x.get('place') and len(x['food']) <= 12 and not any(w in x['food'] for w in ('节', '（', '(', '季', '之')):
                out[dn(x['food'])].add(x['prov'])
    dm = {d['id']: d['name'] for d in json.load(open(os.path.join(ROOT, 'data/destinations.json'), encoding='utf-8'))['domestic']}
    for x in json.load(open(os.path.join(cat, 'destinations.json'), encoding='utf-8'))['destinations']:
        if x['id'] in dm and x['id'] not in ('hongkong', 'macau', 'taiwan'):
            for d in x.get('eat') or []: out[dn(d)].add(dm[x['id']])
    return out


# 全国都有的泛称菜（“海鲜”“鱼丸”“凉皮”“小笼包”…）：不按省判错。餐食闸和编译器都用这一张表
NATIONWIDE = {'海鲜', '鱼丸', '火腿', '小笼包', '臭豆腐', '凉皮', '烧麦', '包子', '饺子', '面条', '火锅', '烧烤', '米粉', '米线', '馄饨', '卤味', '炒饭', '粥', '汤面', '馒头', '煎饼', '烤鱼', '羊肉串', '拉面', '凉面', '肉夹馍'}
