# 给价格“另算”的线路估参考价（每人，两人同行，含往返大交通），写回 data/catalog/trips.json
# 五项：往返大交通（按离最近的大城市的距离）+ 住（每人每晚，两人一间）+ 吃 + 门票 + 当地交通（打车 / 包车）
import json, re, math

T = json.load(open('data/catalog/trips.json'))
IT = json.load(open('data/itineraries.json'))['itineraries']
CAT = {d['id']: d for d in json.load(open('data/catalog/destinations.json'))['destinations']}
G = json.load(open('data/geo/pois.json'))
HUBS = {'北京': (39.9, 116.4), '上海': (31.23, 121.47), '广州': (23.13, 113.26), '成都': (30.66, 104.06), '西安': (34.34, 108.94), '昆明': (25.04, 102.71), '乌鲁木齐': (43.83, 87.62), '哈尔滨': (45.8, 126.53)}
BIG = {'北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安', '厦门', '苏州', '青岛', '天津', '长沙', '香港', '澳门'}
ASIA_AIR = {'japan': (2200, 4000), 'korea': (1800, 3500), 'thailand': (1800, 3200), 'vietnam': (1600, 3000), 'singapore': (2000, 3500), 'malaysia': (1800, 3200),
            'indonesia': (2500, 4500), 'cambodia': (2000, 3500), 'laos': (1800, 3200), 'philippines': (1800, 3500), 'nepal': (3000, 5000), 'bhutan': (5000, 8000),
            'india': (3000, 5500), 'maldives': (4000, 7000), 'uzbekistan': (3500, 6000), 'turkey': (4500, 7500), 'uae': (3500, 6000), 'mongolia': (2500, 4500)}
ASIA_STAY = {'japan': (400, 700), 'korea': (300, 550), 'singapore': (450, 750), 'maldives': (800, 2000), 'bhutan': (600, 1200), 'uae': (450, 800), 'turkey': (300, 550)}
ASIA_FOOD = {'japan': (250, 400), 'korea': (200, 350), 'singapore': (200, 350), 'uae': (250, 400), 'maldives': (300, 600)}


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def r100(x): return int(round(x / 100.0)) * 100


done = 0
for t in T['trips']:
    p = t.get('price') or {}
    if p.get('lo'): continue
    it = IT.get(t['id'])
    if not it: continue
    d = CAT[it['dest']]; n = len(it['days']); nights = n - 1
    city = it['city']
    first = next((G.get((x.get('city') or city) + '|' + (s.get('q') or s['name'])) for x in it['days'] for s in x['stops'] if G.get((x.get('city') or city) + '|' + (s.get('q') or s['name']))), None)
    pt = (first['lat'], first['lng']) if first else (d['base']['lat'], d['base']['lng'])
    if d['scope'] == 'asia':
        air = ASIA_AIR.get(d['id'], (2500, 4500)); stay = ASIA_STAY.get(d['id'], (180, 380)); food = ASIA_FOOD.get(d['id'], (120, 220))
    else:
        dist = min(km(pt, h) for h in HUBS.values())
        air = (200, 500) if dist < 300 else (500, 1200) if dist < 1000 else (1000, 2000) if dist < 2000 else (1500, 3000)
        high = max(x.get('elev') or 0 for x in it['days']) >= 3000
        stay = (250, 450) if city in BIG else (180, 380) if high else (150, 320)
        food = (100, 200) if city in BIG else (80, 160)
    sees = sum(1 for x in it['days'] for s in x['stops'] if s['type'] in ('sight', 'museum', 'park', 'night'))
    tix = (sees * 30, sees * 90)
    bao = sum(1 for x in it['days'] if any('包车' in (s.get('via') or '') for s in x['stops']))
    local = (bao * 300 + (n - bao) * 40, bao * 500 + (n - bao) * 90)
    lo = air[0] + stay[0] * nights + food[0] * n + tix[0] + local[0]
    hi = air[1] + stay[1] * nights + food[1] * n + tix[1] + local[1]
    t['price'] = {'lo': r100(lo), 'hi': r100(hi), 'currency': 'CNY', 'basis': '参考价：两人同行，含往返大交通（按离最近的大城市估）、住、吃、门票、当地交通'}
    done += 1
json.dump(T, open('data/catalog/trips.json', 'w'), ensure_ascii=False, indent=1)
left = sum(1 for t in T['trips'] if not (t.get('price') or {}).get('lo'))
print('估价', done, '条；仍没价的', left, '条')
