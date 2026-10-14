# 用法：python3 tools/check_new_routes.py build/new_routes/out_*.json  检查子代理写的路线 JSON（加载前）：via 折算时速、标题地名、标签天数、违禁词、sight/deep 覆盖、id 重复
import json, sys, re, math, glob
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))
def mins(v):
    h = re.search(r'(\d+) 小时', v); m = re.search(r'(\d+) 分钟', v)
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)
BAN = re.compile(r"坐船|乘船|游船|渡轮|轮渡|必去|绝美|人间天堂|'|[\U0001F300-\U0001FAFF]")
bad = 0; seen = set(); total = 0
for f in sys.argv[1:]:
    try: arr = json.load(open(f, encoding='utf-8'))
    except Exception as e: print(f, 'JSON 读不出', e); bad += 1; continue
    for r in arr:
        total += 1; errs = []
        if r['id'] in IT or r['id'] in seen: errs.append('id 重复')
        seen.add(r['id'])
        if r['label'].rsplit(' ', 2)[-2:][0] != str(len(r['days'])) and not re.search(r'%d 天$' % len(r['days']), r['label']): errs.append('label 天数不对')
        if re.search(r'\d+ 天$', r['label']) is None: errs.append('label 格式')
        txt = json.dumps(r, ensure_ascii=False)
        m = BAN.search(txt)
        if m: errs.append('违禁词 ' + m.group(0))
        cen = r.get('centers') or {}
        for di, d in enumerate(r['days']):
            names = ' '.join(s['name'] for s in d['stops'])
            for p in re.split(r'\s*·\s*', d['title']):
                p = p.strip()
                if p and p not in ('回程',) and p not in names: errs.append(f'第{di+1}天标题地名「{p}」不在景点名里')
            c0 = d.get('city') or r['city']
            prev = None
            if di == 0 and c0 in cen: prev = tuple(cen[c0])
            elif di > 0:
                pc = r['days'][di - 1].get('stay') or r['days'][di - 1].get('city') or r['city']
                prev = tuple(cen[pc]) if pc in cen else None
            if prev is None and c0 in cen: prev = tuple(cen[c0])
            for s in d['stops']:
                if s.get('lat') is None or s.get('lng') is None: errs.append(f'{s["name"]} 缺坐标'); continue
                here = (s['lat'], s['lng'])
                v = s.get('via') or ''
                if not re.match(r'(步行约|打车约|自驾约|火车约|地铁约|公交约) ', v): errs.append(f'{s["name"]} via 格式「{v}」')
                elif prev and not v.startswith('步行') and not (di == 0 and s is d['stops'][0]):      # 到达日第一站是从机场/出发城市过来的，坐标里没有，不查
                    mm = mins(v); dist = km(prev, here) * 1.25; hi = 200 if v.startswith('火车') else 110
                    if mm and dist > 4 and (dist / (mm / 60) > hi or dist / (mm / 60) < 8): errs.append(f'{s["name"]} via「{v}」折算路程 {dist:.0f}km 时速 {dist / (mm / 60):.0f}km/h')
                prev = here
                if s['name'] not in (r.get('sight') or {}): errs.append(f'{s["name"]} 缺 sight')
                if s['name'] not in (r.get('deep') or {}): errs.append(f'{s["name"]} 缺 deep')
        if errs:
            bad += 1; print('✗', r['id'], r['label']); [print('   ', e) for e in errs[:12]]
print('共', total, '条；有问题', bad)
