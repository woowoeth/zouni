#!/usr/bin/env python3
"""Python 与 JS 的「车程 / 绕路 / 排序 / 预算 / 取片」逐位一致性闸。

    python3 tests/nearby_parity.py                 # 默认：每种出行方式随机 500 对坐标
    python3 tests/nearby_parity.py --seed 7 --n 500
    python3 tests/nearby_parity.py --js /path/to/np_model.js     # 测另一份 JS（反向验证用：临时改一个常数的副本）

三方对比：
  A  tools/compile_itineraries.py 里真正的 leg()（用 ast 把源码抽出来 exec，不 import：那个文件一 import 就开始编译）
  B  tools/nearby_model.py（Python 模型）
  C  site_src/np_model.js（node 跑）
判据：每个 (坐标对 × 出行方式) 的 (怎么走, 分钟, 公里) 完全相等，分钟差必须为 0；
      绕路、预算、排序、开放时间、同处、取片格也要逐项相等（分数允许 1e-9 的浮点误差）。
退出码 1 = 有差异。node 不存在时退出码 2（不是绿）。
"""
import argparse
import ast
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import nearby_model as M   # noqa: E402

NODE_RUNNER = r"""
var fs = require('fs');
var m = require(process.argv[1]);
var cases = JSON.parse(fs.readFileSync(0, 'utf8'));
var out = {};
out.leg = cases.leg.map(function (c) { var r = m.leg(c.a, c.b, c.mode); return [r[0], r[1], r[2], (c.a && c.b) ? m.km(c.a, c.b) : 0]; });
out.r5 = cases.r5.map(function (x) { return m.r5(x); });
out.insert = cases.insert.map(function (c) { return m.detourInsert(c.A, c.B, c.X, c.t0, c.mode); });
out.replace = cases.replace.map(function (c) { return [m.detourReplace(c.A, c.S, c.C, c.X, c.t0a, c.t0b, c.mode), m.replaceNear(c.S, c.X, c.mode)]; });
out.budget = cases.budget.map(function (c) { return m.dayBudgetOk(c.rows, c.ins); });
out.rank = cases.rank.map(function (c) { return m.rank(c.items, c.limit).map(function (x) { return [x.id, x.score]; }); });
out.hours = cases.hours.map(function (c) { return [m.parseHours(c.h), m.hoursOk(c.arr, c.dur, c.h)]; });
out.same = cases.same.map(function (c) { return [m.sameSpot(c.p, c.refs), m.inReach(c.p, c.refs)]; });
out.shards = cases.shards.map(function (b) { return m.shardsFor(b); });
out.cellkey = cases.cellkey.map(function (p) { return m.cellKey(p[0], p[1]); });
out.mode = cases.mode.map(function (c) { return m.modeOfDay(c[0], c[1], c[2]); });
out.kind = cases.kind.map(function (c) { return m.sameKind(c[0], c[1], c[2], c[3], c[4]); });
out.consts = m.C;
out.big = m.BIG_CITIES;
process.stdout.write(JSON.stringify(out));
"""


def compile_leg_namespace():
    """从 tools/compile_itineraries.py 抽出真正的 km / r5 / leg / BIG_CITIES，放进一个干净的命名空间"""
    src = open(os.path.join(ROOT, 'tools', 'compile_itineraries.py'), encoding='utf-8').read()
    keep = []
    for n in ast.parse(src).body:
        if isinstance(n, ast.FunctionDef) and n.name in ('km', 'r5', 'leg'):
            keep.append(n)
        elif isinstance(n, ast.Assign) and any(getattr(t, 'id', None) in ('BIG_CITIES', 'SELF', 'RURAL', 'SELFV') for t in n.targets):
            keep.append(n)
    ns = {'math': math, 're': re}
    exec(compile(ast.Module(body=keep, type_ignores=[]), 'compile_itineraries(extract)', 'exec'), ns)
    return ns


def rnd_pt(rng):
    return [round(rng.uniform(-50, 62), 6), round(rng.uniform(-179, 179), 6)]


def rnd_near(rng, a):
    """离 a 一个对数均匀分布的距离（0.05–600 公里）"""
    d = math.exp(rng.uniform(math.log(0.05), math.log(600)))
    ang = rng.uniform(0, 2 * math.pi)
    lat = a[0] + d * math.cos(ang) / 111.0
    lng = a[1] + d * math.sin(ang) / (111.0 * max(0.2, math.cos(a[0] * math.pi / 180)))
    return [round(max(-89, min(89, lat)), 6), round(lng, 6)]


def make_cases(rng, n):
    C = {'leg': [], 'r5': [], 'insert': [], 'replace': [], 'budget': [], 'rank': [], 'hours': [], 'same': [], 'shards': [], 'cellkey': [], 'mode': [], 'kind': []}
    for mode in M.MODES:
        for _ in range(n):
            a = rnd_pt(rng)
            C['leg'].append({'a': a, 'b': rnd_near(rng, a), 'mode': mode})
    C['leg'].append({'a': [34.2, 108.9], 'b': [34.2, 108.9], 'mode': 'city'})   # 同一点
    C['leg'].append({'a': None, 'b': [1, 1], 'mode': 'drive'})                  # 缺坐标
    C['r5'] = [2.5, 12.5, 17.5, 7.5, 22.5, 0.5, 1.5, 2.4999, 2.5001, 99.5, 100.5, 35.0, 37.5] + [rng.uniform(0, 400) for _ in range(300)]
    for _ in range(n):
        mode = rng.choice(M.MODES)
        A = rnd_pt(rng); B = rnd_near(rng, A); X = rnd_near(rng, A); S = rnd_near(rng, A)
        t0 = rng.choice([None, None, rng.randint(5, 240)])
        C['insert'].append({'A': A, 'B': rng.choice([B, B, None]), 'X': X, 't0': t0, 'mode': mode})
        C['replace'].append({'A': rng.choice([A, A, None]), 'S': S, 'C': rng.choice([B, B, None]), 'X': X, 't0a': rng.choice([None, rng.randint(5, 240)]), 't0b': rng.choice([None, rng.randint(5, 240)]), 'mode': mode})
    for _ in range(n):
        rows = []
        t = rng.randint(6 * 60, 12 * 60)
        for _ in range(rng.randint(1, 8)):
            k = rng.choice(['see', 'fun', 'eat', 'dep', 'stay'])
            e = t + rng.randint(5, 200)
            rows.append({'s': t, 'e': rng.choice([e, e, None]), 'k': k})
            t = e + rng.randint(0, 40)
        C['budget'].append({'rows': rows, 'ins': rng.random() < 0.5})
    for _ in range(80):
        items = [{'id': 'c%03d' % rng.randint(0, 40), 'delta': rng.choice([0.0, 5.0, 12.5, 20.0, 29.9, 31.0, rng.uniform(0, 60)]), 'has_s': rng.random() < 0.7,
                  'pop': rng.randint(0, 30), 'same': rng.random() < 0.3, 'f': rng.choice([None, 1.0, 1.5, 2.0, 0.9]), 'approx': rng.random() < 0.6} for _ in range(rng.randint(1, 12))]
        C['rank'].append({'items': items, 'limit': rng.choice([5, 5, 3, 12])})
    for h in ['8:30–17:00（冬季到 16:30）', '9:00-17:00', '8:00–22:00', '', '全天开放', '旺季 8:00–18:00', '9:00 至 16:30', '0:00—24:00', '8:30–17:00 停止入场']:
        for arr in (480, 600, 960, 990, 1020, 1100):
            C['hours'].append({'h': h, 'arr': arr, 'dur': rng.choice([30, 60, 120])})
    for _ in range(n):
        p = rnd_pt(rng)
        refs = [rnd_near(rng, p) if rng.random() < 0.9 else None for _ in range(rng.randint(0, 4))]
        refs = [r for r in refs if r is not None] + ([None] if rng.random() < 0.2 else [])
        C['same'].append({'p': p, 'refs': refs})
    # 近距离的“同处”边界
    for d_m in (100, 240, 249, 251, 400, 590, 610):
        p = [34.2, 108.9]; q = [34.2 + d_m / 111000.0, 108.9]
        C['same'].append({'p': p, 'refs': [q]})
    for _ in range(80):
        a = rnd_pt(rng); b = rnd_near(rng, a)
        C['shards'].append([min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])])
    C['shards'] += [[34.2, 108.9, 34.2, 108.9], [32.65, 110.35, 32.65, 110.35], [-33.9, 151.2, -33.9, 151.2], [0.1, -0.1, 0.1, -0.1]]
    for _ in range(n):
        C['cellkey'].append(rnd_pt(rng))
    C['cellkey'] += [[0, 0], [-90, -180], [-0.0001, -0.0001], [33.0, 108.0], [32.9999, 107.9999]]
    for d in (True, False):
        for dom in (True, False):
            for c in ('西安', '敦煌', '东京', '', '拉萨', '库车'):
                C['mode'].append([d, dom, c])
    words = ['大慈恩寺', '陕西历史博物馆', '小雁塔', '兴庆宫公园', '西湖', '河坊街', '灵隐寺', '岳麓山', '大唐不夜城']
    for _ in range(120):
        C['kind'].append([rng.choice(['sg', 'pk', 'ms', 'st']), rng.choice(words), rng.choice(['sg', 'pk', 'ms', 'st']), rng.choice(words), rng.choice(['', '博物馆 · 寺', '古塔 · 老街', '湖'])])
    return C


def close(a, b, tol=1e-9):
    return a == b or (a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=500)
    ap.add_argument('--seed', type=int, default=None)
    ap.add_argument('--js', default=os.path.join(ROOT, 'site_src', 'np_model.js'))
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.SystemRandom().randint(1, 10 ** 9)
    rng = random.Random(seed)
    node = shutil.which('node')
    if not node:
        print('没有 node：无法比对 JS（退出码 2，不算绿）')
        return 2
    cases = make_cases(rng, a.n)
    p = subprocess.run([node, '-e', NODE_RUNNER, os.path.abspath(a.js)], input=json.dumps(cases), capture_output=True, text=True)
    if p.returncode:
        print('node 运行失败：', p.stderr[-800:])
        return 1
    J = json.loads(p.stdout)
    ns = compile_leg_namespace()
    bad = []
    mismatch_min = 0

    # 常量
    py_consts = {'ROUTE_FACTOR': M.ROUTE_FACTOR, 'WALK_KM': M.WALK_KM, 'DETOUR_MAX': M.DETOUR_MAX, 'REPLACE_NEAR_MAX': M.REPLACE_NEAR_MAX, 'F_MIN': M.F_MIN, 'F_MAX': M.F_MAX,
                 'SHOW_STEP': M.SHOW_STEP, 'MAX_NONMEAL': M.MAX_NONMEAL, 'END_LIMIT': M.END_LIMIT, 'SPAN_LIMIT': M.SPAN_LIMIT, 'SAME_SPOT_KM': M.SAME_SPOT_KM, 'BESIDE_KM': M.BESIDE_KM,
                 'REACH_KM': M.REACH_KM, 'LIST_MAX': M.LIST_MAX, 'BBOX_PAD': M.BBOX_PAD, 'GRID': M.GRID, 'W_HAS_SENTENCE': M.W_HAS_SENTENCE, 'W_POP_CAP': M.W_POP_CAP, 'W_POP_K': M.W_POP_K,
                 'W_SAME_KIND': M.W_SAME_KIND, 'F_SLOW': M.F_SLOW, 'W_SLOW': M.W_SLOW, 'W_APPROX': M.W_APPROX, 'APPROX_DELTA': M.APPROX_DELTA}
    for k, v in py_consts.items():
        if J['consts'].get(k) != v:
            bad.append('常量 %s：Python %r ≠ JS %r' % (k, v, J['consts'].get(k)))
    if sorted(J['big']) != sorted(M.BIG_CITIES):
        bad.append('BIG_CITIES：JS 与 Python 不同')
    if sorted(ns['BIG_CITIES']) != sorted(M.BIG_CITIES):
        bad.append('BIG_CITIES：nearby_model 与 compile_itineraries 不同')
    # 硬性写死的阈值（用户 2026-10-16 拍板）：任何一边被悄悄改了都红
    for name, want in (('DETOUR_MAX', 30), ('MAX_NONMEAL', 5), ('END_LIMIT', 21 * 60 + 30), ('SPAN_LIMIT', 13 * 60)):
        if getattr(M, name) != want or J['consts'].get(name) != want:
            bad.append('拍板的阈值 %s 应为 %s，现在 Python=%r JS=%r' % (name, want, getattr(M, name), J['consts'].get(name)))

    # 车程：compile_itineraries.leg ↔ Python ↔ JS
    nleg = 0
    for c, jr in zip(cases['leg'], J['leg']):
        mode = c['mode']
        ns['SELF'][0] = (mode == 'drive'); ns['RURAL'][0] = (mode == 'rural'); ns['SELFV'][0] = False
        a_ = ns['leg'](c['a'], c['b'], None) if c['a'] and c['b'] else ('打车', 20, None)
        b_ = M.leg(c['a'], c['b'], mode)
        j_ = (jr[0], jr[1], jr[2])
        nleg += 1
        if tuple(a_) != tuple(b_):
            bad.append('compile.leg ≠ nearby_model.leg %s %s: %r vs %r' % (mode, c, a_, b_))
        if tuple(b_) != j_:
            mismatch_min = max(mismatch_min, abs(b_[1] - j_[1]))
            bad.append('Python ≠ JS leg %s %s: %r vs %r' % (mode, c, b_, j_))
        if c['a'] and c['b'] and abs(M.km(c['a'], c['b']) - jr[3]) > 1e-9 * max(1, jr[3]):
            bad.append('km 浮点差 %s' % c)
    for x, jr in zip(cases['r5'], J['r5']):
        if M.r5(x) != jr:
            bad.append('r5(%r)：Python %r ≠ JS %r（银行家舍入）' % (x, M.r5(x), jr))
    for c, jr in zip(cases['insert'], J['insert']):
        py = M.detour_insert(c['A'], c['B'], c['X'], c['t0'], c['mode'])
        if not close(py, jr, 0):
            bad.append('detour_insert %r：Python %r ≠ JS %r' % (c, py, jr))
    for c, jr in zip(cases['replace'], J['replace']):
        py = M.detour_replace(c['A'], c['S'], c['C'], c['X'], c['t0a'], c['t0b'], c['mode'])
        pn = M.replace_near(c['S'], c['X'], c['mode'])
        if not close(py, jr[0], 0) or pn != jr[1]:
            bad.append('detour_replace %r：Python %r/%r ≠ JS %r' % (c, py, pn, jr))
    for c, jr in zip(cases['budget'], J['budget']):
        py = M.day_budget_ok(c['rows'], c['ins'])
        if py != jr:
            bad.append('day_budget_ok %r：Python %r ≠ JS %r' % (c, py, jr))
    for c, jr in zip(cases['rank'], J['rank']):
        py = [[x['id'], x['score']] for x in M.rank(c['items'], c['limit'])]
        if [x[0] for x in py] != [x[0] for x in jr] or any(not close(x[1], y[1]) for x, y in zip(py, jr)):
            bad.append('rank：Python %r ≠ JS %r' % (py, jr))
    for c, jr in zip(cases['hours'], J['hours']):
        pp = M.parse_hours(c['h'])
        py = [list(pp) if pp else None, M.hours_ok(c['arr'], c['dur'], c['h'])]
        if py != jr:
            bad.append('hours %r：Python %r ≠ JS %r' % (c, py, jr))
    for c, jr in zip(cases['same'], J['same']):
        py = [M.same_spot(c['p'], c['refs']), M.in_reach(c['p'], c['refs'])]
        if py != jr:
            bad.append('same_spot/in_reach %r：Python %r ≠ JS %r' % (c, py, jr))
    for b, jr in zip(cases['shards'], J['shards']):
        if M.shards_for(b) != jr:
            bad.append('shards_for %r：Python %r ≠ JS %r' % (b, M.shards_for(b), jr))
    for pt, jr in zip(cases['cellkey'], J['cellkey']):
        if M.cell_key(pt[0], pt[1]) != jr:
            bad.append('cell_key %r：Python %r ≠ JS %r' % (pt, M.cell_key(pt[0], pt[1]), jr))
    for c, jr in zip(cases['mode'], J['mode']):
        if M.mode_of_day(c[0], c[1], c[2]) != jr:
            bad.append('mode_of_day %r' % (c,))
    for c, jr in zip(cases['kind'], J['kind']):
        if M.same_kind(c[0], c[1], c[2], c[3], c[4]) != jr:
            bad.append('same_kind %r' % (c,))

    print('seed=%d  JS=%s' % (seed, os.path.relpath(a.js, ROOT) if a.js.startswith(ROOT) else a.js))
    print('车程：%d 对（%d 对坐标 × %s）三方比对（compile_itineraries.leg ↔ nearby_model.py ↔ np_model.js）' % (nleg, a.n, '/'.join(M.MODES)))
    print('绕路 %d 组（插入）+ %d 组（替换）· 预算 %d · 排序 %d · 开放时间 %d · 同处/范围 %d · 取片 %d · 格键 %d · 模式 %d · 同类 %d' % (
        len(cases['insert']), len(cases['replace']), len(cases['budget']), len(cases['rank']), len(cases['hours']), len(cases['same']), len(cases['shards']), len(cases['cellkey']), len(cases['mode']), len(cases['kind'])))
    if bad:
        print('不一致 %d 处（分钟最大差 %d）。前 8 条：' % (len(bad), mismatch_min))
        for b in bad[:8]:
            print('  -', b[:300])
        return 1
    print('全部一致：分钟差 0，不一致 0')
    return 0


if __name__ == '__main__':
    sys.exit(main())
