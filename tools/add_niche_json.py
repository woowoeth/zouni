# 用法：python3 tools/add_niche_json.py build/niche/out_*.json   （先校验，全部过了才写 data/catalog/niche.json）
# 校验：字段齐全、status 合法、note 50–100 字、坐标在中国范围（含港澳台）、id/名字不重复、不是 5A/世界遗产、没有违禁词；
# 自动关联：该目的地某条路线的景点名里含这个地点的主名（括号前）就把 trip 设成那条路线（最多一条，选站点最多的）。
import json, sys, re
NI = json.load(open('data/catalog/niche.json', encoding='utf-8'))
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
D = json.load(open('data/destinations.json', encoding='utf-8'))
DEST = {x['id']: x['name'] for x in D['domestic']}
Q = json.load(open('data/catalog/cn_quality.json', encoding='utf-8'))['items']
QN = {(i.get('short') or i['name']) for i in Q} | {i['name'] for i in Q}
have_id = {x['id'] for x in NI['items']}; have_nm = {re.split(r'[（(·]', x['name'])[0].strip() for x in NI['items']}
BAN = re.compile(r"'|必去|绝美|人间天堂|[\U0001F300-\U0001FAFF]|海拔")
new, errs = [], []
for f in sys.argv[1:]:
    try: arr = json.load(open(f, encoding='utf-8'))
    except Exception as e: errs.append(f'{f} JSON 读不出 {e}'); continue
    for x in arr:
        tag = f"{x.get('dest')}/{x.get('name')}"
        for k in ('id', 'name', 'prov', 'dest', 'status', 'note', 'lat', 'lng', 'src'):
            if x.get(k) in (None, ''): errs.append(f'{tag} 缺 {k}')
        if x.get('dest') not in DEST: errs.append(f'{tag} dest 不对'); continue
        if DEST[x['dest']] != x.get('prov'): errs.append(f"{tag} prov 应为 {DEST[x['dest']]}")
        if x.get('status') not in ('open', 'restricted', 'paused', 'check'): errs.append(f'{tag} status 不合法')
        n = len(x.get('note') or '')
        if not 50 <= n <= 100: errs.append(f'{tag} note 长度 {n}')
        if BAN.search((x.get('note') or '') + (x.get('name') or '')): errs.append(f'{tag} 有违禁词')
        la, lo = x.get('lat') or 0, x.get('lng') or 0
        if not (18 <= la <= 54 and 73 <= lo <= 135): errs.append(f'{tag} 坐标不在中国范围 {la},{lo}')
        main = re.split(r'[（(·]', x['name'])[0].strip()
        if x['id'] in have_id: errs.append(f'{tag} id 重复')
        if main in have_nm: errs.append(f'{tag} 名字重复')
        if main in QN: errs.append(f'{tag} 是 5A/世界遗产，不能放小众')
        if not re.match(r'^[a-z0-9_]+$', x['id']): errs.append(f'{tag} id 格式')
        have_id.add(x['id']); have_nm.add(main)
        # 自动关联路线
        best = None
        for rid, r in IT.items():
            if r['dest'] != x['dest']: continue
            hit = sum(1 for d in r['days'] for s in d['stops'] if main and (main in s['name'] or s['name'] in main and len(s['name']) >= 3))
            if hit and (best is None or hit > best[0]): best = (hit, rid)
        x['trip'] = best[1] if best else None
        new.append(x)
if errs:
    print('✗ 有问题，没写入：'); [print('  ', e) for e in errs[:80]]; print('共', len(errs), '处；候选', len(new), '条'); sys.exit(1)
NI['items'] += new
json.dump(NI, open('data/catalog/niche.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('写入', len(new), '条；其中关联到路线', sum(1 for x in new if x['trip']), '条；总数', len(NI['items']))
