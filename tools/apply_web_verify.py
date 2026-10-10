# 把联网核实的结果写回：fixed 改 data/geo/pois.json 坐标（偏移超过 80 公里的不信，留给人看）；replace 只列出来，手工处理。
# 用法：python3 tools/apply_web_verify.py <ver_in_N.json 所在目录> 。之后再跑 `verify_auto_geo.py vias <改前的 pois.json>` 重算 via
import json, glob, os, sys, math
d = sys.argv[1]
G = json.load(open('data/geo/pois.json', encoding='utf-8'))
def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
fx = rep = skip = 0; reps = []
for fi in sorted(glob.glob(d + '/ver_in_*.json')):
    fo = fi.replace('ver_in_', 'ver_out_')
    if not os.path.exists(fo): print('缺', fo); continue
    inp = {x['k']: x for x in json.load(open(fi, encoding='utf-8'))}
    out = json.load(open(fo, encoding='utf-8'))
    for k, v in out.items():
        x = inp.get(k)
        if not x: continue
        key = x['day_city'] + '|' + x['q']
        if v['v'] == 'fixed' and v.get('lat') and v.get('lng'):
            a = (x['lat'], x['lng'])
            if km(a, (v['lat'], v['lng'])) > 80: skip += 1; print('偏移太大不信', x['route'], x['name'], round(km(a, (v['lat'], v['lng']))), v.get('note')); continue
            G[key] = {'lat': v['lat'], 'lng': v['lng'], 'hit': '联网核对 ' + (v.get('note') or ''), 'q': x['q'], 'src': 'web'}; fx += 1
        elif v['v'] == 'replace': reps.append((k, x['route'], x['name'], v.get('replace')))
json.dump(G, open('data/geo/pois.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(reps, open('build/web_replace.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('改坐标', fx, '| 偏移太大', skip, '| 待换景点', len(reps))
