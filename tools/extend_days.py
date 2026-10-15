# 用法：python3 tools/extend_days.py build/thin/patch_t0.json ...   把“补薄天”的补丁合进 data/itineraries.json
# 补丁每项：{id, day, insert_at, stops:[{name,q,type,dur,via,lat,lng,sight,deep}], next_via?, title, text}
import json, sys, re
IT_PATH, GP_PATH, BS_PATH = 'data/itineraries.json', 'data/geo/pois.json', 'tools/build_site.py'
IT = json.load(open(IT_PATH, encoding='utf-8')); GP = json.load(open(GP_PATH, encoding='utf-8'))
BAD = re.compile(r"船|渡轮|游艇|海拔 ?\d|视频|博主|字幕|必去|绝美|人间天堂|'")
ok, bad, SIGHT, DEEP = 0, [], {}, {}
for p in sys.argv[1:]:
    for it in json.load(open(p, encoding='utf-8')):
        r = IT['itineraries'].get(it['id'])
        if not r: bad.append((it['id'], '无此线路')); continue
        d = r['days'][it['day'] - 1]; c = d.get('city') or r['city']
        txt = json.dumps(it, ensure_ascii=False)
        if BAD.search(txt): bad.append((it['id'], '含禁用词 ' + BAD.search(txt).group(0))); continue
        names = {s['name'] for s in d['stops']}
        new = [s for s in it['stops'] if s['name'] not in names]
        if not new or len(d['stops']) + len(new) > 4: bad.append((it['id'], '无新点或超 4 站')); continue
        if any(s.get('lat') is None or s.get('lng') is None or not re.match(r'^(步行|打车|自驾|公交|火车)约 ', s.get('via', '')) for s in new): bad.append((it['id'], '缺坐标或 via 格式')); continue
        at = max(0, min(it.get('insert_at', len(d['stops'])), len(d['stops'])))
        for k, s in enumerate(new):
            GP.setdefault(c + '|' + (s.get('q') or s['name']), {'lat': float(s['lat']), 'lng': float(s['lng']), 'hit': '人工核对（近似）', 'q': s.get('q') or s['name'], 'src': 'curated'})
            d['stops'].insert(at + k, {'name': s['name'], 'q': s.get('q') or s['name'], 'type': s.get('type') or 'sight', 'dur': int(s.get('dur') or 60), 'via': s['via']})
            if s.get('sight'): SIGHT[s['name']] = s['sight']
            if s.get('deep'): DEEP[s['name']] = s['deep']
        if it.get('next_via') and at + len(new) < len(d['stops']): d['stops'][at + len(new)]['via'] = it['next_via']
        if it.get('title'): d['title'] = it['title']
        if it.get('text'): d['text'] = it['text']
        ok += 1
s = open(BS_PATH, encoding='utf-8').read()
i = s.index('SIGHT = {'); j = s.index('\n}\n', i); block = s[i:j]
si = {k: v for k, v in SIGHT.items() if "'%s':" % k not in block and "'" not in k and "'" not in v}
a = "'拜将坛': '汉中刘邦拜韩信为大将的地方',"
assert s.count(a) == 1
s = s.replace(a, a + '\n' + ''.join("    '%s': '%s',\n" % kv for kv in si.items()).rstrip('\n')) if si else s
i = s.index('DEEP = {'); j = s.index('\n}\n', i); block = s[i:j]
de = {k: v for k, v in DEEP.items() if "'%s':" % k not in block and "'" not in k and "'" not in v}
a = "DEEP = {   # “懂一点”的补充段落：时间轴那一行只是一句话，这里讲来历和看点；只写核对过的\n"
assert s.count(a) == 1
s = s.replace(a, a + ''.join("    '%s': '%s',\n" % kv for kv in de.items()))
json.dump(IT, open(IT_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); json.dump(GP, open(GP_PATH, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
open(BS_PATH, 'w', encoding='utf-8').write(s)
print('补了', ok, '天；拒绝', bad, '| SIGHT', len(si), '| DEEP', len(de))
