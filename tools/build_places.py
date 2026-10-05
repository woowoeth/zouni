# 城市表 + 线路里的景点 + 目的地表 + 口碑补充 → data/places.json（结构见 data/schema/place.schema.json）
import json, glob, re, urllib.parse, hashlib
CITYDEST = {'成都':'sichuan','乌鲁木齐':'xinjiang','伊宁':'xinjiang','香格里拉':'yunnan','那拉提':'xinjiang','布尔津':'xinjiang','禾木':'xinjiang','喀纳斯':'xinjiang',
            '上海':'shanghai','杭州':'zhejiang','苏州':'jiangsu','额济纳':'neimenggu','九寨沟':'sichuan','张家界市':'hunan','武陵源':'hunan','香港':'hongkong','大阪':'japan'}
ROUTEDEST = {'cd3':'sichuan','xj10':'xinjiang','nm4':'neimenggu','jz4':'sichuan','sh3':'shanghai','hz3':'zhejiang','sz3':'jiangsu','zjj4':'hunan','hk2':'hongkong','kansai4':'japan'}
D = json.load(open('data/destinations.json')); DEST = {x['id']: x for x in D['domestic'] + D['asia']}
CC = {x['id']: x.get('cc', 'cn').upper() for x in D['asia']}; CC.update({'hongkong': 'HK', 'macau': 'MO', 'taiwan': 'TW'})
DPID = {'上海': 1, '北京': 2, '杭州': 3}
CITYFIX = {'佐敦': '香港', '武陵源': '张家界', '张家界市': '张家界', '西湖': '杭州', '外滩': '上海', '平江路': '苏州', '关西机场': '大阪'}          # 已核实的点评城市 id；其余用点评的搜索页带城市名
EN = json.load(open('data/places_enrich.json'))['places']
def dianping(city, kw):
    city = CITYFIX.get(city, city)
    if city in DPID: return 'https://www.dianping.com/search/keyword/%d/0_%s' % (DPID[city], urllib.parse.quote(kw))
    return 'https://www.dianping.com/ai-search?keyword=' + urllib.parse.quote(((city or '') + ' ' + kw).strip())
def mapurl(country, city, kw):
    city = CITYFIX.get(city, city)
    if country in ('CN', 'HK', 'MO'): return 'https://uri.amap.com/search?keyword=' + urllib.parse.quote(kw) + ('&city=' + urllib.parse.quote(city) if city else '')
    return 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(kw)
def enrich_of(name, typ):
    if name in EN: return EN[name]
    if typ not in ('food', 'stay'): return None
    for k, v in EN.items():   # 店名写法不同（如带不带分店名）时，按店名主体对上
        main = k.split('（')[0]
        if len(main) >= 3 and main in name: return v
    return None
def pid(dest, city, name):
    return dest + '-' + hashlib.md5(((city or '') + name).encode()).hexdigest()[:8]
P = {}
def put(rec):
    k = rec['id']
    if k in P:   # 已有：合并来源和出现的线路
        for f in ('sources', 'usedIn'):
            P[k][f] = sorted(set(P[k].get(f, []) + rec.get(f, [])))
        return P[k]
    P[k] = rec; return rec
def base(name, typ, dest, city, kw=None, src=None):
    country = CC.get(dest, 'CN'); kw = kw or name
    r = {'id': pid(dest, city, name), 'name': name, 'type': typ, 'dest': dest, 'country': country, 'city': city, 'area': None, 'price': None, 'tier': None,
         'dishes': [], 'hours': None, 'slots': [], 'rating': None, 'rank': None, 'signature': [], 'highlights': [],
         'links': {'dianping': dianping(city if country in ('CN', 'HK', 'MO', 'JP') else '', kw), 'map': mapurl(country, city, kw)}, 'usedIn': [], 'sources': [src] if src else [], 'verified': '2026-10-04' if src else None}
    e = enrich_of(name, typ)
    if e:
        r.update({k: e[k] for k in ('rating', 'rank', 'signature', 'highlights') if k in e})
        if e.get('rating'): r['sources'] = sorted(set(r['sources'] + [e['rating']['source']]))
    return r
# 1 城市表
for f in glob.glob('data/cities/*.json'):
    c = json.load(open(f)); city = c['city']; dest = CITYDEST.get(city)
    if not dest: continue
    for x in c.get('food', []):
        if x.get('place', '').startswith('附近') or x.get('dish') == '随意' and not x.get('poi'): continue
        r = base(x['place'], 'food', dest, city, x.get('poi') or x['place'], x.get('src'))
        cur = 'JPY' if dest == 'japan' else 'CNY'
        r['price'] = {'amount': x.get('price') or None, 'currency': cur, 'per': 'person', 'text': x.get('priceText')}
        r['dishes'] = [d.strip() for d in re.split('[、，,]', re.sub(r'（.*?）', '', x.get('dish', ''))) if d.strip()]
        if x.get('close'): r['hours'] = {'close': x['close']}
        r['slots'] = x.get('slots', []); put(r)
    for tier, v in (c.get('stay') or {}).items():
        if not v: continue
        r = base(v['name'], 'stay', dest, city, v['name'], v.get('src')); r['tier'] = tier
        r['price'] = {'amount': None, 'currency': 'CNY', 'per': 'night', 'text': v.get('price')} if v.get('price') else None
        if v.get('sell') and not r['highlights']: r['highlights'] = [v['sell']]
        r['links']['ctrip'] = 'https://hotels.ctrip.com/hotels/list?keyword=' + urllib.parse.quote(v['name']); put(r)
    for x in c.get('fun', []):
        r = base(x['name'], 'fun', dest, city, x.get('poi') or x['name'], x.get('src')); r['highlights'] = [x.get('detail', '')] if x.get('detail') else []; put(r)
# 2 线路里的景点（读生成好的 routes.js）
js = open('build/routes.js', encoding='utf-8').read(); R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', js).group(1))
for rid, m in R.items():
    dest = ROUTEDEST[rid]
    for d in m['days']:
        city = d.get('navCity') or d.get('city')
        for w in d['rows']:
            if w['type'] == 'see' and w.get('poi') and not re.search(r'提车|验车|还车|放行李|回程|住处', w['name']):
                r = base(re.split(r'\s*·\s*', w['name'])[0], 'sight', dest, city, w['poi'], '引擎线路'); r['usedIn'] = [rid]
                mm = re.search(r'¥(\d+)', w.get('d', ''))
                if mm: r['price'] = {'amount': int(mm.group(1)), 'currency': 'JPY' if dest == 'japan' else 'CNY', 'per': 'person', 'text': '门票'}
                put(r)
            if w['type'] in ('eat', 'fun') and w.get('poi'):
                nm = w.get('place') if w['type'] == 'eat' else w['name']
                for k, v in P.items():
                    if v['name'] == nm: v['usedIn'] = sorted(set(v['usedIn'] + [rid]))
# 3 目的地表里的“看什么、吃什么”
for did, x in DEST.items():
    for s in x['see']: put(base(s, 'sight', did, x['base'], s, 'destinations.json'))
    for s in x['eat']: put(base(s, 'dish', did, x['base'], x['base'] + ' ' + s, 'destinations.json'))
out = sorted(P.values(), key=lambda r: (r['dest'], r['type'], r['name']))
json.dump({'schema': 'data/schema/place.schema.json', 'count': len(out), 'places': out}, open('data/places.json', 'w'), ensure_ascii=False, indent=1)
from collections import Counter
print('地点', len(out), dict(Counter(r['type'] for r in out)), '有评分', sum(1 for r in out if r['rating']), '有口碑', sum(1 for r in out if r['highlights'] or r['signature']), '目的地', len(set(r['dest'] for r in out)))
# 校验必填
bad = [r['id'] for r in out if not (r['name'] and r['type'] and r['dest'] and r['links'].get('dianping'))]
print('缺必填', len(bad))
