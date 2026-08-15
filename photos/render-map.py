#!/usr/bin/env python3
"""拼瓦片做地图缩略图。
   单张瓦片的问题：点位可能落在瓦片边角，看到的是一片空白郊野。
   拼 3×3 再以点位为中心裁剪，点一定在正中，还能自由选缩放看更大范围。

   用法：
     python3 render-map.py --preview        对比 z9/z10/z11 三种缩放
     python3 render-map.py --zoom 10        按指定缩放全量渲染
"""
import json, math, io, os, sys, base64, urllib.request, concurrent.futures
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.abspath(__file__))
UA = 'ZouniTravelApp/1.0 (https://ourword.ai/zouni/; contact@ourword.ai)'
TS = 256          # 瓦片边长
OUT_W, OUT_H = 200, 150

def deg2num(lat, lon, z):
    """返回带小数的瓦片坐标，小数部分用于精确定位点在瓦片内的位置"""
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n
    lat_r = math.radians(lat)
    y = (1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n
    return x, y

_cache = {}
def get_tile(z, x, y):
    key = (z, x, y)
    if key in _cache:
        return _cache[key]
    n = 2 ** z
    if x < 0 or y < 0 or x >= n or y >= n:
        img = Image.new('RGB', (TS, TS), (233, 237, 228))
        _cache[key] = img
        return img
    url = f'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': UA})
        raw = urllib.request.urlopen(req, timeout=25).read()
        img = Image.open(io.BytesIO(raw)).convert('RGB')
    except Exception:
        img = Image.new('RGB', (TS, TS), (233, 237, 228))
    _cache[key] = img
    return img

def render(lat, lon, z, w=OUT_W, h=OUT_H):
    """拼 3×3 瓦片，以点位为中心裁出 w×h，中心画定位针"""
    fx, fy = deg2num(lat, lon, z)
    cx, cy = int(fx), int(fy)
    canvas = Image.new('RGB', (TS * 3, TS * 3), (233, 237, 228))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            canvas.paste(get_tile(z, cx + dx, cy + dy), ((dx + 1) * TS, (dy + 1) * TS))
    # 点位在画布上的像素坐标
    px = TS + (fx - cx) * TS
    py = TS + (fy - cy) * TS
    left, top = int(px - w / 2), int(py - h / 2)
    left = max(0, min(left, TS * 3 - w))
    top = max(0, min(top, TS * 3 - h))
    im = canvas.crop((left, top, left + w, top + h))
    # 画定位针：白描边红点，任何底色上都看得清
    d = ImageDraw.Draw(im)
    mx, my = int(px - left), int(py - top)
    d.ellipse([mx - 6, my - 6, mx + 6, my + 6], fill=(255, 255, 255))
    d.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=(153, 74, 64))
    return im

def to_b64(im, q=62):
    buf = io.BytesIO()
    im.save(buf, 'JPEG', quality=q, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()

DB = json.load(open(ROOT + '/photos.json', encoding='utf-8'))
maps = [(k, v) for k, v in DB.items() if v.get('type') == 'map' and v.get('lat')]

if '--preview' in sys.argv:
    # 挑三个典型点位：荒野 / 景区 / 城市
    picks = []
    for want in ['poi:sanwan', 'poi:ghost-city', 'poi:cq-erchang', 'poi:hemu-view']:
        for k, v in maps:
            if k == want:
                picks.append((k, v)); break
    out = {}
    for z in (9, 10, 11, 12):
        for k, v in picks:
            out[f'{k}@z{z}'] = to_b64(render(v['lat'], v['lon'], z, 220, 165))
    html = ['<!doctype html><meta charset="utf-8"><body style="background:#f0f0ec;font:12px/1.5 sans-serif;padding:14px">']
    html.append('<h3 style="margin:0 0 10px">缩放级别对比 · 点位已居中</h3>')
    for k, v in picks:
        html.append(f'<div style="margin-bottom:14px"><b>{k}</b><div style="display:flex;gap:6px;margin-top:5px">')
        for z in (9, 10, 11, 12):
            span = round(40075 * math.cos(math.radians(v["lat"])) / (2 ** z) * (220/256), 1)
            html.append(f'<div style="text-align:center"><img src="data:image/jpeg;base64,{out[f"{k}@z{z}"]}" '
                        f'style="border-radius:8px;box-shadow:0 0 0 1px rgba(0,0,0,.08)"><div>z{z} · 约{span}km</div></div>')
        html.append('</div></div>')
    html.append('</body>')
    open(ROOT + '/zoom-preview.html', 'w').write(''.join(html))
    print('对比图已生成：zoom-preview.html')
    sys.exit(0)

Z = int(sys.argv[sys.argv.index('--zoom') + 1]) if '--zoom' in sys.argv else 10
LIMIT = int(sys.argv[sys.argv.index('--limit') + 1]) if '--limit' in sys.argv else 0
thumbs = json.load(open(ROOT + '/thumbs.json')) if os.path.exists(ROOT + '/thumbs.json') else {}
done_keys = set(json.load(open(ROOT+'/rendered.json'))) if os.path.exists(ROOT+'/rendered.json') else set()
todo = [(k, v) for k, v in maps if k not in done_keys]
if LIMIT:
    todo = todo[:LIMIT]
print(f'渲染 {len(todo)} 张地图缩略图（z{Z}，点位居中）…')

def work(item):
    k, v = item
    try:
        return k, to_b64(render(v['lat'], v['lon'], Z))
    except Exception as e:
        return k, None

ok = 0
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    for i, (k, b64) in enumerate(ex.map(work, todo)):
        if b64:
            thumbs[k] = b64; ok += 1
        if (i + 1) % 30 == 0:
            print(f'  {i+1}/{len(todo)}')
            json.dump(thumbs, open(ROOT + '/thumbs.json', 'w'), separators=(',', ':'))

json.dump(thumbs, open(ROOT + '/thumbs.json', 'w'), separators=(',', ':'))
total = sum(len(v) for v in thumbs.values())
print(f'\n  完成 {ok} 张 · 缓存瓦片 {len(_cache)} 块')
print(f'  thumbs.json {total/1024/1024:.2f} MB')
