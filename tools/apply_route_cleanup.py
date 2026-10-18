#!/usr/bin/env python3
# 线路层面清理补丁：把 data/catalog/route_cleanup.json 应用到 data/itineraries.json 与 data/catalog/trips.json
#
# 用法（项目根目录跑）：
#   python3 tools/apply_route_cleanup.py --dry                 只打印将要改什么，不写任何文件
#   python3 tools/apply_route_cleanup.py --check               只校验（含 5 类断言），不写
#   python3 tools/apply_route_cleanup.py --selftest            反向注入自检：故意注入 5 种缺陷，各应报错
#   python3 tools/apply_route_cleanup.py                       落地（先校验、先备份；要落地请在构建空闲时跑）
#   python3 tools/apply_route_cleanup.py --only renames        分步：renames | title_fix | sisters | covered | group（可逗号分隔）
#   python3 tools/apply_route_cleanup.py --revert              逆向补丁还原（只改回我们改过的字段，别人的改动不动）
#   python3 tools/apply_route_cleanup.py --revert --from-backup [时间戳]   整文件还原到快照（默认最早那份 = 第一次落地前的原始状态）
#   --data-dir DIR   指向一份 data/ 的拷贝（里面有 itineraries.json 和 catalog/trips.json），验证时用
#   --cleanup PATH   补丁文件，默认 <data-dir>/catalog/route_cleanup.json，没有则用项目里的
#   --tsv PATH       把“改了什么”的前后表写成 tsv
#
# 保证：幂等（连跑两次文件指纹相同，第二次不重写文件）；落地前必备份到 <data-dir>/catalog/_cleanup_backup/<时间戳>/；
# 只会改 itineraries 的 label/title、trips 的 title/headline 和三个新字段 sisters/covered_by/group_city；
# 不改 id、天数、站点（--check 在内存里把“落地后”和“落地前”逐字段比对，改到别的字段就报错）。
# 字符串漂移保护：当前值既不是补丁里的“旧值”也不是“新值”（别人改过了）时，跳过那一条并报告，不覆盖。
import argparse, copy, collections, datetime, hashlib, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECTIONS = ('renames', 'title_fix', 'sisters', 'covered', 'group')
MANAGED = ('sisters', 'covered_by', 'group_city')      # trips.json 里由本脚本管理的新字段（顺序固定）
CNUM = '零一二三四五六七八九'


class CheckError(Exception):
    pass


def cn(n):
    if n < 10: return '两' if n == 2 else CNUM[n]
    if n < 20: return '十' + (CNUM[n % 10] if n % 10 else '')
    if n < 100: return CNUM[n // 10] + '十' + (CNUM[n % 10] if n % 10 else '')
    return '一百零' + CNUM[n % 10]


def dumps(d):
    return json.dumps(d, ensure_ascii=False, indent=1)      # 与现有两个文件字节一致（无末尾换行）


def sha(s):
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


# ---------------------------------------------------------------- 读写
class Store:
    def __init__(self, data_dir):
        self.dir = data_dir
        self.p_it = os.path.join(data_dir, 'itineraries.json')
        self.p_tr = os.path.join(data_dir, 'catalog', 'trips.json')
        self.backup_root = os.path.join(data_dir, 'catalog', '_cleanup_backup')

    def read(self):
        self.raw_it = open(self.p_it, encoding='utf-8').read()
        self.raw_tr = open(self.p_tr, encoding='utf-8').read()
        self.it_doc = json.loads(self.raw_it)
        self.tr_doc = json.loads(self.raw_tr)
        self.fmt_ok = dumps(self.it_doc) == self.raw_it and dumps(self.tr_doc) == self.raw_tr
        return self

    def write(self, it_doc, tr_doc):
        # 写之前再读一次：别人在这期间改了文件就放弃（一个仓库同一时间只有一个写入者）
        for p, raw in ((self.p_it, self.raw_it), (self.p_tr, self.raw_tr)):
            if open(p, encoding='utf-8').read() != raw:
                raise SystemExit('放弃：%s 在读取之后被别人改了，请稍后重跑' % p)
        for p, doc in ((self.p_it, it_doc), (self.p_tr, tr_doc)):
            tmp = p + '.cleanup.tmp'
            open(tmp, 'w', encoding='utf-8').write(dumps(doc))
            os.replace(tmp, p)

    def snapshot(self, kind='apply'):
        ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        d = os.path.join(self.backup_root, ts)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, 'itineraries.json'), 'w', encoding='utf-8').write(self.raw_it)
        open(os.path.join(d, 'trips.json'), 'w', encoding='utf-8').write(self.raw_tr)
        json.dump({'time': ts, 'kind': kind, 'sha256': {'itineraries.json': sha(self.raw_it), 'trips.json': sha(self.raw_tr)}}, open(os.path.join(d, 'MANIFEST.json'), 'w'), indent=1)
        return d


# ---------------------------------------------------------------- 计划（纯函数：不碰磁盘）
def parse_only(s):
    if not s: return set(SECTIONS)
    out = set()
    for x in s.split(','):
        x = x.strip()
        if x not in SECTIONS: raise SystemExit('--only 只能是 ' + '|'.join(SECTIONS))
        out.add(x)
    return out


def plan(it_doc, tr_doc, cu, only, revert=False):
    """返回 (it_new, tr_new, changes, notes)。changes = [(文件, id, 字段, 旧, 新, 段)]；notes = 跳过/漂移的说明。"""
    it = copy.deepcopy(it_doc); tr = copy.deepcopy(tr_doc)
    I = it['itineraries']; T = {t['id']: t for t in tr['trips']}
    ch = []; notes = []

    def setf(file, d, rid, field, old_ok, new, sec, cur_label=None):
        # old_ok: 允许被改的“当前值”；new: 目标值。revert 时调用方把两者对调。
        cur = d.get(field)
        if cur == new: return
        if cur == old_ok:
            d[field] = new; ch.append((file, rid, field, cur, new, sec))
        else:
            notes.append('漂移跳过 %s %s.%s：当前「%s」既不是旧值「%s」也不是新值「%s」' % (file, rid, field, cur, old_ok, new))

    for sec, key, fields in (('renames', 'renames', ('label', 'title')), ('title_fix', 'title_fix', ('title',))):
        if sec not in only: continue
        for rid, v in cu[key]['items'].items():
            if rid not in I: continue
            r = I[rid]
            if sec == 'renames':
                pairs = [('label', v['old_label'], v['label'])] + ([('title', v['old_title'], v['title'])] if v.get('title') else [])
            else:
                pairs = [('title', v['old_title'], v['title'])]
            for field, old, new in pairs:
                a, b = (new, old) if revert else (old, new)
                setf('itineraries.json', r, rid, field, a, b, sec)
                # trips：label→title，title→headline；只有两边本来一致才跟着改（ae4 这类“trips.title 是另一个写法”的不动）
                t = T.get(rid)
                if t is None: continue
                tf = 'title' if field == 'label' else 'headline'
                hl = v.get('headline') if sec == 'title_fix' else None      # trips.headline 与 itineraries.title 写法不同时，补丁里单独记了旧新值
                if hl:
                    a, b = (hl['new'], hl['old']) if revert else (hl['old'], hl['new'])
                if t.get(tf) == a or t.get(tf) == b:
                    setf('trips.json', t, rid, tf, a, b, sec)
                else:
                    notes.append('trips 不跟 %s %s.%s：当前「%s」与线路表里的写法不同' % (sec, rid, tf, t.get(tf)))

    # 三个新字段：补丁文件是唯一来源——在补丁里的写入，不在补丁里（且本脚本管着这个字段）的删掉
    want = {k: {} for k in MANAGED}
    if 'sisters' in only:
        for g in cu['sisters']['groups']:
            for rid in g['ids']: want['sisters'][rid] = {'ids': g['ids'], 'main': g['main']}
    if 'covered' in only:
        for rid, v in cu['covered_by']['items'].items():
            if v.get('apply'): want['covered_by'][rid] = v['to']
    if 'group' in only:
        for rid, v in cu['group_city']['items'].items(): want['group_city'][rid] = v['g']
    scope = {'sisters': 'sisters' in only, 'covered_by': 'covered' in only, 'group_city': 'group' in only}
    sec_name = {'sisters': 'sisters', 'covered_by': 'covered', 'group_city': 'group'}
    for rid, t in T.items():
        for f in MANAGED:
            if not scope[f]: continue
            w = None if revert else want[f].get(rid)
            if w is None:
                if f in t:
                    ch.append(('trips.json', rid, f, json.dumps(t[f], ensure_ascii=False), '(删除)', sec_name[f])); del t[f]
            elif t.get(f) != w:
                ch.append(('trips.json', rid, f, json.dumps(t[f], ensure_ascii=False) if f in t else '(无)', json.dumps(w, ensure_ascii=False), sec_name[f])); t[f] = w
        # 固定键序：原有键保持原顺序，管理字段按固定顺序排在最后（幂等）
        if any(f in t for f in MANAGED):
            base = {k: v for k, v in t.items() if k not in MANAGED}
            new = dict(base)
            for f in MANAGED:
                if f in t: new[f] = t[f]
            if list(new) != list(t):
                t.clear(); t.update(new)
    tr['trips'] = [T[x['id']] for x in tr['trips']]
    return it, tr, ch, notes


# ---------------------------------------------------------------- 校验
def dup_labels(I):
    g = collections.defaultdict(list)
    for k, r in I.items(): g[(r['dest'], r['label'])].append(k)
    return {a: b for a, b in g.items() if len(b) > 1}


TITLE_DUP = re.compile(r'^(\d+|[一二两三四五六七八九十]+)天\s*[(（][^)）]*[)）]')
TITLE_DIGIT = re.compile(r'^\d')
DAYS_IN_LABEL = re.compile(r'(\d+)\s*天$')


def check_cleanup(it_doc, tr_doc, cu, only, it_new, tr_new):
    """返回 (errors, warnings)。errors 非空 = 不许落地。"""
    E = []; W = []
    I0 = it_doc['itineraries']; I1 = it_new['itineraries']
    T0 = {t['id']: t for t in tr_doc['trips']}; T1 = {t['id']: t for t in tr_new['trips']}
    nd = lambda k: len(I0[k]['days'])
    for sec in ('renames', 'title_fix', 'sisters', 'covered_by', 'group_city'):
        s = cu.get(sec)
        if not isinstance(s, dict) or not s.get('src') or not s.get('conf'): E.append('[结构] %s 缺 src/conf' % sec)
    if E: return E, W

    # 1 id 都存在
    for sec in ('renames', 'title_fix'):
        for rid in cu[sec]['items']:
            if rid not in I0: E.append('[id] %s 里的 %s 不在 itineraries.json' % (sec, rid))
    for g in cu['sisters']['groups']:
        for rid in g['ids']:
            if rid not in T0: E.append('[id] sisters %s 里的 %s 不在 trips.json' % (g['id'], rid))
        if g['main'] not in g['ids']: E.append('[sisters] %s 的 main %s 不在 ids 里' % (g['id'], g['main']))
        if len(g['ids']) < 2 or len(set(g['ids'])) != len(g['ids']): E.append('[sisters] %s 的 ids 少于 2 个或有重复' % g['id'])
    for rid, v in cu['covered_by']['items'].items():
        for x in (rid, v['to']):
            if x not in T0: E.append('[id] covered_by 里的 %s 不在 trips.json' % x)
    for rid in cu['group_city']['items']:
        if rid not in T0: E.append('[id] group_city 里的 %s 不在 trips.json' % rid)
    missing = [t for t in T0 if t not in cu['group_city']['items']]
    if missing: W.append('[group_city] %d 条线路补丁里没有（补丁之后新增的？）：%s' % (len(missing), missing[:8]))
    if E: return E, W

    # 2 同目的地下标签无重复
    if 'renames' in only:
        d = dup_labels(I1)
        for (dest, lab), ids in d.items(): E.append('[重名] 落地后 %s 下标签「%s」仍有 %s' % (dest, lab, ids))
        for rid, v in cu['renames']['items'].items():
            lab = I1[rid]['label']
            if len(lab) > 18: E.append('[重名] %s 的 label「%s」超过 18 字' % (rid, lab))
            m = DAYS_IN_LABEL.search(lab)
            if not m or int(m.group(1)) != nd(rid): E.append('[天数写法] %s 的 label「%s」没有以“%d 天”结尾' % (rid, lab, nd(rid)))
    # 3 标题天数写法一致
    if 'title_fix' in only:
        for rid, v in cu['title_fix']['items'].items():
            t = I1[rid]['title']
            if not t.startswith(cn(nd(rid)) + '天，'): E.append('[天数写法] %s 标题「%s」应以“%s天，”开头' % (rid, t, cn(nd(rid))))
            if TITLE_DUP.match(t) or TITLE_DIGIT.match(t): E.append('[天数写法] %s 标题「%s」仍是重复/阿拉伯数字写法' % (rid, t))
        left = [k for k, r in I1.items() if TITLE_DUP.match(r['title'])]
        if left: E.append('[天数写法] 落地后仍有 %d 条标题带“N天(…)”：%s' % (len(left), left[:8]))
    if 'renames' in only or 'title_fix' in only:
        for rid in set(cu['renames']['items']) | set(cu['title_fix']['items']):
            if rid not in I1: continue
            k = I1[rid].get('kicker') or ''
            for m in re.finditer(r'(\d+)\s*天', k):
                if int(m.group(1)) != nd(rid): W.append('[kicker] %s 的 kicker「%s」天数与 days=%d 不一致（脚本不改 kicker）' % (rid, k, nd(rid)))
    # 4 姐妹线
    if 'sisters' in only or True:
        seen = {}
        gids = [g['id'] for g in cu['sisters']['groups']]
        if len(set(gids)) != len(gids): E.append('[sisters] 组 id 有重复')
        for g in cu['sisters']['groups']:
            ds = [T0[x]['days'] for x in g['ids'] if x in T0]
            if ds != sorted(ds): E.append('[sisters] %s 的 ids 不是按天数升序：%s' % (g['id'], ds))
            if not g.get('cross_dest'):
                dests = {T0[x]['dest'] for x in g['ids'] if x in T0}
                if len(dests) > 1: E.append('[sisters] %s 跨目的地 %s 但没标 cross_dest' % (g['id'], sorted(dests)))
            for x in g['ids']:
                if x in seen: E.append('[sisters] %s 同时在 %s 和 %s 里' % (x, seen[x], g['id']))
                seen[x] = g['id']
    # 5 covered_by 不成环
    nxt = {rid: v['to'] for rid, v in cu['covered_by']['items'].items()}
    for rid in nxt:
        if nxt[rid] == rid: E.append('[covered_by] %s 指向自己' % rid); continue
        cur = rid; path = [rid]
        while cur in nxt:
            cur = nxt[cur]
            if cur in path: E.append('[covered_by] 成环：%s' % ' → '.join(path + [cur])); break
            path.append(cur)
    # 6 group_city ≤ max_groups
    mg = cu['group_city'].get('max_groups', 12)
    per = collections.defaultdict(set)
    for rid, v in cu['group_city']['items'].items():
        if not isinstance(v.get('g'), str) or not v['g'].strip(): E.append('[group_city] %s 的分组名为空' % rid); continue
        if rid in T0: per[T0[rid]['dest']].add(v['g'])
    for dest, gs in per.items():
        if len(gs) > mg: E.append('[group_city] %s 有 %d 个城市分组（上限 %d）' % (dest, len(gs), mg))
    # 7 只改了该改的字段（没改到 id/天数/站点）
    if list(I0) != list(I1): E.append('[不变量] itineraries 的线路 id 集合/顺序变了')
    for k in I0:
        a = {f: v for f, v in I0[k].items() if f not in ('label', 'title')}
        b = {f: v for f, v in I1[k].items() if f not in ('label', 'title')}
        if a != b: E.append('[不变量] %s 的 label/title 之外的字段变了' % k)
    if [t['id'] for t in tr_doc['trips']] != [t['id'] for t in tr_new['trips']]: E.append('[不变量] trips 的 id 集合/顺序变了')
    for k in T0:
        a = {f: v for f, v in T0[k].items() if f not in ('title', 'headline') + MANAGED}
        b = {f: v for f, v in T1[k].items() if f not in ('title', 'headline') + MANAGED}
        if a != b: E.append('[不变量] trips %s 的 title/headline/新字段 之外的字段变了' % k)
        if T1[k]['days'] != T0[k]['days']: E.append('[不变量] trips %s 天数变了' % k)
    for k in I0:
        if k in T0 and T0[k]['days'] != nd(k): W.append('[天数] %s trips.days=%s 与 itineraries 天数 %d 不一致（落地前就是这样）' % (k, T0[k]['days'], nd(k)))
    return E, W


def load_cleanup(path):
    cu = json.load(open(path, encoding='utf-8'))
    return cu


def run_check(it_doc, tr_doc, cu, only):
    it_new, tr_new, ch, notes = plan(it_doc, tr_doc, cu, only)
    E, W = check_cleanup(it_doc, tr_doc, cu, only, it_new, tr_new)
    return E, W, ch, notes, it_new, tr_new


# ---------------------------------------------------------------- 反向注入自检
def selftest(it_doc, tr_doc, cu):
    I = it_doc['itineraries']
    cases = []

    def mut(name, key, fn):
        c = copy.deepcopy(cu); fn(c); cases.append((name, key, c))
    # 1 两条线重名：同目的地、不同组的两条改成同一个标签
    def dup(c):
        a, b = 'sz2x', 'zj2b'
        assert I[a]['dest'] == I[b]['dest']
        c['renames']['items'][b]['label'] = c['renames']['items'][a]['label']
    mut('两条线重名', '[重名]', dup)
    # 2 天数写法不一致：标题改成阿拉伯数字+括号 / 汉字天数与 days 不符
    def d1(c):
        k = next(iter(c['title_fix']['items'])); c['title_fix']['items'][k]['title'] = '%d天(%s)，x' % (len(I[k]['days']), cn(len(I[k]['days'])))
    mut('天数写法不一致（5天(五天)）', '[天数写法]', d1)
    def d2(c):
        k = next(iter(c['title_fix']['items'])); c['title_fix']['items'][k]['title'] = cn(len(I[k]['days']) + 1) + '天，x'
    mut('天数写法不一致（天数对不上）', '[天数写法]', d2)
    # 3 sisters 含不存在 id
    mut('sisters 含不存在的 id', '[id]', lambda c: c['sisters']['groups'][0]['ids'].append('zz_not_exist'))
    # 4 covered_by 成环
    def cyc(c):
        c['covered_by']['items']['cq3']['to'] = 'cq4d'
        c['covered_by']['items']['cq4d'] = {'to': 'cq3', 'apply': True}
    mut('covered_by 成环', '[covered_by] 成环', cyc)
    # 5 group_city 超 12 个
    def many(c):
        ids = [r for r, v in c['group_city']['items'].items() if I.get(r, {}).get('dest') == 'sichuan'][:14]
        for i, r in enumerate(ids): c['group_city']['items'][r] = {'g': '城%d' % i, 'how': 'inject'}
    mut('group_city 超 12 个', '[group_city]', many)
    # 附加：改到不该改的东西（把 label 之外的站点改了）——plan 不会做，这里直接验不变量检测器本身会红
    rows = []; ok = True
    E, W, ch, notes, itn, trn = run_check(it_doc, tr_doc, cu, set(SECTIONS))
    rows.append(('基线（原补丁）', '应无错误', 'PASS' if not E else 'FAIL ' + str(E[:2])))
    ok &= not E
    for name, key, c in cases:
        E, W, *_ = run_check(it_doc, tr_doc, c, set(SECTIONS))
        hit = any(key in e for e in E)
        rows.append((name, key, 'PASS（报错 %d 条，首条：%s）' % (len(E), E[0][:60]) if hit else 'FAIL（没报出 %s；实际错误 %s）' % (key, E[:1])))
        ok &= hit
    # 不变量检测器：构造一个“落地后改了站点”的 it_new，检测函数必须红
    itn2 = copy.deepcopy(itn); k = next(iter(itn2['itineraries'])); itn2['itineraries'][k]['days'][0]['stops'].pop()
    E2, _ = check_cleanup(it_doc, tr_doc, cu, set(SECTIONS), itn2, trn)
    hit = any('[不变量]' in e for e in E2)
    rows.append(('落地后改了站点', '[不变量]', 'PASS' if hit else 'FAIL')); ok &= hit
    # 幂等：对落地后的结果再 plan 一次必须零变化
    _, _, ch2, _ = plan(itn, trn, cu, set(SECTIONS))
    rows.append(('幂等（第二次 plan）', '零变化', 'PASS' if not ch2 else 'FAIL（还有 %d 处变化）' % len(ch2))); ok &= not ch2
    # 逆向：落地后 revert 回到落地前
    itr, trr, _, _ = plan(itn, trn, cu, set(SECTIONS), revert=True)
    same = dumps(itr) == dumps(it_doc) and dumps(trr) == dumps(tr_doc)
    rows.append(('apply→revert 与原文件逐字节相同', '回滚', 'PASS' if same else 'FAIL')); ok &= same
    for r in rows: print('%-28s %-16s %s' % r)
    print('SELFTEST', 'OK' if ok else 'FAILED')
    return 0 if ok else 1


# ---------------------------------------------------------------- 输出
def summarize(ch, notes, tsv=None, verbose=False):
    by = collections.Counter((c[5], c[0], c[2]) for c in ch)
    for (sec, f, fld), n in sorted(by.items()): print('  %-10s %-16s %-10s %d 处' % (sec, f, fld, n))
    print('  合计 %d 处改动，涉及 %d 条线路' % (len(ch), len({c[1] for c in ch})))
    shown = collections.Counter()
    for c in ch:
        if verbose or shown[c[5]] < 6:
            print('   [%s] %s %s.%s：%s → %s' % (c[5], c[0][:4], c[1], c[2], c[3], c[4])); shown[c[5]] += 1
    if not verbose and len(ch) > sum(shown.values()): print('   …（每段只列前 6 条；--tsv 写全表，-v 打印全部）')
    for n in notes: print('  注意：' + n)
    if tsv:
        with open(tsv, 'w', encoding='utf-8') as fh:
            fh.write('段\t文件\tid\t字段\t旧\t新\n')
            for c in ch: fh.write('\t'.join([c[5], c[0], c[1], c[2], str(c[3]).replace('\t', ' '), str(c[4]).replace('\t', ' ')]) + '\n')
        print('  前后表：' + tsv)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--data-dir', default=os.path.join(ROOT, 'data'))
    ap.add_argument('--cleanup'); ap.add_argument('--only'); ap.add_argument('--tsv')
    ap.add_argument('--dry', action='store_true'); ap.add_argument('--check', action='store_true')
    ap.add_argument('--selftest', action='store_true'); ap.add_argument('--revert', action='store_true')
    ap.add_argument('--from-backup', nargs='?', const='latest'); ap.add_argument('-v', action='store_true')
    a = ap.parse_args()
    only = parse_only(a.only)
    st = Store(os.path.abspath(a.data_dir)).read()
    cpath = a.cleanup or (os.path.join(st.dir, 'catalog', 'route_cleanup.json') if os.path.exists(os.path.join(st.dir, 'catalog', 'route_cleanup.json')) else os.path.join(ROOT, 'data', 'catalog', 'route_cleanup.json'))
    cu = load_cleanup(cpath)
    print('数据：%s　补丁：%s　范围：%s' % (st.dir, cpath, ','.join(s for s in SECTIONS if s in only)))
    if not st.fmt_ok:
        print('停止：itineraries.json / trips.json 重新序列化后与原文件不是逐字节一致，落地会整文件重排。先查原因。'); return 2

    if a.selftest: return selftest(st.it_doc, st.tr_doc, cu)

    if a.revert and a.from_backup:
        ts = a.from_backup
        subs = sorted(os.listdir(st.backup_root)) if os.path.isdir(st.backup_root) else []
        if not subs: print('没有备份'); return 2
        print('可用快照：' + '  '.join(subs))
        if ts == 'latest':
            # 默认回到“第一次落地之前”的原始状态：最早的那份 kind=apply 的快照
            ts = next((x for x in subs if json.load(open(os.path.join(st.backup_root, x, 'MANIFEST.json'))).get('kind') == 'apply'), subs[0])
        d = os.path.join(st.backup_root, ts)
        man = json.load(open(os.path.join(d, 'MANIFEST.json')))
        raw_it = open(os.path.join(d, 'itineraries.json'), encoding='utf-8').read(); raw_tr = open(os.path.join(d, 'trips.json'), encoding='utf-8').read()
        assert sha(raw_it) == man['sha256']['itineraries.json'] and sha(raw_tr) == man['sha256']['trips.json'], '备份文件与 MANIFEST 指纹不一致'
        print('整文件还原到快照 %s（会丢掉快照之后别人对这两个文件的改动！）' % ts)
        if a.dry: return 0
        st.snapshot('revert-full'); st.write(json.loads(raw_it), json.loads(raw_tr)); print('已还原'); return 0

    if a.revert:
        it_new, tr_new, ch, notes = plan(st.it_doc, st.tr_doc, cu, only, revert=True)
        print('逆向补丁（只改回补丁改过的字段）：')
        summarize(ch, notes, a.tsv, a.v)
        if a.dry or not ch: print('（dry/无变化，未写文件）' if ch else '无变化'); return 0
        d = st.snapshot('revert'); st.write(it_new, tr_new); print('已还原；还原前快照在 ' + d); return 0

    E, W, ch, notes, it_new, tr_new = run_check(st.it_doc, st.tr_doc, cu, only)
    print('将要改：' if (a.dry or a.check) else '改动：')
    summarize(ch, notes, a.tsv, a.v)
    for w in W[:20]: print('  警告：' + w)
    if len(W) > 20: print('  …警告共 %d 条' % len(W))
    if E:
        print('校验失败（%d）：' % len(E))
        for e in E[:30]: print('  ✗ ' + e)
        return 1
    drift = [n for n in notes if n.startswith('漂移')]
    if a.check:
        print('CHECK OK' + ('（有 %d 条漂移跳过，补丁与现状已不同步）' % len(drift) if drift else '')); return 1 if drift else 0
    if a.dry: print('DRY：没有写任何文件'); return 0
    if not ch: print('无变化（已经是落地后的状态），未重写文件'); return 0
    d = st.snapshot(); st.write(it_new, tr_new)
    st2 = Store(st.dir).read()
    _, _, ch2, _ = plan(st2.it_doc, st2.tr_doc, cu, only)
    assert not ch2, '落地后再 plan 仍有变化，幂等性被破坏'
    print('已落地；备份在 %s；落地后 itineraries sha=%s trips sha=%s' % (d, sha(st2.raw_it)[:12], sha(st2.raw_tr)[:12]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
