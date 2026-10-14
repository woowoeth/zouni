import math
from gen import S, W, H, OUT, f
from gen3 import vgrad, glow


def ell(s, cx, cy, rx, ry, c, op=1):
    s.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{c}" opacity="{op}"/>')


def zjj4():
    """张家界：主角是一根石英砂岩柱，顶上长着松；别的峰压进雾里。"""
    s = S(61)
    vgrad(s, 0, 640, [(0, '#dfe6e2'), (.6, '#c9d6d0'), (1, '#b7c8c1')])
    # 远峰：压淡
    for x, w, h in [(30, 46, 300), (90, 34, 380), (420, 40, 340), (480, 54, 280), (540, 36, 360)]:
        s.path(f'M{x},{640} L{x + 4},{640 - h} Q{x + w / 2},{640 - h - 14} {x + w - 4},{640 - h} L{x + w},{640} Z', '#9fb3ad', .45)
    # 雾带
    for k, y in enumerate((420, 500, 560)):
        ell(s, 300, y, 360, 34, '#eef2ef', .7)
    # 主角：石柱
    cx = 290
    s.path(f'M{cx - 52},{800} L{cx - 46},{300} Q{cx - 40},{250} {cx - 10},{236} Q{cx + 30},{226} {cx + 44},{262} L{cx + 56},{800} Z', '#8a7b66')
    for k in range(9):
        y = 300 + k * 54
        s.path(f'M{cx - 46},{y} Q{cx},{y + 6} {cx + 50},{y - 4}', None, .5, '#6d604f', 3)
    s.path(f'M{cx + 8},{240} L{cx + 50},{800} L{cx + 56},{800} L{cx + 44},{262} Z', '#6f6352', .7)
    # 顶上的松
    for (dx, dy, w) in [(-26, 214, 64), (-10, 196, 56), (6, 180, 44)]:
        ell(s, cx + dx + w / 2 - 30, dy, w / 2, 9, '#3f5a46')
    s.path(f'M{cx - 4},{236} C{cx - 6},{214} {cx + 4},{200} {cx},{180}', None, 1, '#4a3a2c', 5)
    # 前景雾和深色崖底，留给标题
    ell(s, 300, 620, 420, 60, '#e9efec', .85)
    vgrad(s, 640, 800, [(0, '#5c6a64'), (1, '#1f2624')])
    s.grain(61)
    return s.svg(61)


def hk2():
    """香港：主角是维港上的一艘天星小轮；对岸的楼压成剪影。"""
    s = S(62)
    vgrad(s, 0, 470, [(0, '#24345a'), (.6, '#a86c7a'), (1, '#efb07c')])
    glow(s, 160, 440, 160, '#ffd9a8', .5)
    # 对岸：压淡
    xs = 0
    for k, (w, h) in enumerate([(30, 120), (22, 200), (36, 150), (18, 260), (40, 170), (26, 220), (34, 140), (20, 300), (44, 180), (30, 230), (38, 160), (24, 210), (40, 130), (30, 190), (40, 150)]):
        s.rect(xs, 470 - h, w, h, '#3d3a58', .6)
        for r in range(0, h - 20, 22):
            if (k + r) % 3 == 0: s.rect(xs + 6, 470 - h + 10 + r, w - 12, 3, '#ffd28a', .45)
        xs += w + 2
    # 山
    s.path('M0,330 C120,280 240,300 320,270 C420,236 520,280 600,262 L600,350 L0,350 Z', '#2c2b46', .35)
    # 海
    vgrad(s, 470, 800, [(0, '#5a5a7c'), (.4, '#2b2c46'), (1, '#12131f')])
    for k in range(14):
        y = 486 + k * 9
        s.rect(60 + (k * 53) % 420, y, 50 + (k * 17) % 60, 2, '#ffd9a8', .3)
    # 主角：天星小轮
    cx, y0 = 300, 560
    s.path(f'M{cx - 150},{y0} L{cx + 150},{y0} L{cx + 128},{y0 + 34} L{cx - 128},{y0 + 34} Z', '#1f5a3e')   # 船身绿
    s.rect(cx - 150, y0 - 4, 300, 8, '#e9e2cf')
    s.rect(cx - 118, y0 - 40, 236, 36, '#f2ecdc')                                                           # 上层白
    for k in range(10):
        s.rect(cx - 108 + k * 23, y0 - 32, 14, 18, '#ffd28a', .9)
    s.rect(cx - 126, y0 - 46, 252, 8, '#1f5a3e')
    s.rect(cx - 6, y0 - 70, 12, 26, '#e9e2cf')
    s.rect(cx - 9, y0 - 74, 18, 6, '#1f5a3e')
    ell(s, cx, y0 + 40, 170, 8, '#0c0d16', .5)
    for k in range(5):
        s.path(f'M{cx + 150 + k * 10},{y0 + 26 + k * 3} l40,0', None, .5 - k * .08, '#e9e2cf', 2)
    s.grain(62)
    return s.svg(62)


def kansai4():
    """大阪：主角是大阪城天守阁，石垣在下；城下的树压淡。"""
    s = S(63)
    vgrad(s, 0, 600, [(0, '#bfd6e4'), (.7, '#e8e2d2'), (1, '#efd9b8')])
    glow(s, 440, 160, 120, '#fff6e2', .6)
    cx = 300
    # 石垣
    s.path(f'M{cx - 170},{600} L{cx - 130},{470} L{cx + 130},{470} L{cx + 170},{600} Z', '#9a9285')
    for k in range(6):
        y = 482 + k * 20
        s.path(f'M{cx - 130 - k * 6},{y} L{cx + 130 + k * 6},{y}', None, .35, '#6e675c', 2)
    # 天守：五层屋檐
    levels = [(220, 46), (190, 42), (160, 40), (128, 38), (96, 36)]
    y = 470
    for i, (w, h) in enumerate(levels):
        s.rect(cx - w / 2 + 10, y - h, w - 20, h, '#f4f1ea')
        for k in range(int((w - 40) / 26)):
            s.rect(cx - w / 2 + 22 + k * 26, y - h + 12, 12, 14, '#3a4a5a', .85)
        s.path(f'M{cx - w / 2 - 14},{y - h + 4} Q{cx},{y - h - 16} {cx + w / 2 + 14},{y - h + 4} L{cx + w / 2 - 6},{y - h + 10} L{cx - w / 2 + 6},{y - h + 10} Z', '#3f6f72')
        s.rect(cx - w / 2 - 4, y - h + 2, w + 8, 4, '#c9a24f', .9)
        y -= h
    s.path(f'M{cx - 34},{y + 4} L{cx},{y - 30} L{cx + 34},{y + 4} Z', '#3f6f72')
    for sx in (-1, 1):
        s.path(f'M{cx + sx * 26},{y} q{sx * 6},-10 {sx * 2},-18', None, 1, '#c9a24f', 4)
    # 城下的树：压淡
    for k in range(12):
        ell(s, 20 + k * 52, 610, 40, 28, '#6f8a6a', .55)
    # 护城河和深色前景，留给标题
    vgrad(s, 620, 800, [(0, '#3e5560'), (1, '#16212a')])
    for k in range(8):
        s.rect(60 + k * 60, 640 + (k % 3) * 18, 40, 2, '#c9d6dc', .3)
    s.grain(63)
    return s.svg(63)


for name, fn in (('zjj4', zjj4), ('hk2', hk2), ('kansai4', kansai4)):
    svg = fn()
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8').write(svg)
    print(name, len(svg) // 1024, 'KB')
