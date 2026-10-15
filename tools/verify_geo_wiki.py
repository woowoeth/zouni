# 用中文维基百科的坐标核对景点坐标（Nominatim/Photon 没覆盖到的名胜多半有词条，词条坐标比子代理凭记忆写的可靠）。
# 用法：python3 tools/verify_geo_wiki.py query [前缀]   → 查询并落盘 build/wiki_cache.json（可续跑）
#       python3 tools/verify_geo_wiki.py apply         → 词条标题和景点名对得上、离现坐标 5–150 公里的改 data/geo/pois.json；≤5 公里算已核对
import json, math, os, re, subprocess, sys, time, urllib.parse
import opencc
T2S = opencc.OpenCC('t2s').convert      # 维基词条标题有繁体
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
G = json.load(open('data/geo/pois.json', encoding='utf-8'))
CP = 'build/wiki_cache.json'
AUTO = set()
for f in os.listdir('data/auto_routes'):
    for r in json.load(open('data/auto_routes/' + f, encoding='utf-8')): AUTO.add(r['id'])


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def targets():
    seen = {}
    for rid in sorted(AUTO):
        r = IT.get(rid)
        if not r: continue
        for d in r['days']:
            c = d.get('city') or r['city']
            for s in d['stops']:
                q = s.get('q') or s['name']; k = c + '|' + q; g = G.get(k)
                if g and g.get('lat') and k not in seen and g.get('src') not in ('osm', 'photon', 'wiki'): seen[k] = (rid, s['name'], q, (g['lat'], g['lng']))
    return seen


def core(n):
    n = re.sub(r'[（(].*?[)）]', '', n).strip()
    return n


def wiki(name):
    u = 'https://zh.wikipedia.org/w/api.php?' + urllib.parse.urlencode({'action': 'query', 'generator': 'search', 'gsrsearch': name, 'gsrlimit': 4, 'prop': 'coordinates', 'colimit': 4, 'format': 'json', 'formatversion': 2})
    for _ in range(6):
        o = subprocess.run(['curl', '-s', '-i', '-m', '25', '-A', 'zouni-travel-data/1.0 (zouni.app; contact via site)', u], capture_output=True, text=True)
        head, body = (re.split(r"\r?\n\r?\n", o.stdout, maxsplit=1) + [''])[:2]
        if head.startswith(('HTTP/2 429', 'HTTP/1.1 429')):
            m = re.search(r'retry-after: (\d+)', head, re.I); time.sleep(int(m.group(1)) + 30 if m else 90); continue
        time.sleep(0.6)
        try:
            pages = json.loads(body).get('query', {}).get('pages', [])
            return [{'title': p['title'], 'lat': p['coordinates'][0]['lat'], 'lng': p['coordinates'][0]['lon']} for p in pages if p.get('coordinates')]
        except Exception: time.sleep(2)
    return None


def match(name, title):
    a, b = core(name), re.sub(r'[（(].*?[)）]', '', T2S(title))
    a2 = re.sub(r'(景区|风景区|旅游区|国家公园|遗址公园|公园|景点)$', '', a); b2 = re.sub(r'(景区|风景区|旅游区|国家公园|遗址公园|公园|景点)$', '', b)
    return len(a2) >= 2 and (a2 in b or b2 in a)


if sys.argv[1] == 'query':
    P = json.load(open(CP, encoding='utf-8')) if os.path.exists(CP) else {}
    todo = [(k, v) for k, v in targets().items() if P.get(k) is None]
    print('待查', len(todo), flush=True)
    from concurrent.futures import ThreadPoolExecutor
    def work(kv):
        k, (rid, name, q, cur) = kv
        return k, wiki(core(name))
    with ThreadPoolExecutor(1) as ex:
        for i, (k, res) in enumerate(ex.map(work, todo)):
            P[k] = res
            if i % 100 == 0: json.dump(P, open(CP, 'w', encoding='utf-8'), ensure_ascii=False); print(i, '/', len(todo), flush=True)
    json.dump(P, open(CP, 'w', encoding='utf-8'), ensure_ascii=False); print('完成')

if sys.argv[1] == 'apply':
    P = json.load(open(CP, encoding='utf-8')); ok = ch = far = nomatch = 0; rows = []
    for k, (rid, name, q, cur) in targets().items():
        res = P.get(k)
        if not res: nomatch += 1; continue
        hit = [x for x in res if match(name, x['title'])]
        if not hit: nomatch += 1; continue
        b = min(hit, key=lambda x: km(cur, (x['lat'], x['lng']))); d = km(cur, (b['lat'], b['lng']))
        if d <= 5: ok += 1; G[k]['src'] = G[k].get('src') or 'curated'; continue
        if d <= 150:
            G[k] = {'lat': b['lat'], 'lng': b['lng'], 'hit': '维基百科 ' + b['title'], 'q': q, 'src': 'wiki'}; ch += 1; rows.append((rid, name, round(d), b['title']))
        else: far += 1
    json.dump(G, open('data/geo/pois.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已核对一致', ok, '| 改坐标', ch, '| 差太远不采信', far, '| 无词条/对不上', nomatch)
    json.dump(rows, open('build/wiki_changed.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
