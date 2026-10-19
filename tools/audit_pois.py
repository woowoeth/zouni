#!/usr/bin/env python3
"""pois.json 坐标系统性审计（2026-10-19，起因：'西安|西安城墙永宁门' q 写成泛称、坐标落在西城墙桥梓口）。

用法（项目根目录）：
  python3 tools/audit_pois.py                 # 只审计：写 build/audit_pois.csv，打印各规则命中数
  python3 tools/audit_pois.py --verify 300    # 对引用最多的前 N 条命中项用 Nominatim 核实 → 生成 build/audit_pois_plan.json
                                              #   + build/audit_pois_unsure.csv（拿不准的，留给人）
  python3 tools/audit_pois.py --apply         # 把 plan 里“有明确证据”的写进 data/geo/pois.json（先备份）

规则（pois 键 = 当天 city + '|' + q）：
  a  q 缺专名：站名里有“某某门/寺/塔/馆…”（专名），q 里却没有这个专名（只写泛称）
  b  hit 里没有站名核心词（仅对真实地址型 hit；“人工核对（近似）”这类没有地址的跳过）
  c  坐标离当天城市中心过远：c1 > 40 公里；c2 > 120 公里且站名里没有郊区地名（区/县/镇…）
  d  同一坐标（3 位小数，约 100 米）被 >= 4 个不同站名共用（占位坐标）
  e  站名里的区/县/镇/乡/旗名，在 hit 里的行政区中找不到
改坐标的证据门槛：Nominatim 返回的 name 与站名某一专名部分精确相等、是点状要素（包围盒对角线 <= 1.2 公里）、
  不是车站/道路、离城市中心 <= 60 公里（防同名远处）、离现坐标 > 1.5 公里、同名候选之间互相 <= 1.5 公里（否则拿不准）、
  且共用该键的所有站名都含这个专名。
Nominatim：1 请求/秒，User-Agent 带 zouni，结果缓存到 build/audit_cache.json。用 curl（本机 python urllib 的 HTTPS 会证书失败）。
"""
import csv, json, math, os, re, subprocess, sys, time, urllib.parse
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
GP = 'data/geo/pois.json'
CSV = 'build/audit_pois.csv'
CACHE = 'build/audit_cache.json'
PLAN = 'build/audit_pois_plan.json'
UNSURE = 'build/audit_pois_unsure.csv'
UA = 'zouni-audit/1.0 (majian@bituniverse.org)'

SUF = '门寺塔馆庙宫殿祠观陵楼阁庵'
GENERIC3 = ('博物馆', '纪念馆', '美术馆', '展览馆', '科技馆', '图书馆', '艺术馆', '体育馆', '文化馆', '博物院', '陈列馆', '展示馆', '大剧院')
SPLIT = re.compile(r'[·•・（）()/／、，,\s\-—–+＋&和与及]+')
GENERIC_WORDS = ('风景名胜区', '风景区', '旅游区', '旅游度假区', '景区', '国家森林公园', '森林公园', '国家公园', '遗址公园', '景点')
APPROX = re.compile(r'人工|近似|补录|核对|城市中心|refix')
ADMIN_PART = re.compile(r'^([\u4e00-\u9fa5]{2,3})(区|县|镇|乡|旗)$')


def km(a, b):
    r = math.pi / 180
    dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def parts_of(name):
    return [x for x in SPLIT.split(name) if x]


def terms_of(name):
    """站名里的“专名”：以 门/寺/塔/馆/庙/宫… 结尾的部分的尾巴（门允许 2 字，如 南门；其余至少 3 字）。返回 [(整段, 尾巴)]"""
    out = []
    for p in parts_of(name):
        if p[-1] not in SUF: continue
        if p[-1] == '门':
            if len(p) < 2: continue
        elif len(p) < 3: continue
        t = p if len(p) <= 4 else p[-4:]
        if t[-3:] in GENERIC3 and len(p) > 4: t = p[-5:]
        out.append((p, t))
    return out


HAS_CJK = re.compile(r'[\u4e00-\u9fa5]')
GEN_TAIL = ('博物馆', '博物院', '纪念馆', '美术馆', '展览馆', '科技馆', '图书馆', '艺术馆', '陈列馆', '展示馆', '大剧院')


def distinct_of(t):
    """专名去掉通用后缀后的“区分部分”：永宁门 → 永宁；白塔寺 → 白塔；南门 → 南。"""
    for g in GEN_TAIL:
        if t.endswith(g) and len(t) > len(g): return t[:-len(g)]
    return t[:-1]


def term_ok(q, name):
    """q 是否含站名专名的区分部分（q 不含汉字的外文 q 不判）；有多个专名时 q 含任一个就算过。返回 (过?, 缺的专名列表)"""
    ts = terms_of(name)
    if not ts or not HAS_CJK.search(q): return True, []
    qn = q.replace(' ', '')
    for p, t in ts:
        d = distinct_of(t)
        if d in qn or p in qn or t in qn: return True, []
    return False, [t for _, t in ts]


def cores_of(name, city):
    out = []
    for p in parts_of(name):
        for g in GENERIC_WORDS: p = p.replace(g, '')
        if p.startswith(city) and len(p) > len(city) + 1: p = p[len(city):]
        if len(p) >= 2: out.append(p)
    return out


def load():
    P = json.load(open(GP, encoding='utf-8'))
    I = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
    return P, I


def collect(P, I):
    """键 → {names, qs, routes}（只收 pois 里有坐标的键）"""
    K = {}
    for rid, v in I.items():
        city = v['city']
        for d in v['days']:
            c = d.get('city', city)
            for s in d['stops']:
                k = c + '|' + s['q']
                e = K.setdefault(k, {'city': c, 'q': s['q'], 'names': set(), 'routes': set(), 'types': set()})
                e['names'].add(s['name']); e['routes'].add(rid); e['types'].add(s.get('type', ''))
    return K


def audit():
    P, I = load()
    K = collect(P, I)
    # d：同一坐标多个站名
    by_xy = defaultdict(set)
    for k, e in K.items():
        g = P.get(k)
        if not g or g.get('lat') is None or e['q'] == e['city']: continue
        by_xy[(round(g['lat'], 3), round(g['lng'], 3))].update(e['names'])
    rows = []
    cnt = defaultdict(int)
    for k, e in K.items():
        g = P.get(k)
        if not g or g.get('lat') is None: continue
        c, q = e['city'], e['q']
        if q == c: continue
        names = sorted(e['names'])
        hit = g.get('hit') or ''
        rules = []; why = []
        # a
        for n in names:
            ok, miss = term_ok(q, n)
            if not ok: rules.append('a'); why.append(f'站名「{n}」专名 {"/".join(miss)} 不在 q「{q}」里'); break
        # b
        if ',' in hit and not APPROX.search(hit):
            allc = [x for n in names for x in cores_of(n, c) if len(x) > 2]
            if allc and not any(x in hit for x in allc) and not any(x[i:i + 2] in hit for x in allc for i in range(len(x) - 1)):
                rules.append('b'); why.append('hit 里没有站名核心词')
        # c
        cc = P.get(c + '|' + c); dist = ''
        if cc and cc.get('lat') is not None:
            dd = km((cc['lat'], cc['lng']), (g['lat'], g['lng'])); dist = round(dd, 1)
            sub = any(re.search(r'[一-龥]{2,}(区|县|镇|乡|旗)', n) for n in names)
            if dd > 120 and not sub: rules.append('c2'); why.append(f'离城市中心 {dd:.0f} 公里且站名无郊区地名')
            elif dd > 40: rules.append('c1'); why.append(f'离城市中心 {dd:.0f} 公里')
        # d
        names_here = by_xy[(round(g['lat'], 3), round(g['lng'], 3))]
        if len(names_here) >= 4: rules.append('d'); why.append(f'同坐标 {len(names_here)} 个站名共用')
        # e
        if ',' in hit and not APPROX.search(hit):
            for n in names:
                for p in parts_of(n):
                    m = ADMIN_PART.match(p)
                    if m and not re.search(r'(景|园|山|游|古|文化|风景|重建|喜马拉雅|硫磺浴)$', m.group(1)) and m.group(1) not in hit and m.group(1) not in c:
                        rules.append('e'); why.append(f'站名区县「{p}」不在 hit 行政区里'); break
                if rules and rules[-1] == 'e': break
        if not rules: continue
        for r in set(rules): cnt[r] += 1
        rows.append({'key': k, 'city': c, 'q': q, 'names': ' | '.join(names[:3]), 'lat': g['lat'], 'lng': g['lng'],
                     'hit': hit[:80], 'src': g.get('src'), 'refs': len(e['routes']), 'rules': ','.join(sorted(set(rules))),
                     'dist_city_km': dist, 'why': '；'.join(why)})
    W = {'a': 5, 'b': 2, 'c2': 4, 'c1': 1, 'd': 2, 'e': 2}
    for r in rows: r['score'] = sum(W[x] for x in r['rules'].split(','))
    rows.sort(key=lambda r: (-r['refs'], -r['score'], r['key']))
    os.makedirs('build', exist_ok=True)
    cols = ['key', 'refs', 'score', 'rules', 'city', 'q', 'names', 'lat', 'lng', 'src', 'hit', 'dist_city_km', 'why']
    with open(CSV, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows: w.writerow({c: r[c] for c in cols})
    print(f'审计的键 {len(K)}；命中 {len(rows)} 条 → {CSV}')
    print('规则命中数：' + '  '.join(f'{k}={cnt[k]}' for k in ('a', 'b', 'c1', 'c2', 'd', 'e')))
    return rows, K, P


# ---------- Nominatim ----------
def nominatim(cache, q, cc):
    ck = f'{q}|{cc}'
    if ck in cache: return cache[ck]
    url = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode(
        {'q': q, 'format': 'jsonv2', 'limit': 8, 'accept-language': 'zh', **({'countrycodes': cc} if cc else {})})
    res = None
    for _ in range(3):
        time.sleep(1.1)
        r = subprocess.run(['curl', '-s', '-m', '25', '-A', UA, url], capture_output=True)
        try:
            res = json.loads(r.stdout.decode('utf-8')); break
        except Exception:
            time.sleep(3)
    if res is None: return None        # 取数失败不缓存
    cache[ck] = res
    return res


def load_cache():
    return json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}


def save_cache(c):
    json.dump(c, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)


def cc_of(P, city, K_dest):
    return 'cn' if K_dest else ''


def verify(n, strong=False, noncur=False):
    rows, K, P = audit()
    allrows = rows
    sel = rows[:n]
    for r in rows[n:]:      # 前 n 条之外：strong=a/b/c2/d/e 命中的（比 c1 更像真错）；noncur=非 curated（在线查询自动得来、没人看过）的
        if (strong and set(r['rules'].split(',')) & {'a', 'b', 'c2', 'd', 'e'}) or (noncur and r['src'] != 'curated'): sel.append(r)
    rows = sel; n = len(rows)
    I = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
    DEST = {d['id']: d for k in ('domestic', 'asia', 'world') for d in json.load(open('data/destinations.json', encoding='utf-8'))[k]}
    domestic = {d['id'] for d in json.load(open('data/destinations.json', encoding='utf-8'))['domestic']}
    key_dest = {}
    for rid, v in I.items():
        for d in v['days']:
            for s in d['stops']: key_dest.setdefault(d.get('city', v['city']) + '|' + s['q'], v['dest'])
    cache = load_cache()
    plan, unsure = [], []
    from collections import Counter
    stat = Counter()
    for r in rows[:n]:
        k = r['key']; e = K[k]; g = P[k]; c = e['city']
        cur = (g['lat'], g['lng'])
        cc = P.get(c + '|' + c); cen = (cc['lat'], cc['lng']) if cc and cc.get('lat') is not None else cur
        isdom = key_dest.get(k) in domestic or key_dest.get(k) == 'taiwan'
        names = sorted(e['names'])
        # 候选专名：每个站名的各部分（带专名的优先），去重
        cands = []
        for nm in names:
            ts = [p for p, _ in terms_of(nm)]
            for p in (ts or [x for x in parts_of(nm) if len(x) >= 3]):
                for g_ in GENERIC_WORDS: p = p.replace(g_, '')
                if p.startswith(c) and len(p) > len(c) + 1: p = p[len(c):]
                if len(p) >= 2 and p not in cands: cands.append(p)
        verdict = None; note = ''
        for cand in cands[:3]:
            qn0 = e['q'].replace(' ', '')
            qq = e['q'] if (cand in qn0 and HAS_CJK.search(qn0)) else f'{cand} {c}'      # q 里带了别的城市（“柳叶湖 常德”）就按 q 查，不强加当天城市
            res = nominatim(cache, qq, 'cn' if isdom else '')
            if res is None: note = 'Nominatim 取数失败'; continue
            exact = []
            for x in res:
                nm_ = x.get('name') or ''
                if nm_ != cand: continue
                if x.get('category') in ('railway', 'highway', 'public_transport', 'boundary', 'place') and not (x.get('category') == 'place' and False): continue
                bb = [float(t) for t in x['boundingbox']]
                diag = km((bb[0], bb[2]), (bb[1], bb[3]))
                if diag > 1.2: continue
                pos = (float(x['lat']), float(x['lon']))
                # 远处的点只在“小修正”（离现坐标 <= 10 公里）时才信；大幅搬家要求新点在城市中心 60 公里内（防 金沙湾→深圳、华严寺→蔚县 这类同名）
                if km(cen, pos) > 60 and km(cur, pos) > 10: continue
                exact.append((pos, x))
            if not exact: note = f'「{cand}」无点状精确命中'; continue
            if any(km(exact[0][0], p) > 1.5 for p, _ in exact[1:]):
                # 同名多点：只有“名字里带城市名、且有一个点明显最靠近城市中心”才认它（泉州开元寺：鲤城区 vs 永春县）
                srt = sorted(exact, key=lambda t: km(cen, t[0])); db = km(cen, srt[0][0])
                if (c in e['q'] or any(c in nm for nm in names)) and db <= 30 and all(km(cen, p) >= max(2.5 * db, db + 20) for p, _ in srt[1:]):
                    exact = [srt[0]]
                else:
                    note = f'「{cand}」有多个相距 >1.5 公里的同名点'; verdict = 'unsure'; break
            pos, x = exact[0]
            d_ = km(cur, pos)
            qn_ = e['q'].replace(' ', '')
            if not HAS_CJK.search(qn_) or sum(1 for i in range(len(cand) - 1) if cand[i:i + 2] in qn_) < (1 if len(cand) <= 3 else 2):
                verdict = 'unsure'; note = f'q「{e["q"]}」与匹配名「{cand}」对不上，不信'; break
            if d_ <= 1.5: verdict = 'ok'; note = f'现坐标已在「{cand}」1.5 公里内（{d_:.1f}）'; break
            if d_ > 5 and (c not in x['display_name'] or x.get('category') == 'natural' or re.search(r'[峰山湖川岭谷滩海岛坝原营]$|大本营|山口|垭口|达坂|仁波齐', cand)):
                # 大于 5 公里的搬动：新点的地址里必须有当天城市名，且不是山/湖/冰川这类“面状自然物”的代表点
                # （同心清真大寺→银川、芒景村→景谷、冈仁波齐山峰→转山起点 都是这样被拦下的）
                verdict = 'unsure'; note = f'「{cand}」要搬 {d_:.1f} 公里，但新点地址里没有「{c}」或是自然物，不信'; break
            others = [nm for nm in names if cand not in nm]
            if others: note = f'共用该键的站名 {others} 不含「{cand}」'; verdict = 'unsure'; break
            verdict = 'change'
            plan.append({'key': k, 'old': [g['lat'], g['lng']], 'new': [round(pos[0], 7), round(pos[1], 7)], 'dist_km': round(d_, 2),
                         'q_used': qq, 'hit': x['display_name'], 'cand': cand, 'refs': r['refs'], 'rules': r['rules'], 'names': names})
            break
        stat[verdict or 'none'] += 1
        if verdict in (None, 'unsure'):
            unsure.append({**{c_: r[c_] for c_ in ('key', 'refs', 'rules', 'names', 'lat', 'lng', 'src', 'hit', 'why')}, 'note': note or '无证据'})
        if len(cache) % 20 == 0: save_cache(cache)
    save_cache(cache)
    json.dump(plan, open(PLAN, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    cols = ['key', 'refs', 'rules', 'names', 'lat', 'lng', 'src', 'hit', 'why', 'note']
    with open(UNSURE, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(unsure)
    print('判定：', dict(stat))
    print(f'核实 {min(n, len(rows))} 条：有证据可改 {len(plan)}；拿不准/无证据 {len(unsure)} → {UNSURE}；计划 → {PLAN}')


def apply():
    plan = json.load(open(PLAN, encoding='utf-8'))
    P = json.load(open(GP, encoding='utf-8'))
    import shutil
    bak = 'build/pois.json.bak_audit'
    if not os.path.exists(bak): shutil.copy(GP, bak)
    n = 0
    for it in plan:
        g = P[it['key']]
        if [g['lat'], g['lng']] != it['old']: print('跳过（现坐标已变）', it['key']); continue
        g['lat'], g['lng'] = it['new']
        g['hit'] = '人工核对（Nominatim）'; g['q'] = it['q_used']; g['src'] = 'curated'
        n += 1
    # 同证据传播：别的城市下 q 含同一专名、且坐标与旧坐标逐位相同的键（同一次错误的拷贝，如 厦门|泉州开元寺）一并改
    n2 = 0
    for it in plan:
        for k, v in P.items():
            if isinstance(v, dict) and v.get('lat') is not None and k != it['key'] and it['cand'] in k and abs(v['lat'] - it['old'][0]) < 1e-6 and abs(v['lng'] - it['old'][1]) < 1e-6:
                v['lat'], v['lng'] = it['new']; v['hit'] = '人工核对（Nominatim）'; v['q'] = it['q_used']; v['src'] = 'curated'; n2 += 1
    print('传播改了', n2, '条')
    json.dump(P, open(GP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('已改', n, '条（备份', bak, '）')


# ---------- 构建门（tests/data_checks.py 第 35 项调用）----------
BASELINE = 'data/geo/q_term_baseline.json'


def term_violations(I, baseline=()):
    """所有站点里：站名带专名（某某门/寺/塔/馆…）而 q 里没有它的区分部分的 (键, 站名, q)。baseline 里的键（存量，已审）不报。"""
    bad = []; seen = set()
    for rid, v in I.items():
        for di, d in enumerate(v['days']):
            c = d.get('city', v['city'])
            for s in d['stops']:
                ok, miss = term_ok(s['q'], s['name'])
                k = c + '|' + s['q']
                if ok or k in baseline or (k, s['name']) in seen: continue
                seen.add((k, s['name']))
                bad.append(f'{rid} 第{di + 1}天「{s["name"]}」：专名 {"/".join(miss)} 不在 q「{s["q"]}」里（键 {k}）')
    return bad


def selftest():
    """闸自检：好稿不红、注入的缺陷红。返回错误列表。"""
    errs = []
    mk = lambda name, q: {'x': {'city': '西安', 'days': [{'stops': [{'name': name, 'q': q}]}]}}
    if term_violations(mk('西安城墙 · 永宁门', '西安城墙永宁门')): errs.append('好稿被误报（q 含专名）')
    if not term_violations(mk('西安城墙 · 永宁门', '西安城墙')): errs.append('漏报：q 只写泛称“西安城墙”')
    if not term_violations(mk('大雁塔', '西安大慈恩寺')): errs.append('漏报：站名大雁塔而 q 写别的')
    if term_violations(mk('浅草寺', 'Senso-ji')): errs.append('外文 q 不该判')
    if term_violations(mk('钟楼', '西安钟楼')) : errs.append('好稿被误报（钟楼）')
    if term_violations(mk('西安城墙 · 永宁门', '西安城墙'), baseline={'西安|西安城墙'}): errs.append('baseline 键没有放行')
    return errs


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[:1] == ['--selftest']:
        e = selftest(); print('\n'.join(e) or '自检通过'); sys.exit(1 if e else 0)
    if a[:1] == ['--baseline']:
        I = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
        ks = sorted({x.split('（键 ')[1][:-1] for x in term_violations(I)})
        json.dump({'note': '存量：站名带专名而 q 没有它的区分部分，已逐条看过、无需改（新增不许）。改完一条就从这里删一条。', 'keys': ks}, open(BASELINE, 'w', encoding='utf-8'), ensure_ascii=False, indent=1); print(len(ks), 'keys')
    elif a[:1] == ['--verify']: verify(int(a[1]) if len(a) > 1 else 300, '--strong' in a, '--noncur' in a)
    elif a[:1] == ['--apply']: apply()
    else: audit()
