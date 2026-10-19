#!/usr/bin/env python3
"""行程标题的两条会红的判据（2026-10-19，线路清理 D）：
  T1 标题不得以“N天(…)”开头（旧：52 条写成“5天(五天)，…”“4天(四)，…”“2天(两日)，…”，页头大字“5 天”紧跟其后，重复）
  T2 同一目的地下 label 不得重名（旧：18 组 37 条“深圳 2 天”“澳门 3 天”……，列表和搜索里分不出谁是谁）
用法：python3 tests/title_check.py            查 data/itineraries.json + data/catalog/trips.json
      python3 tests/title_check.py --selftest 反向自检：在内存里注入 3 种缺陷，各自必须红；没红 = 判据失效 = 退出码 1
data_checks.py 会调 check()。"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BAD_TITLE = re.compile(r'^\s*\d+\s*天\s*[(（]')


def check(itins, trips):
    bad = []
    for i in itins:
        for f in ('title', 'label'):
            if BAD_TITLE.match(i.get(f) or ''): bad.append(f'T1 {i["id"]} {f}「{i[f][:24]}」以“N天(…)”开头')
    for t in trips:
        for f in ('title', 'headline'):
            if BAD_TITLE.match(t.get(f) or ''): bad.append(f'T1 trips {t["id"]} {f}「{t[f][:24]}」以“N天(…)”开头')
    seen = {}
    for t in trips:
        if not re.match(r'Route\.dc\.html#', t.get('page') or ''): continue
        lab = re.sub(r'\s+', '', t.get('label') or t.get('title') or '')
        seen.setdefault((t.get('dest'), lab), []).append(t['id'])
    for (d, lab), ids in seen.items():
        if len(ids) > 1: bad.append(f'T2 目的地 {d} 下 label「{lab}」重名：{ids}')
    return bad


def load():
    I = json.load(open(os.path.join(ROOT, 'data', 'itineraries.json'), encoding='utf-8'))['itineraries']
    if isinstance(I, dict): I = [dict(v, id=k) for k, v in I.items()]
    T = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'trips.json'), encoding='utf-8'))['trips']
    return I, T


if __name__ == '__main__':
    I, T = load()
    if '--selftest' in sys.argv:
        import copy
        ok = True
        cases = {
            '标题“5天(五天)，…”': lambda i, t: i[0].update(title='5天(五天)，测试'),
            '标题“4天（四）…”（全角括号）': lambda i, t: i[1].update(title='4天（四），测试'),
            'label 重名': lambda i, t: [x.update(label='重名线路 2 天') for x in [y for y in t if re.match(r'Route\.dc\.html#', y.get('page') or '') and y['dest'] == t[0]['dest']][:2]],
        }
        for name, f in cases.items():
            i2, t2 = copy.deepcopy(I), copy.deepcopy(T)
            f(i2, t2); r = check(i2, t2)
            print(('PASS' if r else 'FAIL'), name, '→', (r[0][:60] if r else '没报错：判据失效'))
            ok = ok and bool(r)
        base = check(I, T); print(('PASS' if not base else 'FAIL'), '当前数据', '→', base[:2]); ok = ok and not base
        sys.exit(0 if ok else 1)
    bad = check(I, T)
    for b in bad[:30]: print('✗', b)
    print('标题检查', '通过' if not bad else f'{len(bad)} 处不过'); sys.exit(1 if bad else 0)
