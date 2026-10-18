#!/usr/bin/env python3
"""路线地图的自托管底图资源（2026-10-18）：把 OpenFreeMap 的 liberty 样式、sprite、常用西文字形取一份放进 site_src/map/，建站时原样拷到 assets/map/。

为什么：以前每次点开地图都要先到 tiles.openfreemap.org 取样式（43KB）→ 再取 sprite → 再取字形，串成一条链，慢网下占了一大半时间；
自托管以后它们和 routemap.js 一样走本站（GitHub Pages / Service Worker），运行时不再改图层（隐藏边界、标注改中文的修改在这里一次做完）。

用法：
    python3 tools/map_assets.py            # site_src/map/ 已齐就什么都不做（建站每次调用，不联网）
    python3 tools/map_assets.py --refresh  # 重新从 OpenFreeMap 取（样式换版本、边界图层 id 变了时；之后重跑 tests/data_checks.py 的第 33 项和 route_map_check --live）
    python3 tools/map_assets.py --check    # 只联网对照：线上样式里命中隐藏规则的图层，在自托管样式里是不是全部 visibility:none（data_checks 33 / map_app_check --live 用）

产物：
    site_src/map/style.json            已改好的样式（边界 / 国家 / 省级 / 争议图层全部 visibility:none；标注 text-field 改成中文优先）；sprite / glyphs 写成站内绝对路径（运行时 routemap.js 补上 origin）
    site_src/map/sprite/ofm{,@2x}.{json,png}
    site_src/map/fonts/<字体名>/<范围>.pbf     西文常用范围（0-255 / 256-511 / 8192-8447）；中文字形不下载（localIdeographFontFamily 用系统字体），别的范围运行时回退到 OpenFreeMap
"""
import json, os, re, sys, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'site_src', 'map')
OFM = 'https://tiles.openfreemap.org'
STYLE_URL = OFM + '/styles/liberty'
# 合规：边界线图层（含争议边界）和国家 / 省级标注一律隐藏（data_checks 33 扫这一行）
HIDE_RE = re.compile(r'boundary|country|state|disputed')
ZH_TEXT = ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh'], ['get', 'name']]
FONT_RANGES = ['0-255', '256-511', '8192-8447']
LOCAL_PREFIX = '/assets/map'


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'zouni-build/1.0 (+https://zouni.app)', 'Accept-Encoding': 'identity'})
    import ssl
    try: ctx = ssl.create_default_context()
    except Exception: ctx = None
    try: return urllib.request.urlopen(req, timeout=40, context=ctx).read()
    except Exception:
        import subprocess      # 本机 Python 的 urllib 访问 HTTPS 会证书校验失败（见 docs/handoff/04）：退回 curl，不关证书校验
        r = subprocess.run(['curl', '-sfL', '--max-time', '40', '-A', 'zouni-build/1.0 (+https://zouni.app)', url], capture_output=True)
        if r.returncode != 0 or not r.stdout: raise RuntimeError('取不到 ' + url)
        return r.stdout


def tune(st):
    """隐藏边界 / 国家 / 省级图层；标注 text-field 改成中文优先（盾牌 shield 图层不动）。返回 (样式, 隐藏的图层数)"""
    n = 0
    for l in st['layers']:
        if HIDE_RE.search(l['id']):
            l.setdefault('layout', {})['visibility'] = 'none'; n += 1
        elif l.get('type') == 'symbol' and l.get('layout', {}).get('text-field') and 'shield' not in l['id']:
            l['layout']['text-field'] = ZH_TEXT
    return st, n


def fonts_of(st):
    s = set()
    for l in st['layers']:
        tf = l.get('layout', {}).get('text-font')
        if isinstance(tf, list):
            for f in tf:
                if isinstance(f, str): s.add(f)
    return sorted(s)


def refresh():
    st = json.loads(get(STYLE_URL))
    sprite = st['sprite']; glyphs = st['glyphs']
    st, n_hide = tune(st)
    st['sprite'] = LOCAL_PREFIX + '/sprite/ofm'
    st['glyphs'] = LOCAL_PREFIX + '/fonts/{fontstack}/{range}.pbf'
    os.makedirs(os.path.join(OUT, 'sprite'), exist_ok=True)
    for suf in ('', '@2x'):
        for ext in ('json', 'png'):
            open(os.path.join(OUT, 'sprite', 'ofm%s.%s' % (suf, ext)), 'wb').write(get('%s%s.%s' % (sprite, suf, ext)))
    tot = 0
    for f in fonts_of(st):
        d = os.path.join(OUT, 'fonts', f); os.makedirs(d, exist_ok=True)
        for r in FONT_RANGES:
            b = get(glyphs.replace('{fontstack}', urllib.parse.quote(f)).replace('{range}', r)); open(os.path.join(d, r + '.pbf'), 'wb').write(b); tot += len(b)
    open(os.path.join(OUT, 'style.json'), 'w', encoding='utf-8').write(json.dumps(st, ensure_ascii=False, separators=(',', ':')))
    print('已刷新 site_src/map/：样式 %d 层（隐藏 %d）· 字形 %d KB · sprite 4 个' % (len(st['layers']), n_hide, tot // 1024))


def have():
    return all(os.path.exists(os.path.join(OUT, p)) for p in ('style.json', 'sprite/ofm.json', 'sprite/ofm@2x.png'))


def check_live():
    live = json.loads(get(STYLE_URL)); mine = json.load(open(os.path.join(OUT, 'style.json'), encoding='utf-8'))
    ids = {l['id']: l for l in mine['layers']}; bad = []; hit = 0
    for l in live['layers']:
        if HIDE_RE.search(l['id']):
            hit += 1
            m = ids.get(l['id'])
            if not m or m.get('layout', {}).get('visibility') != 'none': bad.append(l['id'])
    new = [l['id'] for l in live['layers'] if l['id'] not in ids]
    print('线上样式 %d 层，命中隐藏规则 %d 层；自托管样式里没隐藏 / 没有的：%s；线上新增的图层：%s' % (len(live['layers']), hit, bad or '无', new or '无'))
    return not bad and hit > 0


if __name__ == '__main__':
    if '--check' in sys.argv: sys.exit(0 if check_live() else 1)
    if '--refresh' in sys.argv or not have(): refresh()
    else: print('site_src/map/ 已齐（--refresh 重取）')
