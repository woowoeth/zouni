# 跟片走的片子封面：每部片子一张插图，和行程海报同一套画法（gen.py 的 S、gen3.py 的渐变和光晕）。
# 用法：项目根目录  python3 tools/posters/gen_shows.py   → 写到 site_src/posters/show-<slug>.svg
import os, sys, math
_mk = os.makedirs; os.makedirs = lambda *a, **k: None      # gen.py 导入时会建一个线上输出目录，本机没有，跳过
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from gen import S, W, H, f
os.makedirs = _mk


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
OUT = os.path.join('site_src', 'posters')


def ell(s, cx, cy, rx, ry, c, op=1):
    s.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{c}" opacity="{op}"/>')


def steam(s, x, y, n, c='#fff8ec', op=.5, h=120):
    for k in range(n):
        xx = x + (k - (n - 1) / 2) * 34
        s.path(f'M{f(xx)},{f(y)} C{f(xx - 18)},{f(y - h * .35)} {f(xx + 18)},{f(y - h * .6)} {f(xx)},{f(y - h)}', None, op, c, 7)


def shejian():
    """舌尖上的中国：暖色黄昏里叠起来的蒸笼，热气往上冒。"""
    s = S(101); vgrad(s, 0, 800, [(0, '#f3c98d'), (.55, '#d98a4e'), (1, '#6b3b27')])
    glow(s, 300, 330, 300, '#ffe8bf', .6)
    for k in range(4):
        y = 470 - k * 62; w = 250 - k * 6
        ell(s, 300, y + 40, w / 2, 20, '#7a4a2b'); s.rect(300 - w / 2, y, w, 40, '#c99356')
        for j in range(9): s.line(300 - w / 2 + 14 + j * (w - 28) / 8, y + 3, 300 - w / 2 + 14 + j * (w - 28) / 8, y + 37, '#a8743c', 2, .8)
        ell(s, 300, y, w / 2, 20, '#e0b274'); ell(s, 300, y, w / 2 - 8, 14, '#f4d7a0')
    ell(s, 300, 410 - 3 * 62, 130, 18, '#6b3b27'); s.circ(300, 410 - 3 * 62 - 14, 16, '#6b3b27')
    steam(s, 300, 190, 4, op=.55, h=150)
    ell(s, 300, 560, 220, 22, '#3b2217', .55)
    vgrad(s, 600, 800, [(0, '#8a5232'), (1, '#2a1812')])
    s.grain(101); return s.svg(101)


def fengwei():
    """风味人间：青绿底上一只大盘子，餐刀餐叉，半个柠檬，几粒辣椒。"""
    s = S(102); vgrad(s, 0, 800, [(0, '#2f6f6a'), (1, '#173a3a')])
    glow(s, 300, 360, 320, '#8fd0c1', .35)
    ell(s, 300, 400, 210, 210, '#f2ede0'); ell(s, 300, 400, 170, 170, '#e4ddc9'); ell(s, 300, 400, 120, 120, '#f6f1e4')
    for k in range(7):
        a = k * .9; x = 300 + math.cos(a) * 54; y = 400 + math.sin(a) * 40
        s.circ(x, y, 22, '#d9573b', .95); s.circ(x - 6, y - 6, 7, '#f29a7c', .8)
    s.circ(350, 440, 40, '#f1d34f'); s.circ(350, 440, 32, '#f8e88c')
    for k in range(6): s.line(350, 440, 350 + math.cos(k * 1.05) * 30, 440 + math.sin(k * 1.05) * 30, '#f1d34f', 2)
    s.rect(70, 190, 12, 440, '#cfd3cf'); s.poly([(60, 190), (92, 190), (86, 280), (66, 280)], '#cfd3cf')
    s.rect(518, 190, 12, 440, '#cfd3cf'); ell(s, 524, 220, 22, 40, '#cfd3cf')
    vgrad(s, 640, 800, [(0, '#173a3a'), (1, '#0c1f1f')]); s.grain(102); return s.svg(102)


def yuanchandi():
    """风味原产地：梯田一层层往上，顶上一轮日头，田里站着稻穗。"""
    s = S(103); vgrad(s, 0, 800, [(0, '#f6dfa8'), (.4, '#cfe0a0'), (1, '#4c7a3f')])
    s.sun(440, 170, 52, '#fff1c4', '#fff1c4')
    for k in range(7):
        y = 330 + k * 66; c = ['#9cbd6a', '#86ad59', '#6f9a4c', '#5b8841', '#4d7a38', '#3f6a30', '#335a29'][k]
        s.path(f'M-20,{y + 30} C120,{y - 24} 280,{y + 36} 420,{y - 6} C500,{y - 24} 560,{y + 6} 640,{y - 10} L640,820 L-20,820 Z', c)
        s.path(f'M-20,{y + 34} C120,{y - 20} 280,{y + 40} 420,{y - 2} C500,{y - 20} 560,{y + 10} 640,{y - 6}', None, .5, '#e8f1c8', 3)
    for k in range(12):
        x = 40 + k * 46; y = 640 + (k % 3) * 30
        s.path(f'M{x},{y} C{x - 4},{y - 40} {x + 4},{y - 70} {x + 14},{y - 96}', None, 1, '#d9b84a', 3)
        for j in range(6): ell(s, x + 6 + j * 2, y - 40 - j * 9, 5, 2.4, '#e6c85a')
    s.grain(103); return s.svg(103)


def zaocan():
    """早餐中国：清晨，一笼小笼包冒热气，旁边一碗豆浆。"""
    s = S(104); vgrad(s, 0, 800, [(0, '#f7e3b8'), (.5, '#f4cf93'), (1, '#c98a58')])
    s.sun(150, 190, 60, '#fff3d0', '#fff3d0')
    ell(s, 300, 560, 250, 70, '#7a5236'); ell(s, 300, 520, 250, 70, '#c9a05f'); ell(s, 300, 512, 232, 58, '#e9cc8f')
    for k in range(5):
        x = 170 + k * 65; y = 505 + (k % 2) * 14
        ell(s, x, y, 34, 26, '#fdf6e6'); s.path(f'M{x - 14},{y - 6} q14,-10 28,0', None, .7, '#e4d3ac', 2)
    ell(s, 300, 640, 70, 22, '#d8d2c0'); s.rect(230, 590, 140, 50, '#efe9d8'); ell(s, 300, 590, 70, 18, '#f7f3e4'); ell(s, 300, 592, 60, 12, '#f2e8c8')
    steam(s, 300, 440, 5, op=.6, h=170)
    s.grain(104); return s.svg(104)


def guobao():
    """如果国宝会说话：深红底上一只青铜鼎，绿锈，腹上有纹。"""
    s = S(105); vgrad(s, 0, 800, [(0, '#5a1f1b'), (1, '#1f0b0a')])
    glow(s, 300, 340, 280, '#d99a5a', .45)
    cx = 300
    for dx in (-90, 90): s.path(f'M{cx + dx - 14},560 L{cx + dx - 10},660 L{cx + dx + 10},660 L{cx + dx + 14},560 Z', '#3f6a58')
    s.path(f'M{cx - 150},300 C{cx - 190},420 {cx - 130},560 {cx - 90},570 L{cx + 90},570 C{cx + 130},560 {cx + 190},420 {cx + 150},300 Z', '#4f8269')
    s.path(f'M{cx - 150},300 L{cx + 150},300 L{cx + 150},316 L{cx - 150},316 Z', '#3f6a58')
    for dx in (-150, 150): s.path(f'M{cx + dx - 12},300 L{cx + dx - 12},230 L{cx + dx + 12},230 L{cx + dx + 12},300', None, 1, '#3f6a58', 12)
    for k in range(7):
        x = cx - 110 + k * 36; s.path(f'M{x},340 q18,22 36,0 M{x},378 q18,22 36,0', None, .7, '#2f5546', 4)
    s.path(f'M{cx - 60},430 q30,30 60,0 q30,30 60,0', None, .8, '#a8d1b8', 3)
    s.circ(cx - 40, 480, 9, '#a8d1b8', .5); s.circ(cx + 70, 410, 6, '#a8d1b8', .5)
    ell(s, 300, 680, 230, 26, '#0e0504', .6); s.grain(105); return s.svg(105)


def xiangchou():
    """记住乡愁：青瓦白墙的老村，马头墙，一弯月亮。"""
    s = S(106); vgrad(s, 0, 800, [(0, '#2b3a55'), (.55, '#6a7a8e'), (1, '#c9c2ae')])
    stars(s, 30, 240); s.circ(450, 160, 44, '#f7efd2'); glow(s, 450, 160, 130, '#f7efd2', .4)
    s.range_(430, 36, '#59697a', 8, 800)
    for k, (x, w, h) in enumerate([(30, 150, 120), (190, 130, 150), (330, 160, 110), (480, 140, 140)]):
        y = 700 - h; s.rect(x, y, w, h, '#efe9dc')
        s.path(f'M{x - 8},{y} L{x + w * .5},{y - 46} L{x + w + 8},{y} Z', '#3b4048')
        s.path(f'M{x + w},{y} L{x + w},{y - 30} L{x + w + 18},{y - 8} L{x + w + 18},{y + 8} Z', '#efe9dc')
        s.rect(x + w * .38, y + h * .45, w * .24, h * .55, '#3b2a22'); s.rect(x + w * .1, y + h * .28, 18, 24, '#f2c46a', .9)
    ell(s, 300, 706, 340, 16, '#8f9a86'); vgrad(s, 706, 800, [(0, '#7a8570'), (1, '#3b4538')]); s.grain(106); return s.svg(106)


def yichuan():
    """人生一串：夜里炭火，几根烤串，火星往上飘。"""
    s = S(107); vgrad(s, 0, 800, [(0, '#150e12'), (1, '#3a1710')])
    glow(s, 300, 560, 330, '#ff7a2e', .55)
    s.rect(80, 520, 440, 120, '#2a1410'); s.rect(80, 520, 440, 10, '#e8541f')
    for k in range(18): ell(s, 100 + k * 24, 560 + (k % 3) * 8, 14, 7, ['#ff9a2e', '#ff6a1f', '#ffc25a'][k % 3], .9)
    for k in range(5):
        y = 470 + k * 6; x0 = 90 + k * 12
        s.line(x0, y + 10, 520 - k * 10, y - 16, '#cfc4a8', 3)
        for j in range(4): ell(s, x0 + 90 + j * 60, y - 6 - j * 4.5, 22, 14, ['#a8532b', '#8a3f1f', '#c0683a', '#8a3f1f'][(j + k) % 4])
    for k in range(26): s.circ(s.r.uniform(120, 480), s.r.uniform(150, 480), s.r.uniform(1.2, 3), '#ffb35a', s.r.uniform(.4, .9))
    s.grain(107); return s.svg(107)


def xiaoye():
    """宵夜江湖：夜市小摊，红灯笼，布棚。"""
    s = S(108); vgrad(s, 0, 800, [(0, '#1a1d3a'), (.6, '#3a2a4a'), (1, '#6b3a3a')])
    s.rect(60, 290, 480, 60, '#c9453a'); s.poly([(40, 350), (560, 350), (540, 380), (60, 380)], '#e2744a')
    for k in range(9): s.rect(60 + k * 53, 290, 26, 60, '#f2e2c0', .9)
    for k in range(7):
        x = 90 + k * 70; s.line(x, 120, x, 190 + (k % 2) * 20, '#3b2a22', 2); ell(s, x, 220 + (k % 2) * 20, 26, 34, '#e0392b'); glow(s, x, 220 + (k % 2) * 20, 70, '#ffb35a', .5)
    s.rect(80, 520, 440, 150, '#3b2a22'); s.rect(80, 500, 440, 22, '#8a5a3a')
    for k in range(5): ell(s, 140 + k * 80, 480, 30, 12, '#e8d9b8'); steam(s, 140 + k * 80, 470, 1, op=.45, h=70)
    vgrad(s, 670, 800, [(0, '#2a1a2a'), (1, '#120c14')]); s.grain(108); return s.svg(108)


def hexi():
    """河西走廊：雪山脚下的沙漠，一线长城，一座烽燧。"""
    s = S(109); vgrad(s, 0, 800, [(0, '#f2dcae'), (.5, '#e9b97a'), (1, '#b9733f')])
    s.sun(150, 220, 46, '#fff1c4', '#fff1c4')
    s.peak(420, 230, 470, 170, '#cdd5dd', '#8f9aa8', '#ffffff')
    s.peak(250, 300, 470, 140, '#b8c1cb', '#7f8a98', '#f6f8fa')
    s.range_(470, 22, '#c98d57', 5, 800)
    s.path('M-20,560 C100,520 220,560 340,520 C440,490 520,520 640,500 L640,820 L-20,820 Z', '#d6a064')
    s.path('M-20,700 C120,640 260,700 400,650 C500,620 560,650 640,630 L640,820 L-20,820 Z', '#b9733f')
    s.rect(430, 440, 44, 90, '#a8693b'); s.rect(424, 430, 56, 14, '#8a5330')
    s.path('M-20,590 L430,530', None, 1, '#9a5f36', 10); s.path('M-20,598 L430,538', None, .6, '#c98d57', 3)
    s.grain(109); return s.svg(109)


def shuben():
    """跟着书本去旅行：一本打开的书，书页上长出山和小路。"""
    s = S(110); vgrad(s, 0, 800, [(0, '#f1e6cf'), (1, '#d8c6a0')])
    s.poly([(60, 330), (300, 360), (300, 640), (60, 600)], '#fbf6e8'); s.poly([(540, 330), (300, 360), (300, 640), (540, 600)], '#f4ecd6')
    s.line(300, 360, 300, 640, '#c9b88f', 2)
    s.poly([(80, 470), (140, 380), (200, 450), (250, 400), (290, 470), (290, 580), (80, 560)], '#8fb08a')
    s.poly([(310, 470), (360, 400), (430, 470), (480, 420), (520, 470), (520, 570), (310, 585)], '#6f9a8a')
    s.path('M120,570 C170,520 220,540 270,500', None, .9, '#f7f1dc', 6)
    s.circ(150, 395, 22, '#f2b36a')
    s.path('M60,330 L300,360 L540,330', None, 1, '#d8c6a0', 4)
    for k in range(5): s.line(90, 620 + k * 0, 90, 620, '#fff', 0)
    ell(s, 300, 690, 230, 22, '#8a7550', .35)
    s.birds(430, 250, 4, '#6a5a3a'); s.grain(110); return s.svg(110)


def hangpai():
    """航拍中国：从天上看——一块块田，一条河拐弯，一条路穿过。"""
    s = S(111); vgrad(s, 0, 800, [(0, '#8fb98a'), (1, '#4c7a5a')])
    cols = ['#d6c26a', '#a8c46a', '#7fa860', '#c9a050', '#6e9a5e', '#e0d28a']
    for r in range(8):
        for c in range(6):
            x, y = c * 105 - 10 + (r % 2) * 14, r * 110 - 10; s.poly([(x, y), (x + 100, y + 6 * (c % 2)), (x + 96, y + 104), (x - 4, y + 100 - 5 * (r % 2))], cols[(r * 3 + c * 5) % 6], .95)
    s.path('M-20,200 C140,260 220,120 360,300 C470,440 380,560 520,640 C560,670 620,700 650,760', None, 1, '#4a8fb0', 38)
    s.path('M-20,200 C140,260 220,120 360,300 C470,440 380,560 520,640 C560,670 620,700 650,760', None, .5, '#a8d4e2', 12)
    s.path('M-20,600 C140,560 300,620 420,520 C520,440 560,380 650,360', None, 1, '#e8dcc0', 10)
    s.path('M-20,600 C140,560 300,620 420,520 C520,440 560,380 650,360', None, 1, '#9a8f78', 2)
    s.cloud(380, 90, 200, '#fff', '#dfe8ee'); s.cloud(40, 560, 160, '#fff', '#dfe8ee'); s.grain(111); return s.svg(111)


def laoguang():
    """老广的味道：骑楼拱廊，竹笼点心，暖色。"""
    s = S(112); vgrad(s, 0, 800, [(0, '#f1d9a8'), (1, '#c98a58')])
    for k in range(4):
        x = 20 + k * 150; s.rect(x, 200, 130, 520, '#e6c58a')
        s.path(f'M{x + 10},720 L{x + 10},400 Q{x + 65},320 {x + 120},400 L{x + 120},720 Z', '#8a4a2b')
        s.path(f'M{x + 22},720 L{x + 22},410 Q{x + 65},340 {x + 108},410 L{x + 108},720 Z', '#f4e4bf')
        s.rect(x, 200, 130, 22, '#6b8a4a'); s.rect(x + 40, 250, 50, 40, '#fff3d2', .9)
    ell(s, 300, 640, 220, 60, '#7a4a2b'); ell(s, 300, 616, 220, 60, '#c9a05f'); ell(s, 300, 608, 204, 50, '#e9cc8f')
    for k in range(4): ell(s, 190 + k * 74, 604 + (k % 2) * 8, 28, 20, '#fdf3dc'); s.path(f'M{176 + k * 74},{598 + (k % 2) * 8} q14,-8 28,0', None, .7, '#e4c9a0', 2)
    steam(s, 300, 560, 4, op=.5, h=130); s.grain(112); return s.svg(112)


def changjiang():
    """话说长江：江水从峡谷里出来，两岸是压进雾里的山。"""
    s = S(113); vgrad(s, 0, 800, [(0, '#dfe6e2'), (.55, '#b8cbc4'), (1, '#6c8a86')])
    for k, (x, w, h, c, op) in enumerate([(-30, 260, 520, '#7d968f', .5), (360, 280, 600, '#6b8680', .55), (140, 200, 430, '#8fa8a2', .45)]):
        s.path(f'M{x},800 L{x + 30},{800 - h} Q{x + w / 2},{800 - h - 40} {x + w - 20},{800 - h + 10} L{x + w},800 Z', c, op)
    ell(s, 300, 430, 380, 50, '#eef3f0', .7)
    s.path('M300,820 C260,700 360,640 320,540 C290,470 250,430 300,380', None, 1, '#5d8a96', 90)
    s.path('M300,820 C260,700 360,640 320,540 C290,470 250,430 300,380', None, .5, '#b8d6dc', 24)
    s.path('M308,560 l36,-30 l-6,30 z', '#3b2a22'); s.rect(318, 556, 28, 6, '#8a5a3a')
    ell(s, 300, 330, 330, 40, '#f4f7f5', .8); s.grain(113); return s.svg(113)


def silu():
    """丝绸之路：商队走过沙丘，一轮大日头，远处一座土塔。"""
    s = S(114); vgrad(s, 0, 800, [(0, '#f6d9a0'), (.5, '#ec9a5a'), (1, '#8a3f2b')])
    s.sun(300, 330, 100, '#fff0c0', '#ffe3a0')
    s.path('M-20,520 C100,470 200,520 300,490 C420,455 520,520 640,480 L640,820 L-20,820 Z', '#c9693f')
    s.path('M-20,620 C120,560 260,640 380,580 C480,540 560,590 640,570 L640,820 L-20,820 Z', '#a8502f')
    s.path('M-20,740 C140,690 300,760 460,700 C540,672 600,700 640,690 L640,820 L-20,820 Z', '#6b2f1f')
    for k in range(5):
        x = 90 + k * 82; y = 566 - k * 4 + (k % 2) * 3
        s.path(f'M{x - 16},{y} L{x - 14},{y - 24} Q{x - 6},{y - 40} {x + 6},{y - 28} L{x + 22},{y - 34} L{x + 18},{y} Z', '#2a1410')
        s.line(x - 12, y, x - 12, y + 26, '#2a1410', 3); s.line(x + 14, y, x + 14, y + 26, '#2a1410', 3)
        s.path(f'M{x - 16},{y - 14} q-18,-30 -4,-52', None, 1, '#2a1410', 4)
    s.rect(500, 400, 40, 96, '#8a3f2b'); s.rect(494, 392, 52, 12, '#6b2f1f')
    s.birds(180, 190, 3, '#6b2f1f'); s.grain(114); return s.svg(114)


def sichou():
    """新丝绸之路：绿洲里的白杨和清真寺圆顶，远处是天山。"""
    s = S(115); vgrad(s, 0, 800, [(0, '#bfe0ea'), (.5, '#eadcb8'), (1, '#b88a52')])
    s.peak(160, 240, 520, 200, '#c8d4de', '#8a98a8', '#ffffff'); s.peak(430, 290, 520, 190, '#b8c4d0', '#7d8a9a', '#f4f7fa')
    s.range_(520, 18, '#b8935c', 6, 800)
    for x, h in [(60, 190), (110, 220), (160, 180), (470, 200), (520, 230), (565, 180)]:
        ell(s, x, 620 - h / 2, 18, h / 2, '#4f7a3f'); ell(s, x, 620 - h / 2, 10, h / 2 - 6, '#6f9a52', .8); s.rect(x - 2, 620, 4, 40, '#5a4a30')
    s.path('M200,640 L200,520 Q300,380 400,520 L400,640 Z', '#f2ead6'); s.path('M215,520 Q300,400 385,520 Z', '#3f8a8a')
    s.rect(296, 380, 8, 26, '#d9b84a'); s.rect(250, 560, 100, 80, '#eadfc4'); s.path('M300,640 L300,580 Q300,560 320,580 L320,640', None, 1, '#8a6a3a', 5)
    s.rect(180, 520, 14, 120, '#f2ead6'); s.rect(406, 520, 14, 120, '#f2ead6'); s.poly([(176, 520), (197, 520), (187, 480)], '#3f8a8a'); s.poly([(402, 520), (423, 520), (413, 480)], '#3f8a8a')
    vgrad(s, 660, 800, [(0, '#b88a52'), (1, '#6b4a2a')]); s.grain(115); return s.svg(115)


def yingxiang():
    """中国影像方志：一张老县志的纸，等高线，一枚红色图钉。"""
    s = S(116); vgrad(s, 0, 800, [(0, '#efe4c8'), (1, '#d8c49a')])
    for k in range(9):
        r = 40 + k * 34; s.path(f'M{300 - r * 1.2},{430 + math.sin(k) * 14} C{300 - r},{430 - r * 1.1} {300 + r * .9},{430 - r * 1.2} {300 + r * 1.15},{430 + 10} C{300 + r},{430 + r} {300 - r},{430 + r * 1.05} {300 - r * 1.2},{430 + math.sin(k) * 14} Z', None, .55, '#b08a58', 2)
    s.path('M60,700 C180,640 220,560 320,580 C420,600 480,540 560,470', None, 1, '#6aa0b0', 8)
    s.circ(300, 380, 16, '#b7352b'); s.path('M300,396 L300,470', None, 1, '#6a5a3a', 4); ell(s, 300, 476, 22, 6, '#6a5a3a', .35)
    s.rect(70, 120, 200, 8, '#8a6a3a', .5); s.rect(70, 146, 140, 6, '#8a6a3a', .35)
    for k in range(10): s.line(60, 720 + 0, 60, 720, '#000', 0)
    s.grain(116); return s.svg(116)


def phil():
    """菲尔来蹭饭：方格桌布，几盘菜，头顶一串小灯。"""
    s = S(117); vgrad(s, 0, 800, [(0, '#f5c9a0'), (1, '#e0805a')])
    for k in range(13):
        x = 20 + k * 46; y = 150 + 28 * math.sin(k * .55); s.circ(x, y, 7, '#fff3c4'); glow(s, x, y, 36, '#fff3c4', .6)
    s.path('M0,150 Q300,200 600,150', None, 1, '#6b3b27', 2)
    s.poly([(0, 470), (600, 470), (600, 800), (0, 800)], '#f6efe0')
    for r in range(8):
        for c in range(10):
            if (r + c) % 2 == 0: s.rect(c * 60, 470 + r * 42, 60, 42, '#d9573b', .85)
    for cx, cy, c in [(180, 560, '#f1d34f'), (420, 580, '#7aa84f'), (300, 680, '#e8884a')]:
        ell(s, cx, cy, 100, 46, '#fdfaf0'); ell(s, cx, cy, 78, 34, c, .95); s.circ(cx - 20, cy - 6, 10, '#fff', .35)
    s.rect(70, 600, 10, 120, '#cfd3cf'); s.rect(520, 600, 10, 120, '#cfd3cf')
    s.grain(117); return s.svg(117)


def weizhi():
    """未知之旅：舷窗外的云海，机翼一角，天边一线暮光。"""
    s = S(118); vgrad(s, 0, 800, [(0, '#1f2a55'), (.5, '#c46a7a'), (1, '#f3b27a')])
    stars(s, 26, 220)
    for k in range(9): s.cloud(-40 + k * 70, 470 + (k % 3) * 40, 260, '#f6d9c8', '#e0a8a8')
    vgrad(s, 640, 800, [(0, '#6a5a8a'), (1, '#2a2548')])
    s.poly([(600, 380), (140, 620), (100, 700), (600, 560)], '#d8dbe0'); s.poly([(600, 380), (140, 620), (150, 640), (600, 420)], '#b8bcc4')
    s.rect(110, 640, 10, 12, '#e0392b', .9)
    s.add('<path fill-rule="evenodd" d="M0,0 L600,0 L600,800 L0,800 Z M70,70 Q300,0 530,70 L530,730 Q300,800 70,730 Z" fill="#10131f"/>')
    s.grain(118); return s.svg(118)


def jietou():
    """街头美食：推车，彩灯，蒸汽，一把遮阳伞。"""
    s = S(119); vgrad(s, 0, 800, [(0, '#1f3a4a'), (.6, '#3a6a6a'), (1, '#e0a55a')])
    for k in range(10): s.circ(30 + k * 60, 140 + 22 * math.sin(k), 7, ['#ffd24a', '#ff7a5a', '#8fe0c0'][k % 3]); glow(s, 30 + k * 60, 140 + 22 * math.sin(k), 40, '#ffe8a0', .5)
    s.path('M0,140 Q300,200 600,140', None, 1, '#10202a', 2)
    s.poly([(120, 330), (480, 330), (540, 400), (60, 400)], '#d9453a')
    for k in range(7): s.poly([(60 + k * 69, 400), (129 + k * 69, 400), (120 + k * 69, 330), (111 + k * 69 - 0, 330)], '#f4e4c8' if k % 2 == 0 else '#d9453a')
    s.line(300, 330, 300, 250, '#10202a', 6); s.rect(100, 480, 400, 130, '#8a5a3a'); s.rect(100, 480, 400, 16, '#c9965a')
    for k in range(4): ell(s, 160 + k * 90, 470, 34, 12, '#e8d9b8'); steam(s, 160 + k * 90, 460, 1, op=.5, h=100)
    for dx in (-130, 130): s.circ(300 + dx, 640, 40, '#1c1d1a'); s.circ(300 + dx, 640, 16, '#8a8a82')
    vgrad(s, 690, 800, [(0, '#3a4a3a'), (1, '#12181a')]); s.grain(119); return s.svg(119)


def lp():
    """孤独星球年度榜：罗盘压在经纬网上，蓝底。"""
    s = S(120); vgrad(s, 0, 800, [(0, '#1a4a7a'), (1, '#0c2440')])
    for k in range(8): ell(s, 300, 400, 90 + k * 34, 250, None or 'none', 0); s.path(f'M{300 - (90 + k * 34)},400 A{90 + k * 34},250 0 1,0 {300 + (90 + k * 34)},400 A{90 + k * 34},250 0 1,0 {300 - (90 + k * 34)},400', None, .25, '#9fd0f0', 1.5)
    for k in range(6): s.path(f'M60,{240 + k * 64} Q300,{240 + k * 64 + (k - 2.5) * 20} 540,{240 + k * 64}', None, .25, '#9fd0f0', 1.5)
    s.circ(300, 400, 150, '#f4e8c4'); s.circ(300, 400, 138, '#0f2f55'); s.circ(300, 400, 120, 'none')
    for k in range(32):
        a = k * math.pi / 16; r0 = 120 if k % 4 else 104; s.line(300 + math.cos(a) * r0, 400 + math.sin(a) * r0, 300 + math.cos(a) * 134, 400 + math.sin(a) * 134, '#f4e8c4', 2 if k % 4 else 3)
    s.poly([(300, 280), (322, 400), (300, 520), (278, 400)], '#e0392b'); s.poly([(180, 400), (300, 378), (420, 400), (300, 422)], '#f4e8c4'); s.circ(300, 400, 14, '#f4e8c4')
    stars(s, 30, 200); s.grain(120); return s.svg(120)


def natgeo():
    """国家地理年度榜：黄色画框，框里一座山，一轮低日。"""
    s = S(121); s.rect(0, 0, W, H, '#f2c230')
    s.rect(60, 90, 480, 620, '#3a5a7a'); vgrad(s, 90, 710, [(0, '#f6d7a0'), (.45, '#e89a5a'), (1, '#3a2a3a')])
    s.sun(380, 300, 54, '#fff1c4', '#fff1c4')
    s.peak(230, 330, 620, 210, '#6a5a6a', '#3f3446', '#f4e4dc'); s.peak(430, 410, 620, 130, '#7a6a76', '#4f4256', None)
    vgrad(s, 600, 710, [(0, '#3a2a3a'), (1, '#1a1220')])
    s.conifer(120, 700, 120, '#1a2a22'); s.conifer(170, 700, 90, '#223a2c'); s.conifer(500, 700, 110, '#1a2a22')
    s.path('M60,90 L540,90 L540,710 L60,710 Z', None, 1, '#f2c230', 6); s.grain(121); return s.svg(121)


def roc():
    """Roc山海行（河西走廊自驾）：落日，祁连雪山，一条笔直的戈壁公路，路上一辆车。"""
    s = S(122); vgrad(s, 0, 800, [(0, '#2a2f55'), (.42, '#d9774f'), (.62, '#f4c27a'), (1, '#e8b678')])
    s.circ(420, 330, 64, '#fff1c4'); glow(s, 420, 330, 150, '#ffd79a', .5)
    s.poly([(0, 470), (90, 380), (170, 430), (260, 330), (350, 440), (430, 390), (520, 450), (600, 400), (600, 520), (0, 520)], '#5a4a6a')
    s.poly([(260, 330), (232, 372), (250, 366), (262, 388), (278, 362), (298, 376)], '#f6e9e0')
    s.poly([(90, 380), (68, 410), (86, 404), (98, 420), (112, 398)], '#f6e9e0')
    s.poly([(0, 520), (600, 520), (600, 800), (0, 800)], '#c99a62')
    s.poly([(0, 640), (600, 560), (600, 800), (0, 800)], '#b5834e', .45)
    s.poly([(270, 520), (330, 520), (560, 800), (40, 800)], '#3a3433')
    for k in range(6):
        y0 = 540 + k * k * 8 + k * 14; s.poly([(298 - k * 1.2, y0), (302 + k * 1.2, y0), (303 + k * 2.4, y0 + 18 + k * 4), (297 - k * 2.4, y0 + 18 + k * 4)], '#f2d68a')
    s.rect(262, 690, 76, 30, '#c8432f'); s.rect(274, 676, 52, 20, '#d9d9d4'); s.circ(280, 724, 9, '#1c1d1a'); s.circ(320, 724, 9, '#1c1d1a')
    s.grain(122); return s.svg(122)


SHOWS = {'shejian': shejian, 'fengwei': fengwei, 'yuanchandi': yuanchandi, 'zaocan': zaocan, 'guobao': guobao, 'xiangchou': xiangchou, 'yichuan': yichuan, 'xiaoye': xiaoye,
         'hexi': hexi, 'shuben': shuben, 'hangpai': hangpai, 'laoguang': laoguang, 'changjiang': changjiang, 'silu': silu, 'sichou': sichou, 'yingxiang': yingxiang,
         'phil': phil, 'weizhi': weizhi, 'roc': roc, 'jietou': jietou, 'lp': lp, 'natgeo': natgeo}
if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for k, fn in SHOWS.items():
        open(os.path.join(OUT, f'show-{k}.svg'), 'w', encoding='utf-8').write(fn())
    print('写了', len(SHOWS), '张')
