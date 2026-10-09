import math
from gen import S, W, H, OUT, f
from gen3 import vgrad, glow


def ell(s, cx, cy, rx, ry, c, op=1):
    s.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{c}" opacity="{op}"/>')


def cd3():
    s = S(31)
    vgrad(s, 0, 560, [(0, '#f1dcb7'), (.6, '#ecc995'), (1, '#e3b47a')])
    glow(s, 420, 200, 260, '#fff2d6', .55)
    # 屋檐：压淡
    s.poly([(0, 40), (600, 10), (600, 62), (0, 92)], '#8a6a4c', .35)
    for k in range(16):
        x = k * 40
        s.poly([(x, 92 - k * 2), (x + 30, 90 - k * 2), (x + 30, 104 - k * 2), (x, 106 - k * 2)], '#7a5a3e', .28)
    # 竹影：压淡
    for side, x0 in (('l', 30), ('r', 560)):
        for k in range(6):
            y = 140 + k * 46
            ang = (-0.5 if side == 'l' else 0.5) + s.r.uniform(-.2, .2)
            L = 70
            p = [(x0, y), (x0 + L * math.cos(ang) * (1 if side == 'l' else -1) * -1, y + L * math.sin(abs(ang))), (x0 + 6, y + 10)]
            s.path(f'M{f(x0)},{f(y)} q{f(30 if side=="l" else -30)},-10 {f(70 if side=="l" else -70)},{f(18)} q-{f(30 if side=="l" else -30)},12 -{f(70 if side=="l" else -70)},-18 Z', '#7f9a6a', .35)
        s.rect(x0 - 3 if side == 'l' else x0 - 3, 100, 6, 460, '#8aa070', .3)
    # 竹椅椅背：右侧，压淡
    for k in range(9):
        s.rect(470 + k * 13, 250, 6, 330, '#c9a36a', .55)
    s.rect(462, 250, 130, 10, '#b88d55', .6)
    s.rect(462, 330, 130, 8, '#b88d55', .5)
    # 桌面
    vgrad(s, 560, 800, [(0, '#4a3322'), (1, '#1d140d')])
    for k in range(7):
        y0 = 580 + k * 30
        s.path(f'M-10,{y0} C150,{y0 - 6} 320,{y0 + 6} 610,{y0 - 4}', None, .25, '#6a4a32', 2)
    s.rect(0, 556, W, 8, '#5c4130')
    # 主角：盖碗
    cx, base = 280, 540
    ell(s, cx + 10, base + 22, 190, 26, '#1a120c', .45)          # 影子
    ell(s, cx, base, 170, 34, '#c9a24f')                          # 茶船（铜）
    ell(s, cx, base - 6, 150, 26, '#e1bd68')
    ell(s, cx, base - 10, 118, 18, '#b58d3f', .6)
    # 碗身
    s.path(f'M{cx - 120},{base - 150} C{cx - 118},{base - 60} {cx - 70},{base - 14} {cx},{base - 12} C{cx + 70},{base - 14} {cx + 118},{base - 60} {cx + 120},{base - 150} Z', '#f7f4ec')
    s.path(f'M{cx + 30},{base - 150} C{cx + 60},{base - 120} {cx + 100},{base - 70} {cx + 120},{base - 150} Z', '#dcd6c8', .7)
    s.path(f'M{cx - 112},{base - 104} C{cx - 60},{base - 92} {cx + 60},{base - 92} {cx + 112},{base - 104}', None, .9, '#2f5c8a', 5)
    s.path(f'M{cx - 106},{base - 90} C{cx - 60},{base - 80} {cx + 60},{base - 80} {cx + 106},{base - 90}', None, .7, '#2f5c8a', 2)
    for k in range(7):
        x = cx - 84 + k * 28
        s.circ(x, base - 72, 5, '#2f5c8a', .8)
    ell(s, cx, base - 150, 120, 20, '#ede8db')
    ell(s, cx - 20, base - 150, 92, 14, '#7c8a3c')                # 茶汤（盖子没盖严，露出一角）
    for k in range(5):
        s.path(f'M{cx - 70 + k * 22},{base - 152} l12,-3', None, .9, '#4e6a2a', 3)
    # 盖子：斜搭在碗沿
    s.add(f'<g transform="rotate(-9 {cx + 40} {base - 170})">')
    s.path(f'M{cx - 80},{base - 166} C{cx - 60},{base - 214} {cx + 140},{base - 214} {cx + 160},{base - 166} Z', '#f8f5ee')
    ell(s, cx + 40, base - 166, 120, 12, '#e4dece')
    s.path(f'M{cx - 50},{base - 182} C{cx},{base - 196} {cx + 80},{base - 196} {cx + 130},{base - 182}', None, .9, '#2f5c8a', 4)
    ell(s, cx + 40, base - 214, 22, 8, '#e9e4d6')
    ell(s, cx + 40, base - 222, 12, 9, '#f8f5ee')
    s.add('</g>')
    # 热气
    for k in range(3):
        x = cx - 40 + k * 32
        s.path(f'M{x},{base - 196} c-14,-24 14,-40 0,-64 c-12,-20 10,-36 2,-56', None, .55, '#fffaf0', 5)
    # 一小碟瓜子：配角
    ell(s, 500, 600, 54, 14, '#e9e2d2')
    for k in range(14):
        ell(s, 470 + s.r.uniform(0, 60), 594 + s.r.uniform(-4, 6), 6, 3, '#3a2a1e')
    s.grain(31)
    return s.svg(31)


svg = cd3()
open(f'{OUT}/cd3.svg', 'w', encoding='utf-8').write(svg)
print('cd3.svg', len(svg) // 1024, 'KB')
