#!/usr/bin/env python3
"""detail_simplify_check.py 的反向注入一次跑完（每种注入只跑它该红的那几组，必须退出码 1；全红 = 判据没有哑掉）。

用法：python3 tests/detail_simplify_inject_all.py build/site [名字,名字…]
输出每种注入：红了几条、哪一条先红；最后汇总“全红 / 哪几个没红”。退出码：全红 0，有没红的 1。
（注入只改送到浏览器的 site.js / site.css / 页面 HTML，磁盘上的站不动；复原 = 不加 --inject 再跑一遍全套，见 04 号文档。）
"""
import os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = sys.argv[1] if len(sys.argv) > 1 else 'build/site'
PLAN = [      # (注入名, 只跑的组, 只测的层)
    ('xb_back', 'S1', '分享'), ('x_small', 'S1', '分享'), ('confirm_back', 'S1', '分享'),
    ('no_stack', 'S3', None), ('cl_unlock', 'S3', None), ('back_shot', 'S2', '分享图（存图层）'),
    ('swipe_off', 'S4', None), ('swipe_steal', 'S4', None),
    ('pre_boxes', 'S5', None), ('date_dup', 'S5', None), ('kick_days', 'S5', None),
    ('cl_every_day', 'S8', None), ('facts_road', 'S8', None), ('label_old', 'S8', None),
    ('dock_nolink', 'S10', None), ('ics_gone', 'S10', None), ('stay_nojump', 'S10', None),
    ('copy_noarea', 'SX', None), ('gray_old', 'S11', None), ('ret_gone', 'S12', None), ('foot_wrap', 'S13', None),
]
want = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
miss = []
for name, only, layers in PLAN:
    if want and name not in want: continue
    cmd = [sys.executable, os.path.join(ROOT, 'tests', 'detail_simplify_check.py'), SITE, '--inject', name, '--only', only] + (['--layers', layers] if layers else [])
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    reds = [l for l in out.splitlines() if l.startswith('✗')]
    na = 'INJECT-NOT-APPLIED' in out
    ok = r.returncode == 1 and reds
    print('%-14s %s  红 %d 条%s  首条：%s' % (name, '✓ 红了' if ok else '✗ 没红!', len(reds), '（含 INJECT-NOT-APPLIED！）' if na else '', (reds[0][:110] if reds else '')), flush=True)
    if not ok or na: miss.append(name)
print('\n反向注入 %d 种：%s' % (len([1 for n, _, _ in PLAN if not want or n in want]), '全红' if not miss else '没红 / 没生效：' + ' '.join(miss)))
sys.exit(1 if miss else 0)
