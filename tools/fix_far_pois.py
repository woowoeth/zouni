# 找出“作者没写交通方式、却被算成两小时以上包车”的站点（多半坐标落到了同名的别处），在当天城市附近重新查一次
import json, re, math, time, urllib.request, urllib.parse
R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', open('build/routes.js', encoding='utf-8').read()).group(1))
IT = json.load(open('data/itineraries.json'))['itineraries']
G = json.load(open('data/geo/pois.json'))
CC = {x['id']: x['cc'] for x in json.load(open('data/destinations.json'))['asia']}
UA = {'User-Agent': 'zouni-fix/1.0 (zouni.app)'}
def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
def nom(q, cc, center, box=0.8):
    vb = f'{center[1]-box},{center[0]+box},{center[1]+box},{center[0]-box}'
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 5, 'countrycodes': cc, 'viewbox': vb, 'bounded': 1, 'accept-language': 'zh'})
    try: r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    except Exception: r = []
    time.sleep(1.1); return r
fixed = []; approx = []
for rid, r in R.items():
    if not r.get('compiled') or rid not in IT: continue
    it = IT[rid]; cc = CC.get(it['dest'], 'cn')
    for di, d in enumerate(r['days']):
        idays = it['days'][di]; dcity = idays.get('city', it['city'])
        cg = G.get(dcity + '|' + dcity)
        if not cg: continue
        center = (cg['lat'], cg['lng'])
        for w in d['rows']:
            if w['type'] != 'dep': continue
            m = re.search(r'包车约 (\d+) 小时', w.get('how', ''))
            if not (m and int(m.group(1)) >= 2 and '公里' in w.get('how', '')): continue
            st = next((s for s in idays['stops'] if (s['name'] == w['to'] or s['name'].startswith(w['to']) or w['to'] in s['name'])), None)
            if not st or st.get('via'): continue          # 作者写了交通方式的是真长途，不动
            key = dcity + '|' + (st.get('q') or st['name'])
            g = G.get(key)
            if g and km((g['lat'], g['lng']), center) <= 80: continue
            hit = None
            for q in (st.get('q'), st['name'], dcity + ' ' + st['name']):
                for x in nom(q, cc, center):
                    pt = (float(x['lat']), float(x['lon']))
                    if km(pt, center) <= 80: hit = pt; break
                if hit: break
            if hit:
                G[key] = {'lat': hit[0], 'lng': hit[1], 'hit': '城市附近重查', 'q': st.get('q') or st['name'], 'src': 'refix'}; fixed.append(f'{rid}/{di+1} {st["name"]}')
            else:
                G[key] = {'lat': center[0], 'lng': center[1], 'hit': '城市中心（近似）', 'q': st.get('q') or st['name'], 'src': 'refix-approx'}; approx.append(f'{rid}/{di+1} {st["name"]}')
json.dump(G, open('data/geo/pois.json', 'w'), ensure_ascii=False, indent=1)
print('在城市附近重新查到', len(fixed), fixed[:20]); print('查不到、先用城市中心（近似）', len(approx), approx[:20])
