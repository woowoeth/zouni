#!/usr/bin/env python3
"""路线地图的自托管底图资源（2026-10-18）：把 OpenFreeMap 的 liberty 样式、sprite、常用西文字形取一份放进 site_src/map/，建站时原样拷到 assets/map/。

为什么：以前每次点开地图都要先到 tiles.openfreemap.org 取样式（43KB）→ 再取 sprite → 再取字形，串成一条链，慢网下占了一大半时间；
自托管以后它们和 routemap.js 一样走本站（GitHub Pages / Service Worker），运行时不再改图层（隐藏边界、标注改中文的修改在这里一次做完）。

用法：
    python3 tools/map_assets.py            # site_src/map/ 已齐就什么都不做（建站每次调用，不联网）
    python3 tools/map_assets.py --refresh  # 重新从 OpenFreeMap 取（样式换版本、边界图层 id 变了时；之后重跑 tests/data_checks.py 的第 33 项和 route_map_check --live）
    python3 tools/map_assets.py --requiet  # 不联网：给现有样式套“底图退后”（隐藏盾牌 / 村名、标注压小压淡）
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
ZH_TEXT = ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh'], ['get', 'name:ja'], ['get', 'name:latin'], ['get', 'name']]      # 中文优先 → 日文（汉字，中国人读得懂）→ 拉丁字母（泰文 / 阿拉伯文 / 韩文 / 西里尔字母的地名中国人读不了，不如拉丁字母）→ 本地名（2026-10-20）
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


# 底图退后（2026-10-19，用户：底图太吵、抢站点）：杂志风是“底图退后、线路和站点在前”。
# 规则：道路盾牌（G3021 之类）和村 / 乡镇一级的名字不要；区名 / 路名 / POI 字号压小、颜色换成纸色底上的浅灰（halo 用纸色）；竖排路名保留但更淡。
# 站点方块和站名标签是页面上的 DOM，永远叠在底图（canvas）之上，不靠样式保证。门禁：data_checks 第 33 项 + tests/map_polish_check.py（数的是样式文件本身）
QUIET = {
    'text': '#8f8b80', 'halo': 'rgba(244,242,236,0.92)', 'road_text': '#a39f94',
    'hide': re.compile(r'shield|label_village'),      # 道路盾牌、村名整层不要
    'cap': {'label_town': 11, 'label_other': 10, 'label_city': 14, 'label_city_capital': 15, 'highway-name-major': 11, 'highway-name-minor': 10.5, 'highway-name-path': 10, 'poi_r1': 10, 'poi_r7': 10, 'poi_r20': 10, 'poi_transit': 10, 'airport': 10, 'water_name_point_label': 10, 'water_name_line_label': 10, 'waterway_line_label': 10},      # 每层字号上限（px）
    'minz': {'label_town': 9, 'label_other': 13, 'poi_r20': 17, 'poi_r7': 16.5, 'poi_r1': 16},      # 低等级的名字放大到更近才出现
}


def _cap_size(ts, cap):
    """text-size 可能是数字，也可能是 interpolate 表达式：把每个输出值压到 cap 以内（不放大）"""
    if isinstance(ts, (int, float)): return min(ts, cap)
    if isinstance(ts, list) and ts and ts[0] == 'interpolate':
        out = list(ts)
        for i in range(4, len(out), 2):
            if isinstance(out[i], (int, float)): out[i] = min(out[i], cap)
        return out
    return ts


def quiet(st):
    """把样式里的标注压低；重复调用无副作用（metadata.zouni_quiet 记号）。返回 (样式, 改的图层数)"""
    st.setdefault('metadata', {})
    n = 0
    for l in st['layers']:
        lay = l.setdefault('layout', {}); pt = l.setdefault('paint', {})
        if QUIET['hide'].search(l['id']):
            lay['visibility'] = 'none'; n += 1; continue
        if l.get('type') != 'symbol' or not lay.get('text-field'): continue
        cap = QUIET['cap'].get(l['id'])
        if cap is not None and 'text-size' in lay: lay['text-size'] = _cap_size(lay['text-size'], cap)
        mz = QUIET['minz'].get(l['id'])
        if mz is not None: l['minzoom'] = max(l.get('minzoom', 0), mz)
        pt['text-color'] = QUIET['road_text'] if l['id'].startswith('highway-name') else QUIET['text']
        pt['text-halo-color'] = QUIET['halo']; pt['text-halo-width'] = 1.2; pt['text-halo-blur'] = 0
        if l.get('type') == 'symbol' and lay.get('icon-image'): pt['icon-opacity'] = 0.55
        n += 1
    st['metadata']['zouni_quiet'] = 1
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
    st, n_hide = tune(st); st, _nq = quiet(st)
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


def relang(st):
    """把已经生成的样式里“中文优先”的 text-field 换成现在的 ZH_TEXT（不联网；重复调用无副作用）。返回 (样式, 改的图层数)"""
    old = ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh'], ['get', 'name']]; n = 0
    for l in st['layers']:
        tf = l.get('layout', {}).get('text-field')
        if tf == old or (isinstance(tf, list) and tf[:3] == ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh']] and tf != ZH_TEXT): l['layout']['text-field'] = ZH_TEXT; n += 1
    return st, n


if __name__ == '__main__':
    if '--relang' in sys.argv:
        f = os.path.join(OUT, 'style.json'); st = json.load(open(f, encoding='utf-8')); st, n = relang(st)
        open(f, 'w', encoding='utf-8').write(json.dumps(st, ensure_ascii=False, separators=(',', ':'))); print('已改 %d 个图层的地名语言' % n); sys.exit(0)
    if '--check' in sys.argv: sys.exit(0 if check_live() else 1)
    if '--requiet' in sys.argv:      # 不联网：对现有 site_src/map/style.json 套一遍“底图退后”（已经套过就什么也不做）
        f = os.path.join(OUT, 'style.json'); st = json.load(open(f, encoding='utf-8'))
        if st.get('metadata', {}).get('zouni_quiet'): print('已经是退后版')
        else: st, n = quiet(st); open(f, 'w', encoding='utf-8').write(json.dumps(st, ensure_ascii=False, separators=(',', ':'))); print('已压低 %d 个图层' % n)
        sys.exit(0)
    if '--refresh' in sys.argv or not have(): refresh()
    else: print('site_src/map/ 已齐（--refresh 重取）')
