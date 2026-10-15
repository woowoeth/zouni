# 用中文维基百科坐标校正「小众」里 n5_ 开头条目的坐标：词条标题和名字对得上、离现坐标 3–150 公里的改，其余不动。
import json, sys, re
sys.argv = ['x', 'none']
exec(open('tools/verify_geo_wiki.py').read().split("if sys.argv[1] == 'query'")[0])
from concurrent.futures import ThreadPoolExecutor
NI = json.load(open('data/catalog/niche.json', encoding='utf-8'))
items = [x for x in NI['items'] if x['id'].startswith('n5_')]
def work(x): return x['id'], wiki(re.split(r'[（(·]', x['name'])[0].strip())
with ThreadPoolExecutor(6) as ex: R = dict(ex.map(work, items))
ok = ch = no = far = 0; rows = []
for x in items:
    res = R.get(x['id']) or []; hit = [h for h in res if match(re.split(r'[（(·]', x['name'])[0].strip(), h['title'])]
    if not hit: no += 1; continue
    cur = (x['lat'], x['lng']); b = min(hit, key=lambda h: km(cur, (h['lat'], h['lng']))); d = km(cur, (b['lat'], b['lng']))
    if d <= 3: ok += 1; continue
    if d <= 150: rows.append((x['name'], round(d), b['title'])); x['lat'], x['lng'] = round(b['lat'], 4), round(b['lng'], 4); ch += 1
    else: far += 1
json.dump(NI, open('data/catalog/niche.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('一致', ok, '| 改', ch, '| 差太远不采信', far, '| 无词条', no)
for r in rows[:30]: print(r)
