# 只读核对：pois.json 里 src=by_name_fallback 的坐标，用 Nominatim 按「q + 城市」重查，列出偏差大的。不改 pois.json。
# 用法：python3 tools/xcheck_fallback.py   → 结果落盘 build/xcheck_fallback.json（可续跑，已查过的跳过）
import json, math, os, time, urllib.parse, subprocess
G = json.load(open('data/geo/pois.json', encoding='utf-8'))
OUT = 'build/xcheck_fallback.json'
R = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


keys = [k for k, v in G.items() if isinstance(v, dict) and v.get('src') == 'by_name_fallback']
for i, k in enumerate(keys):
    if k in R: continue
    v = G[k]; city = k.split('|')[0]
    u = 'https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3&accept-language=zh,en&q=' + urllib.parse.quote(v['q'] + ' ' + city)
    try:
        o = subprocess.run(['curl', '-s', '-m', '20', '-A', 'zouni-xcheck/1.0', u], capture_output=True, text=True).stdout
        js = json.loads(o) if o.strip() else []
    except Exception as e:
        js = None
    if js is None: continue
    hits = [{'lat': float(x['lat']), 'lng': float(x['lon']), 'name': x.get('display_name', '')[:80]} for x in js]
    near = min((km((v['lat'], v['lng']), (h['lat'], h['lng'])) for h in hits), default=None)
    R[k] = {'cur': [v['lat'], v['lng']], 'q': v['q'], 'hits': hits, 'near_km': near}
    if i % 20 == 0: json.dump(R, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
    time.sleep(1.1)
json.dump(R, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False)
bad = {k: r for k, r in R.items() if r['near_km'] is not None and r['near_km'] > 0.3}
print('共', len(R), '查无结果', sum(1 for r in R.values() if r['near_km'] is None), '偏差>300m', len(bad))
