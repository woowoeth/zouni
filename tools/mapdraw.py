# 路线示意图：真实省界 / 国界做底图，平滑路线，天数圆章，地名避让，比例尺
import json, math, os, re, html

E = lambda s: html.escape(str(s if s is not None else ''), quote=True)
BASE = []          # [(名字, 'cn'/'w', [环, ...], 外框)]


def _rings(geom):
    t = geom['type']; cs = geom['coordinates']
    if t == 'Polygon': return [cs[0]]
    if t == 'MultiPolygon': return [p[0] for p in cs]
    return []


def load_base():
    if BASE: return BASE
    d = 'data/geo/base'
    if os.path.exists(f'{d}/cn_prov.json'):
        for f in json.load(open(f'{d}/cn_prov.json'))['features']:
            nm = f['properties'].get('name') or ''
            for r in _rings(f['geometry']):
                if len(r) < 4: continue
                xs = [p[0] for p in r]; ys = [p[1] for p in r]
                BASE.append((nm, 'cn', r, (min(xs), min(ys), max(xs), max(ys))))
    if os.path.exists(f'{d}/ne50.json'):
        for f in json.load(open(f'{d}/ne50.json'))['features']:
            pr = f['properties']; nm = pr.get('NAME_ZH') or pr.get('NAME') or ''
            if pr.get('ISO_A2') in ('CN', 'TW') or nm in ('中华人民共和国', '中国', '台湾'): continue   # 中国用省界那份
            for r in _rings(f['geometry']):
                if len(r) < 4: continue
                xs = [p[0] for p in r]; ys = [p[1] for p in r]
                BASE.append((nm, 'w', r, (min(xs), min(ys), max(xs), max(ys))))
    return BASE


def merc(lat): return math.degrees(math.log(math.tan(math.pi / 4 + math.radians(max(-85, min(85, lat))) / 2)))


def rdp(pts, eps):
    if len(pts) < 3: return pts
    a, b = pts[0], pts[-1]
    if abs(a[0] - b[0]) + abs(a[1] - b[1]) < 1e-9:            # 闭合的环：从离起点最远的点拆成两段
        k = max(range(len(pts)), key=lambda i: (pts[i][0] - a[0]) ** 2 + (pts[i][1] - a[1]) ** 2)
        if k in (0, len(pts) - 1): return pts[:1]
        return rdp(pts[:k + 1], eps)[:-1] + rdp(pts[k:], eps)
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1e-9
    i_, dmax = 0, 0
    for i in range(1, len(pts) - 1):
        d = abs(dy * pts[i][0] - dx * pts[i][1] + b[0] * a[1] - b[1] * a[0]) / L
        if d > dmax: i_, dmax = i, d
    if dmax > eps: return rdp(pts[:i_ + 1], eps)[:-1] + rdp(pts[i_:], eps)
    return [a, b]


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))


def smooth(pts):
    """穿过各点的平滑曲线（Catmull-Rom 转三次贝塞尔）"""
    if len(pts) < 2: return ''
    d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]; p1 = pts[i]; p2 = pts[i + 1]; p3 = pts[i + 2] if i + 2 < len(pts) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6); c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}'
    return d


def render(days, title, home=None, W=390, H=290, uid='m'):
    """days: [[(lat, lng, 名字, 类型), ...], ...]；home: 本省 / 本国名字（底图上深一点）"""
    allp = [p for d in days for p in d]
    if len(allp) < 2: return '', []
    lats = [p[0] for p in allp]; lngs = [p[1] for p in allp]
    my0, my1 = merc(min(lats)), merc(max(lats)); x0, x1 = min(lngs), max(lngs)
    span_x = max(x1 - x0, .12); span_y = max(my1 - my0, .12)
    pad = 30
    sc = min((W - 2 * pad) / span_x, (H - 2 * pad - 16) / span_y)
    cx = (x0 + x1) / 2; cy = (my0 + my1) / 2
    P = lambda la, lo: (W / 2 + (lo - cx) * sc, (H - 16) / 2 + 4 - (merc(la) - cy) * sc)
    # 画面对应的经纬度范围（多留一圈）
    vx0 = cx - (W / 2) / sc - 1; vx1 = cx + (W / 2) / sc + 1
    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{E(title)} 路线示意图">',
         f'<defs><clipPath id="c{uid}"><rect width="{W}" height="{H}"/></clipPath></defs><rect width="{W}" height="{H}" fill="#e5ebeb"/><g clip-path="url(#c{uid})">']
    eps = 0.9
    for nm, src, ring, (bx0, by0, bx1, by1) in load_base():
        if bx1 < vx0 or bx0 > vx1: continue
        if merc(by1) < cy - (H / 2) / sc - 1 or merc(by0) > cy + (H / 2) / sc + 1: continue
        pts = [P(la, lo) for lo, la in ring]
        if max(abs(pts[0][0] - p[0]) for p in pts) < 1.5 and max(abs(pts[0][1] - p[1]) for p in pts) < 1.5: continue
        pts = rdp(pts, eps)
        if len(pts) < 3: continue
        hl = bool(home) and (home in nm or nm in (home or ''))
        o.append(f'<path d="M' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in pts) + f'Z" fill="{"#efe7d6" if hl else "#f6f3ec"}" stroke="#cfc6b3" stroke-width=".7" stroke-linejoin="round"/>')
    o.append('</g>')
    # 路线
    seq = [(P(la, lo), nm, tp, di) for di, d in enumerate(days) for (la, lo, nm, tp) in d]
    xy = [s[0] for s in seq]
    o.append(f'<path d="{smooth(xy)}" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" opacity=".85" vector-effect="non-scaling-stroke"/>')
    o.append(f'<path d="{smooth(xy)}" fill="none" stroke="#a63d27" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>')
    boxes = [(10, H - 30, 150, H - 6), (W - 36, 8, W - 6, 44)]
    legend = []; marks = []
    for (x, y), nm, tp, di in seq:
        if tp in ('see', 'fun'): o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.2" fill="#fff" stroke="#a63d27" stroke-width="1.6"/>')
    firsts = {}
    for (x, y), nm, tp, di in seq:
        if di not in firsts: firsts[di] = (x, y)
    for di, (x, y) in firsts.items():
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8.5" fill="#a63d27" stroke="#fff" stroke-width="1.5"/><text x="{x:.1f}" y="{y + 3.6:.1f}" text-anchor="middle" font-family="Noto Sans SC,sans-serif" font-size="10" font-weight="700" fill="#fff">{di + 1}</text>')
        boxes.append((x - 9, y - 9, x + 9, y + 9))
    # 地名：每个景点一次，放不下的进图下列表
    seen = set()
    for (x, y), nm, tp, di in seq:
        if not nm or tp not in ('see', 'fun') or nm in seen: continue
        seen.add(nm); legend.append(nm); num = len(legend)
        placed = False
        for fs in (11, 10):
            w = len(nm[:8]) * fs + 4
            for (lx, ly, anc) in ((x + 7, y + 4, 'start'), (x - 7, y + 4, 'end'), (x, y - 8, 'middle'), (x, y + fs + 7, 'middle'), (x + 6, y - 6, 'start'), (x - 6, y - 6, 'end'), (x + 6, y + fs + 5, 'start'), (x - 6, y + fs + 5, 'end')):
                bx0 = lx if anc == 'start' else lx - w if anc == 'end' else lx - w / 2; bx1 = bx0 + w; by0, by1 = ly - fs, ly + 3
                if bx0 < 6 or bx1 > W - 6 or by0 < 6 or by1 > H - 6: continue
                if any(not (bx1 < a or bx0 > c or by1 < b or by0 > d_) for a, b, c, d_ in boxes): continue
                boxes.append((bx0, by0, bx1, by1)); placed = True
                o.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-family="Noto Sans SC,sans-serif" font-size="{fs}" font-weight="600" fill="#2b2c28" paint-order="stroke" stroke="#f6f3ec" stroke-width="3" stroke-linejoin="round">{E(nm[:8])}</text>')
                break
            if placed: break
        if not placed:
            marks.append((x, y, num))
    # 比例尺：挑一个整数公里，长度 40–90 像素
    kmpx = km((lats[0], cx - 30 / sc), (lats[0], cx + 30 / sc)) / 60
    for nice in (1, 2, 5, 10, 20, 50, 100, 200, 500, 1000):
        if 40 <= nice / kmpx <= 110: break
    L = nice / kmpx
    o.append(f'<g font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59"><rect x="12" y="{H - 16}" width="{L:.0f}" height="3" fill="#2b2c28"/><rect x="{12 + L / 2:.0f}" y="{H - 16}" width="{L / 2:.0f}" height="3" fill="#f6f3ec" stroke="#2b2c28" stroke-width=".6"/><text x="{14 + L:.0f}" y="{H - 12}">{nice} 公里</text></g>')
    o.append(f'<g transform="translate({W - 20},26)"><path d="M0,-11 L5,5 L0,1.5 L-5,5 Z" fill="#2b2c28"/><text x="0" y="-14" text-anchor="middle" font-family="Noto Sans SC,sans-serif" font-size="9" font-weight="700" fill="#2b2c28">北</text></g>')
    o.append('</svg>')
    byday = []
    for di, d in enumerate(days):
        ns = []
        for (la, lo, nm, tp) in d:
            if nm and tp in ('see', 'fun') and nm not in ns: ns.append(nm)
        byday.append(ns)
    return ''.join(o), byday


def render_points(pts, title, home=None, dots=(), W=390, H=300, uid='d'):
    """目的地页：真实底图 + 每条线路一个点（名字是链接）+ 5A 小黑点"""
    allp = [(a, b) for a, b, _, _ in pts] + list(dots)
    if len(pts) < 2: return '', []
    lats = [p[0] for p in allp]; lngs = [p[1] for p in allp]
    my0, my1 = merc(min(lats)), merc(max(lats)); x0, x1 = min(lngs), max(lngs)
    pad = 34; sc = min((W - 2 * pad) / max(x1 - x0, .3), (H - 2 * pad) / max(my1 - my0, .3))
    cx = (x0 + x1) / 2; cy = (my0 + my1) / 2
    P = lambda la, lo: (W / 2 + (lo - cx) * sc, H / 2 - (merc(la) - cy) * sc)
    vx0 = cx - (W / 2) / sc - 1; vx1 = cx + (W / 2) / sc + 1
    o = [f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{E(title)}">',
         f'<defs><clipPath id="c{uid}"><rect width="{W}" height="{H}"/></clipPath></defs><rect width="{W}" height="{H}" fill="#e5ebeb"/><g clip-path="url(#c{uid})">']
    for nm, src, ring, (bx0, by0, bx1, by1) in load_base():
        if bx1 < vx0 or bx0 > vx1: continue
        if merc(by1) < cy - (H / 2) / sc - 1 or merc(by0) > cy + (H / 2) / sc + 1: continue
        q = [P(la, lo) for lo, la in ring]
        if max(abs(q[0][0] - p[0]) for p in q) < 1.5 and max(abs(q[0][1] - p[1]) for p in q) < 1.5: continue
        q = rdp(q, .9)
        if len(q) < 3: continue
        hl = bool(home) and (home in nm or nm in (home or ''))
        o.append(f'<path d="M' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in q) + f'Z" fill="{"#efe7d6" if hl else "#f6f3ec"}" stroke="#cfc6b3" stroke-width=".7" stroke-linejoin="round"/>')
    o.append('</g>')
    for la, lo in dots:
        x, y = P(la, lo); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#2b2c28" opacity=".35"/>')
    boxes = [(10, H - 28, 330, H - 6), (W - 36, 8, W - 6, 44)]; unl = []
    for la, lo, nm, href in pts:
        x, y = P(la, lo); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#fff" stroke="#a63d27" stroke-width="2"/>')
    for la, lo, nm, href in pts:
        x, y = P(la, lo); done = False
        for fs in (12, 10):
            w = len(nm) * fs + 6
            for (lx, ly, anc) in ((x + 8, y + 4, 'start'), (x - 8, y + 4, 'end'), (x, y - 9, 'middle'), (x, y + fs + 7, 'middle'), (x + 6, y - 7, 'start'), (x - 6, y - 7, 'end'), (x + 6, y + fs + 5, 'start'), (x - 6, y + fs + 5, 'end')):
                bx0 = lx if anc == 'start' else lx - w if anc == 'end' else lx - w / 2; bx1 = bx0 + w
                if bx0 < 8 or bx1 > W - 8 or ly - fs < 8 or ly + 3 > H - 8: continue
                if any(not (bx1 < a or bx0 > c or ly + 3 < b or ly - fs > d_) for a, b, c, d_ in boxes): continue
                boxes.append((bx0, ly - fs, bx1, ly + 3)); done = True
                o.append(f'<a href="{E(href)}" aria-label="{E(nm)}"><rect x="{min(bx0 - 2, (bx0 + bx1) / 2 - 24):.1f}" y="{ly - 30:.1f}" width="{max(w + 6, 48):.1f}" height="46" fill="#fff" fill-opacity="0"/><text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-family="Noto Sans SC,sans-serif" font-size="{fs}" font-weight="700" fill="#a63d27" paint-order="stroke" stroke="#f6f3ec" stroke-width="3" stroke-linejoin="round">{E(nm)}</text></a>')
                break
            if done: break
        if not done: unl.append((href, nm))
    o.append(f'<text x="12" y="{H - 12}" font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59" paint-order="stroke" stroke="#f6f3ec" stroke-width="3">红圈是排好的线路（点名字进去），小黑点是 5A 和世界遗产</text>')
    o.append(f'<g transform="translate({W - 20},26)"><path d="M0,-11 L5,5 L0,1.5 L-5,5 Z" fill="#2b2c28"/><text x="0" y="-14" text-anchor="middle" font-family="Noto Sans SC,sans-serif" font-size="9" font-weight="700" fill="#2b2c28">北</text></g></svg>')
    return ''.join(o), unl
