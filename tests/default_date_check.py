#!/usr/bin/env python3
"""全站线路页的默认出发日期规则一致（2026-10-18，历史爱好者发现：东坡线建议 2027 年 11/9，蜀中李白、长征默认 10/24、10/25，而东坡线最佳季节 10/25–12/5 现在就能去）。会红。纯静态。

用法（项目根目录；先 bash build/pipe.sh build/site，建站当天跑）：
    python3 tests/default_date_check.py build/site
    python3 tests/default_date_check.py build/site --inject year_jump|late_window    # 反向自检：改的是测试读到的 data-start，必须变红

规则（tools/build_site.py::start_date 的注释）：先取 start 的月日在今天之后最近的一次；今天在“最好的日子”窗口里 → 下一个周六、不出窗口；窗口 30 天内就开 → 窗口里的第一个周六；其余 → 最近的一次；之后避开周一闭馆和假日高峰（所以会有几天偏差）
D1  所有页的默认日期 ≥ 明天、不晚于 14 个月后（不会无故跳到明年以后）
D2  今天正落在窗口里的线路：默认日期在窗口内，且在 2 到 16 天之内（≈ 下一个周六，避开周一 / 假日偏几天）
D3  窗口 30 天内就开的线路：默认日期在窗口里，且在窗口开始后 10 天之内（窗口里第一个周六附近）
D4  同一个季节的几条线（东坡 / 李白 / 长征：窗口都含今天或快开）默认日期互相差 ≤ 14 天
"""
import datetime, glob, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = sys.argv[1:]
SITE = os.path.abspath(A[0]) if A and not A[0].startswith('--') else os.path.join(ROOT, 'build', 'site')
INJ = A[A.index('--inject') + 1] if '--inject' in A else None
if INJ and INJ not in ('year_jump', 'late_window'): sys.exit('--inject 只认 year_jump / late_window')
T = datetime.date.today()
import json
_T = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'trips.json'), encoding='utf-8'))
ANY = {t['id'] for t in (_T if isinstance(_T, list) else _T.get('trips', _T)) if isinstance(t, dict) and t.get('anytime')}      # 数据里标了“一年四季都能去”的线不按窗口算（km2、mgs2 同时写了窗口，是数据里的矛盾）
oks, fails = [], []
def check(name, cond, detail=''): (oks if cond else fails).append(name + ('  → ' + str(detail)[:400] if not cond and detail != '' else ''))
rows = {}
for p in glob.glob(os.path.join(SITE, 'trip', '*', 'index.html')):
    rid = os.path.basename(os.path.dirname(p)); h = open(p, encoding='utf-8').read()
    m = re.search(r'data-start="([\d-]+)"', h); b = re.search(r'data-best="([^"]*)"', h)
    if not m: continue
    rows[rid] = (datetime.date.fromisoformat(m.group(1)), b.group(1).split(',') if b and b.group(1) else None)
if INJ == 'year_jump' and 'hss1a' in rows: rows['hss1a'] = (rows['hss1a'][0].replace(year=rows['hss1a'][0].year + 1), rows['hss1a'][1])
if INJ == 'late_window' and 'hlia' in rows: rows['hlia'] = (rows['hlia'][0] + datetime.timedelta(days=60), rows['hlia'][1])


def window(b):
    """今天所在 / 之后最近的一个窗口 (开始, 结束, 是否含今天)"""
    a, e = b; md0 = T.strftime('%m-%d'); wrap = a > e
    inside = (md0 >= a or md0 <= e) if wrap else (a <= md0 <= e)
    if inside:
        end = datetime.date(T.year + (1 if wrap and md0 >= a else 0), int(e[:2]), int(e[3:]))
        return T, end, True
    lo = datetime.date(T.year, int(a[:2]), int(a[3:]))
    if lo < T: lo = datetime.date(T.year + 1, int(a[:2]), int(a[3:]))
    return lo, datetime.date(lo.year + (1 if wrap else 0), int(e[:2]), int(e[3:])), False


bad1 = [(r, d.isoformat()) for r, (d, b) in rows.items() if d <= T or d > T + datetime.timedelta(days=430)]
check('D1 %d 个线路页：默认出发日 ≥ 明天、不晚于 14 个月后' % len(rows), len(rows) > 1000 and not bad1, bad1[:4])
bad2, bad3, n2, n3, near = [], [], 0, 0, {}
for r, (d, b) in rows.items():
    if not b or r in ANY or b[0] == '01-01' and b[1] == '12-31': continue
    lo, hi, inside = window(b)
    if inside and (hi - T).days >= 3:
        n2 += 1
        if not (lo <= d <= hi and 2 <= (d - T).days <= 16): bad2.append((r, d.isoformat(), '窗口到 %s' % hi.isoformat()))
        near[r] = d
    elif not inside and 0 < (lo - T).days <= 30 and (hi - lo).days >= 7:
        n3 += 1
        if not (lo <= d <= hi and (d - lo).days <= 10): bad3.append((r, d.isoformat(), '窗口 %s–%s' % (lo.isoformat(), hi.isoformat())))
        near[r] = d
check('D2 今天正落在窗口里的 %d 条线：默认日期在窗口内、2–16 天后（下一个周六，避开周一 / 假日）' % n2, n2 >= 20 and not bad2, bad2[:5])
check('D3 窗口 30 天内就开的 %d 条线：默认日期在窗口里、窗口开始后 10 天之内' % n3, n3 >= 3 and not bad3, bad3[:5])
seas = {r: near[r] for r in ('hss1a', 'hlia', 'hcz1', 'hss2a', 'hkx2', 'hlib') if r in near}
spread = (max(seas.values()) - min(seas.values())).days if seas else 99
check('D4 同一个季节的几条线（%s）默认日期互相差 %d 天（≤14）' % (', '.join('%s %s' % (r, d.strftime('%m/%d')) for r, d in sorted(seas.items())), spread), len(seas) >= 3 and spread <= 14, seas)
for x in oks: print('✓', x)
for x in fails: print('✗', x)
print('\n默认出发日期：%d 过 · %d 红%s' % (len(oks), len(fails), '（--inject %s）' % INJ if INJ else ''))
sys.exit(1 if fails else 0)
