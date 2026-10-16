#!/usr/bin/env python3
"""「顺路加一站 / 换一站」的候选池（离线构建）。设计：docs/handoff/design-nearby-stops.md §2。

用法（项目根目录；只读 data/、tools/build_site.py，只写 build/np/）：
    python3 tools/build_nearby_pool.py            # 构建 + 打印漏斗/分片数字
    python3 tools/build_nearby_pool.py --quiet    # 只打一行总结

输入：data/itineraries.json（站点）· data/geo/pois.json（坐标）· data/catalog/niche.json（只取 open）·
      data/catalog/tickets.json · data/catalog/destinations.json · data/destinations.json ·
      tools/build_site.py 里的 SIGHT / DEEP / BOOK / FOREIGN_CLOSED（用 ast 读字典，不 import、不改）·
      build/denies.txt（串线闸的拒绝名单，有就用）
输出：build/np/pool.json          全部候选（带调试字段 k，不进页面）
      build/np/<纬格>_<经格>.js    3° 网格分片：(window.ZNP=window.ZNP||{})['34_36']=[…];
      build/np/_index.js           有数据的格的清单 window.ZNP_CELLS=['34_100',…]（客户端只请求清单里的格）
      build/np/stats.json          漏斗、类型、国内外、分片体积

每个候选（分片里的字段）：
  i 稳定 id · n 名字 · c 城市（导航用，国内是城市；niche 是省） · a,o 纬度、经度（3 位小数）· t 类型 2 字码 ·
  d 停留分钟（各线里时长的中位数，没有按类型表）· s 一句话（≤24 字）· q 导航查询词 ·
  x 门票等 {t 门票, h 开放时间, b 要预约, cl 闭馆日（JS 周几，0=周日）} · p 被几条线用过 · ds 目的地 id（只有国外写；没有 = 国内；q 缺省 = n）·
  ev 1=晚上才有意义（只插在当天最后一站之后）· ap 1=坐标是人工近似（绕路分钟只当量级）· al 同址并入的别名
"""
import ast
import collections
import gzip
import hashlib
import json
import math
import os
import re
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import nearby_model as M   # noqa: E402

OUT = os.path.join(ROOT, 'build', 'np')

# ---------------------------------------------------------------- 规则常量（改了要同步设计文档）
ALLOWED_TYPES = {'sight', 'park', 'street', 'museum', 'fun', 'temple', 'beach', 'mountain', 'lake', 'culture', 'town', 'night'}
TYPE_CODE = {'sight': 'sg', 'park': 'pk', 'street': 'st', 'museum': 'ms', 'fun': 'fn', 'temple': 'tp', 'beach': 'bc',
             'mountain': 'mt', 'lake': 'lk', 'culture': 'cl', 'town': 'tn', 'night': 'nt'}
DUR_BY_TYPE = {'sight': 120, 'museum': 150, 'street': 90, 'park': 60, 'fun': 90, 'night': 60}   # compile_itineraries.DUR
DUR_DEFAULT = 90
# 非景点：机场、车站、公路、码头、酒店、营地、商场、餐厅、医院…（名字和 q 都查）
NON_ATTR = re.compile(r'机场|航站|火车站|高铁站|动车站|客运站|汽车站|地铁站|车站|公路|环线|沿途|提车|还车|码头|渡口|渡轮|轮渡|口岸|边检|检查站|服务区|加油站|收费站|停车场|'
                      r'酒店|宾馆|民宿|客栈|青旅|旅馆|营地|住宿|超市|商场|购物中心|百货|奥特莱斯|餐厅|饭店|酒楼|火锅店|咖啡馆|夜市|美食街|医院|学校|大学城|航班|总站|巴士站|公交|[东南西北]站|高铁|动车|地铁|索道|缆车|军港|军事')
BOAT_ONLY = re.compile(r'(?<!半)岛$|列岛|群岛|屿$')      # 名字本身是岛：要过水（渡轮），直线车程模型看不出来，不进池
TOWN_ONLY = re.compile(r'(?<!古)(县城|乡镇)$|(?<!保护)(?<!观测)(?<!气象)站$')     # 县城本身是落脚点，不是景点（“古县城”是景点）
MALL_TEXT = re.compile(r'商场|购物中心|百货|奥特莱斯')
BASE_TEXT = re.compile(r'落脚|补给|加油|歇脚|中转|换乘|过夜|住宿|出发点|吃饭的地方')
ALT_NAME = re.compile(r'垭口|雪山|冰川|大本营|纳木错|羊卓|冈仁波齐|昆仑山口|唐古拉|珠峰|可可西里|布达拉|乃琼|玉龙雪山|海拔|5[0-9]{3}米|4[0-9]{3}米')
SEASONAL = re.compile(r'樱|红叶|枫叶|红枫|滑雪|雾凇|花海|薰衣草|荷花|油菜花|杜鹃|梅花|郁金香|桃花|梨花|银杏|赏雪|冰雕|冰灯|雪乡|萤火虫|赏枫|赏花|花田')
EVENING = re.compile(r'夜游|夜景|夜晚|不夜城|霓虹|灯会|灯光秀|酒吧|居酒屋|夜场|夜间')
ELEV_ALT = 3500            # 当天海拔 ≥ 3500：那天的站不进候选
FAR_CITY_KM = 400          # 离所属城市中心 > 400 公里：坐标不可信
CITY_LEVEL_KM = 0.05       # 坐标和城市中心几乎重合、名字又不是城市本身：是“市中心”级的占位坐标
MERGE_SAME_NAME_KM = 15    # 同名 15 公里内合并
MERGE_CONTAIN_KM = 1.5     # 名字互相包含 1.5 公里内合并
MERGE_SPOT_KM = 0.25       # 250 米内视为同处，合并（大雁塔 + 大慈恩寺）
SENT_MAX = 24
GENERIC2 = set('景区 公园 风景 名胜 旅游 博物 物馆 纪念 念馆 古城 古镇 老街 步行 街区 中心 广场 大街 遗址 保护 国家 森林 湿地 地质 世界 文化 历史 风情 度假 大桥 故居 公馆 美术 术馆 景点 国家森林 风景区 旅游区 自然 保护区 管理 管理局'.split())
SHARD_MAX_BYTES = 30 * 1024


def load(p):
    return json.load(open(os.path.join(ROOT, p), encoding='utf-8'))


def short(n):
    return re.split(r'\s*·\s*', n)[0].strip()


# ---------------------------------------------------------------- 读 build_site.py 里的字典（ast，不 import）
def read_dicts():
    src = open(os.path.join(ROOT, 'tools', 'build_site.py'), encoding='utf-8').read()
    out = {'SIGHT': {}, 'DEEP': {}, 'BOOK': {}, 'FOREIGN_CLOSED': {}}
    for n in ast.parse(src).body:
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
            for tg in n.targets:
                nm = getattr(tg, 'id', None)
                if nm in out:
                    try:
                        out[nm].update(ast.literal_eval(n.value))
                    except ValueError:
                        pass
        elif isinstance(n, ast.Expr) and isinstance(n.value, ast.Call) and isinstance(n.value.func, ast.Attribute):
            f = n.value.func
            if getattr(f.value, 'id', None) == 'BOOK' and f.attr == 'update' and n.value.args and isinstance(n.value.args[0], ast.Dict):
                try:
                    out['BOOK'].update(ast.literal_eval(n.value.args[0]))
                except ValueError:
                    pass
    return out


def index_keys(d):
    """键 → 按“景点名部分”建倒排：k0 = 去掉“限定词|”的部分"""
    idx = collections.defaultdict(list)
    for k in d:
        k0 = k.split('|', 1)[1] if '|' in k else k
        idx[k0].append(k)
    return idx


def substrings(name):
    """站名的所有 2–14 字子串（排好序：同长度的键并列时结果要稳定，不能看集合的遍历顺序）"""
    s = set()
    for i in range(len(name)):
        for j in range(i + 2, min(len(name), i + 14) + 1):
            s.add(name[i:j])
    return sorted(s)


def clip(s):
    """一句话 ≤ 24 字：按“，；”分句，能装下几句装几句；第一句就超长就在 23 字处截断加省略号"""
    s = (s or '').strip()
    if len(s) <= SENT_MAX:
        return s.rstrip('。')
    parts = re.split(r'(?<=[，；])', s)
    out = ''
    for p in parts:
        if len((out + p).rstrip('，；。')) <= SENT_MAX:
            out += p
        else:
            break
    out = out.rstrip('，；。')
    if len(out) >= 6:
        return out
    return s[:SENT_MAX - 1] + '…'


class Texts:
    def __init__(self):
        d = read_dicts()
        self.SIGHT, self.DEEP, self.BOOK, self.FC = d['SIGHT'], d['DEEP'], d['BOOK'], d['FOREIGN_CLOSED']
        self.sidx = index_keys(self.SIGHT)
        self.didx = index_keys(self.DEEP)
        self.bidx = index_keys(self.BOOK)
        self.TIX = load('data/catalog/tickets.json')
        self.deny = set()
        self.home = {}        # (表, 键) → 文案“本家”所在的线（串线闸写在 denies.txt 里的“本家在 [...]”）
        dp = os.path.join(ROOT, 'build', 'denies.txt')
        if os.path.exists(dp):
            for line in open(dp, encoding='utf-8'):
                m = re.match(r'(SIGHT|BOOK|TIX|DEEP) 「(.+?)」拒绝 (\S+?)（(?:本家在|文案点名的是) (\[.*?\])', line)
                if m:
                    self.deny.add((m.group(1), m.group(2), m.group(3)))
                    self.home.setdefault((m.group(1), m.group(2)), set()).update(re.findall(r"'([^']+)'", m.group(4)))

    def sentence(self, names, core, ctx, rids):
        """一句话 → (文字, SIGHT 键)。SIGHT 里最长的键（景点名部分在站名里；两字键必须等于核心名；带限定词的键限定词要出现在上下文里）；
        没有再用 DEEP 的第一句（≤24 字才用）。串线闸（build/denies.txt）拒绝过这条线、或这条线不在文案“本家”里的，不用。"""
        best = None
        for nm in names:
            for sub in sorted(set(substrings(nm)) | {core}):
                for k in self.sidx.get(sub, ()):
                    if len(sub) <= 2 and sub != core:
                        continue
                    if '|' in k and not any(x in ctx for x in k.split('|', 1)[0].split('/')):
                        continue
                    if rids and all(('SIGHT', k, r) in self.deny for r in rids):
                        continue
                    h = self.home.get(('SIGHT', k))
                    if h and not (h & rids):
                        continue
                    rank = (len(sub), '|' in k)
                    if best is None or rank > best[0]:
                        best = (rank, self.SIGHT[k], k)
        if best:
            return clip(best[1]), best[2]
        for nm in names:
            for sub in sorted(set(substrings(nm)) | {core}):
                for k in self.didx.get(sub, ()):
                    if sub != nm and sub != core and len(sub) < 3:
                        continue
                    if '|' in k and not any(x in ctx for x in k.split('|', 1)[0].split('/')):
                        continue
                    if rids and all(('DEEP', k, r) in self.deny for r in rids):
                        continue
                    h = self.home.get(('DEEP', k))
                    if h and not (h & rids):
                        continue
                    first = re.split(r'[。；]', self.DEEP[k])[0]
                    if 6 <= len(first) <= SENT_MAX:
                        return first, 'DEEP:' + k
        return '', ''

    def ticket(self, names, rids):
        """门票 / 开放时间 / 闭馆日 / 要预约。取最长键（站名里包含）。"""
        x = {}
        best = None
        for nm in names:
            for sub in substrings(nm):
                if sub in self.TIX and not all(('TIX', sub, r) in self.deny for r in rids) and (best is None or len(sub) > len(best)):
                    best = sub
        cl = None
        if best:
            v = self.TIX[best]
            if v.get('t'):
                x['t'] = v['t'][:30]
            if v.get('h'):
                x['h'] = v['h'][:40]
            m = re.search(r'周([一二三四五六日])闭馆', v.get('c') or '')
            if m:
                cl = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '日': 0}[m.group(1)]
        for nm in names:
            c0 = short(nm)
            if c0 in self.FC:
                cl = self.FC[c0]
        if cl is not None:
            x['cl'] = cl
        bk = None
        for nm in names:
            for sub in substrings(nm):
                for k in self.bidx.get(sub, ()):
                    if not all(('BOOK', k, r) in self.deny for r in rids) and (bk is None or len(sub) > len(bk)):
                        bk = sub
        if bk:
            x['b'] = 1
        return x


# ---------------------------------------------------------------- 坐标可信度
def two_char_windows(s):
    s = re.sub(r'[^一-鿿]', '', s or '')
    return {s[i:i + 2] for i in range(len(s) - 1)}


def ascii_tokens(s):
    return {w.lower() for w in re.findall(r'[A-Za-z]{4,}', s or '')}


def name_ok(hit, q, core, city):
    """地理编码器命中的显示名：第一段必须和 q 或站名共享一个有意义的词，否则是命中了别处。
    （设计 §2.2-1：翠华山被定位到“交大财经社区西院-4号楼”就是这样被拦下的）
    中文：共享一个两字词（去掉“景区/公园…”这类泛词和城市名）；英文：共享一个 ≥4 字母的词；
    第一段既没有汉字也没有拉丁字母（泰文、阿拉伯文…）：判断不了，放行（靠“离城市中心 ≤400 公里”兜底）。"""
    if not re.search(r'[\u4e00-\u9fff]', q or ''):
        return True      # 英文查询词（国外）：显示名常是当地文字或译名，对不上字面，判断不了，放行（靠“离城市中心 ≤400 公里”兜底）
    first = re.split(r'[,，]', hit or '')[0]
    hw = two_char_windows(first)
    ha = ascii_tokens(first)
    if not hw and not ha:
        return True
    nw0 = (two_char_windows(q) | two_char_windows(core)) - GENERIC2
    nw = nw0 - two_char_windows(city) or nw0
    if (hw & nw) - GENERIC2:
        return True
    return bool(ha & (ascii_tokens(q) | ascii_tokens(core)))


def trusted_point(P, city, q, core, inline, ref_pt):
    """返回 (点或 None, 近似标志, 拒绝原因)。原因 ∈ no_coord / city_level / far_city / name_mismatch / far_city_osm"""
    if inline:
        pt = (inline[0], inline[1])
        hit, src = '内联', 'inline'
    else:
        g = P.get(city + '|' + q)
        if not isinstance(g, dict) or g.get('lat') is None:
            return None, 0, 'no_coord'
        pt = (g['lat'], g['lng'])
        hit, src = g.get('hit') or '', g.get('src')
    if hit.startswith(('市区中心', '市中心')):
        return None, 0, 'city_level'
    cc = P.get(city + '|' + city)
    if isinstance(cc, dict) and cc.get('lat') is not None and q != city and core != city:
        if M.km(pt, (cc['lat'], cc['lng'])) < CITY_LEVEL_KM:
            return None, 0, 'city_level'
    if ref_pt and M.km(pt, ref_pt) > FAR_CITY_KM:
        return None, 0, 'far_city_osm' if src == 'osm' else 'far_city'
    if not inline and not hit.startswith(('人工', 'OSM', '市区')) and not name_ok(re.sub(r'^\S*核对\s*', '', hit), q, core, city):
        return None, 0, 'name_mismatch'      # 地理编码器命中的显示名（不论 src 标的是 None/osm/curated）：第一段要和站名对得上
    ap = 1 if (hit.startswith(('人工', 'OSM')) or src in ('osm', 'web', 'inline')) else 0
    return pt, ap, ''


# ---------------------------------------------------------------- 主流程
def build(quiet=False):
    IT = load('data/itineraries.json')['itineraries']
    P = load('data/geo/pois.json')
    CAT = {d['id']: d for d in load('data/catalog/destinations.json')['destinations']}
    DST = load('data/destinations.json')
    FOREIGN = {x['id'] for k in ('asia', 'world') for x in DST.get(k, [])} | {'taiwan'}   # compile_itineraries 的 ASIA_CC 键集
    NICHE = [x for x in load('data/catalog/niche.json')['items']]
    T = Texts()

    # 1 收集：以 (城市, q) 为单位
    U = {}
    for rid, it in IT.items():
        for di, d in enumerate(it['days']):
            city = d.get('city', it['city'])
            for s in d['stops']:
                k = city + '|' + s['q']
                u = U.setdefault(k, {'city': city, 'q': s['q'], 'names': collections.Counter(), 'types': collections.Counter(), 'durs': [],
                                     'rids': set(), 'free': 0, 'alt': 0, 'dest': collections.Counter(), 'ctx': set(), 'inline': None})
                u['names'][s['name']] += 1
                u['types'][s['type']] += 1
                u['rids'].add(rid)
                u['dest'][it['dest']] += 1
                u['ctx'].update([city, it.get('label', ''), d.get('title', ''), d.get('stay', '') or ''])
                if not s.get('at'):
                    u['free'] += 1
                    if s.get('dur'):
                        u['durs'].append(s['dur'])
                if (d.get('elev') or 0) >= ELEV_ALT:
                    u['alt'] = 1
                if s.get('lat') is not None and s.get('lng') is not None:
                    u['inline'] = (s['lat'], s['lng'])

    F = collections.OrderedDict()      # 漏斗：名 → 剔除数
    def drop(reason, n=1):
        F[reason] = F.get(reason, 0) + n

    cands = []
    total_units = len(U)
    for k in sorted(U):
        u = U[k]
        names = list(u['names'])
        core = short(u['names'].most_common(1)[0][0])
        ty = u['types'].most_common(1)[0][0]
        if ty not in ALLOWED_TYPES:
            drop('类型不是景点（food/station/mall/city/district/market/shop/cafe/camp…）'); continue
        if not u['free']:
            drop('只有定点 at（日出日落、演出、开船）'); continue
        if NON_ATTR.search(core) or NON_ATTR.search(u['q']) or any(NON_ATTR.search(n) for n in names) or TOWN_ONLY.search(core) or BOAT_ONLY.search(core):
            drop('名字像机场/车站/酒店/营地/商场/餐厅/码头…'); continue
        ds = u['dest'].most_common(1)[0][0]
        cc = P.get(u['city'] + '|' + u['city'])
        if isinstance(cc, dict) and cc.get('lat') is not None:
            ref = (cc['lat'], cc['lng'])
        else:
            b = CAT[ds]['base']; ref = (b['lat'], b['lng'])
        pt, ap, why = trusted_point(P, u['city'], u['q'], core, u['inline'], ref)
        if why:
            drop({'no_coord': '没有坐标', 'city_level': '坐标是市中心/行政区级占位', 'far_city': '坐标离所属城市 >400 公里',
                  'far_city_osm': '坐标离所属城市 >400 公里（来源 osm）', 'name_mismatch': '非人工坐标且命中名对不上站名'}[why]); continue
        if u['alt'] or ALT_NAME.search(core) or ALT_NAME.search(u['q']):
            drop('高海拔（当天 elev≥3500 或名字含雪山/垭口/大本营…）'); continue
        ctx = ''.join(sorted(u['ctx']))
        s, skey = T.sentence(names, core, ctx, u['rids'])
        if SEASONAL.search(core) or SEASONAL.search(s):
            drop('季节限定（樱/红叶/滑雪/雾凇/花海/薰衣草…）'); continue
        if MALL_TEXT.search(s):
            drop('一句话写的是商场'); continue
        if BASE_TEXT.search(s):
            drop('一句话写的是落脚/补给/中转（不是景点）'); continue
        durs = u['durs']
        d_ = int(statistics.median(durs)) if durs else DUR_BY_TYPE.get(ty, DUR_DEFAULT)
        c = {'k': k, 'i': '', 'n': core, 'c': u['city'], 'a': round(pt[0], 3), 'o': round(pt[1], 3), 't': TYPE_CODE[ty], 'd': d_, 's': s,
             'q': u['q'], 'x': T.ticket(names, u['rids']), 'p': len(u['rids']), 'ds': ds, '_rids': set(u['rids']), '_names': set(x_ for n in names for x_ in re.split(r'\s*·\s*', n) if x_.strip()), '_qtok': {w for w in u['q'].split() if len(w) >= 3}, '_skey': skey}
        if ty == 'night' or EVENING.search(core) or EVENING.search(s):
            c['ev'] = 1
        if ap:
            c['ap'] = 1
        cands.append(c)
    n_after_filters = len(cands)
    # 一句话的“同名异地”再扫一遍：同一个 SIGHT 键被相距 >50 公里的几个候选用上（兴教寺：西安 vs 大理沙溪），说明文案只属于其中一处，
    # 又没有串线闸的“本家”信息可判 → 都不用这句话（宁可没有，不要错挂）
    by_key = collections.defaultdict(list)
    for c in cands:
        if c['_skey'] and not c['_skey'].startswith('DEEP:'):
            by_key[c['_skey']].append(c)
    n_amb = 0
    for k_, lst in by_key.items():
        if len(lst) > 1 and any(M.km((a['a'], a['o']), (b['a'], b['o'])) > 50 for a in lst for b in lst):
            for c in lst:
                c['s'] = ''
                n_amb += 1
    if n_amb:
        drop('（不剔除，只清掉一句话）同名异地的一句话', n_amb)

    # 2 并入 niche（只取 open）
    n_niche_open = 0
    for x in NICHE:
        if x['status'] != 'open':
            continue
        n_niche_open += 1
        core = short(re.sub(r'（.*?）', '', x['name']))
        if NON_ATTR.search(core) or TOWN_ONLY.search(core) or BOAT_ONLY.search(core):
            drop('niche：名字像车站/营地/岛…'); continue
        if ALT_NAME.search(core) or ALT_NAME.search(x['name']):
            drop('niche：高海拔名字'); continue
        s = clip(re.split(r'[。；]', x.get('note') or '')[0])
        if SEASONAL.search(core) or SEASONAL.search(s):
            drop('niche：季节限定'); continue
        if MALL_TEXT.search(s) or BASE_TEXT.search(s):
            s = ''
        c = {'k': 'niche|' + x['id'], 'i': '', 'n': core, 'c': x.get('prov') or '', 'a': round(x['lat'], 3), 'o': round(x['lng'], 3), 't': 'sg', 'd': DUR_DEFAULT,
             's': s, 'q': core, 'x': {}, 'p': 0, 'ds': x['dest'], '_rids': set(), '_names': {core}, '_qtok': set(), '_skey': '', '_niche': 1}
        cands.append(c)
    n_niche_in = len(cands) - n_after_filters

    # 3 合并（同名 15km / 名字包含 1.5km / 250m 同处）；领头的是被线路用得多的、有一句话的
    cands.sort(key=lambda c: (-len(c['_rids']), 0 if c['s'] else 1, 0 if c['x'] else 1, 1 if c.get('ap') else 0, c['k']))
    leaders = []
    grid = collections.defaultdict(list)
    G = 0.25                                      # 约 27 公里的桶；同名合并最远 15 公里
    merged = collections.Counter()
    for c in cands:
        pt = (c['a'], c['o'])
        gi, gj = int(math.floor(pt[0] / G)), int(math.floor(pt[1] / G))
        into = None
        for di_ in (-1, 0, 1):
            for dj_ in (-1, 0, 1):
                for L in grid.get((gi + di_, gj + dj_), ()):
                    dd = M.km(pt, (L['a'], L['o']))
                    if dd <= MERGE_SPOT_KM:
                        into, why = L, '250 米内同处'
                    elif dd <= MERGE_CONTAIN_KM and any(a != b and (a in b or b in a) and min(len(a), len(b)) >= 3 for a in c['_names'] for b in L['_names']):
                        into, why = L, '名字互相包含且 1.5 公里内'
                    elif dd <= MERGE_CONTAIN_KM and (any(w in L['_names'] for w in c['_qtok']) or any(w in c['_names'] for w in L['_qtok'])):
                        into, why = L, '导航词点名了对方且 1.5 公里内'
                    elif dd <= MERGE_SAME_NAME_KM and (c['_names'] & L['_names']):
                        into, why = L, '同名且 15 公里内'
                    if into:
                        break
                if into:
                    break
            if into:
                break
        if into:
            merged[why] += 1
            if os.environ.get('NP_DEBUG'):
                print('MERGE', why, '|', c['c'], c['n'], '<-', L['n'], '%.2fkm' % M.km((c['a'], c['o']), (L['a'], L['o'])))
            L = into
            L['_rids'] |= c['_rids']
            L['_names'] |= c['_names']
            if not L['s'] and c['s'] and not (SEASONAL.search(c['s']) or MALL_TEXT.search(c['s']) or BASE_TEXT.search(c['s'])):
                L['s'] = c['s']
            if not L['x'] and c['x']:
                L['x'] = c['x']
            if c['n'] != L['n'] and c['n'] not in L.setdefault('al', []) and len(L['al']) < 3 and len(c['n']) <= 12:
                L['al'].append(c['n'])
            continue
        leaders.append(c)
        grid[(gi, gj)].append(c)
    for c in leaders:
        c['p'] = len(c['_rids'])
        c['i'] = hashlib.md5(('%s|%s|%.2f|%.2f' % (c['n'], c['c'], c['a'], c['o'])).encode('utf-8')).hexdigest()[:8]
    # id 撞了（极少）：加后缀
    seen = collections.Counter()
    for c in sorted(leaders, key=lambda c: c['k']):
        seen[c['i']] += 1
        if seen[c['i']] > 1:
            c['i'] += chr(96 + seen[c['i']])
    pool = sorted(leaders, key=lambda c: (c['a'], c['o'], c['i']))

    # 4 分片
    shards = collections.defaultdict(list)
    for c in pool:
        shards[M.cell_key(c['a'], c['o'])].append(c)
    os.makedirs(OUT, exist_ok=True)
    for f in os.listdir(OUT):
        if f.endswith('.js') or f in ('pool.json', 'stats.json'):   # 这个目录是本脚本独占的
            os.remove(os.path.join(OUT, f))
    KEYS = ('i', 'n', 'c', 'a', 'o', 't', 'd', 's', 'q', 'x', 'p', 'ds', 'ev', 'ap', 'al')
    sizes = {}
    gz_total = 0
    for key, lst in sorted(shards.items()):
        rows = []
        for c in lst:
            r = {k: c[k] for k in KEYS if k in c and (c[k] or k in ('a', 'o', 'd', 'p'))}
            if r.get('q') == r['n']:
                del r['q']                      # 导航词和名字相同就不写：客户端 q = q || n
            if c['ds'] not in FOREIGN:
                r.pop('ds', None)               # 国内不写：没有 ds = 国内（国内线的 dest 标得不准，不用来过滤）；国外写，只在同国家内找
            rows.append(r)
        body = "(window.ZNP=window.ZNP||{})['%s']=%s;\n" % (key, json.dumps(rows, ensure_ascii=False, separators=(',', ':')))
        data = body.encode('utf-8')
        open(os.path.join(OUT, key + '.js'), 'wb').write(data)
        sizes[key] = len(data)
        gz_total += len(gzip.compress(data, 9))
    # 有数据的格的清单：客户端只请求清单里的格（没有清单就分不清“这格没有景点（404）”和“没网”）
    idx = "window.ZNP_CELLS=%s;\n" % json.dumps(sorted(sizes), separators=(',', ':'))
    open(os.path.join(OUT, '_index.js'), 'w', encoding='utf-8').write(idx)
    full = [{k: c[k] for k in ('k',) + KEYS if k in c} for c in pool]
    json.dump(full, open(os.path.join(OUT, 'pool.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))

    # 5 统计
    dom = sum(1 for c in pool if c['ds'] not in FOREIGN)
    bytype = collections.Counter(c['t'] for c in pool)
    stats = {
        'units': total_units, 'after_filters': n_after_filters, 'niche_open': n_niche_open, 'niche_added_before_merge': n_niche_in,
        'dropped': dict(F), 'merged': dict(merged), 'pool': len(pool), 'domestic': dom, 'foreign': len(pool) - dom,
        'by_type': dict(bytype.most_common()), 'with_sentence': sum(1 for c in pool if c.get('s')), 'with_ticket': sum(1 for c in pool if c.get('x')),
        'with_booking': sum(1 for c in pool if c.get('x', {}).get('b')), 'evening': sum(1 for c in pool if c.get('ev')), 'approx': sum(1 for c in pool if c.get('ap')),
        'niche_in_pool': sum(1 for c in pool if c['k'].startswith('niche|')),
        'shards': len(sizes), 'shard_total_bytes': sum(sizes.values()), 'shard_max_bytes': max(sizes.values()), 'shard_max_key': max(sizes, key=sizes.get),
        'shard_gzip_total_bytes': gz_total, 'shard_median_bytes': int(statistics.median(sizes.values())),
        'shard_over_limit': [k for k, v in sizes.items() if v > SHARD_MAX_BYTES],
    }
    json.dump(stats, open(os.path.join(OUT, 'stats.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if quiet:
        print('池 %d（国内 %d / 国外 %d）· 分片 %d 个，共 %.0f KB（gzip %.0f KB），最大 %s %.1f KB' % (
            stats['pool'], dom, len(pool) - dom, stats['shards'], stats['shard_total_bytes'] / 1024, gz_total / 1024, stats['shard_max_key'], stats['shard_max_bytes'] / 1024))
        return stats
    print('候选池漏斗（单位：线路里出现过的唯一 (城市, q)）')
    print('  起点 %d' % total_units)
    for k_, v_ in F.items():
        print('  - %-60s %5d' % (k_, v_))
    print('  = 过滤后 %d；并入 niche open %d 个里新增 %d' % (n_after_filters, n_niche_open, n_niche_in))
    print('  合并（同址/同名/包含）：' + '，'.join('%s %d' % (k_, v_) for k_, v_ in merged.items()))
    print('  最终池 %d：国内 %d · 国外 %d · 来自 niche %d' % (stats['pool'], dom, len(pool) - dom, stats['niche_in_pool']))
    print('  类型：' + ' '.join('%s %d' % kv for kv in bytype.most_common()))
    print('  有一句话 %d · 有门票/时间信息 %d · 要预约 %d · 晚上才有意义 %d · 坐标近似 %d' % (
        stats['with_sentence'], stats['with_ticket'], stats['with_booking'], stats['evening'], stats['approx']))
    print('分片（3° 网格）：%d 片 · 共 %.1f KB（gzip %.1f KB）· 中位 %.1f KB · 最大 %s = %.1f KB · 超过 30 KB 的片 %d' % (
        stats['shards'], stats['shard_total_bytes'] / 1024, gz_total / 1024, stats['shard_median_bytes'] / 1024, stats['shard_max_key'], stats['shard_max_bytes'] / 1024, len(stats['shard_over_limit'])))
    print('输出：%s' % os.path.relpath(OUT, ROOT))
    return stats


if __name__ == '__main__':
    build(quiet='--quiet' in sys.argv)
