# 用 Photon（komoot）二次核对 Nominatim 没查到的景点坐标。
# 用法：python3 tools/verify_geo_photon.py query   → 查询，结果落盘 build/photon_cache.json（可续跑）
#       python3 tools/verify_geo_photon.py apply   → 命中名字含景点核心词、离现坐标 8–80 公里的，改 data/geo/pois.json；其余只统计
import json, math, os, re, subprocess, sys, time, urllib.parse
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
G = json.load(open('data/geo/pois.json', encoding='utf-8'))
CP = 'build/photon_cache.json'
CACHES = [json.load(open(p, encoding='utf-8')) for p in ('build/nominatim_check.json', 'build/nominatim_check_f.json') if os.path.exists(p)]
AUTO = set()
for f in os.listdir('data/auto_routes'):
    for r in json.load(open('data/auto_routes/' + f, encoding='utf-8')): AUTO.add(r['id'])


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def unresolved():
    out = []
    for rid in sorted(AUTO):
        r = IT.get(rid)
        if not r: continue
        for d in r['days']:
            c = d.get('city') or r['city']
            for s in d['stops']:
                q = s.get('q') or s['name']
                if any(C.get(q) for C in CACHES): continue
                g = G.get(c + '|' + q)
                if g and g.get('lat'): out.append((rid, c, s['name'], q, (g['lat'], g['lng'])))
    return out


def photon(q, near):
    u = 'https://photon.komoot.io/api/?' + urllib.parse.urlencode({'q': q, 'limit': 6, 'lat': near[0], 'lon': near[1]})
    for _ in range(2):
        o = subprocess.run(['curl', '-s', '-m', '25', '-A', 'zouni-travel-data/1.0 (zouni.app)', u], capture_output=True, text=True)
        time.sleep(0.6)
        try:
            return [{'lat': f['geometry']['coordinates'][1], 'lng': f['geometry']['coordinates'][0], 'name': (f['properties'].get('name') or '') + ' ' + (f['properties'].get('city') or '')} for f in json.loads(o.stdout)['features']]
        except Exception: time.sleep(3)
    return None


def core(n):
    n = re.sub(r'[（(].*?[)）]', '', n)
    n = re.sub(r'(景区|风景区|旅游区|国家公园|博物馆|遗址|古镇|古城|公园|寺|山|湖|村|街)$', '', n)
    return n[:4] if len(n) > 4 else n


if sys.argv[1] == 'query':
    P = json.load(open(CP, encoding='utf-8')) if os.path.exists(CP) else {}
    todo = [x for x in unresolved() if (x[1] + '|' + x[3]) not in P]
    print('待查', len(todo), flush=True)
    for i, (rid, c, name, q, cur) in enumerate(todo):
        P[c + '|' + q] = photon(q if c in q else c + ' ' + q, cur)
        if i % 40 == 0: json.dump(P, open(CP, 'w', encoding='utf-8'), ensure_ascii=False); print(i, '/', len(todo), flush=True)
    json.dump(P, open(CP, 'w', encoding='utf-8'), ensure_ascii=False); print('完成')

if sys.argv[1] == 'apply':
    P = json.load(open(CP, encoding='utf-8')); ok = ch = fl = nores = 0; rows = []
    for rid, c, name, q, cur in unresolved():
        res = P.get(c + '|' + q)
        if not res: nores += 1; continue
        best = min(res, key=lambda x: km(cur, (x['lat'], x['lng']))); d = km(cur, (best['lat'], best['lng']))
        if d <= 8: ok += 1; continue
        named = [x for x in res if core(name) and core(name) in x['name'] and km(cur, (x['lat'], x['lng'])) <= 80]
        if named and d <= 80:
            b = min(named, key=lambda x: km(cur, (x['lat'], x['lng'])))
            G[c + '|' + q] = {'lat': b['lat'], 'lng': b['lng'], 'hit': 'Photon 核对 ' + b['name'].strip(), 'q': q, 'src': 'photon'}; ch += 1; rows.append((rid, name, round(km(cur, (b['lat'], b['lng']))), b['name'].strip()))
        else: fl += 1
    json.dump(G, open('data/geo/pois.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('一致', ok, '| 改坐标', ch, '| 存疑未改', fl, '| 仍无结果', nores)
    json.dump(rows, open('build/photon_changed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
