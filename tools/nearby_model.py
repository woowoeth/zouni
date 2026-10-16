#!/usr/bin/env python3
"""「顺路加一站 / 换一站」的车程与绕路模型（Python 版）。

设计：docs/handoff/design-nearby-stops.md §3。JS 版是 site_src/np_model.js，两边必须逐位一致
（tests/nearby_parity.py 每次随机抽 500 对坐标 × 3 种出行方式比对，差值必须为 0 分钟）。

车程 leg() 严格复刻 tools/compile_itineraries.py::leg（去掉 via 分支：新站没有作者写的车程）。
不直接 import 那个文件：它在模块层就读 build/routes.js 并开始编译。取而代之，
tests/nearby_parity.py 用 ast 把 compile_itineraries.leg 的源码抽出来 exec，和这里逐对比较，
所以那边改了数字，这边的闸会红。

模式 mode（由“当天”决定，写在页面 section.day[data-lm]，客户端不要猜）：
  drive  线路是自驾线（compile 里的 SELF）
  rural  国内（目的地不在 ASIA_CC）且当天城市不在 BIG_CITIES（compile 里的 RURAL）
  city   其余
"""
import math
import re

# ---------------------------------------------------------------- 常量（设计文档里的公式和阈值）
ROUTE_FACTOR = 1.25            # 直线距离 → 路程
WALK_KM = 1.3                  # 路程 < 1.3 公里：步行 4.5km/h
DETOUR_MAX = 30                # 顺路阈值（分钟）：用户 2026-10-16 拍板 30
REPLACE_NEAR_MAX = 30          # 替换：新站离被换的站 ≤ 30 分钟车程（同一片区）
F_MIN, F_MAX = 0.8, 2.0        # 作者写的车程 / 模型车程 的比例夹在这个范围
SHOW_STEP = 5                  # 显示取整到 5 分钟
MAX_NONMEAL = 4                # 当天非吃饭站（see/fun）≤ 4（仅限插入）
END_LIMIT = 22 * 60 + 30       # 当天结束 ≤ 22:30
SPAN_LIMIT = 10 * 60           # 当天第一行到最后一行 ≤ 10 小时
SAME_SPOT_KM = 0.25            # 250 米内视为同处：不出现在列表里
BESIDE_KM = 0.6                # 250–600 米：出现，标“就在旁边”
REACH_KM = 35                  # 候选离参照点直线 > 35 公里不参与
LIST_MAX = 5                   # 候选列表最多 5 个
BBOX_PAD = 0.35                # 取片包围盒 ±0.35°（约 35 公里）
GRID = 3                       # 3° 网格
# 排序
W_HAS_SENTENCE = 6
W_POP_CAP, W_POP_K = 6, 2      # min(6, 2*ln(1+被几条线用过))
W_SAME_KIND = 4
F_SLOW, W_SLOW = 1.4, 3        # f > 1.4（山路慢，估算不准）扣 3
W_APPROX, APPROX_DELTA = 8, 20  # 坐标是“近似”且 Δ ≥ 20 扣 8
KIND_WORDS = ('寺', '馆', '园', '街', '塔', '山', '湖')

BIG_CITIES = ('北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安', '厦门', '苏州', '青岛', '天津', '长沙', '香港', '澳门', '佐敦', '郑州', '沈阳', '大连', '哈尔滨', '昆明', '南宁', '福州', '济南', '合肥', '南昌', '贵阳', '兰州', '乌鲁木齐', '呼和浩特', '石家庄', '太原', '宁波', '无锡', '扬州', '洛阳', '开封', '泉州', '三亚', '海口', '桂林', '拉萨')
MODES = ('city', 'rural', 'drive')


# ---------------------------------------------------------------- 距离和车程
def km(a, b):
    r = math.pi / 180
    dl = (b[1] - a[1]) * r
    p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def r5(x):
    """和 compile_itineraries.r5 相同：Python 的 round 是“银行家舍入”（x.5 取偶），JS 版要复刻这一点"""
    return int(5 * round(x / 5.0))


def mode_of_day(drive, domestic, city):
    """当天的出行方式。drive：自驾线；domestic：目的地不在 ASIA_CC；city：当天城市"""
    if drive:
        return 'drive'
    if domestic and city not in BIG_CITIES:
        return 'rural'
    return 'city'


def leg(a, b, mode='city'):
    """两点之间 → (怎么走, 分钟, 公里)。a、b 是 (lat, lng)。没有 via 分支。"""
    if not a or not b:
        return '打车', 20, None
    d = km(a, b) * ROUTE_FACTOR
    if d < WALK_KM:
        return '步行', max(5, r5(d / 4.5 * 60)), None
    if mode == 'drive':
        if d < 20:
            return '开车', max(10, r5(d / 30 * 60 + 5)), round(d)
        return '自驾约', r5(d / 70 * 60 + 10), round(d)
    if mode == 'rural' and d >= 12:
        return '包车约', r5(d / 50 * 60 + 10), round(d)
    if d < 20:
        return '打车', max(10, r5(d / 25 * 60 + 8)), round(d)
    if d < 60:
        return '打车约', r5(d / 55 * 60 + 10), round(d)
    return '包车约', r5(d / 65 * 60 + 10), round(d)


def t(a, b, mode='city'):
    return leg(a, b, mode)[1]


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def factor(a, b, t0, mode='city'):
    """f = clamp(t0(A,B) / t(A,B), 0.8, 2.0)；t0 缺失 f=1。山路比直线慢，把作者的经验按比例带到新路段"""
    if not t0:
        return 1.0
    return clamp(t0 / float(t(a, b, mode)), F_MIN, F_MAX)


def show5(x):
    """显示用：取整到 5 分钟（和 r5 同一种舍入）"""
    return r5(x)


# ---------------------------------------------------------------- 绕路
def detour_insert(A, B, X, t0_AB=None, mode='city'):
    """把 X 插在 A 之后、B 之前：Δ = f·(t(A,X)+t(X,B)) − t0(A,B)，取 max(0, …)。
    B 缺失（当天最后一站且没有住处坐标）：只算去程 t(A,X)。"""
    if B is None:
        return float(t(A, X, mode))
    f = factor(A, B, t0_AB, mode)
    base = t0_AB if t0_AB else t(A, B, mode)
    return max(0.0, f * (t(A, X, mode) + t(X, B, mode)) - base)


def detour_replace(A, S, C, X, t0_AS=None, t0_SC=None, mode='city'):
    """把 S 换成 X：Δ = f1·t(A,X) + f2·t(X,C) − t0(A,S) − t0(S,C)（可以为负：省路，不取 max）。
    A 或 C 缺失（当天第一站没有起点 / 最后一站没有住处）：那一侧不算。
    另要求 replace_near(S, X)；这里不判，调用方判。"""
    d = 0.0
    if A is not None:
        f1 = factor(A, S, t0_AS, mode)
        d += f1 * t(A, X, mode) - (t0_AS if t0_AS else t(A, S, mode))
    if C is not None:
        f2 = factor(S, C, t0_SC, mode)
        d += f2 * t(X, C, mode) - (t0_SC if t0_SC else t(S, C, mode))
    return d


def replace_near(S, X, mode='city'):
    return t(S, X, mode) <= REPLACE_NEAR_MAX


def detour_ok(delta):
    return delta <= DETOUR_MAX


# ---------------------------------------------------------------- 当天预算
def day_budget_ok(rows, inserting=True):
    """rows：这一天（试算重排之后）每一行 {s: 开始分钟, e: 结束分钟, k: 'see'|'fun'|'eat'|'dep'|'stay'}。
    返回 {ok, reason, n, first, last, span}；reason ∈ '' | 'full' | 'late' | 'long'。
    非吃饭站 = see + fun；“≤4”只在 inserting 时判（替换不增加站数）。"""
    n = 0
    first = None
    last = 0
    for r in rows:
        if r['k'] in ('see', 'fun'):
            n += 1
        e = r.get('e')
        if e is None:
            e = r['s']
        first = r['s'] if first is None or r['s'] < first else first
        last = e if e > last else last
    first = 0 if first is None else first
    span = last - first
    reason = ''
    if inserting and n > MAX_NONMEAL:
        reason = 'full'
    elif last > END_LIMIT:
        reason = 'late'
    elif span > SPAN_LIMIT:
        reason = 'long'
    return {'ok': reason == '', 'reason': reason, 'n': n, 'first': first, 'last': last, 'span': span}


# ---------------------------------------------------------------- 同处 / 范围 / 开放时间
def same_spot(cand, refs):
    """候选和当天任一站的最近距离：<250 米 'same'（不出现）；<600 米 'beside'（标“就在旁边”）；否则 ''"""
    best = None
    for p in refs:
        if p is None:
            continue
        d = km(cand, p)
        best = d if best is None or d < best else best
    if best is None:
        return ''
    if best < SAME_SPOT_KM:
        return 'same'
    if best < BESIDE_KM:
        return 'beside'
    return ''


def in_reach(cand, refs):
    """离任一参照点直线 ≤ 35 公里"""
    for p in refs:
        if p is not None and km(cand, p) <= REACH_KM:
            return True
    return False


_HRS = re.compile(r'(\d{1,2}):(\d{2})\s*[–—~\-至]\s*(\d{1,2}):(\d{2})')


def parse_hours(h):
    """“8:30–17:00（冬季到 16:30）” → (510, 1020)；解析不出 → None。取第一个时间段"""
    m = _HRS.search(h or '')
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2)), int(m.group(3)) * 60 + int(m.group(4))


def hours_ok(arrive, dur, h):
    """到达 + min(停留, 60) ≤ 关门；没有开放时间信息 → 通过（第一版不声称实时开放）"""
    p = parse_hours(h)
    if not p:
        return True
    return arrive + min(dur, 60) <= p[1]


def closed_on(cl, weekday):
    """cl：闭馆日（JS 周几，0=周日…6=周六，None 表示没有信息）；weekday 同一套"""
    return cl is not None and cl == weekday


# ---------------------------------------------------------------- 排序
def kind_words(s):
    return [w for w in KIND_WORDS if w in (s or '')]


def same_kind(cand_t, cand_n, ref_t, ref_n, day_title):
    """同类型：类型码相同，或名字/当天标题共享类别词（寺 馆 园 街 塔 山 湖）"""
    if cand_t and ref_t and cand_t == ref_t:
        return True
    ck = kind_words(cand_n)
    if not ck:
        return False
    rk = kind_words(ref_n) + kind_words(day_title)
    for w in ck:
        if w in rk:
            return True
    return False


def rank_score(c):
    """c: {delta, has_s, pop, same, f, approx}。不奖励“省路”：用 max(Δ,0)"""
    dp = c['delta'] if c['delta'] > 0 else 0.0
    s = -dp
    if c.get('has_s'):
        s += W_HAS_SENTENCE
    s += min(W_POP_CAP, W_POP_K * math.log(1 + (c.get('pop') or 0)))
    if c.get('same'):
        s += W_SAME_KIND
    if (c.get('f') or 1.0) > F_SLOW:
        s -= W_SLOW
    if c.get('approx') and c['delta'] >= APPROX_DELTA:
        s -= W_APPROX
    return s


def rank(cands, limit=LIST_MAX):
    """按分数降序；同分按绕路少、再按 id 字符串（保证两边顺序一致）；取前 limit 个，不凑数"""
    out = []
    for c in cands:
        d = dict(c)
        d['score'] = rank_score(c)
        out.append(d)
    out.sort(key=lambda d: (-d['score'], d['delta'], str(d.get('id', ''))))
    return out[:limit]


# ---------------------------------------------------------------- 3° 网格
def cell(lat, lng):
    """点 → (纬格, 经格)：floor((lat+90)/3), floor((lng+180)/3)，都是非负整数，文件名 <纬格>_<经格>.js"""
    return int(math.floor((lat + 90) / GRID)), int(math.floor((lng + 180) / GRID))


def cell_key(lat, lng):
    a, b = cell(lat, lng)
    return '%d_%d' % (a, b)


def shards_for(bbox):
    """bbox = [minLat, minLng, maxLat, maxLng]：外扩 ±0.35° 后覆盖到的所有格 → ['纬格_经格', …]（排好序）"""
    a0, b0 = cell(bbox[0] - BBOX_PAD, bbox[1] - BBOX_PAD)
    a1, b1 = cell(bbox[2] + BBOX_PAD, bbox[3] + BBOX_PAD)
    out = []
    for a in range(a0, a1 + 1):
        for b in range(b0, b1 + 1):
            out.append('%d_%d' % (a, b))
    return out
