#!/usr/bin/env python3
"""地图的反向自检总表（2026-10-18）：逐个注入缺陷，对应判据必须红；全部红才算闸是活的。

用法（项目根目录；先建好站）：
    python3 tests/map_inject_all.py build/site               # 跑全部（约 10–15 分钟）
    python3 tests/map_inject_all.py build/site --only coop_on,snap_off
每一行：注入名 → 跑哪一节判据 → 退出码（1 = 红 = 好）。有一个没红就退出码 1，并列出来。
注入只改送到浏览器的文件（见 map_app_check.py 的 INJ），磁盘上的站不动；注入点没生效（旧串找不到）也算红（map_app_check 自己会报 INJECT-NOT-APPLIED）。
sw_tiles_inf 另由 data_checks 第 33 项守（TILE_MAX ≤ 500）：这里改的是 sw.js，M12c 会红。
map_perf.py 自己的反向自检：python3 tests/map_perf.py --target fixture --site build/site --profiles 4g --modes cold --cases 4g:cold --inject slow_boot --assert
"""
import os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else 'build/site'
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
PLAN = [      # (注入名, 跑哪几节)
    ('coop_on', 'M2'), ('pinch_page', 'M2'), ('no_lock', 'M2'), ('rot_on', 'M2'), ('mk_auto', 'M2'),
    ('snap_off', 'M3'), ('half_tall', 'M3'), ('no_handoff', 'M3'),
    ('fly_off', 'M4'), ('row_back_off', 'M4'), ('card_swipe_off', 'M4'), ('blank_keeps', 'M4'),
    ('x_small', 'M5'), ('dock_show', 'M5'), ('col_full', 'M5'),
    ('retry_off', 'M6'), ('boot_blank', 'M6'),
    ('prefetch_saver', 'M7'), ('prefetch_slow', 'M7'), ('warm_off', 'M7'),
    ('cjk_net', 'M11'), ('border_on', 'M11'),
    ('sw_tiles_off', 'M12'), ('sw_tiles_inf', 'M12'),
    ('tap_radius', 'M13'), ('no_dense', 'M13'), ('no_merge', 'M13'), ('adj_small', 'M13'), ('nav_off_pg', 'M13'),
]
bad = []; n = 0
for name, sec in PLAN:
    if ONLY and name not in ONLY: continue
    n += 1
    r = subprocess.run([sys.executable, os.path.join(ROOT, 'tests', 'map_app_check.py'), SITE, '--inject', name, '--only', sec], cwd=ROOT, capture_output=True, text=True)
    red = r.returncode == 1
    tail = [l for l in r.stdout.splitlines() if l.startswith('✗')][:2]
    print('%-16s %-4s %s  %s' % (name, sec, '红（好）' if red else '没红（注入没被抓住！）', (' | '.join(t[:90] for t in tail)) if red else r.stdout.strip().splitlines()[-1][:100]), flush=True)
    if not red: bad.append(name)
print('\n共 %d 个注入，%d 个红，没红的：%s' % (n, n - len(bad), bad or '无'))
sys.exit(1 if bad else 0)
