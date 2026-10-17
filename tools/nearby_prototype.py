#!/usr/bin/env python3
"""「顺路加一站 / 换一站」候选原型：用 build/np/pool.json（先跑 tools/build_nearby_pool.py）和 data/itineraries.json（不依赖 build/routes.js：它会被别的流水线反复重建），
对 5 条线路各 3 个站点算“在它后面加”和“换成”的候选，再算全站“空状态占比”。

    python3 tools/nearby_prototype.py                         # 5 条线路样例 + 空状态占比
    python3 tools/nearby_prototype.py --route xa3 --day 3     # 指定线路（和天）
    python3 tools/nearby_prototype.py --stats-only

模型全部来自 tools/nearby_model.py（和页面里的 site_src/np_model.js 同一套）。
原型的当天时间表是估算：按 compile_itineraries 的车程规则（作者写的 via 优先，否则 leg()）、站点 dur、午饭 60 分钟排一遍；
插入后把后面的行整体后推 Δ + 新站停留，再交给 day_budget_ok 判；
页面里用 replan 的真试算，不用估算（设计 §3.2）。候选列表的每一项都带上算它用的输入点，tests/nearby_pool_check.py 据此独立复算。
"""
import argparse
import collections
import datetime
import json
import math
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import nearby_model as M   # noqa: E402
import build_nearby_pool as B   # noqa: E402

GRID = 0.5


def short(n):
    return re.split(r'\s*·\s*', n)[0].strip()


def mins_of(txt):
    h = re.search(r'(\d+) 小时', txt or '')
    m = re.search(r'(\d+) 分', txt or '')
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


def hm(s):
    h, m = s.split(':')
    return int(h) * 60 + int(m)


def fmt(m):
    return '%02d:%02d' % (m // 60, m % 60)


class World:
    def __init__(self):
        pp = os.path.join(ROOT, 'build', 'np', 'pool.json')
        if not os.path.exists(pp):
            raise SystemExit('没有 build/np/pool.json：先跑 python3 tools/build_nearby_pool.py')
        self.pool = json.load(open(pp, encoding='utf-8'))
        self.IT = B.load('data/itineraries.json')['itineraries']
        self.P = B.load('data/geo/pois.json')
        dst = B.load('data/destinations.json')
        self.foreign = {x['id'] for k in ('asia', 'world') for x in dst.get(k, [])} | {'taiwan'}
        self.cat = {d['id']: d for d in B.load('data/catalog/destinations.json')['destinations']}
        self.grid = collections.defaultdict(list)
        for c in self.pool:
            self.grid[(int(math.floor(c['a'] / GRID)), int(math.floor(c['o'] / GRID)))].append(c)

    def near(self, pt, radius_km=M.REACH_KM):
        """pt 周围 radius_km 内的池条目"""
        out = []
        dl = radius_km / 111.0 + 0.01
        dg = radius_km / (111.0 * max(0.2, math.cos(pt[0] * math.pi / 180))) + 0.01
        for i in range(int(math.floor((pt[0] - dl) / GRID)), int(math.floor((pt[0] + dl) / GRID)) + 1):
            for j in range(int(math.floor((pt[1] - dg) / GRID)), int(math.floor((pt[1] + dg) / GRID)) + 1):
                out.extend(self.grid.get((i, j), ()))
        return out

    def city_pt(self, city, dest):
        g = self.P.get(city + '|' + city)
        if isinstance(g, dict) and g.get('lat') is not None:
            return (g['lat'], g['lng'])
        b = self.cat[dest]['base']
        return (b['lat'], b['lng'])


DUR_BY_TYPE = {'sight': 120, 'museum': 150, 'street': 90, 'park': 60, 'food': 60, 'night': 60, 'fun': 90}


def day_model(W, rid, di):
    """按 compile_itineraries 的规则把一天排出来（估算）：行 {s, e, k, name, pt, at, type, dur}，k = see|fun|eat|dep"""
    it = W.IT[rid]
    itd = it['days'][di]
    city = itd.get('city') or it['city']
    domestic = it['dest'] not in W.foreign
    mode = M.mode_of_day(bool(it.get('drive')), domestic, city)
    base = W.city_pt(city, it['dest'])
    t = hm(itd.get('start', '09:00'))
    prev = base
    rows = []
    lunched = t >= 13 * 60
    for st in itd['stops']:
        g = W.P.get(city + '|' + st['q'])
        pt = (st['lat'], st['lng']) if st.get('lat') is not None else ((g['lat'], g['lng']) if isinstance(g, dict) and g.get('lat') is not None else None)
        if st.get('via'):
            mins = mins_of(st['via']) or 25
        elif pt and prev:
            mins = M.leg(prev, pt, mode)[1]
        else:
            mins = 20
        if not lunched and t + mins >= 12 * 60 + 30 and st['type'] != 'food':
            rows.append({'s': t, 'e': t + 60, 'k': 'eat', 'name': '午饭', 'poi': None, 'pt': None, 'at': None, 'how': None, 'type': '', 'dur': 60})
            t += 60
            lunched = True
        rows.append({'s': t, 'e': t + mins, 'k': 'dep', 'name': short(st['name']), 'poi': None, 'pt': None, 'at': None, 'how': None, 'type': '', 'dur': mins})
        t += mins
        if st.get('at'):
            t = max(t, hm(st['at']))
        dur = st.get('dur') or DUR_BY_TYPE.get(st['type'], 90)
        k = 'eat' if st['type'] == 'food' else ('fun' if st['type'] in ('fun', 'night') else 'see')
        rows.append({'s': t, 'e': t + dur, 'k': k, 'name': st['name'], 'poi': st['q'], 'pt': pt, 'at': st.get('at'), 'how': None,
                     'type': B.TYPE_CODE.get(st['type'], ''), 'dur': dur})
        t += dur
        if pt:
            prev = pt
        if k == 'eat':
            lunched = lunched or t <= 15 * 60
    start = it['start']
    date = datetime.date(start[0], start[1] + 1, start[2]) + datetime.timedelta(days=di)
    sg = W.P.get(city + '|' + (itd.get('stay') or '')) if itd.get('stay') else None
    stay_pt = (sg['lat'], sg['lng']) if isinstance(sg, dict) and sg.get('lat') is not None and M.km(base, (sg['lat'], sg['lng'])) < 60 else base
    return {'rid': rid, 'di': di, 'city': city, 'mode': mode, 'rows': rows, 'title': itd.get('title', ''), 'weekday': (date.weekday() + 1) % 7,
            'base': base, 'stay': stay_pt, 'dest': it['dest'], 'foreign': not domestic}


def route_known(W, rid):
    """整条线的站名（含 · 拆开的各段）和坐标：排除“本线已有”"""
    names = []
    it = W.IT[rid]
    for d in it['days']:
        city = d.get('city') or it['city']
        for st in d['stops']:
            g = W.P.get(city + '|' + st['q'])
            pt = (st['lat'], st['lng']) if st.get('lat') is not None else ((g['lat'], g['lng']) if isinstance(g, dict) and g.get('lat') is not None else None)
            for seg in re.split(r'\s*·\s*', st['name']):
                names.append((seg, pt))
    return names


def already_in_route(c, known):
    """名字相同且 15 公里内；名字互相包含（≥3 字）且 15 公里内（二郎剑 / 青海湖二郎剑景区：两处坐标差十几公里，是同一处）；任何站 120 米内"""
    cn = {c['n']} | set(c.get('al') or [])
    cpt = (c['a'], c['o'])
    for seg, pt in known:
        if pt is None:
            for a in cn:
                if a == seg:
                    return True
            continue
        d = M.km(cpt, pt)
        if d <= 0.12:
            return True
        for a in cn:
            if a == seg and d <= 15:
                return True
            if a != seg and min(len(a), len(seg)) >= 3 and (a in seg or seg in a) and d <= 15:
                return True
    return False


def point_rows(dm):
    return [i for i, r in enumerate(dm['rows']) if r['pt'] is not None and r['k'] in ('see', 'fun', 'eat')]


def anchors(dm):
    """可以“调整”的站：see/fun、有坐标、不是定点"""
    return [i for i, r in enumerate(dm['rows']) if r['k'] in ('see', 'fun') and r['pt'] is not None and not r['at']]


def neighbors(dm, i):
    """第 i 行的前一个点、后一个点，以及它们之间已写的车程分钟（只在中间只隔一条 dep 行时才有）"""
    rows = dm['rows']
    pr = [j for j in point_rows(dm) if j < i]
    nx = [j for j in point_rows(dm) if j > i]
    A = rows[pr[-1]]['pt'] if pr else dm['base']
    t0a = None
    if pr and i - pr[-1] == 2 and rows[i - 1]['k'] == 'dep':
        t0a = rows[i - 1]['e'] - rows[i - 1]['s'] or None
    elif not pr and i >= 1 and rows[i - 1]['k'] == 'dep' and i == 1:
        t0a = rows[i - 1]['e'] - rows[i - 1]['s'] or None
    if nx:
        C = rows[nx[0]]['pt']
        t0c = None
        if nx[0] - i == 2 and rows[i + 1]['k'] == 'dep':
            t0c = rows[i + 1]['e'] - rows[i + 1]['s'] or None
    else:
        C = dm['stay']
        t0c = None
    return A, t0a, C, t0c


def trial_rows(dm, i, shift, new_row=None):
    """试算：第 i 行之后的行整体后推 shift；可再加一行 new_row"""
    out = []
    for j, r in enumerate(dm['rows']):
        if r['k'] == 'stay':
            continue
        if j > i:
            out.append({'s': r['s'] + shift, 'e': r['e'] + shift, 'k': r['k']})
        else:
            out.append({'s': r['s'], 'e': r['e'], 'k': r['k']})
    if new_row:
        out.append(new_row)
    return out


def candidates_for(W, rid, di, i, kind, known=None, with_budget=True):
    """第 di 天第 i 行（编译后的行号）：kind='insert'（在它后面加）或 'replace'（换成）。返回排好序的候选（≤5）。
    每项带 inputs，供复算：{A,B/S/C,X,t0..,mode}。"""
    dm = day_model(W, rid, di)
    S = dm['rows'][i]
    mode = dm['mode']
    A, t0a, C, t0c = neighbors(dm, i)
    Spt = S['pt']
    known = known if known is not None else route_known(W, rid)
    day_pts = [r['pt'] for r in dm['rows'] if r['pt'] is not None]
    last_pt_idx = point_rows(dm)[-1] if point_rows(dm) else -1
    ref = [Spt, A, C] if kind == 'insert' else [Spt]
    out = []
    for c in W.near(Spt):
        X = (c['a'], c['o'])
        if (c['ds'] in W.foreign) != dm['foreign']:
            continue
        if dm['foreign'] and c['ds'] != dm['dest']:
            continue
        if dm['city'] in M.BIG_CITIES and c['c'] != dm['city']:
            continue
        if c.get('ev') and not (kind == 'insert' and i >= last_pt_idx):
            continue
        if not M.in_reach(X, ref):
            continue
        sp = M.same_spot(X, day_pts)
        if sp == 'same':
            continue
        if already_in_route(c, known):
            continue
        xx = c.get('x') or {}
        if M.closed_on(xx.get('cl'), dm['weekday']):
            continue
        if kind == 'insert':
            delta = M.detour_insert(Spt, C if C is not None else None, X, t0c, mode)
            # 在 S 之后插：A' = S，B' = 下一个点
            f = M.factor(Spt, C, t0c, mode) if (C is not None and t0c) else 1.0
            if not M.detour_ok(delta):
                continue
            arrive = S['e'] + M.t(Spt, X, mode)
            shift = int(round(delta)) + c['d']
            new_row = {'s': arrive, 'e': arrive + c['d'], 'k': 'fun'}
            rows_ = trial_rows(dm, i, shift, new_row)
            inputs = {'A': Spt, 'B': C, 'X': X, 't0': t0c, 'mode': mode, 'P': A}      # P：S 的前一个点——“离参照点 ≤35 公里”的参照点是 [S, P, B]（和 site.js 一致）
        else:
            if not M.replace_near(Spt, X, mode):
                continue
            delta = M.detour_replace(A, Spt, C, X, t0a, t0c, mode)
            if not M.detour_ok(delta):
                continue
            f = max(M.factor(A, Spt, t0a, mode) if t0a else 1.0, M.factor(Spt, C, t0c, mode) if t0c else 1.0)
            arrive = S['s'] + int(round(M.factor(A, Spt, t0a, mode) * M.t(A, X, mode) - (t0a or M.t(A, Spt, mode))))
            shift = int(round(delta)) + c['d'] - S['dur']
            rows_ = trial_rows(dm, i, shift)
            # 被换的那一行自己的时长也变了：把它的结束换成新站的
            ri = [j for j, r in enumerate(dm['rows']) if r['k'] != 'stay'].index(i)
            rows_[ri] = {'s': arrive, 'e': arrive + c['d'], 'k': S['k']}
            inputs = {'A': A, 'S': Spt, 'C': C, 'X': X, 't0a': t0a, 't0b': t0c, 'mode': mode}
        if not M.hours_ok(arrive, c['d'], xx.get('h')):
            continue
        bud = M.day_budget_ok(rows_, kind == 'insert')
        if with_budget and not bud['ok']:
            continue
        out.append({'id': c['i'], 'n': c['n'], 's': c.get('s', ''), 't': c['t'], 'd': c['d'], 'delta': delta, 'shown': M.show5(delta), 'pop': c['p'],
                    'has_s': bool(c.get('s')), 'same': M.same_kind(c['t'], c['n'], S['type'], S['name'], dm['title']), 'f': f, 'approx': bool(c.get('ap')),
                    'beside': sp == 'beside', 'tags': [x for x, v in (('要预约', xx.get('b')), ('周一闭馆' if xx.get('cl') == 1 else '', xx.get('cl') == 1), ('就在旁边', sp == 'beside')) if v and x],
                    'kind': kind, 'inputs': inputs, 'day': {'rid': rid, 'di': di, 'i': i, 'city': dm['city'], 'weekday': dm['weekday']}, 'pt': X, 'budget': bud,
                    'ds': c['ds']})
    return M.rank(out)


def _fmt_delta(c):
    if c['kind'] == 'insert':
        return '+%d 分钟' % c['shown']
    if c['delta'] >= 5:
        return '多 %d 分钟' % c['shown']
    if c['delta'] <= -10:
        return '省 %d 分钟' % -c['shown']
    return '路程差不多'


def pick_anchors(W, rid, day=None, n=3):
    """每条线挑 n 个站：均匀取（20% / 50% / 80% 位置），只取有坐标、非定点的 see/fun"""
    lst = []
    for di in range(len(W.IT[rid]['days'])):
        if day is not None and di != day - 1:
            continue
        dm = day_model(W, rid, di)
        for i in anchors(dm):
            lst.append((di, i))
    if not lst:
        return []
    if len(lst) <= n:
        return lst
    return [lst[int(len(lst) * q)] for q in (0.2, 0.5, 0.8)][:n]


def show(W, rid, day=None):
    it = W.IT[rid]
    print('=' * 78)
    print('%s · %s（%s，%s）' % (rid, it['label'], it['dest'], '国外' if it['dest'] in W.foreign else '国内'))
    known = route_known(W, rid)
    for di, i in pick_anchors(W, rid, day):
        dm = day_model(W, rid, di)
        S = dm['rows'][i]
        print('-' * 78)
        print('第 %d 天 %s（%s）· 模式 %s · 「%s」%s–%s' % (di + 1, dm['title'], dm['city'], dm['mode'], S['name'], fmt(S['s']), fmt(S['e'])))
        for kind, lab in (('insert', '在它后面加'), ('replace', '换成')):
            cs = candidates_for(W, rid, di, i, kind, known)
            allc = candidates_for(W, rid, di, i, kind, known, with_budget=False)
            print('  %s：%d 个%s' % (lab, len(cs), '' if len(allc) == len(cs) else '（另有 %d 个被当天预算挡掉：这天已排满）' % (len(allc) - len(cs))))
            for c in cs:
                print('    %-12s %-9s %s · 约 %d 分 · %s %s' % (c['n'], _fmt_delta(c), c['t'], c['d'], c['s'] or '（没有一句话）', ('[' + '/'.join(c['tags']) + ']') if c['tags'] else ''))


def empty_stats(W, limit=None):
    """全站空状态占比：每个 see/fun 锚点的“在它后面加”（insert）和“换成”（replace）的候选数"""
    per = {(g, k): [] for g in ('domestic', 'foreign') for k in ('insert', 'replace')}
    line_max = {'domestic': [], 'foreign': []}
    full_only = {'domestic': 0, 'foreign': 0}
    n_routes = 0
    for rid in W.IT:
        n_routes += 1
        known = route_known(W, rid)
        cnts = []
        g = 'foreign' if W.IT[rid]['dest'] in W.foreign else 'domestic'
        for di in range(len(W.IT[rid]['days'])):
            dm = day_model(W, rid, di)
            for i in anchors(dm):
                cs = candidates_for(W, rid, di, i, 'insert', known)
                per[(g, 'insert')].append(len(cs))
                cnts.append(len(cs))
                if not cs and candidates_for(W, rid, di, i, 'insert', known, with_budget=False):
                    full_only[g] += 1
                per[(g, 'replace')].append(len(candidates_for(W, rid, di, i, 'replace', known)))
        if cnts:
            line_max[g].append(max(cnts))
        if limit and n_routes >= limit:
            break
    res = {}
    for g in ('domestic', 'foreign'):
        res[g] = {'zero_because_full': full_only[g], 'lines': len(line_max[g]), 'lines_with_none': sum(1 for x in line_max[g] if x == 0),
                  'line_max_median': statistics.median(line_max[g]) if line_max[g] else 0}
        for k in ('insert', 'replace'):
            v = per[(g, k)]
            res[g][k] = {'stops': len(v), 'median': statistics.median(v) if v else 0, 'zero_share': (sum(1 for x in v if x == 0) / len(v)) if v else 0,
                         'ge3_share': (sum(1 for x in v if x >= 3) / len(v)) if v else 0}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--route', default=None)
    ap.add_argument('--day', type=int, default=None)
    ap.add_argument('--stats-only', action='store_true')
    ap.add_argument('--no-stats', action='store_true')
    a = ap.parse_args()
    W = World()
    if not a.stats_only:
        for rid in ([a.route] if a.route else ['xa3', 'gqhx10', 'tk4', 'par5', 'nj3']):
            show(W, rid, a.day)
    if not a.no_stats:
        st = empty_stats(W)
        print('=' * 78)
        print('空状态占比（每个可调整的站，“在它后面加”的候选数；已过滤 同处/本线已有/跨城/关门/当天预算）')
        for g, lab in (('domestic', '国内'), ('foreign', '国外')):
            s = st[g]
            for k, kl in (('insert', '在它后面加'), ('replace', '换成')):
                x = s[k]
                print('  %s · %s：%d 个站 · 每站候选数中位 %s · 0 个的占 %.0f%% · ≥3 个的占 %.0f%%' % (lab, kl, x['stops'], x['median'], x['zero_share'] * 100, x['ge3_share'] * 100))
            print('  %s · 整条线：%d 条线里，一个站都没有“加”候选的 %d 条（%.0f%%）· 每条线最多一站的候选数中位 %s · “加”为 0 里因当天已排满的站 %d 个' % (
                lab, s['lines'], s['lines_with_none'], 100.0 * s['lines_with_none'] / max(1, s['lines']), s['line_max_median'], s['zero_because_full']))


if __name__ == '__main__':
    main()
