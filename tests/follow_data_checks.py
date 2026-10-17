#!/usr/bin/env python3
"""「跟谁走」专栏的数据闸（2026-10-17）。tests/data_checks.py 第 32 项调用它；也可以单独跑。

用法（项目根目录）：
    python3 tests/follow_data_checks.py [建好的站目录]        # 不给站目录只查数据（①②④⑤的数据部分）；任一红退出码 1
    python3 tests/follow_data_checks.py build/site --inject 名字   # 反向自检：在内存里故意弄坏一处，必须变红（不改磁盘）
    python3 tests/follow_data_checks.py build/site --selftest      # 把所有注入都跑一遍，每个都得红，否则退出码 2

判据（数据来源 data/history/*.json、data/catalog/trips.json、data/itineraries.json、建好的站）：
 ① 每个主题的 routes 都在 itineraries 里、页面 /trip/<id>/ 存在、/follow/<主题>/ 存在且链到它；_registry.json 和主题文件一致
 ② notes 的每个键都等于该主题某条线路里某个 stop.name（对不上就红；两种布局入库时已合并到顶层）
 ③ 审计字段不外泄：data 里所有 src 的原文，不得出现在 /follow/、主题线路页、tidx.js、llms.txt、/all/ 里（不是数“src”三个字母，页面里 <img src> 太多）
 ④ 评价性/煽动性词表：line、intro、tagline、年表的 what 里出现就红（词表在 BAD_WORDS，发现新的就补）
 ⑤ /follow/ 页面必须包含 trips.json 里所有带 follow 字段的线路（从数据反查：每个主题页链到它的每条线；follow 指向不存在的主题也红）
 ⑥ 每个主题至少含 1 个 博物馆|博物院|纪念馆|故居|遗址|陈列馆|旧址|纪念园|祠|陵 类站点（type=museum 或名字含词）；缺了只给警告清单，不拦
 ⑦ 注释真的落到了页面上：每条 note 的“名字：句子”至少出现在该主题某条线路页的 p.fnote 里（站点名对上了、但行没匹配上也会红）
 ⑧ 主题线路里 type=museum 的站，页面行上带 data-mc="1"（周一红字提醒的挂点）
"""
import html as _html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ARGV = sys.argv[1:]
SITE = next((a for a in ARGV if not a.startswith('--') and os.path.isdir(a)), None)
INJECT = ARGV[ARGV.index('--inject') + 1] if '--inject' in ARGV else None

BAD_WORDS = ['暴君', '昏君', '英明', '伟大', '残暴', '血腥屠杀', '罪恶', '英雄壮举', '永垂不朽',
             '千古一帝', '千古罪人', '一代明君', '明君', '圣君', '暴政', '暴虐', '丰功伟绩', '功勋卓著', '民族英雄', '盖世英雄', '一代英雄',
             '雄才大略', '杰出', '卓越', '光辉', '崇高', '不朽', '丰碑', '万古流芳', '流芳百世', '遗臭', '屠夫', '独夫', '奸臣', '奸雄', '卖国', '汉奸',
             '反动', '凶残', '血雨腥风', '歌颂', '赞颂', '讴歌', '光荣', '神圣', '英勇', '壮烈', '悲壮', '惨无人道', '令人发指', '罪行', '恶行', '最伟大', '最杰出', '最著名']
BAD_RE = re.compile('|'.join(map(re.escape, BAD_WORDS)))
_NB = re.compile(r'(\d) (天|晚|月|日|处|条|家|个|人)')    # 和 build_site._NB 同一条
MUS_RE = re.compile(r'博物馆|博物院|纪念馆|故居|遗址|陈列馆|旧址|纪念园|祠|陵')


class State: pass


def load():
    S = State()
    S.hist = {}
    for f in sorted(os.listdir('data/history')) if os.path.isdir('data/history') else []:
        if not f.endswith('.json') or f.startswith('_'): continue
        h = json.load(open(os.path.join('data/history', f), encoding='utf-8')); S.hist[h['id']] = h
    S.reg = json.load(open('data/history/_registry.json', encoding='utf-8')) if os.path.exists('data/history/_registry.json') else {}
    S.it = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
    S.trips = json.load(open('data/catalog/trips.json', encoding='utf-8'))['trips']
    S.pages = {}
    return S


def page(S, path):
    """站里的页面文本（缓存；注入时可以改 S.pages）。没有站或文件不在返回 None"""
    if not SITE: return None
    if path not in S.pages:
        f = os.path.join(SITE, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(SITE, path.strip('/'))
        S.pages[path] = open(f, encoding='utf-8').read() if os.path.exists(f) else None
    return S.pages[path]


def stop_names(S, tid):
    return {s['name'] for r in S.hist[tid].get('routes') or [] if r in S.it for d in S.it[r]['days'] for s in d['stops']}


def check1(S):
    bad = []
    for tid, h in S.hist.items():
        if not h.get('routes'): bad.append(f'[{tid}] 没有线路')
        for r in h.get('routes') or []:
            if r not in S.it: bad.append(f'[{tid}] 线路 {r} 不在 data/itineraries.json'); continue
            if SITE and page(S, f'/trip/{r}/') is None: bad.append(f'[{tid}] 线路页 /trip/{r}/ 不存在')
        if SITE:
            fp = page(S, f'/follow/{tid}/')
            if fp is None: bad.append(f'[{tid}] 主题页 /follow/{tid}/ 不存在'); continue
            for r in h.get('routes') or []:
                if f'href="/trip/{r}/"' not in fp: bad.append(f'[{tid}] 主题页没有链到线路 {r}')
            ix = page(S, '/follow/')
            if ix is None or f'href="/follow/{tid}/"' not in ix: bad.append(f'[{tid}] /follow/ 目录里没有这个主题')
    for tid, rs in S.reg.items():
        if tid in S.hist and sorted(rs) != sorted(S.hist[tid].get('routes') or []): bad.append(f'[{tid}] _registry.json 和主题文件的线路不一致')
    return bad


def check2(S):
    bad = []
    for tid, h in S.hist.items():
        names = stop_names(S, tid)
        for k in (h.get('notes') or {}):
            if k not in names: bad.append(f'[{tid}] 注释的站点名「{k}」不等于该主题任何线路里的 stop.name')
    return bad


def content_text(S):
    out = []
    for h in S.hist.values():
        out += [h.get('tagline') or '', h.get('intro') or ''] + [(x.get('what') or '') + (x.get('where') or '') for x in h.get('timeline') or []] + [v.get('line') or '' for v in (h.get('notes') or {}).values()]
    return ''.join(out)


def srcs(S):
    """所有审计字段的原文。原文碰巧就是正文里写的一个词（课文名、书名）的不算：那是正文，不是泄露；正文块本身另有“p.fnote 必须逐字等于 名字：line”这条把关"""
    out = set()
    for h in S.hist.values():
        for v in (h.get('notes') or {}).values():
            if v.get('src'): out.add(v['src'].strip())
        for x in h.get('timeline') or []:
            if x.get('src'): out.add(x['src'].strip())
    ct = content_text(S)
    return {s for s in out if len(s) >= 4 and s not in ct}


def expected_notes(S, tid):
    h = S.hist[tid]; nm = re.sub(r'[（(].*?[）)]', '', h.get('name') or tid).strip() or tid; out = {}
    for k, v in (h.get('notes') or {}).items():
        line = (v.get('line') or '').strip().rstrip('。')
        if not line: continue
        if v.get('conf') == 'medium' and '相传' not in line: line = '相传' + line
        out[k] = _html.escape(_NB.sub('\\1\u00a0\\2', f'{nm}：{line}'))     # 页面里 E() 会把“1 月”这类数字+单位中间的空格换成不换行空格
    return out


def check3(S):
    """/follow/、tidx、llms、/all/ 里整页查；线路页只查我们加进去的两块（p.fnote、a.fbn）——线路本身的文字（课文名、书名）可能碰巧和某条 src 一样，不是泄露"""
    if not SITE: return []
    bad = []; ss = srcs(S)
    whole = ['/follow/', '/all/', '/llms.txt', '/assets/tidx.js'] + [f'/follow/{t}/' for t in S.hist]
    trips = [f'/trip/{r}/' for h in S.hist.values() for r in h.get('routes') or []]
    HOF = {r: tid for tid, h in S.hist.items() for r in h.get('routes') or []}
    def leak(p, t):
        for s in ss:
            if s in t or _html.escape(s) in t or _html.escape(s, quote=False) in t: return s
    for p in whole:
        t = page(S, p)
        if not t: continue
        s = leak(p, t)
        if s: bad.append(f'{p} 里出现了审计字段「{s[:30]}」')
    for p in trips:
        t = page(S, p)
        if not t: continue
        want = set(expected_notes(S, HOF[p.split('/')[2]]).values()) if p.split('/')[2] in HOF else set()
        for g in re.findall(r'<p class="fnote">(.*?)</p>', t, re.S):
            if g not in want: bad.append(f'{p} 有一块站点注释不是“名字：line”原文：{g[:40]}')
        mine = ' '.join(re.findall(r'<p class="fnote">.*?</p>|<a class="fbn".*?</a>', t, re.S))
        s = leak(p, mine)
        if s: bad.append(f'{p} 的站点注释/横幅里出现了审计字段「{s[:30]}」')
        if re.search(r'"src"\s*:', t): bad.append(f'{p} 里有 "src": 字段')
    return bad


def check4(S):
    bad = []
    for tid, h in S.hist.items():
        for where, txt in [('tagline', h.get('tagline')), ('intro', h.get('intro'))] + [(f'年表 {x.get("when")}', x.get('what')) for x in h.get('timeline') or []] + [(f'注释「{k}」', v.get('line')) for k, v in (h.get('notes') or {}).items()]:
            m = BAD_RE.search(txt or '')
            if m: bad.append(f'[{tid}] {where} 含评价性词「{m.group(0)}」：{(txt or "")[:40]}')
    return bad


def check5(S):
    bad = []
    fol = [t for t in S.trips if t.get('follow')]
    for t in fol:
        if t['follow'] not in S.hist: bad.append(f'trips.json 里 {t["id"]} 的 follow={t["follow"]} 没有对应的主题文件'); continue
        if SITE:
            fp = page(S, f'/follow/{t["follow"]}/')
            if fp is None or f'href="/trip/{t["id"]}/"' not in fp: bad.append(f'/follow/{t["follow"]}/ 里没有 follow 线路 {t["id"]}')
    if SITE and S.hist and not fol: bad.append('trips.json 里没有任何带 follow 的线路，判据可能失效')
    ids = {t['id'] for t in fol}
    for tid, h in S.hist.items():
        for r in h.get('routes') or []:
            if r not in ids: bad.append(f'[{tid}] 线路 {r} 在 trips.json 里没有 follow 标记')
    return bad


def warn6(S):
    out = []
    for tid, h in S.hist.items():
        ok = False
        for r in h.get('routes') or []:
            for d in (S.it.get(r) or {}).get('days') or []:
                for s in d['stops']:
                    if s.get('type') == 'museum' or MUS_RE.search(s['name']): ok = True
        if not ok: out.append(f'{tid}（{h.get("name")}）')
    return out


def check7(S):
    if not SITE: return []
    bad = []
    for tid, h in S.hist.items():
        pages = [(r, page(S, f'/trip/{r}/')) for r in h.get('routes') or []]
        for k, want in expected_notes(S, tid).items():
            if not any(t and ('<p class="fnote">' + want + '</p>') in t for _, t in pages): bad.append(f'[{tid}]「{k}」的注释没有出现在任何线路页上')
    return bad


def check8(S):
    if not SITE: return []
    bad = []
    for tid, h in S.hist.items():
        for r in h.get('routes') or []:
            n = sum(1 for d in (S.it.get(r) or {}).get('days') or [] for s in d['stops'] if s.get('type') == 'museum')
            t = page(S, f'/trip/{r}/')
            if t is None or not n: continue
            got = len(re.findall(r'data-mc="1"', t))
            if got < n: bad.append(f'{r}：有 {n} 个 museum 站，页面上带 data-mc 的只有 {got} 行')
    return bad


CHECKS = [('① 线路和页面都在', check1), ('② 注释的站点名对得上', check2), ('③ 审计字段 src 不外泄', check3), ('④ 评价性/煽动性词', check4), ('⑤ /follow/ 含全部 follow 线路', check5),
          ('⑦ 注释落到页面上', check7), ('⑧ museum 站带周一提醒挂点', check8)]


def inject(S, name):
    """在内存里弄坏一处；返回应该变红的判据前缀"""
    tid = sorted(S.hist)[0]; h = S.hist[tid]
    if name == 'note_key':
        k = next(iter(h['notes'])); h['notes']['不存在的站点名'] = h['notes'].pop(k); return '② '
    if name == 'src_leak':
        s = next(iter(srcs(S))); p = f'/follow/{tid}/'; page(S, p); S.pages[p] = (S.pages[p] or '') + f'<p>{s}</p>'; return '③ '
    if name == 'bad_word': h['intro'] = (h.get('intro') or '') + '他是一位暴君。'; return '④ '
    if name == 'missing_trip':
        r = h['routes'][0]; p = f'/follow/{tid}/'; page(S, p); S.pages[p] = (S.pages[p] or '').replace(f'href="/trip/{r}/"', 'href="/nowhere/"'); return '⑤ '
    if name == 'route_missing': h['routes'].append('nonexistent_route_x'); return '① '
    if name == 'note_dropped':
        for r in h['routes']:
            p = f'/trip/{r}/'; page(S, p)
            if S.pages.get(p): S.pages[p] = S.pages[p].replace('class="fnote"', 'class="gone"')
        return '⑦ '
    if name == 'mc_dropped':
        for r in [r for hh in S.hist.values() for r in hh['routes']]:
            p = f'/trip/{r}/'; page(S, p)
            if S.pages.get(p): S.pages[p] = S.pages[p].replace('data-mc="1"', '')
        return '⑧ '
    raise SystemExit('没有这个注入：' + name)


INJECTS = ['note_key', 'src_leak', 'bad_word', 'missing_trip', 'route_missing', 'note_dropped', 'mc_dropped']


def run(S):
    fails = []
    for title, fn in CHECKS:
        bad = fn(S)
        if bad: fails.append((title, bad))
    return fails


def main():
    if '--selftest' in ARGV:
        if not SITE: print('--selftest 要给站目录'); return 2
        bad = 0
        for nm in INJECTS:
            S = load(); pref = inject(S, nm); f = run(S)
            hit = [t for t, _ in f if t.startswith(pref)]
            print(('红（正确）' if hit else '没红（判据有洞）'), '·', nm, '→', hit[:1])
            if not hit: bad += 1
        S = load(); base = run(S)
        print('不注入时：', '全绿' if not base else '红 ' + str([t for t, _ in base]))
        return 2 if bad else 0
    S = load()
    pref = inject(S, INJECT) if INJECT else None
    if not S.hist:
        print('data/history 里没有主题（还没入库？）'); return 0 if not SITE else 1
    fails = run(S)
    w = warn6(S)
    if w: print(f'警告（不拦）⑥ 这 {len(w)} 个主题没有 博物馆/纪念馆/故居/遗址/陈列馆/旧址/纪念园/祠/陵 类站点：' + '、'.join(w))
    if INJECT:
        hit = [t for t, _ in fails if t.startswith(pref)]
        print(('红（正确）' if hit else '没红（判据有洞）'), '·', INJECT, '→', hit[:1]); return 0 if hit else 2
    for title, bad in fails:
        print(f'✗ 跟谁走 {title}：{len(bad)} 处')
        for x in bad[:30]: print('   ', x)
    if fails: return 1
    print(f'跟谁走数据闸全部通过（{len(S.hist)} 个主题，{sum(len(h.get("routes") or []) for h in S.hist.values())} 条线路' + ('' if SITE else '；没给站目录，页面项未查') + '）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
