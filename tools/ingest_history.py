# 用法（项目根目录）：
#   python3 tools/ingest_history.py            全量：读 build/history/*.json（跳过 chk_*、research_*、_*），每个主题重新入库
#   python3 tools/ingest_history.py --only sushi [--only kangxi ...]    只重做指定主题（主题 id = 文件里的 id）
#   python3 tools/ingest_history.py --dry      只校验、列清单，不写任何文件
# 做什么（专栏“跟谁走”的入库，2026-10-17）：
#   1 先清掉上次由本工具入库的该主题线路（data/history/_registry.json 记着每个主题入库了哪些线路 id），再重新入库——所以可以反复跑、不留重复
#   2 每条线路过 tools/check_new_routes.py（id 重复以外的错必须为零），不过的线路只跳过该线路并列出原因，不让整次失败
#   3 写 data/auto_routes/history_<主题id>.json，再交 tools/add_routes_json.py（itineraries / trips / destinations / pois / SIGHT / DEEP；start 月份由它转 0 起算，这里不转）
#   4 trips.json 里这些线路多一个 follow=<主题id>（数据闸 5 从它反查）
#   5 data/history/<主题id>.json：{id,kind,name,tagline,intro,timeline[{when,where,what,src}],routes[线路id],notes{站点名:{line,src,conf}}}
#     notes 有两种布局：主题顶层 notes，或每条线路对象里的 routes[i].notes——两种都读，合并到顶层。src 只留在 data 里供审计，页面绝不显示。
# 线路 id 若和“不是本主题入库的”现有线路冲突：该线路报错并跳过（不覆盖旧线）。
import json, sys, os, re, glob, subprocess, copy

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SRC_DIR, HIST_DIR, AUTO_DIR = 'build/history', 'data/history', 'data/auto_routes'
IT_P, TR_P, DS_P = 'data/itineraries.json', 'data/catalog/trips.json', 'data/destinations.json'
REG_P = os.path.join(HIST_DIR, '_registry.json')
load = lambda p: json.load(open(p, encoding='utf-8'))


def dump(o, p):
    json.dump(o, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def source_files():
    out = []
    for f in sorted(glob.glob(os.path.join(SRC_DIR, '*.json'))):
        b = os.path.basename(f)
        if b.startswith(('chk_', 'research_', '_')): continue
        out.append(f)
    return out


def merge_notes(d):
    """顶层 notes 和 routes[i].notes 合并（同名站点后者不覆盖前者）；返回 {站点名: {line, src, conf}}"""
    notes = {}
    for k, v in (d.get('notes') or {}).items(): notes[k] = v
    for r in d.get('routes') or []:
        for k, v in (r.get('notes') or {}).items(): notes.setdefault(k, v)
    return notes


def main():
    args = sys.argv[1:]
    only = [args[i + 1] for i, a in enumerate(args) if a == '--only' and i + 1 < len(args)]
    dry = '--dry' in args
    os.makedirs(HIST_DIR, exist_ok=True)
    reg = load(REG_P) if os.path.exists(REG_P) else {}
    topics = {}
    for f in source_files():
        try: d = load(f)
        except Exception as e:
            print('✗', f, 'JSON 读不出', e); continue
        if not isinstance(d, dict) or not d.get('id') or not isinstance(d.get('routes'), list):
            print('✗', f, '不是主题文件（缺 id / routes），跳过'); continue
        if d['id'] in topics: print('✗', f, '主题 id 重复', d['id'], '，跳过'); continue
        topics[d['id']] = d
    todo = sorted(topics) if not only else [t for t in only if t in topics]
    for t in only:
        if t not in topics: print('✗ --only', t, '在 build/history 里找不到')
    IT, TR, DS = load(IT_P), load(TR_P), load(DS_P)
    dest_ids = {x['id'] for k in ('domestic', 'asia', 'world') for x in DS[k]}
    owner_other = lambda rid, tid: any(rid in v for k, v in reg.items() if k != tid)
    report = []          # (主题, 线路, 原因)
    plans = {}           # 主题 -> [路线对象]
    # 1 校验（在内存里先把本主题旧线路当作“不存在”）
    for tid in todo:
        d = topics[tid]; mine = set(reg.get(tid, [])); ok = []; seen = set()
        for r in d['routes']:
            rid = r.get('id')
            if not isinstance(rid, str) or not rid: report.append((tid, rid, '缺 id')); continue
            if rid in seen: report.append((tid, rid, '主题内 id 重复')); continue
            seen.add(rid)
            if (rid in IT['itineraries'] or any(t['id'] == rid for t in TR['trips'])) and rid not in mine:
                report.append((tid, rid, '线路 id 与现有线路冲突（不是本主题入库的），没有覆盖')); continue
            if owner_other(rid, tid): report.append((tid, rid, '线路 id 已属于别的主题')); continue
            if r.get('dest') not in dest_ids: report.append((tid, rid, f'dest「{r.get("dest")}」不在 destinations.json')); continue
            if not all(isinstance(dd.get('text'), str) for dd in r.get('days') or []): report.append((tid, rid, 'days[].text 必须是字符串')); continue
            o = copy.deepcopy(r)
            for k in ('video', 'notes', 'follow'): o.pop(k, None)
            ok.append(o)
        # check_new_routes（id 重复以外的错必须为零）：逐条单独检查，不过的只跳过该条
        good = []
        for o in ok:
            tmp = os.path.join(AUTO_DIR, f'_chk_{tid}_{o["id"]}.json'); dump([o], tmp)
            out = subprocess.run([sys.executable, 'tools/check_new_routes.py', tmp], capture_output=True, text=True).stdout
            os.remove(tmp)
            errs = [l.strip() for l in out.splitlines() if l.startswith('    ') and 'id 重复' not in l]
            if errs: report.append((tid, o['id'], '; '.join(errs[:6]))); continue
            good.append(o)
        plans[tid] = good
    if dry:
        for tid in todo: print('主题', tid, d_name(topics[tid]), '可入库', [o['id'] for o in plans[tid]])
        show(report); return 1 if report else 0
    # 2 清掉旧线路（只清本次要重做的主题）
    removed = []
    for tid in todo:
        for rid in reg.get(tid, []):
            if rid in IT['itineraries']: del IT['itineraries'][rid]; removed.append(rid)
            TR['trips'] = [t for t in TR['trips'] if t['id'] != rid]
            for k in ('domestic', 'asia', 'world'):
                for x in DS[k]:
                    if rid in (x.get('routes') or []): x['routes'] = [y for y in x['routes'] if y != rid]
        reg[tid] = []
    dump(IT, IT_P); dump(TR, TR_P); dump(DS, DS_P)
    # 3 写 auto_routes，一次交给 add_routes_json
    files = []
    for tid in todo:
        p = os.path.join(AUTO_DIR, f'history_{tid}.json')
        if plans[tid]: dump(plans[tid], p); files.append(p)
        elif os.path.exists(p): os.remove(p)
    if files:
        out = subprocess.run([sys.executable, 'tools/add_routes_json.py'] + files, capture_output=True, text=True)
        print((out.stdout.strip().splitlines() or [out.stderr[-300:]])[-1])
        if out.returncode != 0: print(out.stderr[-600:]); return 1
    IT, TR = load(IT_P), load(TR_P)
    # 4 登记、trips.follow、data/history
    for tid in todo:
        d = topics[tid]; got = [o['id'] for o in plans[tid] if o['id'] in IT['itineraries']]
        for o in plans[tid]:
            if o['id'] not in IT['itineraries']: report.append((tid, o['id'], 'add_routes_json 没写进去'))
        reg[tid] = got
        for t in TR['trips']:
            if t['id'] in got: t['follow'] = tid
        notes = merge_notes(d)
        # 注释的站点名要等于某条线路里的 stop.name。属于“被跳过的线路”的注释一并不入库（线路没了，注释没意义，已在上面报过）；完全对不上任何线路的留在 data 里，让数据闸 2 变红
        names_ok = {s['name'] for o in plans[tid] for dd in o['days'] for s in dd['stops']}
        names_all = {s['name'] for r in d['routes'] for dd in (r.get('days') or []) for s in dd.get('stops') or []}
        for k in [k for k in notes if k not in names_ok and k in names_all]:
            del notes[k]; report.append((tid, k, '注释属于被跳过的线路，没有入库'))
        for k in notes:
            if k not in names_ok: report.append((tid, k, '注释的站点名对不上任何线路的 stop.name（数据闸 2 会红，请内容 agent 改）'))
        dump({'id': tid, 'kind': d.get('kind') or 'person', 'name': d.get('name') or tid, 'tagline': d.get('tagline') or '', 'intro': d.get('intro') or '',
              'timeline': [{k: x.get(k, '') for k in ('when', 'where', 'what', 'src')} for x in d.get('timeline') or []],
              'routes': got, 'notes': notes}, os.path.join(HIST_DIR, tid + '.json'))
    dump(TR, TR_P)
    dump({k: reg[k] for k in sorted(reg)}, REG_P)
    for tid in todo: print('主题', tid, d_name(topics[tid]), '入库', reg[tid])
    print('清掉旧线路', len(removed), '条；本次入库', sum(len(reg[t]) for t in todo), '条')
    show(report)
    return 0


def d_name(d): return d.get('name') or d.get('id')


def show(report):
    if not report: return
    print('\n没入库的线路（只跳过这一条）：')
    for tid, rid, why in report: print(f'  ✗ [{tid}] {rid}：{why}')


if __name__ == '__main__':
    sys.exit(main())
