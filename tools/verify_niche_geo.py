# 用法：python3 tools/verify_niche_geo.py <niche_before.json>   只复核比这份基准“多出来的”条目的坐标
# 规则：Nominatim 命中且 display_name 含目的地省名；与原坐标 ≤6km 算一致；6–60km 改成命中点（hit 写进 note 外的日志）；>60km 只记录不改。
import json, sys, subprocess, urllib.parse, time, math, re
base = {x['id'] for x in json.load(open(sys.argv[1], encoding='utf-8'))['items']}
NI = json.load(open('data/catalog/niche.json', encoding='utf-8'))
def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def nom(q, cc):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 6, 'accept-language': 'zh', 'countrycodes': cc})
    for t in range(3):
        o = subprocess.run(['curl', '-s', '-m', '25', '-A', 'zouni-travel-data/1.0 (zouni.app)', u], capture_output=True, text=True); time.sleep(1.3)
        try: return [{'lat': float(x['lat']), 'lng': float(x['lon']), 'name': x['display_name']} for x in json.loads(o.stdout or '[]')]
        except Exception: time.sleep(4 + 4 * t)
    return None
log = []; ok = chg = far = none = 0
for x in NI['items']:
    if x['id'] in base: continue
    cc = {'taiwan': 'tw', 'hongkong': 'hk', 'macau': 'mo'}.get(x['dest'], 'cn')
    main = re.split(r'[（(·]', x['name'])[0].strip()
    res = nom(main + ' ' + x['prov'], cc) or []
    res = [r for r in res if x['prov'] in r['name'] or (cc != 'cn')]
    if not res: none += 1; log.append((x['id'], '无命中')); continue
    b = min(res, key=lambda r: km((x['lat'], x['lng']), (r['lat'], r['lng']))); d = km((x['lat'], x['lng']), (b['lat'], b['lng']))
    if d <= 6: ok += 1
    elif d <= 60: chg += 1; log.append((x['id'], f'改坐标 偏 {d:.0f}km', [x['lat'], x['lng']], '->', [round(b['lat'], 4), round(b['lng'], 4)], b['name'][:40])); x['lat'], x['lng'] = round(b['lat'], 4), round(b['lng'], 4)
    else: far += 1; log.append((x['id'], f'命中离 {d:.0f}km，不改', b['name'][:40]))
json.dump(NI, open('data/catalog/niche.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(log, open('build/niche_verify.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('一致', ok, '| 改', chg, '| 命中太远没改', far, '| 无命中', none)
