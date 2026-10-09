# 用法：项目根目录 python3 tools/add_routes_json.py data/auto_routes/xxx.json [...]
# 把“路线 JSON”加进 data/itineraries.json、catalog/trips.json、destinations.json、geo/pois.json（城市中心）、build_site.py 的 SIGHT/DEEP。
# 路线 JSON 是数组，每项：{id, dest, city, label, title, kicker, start:[年,月,日], ok:[MM-DD,MM-DD], best:[MM-DD,MM-DD], prep:[..],
#   days:[{title, text, start, stay, city, elev, stops:[{name,q,type,dur,via}], lunch, dinner}], sight:{景点:一句}, deep:{景点:一段}, centers:{城市:[纬,经]}}
# 编号已被占用的跳过；已有的 SIGHT/DEEP 不覆盖。
import json, sys

IT_PATH, TR_PATH, DS_PATH, BS_PATH, GP_PATH = 'data/itineraries.json', 'data/catalog/trips.json', 'data/destinations.json', 'tools/build_site.py', 'data/geo/pois.json'
load = lambda p: json.load(open(p, encoding='utf-8'))
IT, TR, DS, GP = load(IT_PATH), load(TR_PATH), load(DS_PATH), load(GP_PATH)
routes = []
for p in sys.argv[1:]:
    routes += load(p)
SIGHT, DEEP, CENTERS, added, skipped = {}, {}, {}, [], []
for L in routes:
    if L['id'] in IT['itineraries'] or any(t['id'] == L['id'] for t in TR['trips']):
        skipped.append(L['id']); continue
    dest = next((x for k in ('domestic', 'asia', 'world') for x in DS[k] if x['id'] == L['dest']), None)
    if dest is None: skipped.append(L['id'] + '(dest?)'); continue
    days = []
    for d in L['days']:
        o = {'title': d['title'], 'text': d['text'], 'stops': [], 'start': d['start'], 'elev': d.get('elev') or 0}
        for s in d['stops']:
            o['stops'].append({'name': s['name'], 'q': s.get('q') or s['name'], 'type': s.get('type') or 'sight', 'dur': int(s.get('dur') or 90), 'via': s.get('via') or '打车约 20 分钟'})
        if d.get('stay'): o['stay'] = d['stay']
        if d.get('city'): o['city'] = d['city']
        if d.get('lunch'): o['lunch'] = d['lunch']
        if d.get('dinner'): o['dinner'] = d['dinner']
        days.append(o)
    IT['itineraries'][L['id']] = {'city': L['city'], 'label': L['label'], 'title': L['title'], 'kicker': L['kicker'], 'prep': L['prep'], 'days': days, 'dest': L['dest'], 'start': L['start']}
    dest.setdefault('routes', []).append(L['id'])
    TR['trips'].append({'id': L['id'], 'dest': L['dest'], 'name': L['label'].rsplit(' ', 2)[0], 'region': dest['region'], 'days': len(days), 'title': L['label'], 'headline': L['title'], 'dek': days[0]['text'],
                        'why': None, 'price': None, 'tags': L.get('tags', []), 'season': {'ok': L['ok'], 'best': L['best']}, 'anytime': False, 'status': 'ok', 'page': 'Route.dc.html#' + L['id'], 'engineRoute': None, 'poster': None})
    SIGHT.update(L.get('sight') or {}); DEEP.update(L.get('deep') or {})
    for c, (la, ln) in (L.get('centers') or {}).items(): CENTERS.setdefault(c, (la, ln))
    added.append(L['id'])
for c, (la, ln) in CENTERS.items():
    GP.setdefault(c + '|' + c, {'lat': la, 'lng': ln, 'hit': '人工核对（市中心）', 'q': c, 'src': 'curated'})
s = open(BS_PATH, encoding='utf-8').read()
i = s.index('SIGHT = {'); j = s.index('\n}\n', i); block = s[i:j]
si = {k: v for k, v in SIGHT.items() if "'%s':" % k not in block and "'" not in k}
a = "'拜将坛': '汉中刘邦拜韩信为大将的地方',"
assert s.count(a) == 1
s = s.replace(a, a + '\n' + ''.join("    '%s': '%s',\n" % kv for kv in si.items() if "'" not in kv[1]).rstrip('\n'))
i = s.index('DEEP = {'); j = s.index('\n}\n', i); block = s[i:j]
de = {k: v for k, v in DEEP.items() if "'%s':" % k not in block and "'" not in k and "'" not in v}
a = "DEEP = {   # “懂一点”的补充段落：时间轴那一行只是一句话，这里讲来历和看点；只写核对过的\n"
assert s.count(a) == 1
s = s.replace(a, a + ''.join("    '%s': '%s',\n" % kv for kv in de.items()))
for p, o in ((IT_PATH, IT), (TR_PATH, TR), (DS_PATH, DS), (GP_PATH, GP)):
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(BS_PATH, 'w', encoding='utf-8').write(s)
print('写入', len(added), '条；跳过', skipped, '| SIGHT', len(si), '| DEEP', len(de))
