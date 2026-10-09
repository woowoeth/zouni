import math
from gen import S, W, H, OUT, smooth, f, pts


# ---------- 新部件 ----------
def vgrad(s, y0, y1, stops):
    gid = f'v{len(s.defs)}'
    st = ''.join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
    s.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">{st}</linearGradient>')
    s.add(f'<rect x="0" y="{f(y0)}" width="{W}" height="{f(y1 - y0)}" fill="url(#{gid})"/>')


def glow(s, cx, cy, r, c, op=.6):
    gid = f'r{len(s.defs)}'
    s.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{c}" stop-opacity="{op}"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    s.add(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}" fill="url(#{gid})"/>')


def stars(s, n, y1, c='#fff8e8'):
    for _ in range(n):
        s.circ(s.r.uniform(0, W), s.r.uniform(8, y1), s.r.uniform(.6, 1.8), c, s.r.uniform(.35, .9))


def crescent(s, cx, cy, r, c):
    s.path(f'M{f(cx)},{f(cy - r)} A{f(r)},{f(r)} 0 1,0 {f(cx)},{f(cy + r)} A{f(r * .72)},{f(r)} 0 1,1 {f(cx)},{f(cy - r)} Z', c)


def rays(s, x, y, n, c, op=.14, spread=(.3, 1.4), length=900):
    for k in range(n):
        a = spread[0] + (spread[1] - spread[0]) * k / max(1, n - 1) + s.r.uniform(-.04, .04)
        w = s.r.uniform(.02, .05)
        p = [(x, y), (x + length * math.cos(a - w), y + length * math.sin(a - w)), (x + length * math.cos(a + w), y + length * math.sin(a + w))]
        s.poly(p, c, op * s.r.uniform(.6, 1))


# ================= 西藏 · 黄昏的布达拉宫（主体：宫殿） =================
def xz7():
    s = S(21)
    vgrad(s, 0, 640, [(0, '#27304c'), (.3, '#4b4566'), (.55, '#9a6f7e'), (.74, '#e2a072'), (1, '#f0c48c')])
    stars(s, 60, 230)
    crescent(s, 470, 110, 22, '#f6ead0')
    # 远山：压成低对比剪影
    s.range_(380, 40, '#8e7c93', 301, 560)
    s.range_(420, 26, '#76667f', 302, 560)
    glow(s, 300, 380, 260, '#f6c98a', .55)
    # 红山：简化剪影
    hill = [(-10, 600), (80, 560), (160, 520), (240, 496), (300, 490), (360, 496), (440, 520), (520, 560), (610, 600)]
    s.path(smooth(hill) + ' L610,640 L-10,640 Z', '#3a2b33')
    # 宫殿：放大、细化
    def P(x, y):
        return (300 + (x - 300) * 1.3, 520 + (y - 470) * 1.3)
    white, shade, win, lit, red = '#f8ead2', '#d8bf9f', '#3b2a22', '#f7c76c', '#a3392a'
    def box(x0, y0, x1, y1, c, op=1):
        a, b = P(x0, y0), P(x1, y1)
        s.poly([(a[0], b[1]), (a[0], a[1]), (b[0], a[1]), (b[0], b[1])], c, op)
    box(150, 428, 450, 470, white)
    box(170, 378, 430, 428, white)
    box(190, 336, 246, 378, white)
    box(354, 336, 410, 378, white)
    box(410, 336, 450, 470, shade, .6)
    box(150, 426, 450, 429, '#d6c2a4')
    box(170, 376, 430, 379, '#d6c2a4')
    # 之字台阶
    a = [P(162, 468), P(230, 452), P(176, 440), P(240, 430)]
    s.path('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in a), None, .9, '#e2cfb2', 3)
    a = [P(440, 468), P(372, 452), P(424, 440), P(360, 430)]
    s.path('M' + ' L'.join(f'{f(x)},{f(y)}' for x, y in a), None, .9, '#e2cfb2', 3)
    for (y0, x0, x1) in [(440, 252, 350), (454, 252, 350), (390, 180, 420), (404, 180, 420), (348, 198, 240), (360, 198, 240), (348, 360, 404), (360, 360, 404)]:
        x = x0
        while x < x1:
            q = [P(x, y0), P(x + 6, y0), P(x + 5, y0 + 8), P(x + 1, y0 + 8)]
            s.poly(q, lit if s.r.random() < .22 else win)
            x += 13
    box(246, 292, 354, 378, red)
    box(246, 292, 354, 304, '#4a2219')
    for k in range(18):
        a, b = P(248 + k * 6, 292), P(251 + k * 6, 304)
        s.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], '#2b130e', .8)
    box(330, 304, 354, 378, '#7c2219', .55)
    for y0 in (314, 330, 346, 362):
        x = 254
        while x < 346:
            a, b = P(x - 1.5, y0 - 1.5), P(x + 7.5, y0 + 9.5)
            s.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], '#f3ead9')
            a, b = P(x, y0), P(x + 6, y0 + 8)
            s.rect(a[0], a[1], b[0] - a[0], b[1] - a[1], lit if s.r.random() < .3 else '#2b1a14')
            x += 15
    for x0, w0, y0 in ((252, 22, 280), (284, 32, 274), (326, 22, 280)):
        s.poly([P(x0 - 4, y0 + 12), P(x0 + w0 + 4, y0 + 12), P(x0 + w0 - 2, y0 + 4), P(x0 + 2, y0 + 4)], '#f0c35a')
        s.poly([P(x0 + 2, y0 + 4), P(x0 + w0 - 2, y0 + 4), P(x0 + w0 / 2, y0 - 6)], '#f6d47e')
        a = P(x0 + w0 / 2, y0 - 16)
        s.rect(a[0] - 2, a[1], 4, 13, '#f0c35a')
        s.circ(a[0], a[1] - 2, 4, '#f6d47e')
    glow(s, 300, 330, 120, '#ffd99a', .25)
    # 城市：压暗，只留零星灯火
    vgrad(s, 600, 800, [(0, '#1f2433'), (1, '#12151d')])
    x = -10
    while x < W:
        w0, h0 = s.r.uniform(30, 60), s.r.uniform(10, 24)
        s.rect(x, 600 - h0, w0, h0 + 2, '#1f2433')
        if s.r.random() < .5:
            s.rect(x + 6, 600 - h0 + 6, 5, 5, '#f2c48a', .8)
        x += w0 + s.r.uniform(2, 8)
    s.grain(21)
    return s.svg(21)


# ================= 纳木错 · 日落（主体：石柱 + 日光路） =================
def nam():
    s = S(22)
    vgrad(s, 0, 470, [(0, '#e9b38c'), (.6, '#efa077'), (1, '#f3c493')])
    s.sun(300, 430, 40, '#fbe7b6', '#f6c88f')
    # 远山压淡
    s.range_(445, 18, '#c79a9a', 401, 480)
    s.range_(458, 8, '#b48a95', 402, 480)
    vgrad(s, 468, 640, [(0, '#3f6f86'), (1, '#24495e')])
    for k in range(26):
        y = 472 + k * 6.4
        w0 = 34 + k * 5.5
        s.rect(300 - w0 / 2 + s.r.uniform(-8, 8), y, w0 * s.r.uniform(.5, 1), 2.6, '#fbd99e', .85 - k * .025, 1.3)
    # 石柱：放大做主体
    s.path('M70,700 L96,470 Q110,410 150,404 Q194,410 200,470 L220,700 Z', '#3b2f33')
    s.path('M104,470 Q118,422 150,416 L158,700 L116,700 Z', '#4f3f42', .9)
    for k in range(14):
        y = 440 + k * 18
        s.line(112 + k * .6, y, 132 + k * .6, y + 8, '#2d2427', 1.6, .55)
    s.path('M236,700 L250,560 Q258,530 282,530 Q306,536 310,566 L322,700 Z', '#3b2f33')
    s.path('M256,566 Q264,540 282,540 L286,700 L262,700 Z', '#4f3f42', .9)
    s.flags(150, 410, 282, 532, 40, 12, ['#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f', '#f1c232'], 11)
    vgrad(s, 640, 800, [(0, '#22303c'), (1, '#141b22')])
    for k in range(40):
        s.circ(s.r.uniform(0, W), s.r.uniform(650, 790), s.r.uniform(1.2, 3), '#33414f', .7)
    s.grain(22)
    return s.svg(22)


# ================= 南疆 · 慕士塔格清晨（主体：雪山） =================
def njg8():
    s = S(23)
    vgrad(s, 0, 520, [(0, '#bcd3e3'), (.7, '#e3ecef'), (1, '#f2efe6')])
    for k in range(3):
        y = 90 + k * 34
        s.path(f'M{60 + k * 90},{y} q120,-10 260,0', None, .5, '#f6f8f8', 3)
    dome = [(-20, 500), (40, 420), (110, 320), (190, 230), (270, 176), (330, 166), (400, 186), (470, 240), (540, 330), (620, 450)]
    s.path(smooth(dome) + ' L620,540 L-20,540 Z', '#fbfaf6')
    s.path(smooth([(330, 166), (400, 186), (470, 240), (540, 330), (620, 450)]) + ' L620,540 L350,540 Q340,340 330,166 Z', '#c3d2e0')
    for k in range(14):
        x = 120 + k * 30
        top = 200 + abs(x - 320) * .5
        s.path(f'M{x},{top} q{s.r.uniform(-12, 12)},80 {s.r.uniform(-24, 24)},190', None, .55, '#d9e3ec', 2.2)
    for k in range(16):
        x = s.r.uniform(160, 500)
        y = 300 + abs(x - 320) * .35 + s.r.uniform(0, 40)
        s.path(f'M{f(x)},{f(y)} l{f(s.r.uniform(6, 16))},{f(s.r.uniform(6, 14))}', None, .5, '#a9bccd', 1.6)
    for k in range(10):
        x = s.r.uniform(40, 580)
        y = 470 + s.r.uniform(-10, 30)
        s.path(f'M{f(x)},{f(y)} l{f(s.r.uniform(20, 40))},{f(s.r.uniform(-3, 3))}', None, .7, '#a29384', 4)
    s.range_(500, 14, '#b39b80', 401, 560)
    vgrad(s, 530, 600, [(0, '#e0b453'), (1, '#c99437')])
    s.path('M-10,548 C140,570 230,540 330,556 S520,578 610,552', None, .8, '#eef4f5', 3)
    # 远处石头城：小而淡
    x = 470
    while x < 560:
        s.rect(x, 520, 8, 12, '#b9a58a', .7)
        x += 12
    # 骆驼队：小
    for k in range(4):
        x0, y0 = 130 + k * 24, 560
        s.path(f'M{x0},{y0} q2,-9 8,-9 q3,-6 7,0 q5,-2 6,4 l3,-4 l1,3 l-2,3 l0,8 l-3,0 l0,-6 l-9,0 l0,6 l-3,0 z', '#3a281b')
    vgrad(s, 598, 800, [(0, '#3e2c1e'), (1, '#1f160f')])
    s.tufts(610, 790, '#2c1f15', 40, (8, 16))
    s.grain(23)
    return s.svg(23)


# ================= 额济纳 · 一棵胡杨（主体：大树） =================
def nm4():
    s = S(24)
    vgrad(s, 0, 560, [(0, '#f2d8a8'), (.55, '#efbf7c'), (1, '#e59a58')])
    glow(s, 360, 330, 300, '#fff1c8', .55)
    # 远处胡杨：小剪影
    for k in range(9):
        x = 20 + k * 70 + s.r.uniform(-10, 10)
        s.rect(x - 1.5, 492, 3, 14, '#b97b3c', .6)
        s.circ(x, 488, s.r.uniform(8, 12), '#d0904a', .55)
    s.path('M-10,500 C150,488 300,506 610,494 L610,520 L-10,520 Z', '#d79a5b', .6)
    m = s.mark()
    x, y, sc = 300, 520, 2.0
    s.path(f'M{x - 14 * sc},{y} C{x - 12 * sc},{y - 40 * sc} {x - 34 * sc},{y - 70 * sc} {x - 8 * sc},{y - 112 * sc} L{x + 10 * sc},{y - 110 * sc} C{x + 18 * sc},{y - 70 * sc} {x + 6 * sc},{y - 40 * sc} {x + 14 * sc},{y} Z', '#5a3b24')
    for k in range(9):
        s.path(f'M{x - 10 * sc + k * 2.4 * sc},{y - 6} q{s.r.uniform(-6, 6)},{-40 * sc} {s.r.uniform(-8, 8)},{-96 * sc}', None, .5, '#3f2817', 1.6)
    for bx, by, ex, ey, w in ((0, -88, -60, -140, 8), (2, -100, 52, -150, 7), (-8, -66, -84, -100, 6), (6, -76, 70, -108, 6), (0, -108, -14, -168, 5), (-30, -120, -70, -150, 4)):
        s.path(f'M{x + bx * sc},{y + by * sc} Q{x + (bx + ex) / 2 * sc},{y + (by + ey) / 2 * sc - 10 * sc} {x + ex * sc},{y + ey * sc}', None, 1, '#5a3b24', w * sc / 2)
    for k in range(60):
        cx = x + s.r.uniform(-110, 110) * sc * .9
        cy = y - 140 * sc + s.r.uniform(-48, 40) * sc
        s.circ(cx, cy, s.r.uniform(10, 22) * sc * .7, s.r.choice(['#f2c14e', '#e5a21f', '#d88a1f', '#c9781c', '#f2c14e']))
    for k in range(26):
        s.circ(x + s.r.uniform(-80, 40) * sc, y - 168 * sc + s.r.uniform(-14, 14) * sc, s.r.uniform(5, 9) * sc * .7, '#fde8a6', .95)
    for k in range(10):
        s.circ(x + s.r.uniform(-90, 90) * sc, y - 110 * sc + s.r.uniform(0, 24) * sc, s.r.uniform(8, 12) * sc * .7, '#9a5414', .45)
    tree_end = s.mark()
    vgrad(s, 520, 640, [(0, '#5b6f7c'), (1, '#33424d')])
    s.mirror(m, 520, 520, 640, .38, tree_end)
    s.ripples(526, 636, '#c6d3d9', 30, .45)
    vgrad(s, 638, 800, [(0, '#3d2e21'), (1, '#1f170f')])
    s.grain(24)
    return s.svg(24)


# ================= 九寨沟 · 五花海（主体：湖） =================
def jz4():
    s = S(25)
    vgrad(s, 0, 260, [(0, '#e7ece6'), (1, '#f1efe6')])
    s.range_(170, 30, '#c3d0c8', 501, 300)
    s.rect(0, 200, W, 40, '#f4f2ea', .7)
    s.range_(240, 34, '#9fb4a6', 502, 330)
    # 彩林：色带，不再铺满点点
    bands = [(270, '#5f7f5a'), (296, '#b9582e'), (318, '#d99a3c'), (338, '#7d8f4a'), (356, '#c7672f')]
    for k, (y0, c) in enumerate(bands):
        p = s.ridge(-20, W + 20, y0, 14, 5, 520 + k)
        s.poly(p + [(W + 20, 390), (-20, 390)], c)
    for k in range(70):
        x = s.r.uniform(0, W)
        y = s.r.uniform(368, 388)
        s.circ(x, y, s.r.uniform(5, 9), s.r.choice(['#d24e2a', '#e8a33c', '#f2c14e', '#6f8f4b']), .9)
    # 湖：主体
    vgrad(s, 388, 650, [(0, '#5ccdc4'), (.35, '#35aab0'), (.7, '#227d8a'), (1, '#175a66')])
    for k in range(9):
        y0 = 400 + k * 26
        s.path(f'M-10,{y0} C150,{y0 + 14} 300,{y0 - 10} 450,{y0 + 8} S600,{y0 + 4} 610,{y0}', None, .25, '#bff0ea', 2)
    for k in range(18):
        y = 392 + k * 2.4
        s.rect(0, y, W, 2.2, s.r.choice(['#d24e2a', '#e8a33c', '#7d8f4a', '#f2c14e']), .2)
    # 水下倒木：细节
    for (x0, y0, ang, L) in ((80, 520, -.18, 260), (210, 470, .12, 220), (330, 560, -.05, 240), (150, 600, .2, 180)):
        x1, y1 = x0 + L * math.cos(ang), y0 + L * math.sin(ang) * .4
        s.line(x0, y0, x1, y1, '#e6d6b0', 5, .55)
        s.line(x0, y0 + 2, x1, y1 + 2, '#f6ecd0', 1.5, .45)
        for j in range(4):
            bx = x0 + (x1 - x0) * (j + 1) / 5
            by = y0 + (y1 - y0) * (j + 1) / 5
            s.line(bx, by, bx + s.r.uniform(-14, 14), by - s.r.uniform(10, 18), '#e6d6b0', 2, .45)
    vgrad(s, 650, 800, [(0, '#164f5a'), (1, '#0e3239')])
    s.grain(25)
    return s.svg(25)


# ================= 北京 · 屋檐特写（主体：金顶一角） =================
def bj4():
    s = S(26)
    vgrad(s, 0, 600, [(0, '#8fb8cf'), (.6, '#c9dde6'), (1, '#e8eef0')])
    # 大屋檐对角构图
    gold, gold2, gold3 = '#e2ae45', '#c9922f', '#a8752a'
    s.poly([(-20, 120), (430, 300), (600, 250), (620, 290), (440, 360), (-20, 190)], gold)
    for k in range(26):
        t = k / 26
        x0, y0 = -20 + 450 * t, 120 + 180 * t
        s.line(x0, y0, x0 - 18, y0 + 70, gold3, 3, .5)
    s.poly([(-20, 190), (440, 360), (620, 290), (620, 310), (446, 380), (-20, 214)], gold2)
    for k in range(40):
        t = k / 40
        x0, y0 = -20 + 460 * t, 190 + 170 * t
        s.circ(x0, y0 + 10, 4, '#f3cf73')
    # 脊兽
    for k in range(6):
        x0 = 470 + k * 22
        y0 = 292 - k * 7
        s.path(f'M{x0},{y0} q4,-14 10,-14 q6,2 6,8 l4,2 l-4,4 l0,6 Z', '#7a5a2a')
    s.path('M600,248 q14,-24 22,-26 l2,30 Z', gold2)
    # 斗拱彩画
    s.poly([(-20, 214), (446, 380), (446, 420), (-20, 260)], '#2f6d74')
    for k in range(18):
        t = k / 18
        x0, y0 = -10 + 440 * t, 224 + 160 * t
        s.rect(x0, y0, 16, 18, '#3f8a83')
        s.circ(x0 + 8, y0 + 9, 3, '#e2ae45')
    s.poly([(-20, 260), (446, 420), (446, 432), (-20, 274)], '#e2ae45', .9)
    # 红柱与墙
    s.poly([(-20, 274), (446, 432), (446, 620), (-20, 620)], '#9b2c22')
    for k in range(5):
        x0 = 30 + k * 90
        s.poly([(x0, 290 + x0 * .34), (x0 + 22, 298 + x0 * .34), (x0 + 22, 620), (x0, 620)], '#7d231b')
    # 喜鹊：一只
    s.path('M300,128 q18,-12 36,-4 l26,-10 l-14,14 q-6,14 -26,14 q-16,0 -22,-14 Z', '#1f2a33')
    s.circ(338, 122, 4, '#1f2a33')
    s.path('M318,132 q8,4 16,0', None, 1, '#f4f6f6', 2)
    # 枫叶：少量
    for k in range(9):
        x, y, r0 = s.r.uniform(470, 590), s.r.uniform(40, 200), s.r.uniform(8, 13)
        star = []
        for j in range(10):
            ang = -math.pi / 2 + j * math.pi / 5
            rr = r0 if j % 2 == 0 else r0 * .45
            star.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
        s.poly(star, s.r.choice(['#c8432f', '#d9562f', '#b5372a']))
    s.path('M620,40 C560,60 520,110 500,190', None, 1, '#4a2f22', 4)
    vgrad(s, 600, 800, [(0, '#5a1c16'), (1, '#2a0f0c')])
    for k in range(30):
        s.rect(s.r.uniform(0, W), s.r.uniform(610, 790), s.r.uniform(20, 60), 2, '#7a2a20', .4, 1)
    s.grain(26)
    return s.svg(26)


# ================= 稻城 · 日照金山（主体：仙乃日） =================
def sc5():
    s = S(27)
    vgrad(s, 0, 560, [(0, '#24324f'), (.5, '#5a6e92'), (1, '#b7c6d8')])
    stars(s, 50, 200)
    # 侧峰：暗剪影
    s.poly([(-20, 560), (60, 330), (110, 390), (180, 560)], '#4a5a7a')
    s.poly([(420, 560), (520, 320), (620, 470), (620, 560)], '#4a5a7a')
    # 仙乃日：主体
    cx, top, base, hw = 300, 120, 560, 230
    s.poly([(cx - hw, base), (cx, top), (cx + hw, base)], '#6f86a8')
    s.poly([(cx, top), (cx + hw, base), (cx + 40, base)], '#526a8f')
    for k in range(18):
        x = cx - 150 + k * 18
        s.line(x, base - 30, cx + (x - cx) * .25, top + 80 + abs(x - cx) * .3, '#9fb2cc', 1.6, .35)
    # 金顶：上 22% 被晨光照亮
    gy = top + (base - top) * .24
    gl = hw * .24
    s.poly([(cx - gl, gy), (cx, top), (cx + gl, gy)], '#f5c27c')
    s.poly([(cx, top), (cx + gl, gy), (cx + gl * .2, gy)], '#e79a7f', .75)
    zig = []
    for i in range(9):
        x = cx - gl + 2 * gl * i / 8
        zig.append((x, gy + (6 if i % 2 else -4)))
    s.poly([(cx - gl, gy)] + zig + [(cx + gl, gy)], '#f5c27c')
    glow(s, cx, top + 40, 120, '#ffd59a', .35)
    # 草甸与白塔：小、暗
    vgrad(s, 560, 800, [(0, '#2a3346'), (1, '#151a26')])
    s.path('M420,560 l0,-10 l6,-8 l0,-8 l4,-6 l4,6 l0,8 l6,8 l0,10 Z', '#c9cdd6', .8)
    s.flags(434, 538, 560, 560, 8, 8, ['#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f', '#f1c232'], 6)
    s.tufts(570, 790, '#202838', 60, (8, 16))
    s.grain(27)
    return s.svg(27)


# ================= 北疆 · 禾木晨雾（主体：木屋 + 前景白桦） =================
def xj10():
    s = S(28)
    vgrad(s, 0, 600, [(0, '#e9ebe4'), (1, '#dfe2d8')])
    s.range_(250, 40, '#c5ccc8', 601, 420)
    s.range_(300, 30, '#b1bbb6', 602, 440)
    s.rect(0, 330, W, 60, '#f1f1ea', .8)
    for k in range(40):
        s.conifer(s.r.uniform(160, 600), s.r.uniform(380, 420), s.r.uniform(14, 22), '#9aa79c')
    s.rect(0, 400, W, 30, '#eeeee6', .7)
    s.rect(0, 420, W, 120, '#c2b080')
    # 木屋：主体
    for x0, y0, w0 in ((250, 500, 96), (356, 506, 76), (432, 496, 70), (190, 512, 60)):
        h0 = w0 * .55
        s.rect(x0, y0 - h0, w0, h0, '#7a4e32')
        for j in range(6):
            s.line(x0, y0 - h0 + 4 + j * h0 / 6, x0 + w0, y0 - h0 + 4 + j * h0 / 6, '#5e3a24', 1.6, .85)
            s.circ(x0 + 2, y0 - h0 + 4 + j * h0 / 6, 2, '#9a6a44')
        s.poly([(x0 - 10, y0 - h0 + 2), (x0 + w0 / 2, y0 - h0 - w0 * .42), (x0 + w0 + 10, y0 - h0 + 2)], '#4a2f22')
        s.poly([(x0 + w0 / 2, y0 - h0 - w0 * .42), (x0 + w0 + 10, y0 - h0 + 2), (x0 + w0 / 2 + 4, y0 - h0 + 2)], '#3a2418', .6)
        s.rect(x0 + w0 * .32, y0 - h0 * .62, w0 * .22, h0 * .32, '#f4c44a')
        s.rect(x0 + w0 * .33, y0 - h0 * .62, 1.5, h0 * .32, '#5e3a24')
        s.rect(x0 + w0 * .7, y0 - h0 - w0 * .3, 7, 16, '#4a2f22')
        s.path(f'M{x0 + w0 * .7 + 3},{y0 - h0 - w0 * .3} c-12,-12 12,-22 0,-36 c-10,-12 10,-20 2,-32', None, .65, '#f6f6f0', 4)
    s.rect(0, 470, W, 24, '#f1f1ea', .35)
    # 前景白桦：画框
    for x0, w0 in ((24, 18), (70, 12), (560, 14)):
        s.rect(x0, -10, w0, 620, '#f2efe6')
        for j in range(18):
            y = s.r.uniform(0, 600)
            s.rect(x0 + s.r.uniform(0, w0 * .4), y, w0 * s.r.uniform(.4, .9), s.r.uniform(2, 5), '#2b2620')
        s.rect(x0 + w0 * .7, -10, w0 * .3, 620, '#d9d4c6', .6)
    for k in range(40):
        s.circ(s.r.uniform(-10, 180), s.r.uniform(-10, 160), s.r.uniform(10, 22), s.r.choice(['#e6b33a', '#f2c14e', '#d89a2a']))
    for k in range(14):
        s.circ(s.r.uniform(520, 620), s.r.uniform(-10, 110), s.r.uniform(10, 20), s.r.choice(['#e6b33a', '#f2c14e']))
    vgrad(s, 540, 800, [(0, '#3a3a2c'), (1, '#1d1e17')])
    for k in range(20):
        s.line(110 + k * 22, 548, 112 + k * 22, 570, '#2a2a20', 3, .8)
    s.line(100, 556, 560, 560, '#2a2a20', 3, .8)
    s.tufts(580, 790, '#2a2b21', 50, (8, 16))
    s.grain(28)
    return s.svg(28)


# ================= 黄山 · 一棵松（主体：松） =================
def hs2():
    s = S(29)
    vgrad(s, 0, 640, [(0, '#f6eee0'), (.6, '#efdcc2'), (1, '#e8cfae')])
    rays(s, 600, 0, 7, '#fff6e6', .16, (1.9, 2.6))
    # 远峰：淡
    for x0, top, w0 in ((420, 250, 80), (500, 280, 70), (560, 230, 60), (360, 300, 60)):
        s.path(f'M{x0 - w0 / 2},470 Q{x0 - w0 * .4},{top + 40} {x0 - w0 * .1},{top} Q{x0 + w0 * .2},{top - 10} {x0 + w0 * .4},{top + 30} Q{x0 + w0 * .5},{top + 120} {x0 + w0 / 2},470 Z', '#d3cdc4')
    for y0, c in ((420, '#fbf7ef'), (450, '#f6f0e4'), (480, '#ffffff')):
        x = -40
        while x < W + 40:
            r0 = s.r.uniform(26, 50)
            s.circ(x, y0, r0, c)
            x += r0 * 1.15
        s.rect(-10, y0, W + 20, 680 - y0, c)
    for k in range(5):
        s.rect(-10, 530 + k * 22, W + 20, 2.5, '#e9e1d4', .6)
    # 悬崖与松：主体
    s.path('M-10,800 L-10,470 C30,452 70,456 110,480 C150,504 180,560 230,600 L260,800 Z', '#3a3f40')
    s.path('M-10,520 C30,500 60,506 90,526 L110,800 L-10,800 Z', '#2c3132')
    for k in range(16):
        s.line(s.r.uniform(0, 200), s.r.uniform(500, 600), s.r.uniform(0, 220), s.r.uniform(560, 700), '#4a5052', 2, .6)
    s.path('M90,500 C110,450 160,420 210,380 C260,340 320,320 400,300', None, 1, '#3b2a22', 12)
    s.path('M200,390 C240,400 280,404 330,396', None, 1, '#3b2a22', 7)
    s.path('M150,430 C170,440 200,452 240,452', None, 1, '#3b2a22', 6)
    for k in range(14):
        s.line(110 + k * 18, 470 - k * 12, 118 + k * 18, 472 - k * 12, '#2a1d17', 2, .6)
    for x0, y0, w0 in ((410, 296, 170), (330, 316, 150), (250, 360, 140), (330, 392, 120), (240, 448, 110), (180, 420, 90), (470, 284, 110)):
        s.path(f'M{x0 - w0 / 2},{y0} Q{x0},{y0 - 34} {x0 + w0 / 2},{y0} Q{x0},{y0 + 12} {x0 - w0 / 2},{y0} Z', '#2f4a3a')
        s.path(f'M{x0 - w0 * .4},{y0 - 8} Q{x0},{y0 - 30} {x0 + w0 * .35},{y0 - 10}', None, .75, '#4f7059', 4)
        for j in range(8):
            xx = x0 - w0 * .42 + j * w0 * .12
            s.line(xx, y0 - 2, xx - 3, y0 + 6, '#203327', 1.4, .75)
    vgrad(s, 640, 800, [(0, '#2a2f30'), (1, '#161a1b')])
    s.grain(29)
    return s.svg(29)


for name, fn in (('xz7', xz7), ('nam', nam), ('njg8', njg8), ('nm4', nm4), ('jz4', jz4), ('bj4', bj4), ('sc5', sc5), ('xj10', xj10), ('hs2', hs2)):
    svg = fn()
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8').write(svg)
    print(f'  {name}.svg  {len(svg) // 1024} KB')
