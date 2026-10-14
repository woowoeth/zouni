import math
from gen import S, W, H, OUT, smooth, f

FLAG = ['#2f6ea8', '#f4f1ea', '#c8432f', '#2e7d4f', '#f1c232']


def houses(s, y, c, lit, n_min=26, n_max=54):
    x = -10
    while x < W:
        w0, h0 = s.r.uniform(n_min, n_max), s.r.uniform(10, 28)
        s.rect(x, y - h0, w0, h0 + 2, c)
        s.rect(x - 2, y - h0 - 3, w0 + 4, 3, c)
        for k in range(s.r.randint(1, 3)):
            if s.r.random() < .75:
                s.rect(x + 5 + k * 12, y - h0 + 7, 5, 6, lit, .9)
        x += w0 + s.r.uniform(2, 8)


# ================= 西藏 · 布达拉宫 =================
def xz7():
    s = S(7)
    s.sky([(180, '#f7e1b6'), (140, '#f4d39f'), (120, '#f0c58a'), (360, '#ebb978')])
    s.sun(440, 168, 64, '#e8763a', '#f2a65e')
    s.birds(330, 120, 7, '#5a3a2a', 50)
    s.cloud(40, 150, 170, '#fbeed6', '#e9cfa2')
    s.cloud(470, 300, 120, '#fbeed6', '#e9cfa2')
    s.peak(110, 250, 430, 150, '#a7b2c4', '#7f8ca3', '#f8f4ec')
    s.peak(300, 215, 430, 170, '#9eaabd', '#76849c', '#f8f4ec')
    s.peak(520, 240, 430, 150, '#a7b2c4', '#7f8ca3', '#f8f4ec')
    s.rect(0, 372, W, 30, '#f3d6a8', .45)
    s.range_(400, 26, '#6f7d93', 71, 520)
    s.rect(0, 410, W, 20, '#f0c58a', .25)
    hill = [(-10, 530), (60, 492), (130, 452), (200, 420), (270, 404), (330, 402), (400, 414), (470, 446), (540, 486), (610, 530)]
    s.path(smooth(hill) + ' L610,560 L-10,560 Z', '#8a5a3c')
    s.path(smooth([(300, 402), (400, 414), (470, 446), (540, 486), (610, 530)]) + ' L610,560 L300,560 Z', '#76492f', .55)
    for k in range(46):
        x = s.r.uniform(20, 580)
        y = 470 + abs(x - 300) * .18 + s.r.uniform(-25, 30)
        s.path(f'M{f(x)},{f(y)} q{f(s.r.uniform(8, 18))},{f(-s.r.uniform(2, 6))} {f(s.r.uniform(20, 34))},0', None, .7, '#6f452c', 2)
    for k in range(24):
        x = s.r.uniform(60, 540)
        y = 480 + abs(x - 300) * .15 + s.r.uniform(-20, 25)
        s.path(f'M{f(x)},{f(y)} q8,-4 16,0', None, .6, '#a5734f', 2)
    white, wshade, win, red = '#f6efe2', '#e2d6c2', '#3b2a22', '#9b2c22'
    s.poly([(150, 470), (150, 428), (450, 428), (450, 470)], white)
    s.poly([(170, 428), (170, 378), (430, 378), (430, 428)], white)
    s.poly([(190, 378), (190, 336), (246, 336), (246, 378)], white)
    s.poly([(354, 378), (354, 336), (410, 336), (410, 378)], white)
    s.poly([(410, 336), (410, 470), (450, 470), (450, 428), (430, 428), (430, 378)], wshade, .55)
    s.rect(150, 426, 300, 3, '#d9ccb6')
    s.rect(170, 376, 260, 3, '#d9ccb6')
    s.path('M162,468 L230,452 L176,440 L240,430', None, .9, '#d8ccb6', 3)
    s.path('M440,468 L372,452 L424,440 L360,430', None, .9, '#d8ccb6', 3)
    for (y0, x0, x1) in [(440, 252, 350), (454, 252, 350), (390, 180, 420), (404, 180, 420), (348, 198, 240), (360, 198, 240), (348, 360, 404), (360, 360, 404)]:
        x = x0
        while x < x1:
            s.poly([(x, y0), (x + 6, y0), (x + 5, y0 + 8), (x + 1, y0 + 8)], win)
            s.rect(x - 1, y0 - 2, 8, 1.6, '#c8432f', .8)
            x += 13
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
    s.rect(290, 360, 20, 18, '#2b1a14', .85)
    for x0, w0, y0 in ((252, 22, 280), (284, 32, 274), (326, 22, 280)):
        s.poly([(x0 - 4, y0 + 12), (x0 + w0 + 4, y0 + 12), (x0 + w0 - 2, y0 + 4), (x0 + 2, y0 + 4)], '#d9a441')
        s.poly([(x0 + 2, y0 + 4), (x0 + w0 - 2, y0 + 4), (x0 + w0 / 2, y0 - 6)], '#e6b85a')
        s.rect(x0 + w0 / 2 - 1.5, y0 - 16, 3, 10, '#d9a441')
        s.circ(x0 + w0 / 2, y0 - 17, 3, '#e6b85a')
    for x0 in (196, 404):
        s.rect(x0 - 2, 326, 4, 10, '#d9a441')
        s.circ(x0, 324, 3, '#e6b85a')
    for k in range(16):
        x = 140 + k * 21 + s.r.uniform(-4, 4)
        s.circ(x, 488 + abs(x - 300) * .1, s.r.uniform(5, 9), '#55623a')
    s.flags(0, 92, 190, 150, 30, 15, FLAG, 12)
    s.flags(600, 60, 470, 104, 22, 11, FLAG[::-1], 11)
    s.ground(526, '#36425b', '#1d2431')
    houses(s, 530, '#2a3446', '#f2c48a')
    s.rect(0, 528, W, 2, '#45536b')
    s.rect(0, 602, W, 6, '#3a4660')
    for k in range(9):
        x = s.r.uniform(0, W)
        s.rect(x, 603, s.r.uniform(18, 46), 2, '#f2c48a', .7, 1)
    for k in range(7):
        x = 30 + k * 90 + s.r.uniform(-10, 10)
        s.rect(x, 570, 2, 32, '#3d4a63')
        s.circ(x + 1, 568, 4, '#f6d49a', .9)
        s.circ(x + 1, 568, 10, '#f6d49a', .15)
    s.tufts(640, 790, '#2c3547', 60, (8, 18))
    s.grain(7)
    return s.svg(7)


# ================= 纳木错 · 日落 =================
def nam():
    s = S(11)
    s.sky([(150, '#f2c79a'), (110, '#efb084'), (110, '#e99a74'), (430, '#d98a6a')])
    s.sun(170, 402, 46, '#f8e2ae', '#f5c48b')
    s.birds(420, 180, 5, '#6a4a4a', 40)
    s.cloud(300, 110, 200, '#f6d3ad', '#e5ae86')
    s.cloud(40, 210, 130, '#f6d3ad', '#e5ae86')
    m = s.mark()
    for cx, top, hw in ((330, 300, 120), (450, 270, 150), (560, 310, 110), (230, 340, 90)):
        s.peak(cx, top, 455, hw, '#a08fae', '#776a92', '#f8e6dc', .36)
    s.range_(440, 12, '#6a5f84', 113, 470)
    peaks_end = s.mark()
    s.rect(0, 462, W, 160, '#2f6c86')
    s.mirror(m, 462, 462, 616, .3, peaks_end)
    s.reflections(470, 610, '#7fb4c6', 46, .45)
    for k in range(16):
        y = 468 + k * 9
        w0 = 70 - k * 3.2
        s.rect(170 - w0 / 2 + s.r.uniform(-6, 6), y, w0, 3, '#f6c98b', .75 - k * .035, 1.5)
    s.path('M40,622 L52,470 Q60,440 82,438 Q104,442 108,476 L120,622 Z', '#4b3b3d')
    s.path('M58,470 Q66,448 82,446 L86,622 L64,622 Z', '#5f4b4c', .9)
    for k in range(10):
        y = 470 + k * 15
        s.line(56 + k, y, 70 + k, y + 6, '#3a2d2f', 1.4, .6)
    s.path('M128,622 L136,520 Q142,498 158,498 Q174,502 176,530 L184,622 Z', '#4b3b3d')
    s.flags(84, 446, 160, 506, 26, 9, FLAG, 10)
    s.flags(160, 506, 250, 560, 18, 9, FLAG[::-1], 9)
    s.ground(616, '#2c3846', '#1a2129')
    for k in range(90):
        s.circ(s.r.uniform(0, W), s.r.uniform(626, 790), s.r.uniform(1.5, 4), '#3a4656', .8)
    s.tufts(630, 700, '#3a4a40', 40, (6, 14))
    for x0 in (380, 430, 470):
        s.path(f'M{x0},612 q4,-12 18,-12 q12,0 16,8 l6,-4 l0,8 l-4,0 l0,8 l-6,0 l0,-6 l-18,0 l0,6 l-6,0 z', '#1f262f')
    s.grain(11)
    return s.svg(11)


# ================= 南疆 · 帕米尔 =================
def njg8():
    s = S(8)
    s.sky([(190, '#f5e6c6'), (150, '#f1dbb2'), (460, '#ecd09f')])
    s.sun(150, 150, 54, '#d9653b', '#eba068')
    s.birds(420, 110, 5, '#5a3a2a', 40)
    s.cloud(380, 170, 150, '#f8efdc', '#e6d3ae')
    dome = [(30, 450), (90, 360), (160, 270), (230, 214), (300, 192), (370, 206), (440, 252), (510, 330), (580, 430)]
    s.path(smooth(dome) + ' L580,470 L30,470 Z', '#f6f3ec')
    s.path(smooth([(300, 192), (370, 206), (440, 252), (510, 330), (580, 430)]) + ' L580,470 L330,470 Q320,330 300,192 Z', '#cad6e1')
    for k in range(11):
        x = 120 + k * 36
        s.path(f'M{x},{220 + abs(x - 300) * .45} q{s.r.uniform(-14, 14)},70 {s.r.uniform(-20, 20)},150', None, .55, '#dde6ee', 2.4)
    for k in range(18):
        x = s.r.uniform(80, 540)
        y = 400 + abs(x - 300) * .1 + s.r.uniform(-10, 20)
        s.path(f'M{f(x)},{f(y)} l{f(s.r.uniform(10, 30))},{f(s.r.uniform(-4, 4))}', None, .6, '#9a8f86', 3)
    s.range_(420, 30, '#a3876b', 81, 480)
    s.range_(445, 18, '#8d7259', 82, 500)
    s.rect(0, 470, W, 80, '#d8a031')
    for k in range(5):
        y0 = 478 + k * 14
        s.path(f'M-10,{y0} C120,{y0 + 18} 220,{y0 - 14} 320,{y0 + 6} S520,{y0 + 16} 620,{y0}', None, .85, '#eef3f4', 3 - k * .4)
    for k in range(90):
        s.circ(s.r.uniform(0, W), s.r.uniform(474, 548), s.r.uniform(1.5, 3.5), s.r.choice(['#b7801f', '#e8b84a']), .75)
    base = 452
    s.path(f'M360,{base + 20} L380,{base - 10} L560,{base - 10} L590,{base + 20} Z', '#9a7a5c')
    x = 386
    while x < 556:
        s.rect(x, base - 30, 14, 22, '#8c6b4f')
        s.rect(x + 2, base - 36, 4, 6, '#8c6b4f')
        s.rect(x + 8, base - 36, 4, 6, '#8c6b4f')
        s.rect(x + 9, base - 30, 5, 22, '#77593f', .7)
        x += 22
    s.rect(420, base - 52, 20, 44, '#7d5f45')
    s.rect(500, base - 46, 18, 38, '#7d5f45')
    for x0 in (424, 432, 504, 511):
        s.rect(x0, base - 58, 4, 7, '#7d5f45')
    s.rect(426, base - 40, 6, 9, '#3b2a22')
    for x0 in (90, 140):
        s.path(f'M{x0},{base + 14} q0,-18 18,-20 q18,2 18,20 Z', '#f4f1ea')
        s.path(f'M{x0},{base + 14} q0,-18 18,-20 l0,20 Z', '#e1dccf')
        s.rect(x0 + 14, base + 4, 8, 10, '#c8432f')
    s.ground(548, '#5a412d', '#2f2117')
    s.path('M-10,640 C120,610 220,660 330,620 S520,600 610,630', None, .55, '#c9a46a', 10)
    s.path('M-10,640 C120,610 220,660 330,620 S520,600 610,630', None, .8, '#7a5a3a', 2, )
    for k, x0 in enumerate((390, 430, 470, 510)):
        y0 = 612 - k * 4
        s.path(f'M{x0},{y0} q3,-14 12,-14 q4,-10 10,0 q8,-4 10,6 l4,-6 l2,4 l-3,4 l0,12 l-4,0 l0,-9 l-14,0 l0,9 l-4,0 z', '#2a1d14')
    s.tufts(560, 790, '#3e2c1e', 70, (8, 16))
    s.grain(8)
    return s.svg(8)


# ================= 额济纳 · 胡杨 =================
def nm4():
    s = S(4)
    s.sky([(170, '#f8e7c2'), (150, '#f5d9a6'), (480, '#efc98a')])
    s.sun(450, 170, 58, '#e36b2c', '#ef9a55')
    s.birds(250, 120, 4, '#6a4a2a', 40)
    s.path('M-10,420 C120,380 220,410 320,392 S520,370 610,396 L610,500 L-10,500 Z', '#ead0a0')
    s.path('M-10,450 C140,420 260,452 380,430 S540,420 610,440 L610,500 L-10,500 Z', '#dfb978')
    for k in range(8):
        y0 = 440 + k * 7
        s.path(f'M-10,{y0} C150,{y0 - 10} 300,{y0 + 6} 610,{y0 - 6}', None, .3, '#c99f5d', 1.4)

    def poplar(x, y, sc, flip=1):
        s.path(f'M{x - 7 * sc},{y} C{x - 6 * sc},{y - 40 * sc} {x - 18 * sc * flip},{y - 70 * sc} {x - 4 * sc},{y - 110 * sc} L{x + 6 * sc},{y - 108 * sc} C{x + 10 * sc},{y - 70 * sc} {x + 4 * sc},{y - 40 * sc} {x + 8 * sc},{y} Z', '#6b4a2f')
        for k in range(5):
            s.line(x - 4 * sc + k * 2.5 * sc, y - 10 * sc, x - 6 * sc + k * 2 * sc, y - 90 * sc, '#553821', 1.2, .6)
        for bx, by, ex, ey in ((0, -80, -46, -128), (0, -95, 40, -140), (-6, -60, -60, -96), (4, -70, 52, -100), (2, -100, -20, -150)):
            s.path(f'M{x + bx * sc},{y + by * sc} Q{x + (bx + ex) / 2 * sc},{y + (by + ey) / 2 * sc - 8 * sc} {x + ex * sc},{y + ey * sc}', None, 1, '#6b4a2f', 5 * sc)
        for k in range(34):
            cx = x + s.r.uniform(-78, 78) * sc
            cy = y - 130 * sc + s.r.uniform(-42, 46) * sc
            s.circ(cx, cy, s.r.uniform(12, 23) * sc, s.r.choice(['#f2c14e', '#e5a21f', '#c9781c', '#f7d77a', '#e5a21f', '#d88a1f']))
        for k in range(14):
            s.circ(x + s.r.uniform(-60, 60) * sc, y - 152 * sc + s.r.uniform(-30, 12) * sc, s.r.uniform(5, 10) * sc, '#fbe3a0', .9)
        for k in range(6):
            s.circ(x + s.r.uniform(-60, 60) * sc, y - 110 * sc + s.r.uniform(0, 30) * sc, s.r.uniform(8, 13) * sc, '#a9621a', .5)
    m = s.mark()
    poplar(140, 500, 1.15)
    poplar(330, 494, 1.35, -1)
    poplar(500, 500, 1.0)
    trees_end = s.mark()
    s.rect(0, 498, W, 64, '#3e6f8a')
    s.mirror(m, 498, 498, 562, .4, trees_end)
    s.ripples(502, 558, '#a9c9d6', 26, .5)
    s.ground(560, '#5a4631', '#2b2016')
    for k in range(10):
        y0 = 584 + k * 22
        s.path(f'M-10,{y0} C150,{y0 - 8} 300,{y0 + 8} 610,{y0 - 4}', None, .3, '#76603f', 2)
    for k in range(6):
        x0, y0 = s.r.uniform(20, 580), s.r.uniform(600, 760)
        s.path(f'M{f(x0)},{f(y0)} l{f(s.r.uniform(30, 60))},{f(s.r.uniform(-10, 4))} m-20,4 l12,-14', None, .8, '#3a2a1c', 3)
    s.grain(4)
    return s.svg(4)


# ================= 九寨沟 · 彩林 =================
def jz4():
    s = S(5)
    s.sky([(150, '#f2eadb'), (150, '#ece3d0'), (500, '#e6dcc6')])
    s.birds(420, 90, 4, '#5a4a3a', 40)
    s.range_(210, 40, '#b4c6bc', 51, 420)
    s.rect(0, 238, W, 26, '#f4efe4', .75)
    s.range_(290, 50, '#86a294', 52, 470)
    s.rect(0, 318, W, 18, '#f4efe4', .5)
    cols = ['#c4562b', '#e09a3a', '#d8b44a', '#6f8f4b', '#a33b2a', '#e8b25a', '#b8492a']
    m = s.mark()
    for k in range(230):
        x = s.r.uniform(-10, 610)
        edge = 340 + abs(x - 300) * -.1 + 20
        y = s.r.uniform(edge - 20, 492)
        rr = 9 + (y - 330) / 160 * 12
        if s.r.random() < .16:
            s.conifer(x, y, rr * 2.6, '#2e5b4a', '#88a890')
        else:
            s.tree_round(x, y, rr, [s.r.choice(cols), s.r.choice(cols), s.r.choice(cols)])
    forest_end = s.mark()
    s.rect(0, 486, W, 100, '#3fb3b0')
    s.mirror(m, 486, 486, 586, .32, forest_end)
    s.rect(0, 520, W, 66, '#2e9aa0', .55)
    s.rect(0, 556, W, 30, '#237f88', .6)
    for k in range(10):
        x = s.r.uniform(40, 560)
        y = s.r.uniform(500, 576)
        a = s.r.uniform(-.4, .4)
        s.line(x, y, x + 90 * math.cos(a), y + 90 * math.sin(a) * .3, '#d2c09a', 3, .45)
        s.line(x + 30, y, x + 40, y - 12, '#d2c09a', 2, .35)
    s.reflections(490, 580, '#c2ece4', 34, .55)
    s.ground(584, '#235a63', '#14363c')
    s.ripples(596, 700, '#3fb3b0', 30, .35)
    s.tufts(720, 795, '#1d4a50', 40, (8, 16))
    s.grain(5)
    return s.svg(5)


# ================= 北京 · 红墙金瓦 =================
def bj4():
    s = S(6)
    s.sky([(170, '#f6e4c6'), (150, '#f2d3ab'), (480, '#edc493')])
    s.sun(450, 196, 54, '#c8432f', '#e2784a')
    s.birds(200, 130, 6, '#5a3a2a', 50)
    s.path('M-10,420 C60,380 120,330 180,320 C240,330 300,380 360,420 Z', '#7d6a58')
    s.poly([(150, 322), (210, 322), (196, 306), (164, 306)], '#5c4a3c')
    s.poly([(158, 306), (202, 306), (180, 290)], '#6b5a4a')
    for k in range(14):
        s.circ(s.r.uniform(20, 340), s.r.uniform(360, 420), s.r.uniform(6, 12), '#6a5a48', .8)
    gold, gold2, tile = '#d9a441', '#c58f2f', '#b17f2a'
    m = s.mark()
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
    for x0 in (66, 534):
        s.poly([(x0, 372), (x0 + (8 if x0 < 300 else -8), 360), (x0 + (12 if x0 < 300 else -12), 374)], gold2)
    s.rect(110, 384, 380, 70, '#9b2c22')
    s.rect(110, 384, 380, 8, '#3d6b74', .8)
    for k in range(12):
        s.rect(122 + k * 31, 392, 8, 62, '#7d231b')
    for k in range(6):
        x = 150 + k * 52
        s.rect(x, 404, 26, 36, '#c8a04a', .9)
        for j in range(4):
            s.line(x + 2, 410 + j * 8, x + 24, 410 + j * 8, '#9b2c22', 1, .7)
    s.rect(80, 454, 440, 16, '#efe8dc')
    for k in range(40):
        s.rect(86 + k * 11, 446, 3, 10, '#efe8dc')
    s.rect(80, 450, 440, 3, '#efe8dc')
    hall_end = s.mark()
    s.rect(0, 470, W, 64, '#8f2a20')
    s.rect(0, 466, W, 8, '#d9a441')
    for k in range(60):
        s.rect(k * 10, 467, 6, 3, '#b8862f', .8)
    s.ground(532, '#3a3130', '#1f1a1b')
    s.mirror(m, 532, 532, 680, .22, hall_end)
    s.ripples(540, 690, '#d9a441', 30, .3)
    s.path('M-10,40 C60,60 110,90 160,150 S230,230 260,250', None, 1, '#4a2f22', 6)
    s.path('M90,80 C120,70 150,74 180,96', None, 1, '#4a2f22', 4)
    s.path('M180,190 C210,180 240,186 262,200', None, 1, '#4a2f22', 3)
    for k in range(40):
        t = s.r.uniform(0, 1)
        x = -10 + 270 * t + s.r.uniform(-30, 30)
        y = 40 + 210 * t * t + s.r.uniform(-24, 24)
        r0 = s.r.uniform(7, 12)
        star = []
        for j in range(10):
            ang = -math.pi / 2 + j * math.pi / 5 + s.r.uniform(-.1, .1)
            rr = r0 if j % 2 == 0 else r0 * .45
            star.append((x + rr * math.cos(ang), y + rr * math.sin(ang)))
        s.poly(star, s.r.choice(['#c8432f', '#e07a3a', '#b5372a', '#d9562f']))
    for k in range(8):
        x, y = s.r.uniform(80, 560), s.r.uniform(560, 760)
        s.circ(x, y, 4, '#c8432f', .6)
    s.grain(6)
    return s.svg(6)


# ================= 稻城亚丁 =================
def sc5():
    s = S(9)
    s.sky([(180, '#e3ecf1'), (150, '#dbe6ee'), (470, '#d2dfe9')])
    s.cloud(60, 120, 150, '#f6f8fa', '#d6e0e8')
    s.cloud(430, 90, 120, '#f6f8fa', '#d6e0e8')
    s.peak(120, 250, 440, 130, '#b9c6d5', '#7f95ae', '#f7f5f0', .4)
    s.peak(480, 240, 440, 130, '#b9c6d5', '#7f95ae', '#f7f5f0', .4)
    s.peak(300, 150, 440, 170, '#aebdcf', '#71879f', '#f8f6f1', .42, 9)
    for k in range(16):
        x = 266 + k * 6
        s.line(x, 190 + k * 3, x - 40 + k * 2, 290 + k * 4, '#d4dde6', 1.4, .5)
    s.rect(0, 392, W, 22, '#eef3f6', .5)
    s.range_(420, 26, '#3f5a4a', 91, 480)
    for k in range(90):
        x, y = s.r.uniform(0, W), s.r.uniform(420, 476)
        if s.r.random() < .6:
            s.conifer(x, y, s.r.uniform(14, 24), '#2f4a3c')
        else:
            s.circ(x, y - 6, s.r.uniform(4, 8), s.r.choice(['#d8a031', '#e8b84a']))
    s.rect(0, 474, W, 74, '#d0782f')
    s.path('M-10,490 C100,500 160,480 260,492 S420,520 610,500', None, .9, '#e8f0f2', 4)
    for k in range(40):
        x = s.r.uniform(0, W)
        y = s.r.uniform(478, 544)
        s.path(f'M{f(x)},{f(y)} q10,-8 20,0 q-10,6 -20,0', s.r.choice(['#b5482a', '#c25a2a']), .9)
    s.path('M440,532 l0,-10 l6,-8 l0,-8 l4,-6 l4,6 l0,8 l6,8 l0,10 Z', '#f4f1ea')
    s.rect(447, 510, 6, 2, '#d9a441')
    s.flags(452, 498, 560, 530, 10, 8, FLAG, 7)
    for x0 in (120, 160, 330, 360):
        s.path(f'M{x0},540 q4,-10 16,-10 q10,0 14,6 l5,-3 l0,7 l-3,0 l0,7 l-5,0 l0,-5 l-15,0 l0,5 l-5,0 z', '#2a201b')
    s.ground(546, '#4a3b33', '#241c18')
    s.path('M-10,600 C120,580 260,620 400,596 S560,580 610,600', None, .5, '#6b8a9a', 6)
    s.tufts(560, 790, '#3a2e27', 80, (8, 18))
    s.grain(9)
    return s.svg(9)


# ================= 北疆 · 禾木 =================
def xj10():
    s = S(10)
    s.sky([(170, '#f4ecdc'), (150, '#f0e5d0'), (480, '#ebdfc6')])
    s.sun(470, 150, 44, '#f0b86a', '#f3cf96')
    s.birds(200, 110, 5, '#5a4a3a', 40)
    s.peak(120, 230, 400, 140, '#93a6bd', '#6c84a0', '#f7f5f0', .38)
    s.peak(320, 190, 400, 170, '#8ea2ba', '#647d9a', '#f7f5f0', .4)
    s.peak(520, 230, 400, 140, '#93a6bd', '#6c84a0', '#f7f5f0', .38)
    s.range_(380, 22, '#4e6a5a', 101, 440)
    for k in range(60):
        s.conifer(s.r.uniform(0, W), s.r.uniform(386, 432), s.r.uniform(14, 22), '#3e5a4a')
    s.rect(0, 360, W, 26, '#f6f1e7', .75)
    s.rect(0, 430, W, 100, '#c9a44a')
    for k in range(5):
        y0 = 448 + k * 16
        s.line(-10, y0, 610, y0 + s.r.uniform(-6, 6), '#a88a36', 1.2, .5)
    m = s.mark()
    for k in range(22):
        x = s.r.choice([s.r.uniform(10, 210), s.r.uniform(400, 590)])
        h = s.r.uniform(80, 140)
        y = s.r.uniform(470, 520)
        s.rect(x - 2.5, y - h, 5, h, '#f4f1ea')
        for j in range(6):
            s.rect(x - 2.5, y - h + 10 + j * (h / 7), 5, 2.5, '#2b2620')
        for j in range(10):
            s.circ(x + s.r.uniform(-22, 22), y - h + s.r.uniform(-20, 24), s.r.uniform(7, 15), s.r.choice(['#e6b33a', '#f2c14e', '#d89a2a', '#f5d36a']))
    for x0, y0, w0 in ((230, 506, 80), (316, 512, 64), (380, 500, 56)):
        h0 = w0 * .55
        s.rect(x0, y0 - h0, w0, h0, '#7a4e32')
        for j in range(5):
            s.line(x0, y0 - h0 + 5 + j * h0 / 5, x0 + w0, y0 - h0 + 5 + j * h0 / 5, '#5e3a24', 1.6, .8)
        s.poly([(x0 - 8, y0 - h0 + 2), (x0 + w0 / 2, y0 - h0 - w0 * .42), (x0 + w0 + 8, y0 - h0 + 2)], '#4a2f22')
        s.poly([(x0 + w0 / 2, y0 - h0 - w0 * .42), (x0 + w0 + 8, y0 - h0 + 2), (x0 + w0 / 2 + 4, y0 - h0 + 2)], '#3a2418', .6)
        s.rect(x0 + w0 * .35, y0 - h0 * .6, w0 * .22, h0 * .3, '#f1c232')
        s.rect(x0 + w0 * .7, y0 - h0 - w0 * .3, 7, 16, '#4a2f22')
        s.path(f'M{x0 + w0 * .7 + 3},{y0 - h0 - w0 * .3} c-10,-10 10,-18 0,-30 c-8,-10 8,-16 2,-26', None, .6, '#f6f1e7', 3)
    vil_end = s.mark()
    s.line(0, 520, 600, 524, '#5e3a24', 2, .7)
    for k in range(30):
        s.line(k * 20, 512, k * 20 + 2, 528, '#5e3a24', 2, .7)
    s.rect(0, 528, W, 44, '#4f6f80')
    s.mirror(m, 528, 528, 572, .35, vil_end)
    s.ripples(532, 568, '#a9c3cf', 16, .5)
    s.ground(570, '#3a3b2f', '#1f201a')
    s.tufts(580, 790, '#2c2d23', 80, (8, 18))
    s.grain(10)
    return s.svg(10)


# ================= 黄山 · 云海 =================
def hs2():
    s = S(12)
    s.sky([(170, '#f5eada'), (150, '#f0d9bb'), (480, '#eacaa3')])
    s.sun(450, 200, 52, '#f0b86a', '#f4cf98')
    s.birds(330, 140, 5, '#5a4a3a', 40)
    for x0, top, w0, c in ((60, 260, 70, '#c5c9cc'), (150, 230, 60, '#bfc4c7'), (520, 250, 70, '#c5c9cc'), (590, 290, 60, '#cdd0d2')):
        s.path(f'M{x0 - w0 / 2},470 Q{x0 - w0 * .4},{top + 40} {x0 - w0 * .1},{top} Q{x0 + w0 * .2},{top - 10} {x0 + w0 * .4},{top + 30} Q{x0 + w0 * .5},{top + 120} {x0 + w0 / 2},470 Z', c)
    for x0, top, w0 in ((300, 150, 110), (400, 200, 90), (220, 210, 80)):
        s.path(f'M{x0 - w0 / 2},480 Q{x0 - w0 * .45},{top + 60} {x0 - w0 * .15},{top} Q{x0},{top - 14} {x0 + w0 * .2},{top + 6} Q{x0 + w0 * .5},{top + 90} {x0 + w0 / 2},480 Z', '#8e959b')
        s.path(f'M{x0 + w0 * .05},{top + 4} Q{x0 + w0 * .2},{top + 6} {x0 + w0 * .3},{top + 40} Q{x0 + w0 * .5},{top + 120} {x0 + w0 / 2},480 L{x0 + w0 * .1},480 Z', '#6c737a')
        for k in range(7):
            cx = x0 - w0 * .3 + k * w0 * .11
            s.line(cx, top + 30 + s.r.uniform(0, 30), cx + s.r.uniform(-6, 6), top + 160 + s.r.uniform(0, 60), '#5b6268', 1.6, .5)
        for k in range(4):
            px = x0 + s.r.uniform(-w0 * .3, w0 * .3)
            s.conifer(px, top + s.r.uniform(20, 60), 14, '#2f4a3a')
    for k, (y0, c) in enumerate(((410, '#fbf8f2'), (440, '#f4efe6'), (470, '#ffffff'))):
        x = -40
        while x < W + 40:
            r0 = s.r.uniform(24, 46)
            s.circ(x, y0, r0, c)
            x += r0 * 1.2
        s.rect(-10, y0, W + 20, 60, c)
        s.rect(-10, y0 + 18, W + 20, 3, '#e6ddd0', .5)
    s.path('M-10,800 L-10,540 C40,520 90,524 130,548 C170,566 200,600 260,610 L610,640 L610,800 Z', '#2f3a3f')
    s.ground(640, '#2f3a3f', '#1b2225')
    for k in range(18):
        s.line(s.r.uniform(0, 260), s.r.uniform(570, 640), s.r.uniform(0, 260), s.r.uniform(600, 680), '#3d4a50', 2, .6)
    s.path('M40,560 C50,520 70,500 110,470 C140,450 150,420 170,400', None, 1, '#3b2a22', 9)
    s.path('M110,470 C150,470 190,460 230,440', None, 1, '#3b2a22', 6)
    s.path('M70,500 C50,490 30,480 10,476', None, 1, '#3b2a22', 4)
    for x0, y0, w0 in ((150, 396, 90), (196, 424, 110), (240, 438, 80), (108, 452, 70), (30, 470, 60)):
        s.path(f'M{x0 - w0 / 2},{y0} Q{x0},{y0 - 26} {x0 + w0 / 2},{y0} Q{x0},{y0 + 8} {x0 - w0 / 2},{y0} Z', '#2f4a3a')
        s.path(f'M{x0 - w0 * .35},{y0 - 6} Q{x0},{y0 - 24} {x0 + w0 * .3},{y0 - 8}', None, .7, '#4d6f57', 3)
        for j in range(5):
            s.line(x0 - w0 * .4 + j * w0 * .2, y0 - 2, x0 - w0 * .42 + j * w0 * .2, y0 + 4, '#223629', 1.2, .7)
    s.tufts(650, 790, '#26302f', 50, (8, 16))
    s.grain(12)
    return s.svg(12)


for name, fn in (('xz7', xz7), ('nam', nam), ('njg8', njg8), ('nm4', nm4), ('jz4', jz4), ('bj4', bj4), ('sc5', sc5), ('xj10', xj10), ('hs2', hs2)):
    svg = fn()
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8').write(svg)
    print(f'  {name}.svg  {len(svg) // 1024} KB')
