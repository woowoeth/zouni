#!/usr/bin/env python3
"""首页专用小字体（2026-10-17）：从现有的 Google 字体切片（site_src/fonts/*.woff2，可变字重）里，只抠出
tools/home_font_chars.json 里的字（首页渲染的字），按字重做成静态实例，合成一个文件一个（族, 字重），
写 site_src/fonts/home-<名>.woff2 和 site_src/fonts/home.css。首页 <head> 里在 serif.css / sans.css 之后再链接 home.css：
后声明的 @font-face 在 unicode-range 重叠时优先，所以这些字走小文件，其余字仍走原切片（用到才下载）。

用法：  python3 tools/home_font_chars.py build/site   # 先收集字
        python3 tools/make_home_fonts.py               # 再生成（约 1 分钟，确定性）
首屏的 8 张卡每天不同，建议每月重跑一遍这两步；字不在小文件里的会自动退回原切片，只是多下几个。
"""
import json, os, re, sys
from fontTools.ttLib import TTFont
from fontTools import subset, merge
from fontTools.varLib import instancer

FD = 'site_src/fonts'
CH = json.load(open('tools/home_font_chars.json', encoding='utf-8'))
FAM = {'Noto Sans SC': ('sans.css', 'swap'), 'Noto Serif SC': ('serif.css', 'block')}


def slices(css):
    """slice 文件 -> (unicode-range 里的码点集合)"""
    out = {}
    for b in re.findall(r'@font-face\s*\{(.*?)\}', open(os.path.join(FD, css), encoding='utf-8').read(), re.S):
        u = re.search(r'url\(/assets/fonts/(\w+)\.woff2\)', b).group(1); r = re.search(r'unicode-range:\s*([^;]+);', b).group(1)
        out[u] = r
    return out


def ranges(cps):
    cps = sorted(cps); out = []; a = b = None
    for c in cps:
        if a is None: a = b = c
        elif c == b + 1: b = c
        else: out.append((a, b)); a = b = c
    if a is not None: out.append((a, b))
    return ', '.join('U+%x' % x if x == y else 'U+%x-%x' % (x, y) for x, y in out)


def build(fam, wt, chars):
    css, disp = FAM[fam]; need = set(ord(c) for c in chars); found = set(); parts = []
    for u in sorted(slices(css)):
        f = TTFont(os.path.join(FD, u + '.woff2')); cm = f.getBestCmap(); mine = sorted(c for c in need if c in cm and c not in found)
        if not mine: continue
        found.update(mine)
        if 'fvar' in f:
            ax = {a.axisTag: a for a in f['fvar'].axes}; w = max(ax['wght'].minValue, min(ax['wght'].maxValue, wt))
            f = instancer.instantiateVariableFont(f, {'wght': w}, inplace=False)
        opt = subset.Options(); opt.layout_features = ['kern', 'palt']; opt.notdef_outline = True; opt.name_IDs = [1, 2]; opt.drop_tables += ['DSIG', 'BASE', 'STAT', 'vhea', 'vmtx']
        sb = subset.Subsetter(opt); sb.populate(unicodes=mine); sb.subset(f); parts.append(f)
    if not parts: return None, set()
    if len(parts) == 1: m = parts[0]
    else: m = merge.Merger().merge([_save(p, i) for i, p in enumerate(parts)])
    name = 'home-%s%d' % ('serif' if 'Serif' in fam else 'sans', wt)
    out = os.path.join(FD, name + '.woff2'); m.flavor = 'woff2'; m.save(out)
    return name, found


def _save(font, i):
    import io
    b = io.BytesIO(); font.flavor = None; font.save(b); b.seek(0); return b


def main():
    blocks = []; tot = 0
    for key, chars in CH.items():
        fam, wt = key.split('|'); wt = int(wt)
        if fam == 'Noto Serif SC' and wt == 700 and len(chars) < 5: continue      # 极少用，走切片
        name, found = build(fam, wt, chars)
        if not name: continue
        sz = os.path.getsize(os.path.join(FD, name + '.woff2')); tot += sz
        miss = [c for c in chars if ord(c) not in found]
        blocks.append("@font-face {\n  font-family: '%s';\n  font-style: normal;\n  font-weight: %d;\n  font-display: %s;\n  src: url(/assets/fonts/%s.woff2) format('woff2');\n  unicode-range: %s;\n}\n" % (fam, wt, FAM[fam][1], name, ranges(found)))
        print(key, '字', len(found), '/', len(chars), '→', name + '.woff2', sz // 1024, 'KB', ('（切片里没有：%s）' % ''.join(miss)) if miss else '')
    open(os.path.join(FD, 'home.css'), 'w', encoding='utf-8').write(''.join(blocks))
    print('合计', tot // 1024, 'KB')


if __name__ == '__main__':
    main()
