# 用 Nominatim 核对批量补进来的路线的景点坐标（子代理凭记忆写的）。
# 用法：项目根目录  python3 tools/verify_auto_geo.py query   → 把每个景点的搜索词查一遍，结果落盘到 build/nominatim_check.json（可续跑）
#       python3 tools/verify_auto_geo.py apply   → 按规则改 data/geo/pois.json（偏差大且有可靠命中的，改成查到的坐标），并重算受影响的 via 分钟数
import json, math, os, re, subprocess, sys, time, urllib.parse

FOR = os.environ.get('FOREIGN') == '1'     # FOREIGN=1：核对国外路线（不限国家码）
CACHE = 'build/nominatim_check_f.json' if FOR else 'build/nominatim_check.json'
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
G = json.load(open('data/geo/pois.json', encoding='utf-8'))
DS = json.load(open('data/destinations.json', encoding='utf-8'))
AUTO = set()
for f in os.listdir('data/auto_routes'):
    for r in json.load(open('data/auto_routes/' + f, encoding='utf-8')): AUTO.add(r['id'])
FOREIGN = {x['id'] for k in ('asia', 'world') for x in DS[k]}


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def stops():
    out = []
    for rid in sorted(AUTO):
        r = IT.get(rid)
        if not r or (r['dest'] in FOREIGN) != FOR: continue
        for di, d in enumerate(r['days']):
            c = d.get('city') or r['city']
            for si, s in enumerate(d['stops']):
                out.append((rid, di, si, c, s))
    return out


def nom(q):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 6, 'accept-language': 'zh'} | ({} if FOR else {'countrycodes': 'cn'}))
    for _ in range(2):
        o = subprocess.run(['curl', '-s', '-m', '25', '-A', 'zouni-travel-data/1.0 (zouni.app)', u], capture_output=True, text=True)
        time.sleep(1.15)
        try: return [{'lat': float(x['lat']), 'lng': float(x['lon']), 'name': x['display_name'][:60]} for x in json.loads(o.stdout or '[]')]
        except Exception: time.sleep(3)
    return None


if sys.argv[1] == 'query':
    os.makedirs('build', exist_ok=True)
    C = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = []
    for rid, di, si, c, s in stops():
        q = s.get('q') or s['name']
        if q not in C and q not in todo: todo.append(q)
    print('待查', len(todo), flush=True)
    for i, q in enumerate(todo):
        C[q] = nom(q)
        if i % 25 == 0:
            json.dump(C, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False); print(i, '/', len(todo), flush=True)
    json.dump(C, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    print('完成')


def fmt_via(prefix, minutes):
    h, m = divmod(int(round(minutes)), 60)
    return f'{prefix}约 ' + (f'{h} 小时' + (f' {m} 分钟' if m else '') if h else f'{m} 分钟')


if sys.argv[1] == 'apply':
    C = json.load(open(CACHE, encoding='utf-8'))
    changed, flagged, unverified, ok = [], [], 0, 0
    # 1) 城市中心：Nominatim 查到的是“市”的行政区质心，子代理写的是市区，换成市区（万荣、黑马河保持原样）
    for f in sorted(os.listdir('data/auto_routes')):
        for r in json.load(open('data/auto_routes/' + f, encoding='utf-8')):
            if (r['dest'] in FOREIGN) != FOR: continue
            for c, (la, ln) in (r.get('centers') or {}).items():
                g = G.get(c + '|' + c)
                if g and g.get('lat') and km((la, ln), (g['lat'], g['lng'])) > 25 and re.search(r'[市省],', g.get('hit', '')) and c not in ('万荣', '黑马河'):
                    G[c + '|' + c] = {'lat': la, 'lng': ln, 'hit': '人工核对（市区）', 'q': c, 'src': 'curated'}; changed.append(('中心', c))
    # 2) 景点：agent 坐标和 Nominatim 命中对比
    for rid, di, si, c, s in stops():
        q = s.get('q') or s['name']; key = c + '|' + q; g = G.get(key)
        if not g or not g.get('lat'): continue
        res = C.get(q)
        if not res: unverified += 1; continue
        a = (g['lat'], g['lng'])
        best = min(res, key=lambda x: km(a, (x['lat'], x['lng'])))
        d = km(a, (best['lat'], best['lng']))
        if d <= 8: ok += 1; continue
        cen = G.get(c + '|' + c)
        if d <= 60:
            G[key] = {'lat': best['lat'], 'lng': best['lng'], 'hit': 'Nominatim 核对 ' + best['name'], 'q': q, 'src': 'osm'}; changed.append((rid, s['name'], round(d)))
        else:
            near_c = [x for x in res if cen and cen.get('lat') and km((cen['lat'], cen['lng']), (x['lat'], x['lng'])) <= 120]
            if near_c and cen and km(a, (cen['lat'], cen['lng'])) > 120:
                b2 = near_c[0]; G[key] = {'lat': b2['lat'], 'lng': b2['lng'], 'hit': 'Nominatim 核对 ' + b2['name'], 'q': q, 'src': 'osm'}; changed.append((rid, s['name'], '换到市附近'))
            else: flagged.append((rid, s['name'], round(d)))
    json.dump(G, open('data/geo/pois.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    n_via = 0   # via 另用 `vias` 子命令重算（只改坐标变了的景点和它后面一站；起点按前一晚的住处算）
    full = json.load(open('data/itineraries.json', encoding='utf-8')); full['itineraries'] = IT
    json.dump(full, open('data/itineraries.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('核对一致', ok, '| 无法核对', unverified, '| 改坐标', len(changed), '| 存疑未改', len(flagged), '| 重算 via', n_via)
    json.dump({'changed': changed, 'flagged': flagged}, open('build/verify_apply.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if sys.argv[1] == 'vias':
    # 用法：python3 tools/verify_auto_geo.py vias <核对前的 pois.json>   （FOREIGN=1 时处理国外）
    before = json.load(open(sys.argv[2], encoding='utf-8'))
    moved = {k for k, v in G.items() if isinstance(v, dict) and v.get('lat') and isinstance(before.get(k), dict) and before[k].get('lat') and (abs(v['lat'] - before[k]['lat']) > 1e-3 or abs(v['lng'] - before[k]['lng']) > 1e-3)}
    def cen(c):
        g = G.get(c + '|' + c); return (g['lat'], g['lng']) if g and g.get('lat') else None
    n = 0
    for rid in sorted(AUTO):
        r = IT.get(rid)
        if not r or (r['dest'] in FOREIGN) != FOR: continue
        for di, d in enumerate(r['days']):
            c = d.get('city') or r['city']
            start = cen(r['city']) if di == 0 else (cen(r['days'][di - 1].get('stay') or '') or cen(r['days'][di - 1].get('city') or r['city']))
            prev = start; hit_prev = False
            for s_ in d['stops']:
                g = G.get(c + '|' + (s_.get('q') or s_['name']))
                cur = (g['lat'], g['lng']) if g and g.get('lat') else None
                is_moved = (c + '|' + (s_.get('q') or s_['name'])) in moved
                if cur and prev and (is_moved or hit_prev) and s_.get('via'):
                    pre = re.match(r'(打车|包车|自驾|公交|步行)', s_['via'])
                    if pre:
                        dist = km(prev, cur)
                        if pre.group(1) in ('打车', '包车'):
                            spd = 40 if dist < 40 else 60
                            new = fmt_via(pre.group(1), max(10, dist * 1.3 / spd * 60))
                        elif pre.group(1) == '自驾':
                            new = fmt_via('自驾', max(10, dist * 1.3 / 60 * 60))
                        else: new = s_['via']
                        if new != s_['via']: s_['via'] = new; n += 1
                hit_prev = is_moved
                prev = cur or prev
    full = json.load(open('data/itineraries.json', encoding='utf-8')); full['itineraries'] = IT
    json.dump(full, open('data/itineraries.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('重算 via', n, '| 坐标变动的景点', len(moved))
