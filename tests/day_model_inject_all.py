#!/usr/bin/env python3
"""day_model_check.py 的反向注入一次跑完（每种注入只跑它该红的那一组，必须退出码 1；全红 = 判据没有哑掉）。

用法：python3 tests/day_model_inject_all.py build/site [名字,名字…]
输出每种注入：红了几条、哪一条先红；最后汇总“全红 / 哪几个没红或没生效”。退出码：全红 0，有没红的 1。
（注入只改送到浏览器的 site.js / routemap.js，磁盘上的站不动。）
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = sys.argv[1] if len(sys.argv) > 1 else 'build/site'
PLAN = [      # (注入名, 只跑的组)
    ('bar_list', 'D1'), ('model_other', 'D1'), ('bar_nosync', 'D2'),
    ('num_bar', 'D1'), ('num_sum', 'D3'), ('num_glance', 'D3'), ('num_end', 'D3'),
    ('see_noop', 'D4'), ('see_noscroll', 'D4'), ('see_nohi', 'D4'), ('card_taller', 'D4'), ('swipe_off', 'D4'),
    ('tv_other', 'D7'), ('copy_other', 'D7'), ('ics_other', 'D7'), ('zid_unstable', 'D10'),
]
want = set(sys.argv[2].split(',')) if len(sys.argv) > 2 else None
miss = []
for name, only in PLAN:
    if want and name not in want: continue
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'day_model_check.py'), SITE, '--inject', name, '--only', only], capture_output=True, text=True, cwd=ROOT)
    out = r.stdout + r.stderr
    reds = [l for l in out.splitlines() if l.startswith('✗')]
    na = 'INJECT-NOT-APPLIED' in out
    ok = r.returncode == 1 and reds and not na
    print('%-16s %s  红 %d 条%s  首条：%s' % (name, '✓ 红了' if ok else '✗ 没红!', len(reds), '（含 INJECT-NOT-APPLIED！）' if na else '', (reds[0][:100] if reds else '')), flush=True)
    if not ok: miss.append(name)
print('\n反向注入 %d 种：%s' % (len([1 for n, _ in PLAN if not want or n in want]), '全红' if not miss else '没红 / 没生效：' + ' '.join(miss)))
sys.exit(1 if miss else 0)
