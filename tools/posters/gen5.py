import math
from gen import S, W, H, OUT, f
import gen3
from gen3 import vgrad, glow


def ell(s, cx, cy, rx, ry, c, op=1):
    s.add(f'<ellipse cx="{f(cx)}" cy="{f(cy)}" rx="{f(rx)}" ry="{f(ry)}" fill="{c}" opacity="{op}"/>')


def sh3():
    """上海：主角是海关大楼的钟楼，黄昏；对岸陆家嘴压成剪影。"""
    s = S(51)
    vgrad(s, 0, 600, [(0, '#1e2a44'), (.55, '#6d5a7a'), (.85, '#e3a27a'), (1, '#f0c48e')])
    glow(s, 300, 560, 260, '#ffd9a8', .35)
    # 对岸：压淡
    for x, w, h in [(30, 26, 160), (70, 40, 110), (120, 18, 230), (150, 50, 140), (420, 60, 120), (490, 30, 200), (530, 46, 150)]:
        s.rect(x, 560 - h, w, h, '#4b4560', .55)
    s.path('M120,330 l9,-60 l9,60 Z', '#4b4560', .55)
    # 江面
    vgrad(s, 560, 640, [(0, '#3a3a52'), (1, '#24243a')])
    for k in range(10):
        y = 572 + k * 7
        s.rect(80 + (k * 37) % 300, y, 60 + (k * 13) % 50, 2, '#f0c48e', .35)
    # 主角：钟楼
    cx = 300
    s.rect(cx - 70, 330, 140, 330, '#d9c7a4')               # 楼身
    for r in range(5):
        for c in range(4):
            s.rect(cx - 56 + c * 30, 360 + r * 52, 14, 30, '#ffcf7a' if (r + c) % 3 else '#6b5a44', .95)
    s.rect(cx - 46, 250, 92, 82, '#e2d2b0')                 # 钟楼
    s.circ(cx, 290, 28, '#f6eedb')
    s.circ(cx, 290, 24, '#efe4c8')
    s.path(f'M{cx},{290} l0,-17 M{cx},{290} l12,6', None, 1, '#3a2f22', 3)
    s.path(f'M{cx - 50},{250} L{cx},{196} L{cx + 50},{250} Z', '#9a8a6a')  # 尖顶
    s.rect(cx - 3, 172, 6, 26, '#9a8a6a')
    s.rect(cx - 80, 640, 160, 160, '#1a1a28')
    # 近岸：外滩栏杆和地面（深色，留给标题）
    vgrad(s, 640, 800, [(0, '#1b1c2a'), (1, '#0f1018')])
    for k in range(16):
        s.rect(k * 40, 632, 4, 18, '#2a2b3c')
    s.rect(0, 628, W, 6, '#2a2b3c')
    s.grain(51)
    return s.svg(51)


def hz3():
    """杭州：主角是湖对岸夕照里的雷峰塔；断桥和远山压淡。"""
    s = S(52)
    vgrad(s, 0, 520, [(0, '#f3d9b8'), (.6, '#efb98a'), (1, '#e79a6b')])
    glow(s, 420, 360, 160, '#fff1d8', .7)
    s.circ(420, 360, 34, '#fff3dc', .95)
    # 远山：压淡
    s.path('M0,430 C80,380 150,400 220,372 C300,340 360,390 440,360 C520,332 560,380 600,370 L600,520 L0,520 Z', '#c98d6e', .55)
    s.path('M0,470 C100,440 200,456 300,440 C400,424 500,452 600,440 L600,520 L0,520 Z', '#a8735c', .6)
    # 主角：雷峰塔
    cx, base = 250, 470
    for i, (w, h) in enumerate([(70, 34), (62, 32), (54, 30), (46, 28), (38, 26)]):
        y = base - sum(hh for _, hh in [(70, 34), (62, 32), (54, 30), (46, 28), (38, 26)][:i + 1])
        s.rect(cx - w / 2, y, w, h - 8, '#5a3a2e')
        s.path(f'M{cx - w / 2 - 12},{y + h - 8} L{cx + w / 2 + 12},{y + h - 8} L{cx + w / 2 + 4},{y + h - 2} L{cx - w / 2 - 4},{y + h - 2} Z', '#3b2620')
        for k in range(3):
            s.rect(cx - w / 2 + 8 + k * (w - 16) / 2.5, y + 6, 6, 10, '#ffd28a', .9)
    s.path(f'M{cx - 16},{base - 150} L{cx},{base - 184} L{cx + 16},{base - 150} Z', '#3b2620')
    s.rect(cx - 2, base - 200, 4, 18, '#3b2620')
    # 湖面
    vgrad(s, 520, 800, [(0, '#c98b6a'), (.35, '#6b4a48'), (1, '#1d1a20')])
    for k in range(12):
        y = 530 + k * 10
        s.rect(390 + (k % 3) * 8 - k * 2, y, 60 - k * 3, 3, '#ffe2b8', .55)
    # 塔的倒影：淡
    s.rect(cx - 20, 522, 40, 70, '#4a302a', .35)
    # 断桥：右侧，压淡
    s.path('M440,512 Q520,470 600,505 L600,520 L440,520 Z', '#7a5a4a', .55)
    s.grain(52)
    return s.svg(52)


def sz3():
    """苏州：主角是白墙上的月洞门，门里一角亭子和一枝梅。"""
    s = S(53)
    vgrad(s, 0, 800, [(0, '#f2efe6'), (1, '#e6e1d4')])
    # 屋檐压顶
    s.rect(0, 0, W, 40, '#3d4249')
    for k in range(20):
        s.rect(k * 30, 40, 22, 8, '#4c525a')
    # 门里的景
    cx, cy, r = 300, 380, 190
    s.add(f'<clipPath id="moon"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath><g clip-path="url(#moon)">')
    vgrad(s, cy - r, cy + r, [(0, '#cfe0d6'), (1, '#8fb3a0')])
    s.path(f'M{cx - r},{cy + 60} C{cx - 80},{cy + 30} {cx + 60},{cy + 70} {cx + r},{cy + 40} L{cx + r},{cy + r} L{cx - r},{cy + r} Z', '#6e9a84')
    s.path(f'M{cx - r},{cy + 120} L{cx + r},{cy + 110} L{cx + r},{cy + r} L{cx - r},{cy + r} Z', '#5d8a8a', .9)
    # 亭子
    px, py = cx + 70, cy + 20
    s.path(f'M{px - 70},{py - 40} Q{px},{py - 90} {px + 70},{py - 40} L{px + 52},{py - 30} L{px - 52},{py - 30} Z', '#3d4249')
    s.rect(px - 44, py - 30, 6, 70, '#5b4a3a')
    s.rect(px + 38, py - 30, 6, 70, '#5b4a3a')
    s.rect(px - 50, py + 34, 100, 8, '#7a6a58')
    s.add('</g>')
    # 门框
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r + 10}" fill="none" stroke="#9aa0a6" stroke-width="16"/>')
    s.add(f'<circle cx="{cx}" cy="{cy}" r="{r + 2}" fill="none" stroke="#c7cbcf" stroke-width="4"/>')
    # 一枝梅：从左上伸进门洞
    s.path(f'M60,190 C140,220 190,250 240,300 C260,320 280,340 300,346', None, 1, '#3a2f28', 7)
    s.path('M180,236 C200,214 222,206 236,200', None, 1, '#3a2f28', 4)
    for (x, y) in [(150, 214), (196, 238), (236, 200), (252, 312), (286, 338), (224, 282), (120, 204)]:
        for a in range(5):
            ang = a * 2 * math.pi / 5
            s.circ(x + 6 * math.cos(ang), y + 6 * math.sin(ang), 5, '#e9a2a8')
        s.circ(x, y, 3, '#f7d36a')
    # 地面：深色石板，留给标题
    vgrad(s, 600, 800, [(0, '#5b6168'), (1, '#24282d')])
    for k in range(8):
        s.rect(k * 80, 600, 2, 200, '#4a5056', .6)
    s.grain(53)
    return s.svg(53)


for name, fn in (('sh3', sh3), ('hz3', hz3), ('sz3', sz3)):
    svg = fn()
    open(f'{OUT}/{name}.svg', 'w', encoding='utf-8').write(svg)
    print(name, len(svg) // 1024, 'KB')
