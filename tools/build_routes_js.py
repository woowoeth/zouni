# 用法：python3 tools/build_routes_js.py <输出 routes.js 路径>
import json, re, sys, glob
OUT = sys.argv[1] if len(sys.argv) > 1 else 'build/routes.js'
ED = json.load(open('data/editorial/routes.json'))
COSTS = json.load(open('data/costs.json'))
import os
PLACES = {}
if os.path.exists('data/places.json'):
    for r in json.load(open('data/places.json'))['places']:
        if r['type'] != 'dish': PLACES.setdefault(r['name'], r)
def kb(r):
    if not r: return ''
    bits = []
    rt = r.get('rating') or {}
    if rt.get('score') and rt.get('count'): bits.append('%s %.1f 分（%s 条）' % (rt['source'], rt['score'], format(rt['count'], ',')))
    elif rt.get('score'): bits.append('%s %.1f 分' % (rt['source'], rt['score']))
    elif rt.get('count'): bits.append('%s %s 条点评' % (rt['source'], format(rt['count'], ',')))
    if r.get('rank'): bits.append(r['rank'])
    if r.get('signature'): bits.append('招牌 ' + '、'.join(r['signature'][:2]))
    elif r.get('highlights'): bits.append(r['highlights'][0])
    return ' · '.join(bits)
def attach(w, nm):
    r = PLACES.get(nm)
    if r:
        w['dp'] = r['links']['dianping']; k = kb(r)
        if k and r['type'] != 'stay' and k != w.get('d'): w['kb'] = k
    return w
CITIES = [json.load(open(f)) for f in glob.glob('data/cities/*.json')]
POSTER = {'ZJJ4': '593f98efd721b7d1d2a5368deb8b8cec', 'HK2': '9ffe32de2faf342abf6f6b1c71d83544', 'KS4': '49725b5c4e5ce00e190aeb8646b6e995', 'SH3': '701a8fc3e98af25187d582c22c5e0dd4', 'HZ3': '187168aec09628cb37c2c3e5172fa8a0', 'SZ3': '53045776e2b701ebf1ea6b299109c2b3'}
MODE = {'drive': '开车', 'walk': '步行', 'taxi': '打车', 'transit': '地铁', 'bus': '公交', 'shuttle': '区间车'}
BIGCITY = {'张家界市', '武陵源', '佐敦', '成都', '上海', '杭州', '苏州', '乌鲁木齐', '伊宁', '拉萨'}
NOPOI = re.compile(r'提车|验车|还车|住处|湖畔|镇边草坡|进店休整|放行李|回程')
FOODY = re.compile(r'小吃|夜市|美食街')
TEA = re.compile(r'茶社|茶馆')


def clean(n):
    n = re.split(r'\s*·\s*', n or '')[0].strip()
    return re.sub(r'(住这|连住|返回)$', '', n).strip()


def dur(m):
    m = int(m or 0)
    if m >= 60:
        h, mm = divmod(m, 60)
        return f'{h} 小时' + (f' {mm} 分' if mm else '')
    return f'{m} 分钟'


def mins(t):
    h, m = t.split(':')
    return int(h) * 60 + int(m)


def city_of(place):
    return next((c for c in CITIES if clean(place) in c['match']), None)


routes = {}
for rid in ED['order']:
    ed = ED['routes'][rid]
    r = json.load(open(f'data/routes/{rid}.json'))
    days = []
    tot_km, longest = 0, 0
    for i, d in enumerate(r['days']):
        e = ed['days'][i] if i < len(ed['days']) else {}
        place = clean(d.get('place'))
        c = city_of(place)
        last = i == len(r['days']) - 1
        tl = d['timeline']
        rows = []
        streets = [x for x in tl if x['type'] == 'see' and FOODY.search(x['name'])]
        for x in tl:
            t = x['t']
            if x['type'] == 'dep':
                how = (MODE.get(x.get('mode')) or ('区间车' if place == '喀纳斯' else '')) + ' ' + dur(x.get('min')) + (f" · {x['km']} 公里" if x.get('km') else '')
                rows.append({'t': t, 'type': 'dep', 'to': clean(x['to']), 'how': how.strip()})
            elif x['type'] == 'see':
                nm = x['name']
                if FOODY.search(nm):
                    pl = clean(nm)
                    dish = (ed.get('foodStreet') or {}).get(pl, '当地小吃')
                    rows.append({'t': t, 'type': 'eat', 'slot': '午饭' if mins(t) < 16 * 60 else '晚饭', 'dish': dish, 'place': pl,
                                 'd': (f"人均约 ¥{x['cost']}" if x.get('cost') else ''), 'poi': pl})
                    continue
                if TEA.search(nm) and c:
                    fun = next((f for f in c.get('fun', []) if f['poi'] in nm), None)
                    rows.append({'t': t, 'type': 'fun', 'name': clean(nm) + '喝盖碗茶' if '茶社' in nm else nm,
                                 'd': fun['detail'] if fun else dur(x.get('dur')), 'poi': fun['poi'] if fun else clean(nm)})
                    continue
                dd = dur(x.get('dur'))
                if (x.get('dur') or 0) >= 180:
                    if '日落' in nm: dd = '待到日落'
                    elif '休整' in nm: dd = '进店睡一觉，歇到傍晚'
                    elif '闲逛' in nm: dd = '慢慢逛，待到傍晚'
                    elif '傍晚' in nm: dd = '走走歇歇，待到傍晚'
                    elif '黄昏' in nm: dd = '在维港边待到天黑'
                if x.get('cost'): dd += f" · ¥{x['cost']}"
                rows.append({'t': t, 'type': 'see', 'name': nm, 'd': dd, 'poi': '' if NOPOI.search(nm) else clean(nm)})
            elif x['type'] == 'eat':
                if streets and x['slot'] == '午饭' and any(abs(mins(s['t']) - mins(t)) <= 120 for s in streets):
                    continue
                dish, pl = x.get('dish'), x.get('place')
                if x['slot'] == '午饭' and e.get('lunchNear'):
                    rows.append({'t': t, 'type': 'eat', 'slot': '午饭', 'dish': '随意', 'place': e['lunchNear'], 'd': '', 'poi': ''}); continue
                if last and x['slot'] == '午饭' and any(re.search('返程|机场', s2['name']) and mins(t) >= mins(s2['t']) - 45 for s2 in tl if s2['type'] == 'see'):
                    rows.append({'t': t, 'type': 'eat', 'slot': '午饭', 'dish': '随意', 'place': '车站或机场里吃', 'd': '', 'poi': ''}); continue
                if dish in ('待补', None):
                    dish, pl = '随意', '住的地方附近'
                rows.append({'t': t, 'type': 'eat', 'slot': x['slot'], 'dish': dish, 'place': pl,
                             'd': x.get('priceText') or (f"人均 ¥{x['price']}" if x.get('price') else ''), 'poi': (x.get('poi') or '') if (x.get('price') or x.get('priceText')) else ''})
            elif x['type'] == 'fun':
                rows.append({'t': t, 'type': 'fun', 'name': x['name'], 'd': x.get('detail', ''), 'poi': x.get('poi', '')})
        for w in rows:   # 中午就到的“夕照”，名字里去掉夕照
            if w['type'] == 'see' and '夕照' in w['name'] and mins(w['t']) < 15 * 60: w['name'] = clean(w['name'])
        if last:   # LASTFIX 最后一天：回程排在午饭之后
            back = next((w for w in rows if w['type'] == 'dep' and w['to'] == '回程'), None)
            lunch = next((w for w in rows if w['type'] == 'eat'), None)
            if back and lunch and mins(lunch['t']) >= mins(back['t']):
                v = mins(lunch['t']) + 60; back['t'] = '%02d:%02d' % (v // 60, v % 60)
            rows.sort(key=lambda w: w['t'])
        if e.get('rows'): rows = e['rows']   # 引擎排错的天，用编辑层整天覆盖
        for w in rows:
            if w['type'] == 'eat': attach(w, w.get('place'))
            elif w['type'] == 'see': attach(w, clean(w['name']))
            elif w['type'] == 'fun': attach(w, w['name'])
        drive = sum((x.get('min') or 0) for x in tl if x['type'] == 'dep' and x.get('mode') == 'drive')
        if e.get('rows'): drive = 360 if last else 0   # 覆盖的天按覆盖内容算开车
        tot_km += sum((x.get('km') or 0) for x in tl if x['type'] == 'dep' and x.get('mode') == 'drive')
        longest = max(longest, drive)
        tiers = []
        if c and c.get('stay') and not last:
            for k, lab in (('luxury', '奢华'), ('upscale', '高级'), ('budget', '中低')):
                v = c['stay'].get(k)
                if v:
                    pr = PLACES.get(v['name']) or {}
                    tiers.append({'tier': lab, 'name': v['name'], 'sell': v.get('sell', ''), 'price': v.get('price') or '', 'dp': (pr.get('links') or {}).get('dianping', ''), 'kb': kb(dict(pr, signature=[], highlights=[])) if (pr.get('rating')) else ''})
        st_row = next((x for x in tl if x['type'] == 'stay'), None)
        eng = (d['stay'].get('engine') or [{}])[0]
        days.append({'title': e.get('title') or d['title'], 'text': e.get('text', ''), 'lat': round(d['lat'], 2), 'lng': round(d['lng'], 2),
                     'elev': d['facts']['altitude_m'], 'clim': {m: d['facts']['temp_by_month'][str(m)] for m in (9, 10, 11)},
                     'city': place, 'navCity': place if place in BIGCITY else ('上海' if rid == 'sh3' else '杭州' if rid == 'hz3' else '苏州' if rid == 'sz3' else '成都' if rid == 'cd3' else ''),
                     'rows': rows, 'stay': tiers, 'driveMin': drive,
                     'stayName': '' if last else (tiers[0]['name'] if tiers else (st_row or {}).get('name') or place),
                     'stayNote': '' if last else (tiers[0]['sell'] if tiers else (f"约 ¥{eng.get('price')}/间" if eng.get('price') else '')),
                     'story': e.get('story'), 'manners': e.get('manners', []), 'notes': [re.sub(r'^沿途\s*·\s*', '', n) for n in (d.get('notes') or [])][:2]})
    meta = {k: ed[k] for k in ('label', 'title', 'kicker', 'alt', 'start', 'price', 'prep')}
    meta['img'] = '/_blob/' + POSTER.get(ed['poster'], ed['poster'])
    meta['driveTop'] = f'{round(tot_km, -1):.0f} 公里' if ed['driveTop'] == 'AUTO' else ed['driveTop']
    meta['driveSub'] = f'最长一天 {longest / 60:.1f} 小时' if ed['driveSub'] == 'AUTO' else ed['driveSub']
    meta['id'] = rid
    c = COSTS.get(rid)
    if c and ed['price'].startswith('¥'):
        lo, hi = [int(x.replace(',', '')) for x in re.findall(r'[\d,]+', ed['price'])[:2]]
        c = dict(c, trans=[max(0, lo - c['localPP2']), max(0, hi - c['localPP2'])])
    meta['cost'] = c
    elevs = [d['elev'] or 0 for d in days]; longd = sum(1 for d in days if d['driveMin'] >= 360)
    stairs = any(re.search(r'天梯|台阶|爬|索道上山|观景台', w.get('name', '')) for d in days for w in d['rows'] if w['type'] == 'see')
    fit = []
    if max(elevs) >= 3000: fit.append('高海拔，最高住在 %s 米：7 岁以下的孩子、心肺不好的老人慎重' % format(max(elevs), ','))
    if longd: fit.append('有 %d 天开车 6 小时以上：带孩子要多停几次' % longd)
    if stairs: fit.append('台阶和上坡多：膝盖不好的可以少走一段')
    meta['fit'] = fit
    meta['navApp'] = ed.get('navApp', 'amap')
    meta['days'] = days
    routes[rid] = meta

js = 'window.ZOUNI_ORDER=' + json.dumps(ED['order']) + ';\nwindow.ZOUNI_ROUTES=' + json.dumps(routes, ensure_ascii=False, separators=(',', ':')) + ';\n'
open(OUT, 'w', encoding='utf-8').write(js)
print('routes.js', len(js) // 1024, 'KB', {k: len(v['days']) for k, v in routes.items()})
for rid in ('sh3', 'hz3', 'sz3'):
    for d in routes[rid]['days']:
        print(rid, d['title'], '|', ' / '.join(w['t'] + ' ' + (w.get('name') or ('→' + w['to'] if w['type'] == 'dep' else w['slot'] + '·' + w['dish'] + '@' + w['place'])) for w in d['rows'])[:210], '| 住', d['stayName'])
