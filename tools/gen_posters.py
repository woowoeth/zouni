# 给没有手绘封面的行程生成插画封面（600×800，和现有海报同一画风：扁平、层叠、深色前景、纸面颗粒）
# 用法：python3 tools/gen_posters.py [输出目录，默认 site_src/posters]
import json, os, re, sys, math, random, hashlib

OUT = sys.argv[1] if len(sys.argv) > 1 else 'site_src/posters'
os.makedirs(OUT, exist_ok=True)
IT = json.load(open('data/itineraries.json'))['itineraries']
TR = {t['id']: t for t in json.load(open('data/catalog/trips.json'))['trips']}
W, H = 600, 800

PAL = {  # 季节配色：天空上、天空下、远山、近山、主色、点缀、前景
    'sp': dict(s1='#f4e6d8', s2='#e8c9b6', far='#c9b3a8', mid='#8f9a7a', main='#4f6233', acc='#d98a8a', gnd='#2d3027', sun='#fbefe2'),
    'su': dict(s1='#dbe9ee', s2='#a9c9d6', far='#8fb0bf', mid='#4f7d8a', main='#2f5c6b', acc='#e8c46a', gnd='#1f2b2e', sun='#fff6df'),
    'au': dict(s1='#f5dcb4', s2='#e3a46e', far='#c98d6e', mid='#a8735c', main='#6b4a38', acc='#e0a03a', gnd='#2a1f1a', sun='#fbe9c8'),
    'wi': dict(s1='#e6ebf0', s2='#bccadb', far='#a7b6c8', mid='#6f86a8', main='#3d4f6b', acc='#f4f6f8', gnd='#1e2430', sun='#f7f9fb'),
    'dusk': dict(s1='#f3c9b3', s2='#a77a8f', far='#8a6a7f', mid='#5a4a62', main='#3a2f45', acc='#f0b36a', gnd='#1d1a24', sun='#fde3c4'),
}
CATS = [  # 顺序即优先级
    ('museum', ('博物馆 ', '国宝', '三星堆')),
    ('mountain', ('雪山', '冰川', '神山', '冈仁波齐', '珠峰', '贡嘎', '梅里', '格聂', '四姑娘', '玉龙', '南迦巴瓦', '阿尼玛卿', '鱼子西', '日照金山')), ('snow', ('雪乡', '雾凇', '滑雪', '冰雪', '冰灯', '雪如意')),
    ('desert', ('沙漠', '沙坡', '鸣沙', '雅丹', '戈壁', '魔鬼城', '巴丹吉林', '沙湖', '瓦迪拉姆', '佩特拉', '死海', '迪拜')), ('terrace', ('梯田', '红土地')),
    ('canyon', ('峡谷', '嶂谷', '地缝', '大裂谷', '天坑')), ('grass', ('草原', '坝上', '牧场', '草甸', '那拉提', '呼伦贝尔', '乌兰布统')),
    ('sea', ('海岛', '岛', '海边', '海滨', '湾', '沙滩', '金滩', '涠洲', '三亚', '马尔代夫', '巴厘')),
    ('lake', ('湖', '海子', '措', '泊', '天池', '潭')), ('town', ('古城', '古镇', '老街', '村', '寨', '土楼', '水乡', '胡同')),
    ('temple', ('寺', '庙', '塔', '石窟', '佛', '宫', '陵')), ('forest', ('林海', '森林', '竹海', '胡杨', '红叶')),
    ('flower', ('花海', '油菜花', '杜鹃', '樱花', '桃花', '薰衣草')), ('mountain', ('山', '峰', '冰川', '雪山', '垭口')),
]


def season_of(t):
    b = ((t or {}).get('season') or {}).get('best')
    m = int(b[0][:2]) if b else 10
    return 'sp' if m in (3, 4, 5) else 'su' if m in (6, 7, 8) else 'au' if m in (9, 10, 11) else 'wi'


TIBET = {'xizang', 'qinghai'}
PAGODA_OK = {'japan', 'korea', 'vietnam'}


def category(it):
    text = ' '.join([it.get('label', ''), it.get('title', ''), it.get('kicker', '')] + [s['name'] + ' ' for d in it['days'] for s in d['stops']])
    cat = 'city'
    head = ' '.join([it.get('label', ''), it.get('title', ''), it.get('kicker', '')])
    for c, kws in CATS:
        if c == 'museum':
            if any(k.strip() in head for k in ('博物馆', '国宝', '三星堆')): cat = c; break
            continue
        if any(k in text for k in kws): cat = c; break
    hi = it['dest'] in TIBET or '高原' in it.get('kicker', '') or max((d.get('elev') or 0) for d in it['days']) >= 3000
    if hi and cat in ('temple', 'grass', 'city', 'town'): cat = 'mountain'       # 藏区不画汉式宝塔和蒙古包
    return cat


def ridge(rnd, y0, amp, step, rough=0.5):
    pts = []; y = y0
    for x in range(-20, W + 40, step):
        y += rnd.uniform(-amp, amp) * rough; y = max(y0 - amp * 2.2, min(y0 + amp * 1.2, y)); pts.append((x, y))
    d = f'M-20,{H} L' + ' L'.join(f'{x:.0f},{y:.0f}' for x, y in pts) + f' L{W + 40},{H} Z'
    return d


def peaks(rnd, base, n, hmin, hmax):
    xs = sorted(rnd.uniform(40, W - 40) for _ in range(n)); d = f'M-20,{base}'
    x0 = -20; tops = []
    for x in xs:
        h = rnd.uniform(hmin, hmax); w = rnd.uniform(90, 170); tops.append((x, base - h, w, h))
        d += f' L{x - w:.0f},{base} L{x - w * .35:.0f},{base - h * .7:.0f} L{x:.0f},{base - h:.0f} L{x + w * .3:.0f},{base - h * .72:.0f} L{x + w:.0f},{base}'
    return d + f' L{W + 20},{base} L{W + 20},{H} L-20,{H} Z', tops


def pagoda(cx, base, tiers, w0, col, acc):
    s = ''; y = base; w = w0
    for i in range(tiers):
        h = 26
        s += f'<rect x="{cx - w * .36:.0f}" y="{y - h:.0f}" width="{w * .72:.0f}" height="{h}" fill="{col}"/>'
        s += f'<path d="M{cx - w / 2:.0f},{y - h:.0f} Q{cx},{y - h - 16:.0f} {cx + w / 2:.0f},{y - h:.0f} L{cx + w * .42:.0f},{y - h - 6:.0f} L{cx - w * .42:.0f},{y - h - 6:.0f} Z" fill="{col}"/>'
        for k in range(3): s += f'<rect x="{cx - w * .2 + k * w * .16:.0f}" y="{y - h + 8:.0f}" width="5" height="9" fill="{acc}" opacity=".85"/>'
        y -= h + 6; w *= .84
    s += f'<rect x="{cx - 2}" y="{y - 30:.0f}" width="4" height="34" fill="{col}"/>'
    return s


def poster(rid, it):
    t = TR.get(rid, {}); seed = int(hashlib.md5(rid.encode()).hexdigest()[:8], 16); rnd = random.Random(seed)
    se = season_of(t); cat = category(it)
    if rnd.random() < .25 and cat not in ('snow', 'museum'): se = 'dusk'
    yurt_ok = it['dest'] in ('neimenggu', 'xinjiang', 'mongolia')
    pagoda_ok = it['dest'] not in TIBET and (it['dest'] in PAGODA_OK or len(it['dest']) and it['dest'] not in ('thailand', 'malaysia', 'indonesia', 'cambodia', 'laos', 'philippines', 'nepal', 'bhutan', 'india', 'maldives', 'uzbekistan', 'turkey', 'uae', 'mongolia', 'srilanka', 'georgia', 'jordan', 'kazakhstan', 'singapore'))
    P = PAL[se]
    g = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
         f'<defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["s1"]}"/><stop offset="1" stop-color="{P["s2"]}"/></linearGradient>'
         f'<linearGradient id="wt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{P["mid"]}"/><stop offset="1" stop-color="{P["gnd"]}"/></linearGradient>'
         f'<filter id="gr"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="{seed % 97}"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 .07 0"/><feComposite in2="SourceGraphic" operator="in"/></filter></defs>',
         f'<rect width="{W}" height="{H}" fill="url(#sk)"/>']
    sx, sy = rnd.uniform(120, 480), rnd.uniform(110, 230)
    g.append(f'<circle cx="{sx:.0f}" cy="{sy:.0f}" r="{rnd.uniform(34, 56):.0f}" fill="{P["sun"]}" opacity=".9"/>')
    horizon = 520
    for k in range(rnd.randint(2, 4)):
        cx, cy, w_ = rnd.uniform(0, W), rnd.uniform(70, 300), rnd.uniform(80, 160)
        g.append(f'<ellipse cx="{cx:.0f}" cy="{cy:.0f}" rx="{w_:.0f}" ry="{w_ * .16:.0f}" fill="#fff" opacity=".35"/><ellipse cx="{cx + w_ * .3:.0f}" cy="{cy - 8:.0f}" rx="{w_ * .5:.0f}" ry="{w_ * .14:.0f}" fill="#fff" opacity=".3"/>')
    for k in range(rnd.randint(2, 5)):
        bx, by, bw = rnd.uniform(80, 520), rnd.uniform(120, 320), rnd.uniform(8, 14)
        g.append(f'<path d="M{bx - bw:.0f},{by:.0f} q{bw / 2:.0f},-{bw / 2:.0f} {bw:.0f},0 q{bw / 2:.0f},-{bw / 2:.0f} {bw:.0f},0" fill="none" stroke="{PAL[se]["gnd"]}" stroke-width="2" opacity=".55"/>')
    g.append(f'<path d="{ridge(rnd, 360, 30, 40)}" fill="{P["far"]}" opacity=".55"/>')
    if cat in ('mountain', 'snow', 'lake', 'canyon', 'forest', 'temple'):
        d, tops = peaks(rnd, 470, rnd.randint(2, 3), 160, 290)
        g.append(f'<path d="{d}" fill="{P["mid"]}"/>')
        snowy = cat == 'snow' or se == 'wi' or (cat == 'mountain' and (it['dest'] in TIBET or max((x.get('elev') or 0) for x in it['days']) >= 2500 or any(k in ' '.join(s['name'] for dd in it['days'] for s in dd['stops']) for k in ('雪山', '冰川', '贡嘎', '梅里', '冈仁波齐', '珠峰', '玉龙', '四姑娘', '格聂', '南迦巴瓦', '阿尼玛卿'))))
        if snowy:
            for x, ty, w, h in tops:
                k = .3
                g.append(f'<path d="M{x - w * .35 * k * 1.6:.0f},{ty + h * .7 * k * 1.1:.0f} L{x:.0f},{ty:.0f} L{x + w * .3 * k * 1.6:.0f},{ty + h * .72 * k * 1.1:.0f} L{x + w * .1:.0f},{ty + h * .18:.0f} L{x:.0f},{ty + h * .26:.0f} L{x - w * .12:.0f},{ty + h * .17:.0f} Z" fill="#f4f6f8" opacity=".95"/>')
    else:
        g.append(f'<path d="{ridge(rnd, 440, 26, 30)}" fill="{P["mid"]}"/>')
    main = P['main']; acc = P['acc']
    if cat == 'desert':
        for k, (y, c) in enumerate(((470, P['far']), (520, P['mid']), (580, main))):
            a = rnd.uniform(40, 90); ph = rnd.uniform(0, 6)
            pts = ' '.join(f'{x},{y + a * math.sin(x / rnd.uniform(110, 150) + ph):.0f}' for x in range(-20, W + 40, 20))
            g.append(f'<path d="M-20,{H} L{pts} L{W + 40},{H} Z" fill="{c}"/>')
        for k in range(rnd.randint(2, 3)):
            cx = 180 + k * 46; cy = 548 - k * 6
            g.append(f'<path d="M{cx},{cy} q8,-18 18,-6 q6,-12 16,-2 l6,6 h-4 l-4,-4 l-2,18 h-3 l-1,-14 h-14 l-2,14 h-3 l-1,-16 z" fill="{P["gnd"]}"/>')
    elif cat in ('lake', 'sea'):
        g.append(f'<rect x="0" y="{horizon}" width="{W}" height="{H - horizon}" fill="url(#wt)"/>')
        for k in range(14):
            y = horizon + 18 + k * 14; x = sx + rnd.uniform(-30, 30); w = rnd.uniform(30, 90) * (1 - k / 18)
            g.append(f'<rect x="{x - w / 2:.0f}" y="{y}" width="{w:.0f}" height="2" fill="{P["sun"]}" opacity=".55"/>')
        if cat == 'sea':
            ix = rnd.uniform(80, 420)
            g.append(f'<path d="M{ix},{horizon} q60,-70 150,-20 q30,10 50,20 z" fill="{main}"/>')
            bx = rnd.uniform(380, 520)
            g.append(f'<path d="M{bx},{horizon + 70} h44 l-8,10 h-30 z M{bx + 20},{horizon + 70} v-40 l18,34 z" fill="{P["gnd"]}"/>')
        else:
            g.append(f'<path d="M0,{horizon} L{W},{horizon} L{W},{horizon + 3} L0,{horizon + 3} Z" fill="{P["sun"]}" opacity=".4"/>')
    elif cat == 'grass':
        for k, (y, c) in enumerate(((470, P['mid']), (530, main))):
            pts = ' '.join(f'{x},{y + 30 * math.sin(x / 140 + k * 2 + seed % 7):.0f}' for x in range(-20, W + 40, 20))
            g.append(f'<path d="M-20,{H} L{pts} L{W + 40},{H} Z" fill="{c}"/>')
        for k in range(rnd.randint(2, 4) if yurt_ok else 0):
            cx = rnd.uniform(90, 510); cy = 520 + rnd.uniform(-10, 10)
            g.append(f'<path d="M{cx - 22:.0f},{cy:.0f} v-18 q22,-22 44,0 v18 z" fill="#f4efe6"/><path d="M{cx - 4:.0f},{cy:.0f} v-12 h8 v12 z" fill="{P["gnd"]}"/>')
        for k in range(rnd.randint(4, 9)):
            hx = rnd.uniform(60, 540); hy = 540 + rnd.uniform(-10, 30)
            g.append(f'<ellipse cx="{hx:.0f}" cy="{hy:.0f}" rx="9" ry="5" fill="#f4efe6" opacity=".9"/>')
    elif cat == 'terrace':
        for k in range(9):
            y = 470 + k * 28; a = 14 + k * 2
            pts = ' '.join(f'{x},{y + a * math.sin(x / 120 + k * .4):.0f}' for x in range(-20, W + 40, 20))
            g.append(f'<path d="M-20,{H} L{pts} L{W + 40},{H} Z" fill="{[P["mid"], main][k % 2]}" opacity="{.75 + k * .03:.2f}"/>')
            g.append(f'<polyline points="{pts}" fill="none" stroke="{P["sun"]}" stroke-width="2" opacity=".45"/>')
    elif cat == 'canyon':
        g.append(f'<path d="M-20,{H} L-20,300 L120,330 L160,480 L230,620 L250,{H} Z" fill="#8a4a32"/><path d="M{W + 20},{H} L{W + 20},280 L470,320 L430,470 L370,620 L350,{H} Z" fill="#9a5a3a"/>')
        g.append(f'<path d="M250,{H} L300,560 L350,{H} Z" fill="{P["mid"]}" opacity=".8"/>')
    elif cat == 'town':
        g.append(f'<rect x="0" y="{horizon + 40}" width="{W}" height="{H}" fill="url(#wt)"/>')
        x = -10
        while x < W:
            w = rnd.uniform(70, 120); h = rnd.uniform(60, 110); y = horizon + 40
            g.append(f'<rect x="{x:.0f}" y="{y - h:.0f}" width="{w:.0f}" height="{h:.0f}" fill="#efe9dc"/>')
            g.append(f'<path d="M{x - 8:.0f},{y - h:.0f} Q{x + w / 2:.0f},{y - h - 26:.0f} {x + w + 8:.0f},{y - h:.0f} L{x + w:.0f},{y - h + 10:.0f} L{x:.0f},{y - h + 10:.0f} Z" fill="{P["gnd"]}"/>')
            for k in range(2): g.append(f'<rect x="{x + 14 + k * (w - 40) / 1.2:.0f}" y="{y - h + 26:.0f}" width="12" height="16" fill="{P["gnd"]}" opacity=".75"/>')
            if rnd.random() < .5: g.append(f'<circle cx="{x + w / 2:.0f}" cy="{y - h + 22:.0f}" r="6" fill="{acc}"/>')
            x += w + rnd.uniform(4, 14)
        g.append(f'<path d="M140,{horizon + 120} Q300,{horizon + 30} 460,{horizon + 120}" fill="none" stroke="#efe9dc" stroke-width="10"/>')
    elif cat == 'city':
        x = 0
        while x < W:
            w = rnd.uniform(36, 70); h = rnd.uniform(80, 220)
            g.append(f'<rect x="{x:.0f}" y="{horizon - h:.0f}" width="{w:.0f}" height="{h + 10:.0f}" fill="{[P["mid"], main][int(x) % 2]}"/>')
            for yy in range(int(horizon - h + 12), horizon - 10, 22):
                for xx in range(int(x + 8), int(x + w - 8), 14):
                    if rnd.random() < .45: g.append(f'<rect x="{xx}" y="{yy}" width="6" height="9" fill="{P["sun"]}" opacity=".6"/>')
            x += w + 2
        if pagoda_ok: g.append(pagoda(rnd.uniform(160, 440), horizon, 5, 130, P['gnd'], acc))
        g.append(f'<rect x="0" y="{horizon}" width="{W}" height="{H - horizon}" fill="url(#wt)"/>')
    elif cat == 'temple':
        g.append(f'<path d="M60,580 Q300,430 540,580 Z" fill="{main}"/>')
        g.append(pagoda(300, 490, rnd.randint(5, 7), 176, P['gnd'], acc))
    elif cat == 'forest' or cat == 'flower':
        g.append(f'<path d="{ridge(rnd, 520, 20, 30)}" fill="{main}"/>')
        for k in range(rnd.randint(7, 11)):
            cx = rnd.uniform(0, W); h = rnd.uniform(70, 150); y = 560 + rnd.uniform(-20, 30)
            col = acc if (cat == 'forest' and se == 'au' and rnd.random() < .6) else P['gnd']
            g.append(f'<path d="M{cx:.0f},{y - h:.0f} L{cx + h * .32:.0f},{y:.0f} L{cx - h * .32:.0f},{y:.0f} Z" fill="{col}" opacity=".92"/>')
        if cat == 'flower':
            for k in range(160):
                g.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(580, 700):.0f}" r="{rnd.uniform(2, 5):.1f}" fill="{acc}" opacity=".85"/>')
    elif cat == 'snow':
        g.append(f'<path d="{ridge(rnd, 520, 18, 30)}" fill="#f4f6f8"/>')
        for k in range(4):
            cx = 120 + k * 110 + rnd.uniform(-20, 20); y = 560
            g.append(f'<rect x="{cx - 34:.0f}" y="{y - 44}" width="68" height="44" fill="#6b4a38"/><path d="M{cx - 46:.0f},{y - 40} L{cx:.0f},{y - 84} L{cx + 46:.0f},{y - 40} Z" fill="#f7f9fb"/><rect x="{cx - 8:.0f}" y="{y - 26}" width="16" height="16" fill="#f0b36a"/>')
        for k in range(90): g.append(f'<circle cx="{rnd.uniform(0, W):.0f}" cy="{rnd.uniform(0, 600):.0f}" r="{rnd.uniform(1.5, 3.5):.1f}" fill="#fff" opacity=".8"/>')
    elif cat == 'museum':
        cx, base = 300, 560
        g.append(f'<rect x="150" y="{base}" width="300" height="24" fill="{P["gnd"]}"/><rect x="180" y="{base - 12}" width="240" height="12" fill="{main}"/>')
        g.append(f'<path d="M{cx - 110},{base - 160} h220 q-6,110 -60,140 h-100 q-54,-30 -60,-140 z" fill="#7a5a3e"/>'
                 f'<path d="M{cx - 120},{base - 172} h240 v14 h-240 z" fill="#6b4a32"/>'
                 f'<path d="M{cx - 92},{base - 172} v-34 h18 v34 z M{cx + 74},{base - 172} v-34 h18 v34 z" fill="#6b4a32"/>'
                 f'<path d="M{cx - 70},{base - 20} l-22,32 h14 l20,-32 z M{cx + 70},{base - 20} l22,32 h-14 l-20,-32 z M{cx - 8},{base - 20} v32 h16 v-32 z" fill="#5a4030"/>')
        for k in range(6): g.append(f'<path d="M{cx - 90 + k * 36},{base - 120} q18,-16 36,0" fill="none" stroke="#a8735c" stroke-width="3" opacity=".7"/>')
    # 深色前景（放标题的地方）
    g.append(f'<path d="M-20,{H} L-20,{600 + rnd.uniform(-10, 10):.0f} Q{W / 2},{580 + rnd.uniform(-15, 15):.0f} {W + 20},{606 + rnd.uniform(-10, 10):.0f} L{W + 20},{H} Z" fill="{P["gnd"]}"/>')
    for k in range(6):
        y = 640 + k * 24
        g.append(f'<rect x="{rnd.uniform(0, 400):.0f}" y="{y}" width="{rnd.uniform(60, 200):.0f}" height="1.5" fill="#fff" opacity=".05"/>')
    g.append(f'<rect width="{W}" height="{H}" filter="url(#gr)" opacity=".9"/></svg>')
    return '\n'.join(g), cat, se


if __name__ == '__main__':
    stat = {}
    for rid, it in IT.items():
        svg, cat, se = poster(rid, it)
        open(os.path.join(OUT, rid + '.svg'), 'w', encoding='utf-8').write(svg)
        stat[cat] = stat.get(cat, 0) + 1
    print('生成封面', sum(stat.values()), '张', stat)
