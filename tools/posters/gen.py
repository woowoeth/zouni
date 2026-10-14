import math, random, os

W, H = 600, 800
OUT = '/mnt/user-data/outputs/zouni-posters'
os.makedirs(OUT, exist_ok=True)


def f(v):
    return f'{v:.1f}'


def pts(p):
    return ' '.join(f'{f(x)},{f(y)}' for x, y in p)


def smooth(p):
    d = f'M{f(p[0][0])},{f(p[0][1])}'
    for i in range(len(p) - 1):
        p0 = p[i - 1] if i > 0 else p[i]
        p1, p2 = p[i], p[i + 1]
        p3 = p[i + 2] if i + 2 < len(p) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f' C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])}'
    return d


class S:
    def __init__(self, seed):
        self.e = []
        self.defs = []
        self.r = random.Random(seed)

    def add(self, s):
        self.e.append(s)

    def rect(self, x, y, w, h, c, op=1, rx=0):
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(rx)}" fill="{c}" opacity="{op}"/>')

    def poly(self, p, c, op=1):
        self.add(f'<polygon points="{pts(p)}" fill="{c}" opacity="{op}"/>')

    def path(self, d, c, op=1, stroke=None, sw=0, cap='round'):
        if stroke:
            self.add(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}" stroke-linejoin="round" opacity="{op}"/>')
        else:
            self.add(f'<path d="{d}" fill="{c}" opacity="{op}"/>')

    def circ(self, x, y, r, c, op=1):
        self.add(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="{c}" opacity="{op}"/>')

    def line(self, x1, y1, x2, y2, c, sw=1.5, op=1):
        self.add(f'<line x1="{f(x1)}" y1="{f(y1)}" x2="{f(x2)}" y2="{f(y2)}" stroke="{c}" stroke-width="{sw}" stroke-linecap="round" opacity="{op}"/>')

    # ---------- 通用部件 ----------
    def sky(self, bands):
        y = 0
        for h, c in bands:
            self.rect(0, y, W, h + 1, c)
            y += h

    def sun(self, x, y, r, c, halo):
        for k, op in ((2.0, .10), (1.6, .16), (1.3, .26)):
            self.circ(x, y, r * k, halo, op)
        self.circ(x, y, r, c)

    def birds(self, x, y, n, c, spread=60):
        for _ in range(n):
            bx, by, s = x + self.r.uniform(-spread, spread), y + self.r.uniform(-spread * .5, spread * .5), self.r.uniform(5, 9)
            self.path(f'M{f(bx - s)},{f(by - s * .4)} Q{f(bx - s * .4)},{f(by - s * .6)} {f(bx)},{f(by)} Q{f(bx + s * .4)},{f(by - s * .6)} {f(bx + s)},{f(by - s * .4)}', None, 1, c, 1.6)

    def cloud(self, x, y, w, c, shade):
        h = w * .22
        self.rect(x, y, w, h * .55, c, 1, h * .27)
        n = max(3, int(w / 40))
        for i in range(n):
            cx = x + w * (i + .5) / n
            self.circ(cx, y + h * .1, h * (.45 + .25 * math.sin(i * 1.7 + w)), c)
        self.rect(x + w * .08, y + h * .35, w * .84, h * .12, shade, .55, h * .06)

    def peak(self, cx, top, base, hw, light, shadow, snow, depth=.32, steps=7):
        r = self.r
        L = [(cx - hw, base)]
        for i in range(1, steps):
            t = i / steps
            L.append((cx - hw * (1 - t), base - (base - top) * t + r.uniform(-7, 7) * (1 - t)))
        R = []
        for i in range(1, steps):
            t = i / steps
            R.append((cx + hw * t, top + (base - top) * t + r.uniform(-7, 7) * t))
        full = L + [(cx, top)] + R + [(cx + hw, base)]
        self.poly(full, light)
        spine = [(cx, top)]
        for i in range(1, 6):
            t = i / 6
            spine.append((cx + hw * .12 * t + r.uniform(-5, 5), top + (base - top) * t))
        sp = spine + [(cx + hw * .12, base), (cx + hw, base)] + list(reversed(R))
        self.poly(sp, shadow)
        if snow:
            d = (base - top) * depth
            cap = [(x, y) for x, y in L if y < top + d] + [(cx, top)] + [(x, y) for x, y in R if y < top + d]
            cap = [(cx - hw * (d / (base - top)), top + d)] + cap + [(cx + hw * (d / (base - top)), top + d)]
            zig = []
            x0, x1 = cap[-1][0], cap[0][0]
            n = 9
            for i in range(n + 1):
                x = x0 + (x1 - x0) * i / n
                zig.append((x, top + d * (.62 + .38 * (i % 2)) + r.uniform(-4, 4)))
            self.poly(cap + zig, snow)
            # 雪面上的阴影一侧
            sh = [(cx, top)] + [(x, y) for x, y in R if y < top + d] + [(cap[-1][0], top + d * .8), (cx + hw * .1, top + d * .7)]
            self.poly(sh, shadow, .35)
            for k in range(5):
                gx = cx - hw * .3 + k * hw * .14
                self.line(gx, top + d * .4, gx + r.uniform(-10, 10), top + d * .9, shadow, 1.2, .25)

    def ridge(self, x0, x1, y, amp, n, seed, rough=.55):
        rr = random.Random(seed)
        p = [(x0, y + rr.uniform(-amp, amp) * .3), (x1, y + rr.uniform(-amp, amp) * .3)]
        a = amp
        for _ in range(n):
            q = [p[0]]
            for i in range(len(p) - 1):
                (xa, ya), (xb, yb) = p[i], p[i + 1]
                q += [((xa + xb) / 2, (ya + yb) / 2 + rr.uniform(-a, a)), (xb, yb)]
            p = q
            a *= rough
        return p

    def range_(self, y, amp, c, seed, bottom=H, n=6):
        p = self.ridge(-20, W + 20, y, amp, n, seed)
        self.poly(p + [(W + 20, bottom), (-20, bottom)], c)

    def flags(self, x0, y0, x1, y1, sag, n, cols, size=12):
        self.path(f'M{f(x0)},{f(y0)} Q{f((x0 + x1) / 2)},{f((y0 + y1) / 2 + sag)} {f(x1)},{f(y1)}', None, 1, '#3b2a22', 1.4)
        for i in range(1, n):
            t = i / n
            x = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * (x0 + x1) / 2 + t * t * x1
            y = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * ((y0 + y1) / 2 + sag) + t * t * y1
            c = cols[i % len(cols)]
            s = size * self.r.uniform(.85, 1.1)
            self.poly([(x - s * .45, y), (x + s * .45, y), (x + s * .5, y + s * 1.1), (x - s * .4, y + s * 1.05)], c)

    def reflections(self, y0, y1, c, n, op=.5, xr=(0, W)):
        for _ in range(n):
            y = self.r.uniform(y0, y1)
            x = self.r.uniform(*xr)
            w = self.r.uniform(14, 70)
            self.rect(x, y, w, self.r.uniform(1.2, 2.6), c, op * self.r.uniform(.5, 1), 1.2)

    def tree_round(self, x, y, r, cols, trunk=None):
        if trunk:
            self.rect(x - r * .08, y, r * .16, r * .9, trunk)
        for k in range(7):
            self.circ(x + self.r.uniform(-r * .55, r * .55), y + self.r.uniform(-r * .5, r * .25), r * self.r.uniform(.45, .7), cols[k % len(cols)])

    def conifer(self, x, y, h, c, c2=None):
        w = h * .32
        for k in range(3):
            t = k / 3
            self.poly([(x, y - h + h * t * .55), (x - w * (.55 + t * .45), y - h * .35 + h * t * .3), (x + w * (.55 + t * .45), y - h * .35 + h * t * .3)], c)
        if c2:
            self.poly([(x, y - h), (x + w * .9, y - h * .05), (x, y - h * .05)], c2, .35)
        self.rect(x - 1.5, y - h * .08, 3, h * .12, '#3b2a22')

    def grain(self, seed):
        self.add(f'<rect width="{W}" height="{H}" filter="url(#g{seed})" opacity=".55"/>')

    def mark(self):
        return len(self.e)

    def mirror(self, start, axis, y0, y1, op=.28, end=None):
        """把 start 之后画的东西沿水面 axis 翻转，只露在 y0–y1 这段水里"""
        cid = f'c{len(self.defs)}'
        self.defs.append(f'<clipPath id="{cid}"><rect x="0" y="{f(y0)}" width="{W}" height="{f(y1 - y0)}"/></clipPath>')
        part = ''.join(self.e[start:end])
        self.add(f'<g clip-path="url(#{cid})"><g transform="translate(0,{f(2 * axis)}) scale(1,-1)" opacity="{op}">{part}</g></g>')

    def ground(self, y, c_top, c_bot):
        gid = f'gr{len(self.defs)}'
        self.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c_top}"/><stop offset="1" stop-color="{c_bot}"/></linearGradient>')
        self.add(f'<rect x="0" y="{f(y)}" width="{W}" height="{f(H - y)}" fill="url(#{gid})"/>')

    def ripples(self, y0, y1, c, n, op=.35):
        for _ in range(n):
            y = self.r.uniform(y0, y1)
            x = self.r.uniform(-20, W)
            w = self.r.uniform(30, 120)
            self.path(f'M{f(x)},{f(y)} q{f(w / 4)},-3 {f(w / 2)},0 t{f(w / 2)},0', None, op * self.r.uniform(.5, 1), c, 1.4)

    def tufts(self, y0, y1, c, n, h=(6, 14)):
        for _ in range(n):
            x, y, hh = self.r.uniform(0, W), self.r.uniform(y0, y1), self.r.uniform(*h)
            self.path(f'M{f(x)},{f(y)} l{f(-hh * .3)},{f(-hh)} M{f(x)},{f(y)} l0,{f(-hh * 1.15)} M{f(x)},{f(y)} l{f(hh * .35)},{f(-hh * .9)}', None, .9, c, 1.3)

    def svg(self, seed):
        defs = (f'<defs><filter id="g{seed}" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" seed="{seed}"/>'
                f'<feColorMatrix type="matrix" values="0 0 0 0 .1  0 0 0 0 .08  0 0 0 0 .06  0 0 0 .22 0"/></filter>' + ''.join(self.defs) + '</defs>')
        return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{defs}' + ''.join(self.e) + '</svg>'


# ================= 西藏 · 布达拉宫 =================
def xz7():
    s = S(7)
    s.sky([(180, '#f7e1b6'), (140, '#f4d39f'), (120, '#f0c58a'), (360, '#ebb978')])
    s.sun(440, 168, 64, '#e8763a', '#f2a65e')
    s.birds(330, 120, 6, '#5a3a2a', 50)
    s.cloud(40, 150, 170, '#fbeed6', '#e9cfa2')
    s.cloud(470, 300, 120, '#fbeed6', '#e9cfa2')
    s.peak(110, 250, 430, 150, '#a7b2c4', '#7f8ca3', '#f8f4ec')
    s.peak(300, 215, 430, 170, '#9eaabd', '#76849c', '#f8f4ec')
    s.peak(520, 240, 430, 150, '#a7b2c4', '#7f8ca3', '#f8f4ec')
    s.range_(400, 26, '#6f7d93', 71, 520)
    # 红山
    hill = [(-10, 530), (60, 492), (130, 452), (200, 420), (270, 404), (330, 402), (400, 414), (470, 446), (540, 486), (610, 530)]
    s.path(smooth(hill) + f' L610,560 L-10,560 Z', '#8a5a3c')
    for k in range(40):
        x = s.r.uniform(20, 580)
        y = 470 + abs(x - 300) * .18 + s.r.uniform(-25, 30)
        s.path(f'M{f(x)},{f(y)} q{f(s.r.uniform(8, 18))},{f(-s.r.uniform(2, 6))} {f(s.r.uniform(20, 34))},0', None, .7, '#6f452c', 2)
    for k in range(20):
        x = s.r.uniform(60, 540)
        y = 480 + abs(x - 300) * .15 + s.r.uniform(-20, 25)
        s.path(f'M{f(x)},{f(y)} q8,-4 16,0', None, .6, '#a5734f', 2)
    # 白宫三层
    white, wshade, win, red = '#f6efe2', '#e2d6c2', '#3b2a22', '#9b2c22'
    s.poly([(150, 470), (150, 428), (450, 428), (450, 470)], white)
    s.poly([(170, 428), (170, 378), (430, 378), (430, 428)], white)
    s.poly([(190, 378), (190, 336), (246, 336), (246, 378)], white)
    s.poly([(354, 378), (354, 336), (410, 336), (410, 378)], white)
    s.poly([(410, 336), (410, 470), (450, 470), (450, 428), (430, 428), (430, 378)], wshade, .55)
    # 台阶之字
    zz = [(160, 470)]
    for i in range(6):
        zz.append((160 + (i % 2) * 70, 470 - i * 8))
    s.path('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in [(162, 468), (230, 452), (176, 440), (240, 430)]), None, .8, '#d8ccb6', 3)
    s.path('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in [(440, 468), (372, 452), (424, 440), (360, 430)]), None, .8, '#d8ccb6', 3)
    # 白宫窗
    for row, (y0, x0, x1) in enumerate([(440, 252, 350), (454, 252, 350), (390, 180, 420), (404, 180, 420), (348, 198, 240), (360, 198, 240), (348, 360, 404), (360, 360, 404)]):
        x = x0
        while x < x1:
            s.poly([(x, y0), (x + 6, y0), (x + 5, y0 + 8), (x + 1, y0 + 8)], win)
            x += 13
    # 红宫
    s.poly([(246, 378), (246, 292), (354, 292), (354, 378)], red)
    s.poly([(246, 292), (354, 292), (354, 304), (246, 304)], '#4a2219')
    for k in range(18):
        s.rect(248 + k * 6, 292, 3, 12, '#2b130e', .8)
    s.poly([(330, 304), (354, 304), (354, 378), (330, 378)], '#7c2219', .6)
    for y0 in (314, 330, 346, 362):
        x = 254
        while x < 346:
            s.rect(x - 1.5, y0 - 1.5, 9, 11, '#f3ead9')
            s.rect(x, y0, 6, 8, '#2b1a14')
            x += 15
    # 金顶
    for x0, w0, y0 in ((252, 22, 280), (284, 32, 274), (326, 22, 280)):
        s.poly([(x0 - 4, y0 + 12), (x0 + w0 + 4, y0 + 12), (x0 + w0 - 2, y0 + 4), (x0 + 2, y0 + 4)], '#d9a441')
        s.poly([(x0 + 2, y0 + 4), (x0 + w0 - 2, y0 + 4), (x0 + w0 / 2, y0 - 6)], '#e6b85a')
        s.rect(x0 + w0 / 2 - 1.5, y0 - 16, 3, 10, '#d9a441')
        s.circ(x0 + w0 / 2, y0 - 17, 3, '#e6b85a')
    # 经幡
    s.flags(0, 92, 190, 150, 30, 15, ['#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f', '#f1c232'], 12)
    # 深色地面：城市剪影 + 倒影
    s.rect(0, 528, W, 272, '#2b3648')
    x = -10
    while x < W:
        w0, h0 = s.r.uniform(26, 54), s.r.uniform(10, 26)
        s.rect(x, 528 - h0, w0, h0 + 2, '#2b3648')
        s.rect(x + 4, 528 - h0 + 4, w0 - 8, 3, '#3a4760', .8)
        x += w0 + s.r.uniform(2, 8)
    s.reflections(548, 640, '#f2c48a', 26, .22)
    s.reflections(560, 600, '#e8763a', 8, .35, (380, 500))
    s.rect(0, 528, W, 2, '#45536b')
    s.grain(7)
    return s.svg(7)


# ================= 纳木错 · 日落 =================
def nam():
    s = S(11)
    s.sky([(150, '#f2c79a'), (110, '#efb084'), (110, '#e99a74'), (430, '#d98a6a')])
    s.sun(170, 402, 46, '#f8e2ae', '#f5c48b')
    s.cloud(300, 110, 200, '#f6d3ad', '#e5ae86')
    s.cloud(40, 210, 130, '#f6d3ad', '#e5ae86')
    for cx, top, hw in ((330, 300, 120), (450, 270, 150), (560, 310, 110), (230, 340, 90)):
        s.peak(cx, top, 455, hw, '#a08fae', '#776a92', '#f8e6dc', .36)
    s.range_(440, 12, '#6a5f84', 113, 470)
    s.rect(0, 462, W, 160, '#2f6c86')
    s.reflections(470, 610, '#7fb4c6', 40, .45)
    for k in range(16):
        y = 468 + k * 9
        w0 = 70 - k * 3.2
        s.rect(170 - w0 / 2 + s.r.uniform(-6, 6), y, w0, 3, '#f6c98b', .75 - k * .035, 1.5)
    # 扎西岛的石柱
    s.path('M40,622 L52,470 Q60,440 82,438 Q104,442 108,476 L120,622 Z', '#4b3b3d')
    s.path('M58,470 Q66,448 82,446 L86,622 L64,622 Z', '#5f4b4c', .9)
    s.path('M128,622 L136,520 Q142,498 158,498 Q174,502 176,530 L184,622 Z', '#4b3b3d')
    s.flags(84, 446, 160, 506, 26, 9, ['#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f', '#f1c232'], 10)
    s.flags(160, 506, 250, 560, 18, 9, ['#f1c232', '#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f'], 9)
    s.rect(0, 616, W, 184, '#26313d')
    for k in range(70):
        s.circ(s.r.uniform(0, W), s.r.uniform(626, 790), s.r.uniform(1.5, 4), '#3a4656', .8)
    for x0 in (380, 430):
        s.path(f'M{x0},612 q4,-12 18,-12 q12,0 16,8 l6,-4 l0,8 l-4,0 l0,8 l-6,0 l0,-6 l-18,0 l0,6 l-6,0 z', '#1f262f')
    s.grain(11)
    return s.svg(11)


# ================= 南疆 · 帕米尔 =================
def njg8():
    s = S(8)
    s.sky([(190, '#f5e6c6'), (150, '#f1dbb2'), (460, '#ecd09f')])
    s.sun(150, 150, 54, '#d9653b', '#eba068')
    s.birds(420, 110, 4, '#5a3a2a', 40)
    dome = [(30, 450), (90, 360), (160, 270), (230, 214), (300, 192), (370, 206), (440, 252), (510, 330), (580, 430)]
    s.path(smooth(dome) + ' L580,470 L30,470 Z', '#f6f3ec')
    s.path(smooth([(300, 192), (370, 206), (440, 252), (510, 330), (580, 430)]) + ' L580,470 L330,470 Q320,330 300,192 Z', '#cad6e1')
    for k in range(9):
        x = 140 + k * 40
        s.path(f'M{x},{220 + abs(x - 300) * .45} q{s.r.uniform(-14, 14)},70 {s.r.uniform(-20, 20)},150', None, .55, '#dde6ee', 2.4)
    s.range_(420, 30, '#a3876b', 81, 480)
    s.range_(445, 18, '#8d7259', 82, 500)
    s.rect(0, 470, W, 80, '#d8a031')
    for k in range(5):
        y0 = 478 + k * 14
        s.path(f'M-10,{y0} C120,{y0 + 18} 220,{y0 - 14} 320,{y0 + 6} S520,{y0 + 16} 620,{y0}', None, .85, '#eef3f4', 3 - k * .4)
    for k in range(60):
        s.circ(s.r.uniform(0, W), s.r.uniform(474, 548), s.r.uniform(1.5, 3.5), '#b7801f', .7)
    # 石头城
    base = 452
    s.path(f'M360,{base + 20} L380,{base - 10} L560,{base - 10} L590,{base + 20} Z', '#9a7a5c')
    x = 386
    while x < 556:
        s.rect(x, base - 30, 14, 22, '#8c6b4f')
        s.rect(x + 2, base - 36, 4, 6, '#8c6b4f')
        s.rect(x + 8, base - 36, 4, 6, '#8c6b4f')
        x += 22
    s.rect(420, base - 52, 20, 44, '#7d5f45')
    s.rect(500, base - 46, 18, 38, '#7d5f45')
    for x0 in (424, 432, 504, 511):
        s.rect(x0, base - 58, 4, 7, '#7d5f45')
    # 毡房
    for x0 in (90, 140):
        s.path(f'M{x0},{base + 14} q0,-18 18,-20 q18,2 18,20 Z', '#f4f1ea')
        s.rect(x0 + 14, base + 4, 8, 10, '#c8432f')
    s.rect(0, 548, W, 252, '#4a3524')
    s.reflections(560, 640, '#d8a031', 18, .18)
    s.grain(8)
    return s.svg(8)


# ================= 额济纳 · 胡杨 =================
def nm4():
    s = S(4)
    s.sky([(170, '#f8e7c2'), (150, '#f5d9a6'), (480, '#efc98a')])
    s.sun(450, 170, 58, '#e36b2c', '#ef9a55')
    s.path('M-10,420 C120,380 220,410 320,392 S520,370 610,396 L610,500 L-10,500 Z', '#ead0a0')
    s.path('M-10,450 C140,420 260,452 380,430 S540,420 610,440 L610,500 L-10,500 Z', '#dfb978')
    def poplar(x, y, sc, flip=1):
        s.path(f'M{x - 7 * sc},{y} C{x - 6 * sc},{y - 40 * sc} {x - 18 * sc * flip},{y - 70 * sc} {x - 4 * sc},{y - 110 * sc} L{x + 6 * sc},{y - 108 * sc} C{x + 10 * sc},{y - 70 * sc} {x + 4 * sc},{y - 40 * sc} {x + 8 * sc},{y} Z', '#6b4a2f')
        for bx, by, ex, ey in ((0, -80, -46, -128), (0, -95, 40, -140), (-6, -60, -60, -96), (4, -70, 52, -100)):
            s.path(f'M{x + bx * sc},{y + by * sc} Q{x + (bx + ex) / 2 * sc},{y + (by + ey) / 2 * sc - 8 * sc} {x + ex * sc},{y + ey * sc}', None, 1, '#6b4a2f', 5 * sc)
        for k in range(26):
            cx = x + s.r.uniform(-75, 75) * sc
            cy = y - 130 * sc + s.r.uniform(-40, 46) * sc
            col = s.r.choice(['#f2c14e', '#e5a21f', '#c9781c', '#f7d77a', '#e5a21f'])
            s.circ(cx, cy, s.r.uniform(13, 24) * sc, col)
        for k in range(10):
            s.circ(x + s.r.uniform(-60, 60) * sc, y - 150 * sc + s.r.uniform(-30, 10) * sc, s.r.uniform(6, 11) * sc, '#fbe3a0', .9)
    poplar(140, 500, 1.15)
    poplar(330, 494, 1.35, -1)
    poplar(500, 500, 1.0)
    s.rect(0, 498, W, 64, '#3e6f8a')
    for k in range(40):
        s.rect(s.r.uniform(0, W), s.r.uniform(504, 556), s.r.uniform(18, 60), s.r.uniform(2, 4), s.r.choice(['#f2c14e', '#e5a21f']), .45, 2)
    s.rect(0, 560, W, 240, '#4a3a2a')
    for k in range(8):
        y0 = 590 + k * 24
        s.path(f'M-10,{y0} C150,{y0 - 8} 300,{y0 + 8} 610,{y0 - 4}', None, .35, '#5e4a36', 2)
    s.grain(4)
    return s.svg(4)


# ================= 九寨沟 · 彩林 =================
def jz4():
    s = S(5)
    s.sky([(160, '#f2eadb'), (160, '#ece3d0'), (480, '#e6dcc6')])
    s.range_(220, 40, '#a9bdb2', 51, 420)
    s.rect(0, 250, W, 30, '#f4efe4', .7)
    s.range_(300, 50, '#7e9b8c', 52, 470)
    cols = ['#c4562b', '#e09a3a', '#d8b44a', '#6f8f4b', '#a33b2a', '#e8b25a']
    for side, x0, x1 in (('l', -10, 320), ('r', 280, 610)):
        for k in range(150):
            x = s.r.uniform(x0, x1)
            edge = 330 + (x - x0) * .35 if side == 'l' else 330 + (x1 - x) * .35
            y = s.r.uniform(edge, 490)
            if s.r.random() < .18:
                s.conifer(x, y, s.r.uniform(26, 40), '#2e5b4a', '#88a890')
            else:
                s.tree_round(x, y, s.r.uniform(9, 15), [s.r.choice(cols), s.r.choice(cols)])
    s.rect(0, 486, W, 100, '#3fb3b0')
    s.rect(0, 520, W, 66, '#2e9aa0', .8)
    s.rect(0, 556, W, 30, '#237f88', .8)
    for k in range(9):
        x = s.r.uniform(40, 560)
        y = s.r.uniform(500, 576)
        a = s.r.uniform(-.4, .4)
        s.line(x, y, x + 90 * math.cos(a), y + 90 * math.sin(a) * .3, '#d2c09a', 3, .45)
    s.reflections(490, 580, '#c2ece4', 30, .55)
    s.rect(0, 584, W, 216, '#1f4f57')
    s.reflections(600, 680, '#3fb3b0', 16, .25)
    s.grain(5)
    return s.svg(5)


# ================= 北京 · 红墙金瓦 =================
def bj4():
    s = S(6)
    s.sky([(170, '#f6e4c6'), (150, '#f2d3ab'), (480, '#edc493')])
    s.sun(450, 196, 54, '#c8432f', '#e2784a')
    s.birds(200, 130, 5, '#5a3a2a', 50)
    s.path('M-10,420 C60,380 120,330 180,320 C240,330 300,380 360,420 Z', '#7d6a58')
    s.poly([(150, 322), (210, 322), (196, 306), (164, 306)], '#5c4a3c')
    s.poly([(158, 306), (202, 306), (180, 290)], '#6b5a4a')
    # 大殿：两重檐
    gold, gold2, tile = '#d9a441', '#c58f2f', '#b17f2a'
    s.path('M60,372 Q110,360 150,352 L450,352 Q490,360 540,372 L520,384 L80,384 Z', gold)
    for k in range(30):
        x = 90 + k * 14
        s.line(x, 356, x - 6, 382, tile, 1.4, .6)
    s.path('M120,340 Q170,320 210,312 L390,312 Q430,320 480,340 L462,352 L138,352 Z', gold)
    for k in range(20):
        x = 150 + k * 15
        s.line(x, 316, x - 5, 350, tile, 1.4, .6)
    s.path('M200,312 L400,312 L380,300 L220,300 Z', gold2)
    s.rect(212, 296, 176, 5, '#a8782a')
    s.poly([(204, 302), (196, 290), (214, 298)], gold2)
    s.poly([(396, 302), (404, 290), (386, 298)], gold2)
    s.rect(110, 384, 380, 70, '#9b2c22')
    for k in range(12):
        s.rect(122 + k * 31, 390, 8, 64, '#7d231b')
    for k in range(6):
        x = 150 + k * 52
        s.rect(x, 404, 26, 36, '#c8a04a', .9)
        for j in range(4):
            s.line(x + 2, 410 + j * 8, x + 24, 410 + j * 8, '#9b2c22', 1, .7)
    s.rect(80, 454, 440, 16, '#efe8dc')
    for k in range(40):
        s.rect(86 + k * 11, 446, 3, 10, '#efe8dc')
    s.rect(80, 450, 440, 3, '#efe8dc')
    s.rect(0, 470, W, 64, '#8f2a20')
    s.rect(0, 466, W, 8, '#d9a441')
    s.rect(0, 532, W, 268, '#2f2a2b')
    s.reflections(540, 640, '#d9a441', 24, .28)
    s.reflections(545, 600, '#c8432f', 14, .35)
    # 枫枝
    s.path('M-10,40 C60,60 110,90 160,150 S230,230 260,250', None, 1, '#4a2f22', 6)
    s.path('M90,80 C120,70 150,74 180,96', None, 1, '#4a2f22', 4)
    for k in range(30):
        t = s.r.uniform(0, 1)
        x = -10 + 270 * t + s.r.uniform(-30, 30)
        y = 40 + 210 * t * t + s.r.uniform(-24, 24)
        r0 = s.r.uniform(7, 12)
        star = []
        for j in range(10):
            ang = -math.pi / 2 + j * math.pi / 5
            rr = r0 if j % 2 == 0 else r0 * .45
            star.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
        s.poly(star, s.r.choice(['#c8432f', '#e07a3a', '#b5372a', '#d9562f']))
    s.grain(6)
    return s.svg(6)


# ================= 稻城亚丁 =================
def sc5():
    s = S(9)
    s.sky([(180, '#e3ecf1'), (150, '#dbe6ee'), (470, '#d2dfe9')])
    s.cloud(60, 120, 150, '#f6f8fa', '#d6e0e8')
    s.peak(120, 250, 440, 130, '#b9c6d5', '#7f95ae', '#f7f5f0', .4)
    s.peak(480, 240, 440, 130, '#b9c6d5', '#7f95ae', '#f7f5f0', .4)
    s.peak(300, 150, 440, 170, '#aebdcf', '#71879f', '#f8f6f1', .42, 9)
    for k in range(14):
        x = 270 + k * 6
        s.line(x, 190 + k * 3, x - 40 + k * 2, 290 + k * 4, '#d4dde6', 1.4, .5)
    s.range_(420, 26, '#3f5a4a', 91, 480)
    for k in range(70):
        x, y = s.r.uniform(0, W), s.r.uniform(420, 476)
        s.conifer(x, y, s.r.uniform(14, 22), '#2f4a3c') if s.r.random() < .6 else s.circ(x, y - 6, s.r.uniform(4, 7), '#d8a031')
    s.rect(0, 474, W, 74, '#d0782f')
    s.path('M-10,490 C100,500 160,480 260,492 S420,520 610,500', None, .9, '#e8f0f2', 4)
    for k in range(30):
        x = s.r.uniform(0, W)
        y = s.r.uniform(478, 544)
        s.path(f'M{f(x)},{f(y)} q10,-8 20,0 q-10,6 -20,0', '#b5482a', .9)
    s.path('M440,532 l0,-10 l6,-8 l0,-8 l4,-6 l4,6 l0,8 l6,8 l0,10 Z', '#f4f1ea')
    s.rect(447, 510, 6, 2, '#d9a441')
    for x0 in (120, 160, 330):
        s.path(f'M{x0},540 q4,-10 16,-10 q10,0 14,6 l5,-3 l0,7 l-3,0 l0,7 l-5,0 l0,-5 l-15,0 l0,5 l-5,0 z', '#2a201b')
    s.rect(0, 546, W, 254, '#3a2f2a')
    s.reflections(556, 640, '#d0782f', 18, .2)
    s.grain(9)
    return s.svg(9)


# ================= 北疆 · 禾木 =================
def xj10():
    s = S(10)
    s.sky([(170, '#f4ecdc'), (150, '#f0e5d0'), (480, '#ebdfc6')])
    s.sun(470, 150, 44, '#f0b86a', '#f3cf96')
    s.peak(120, 230, 400, 140, '#93a6bd', '#6c84a0', '#f7f5f0', .38)
    s.peak(320, 190, 400, 170, '#8ea2ba', '#647d9a', '#f7f5f0', .4)
    s.peak(520, 230, 400, 140, '#93a6bd', '#6c84a0', '#f7f5f0', .38)
    s.range_(380, 22, '#4e6a5a', 101, 440)
    s.rect(0, 360, W, 26, '#f6f1e7', .75)
    s.rect(0, 430, W, 100, '#c9a44a')
    for k in range(5):
        y0 = 448 + k * 16
        s.line(-10, y0, 610, y0 + s.r.uniform(-6, 6), '#a88a36', 1.2, .5)
    # 白桦
    for k in range(18):
        x = s.r.choice([s.r.uniform(10, 200), s.r.uniform(400, 590)])
        h = s.r.uniform(80, 130)
        y = s.r.uniform(470, 520)
        s.rect(x - 2.5, y - h, 5, h, '#f4f1ea')
        for j in range(5):
            s.rect(x - 2.5, y - h + 10 + j * (h / 6), 5, 2.5, '#2b2620')
        for j in range(8):
            s.circ(x + s.r.uniform(-20, 20), y - h + s.r.uniform(-18, 20), s.r.uniform(8, 15), s.r.choice(['#e6b33a', '#f2c14e', '#d89a2a']))
    # 木屋
    for x0, y0, w0 in ((230, 506, 80), (316, 512, 64), (380, 500, 56)):
        h0 = w0 * .55
        s.rect(x0, y0 - h0, w0, h0, '#7a4e32')
        for j in range(5):
            s.line(x0, y0 - h0 + 5 + j * h0 / 5, x0 + w0, y0 - h0 + 5 + j * h0 / 5, '#5e3a24', 1.6, .8)
        s.poly([(x0 - 8, y0 - h0 + 2), (x0 + w0 / 2, y0 - h0 - w0 * .42), (x0 + w0 + 8, y0 - h0 + 2)], '#4a2f22')
        s.rect(x0 + w0 * .35, y0 - h0 * .6, w0 * .22, h0 * .3, '#f1c232')
        s.rect(x0 + w0 * .7, y0 - h0 - w0 * .3, 7, 16, '#4a2f22')
        s.path(f'M{x0 + w0 * .7 + 3},{y0 - h0 - w0 * .3} c-10,-10 10,-18 0,-30 c-8,-10 8,-16 2,-26', None, .6, '#f6f1e7', 3)
    s.line(0, 520, 600, 524, '#5e3a24', 2, .7)
    for k in range(30):
        s.line(k * 20, 512, k * 20 + 2, 528, '#5e3a24', 2, .7)
    s.rect(0, 528, W, 272, '#33342a')
    s.reflections(540, 620, '#e6b33a', 16, .2)
    s.grain(10)
    return s.svg(10)


# ================= 黄山 · 云海 =================
def hs2():
    s = S(12)
    s.sky([(170, '#f5eada'), (150, '#f0d9bb'), (480, '#eacaa3')])
    s.sun(450, 200, 52, '#f0b86a', '#f4cf98')
    for x0, top, w0, c in ((60, 260, 70, '#c5c9cc'), (150, 230, 60, '#bfc4c7'), (520, 250, 70, '#c5c9cc')):
        s.path(f'M{x0 - w0 / 2},470 Q{x0 - w0 * .4},{top + 40} {x0 - w0 * .1},{top} Q{x0 + w0 * .2},{top - 10} {x0 + w0 * .4},{top + 30} Q{x0 + w0 * .5},{top + 120} {x0 + w0 / 2},470 Z', c)
    for x0, top, w0 in ((300, 150, 110), (400, 200, 90), (220, 210, 80)):
        s.path(f'M{x0 - w0 / 2},480 Q{x0 - w0 * .45},{top + 60} {x0 - w0 * .15},{top} Q{x0},{top - 14} {x0 + w0 * .2},{top + 6} Q{x0 + w0 * .5},{top + 90} {x0 + w0 / 2},480 Z', '#8e959b')
        s.path(f'M{x0 + w0 * .05},{top + 4} Q{x0 + w0 * .2},{top + 6} {x0 + w0 * .3},{top + 40} Q{x0 + w0 * .5},{top + 120} {x0 + w0 / 2},480 L{x0 + w0 * .1},480 Z', '#6c737a')
        for k in range(6):
            cx = x0 - w0 * .3 + k * w0 * .12
            s.line(cx, top + 30 + s.r.uniform(0, 30), cx + s.r.uniform(-6, 6), top + 160 + s.r.uniform(0, 60), '#5b6268', 1.6, .5)
    for k, (y0, c) in enumerate(((410, '#fbf8f2'), (440, '#f4efe6'), (470, '#ffffff'))):
        x = -40
        while x < W + 40:
            r0 = s.r.uniform(24, 46)
            s.circ(x, y0, r0, c)
            x += r0 * 1.2
        s.rect(-10, y0, W + 20, 60, c)
    # 松
    s.path('M40,560 C50,520 70,500 110,470 C140,450 150,420 170,400', None, 1, '#3b2a22', 9)
    s.path('M110,470 C150,470 190,460 230,440', None, 1, '#3b2a22', 6)
    for x0, y0, w0 in ((150, 396, 90), (196, 424, 110), (240, 438, 80), (108, 452, 70)):
        s.path(f'M{x0 - w0 / 2},{y0} Q{x0},{y0 - 26} {x0 + w0 / 2},{y0} Q{x0},{y0 + 8} {x0 - w0 / 2},{y0} Z', '#2f4a3a')
        s.path(f'M{x0 - w0 * .35},{y0 - 6} Q{x0},{y0 - 24} {x0 + w0 * .3},{y0 - 8}', None, .7, '#4d6f57', 3)
    s.path('M-10,800 L-10,540 C40,520 90,524 130,548 C170,566 200,600 260,610 L610,640 L610,800 Z', '#2f3a3f')
    s.rect(0, 640, W, 160, '#2f3a3f')
    for k in range(14):
        s.line(s.r.uniform(0, 260), s.r.uniform(570, 640), s.r.uniform(0, 260), s.r.uniform(600, 680), '#3d4a50', 2, .6)
    s.grain(12)
    return s.svg(12)


if __name__ == '__main__':
    for name, fn in (('xz7', xz7), ('nam', nam), ('njg8', njg8), ('nm4', nm4), ('jz4', jz4), ('bj4', bj4), ('sc5', sc5), ('xj10', xj10), ('hs2', hs2)):
        svg = fn()
        open(f'{OUT}/{name}.svg', 'w', encoding='utf-8').write(svg)
        print(f'  {name}.svg  {len(svg) // 1024} KB')
