#!/usr/bin/env python3
"""盘点：把每个弹层 / 选项 / 提示 / 控件的文字和字数列成表（2026-10-21「文字预算」）。

用法：python3 tests/copy_audit.py build/site_cp [--shots DIR] [--out build/cp_audit.md] [--before build/cp_audit_before.json]
  --before：表里的“现文”用改前存下的 json（改前那次盘点），“改后”读这一次现场取的字；不给就是单次盘点
输出 build/cp_audit.md（人看）和 build/cp_audit.json（copy_check 的前后对比、合计字数用）。
“建议 / 保留理由”两列来自 tests/copy_notes.json（手写：按 位置|现文 查）；没有的留空。
"""
import json, os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copy_common import *

env = Env({})
OUT = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else os.path.join(ROOT, 'build', 'cp_audit.md')
with sync_playwright() as p:
    rows = walk(env, p)
BEFORE = sys.argv[sys.argv.index('--before') + 1] if '--before' in sys.argv else None
after_rows = rows
if BEFORE: rows = json.load(open(BEFORE, encoding='utf-8'))
notes = {}
try: notes = json.load(open(os.path.join(ROOT, 'tests', 'copy_notes.json'), encoding='utf-8'))
except Exception: pass
js = OUT.rsplit('.', 1)[0] + '.json'
json.dump(after_rows, open(js.replace('.json', '_after.json') if BEFORE else js, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
tot = {'main': 0, 'sub': 0, 'n': 0}
L = ['# 文字盘点（390×844）', '', '| 位置 | 类别 | 现文 | 字数 | 副标题 | 字数 | 建议 / 保留理由 |', '|---|---|---|---|---|---|---|']
for r in rows:
    m, s = r.get('main', ''), r.get('sub', '')
    if r['kind'] in ('opt', 'note', 'toast', 'head'):
        tot['main'] += len(m); tot['sub'] += len(s); tot['n'] += 1
    nt = notes.get(r['where'] + '|' + m) or notes.get('*|' + m) or ''
    L.append('| %s | %s | %s | %d | %s | %d | %s |' % (r['where'], r['kind'], m.replace('|', '/'), len(m), s.replace('|', '/'), len(s), nt))
if BEFORE:
    L += ['', '固定文案总字数（弹层里的选项主标题 + 副标题 + 说明 + 标题，不含站名 / 日期格 / 候选）：改前 %d → 改后 %d' % (fixed_total(rows), fixed_total(after_rows))]
    def cnt(rs): return {'opt': sum(1 for r in rs if r['kind'] == 'opt' and r['sub']), 'note': sum(1 for r in rs if r['kind'] == 'note' and r['where'] in FIXED_WHERE)}
    L += ['带副标题的选项：改前 %d 个 → 改后 %d 个；弹层说明段：改前 %d 条 → 改后 %d 条' % (cnt(rows)['opt'], cnt(after_rows)['opt'], cnt(rows)['note'], cnt(after_rows)['note'])]
L += ['', '合计（弹层选项 / 说明 / 提示 / 标题 %d 条）：主文字 %d 字，副标题 %d 字' % (tot['n'], tot['main'], tot['sub'])]
open(OUT, 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('写入', OUT, '共', len(rows), '条；', tot)
env.finish('盘点') if env.fails else None
