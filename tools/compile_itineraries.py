# 声明式行程 → 线路页数据
# 用法：python3 tools/compile_itineraries.py build/routes.js   （把编译结果并进已有的 routes.js）
import json, math, os, re, sys, time, urllib.parse, urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else 'build/routes.js'
IT = json.load(open('data/itineraries.json'))['itineraries']
CAT = {d['id']: d for d in json.load(open('data/catalog/destinations.json'))['destinations']}
TRIPS = {t['id']: t for t in json.load(open('data/catalog/trips.json'))['trips']}
GP = 'data/geo/pois.json'
GEO = json.load(open(GP)) if os.path.exists(GP) else {}
DUR = {'sight': 120, 'museum': 150, 'street': 90, 'park': 60, 'food': 60, 'night': 60, 'fun': 90}
UA = {'User-Agent': 'zouni-travel-data/1.0 (zouni.app)'}


CC = {'macau': 'mo', 'hongkong': 'hk'}
ASIA_CC = {x['id']: x['cc'] for x in json.load(open('data/destinations.json'))['asia']}
CC.update(ASIA_CC)
CUR_CC = ['cn']


def geocode(q, city, base=None, alt=None):
    key = city + '|' + q
    if key in GEO and (GEO[key] or GEO.get(key + '#tried')): return GEO[key]
    for query in [x for x in (q, city + ' ' + q, alt and city + ' ' + alt) if x]:
        u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1, 'countrycodes': CUR_CC[0], 'accept-language': 'zh'})
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()); time.sleep(1.1)
        except Exception:
            r = []; time.sleep(2)
        if r and base and km(base, (float(r[0]['lat']), float(r[0]['lon']))) > 220:
            r = []   # 查到了外地的同名地方，不要
        if r:
            GEO[key] = {'lat': float(r[0]['lat']), 'lng': float(r[0]['lon']), 'hit': r[0]['display_name'][:60], 'q': query}
            json.dump(GEO, open(GP, 'w'), ensure_ascii=False, indent=1)
            return GEO[key]
    GEO[key] = None; GEO[key + '#tried'] = True; json.dump(GEO, open(GP, 'w'), ensure_ascii=False, indent=1)
    return None


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def r5(x): return int(5 * round(x / 5.0))
def hm(m): return '%02d:%02d' % (m // 60, m % 60)
def mm(t): h, m = t.split(':'); return int(h) * 60 + int(m)
def dur_txt(m): return (f'{m // 60} 小时' + (f' {m % 60} 分' if m % 60 else '')) if m >= 60 else f'{m} 分钟'


SELF = [False]


def leg(a, b, via=None):
    """两点之间：怎么走、多久、多远（自驾线路写开车）"""
    if via:
        h = re.search(r'(\d+) 小时', via); m2 = re.search(r'(\d+) 分钟', via)
        mins = (int(h.group(1)) * 60 if h else 0) + (int(m2.group(1)) if m2 else 0)
        return re.sub(r'\s*\d+ (小时|分钟)', '', via).strip(), (mins or 25), None
    if not a or not b: return '打车', 20, None
    d = km(a, b) * 1.25
    if d < 1.3: return '步行', max(5, r5(d / 4.5 * 60)), None
    if SELF[0]:
        if d < 20: return '开车', max(10, r5(d / 30 * 60 + 5)), round(d)
        return '自驾约', r5(d / 70 * 60 + 10), round(d)
    if d < 20: return '打车', max(10, r5(d / 25 * 60 + 8)), round(d)
    if d < 60: return '打车约', r5(d / 55 * 60 + 10), round(d)
    return '包车约', r5(d / 65 * 60 + 10), round(d)


def short(n): return re.split(r'\s*·\s*', n)[0]


def dp(city, kw): return 'https://www.dianping.com/ai-search?keyword=' + urllib.parse.quote(city + ' ' + kw)


s = open(OUT, encoding='utf-8').read()
ORDER = json.loads(re.search(r'window.ZOUNI_ORDER=(\[.*?\]);', s).group(1))
ROUTES = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', s).group(1))
report = []
CITY_FOOD = json.load(open('data/catalog/city_food.json')) if os.path.exists('data/catalog/city_food.json') else {}
for rid, it in IT.items():
    dest = CAT[it['dest']]; city = it['city']; CUR_CC[0] = CC.get(it['dest'], 'cn'); SELF[0] = bool(it.get('drive'))
    base = (dest['base']['lat'], dest['base']['lng'])
    cg = geocode(city, city, None)                      # 以行程所在城市为中心，不用省会
    if cg and km(base, (cg['lat'], cg['lng'])) < 2500: base = (cg['lat'], cg['lng'])   # 离省会远的城市（喀什、札幌、天水）也认
    eat_pool = list(dest['eat']); days = []; n = len(it['days']); drive_tot = 0; longest = 0; carry = None
    for di, d in enumerate(it['days']):
        last = di == n - 1
        dcity = d.get('city', city); dbase = base
        stay_pt = None
        if dcity != city:
            cg2 = geocode(dcity, dcity, None)
            if cg2: dbase = (cg2['lat'], cg2['lng'])
        sc = (GEO.get(dcity + '|' + d['stay']) or GEO.get(city + '|' + d['stay'])) if d.get('stay') else None   # 住处有人工核对过的坐标就用（原来调用了一个不存在的函数，住处坐标从来没用上）
        stay_ok = bool(sc and km(dbase, (sc['lat'], sc['lng'])) < 60)
        stay_pt = (sc['lat'], sc['lng']) if stay_ok else dbase
        far = lambda p: p and km(p, dbase) > 60   # 当天已经到了另一座城：回住处就留在当地
        t = mm(d.get('start', '09:00')); prev = carry or dbase; rows = []; lunched = t >= 13 * 60; dined = False; drive = 0
        meal_i = di

        def meal(slot, spec, at):
            global meal_i
            pool = CITY_FOOD.get(dcity) or CITY_FOOD.get(city) or eat_pool   # 先用当天城市的招牌菜
            dish = (spec or {}).get('dish') or pool[meal_i % len(pool)]; meal_i += 1
            place = (spec or {}).get('place') or '附近'
            return {'t': hm(at), 'type': 'eat', 'slot': slot, 'dish': dish, 'place': place, 'd': '', 'poi': '', 'dp': dp(city, dish.split('、')[0])}

        for si, st in enumerate(d['stops']):
            g = geocode(st.get('q') or st['name'], dcity, dbase, short(st['name'])); pt = (g['lat'], g['lng']) if g else None
            # 晚上的点：先吃晚饭
            dine_there = bool(st.get('at') and mm(st['at']) >= 18 * 60 and (d.get('dinner') or {}).get('place') and (d['dinner']['place'] in st['name'] or d['dinner']['place'] in (st.get('q') or '')))
            if st.get('at') and mm(st['at']) >= 18 * 60 and not dined and not last and not dine_there:
                if t < 17 * 60 + 30:
                    rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': '回去歇一下'}); t = 18 * 60 + 10; prev = stay_pt if stay_ok else (prev if far(prev) else stay_pt)
                rows.append(meal('晚饭', d.get('dinner'), max(t, 18 * 60))); t = max(t, 18 * 60) + 75; dined = True
            # 到了饭点先吃午饭
            if not lunched and t >= 11 * 60 + 40 and st['type'] != 'food':
                if t <= 14 * 60 + 30: rows.append(meal('午饭', d.get('lunch'), t)); t += 60
                lunched = True                                           # 过了两点半就不排“午饭”了，晚上再吃
            how, mins, dist = leg(prev, pt, st.get('via'))
            if dine_there and not dined:
                at0 = max(t + mins, 18 * 60)
                if at0 - mins - t >= 60:
                    if not lunched and 11 * 60 <= t <= 14 * 60:          # 先吃午饭再回去歇
                        rows.append(meal('午饭', d.get('lunch'), max(t, 11 * 60 + 30))); t = max(t, 11 * 60 + 30) + 60; lunched = True
                    rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': '回去歇一下'}); prev = stay_pt if stay_ok else (prev if far(prev) else stay_pt)
                    how, mins, dist = leg(prev, pt, st.get('via'))     # 歇完从住处出发，路程按住处算
                    at0 = max(t + mins, 18 * 60)
                t = at0 - mins
            elif st.get('at'):
                gap = mm(st['at']) - mins - t
                if gap >= 60 and rows: rows.append({'t': hm(t), 'type': 'see', 'name': '沿途慢慢走', 'd': dur_txt(gap), 'poi': '', 'dp': ''})   # (d) 等夕照、等开船的空当
                t = max(t, mm(st['at']) - mins)
            if how.startswith(('包车', '自驾', '开车')): drive += mins
            rows.append({'t': hm(t), 'type': 'dep', 'to': short(st['name']), 'how': f'{how} {dur_txt(mins)}' + (f' · {dist} 公里' if dist and dist >= 5 else '')})
            if not lunched and t < 12 * 60 and t + mins > 13 * 60:   # 车开过中午：路上吃
                spec = d.get('lunch') or {}
                rows.append({'t': hm(12 * 60 + 30), 'type': 'eat', 'slot': '午饭', 'dish': spec.get('dish') or '路上吃', 'place': spec.get('place') or '沿途', 'd': '', 'poi': '', 'dp': ''}); lunched = True
            t += mins; du = st.get('dur') or DUR[st['type']]
            if dine_there and not dined:
                rows.append(meal('晚饭', d.get('dinner'), t)); t += 75; dined = True
            # (c) 路上过了饭点：到了先吃午饭
            if not lunched and t >= 11 * 60 + 40 and st['type'] != 'food':
                if t <= 14 * 60 + 30: rows.append(meal('午饭', d.get('lunch'), t)); t += 60
                lunched = True
            if st['type'] == 'food':
                slot = '早饭' if t < 10 * 60 else ('午饭' if t < 16 * 60 else '晚饭')
                rows.append({'t': hm(t), 'type': 'eat', 'slot': slot, 'dish': st.get('dish', '小吃'), 'place': short(st['name']), 'd': '', 'poi': st.get('q') or st['name'], 'dp': dp(dcity, short(st['name']))})
                if slot == '午饭': lunched = True
                if slot == '晚饭': dined = True
            else:
                rows.append({'t': hm(t), 'type': 'fun' if st['type'] == 'fun' else 'see', 'name': st['name'], 'd': dur_txt(du), 'poi': st.get('q') or st['name'], 'dp': dp(dcity, short(st['name'])), **({'at': st['at']} if st.get('at') else {})})
                if not lunched and t < 12 * 60 and t + du > 13 * 60:   # 逛得久、跨过中午：在里面简单吃
                    rows.append({'t': hm(max(t + 60, 12 * 60 + 15)), 'type': 'eat', 'slot': '午饭', 'dish': '简单吃一点', 'place': short(st['name']) + '里面', 'd': '', 'poi': '', 'dp': ''}); lunched = True
            t += du; prev = pt or prev
        if not lunched and 12 * 60 <= t <= 14 * 60 + 30:
            rows.append(meal('午饭', d.get('lunch'), t)); t += 60; lunched = True
        if last:
            rows.append({'t': hm(t + 10), 'type': 'dep', 'to': '回程', 'how': '去车站或机场'})
        else:
            if not dined:
                if t < 17 * 60 + 30:
                    rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': '回去歇一下'}); t = 18 * 60 + 10; prev = stay_pt if stay_ok else (prev if far(prev) else stay_pt)
                rows.append({'t': hm(max(t, 18 * 60 + 10)), 'type': 'dep', 'to': '吃晚饭', 'how': '开车或步行' if SELF[0] else '打车或步行'})
                rows.append(meal('晚饭', d.get('dinner'), max(t, 18 * 60 + 10) + 20)); t = max(t, 18 * 60 + 10) + 95
            rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': '开车或步行' if SELF[0] else '打车或步行'})
        # 时间必须单调递增
        ts = [mm(w['t']) for w in rows]
        if ts != sorted(ts): report.append(f'{rid} D{di + 1} 时间倒序')
        first = next((GEO.get(dcity + '|' + (x.get('q') or x['name'])) for x in d['stops'] if GEO.get(dcity + '|' + (x.get('q') or x['name']))), None)
        lat, lng = (first['lat'], first['lng']) if first else base
        drive_tot += drive; longest = max(longest, drive)
        lastg = next((GEO.get(dcity + '|' + (x.get('q') or x['name'])) for x in reversed(d['stops']) if GEO.get(dcity + '|' + (x.get('q') or x['name']))), None)
        carry = (lastg['lat'], lastg['lng']) if lastg else carry
        if d.get('stay'):   # 第二天从住的地方出发：住处查得到就用住处
            sg = GEO.get(d['stay'] + '|' + d['stay']) if 'GEO' in globals() else None
            if sg and carry and km((sg['lat'], sg['lng']), carry) <= 400: carry = (sg['lat'], sg['lng'])  # stay_carry：只认核对过的城市中心
        days.append({'title': d['title'], 'text': d['text'], 'lat': round(lat, 2), 'lng': round(lng, 2), 'elev': d.get('elev', dest['base']['elev']),
                     'clim': {m: dest['climate'][str(m)] for m in (9, 10, 11)}, 'city': dcity, 'navCity': dcity, 'rows': rows, 'stay': [],
                     'driveMin': drive, 'stayName': '' if last else d.get('stay', dcity), 'stayNote': '', 'story': d.get('story'), 'manners': [], 'notes': []})
    tr = TRIPS.get(rid, {}); p = tr.get('price') or {}
    meta = {'id': rid, 'label': it['label'], 'title': it['title'], 'kicker': it['kicker'], 'alt': it['title'], 'start': it['start'], 'prep': it['prep'],
            'price': (('约 ' if str(p.get('basis', '')).startswith('参考价') else '') + '¥{:,}–{:,}'.format(p['lo'], p['hi'])) if p.get('lo') else '人均另算',
            'img': ('/_blob/' + tr['poster']) if tr.get('poster') else '', 'driveTop': ('自驾' if SELF[0] else '包车') if drive_tot else '不开车', 'drive': SELF[0], 'loop': bool(it.get('loop')),
            'driveSub': (f'最长一天 {longest / 60:.1f} 小时' if drive_tot else '地铁、打车加步行'), 'navApp': 'google' if it['dest'] in ASIA_CC else 'amap', 'cost': None,
            'fit': ((['高海拔，最高住在 {:,} 米：7 岁以下的孩子、心肺不好的老人慎重'.format(max(x.get('elev') or 0 for x in it['days']))] if max(x.get('elev') or 0 for x in it['days']) >= 3000 else []) + (['有一天要坐 %d 小时以上的车：带孩子要多停几次' % (longest // 60)] if longest >= 180 else [])), 'days': days, 'compiled': True}
    ROUTES[rid] = meta
    if rid not in ORDER: ORDER.append(rid)
hits = sum(1 for k, v in GEO.items() if v and not k.endswith('#tried')); miss = [k for k, v in GEO.items() if not v and not k.endswith('#tried')]
s = re.sub(r'window.ZOUNI_ORDER=\[.*?\];', 'window.ZOUNI_ORDER=' + json.dumps(ORDER) + ';', s, count=1)
s = re.sub(r'window.ZOUNI_ROUTES=.*;\n', lambda m: 'window.ZOUNI_ROUTES=' + json.dumps(ROUTES, ensure_ascii=False, separators=(',', ':')) + ';\n', s, count=1)
open(OUT, 'w', encoding='utf-8').write(s)
print('编译', len(IT), '条；站点坐标', hits, '个，没查到', len(miss), miss[:6], '；问题', report or '无')
