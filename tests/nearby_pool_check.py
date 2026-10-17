#!/usr/bin/env python3
"""「顺路加一站」候选池的质量闸（会红的判据）。先跑 python3 tools/build_nearby_pool.py 生成 build/np/。

    python3 tests/nearby_pool_check.py                      # 全部检查；任一不过退出码 1
    python3 tests/nearby_pool_check.py --inject coord       # 反向验证：在内存里注入一种缺陷，必须变红（不改任何文件）
        coord      把一个候选的坐标挪到 500 公里外
        station    塞进一个火车站和一个机场
        dup        塞进一个和已有候选相距 30 米的同址重复
        threshold  把绕路阈值 DETOUR_MAX 改成 100 万（模拟“阈值被改坏”），候选列表里会混进绕路 >30 分钟的
    python3 tests/nearby_pool_check.py --update-baseline    # 池条数基线（≥95%）重置成现在的条数（有意缩池时才用）

检查项：
  1 坐标：离所属城市中心 ≤400 公里；离所属目的地（基点或其任一城市中心）国内 ≤600、国外 ≤400 公里
  2 命中名：地理编码器命中的显示名第一段要和站名对得上（翠华山被定位到学生公寓就是这样）
  3 非景点：名字/导航词/别名不含 车站 机场 酒店 营地 商场 餐厅 码头…；一句话不写商场/落脚；没有高海拔、季节限定词
  4 同址：任意两个候选相距 ≥250 米；同名 15 公里内不得有两条
  5 字段：一句话 ≤24 字；id 唯一；类型码合法；坐标范围合法；停留 5–600 分钟
  6 条数：不得比基线（tests/nearby_pool_baseline.json）少 5% 以上
  7 分片：每片 ≤36 KB；每个候选在它该在的格里；分片总数据 = pool.json；没有多余的分片文件；_index.js 清单 = 磁盘上的分片
  8 候选结果：抽样若干线路的若干站，“加/换”的每个候选独立复算：绕路 ≤30 分钟、替换新站离原站 ≤30 分钟、
    离参照点 ≤35 公里、和当天站 ≥250 米、当天非吃饭站 ≤5 / 结束 ≤21:30 / 首尾 ≤13 小时、不超 5 个、晚上才有意义的只插在最后一站之后
  9 分片能被 node 执行（window.ZNP[格] 是数组、条数对得上）；没有 node 退出码 2（不当成绿）
这里的 30 / 35 / 250 / 5 / 21:30 / 13 小时是**写死在闸里的字面量**，不读 nearby_model 的常量：常量被改坏时闸要能看出来。
"""
import argparse
import collections
import json
import math
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import nearby_model as M   # noqa: E402
import build_nearby_pool as B   # noqa: E402
import nearby_prototype as NP   # noqa: E402

NP_DIR = os.path.join(ROOT, 'build', 'np')
BASELINE = os.path.join(ROOT, 'tests', 'nearby_pool_baseline.json')
# 写死的字面量（用户 2026-10-16 拍板）
LIT_DETOUR = 30
LIT_REPLACE_NEAR = 30
LIT_REACH_KM = 35
LIT_SAME_KM = 0.25
LIT_MAX_NONMEAL = 5
LIT_END = 21 * 60 + 30
LIT_SPAN = 13 * 60
LIT_LIST = 5
LIT_SHARD_BYTES = 36 * 1024
CITY_KM, DEST_DOM_KM, DEST_FOR_KM = 400, 600, 400
CODES = set(B.TYPE_CODE.values())


def parse_shard(txt):
    """(window.ZNP=window.ZNP||{})['34_36']=[…]; → ('34_36', [...])；格式不对 → (None, None)"""
    m = re.match(r"^\(window\.ZNP=window\.ZNP\|\|\{\}\)\['([\d_]+)'\]=(\[.*\]);\n$", txt, re.S)
    return (m.group(1), json.loads(m.group(2))) if m else (None, None)


def pt(e):
    return (e['a'], e['o'])


def inject(pool, how):
    pool = [dict(e) for e in pool]
    if how == 'coord':
        for e in pool:
            if not e['k'].startswith('niche|') and isinstance(NP_P.get(e['c'] + '|' + e['c']), dict):
                e['a'] = round(e['a'] + 4.5, 3)       # ≈ 500 公里
                print('  [注入] %s（%s）纬度 +4.5°（≈500 公里）' % (e['n'], e['c']))
                break
    elif how == 'station':
        base = next(e for e in pool if e['c'] == '西安')
        for i, (n, extra) in enumerate((('西安北站', {}), ('咸阳国际机场', {}))):
            e = dict(base)
            e.update({'k': '西安|' + n, 'i': 'inj%05d' % i, 'n': n, 'q': n, 'a': round(base['a'] + 0.05 * (i + 1), 3), 'o': round(base['o'] + 0.05 * (i + 1), 3), 's': '', 'x': {}})
            e.pop('al', None)
            pool.append(e)
            print('  [注入] 混入 %s' % n)
    elif how == 'dup':
        e0 = next(e for e in pool if e['c'] == '西安' and e['s'])
        e = dict(e0)
        e.update({'k': e0['k'] + '#dup', 'i': 'injdup01', 'a': round(e0['a'] + 0.0003, 4)})
        pool.append(e)
        print('  [注入] 复制 %s，坐标偏 30 米，换个 id' % e0['n'])
    return pool


def run(pool, how):
    fails = []

    def fail(name, msgs):
        if msgs:
            fails.append((name, msgs))

    P = NP_P
    CAT = {d['id']: d for d in B.load('data/catalog/destinations.json')['destinations']}
    IT = B.load('data/itineraries.json')['itineraries']
    foreign = NP_FOREIGN
    # 目的地 → 它的城市中心们
    centres = collections.defaultdict(set)
    for rid, it in IT.items():
        for d in it['days']:
            g = P.get((d.get('city') or it['city']) + '|' + (d.get('city') or it['city']))
            if isinstance(g, dict) and g.get('lat') is not None:
                centres[it['dest']].add((g['lat'], g['lng']))

    # 1 坐标
    bad = []
    for e in pool:
        cc = P.get(e['c'] + '|' + e['c'])
        if not e['k'].startswith('niche|') and isinstance(cc, dict) and cc.get('lat') is not None:
            d = M.km(pt(e), (cc['lat'], cc['lng']))
            if d > CITY_KM:
                bad.append('%s（%s）离城市中心 %.0f 公里' % (e['n'], e['c'], d))
                continue
        ds = e['ds']
        lim = DEST_FOR_KM if ds in foreign else DEST_DOM_KM
        refs = list(centres.get(ds, ()))
        if ds in CAT:
            refs.append((CAT[ds]['base']['lat'], CAT[ds]['base']['lng']))
        if refs:
            d = min(M.km(pt(e), r) for r in refs)
            if d > lim:
                bad.append('%s（%s，%s）离目的地 %.0f 公里（>%d）' % (e['n'], e['c'], ds, d, lim))
    fail('1 坐标离城市/目的地过远', bad)

    # 2 命中名
    bad = []
    for e in pool:
        g = P.get(e['k'])
        if isinstance(g, dict) and g.get('hit') is not None and abs(g['lat'] - e['a']) < 0.002 and abs(g['lng'] - e['o']) < 0.002:      # 坐标被线路里写的 lat/lng 覆盖的（作者给的）不查命中名
            hit = g['hit']
            if not hit.startswith(('人工', 'OSM', '市区')) and not B.name_ok(re.sub(r'^\S*核对\s*', '', hit), e['q'], e['n'], e['c']):
                bad.append('%s：命中“%s”和站名对不上' % (e['n'], hit[:30]))
    fail('2 命中名对不上站名', bad)

    # 3 非景点
    bad = []
    for e in pool:
        for f_, v in (('名字', e['n']), ('导航词', e['q'])) + tuple(('别名', a) for a in e.get('al', [])):
            if B.NON_ATTR.search(v):
                bad.append('%s 的%s“%s”像车站/机场/酒店/商场…' % (e['n'], f_, v))
        if B.TOWN_ONLY.search(e['n']):
            bad.append('%s 是县城/车站（落脚点）' % e['n'])
        if B.BOAT_ONLY.search(e['n']):
            bad.append('%s 是岛（要过水）' % e['n'])
        s = e.get('s') or ''
        if B.MALL_TEXT.search(s) or B.BASE_TEXT.search(s):
            bad.append('%s 的一句话写的是商场/落脚：%s' % (e['n'], s))
        if B.ALT_NAME.search(e['n']):
            bad.append('%s 是高海拔' % e['n'])
        if B.SEASONAL.search(e['n']) or B.SEASONAL.search(s):
            bad.append('%s 是季节限定' % e['n'])
    fail('3 混入了非景点/高海拔/季节限定', bad)

    # 4 同址
    bad = []
    G = 0.25
    grid = collections.defaultdict(list)
    for e in pool:
        grid[(int(math.floor(e['a'] / G)), int(math.floor(e['o'] / G)))].append(e)
    for (i, j), lst in grid.items():
        near = [x for di in (-1, 0, 1) for dj in (-1, 0, 1) for x in grid.get((i + di, j + dj), ())]
        for a in lst:
            for b in near:
                if a['i'] >= b['i']:
                    continue
                d = M.km(pt(a), pt(b))
                if d < LIT_SAME_KM:
                    bad.append('%s 与 %s 相距 %.0f 米' % (a['n'], b['n'], d * 1000))
                elif a['n'] == b['n'] and d <= 15:
                    bad.append('同名 %s 在 15 公里内有两条（%.1f 公里）' % (a['n'], d))
    fail('4 同址/同名重复', sorted(set(bad)))

    # 5 字段
    bad = []
    ids = collections.Counter(e['i'] for e in pool)
    for e in pool:
        if ids[e['i']] > 1:
            bad.append('id 重复 %s' % e['i'])
        if len(e.get('s') or '') > 24:
            bad.append('%s 一句话 %d 字' % (e['n'], len(e['s'])))
        if e['t'] not in CODES:
            bad.append('%s 类型码 %r' % (e['n'], e['t']))
        if not (-90 <= e['a'] <= 90 and -180 <= e['o'] <= 180):
            bad.append('%s 坐标越界' % e['n'])
        if not (5 <= e['d'] <= 600):
            bad.append('%s 停留 %s 分钟' % (e['n'], e['d']))
    fail('5 字段不合法', sorted(set(bad)))

    # 6 条数
    base = json.load(open(BASELINE, encoding='utf-8')) if os.path.exists(BASELINE) else None
    if not base:
        fail('6 没有基线文件（先 --update-baseline）', ['tests/nearby_pool_baseline.json 不存在'])
    elif len(pool) < base['count'] * 0.95:
        fail('6 池条数比基线少了 5% 以上', ['基线 %d，现在 %d' % (base['count'], len(pool))])

    # 7 分片
    bad = []
    on_disk = {f[:-3]: os.path.join(NP_DIR, f) for f in os.listdir(NP_DIR) if f.endswith('.js') and not f.startswith('_')}
    want = collections.defaultdict(list)
    for e in pool:
        want[M.cell_key(e['a'], e['o'])].append(e)
    for key, path in on_disk.items():
        if os.path.getsize(path) > LIT_SHARD_BYTES:
            bad.append('分片 %s %.1f KB（>36 KB）' % (key, os.path.getsize(path) / 1024))
        txt = open(path, encoding='utf-8').read()
        k2, rows = parse_shard(txt)
        if k2 != key or rows is None:
            bad.append('分片 %s 格式不对' % key)
            continue
        for r in rows:
            if M.cell_key(r['a'], r['o']) != key:
                bad.append('%s 在分片 %s 里，坐标却属于 %s' % (r['n'], key, M.cell_key(r['a'], r['o'])))
    if how is None:                      # 注入只改内存里的池，分片是磁盘上的；不拿注入后的池去比
        total = sum(len(parse_shard(open(p, encoding='utf-8').read())[1] or []) for p in on_disk.values())
        if total != len(pool):
            bad.append('分片里共 %d 条，pool.json %d 条' % (total, len(pool)))
        if set(on_disk) != set(want):
            bad.append('分片文件集合与池不一致：多 %s 少 %s' % (sorted(set(on_disk) - set(want))[:3], sorted(set(want) - set(on_disk))[:3]))
    ix = os.path.join(NP_DIR, '_index.js')
    if not os.path.exists(ix):
        bad.append('缺 _index.js（有数据的格的清单）')
    elif how is None and json.loads(re.match(r'^window\.ZNP_CELLS=(\[.*\]);\n$', open(ix, encoding='utf-8').read(), re.S).group(1)) != sorted(on_disk):
        bad.append('_index.js 的清单和磁盘上的分片不一致')
    fail('7 分片', bad)
    return fails


def check_candidates(W):
    """8 抽样候选独立复算"""
    bad = []
    rids = sorted(W.IT)[::20]
    n_lists = n_cands = 0
    for rid in rids:
        known = NP.route_known(W, rid)
        for di, i in NP.pick_anchors(W, rid, None, 3):
            dm = NP.day_model(W, rid, di)
            S = dm['rows'][i]
            day_pts = [r['pt'] for r in dm['rows'] if r['pt'] is not None]
            last_idx = NP.point_rows(dm)[-1]
            for kind in ('insert', 'replace'):
                cs = NP.candidates_for(W, rid, di, i, kind, known)
                n_lists += 1
                if len(cs) > LIT_LIST:
                    bad.append('%s 第%d天 %s：列表 %d 个（>5）' % (rid, di + 1, S['name'], len(cs)))
                for c in cs:
                    n_cands += 1
                    tag = '%s 第%d天「%s」%s→%s' % (rid, di + 1, S['name'], '加' if kind == 'insert' else '换', c['n'])
                    inp = c['inputs']
                    if kind == 'insert':
                        d = M.detour_insert(inp['A'], inp['B'], inp['X'], inp['t0'], inp['mode'])
                        refs = [inp['A'], inp['B'], inp.get('P')]      # 参照点 = [S, 后一个点, S 的前一个点]：和 candidates_for / site.js 的 ref=[S,A,C] 同一条规则
                    else:
                        d = M.detour_replace(inp['A'], inp['S'], inp['C'], inp['X'], inp['t0a'], inp['t0b'], inp['mode'])
                        refs = [inp['S']]
                        if M.t(inp['S'], inp['X'], inp['mode']) > LIT_REPLACE_NEAR:
                            bad.append(tag + '：新站离原站车程 %d 分钟（>30）' % M.t(inp['S'], inp['X'], inp['mode']))
                    if abs(d - c['delta']) > 1e-9:
                        bad.append(tag + '：报告的绕路 %.1f ≠ 复算 %.1f' % (c['delta'], d))
                    if d > LIT_DETOUR:
                        bad.append(tag + '：绕路 %.0f 分钟（>30）' % d)
                    if not any(r is not None and M.km(inp['X'], r) <= LIT_REACH_KM for r in refs):
                        bad.append(tag + '：离参照点 >35 公里')
                    near = min([M.km(inp['X'], p) for p in day_pts] or [999])
                    if near < LIT_SAME_KM:
                        bad.append(tag + '：离当天某站只有 %.0f 米' % (near * 1000))
                    b = c['budget']
                    if kind == 'insert' and b['n'] > LIT_MAX_NONMEAL:
                        bad.append(tag + '：加完当天 %d 个非吃饭站（>5）' % b['n'])
                    if b['last'] > LIT_END:
                        bad.append(tag + '：加完当天结束 %s（>21:30）' % NP.fmt(b['last']))
                    if b['span'] > LIT_SPAN:
                        bad.append(tag + '：加完当天首尾 %d 分钟（>13 小时）' % b['span'])
                    ev = next((p for p in W.pool if p['i'] == c['id']), {}).get('ev')
                    if ev and not (kind == 'insert' and i >= last_idx):
                        bad.append(tag + '：晚上才有意义的地方插在了白天中间')
    return bad, n_lists, n_cands


def node_check():
    node = shutil.which('node')
    if not node:
        return None
    code = r"""
var fs = require('fs'), vm = require('vm'), dir = process.argv[1], out = {};
fs.readdirSync(dir).forEach(function (f) {
  if (!/\.js$/.test(f) || f.charAt(0) === '_') return;
  var ctx = { window: {} }; vm.createContext(ctx);
  try { vm.runInContext(fs.readFileSync(dir + '/' + f, 'utf8'), ctx); } catch (e) { out[f] = 'ERR ' + e.message; return; }
  var k = f.replace(/\.js$/, ''), a = ctx.window.ZNP && ctx.window.ZNP[k];
  out[f] = Array.isArray(a) ? a.length : 'NOT_ARRAY';
});
process.stdout.write(JSON.stringify(out));
"""
    p = subprocess.run([node, '-e', code, NP_DIR], capture_output=True, text=True)
    return json.loads(p.stdout) if p.returncode == 0 else {'node': 'ERR ' + p.stderr[-200:]}


def main():
    global NP_P, NP_FOREIGN
    ap = argparse.ArgumentParser()
    ap.add_argument('--inject', choices=['coord', 'station', 'dup', 'threshold'], default=None)
    ap.add_argument('--update-baseline', action='store_true')
    a = ap.parse_args()
    pp = os.path.join(NP_DIR, 'pool.json')
    if not os.path.exists(pp):
        print('没有 build/np/pool.json：先跑 python3 tools/build_nearby_pool.py')
        return 2
    pool = json.load(open(pp, encoding='utf-8'))
    if a.update_baseline:
        json.dump({'count': len(pool), 'note': '候选池条数基线；tests/nearby_pool_check.py 要求不少于它的 95%'}, open(BASELINE, 'w', encoding='utf-8'), ensure_ascii=False)
        print('基线 = %d' % len(pool))
        return 0
    W = NP.World()
    NP_P, NP_FOREIGN = W.P, W.foreign
    if a.inject:
        print('反向验证：注入 %s（只改内存，不改任何文件）' % a.inject)
    if a.inject in ('coord', 'station', 'dup'):
        pool = inject(pool, a.inject)
    patched = None
    if a.inject == 'threshold':
        patched = (M.DETOUR_MAX, M.REPLACE_NEAR_MAX)
        M.DETOUR_MAX = 10 ** 6
        M.REPLACE_NEAR_MAX = 10 ** 6
        print('  [注入] DETOUR_MAX / REPLACE_NEAR_MAX = 10**6')
    try:
        fails = run(pool, a.inject if a.inject in ('coord', 'station', 'dup') else None)
        bad8, nl, nc = check_candidates(W)
    finally:
        if patched:
            M.DETOUR_MAX, M.REPLACE_NEAR_MAX = patched
    if bad8:
        fails.append(('8 候选结果不合规', bad8))
    nres = node_check()
    if nres is None:
        print('没有 node：第 9 项无法执行（退出码 2，不当成绿）')
        return 2
    bad9 = [k + ' → ' + str(v) for k, v in nres.items() if not isinstance(v, int)]
    if not a.inject:
        n_shard_rows = sum(v for v in nres.values() if isinstance(v, int))
        if n_shard_rows != len(pool):
            bad9.append('node 数到分片里共 %d 条，池 %d 条' % (n_shard_rows, len(pool)))
    if bad9:
        fails.append(('9 分片不能被 node 执行', bad9))
    names = ['1 坐标离城市/目的地过远', '2 命中名对不上站名', '3 混入了非景点/高海拔/季节限定', '4 同址/同名重复', '5 字段不合法', '6 池条数', '7 分片', '8 候选结果不合规', '9 分片不能被 node 执行']
    failed = {f[0].split(' ')[0] for f in fails}
    print('池 %d 条 · 分片 %d 个 · 抽样 %d 个候选列表、%d 个候选独立复算' % (len(pool), len(nres), nl, nc))
    for n in names:
        print('  %s %s' % ('红' if n.split(' ')[0] in failed else '绿', n))
    for name, msgs in fails:
        print('✗ %s（%d）' % (name, len(msgs)))
        for m in msgs[:5]:
            print('    ' + m[:200])
    if fails:
        print('结果：红（%d 项）' % len(fails))
        return 1
    print('结果：全绿')
    return 0


NP_P = {}
NP_FOREIGN = set()

if __name__ == '__main__':
    sys.exit(main())
