# 给每条行程存一份估价分项（不改原来的高低价），网页里按人数重算人均：房按两人一间分摊、包车按一辆车分摊
import json, math, re
exec(open('tools/estimate_prices.py', encoding='utf-8').read().split("done = 0")[0])   # 复用估价脚本里的常量和函数
ROUTES_C = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', open('build/routes.js', encoding='utf-8').read()).group(1))
n_ = 0
for t in T['trips']:
    it = IT.get(t['id'])
    if not it: continue
    d = CAT[it['dest']]; n = len(it['days']); nights = n - 1; city = it['city']
    first = next((G.get((x.get('city') or city) + '|' + (s.get('q') or s['name'])) for x in it['days'] for s in x['stops'] if G.get((x.get('city') or city) + '|' + (s.get('q') or s['name']))), None)
    pt = (first['lat'], first['lng']) if first else (d['base']['lat'], d['base']['lng'])
    if d['scope'] != 'domestic' or d['id'] == 'taiwan':
        air = ASIA_AIR.get(d['id'], (2500, 4500)); stay = ASIA_STAY.get(d['id'], (180, 380)); food = ASIA_FOOD.get(d['id'], (120, 220))
    else:
        dist = min(km(pt, h) for h in HUBS.values())
        air = (200, 500) if dist < 300 else (500, 1200) if dist < 1000 else (1000, 2000) if dist < 2000 else (1500, 3000)
        high = max(x.get('elev') or 0 for x in it['days']) >= 3000
        stay = (250, 450) if city in BIG else (180, 380) if high else (150, 320)
        food = (100, 200) if city in BIG else (80, 160)
    sees = sum(1 for x in it['days'] for s in x['stops'] if s['type'] in ('sight', 'museum', 'park', 'night'))
    tix = (sees * 30, sees * 90)
    bao = sum(1 for x in it['days'] if any(re.search('包车|自驾', s.get('via') or '') for s in x['stops']))
    local = (bao * 300 + (n - bao) * 40, bao * 500 + (n - bao) * 90)
    p = t.setdefault('price', {})
    rr = ROUTES_C.get(t['id'])
    bao2 = sum(1 for x in (rr or {}).get('days', []) if any(w['type'] == 'dep' and re.match(r'(包车|自驾|开车)', w.get('how') or '') for w in x['rows']))   # 编译后真正要包车的天
    if bao2 > bao and p.get('lo') and not p.get('baoFix'):          # 乡下改成包车后，当地交通按包车重算（只调一次）
        add = ((bao2 - bao) * 300 - (bao2 - bao) * 40, (bao2 - bao) * 500 - (bao2 - bao) * 90)
        p['lo'] = int(round((p['lo'] + add[0]) / 100.0)) * 100; p['hi'] = int(round((p['hi'] + add[1]) / 100.0)) * 100; p['baoFix'] = bao2 - bao
        bao = bao2; local = (bao * 300 + (n - bao) * 40, bao * 500 + (n - bao) * 90)
    p['parts'] = {'stay': list(stay), 'food': list(food), 'tix': list(tix), 'local': list(local), 'nights': nights, 'n': n, 'car': bao > 0 or bao2 > 0 or bool(it.get('drive'))}
    n_ += 1
json.dump(T, open('data/catalog/trips.json', 'w'), ensure_ascii=False, indent=1)
print('存了估价分项', n_, '条')
