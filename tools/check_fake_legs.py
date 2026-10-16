# 反向闸：假长车程（“出发 → X｜包车约 3 小时 · 200 公里”，其实两点都在同一座城里）
# 用法：python3 tools/check_fake_legs.py [build/routes.js] [-v]      有违例退出码 1
# 原理：不信行里写的公里数，从 data/geo/pois.json 的真坐标重算——
#   起点 = 上一站坐标；当天第一段 / 从住处出发 = 当天落脚城市的“城市中心”坐标（城市|城市）
#   终点 = 这一站坐标（城市|q）
#   写了 ≥60 公里、而重算 <60 公里 → 假（起点取错：住处坐标被在线查询解析到外地同名地方、等）
# 另一类（B，只列出来不算违例）：站点坐标离当天城市中心 ≥60 公里，却标成市内的“打车/步行”。
# 真实长途（郊外景点、跨城）重算也 ≥60，不会被报。
import json, math, re, sys, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_args = [a for a in sys.argv[1:] if not a.startswith('-')]
ROUTES = _args[0] if _args else os.path.join(ROOT, 'build/routes.js')
VERBOSE = '-v' in sys.argv
GEO = json.load(open(os.environ.get('ZOUNI_POIS') or os.path.join(ROOT, 'data/geo/pois.json'), encoding='utf-8'))   # ZOUNI_POIS：只给自测用（拿修复前的坐标证明闸会红）
LIM = 60          # 公里：compile 里 ≥60 才写成“包车/自驾约”
KM_RE = re.compile(r'(\d+) 公里')


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def pt(city, key):
    g = GEO.get(city + '|' + key) if key else None
    return (g['lat'], g['lng']) if g and g.get('lat') is not None else None


def load():
    s = open(ROUTES, encoding='utf-8').read()
    return json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', s).group(1))


def scan(R):
    """返回 (A 类假车程, B 类可疑站点, 统计)"""
    fake, susp, tot = [], [], {'long_legs': 0, 'long_legs_city': 0}
    for rid, r in R.items():
        if not r.get('compiled'): continue
        for di, d in enumerate(r['days']):
            city = d.get('city') or ''
            center = pt(city, city)
            cur = None; rows = d['rows']
            ps = pt(city, r['days'][di - 1].get('stayName')) if di > 0 else None     # 昨晚住处（核对过、落在城市 60 公里内才认）
            prev_stay = ps if ps and center and km(ps, center) < 60 else None
            moved = di > 0 and (r['days'][di - 1].get('city') or '') != city   # 换城市的搬家日：第一段从上一座城来，长是真的，不判
            for i, w in enumerate(rows):
                if w['type'] == 'dep':
                    m = KM_RE.search(w.get('how') or '')
                    to = w.get('to')
                    if to in ('住处', '回程', '吃晚饭'):
                        cur = None; continue
                    nxt = next((x for x in rows[i + 1:i + 4] if x['type'] in ('see', 'fun', 'eat') and (x.get('name') or x.get('place') or '').split(' · ')[0] == to), None)   # 车程和到达之间可能插着午饭行
                    tp = pt(city, (nxt or {}).get('poi') or (nxt or {}).get('name')) if nxt else None
                    if m and int(m.group(1)) >= LIM:
                        tot['long_legs'] += 1; tot['long_legs_city'] += 0 if r.get('drive') else 1
                        a = cur or (None if moved else (prev_stay or center))
                        if a and tp:
                            true_km = km(a, tp) * 1.25
                            if true_km < LIM and true_km <= 0.5 * int(m.group(1)):   # 重算也接近 60 的是临界（台儿庄 60/60），不报
                                fake.append({'id': rid, 'drive': bool(r.get('drive')), 'day': di + 1, 'city': city, 'to': to, 'how': w['how'],
                                             'claimed': int(m.group(1)), 'true': round(true_km), 'from': '上一站' if cur else '住处/城市中心', 'label': r['label'], 'top': r.get('driveTop')})
                    if tp and center and km(center, tp) >= LIM and not r.get('drive') and (w.get('how') or '').startswith(('打车', '步行')):
                        susp.append({'id': rid, 'day': di + 1, 'city': city, 'to': to, 'how': w['how'], 'center_km': round(km(center, tp))})
                elif w['type'] in ('see', 'fun', 'eat'):
                    p = pt(city, w.get('poi') or w.get('name'))
                    if p: cur = p
    return fake, susp, tot


def main():
    R = load()
    fake, susp, tot = scan(R)
    routes = sorted({f['id'] for f in fake})
    print(f'假长车程：{len(fake)} 条，涉及 {len(routes)} 条线（≥60 公里车程共 {tot["long_legs"]} 条，其中非自驾城市线 {tot["long_legs_city"]} 条；假的里非自驾 {sum(1 for f in fake if not f["drive"])} 条）')
    lim = len(fake) if VERBOSE else 20
    for f in fake[:lim]:
        print(f"  {f['id']} D{f['day']} {f['city']} → {f['to']}｜{f['how']}｜坐标重算 {f['true']} 公里（起点：{f['from']}）")
    if len(fake) > lim: print(f'  …另有 {len(fake) - lim} 条（加 -v 看全部）')
    if VERBOSE:
        print(f'可疑站点（B 类，不算违例；离城市中心 ≥60 公里却写打车/步行）：{len(susp)}')
        for f in susp[:30]: print(f"  {f['id']} D{f['day']} {f['city']} → {f['to']}｜{f['how']}｜离中心 {f['center_km']} 公里")
    sys.exit(1 if fake else 0)


if __name__ == '__main__':
    main()
