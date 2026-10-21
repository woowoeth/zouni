# 声明式行程 → 线路页数据
# 用法：python3 tools/compile_itineraries.py build/routes.js   （把编译结果并进已有的 routes.js）
import json, zlib, math, os, re, sys, time, urllib.parse, urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else 'build/routes.js'
IT = json.load(open('data/itineraries.json'))['itineraries']
CAT = {d['id']: d for d in json.load(open('data/catalog/destinations.json'))['destinations']}
TRIPS = {t['id']: t for t in json.load(open('data/catalog/trips.json'))['trips']}
GP = 'data/geo/pois.json'
GEO = json.load(open(GP)) if os.path.exists(GP) else {}
DUR = {'sight': 120, 'museum': 150, 'street': 90, 'park': 60, 'food': 60, 'night': 60, 'fun': 90}
UA = {'User-Agent': 'zouni-travel-data/1.0 (zouni.app)'}


CC = {'macau': 'mo', 'hongkong': 'hk'}
ASIA_CC = {x['id']: x['cc'] for k_ in ('asia', 'world') for x in json.load(open('data/destinations.json')).get(k_, [])}
ASIA_CC['taiwan'] = 'tw'     # 台湾在“国内”的港澳台里，但地图、导航、估价都按境外那一套走（高德不覆盖台湾）
CC.update(ASIA_CC)
CUR_CC = ['cn']


def geocode(q, city, base=None, alt=None):
    key = city + '|' + q
    if key in GEO and (GEO[key] or GEO.get(key + '#tried')): return GEO[key]
    for query in [x for x in (q, city + ' ' + q, alt and city + ' ' + alt) if x]:
        u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': query, 'format': 'json', 'limit': 1, 'countrycodes': CUR_CC[0], 'accept-language': 'zh'})
        try:
            r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()); time.sleep(1.1)
        except Exception:
            r = []; time.sleep(2)
        if r and base and km(base, (float(r[0]['lat']), float(r[0]['lon']))) > 220:
            r = []   # 查到了外地的同名地方，不要
        if r:
            GEO[key] = {'lat': float(r[0]['lat']), 'lng': float(r[0]['lon']), 'hit': r[0]['display_name'][:60], 'q': query}
            json.dump(GEO, open(GP, 'w'), ensure_ascii=False, indent=1)
            return GEO[key]
    GEO[key] = None; GEO[key + '#tried'] = True; json.dump(GEO, open(GP, 'w'), ensure_ascii=False, indent=1)
    return None


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def r5(x): return int(5 * round(x / 5.0))
def hm(m): return '%02d:%02d' % (m // 60, m % 60)
def mm(t): h, m = t.split(':'); return int(h) * 60 + int(m)
def dur_txt(m): return (f'{m // 60} 小时' + (f' {m % 60} 分' if m % 60 else '')) if m >= 60 else f'{m} 分钟'


SELF = [False]


BIG_CITIES = {'北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安', '厦门', '苏州', '青岛', '天津', '长沙', '香港', '澳门', '佐敦', '郑州', '沈阳', '大连', '哈尔滨', '昆明', '南宁', '福州', '济南', '合肥', '南昌', '贵阳', '兰州', '乌鲁木齐', '呼和浩特', '石家庄', '太原', '宁波', '无锡', '扬州', '洛阳', '开封', '泉州', '三亚', '海口', '桂林', '拉萨'}
RURAL = [False]   # 乡下：村子、景区之间打不到车，十几公里以上按包车写


SELFV = [False]


def leg(a, b, via=None):
    """两点之间：怎么走、多久、多远（自驾线路写开车）"""
    if via:
        h = re.search(r'(\d+) 小时', via); m2 = re.search(r'(\d+) 分钟', via) or re.search(r'小时 (\d+) 分', via)      # “3 小时 30 分”（分后面没有“钟”）也要认：以前只认“分钟”，30 分丢了、还留在文字里，卡片上成了“自驾约 30 分 3 小时”（2026-10-20）
        mins = (int(h.group(1)) * 60 if h else 0) + (int(m2.group(1)) if m2 else 0)
        _v = re.sub(r'\s*\d+ 小时(?: \d+ 分(?!钟))?', '', re.sub(r'\s*\d+ 分钟', '', via)).strip()
        if SELFV[0] and _v.startswith('包车'): _v = '自驾' + _v[2:]      # 自驾线里没有“包车”：租了车就是自己开（澳洲、新西兰、冰岛的山路没有别的车可包）
        return _v, (mins or 25), None
    if not a or not b: return '打车', 20, None
    d = km(a, b) * 1.25
    if d < 1.3: return '步行', max(5, r5(d / 4.5 * 60)), None
    if SELF[0]:
        if d < 20: return '开车', max(10, r5(d / 30 * 60 + 5)), round(d)
        return '自驾约', r5(d / 70 * 60 + 10), round(d)
    if RURAL[0] and d >= 12: return ('自驾约' if SELFV[0] else '包车约'), r5(d / 50 * 60 + 10), round(d)
    if d < 20: return '打车', max(10, r5(d / 25 * 60 + 8)), round(d)
    if d < 60: return '打车约', r5(d / 55 * 60 + 10), round(d)
    return ('自驾约' if SELFV[0] else '包车约'), r5(d / 65 * 60 + 10), round(d)


def short(n): return re.split(r'\s*·\s*', n)[0]


def back_leg(prev, stay_pt, far, roundtrip, legmax=0, outhow=''):
    # 第 1 天（到达日）调用时 legmax 传 0：那一天最长的去程是从出发城市过来的，不能当返程，只用坐标估算
    """当天最后一站离住处城市很远、而且第二天还以同一座城为基点（当天来回）时，回住处要算车程（原来只写“回去歇一下”，车程被吞掉）。
    换城市的搬家日不算：那天晚上就住在远处。返回 (文字, 分钟, 是不是开车)"""
    if roundtrip and far(prev) and stay_pt:
        how, mins, dist = leg(prev, stay_pt, None)
        est = mins
        if legmax >= 60 and outhow: how = outhow     # 去的时候坐什么，回来也坐什么（火车去就火车回）
        if SELFV[0] and how.startswith('包车'): how = '自驾' + how[2:]
        if legmax >= 60: mins = legmax     # 作者写明了去程时间：返程按去程算（景区路去回基本对称），不用坐标估算（坐标可能不准，估出来会和去程自相矛盾）
        # 超过 8 小时多半是“住处所在城市的中心点”不对，不当成当天来回
        if 60 <= mins <= 480:
            show_dist = dist and dist >= 5 and (legmax < 60 or 0.6 <= est / legmax <= 1.6)   # 估算和去程差太多，说明坐标不可信，公里数不写
            return f'回住处 · {how} {dur_txt(mins)}' + (f' · {dist} 公里' if show_dist else ''), mins, how.startswith(('包车', '自驾', '开车'))
    return None


_GSTAY = re.compile(r'(附近|市区|县城|老城|古城|市中心|城里|边上|一带|营地|客栈|民宿)$')


def move_leg(prev, d, last, rt, sc, dbase):
    """搬家日（今晚住的不是今天出发的城）：最后一站 → 当晚住处的路程。
    原来只有“当天来回”才算回住处，搬家日一律写“回去歇一下”：xb96a 48 天、xl1a 3 天最后一段开车（几十到几百公里）没算进当天，
    哈密 → 额济纳那一天显示“不开车”实为约 7 小时 40 分（2026-10-20）。只对自驾 / 包车线路算（坐火车换城的搬家日方式不明，不猜）。
    目标点：住处有可信坐标（离最后一站 ≤250 公里）就用住处，否则用住处所在城的中心（≤400 公里）。返回和 back_leg 同形的 (文字, 分钟, True) 或 None"""
    if last or not prev or not d.get('stay') or not SELFV[0]: return None      # rt（当天来回）的由 back_leg 管；它只在最后一站离城 >60 公里时才写，40–60 公里的（北极村 → 漠河西林吉 59 公里）落在缝里，下面 rt 时按 ≥40 公里补
    if d.get('stay_via'):     # 作者写明了最后一站到住处的车程（stay_via）：OSRM 在新藏线 / 川藏线不准，或同一路段别的线已有定论，就按它
        _v, _m, _x = leg(None, None, d['stay_via'])
        return f'回住处 · {_v} {dur_txt(_m)}', _m, _v.startswith(('自驾', '开车', '包车'))
    cands = []
    if sc and sc.get('lat') is not None: cands.append(((sc['lat'], sc['lng']), 700))
    core = _GSTAY.sub('', d['stay']).strip()
    cg = GEO.get(core + '|' + core) if core else None
    if cg and cg.get('lat') is not None: cands.append(((cg['lat'], cg['lng']), 700))
    if len(cands) == 2 and km(cands[0][0], cands[1][0]) > 40: cands = cands[::-1]      # 住处坐标和“住的那座城”中心差 >40 公里：信城市中心（build_site 的住处点同一把尺），不信可能被同名地拉远的住处点
    for pt_, lim in cands:
        dd = km(prev, pt_) * 1.25
        if km(prev, pt_) < 25 or km(prev, pt_) > lim or (rt and km(prev, pt_) < 40): continue      # 离住处 <25 公里（直线）的不算“到住处”：最后一站就在住的城里（阳朔西街 → 阳朔城中心 9.5 公里写成“打车 35 分钟”，第一版给 159 个天加了这种噪音）
        how, mins, dist = leg(prev, pt_, None)
        if km(prev, pt_) >= 200:      # 远路：高速为主，按 1.15 倍直线、85 公里/小时（哈密 → 额济纳直线 630 公里，OSRM 679 公里 / 7 小时 40 分；原 leg 的 70 公里/小时会写成 11 小时）
            dist = round(km(prev, pt_) * 1.15); mins = r5(dist / 85 * 60 + 10); how = '自驾约'
        if mins > 780: continue
        if how.startswith('包车'): how = '自驾' + how[2:]
        return f'回住处 · {how} {dur_txt(mins)}' + (f' · {dist} 公里' if dist and dist >= 5 else ''), mins, True
    return None


def dp(city, kw): return 'https://www.dianping.com/ai-search?keyword=' + urllib.parse.quote(city + ' ' + kw)


s = open(OUT, encoding='utf-8').read()
ORDER = json.loads(re.search(r'window.ZOUNI_ORDER=(\[.*?\]);', s).group(1))
ROUTES = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', s).group(1))
report = []
CITY_FOOD = json.load(open('data/catalog/city_food.json')) if os.path.exists('data/catalog/city_food.json') else {}
# 同一条行程里不重复推荐同一道菜：城市招牌菜用完后，从节目里拍过的本省吃的里挨个补（舌尖、风味、老广等；早餐中国不算，那是早餐）
REGION_FOOD = {}
for _f in ('shejian', 'fengwei', 'docs_more', 'docs_more2', 'docs_travel'):
    _p = f'data/catalog/{_f}.json'
    if not os.path.exists(_p): continue
    for _x in json.load(open(_p, encoding='utf-8')):
        if (_x.get('show') or '舌尖上的中国') in ('舌尖上的中国', '风味人间', '风味原产地', '人生一串', '宵夜江湖', '老广的味道', '街头美食') and _x.get('food') and _x['food'] != _x.get('place') and len(_x['food']) <= 12 and not any(w_ in _x['food'] for w_ in ('节', '（', '(', '季', '之')):
            REGION_FOOD.setdefault(_x['prov'], []).append((_x['food'], _x['place']))
def _dup(tok, seen):
    """这道菜和已经吃过的是不是同一道（“呱呱”和“天水呱呱”算一道）"""
    return tok in seen or any(len(tok) >= 2 and len(u) >= 2 and (tok in u or u in tok) for u in seen)


DISH_NOTE = json.load(open('data/catalog/dish_note.json', encoding='utf-8')) if os.path.exists('data/catalog/dish_note.json') else {}   # 外地人看不懂的菜名后面加一个括号说明：{原菜名: 带说明的菜名}
PROV_FOOD = json.load(open('data/catalog/prov_food.json', encoding='utf-8')) if os.path.exists('data/catalog/prov_food.json') else {}   # 各省区市、各国的特色菜（成批补充，见 docs/handoff/03）
CITY_TAGS = ['新奥尔良', '波士顿', '芝加哥', '纽约', '旧金山', '洛杉矶', '得州', '德州', '费城', '拉斯维加斯', '迈阿密', '西雅图', '夏威夷', '缅因', '加州', '堪萨斯', '孟菲斯', '纳什维尔', '底特律', '奥斯汀', '休斯敦', '圣路易斯', '波特兰', '新墨西哥', '路易斯安那', '蒙特利尔', '魁北克', '多伦多', '温哥华', '悉尼', '墨尔本', '布里斯班', '珀斯', '阿德莱德', '塔斯马尼亚', '开普敦', '约翰内斯堡', '墨西哥城', '瓦哈卡', '尤卡坦', '马德里', '巴塞罗那', '塞维利亚', '巴斯克', '里昂', '巴黎', '马赛', '罗马', '那不勒斯', '西西里', '佛罗伦萨', '威尼斯', '伦敦', '爱丁堡', '东京', '大阪', '京都', '札幌', '福冈', '首尔', '釜山', '曼谷', '清迈', '胡志明', '河内', '新德里', '孟买']
GENERIC_OK = {'随意', '简单吃一点', '路上吃', '本地菜', '小吃'} | set(['当地家常菜', '时令蔬菜小炒', '街边小吃', '本地汤面', '炒一桌家常', '小火锅', '烧烤', '饺子或面片', '粥配小菜', '砂锅煲', '烩菜', '炖菜', '家常小炒', '卤味拼盘', '米饭套餐', '包子配豆浆', '凉菜加热菜', '烙饼卷菜'])

NOTMEAL = ('糖', '酥', '糕', '酒', '宵夜', '酱', '茶', '饼干', '月饼', '粽', '蜜饯', '奶', '冰', '清补凉', '铜锣烧', '鲷鱼烧', '今川烧', '大福', '团子', '味噌汤', '杭白菊', '石斛')      # 后几个：甜点和配汤不是一顿饭（九州线晚饭铜锣烧、尾道晚饭鲷鱼烧、东京午饭味噌汤、乌镇晚饭杭白菊、桂林晚饭野生石斛）
def _notmeal(c):
    h = c.split('、')[0].strip()
    if h in ('葡萄', '哈密瓜', '西瓜', '水果'): return True      # 吐鲁番晚饭“葡萄”（整个词才算：葡萄牙黑猪火腿、葡萄叶包饭是菜）
    if any(w_ in h for w_ in ('糖醋', '酥肉', '酥鱼', '酱肘', '酱鸭', '酱牛肉', '酱骨', '豆酱', '酒糟', '醉', '茶油', '汤圆')): return False
    return any(w_ in h for w_ in NOTMEAL)
WILD = ('鸡枞', '松茸', '牛肝菌', '见手青', '干巴菌', '羊肚菌', '竹荪', '菌子', '野生菌', '荔枝', '杨梅', '青梅', '蟹黄', '大闸蟹', '阳澄湖')   # 有季节的：野生菌和时令果、蟹
WILD_MON = {'鸡枞': (6, 10), '松茸': (7, 10), '牛肝菌': (6, 10), '见手青': (6, 10), '干巴菌': (6, 10), '羊肚菌': (3, 5), '竹荪': (5, 10), '菌子': (6, 10), '野生菌': (6, 10), '荔枝': (5, 8), '杨梅': (5, 7), '青梅': (4, 6), '蟹黄': (9, 12), '大闸蟹': (9, 12), '阳澄湖': (9, 12)}
def _offseason(c, month):
    h = c.split('、')[0].strip()
    for w_, (a_, b_) in WILD_MON.items():
        if w_ in h and not (a_ <= month <= b_): return True
    return False
CUR_CITY = [None]
# ——— 2026-10-17 国外线时间表常识 ———
# 晚饭默认时间：欧洲多数餐厅 19:00 后才开（欧洲 19:30，西班牙/意大利 20:00）；日本、东南亚、国内维持原来的 18:30（“出发 → 吃晚饭”18:10，饭 18:30）。
# 只改默认：作者在数据里写明的 at（定点）不动。MEAL0 = 最早开饭的钟点（分钟）；DEP_T = 从住处出发去吃晚饭的钟点 = 饭点 - 20 分钟（国内保持 18:10）
EU_REGION = {x['id'] for x in json.load(open('data/destinations.json')).get('world', []) if x.get('region') == '欧洲'}
def meal0_of(dest):
    if dest in ('spain', 'italy'): return 20 * 60
    if dest in EU_REGION: return 19 * 60 + 30
    return 18 * 60
# 机场/车站 → 住处的默认分钟（按城市类型，不写具体班次）：市区机场远的大城市 60；机场离市区很近的紧凑城市 30；山、岛、湖、村、镇这类要转车的 75；其余 45
AIR_FAR = {'东京', '大阪', '京都', '首尔', '伦敦', '伊斯坦布尔', '雷克雅未克', '吉隆坡', '开罗', '米兰', '纽约', '曼谷', '札幌', '釜山', '福冈', '广岛', '慕尼黑', '布鲁塞尔'}
AIR_NEAR = {'新加坡', '迪拜', '马德里', '里斯本', '阿姆斯特丹', '维也纳', '马累', '马拉喀什', '悉尼', '拉斯维加斯', '旧金山', '赫尔辛基', '都柏林', '布拉格', '巴塞罗那', '多哈', '塔什干', '第比利斯', '安曼', '雅典'}
AIR_REMOTE = re.compile(r'岛|湖|村|镇|谷|山|沙漠|港$|角$|格伦达')
def air_min(city):
    c = city or ''
    if c in AIR_FAR: return 60
    if c in AIR_NEAR: return 30
    if AIR_REMOTE.search(c): return 75
    return 45
# 瑞士、奥地利：缆车、齿轨火车、登山火车是山里的常态，自动配的“打车”不对
ALPINE = {'switzerland', 'austria'}
MOUNT_RE = re.compile(r'缆车|齿轨|索道|登山|山顶|少女峰|铁力士|马特洪|皮拉图斯|里吉|格拉特|冰川|山$|峰$|观景台')
TRAIL_RE = re.compile(r'步道|徒步|小径|栈道|环湖')
_DISH_PLACE = {}
for _p_, _l_ in REGION_FOOD.items():
    for _f_, _pl_ in _l_:
        if _pl_: _DISH_PLACE.setdefault(_f_, []).append(_pl_)
ALIAS_PLACE = {'巴陵': '岳阳', '羊城': '广州', '金陵': '南京', '燕京': '北京', '姑苏': '苏州'}
def _prefix_place(h):
    for n_ in (3, 2):
        p_ = ALIAS_PLACE.get(h[:n_], h[:n_])
        if len(p_) == n_ and (p_ + '|' + p_) in GEO and GEO[p_ + '|' + p_].get('lat'): return GEO[p_ + '|' + p_]
    return None
def _far_dish(c, base):
    h = c.split('、')[0].strip()
    if base and h not in _DISH_PLACE:      # 菜名以地名开头（大连炸海蛎、巴陵全鱼、兰州拉面）：那个地方离今天的城市远，就是外地菜
        g0 = _prefix_place(h)
        if g0 and km(base, (g0['lat'], g0['lng'])) > 90: return True
    pls = _DISH_PLACE.get(h)
    if not pls or not base: return False
    ds = []
    for pl in pls:
        g_ = None
        for k_, v_ in GEO.items():
            if k_.endswith('|' + pl) and k_.split('|')[0] == pl: g_ = v_; break
        if g_: ds.append(km(base, (g_['lat'], g_['lng'])))
    if ds: return min(ds) > 90
    parts = [x for x in (CUR_CITY[0] or '').split('|') if x]
    return not any(pl in x or x in pl for pl in pls for x in parts)      # 查不到出处的坐标：出处地名不在今天的城市里，就当是外地菜
GENERIC_MEAL = ['当地家常菜', '时令蔬菜小炒', '街边小吃', '本地汤面', '炒一桌家常', '小火锅', '烧烤', '饺子或面片', '粥配小菜', '砂锅煲', '烩菜', '炖菜', '家常小炒', '卤味拼盘', '米饭套餐', '包子配豆浆', '凉菜加热菜', '烙饼卷菜']
# ——— 2026-10-20 餐食按所在省过滤 ———
# 大省 / 跨省长线的“菜池”是目的地级的（dbdh24 的目的地是北京：曲阜晚饭涮羊肉、武夷山晚饭卤煮火烧、土楼晚饭豆汁、阳朔晚饭焦圈；hxz1 在库车吃乾州锅盔、hcz1 在广西吃泰和乌鲁鸡汤），
# _far_dish 只认“菜→出处地点”有坐标的那一小部分。这里补一把省级的尺子：菜在 PROV_FOOD / REGION_FOOD / 目的地 eat 里只属于别的省，而今天所在城市的省已知，就不推荐。
import sys as _sys; _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo_prov as _gp
_DM = {x['id']: x['name'] for x in json.load(open('data/destinations.json', encoding='utf-8'))['domestic']}
def _dn(c): return re.sub(r'[（(].*$', '', c.split('、')[0]).strip()
DISH_PROV = {}
for _pv, _ds in PROV_FOOD.items():
    for _d in _ds: DISH_PROV.setdefault(_dn(_d), set()).add(_pv)
for _pv, _l in REGION_FOOD.items():
    for _f, _pl in _l: DISH_PROV.setdefault(_dn(_f), set()).add(_pv)
for _x in CAT.values():
    if _x['id'] in _DM and _x['id'] not in ('hongkong', 'macau', 'taiwan'):
        for _d in _x.get('eat') or []: DISH_PROV.setdefault(_dn(_d), set()).add(_DM[_x['id']])
PROV_NOW = [None]
# 日本只在某几处才有的菜（河豚在下关 / 福冈 / 大阪，鳗鱼饭在浜松 / 名古屋 / 柳川…）：不在这些城市附近就不推荐（青森晚饭河豚料理、道东宇登吕午饭鳗鱼饭）
JP_ONLY = {'河豚': ('下关', '山口', '福冈', '大阪', '东京', '京都', '博多'), '鳗鱼': ('浜松', '名古屋', '柳川', '东京', '大阪', '福冈', '京都', '静冈', '成田', '博多')}
JP_NOW = ['']
def _wrong_prov(c):
    """这道菜只出自别的省（今天所在的省已知，且这道菜的出处省都不是它）"""
    pv = PROV_NOW[0]; s_ = DISH_PROV.get(_dn(c))
    if _dn(c) in _gp.NATIONWIDE: return False
    if pv == '日本':
        h_ = _dn(c)
        for k_, cs_ in JP_ONLY.items():
            if k_ in h_ and not any(x_ in JP_NOW[0] for x_ in cs_): return True
    return bool(pv and s_ and pv not in s_)
# 每天所在城市的月均气温（ERA5，tools/fix_climate.py 生成 data/climate_era5.json）；没有的城市用目的地级的表（日本全国用东京、挪威用奥斯陆，北方线偏暖 10℃ 以上）
_ERA = json.load(open('data/climate_era5.json', encoding='utf-8')) if os.path.exists('data/climate_era5.json') else {'cells': {}, 'cities': {}}
ERA_TAB = {c_: _ERA['cells'][k_] for c_, k_ in _ERA['cities'].items() if k_ in _ERA['cells']}
for rid, it in IT.items():
    dest = CAT[it['dest']]; city = it['city']; CUR_CC[0] = CC.get(it['dest'], 'cn'); SELF[0] = bool(it.get('drive')); SELFV[0] = SELF[0] or any((st_.get('via') or '').startswith('自驾') for d_ in it['days'] for st_ in d_['stops'])
    base = (dest['base']['lat'], dest['base']['lng'])
    MEAL0 = meal0_of(it['dest']); DEP_T = MEAL0 - 20 if MEAL0 > 18 * 60 else 18 * 60 + 10; AT_EVE = MEAL0 + 60 if MEAL0 > 18 * 60 else 18 * 60; ABROAD = it['dest'] in ASIA_CC; ALP = it['dest'] in ALPINE
    cg = geocode(city, city, None)                      # 以行程所在城市为中心，不用省会
    if cg and km(base, (cg['lat'], cg['lng'])) < 2500: base = (cg['lat'], cg['lng'])   # 离省会远的城市（喀什、札幌、天水）也认
    eat_pool = list(dest['eat']); days = []; n = len(it['days']); drive_tot = 0; longest = 0; carry = None
    served = set()
    used_dish = set()      # 同一条行程里每顿饭的菜不重复：先收集手写的，没写的从城市招牌菜、省里的招牌菜里挨个挑还没吃过的
    for _d in it['days']:
        for _k in ('lunch', 'dinner'):
            for _x in ((_d.get(_k) or {}).get('dish') or '').split('、'):
                if _x.strip(): used_dish.add(_x.strip())
    for di, d in enumerate(it['days']):
        last = di == n - 1
        dcity = d.get('city', city); dbase = base
        PROV_NOW[0] = _gp.prov_of(dcity) if it['dest'] in _DM and it['dest'] not in ('hongkong', 'macau', 'taiwan') else (dest['name'] if (it['dest'] in ASIA_CC and dest['name'] in PROV_FOOD) else None)      # 国内按省过滤；国外按国家（中国菜不出现在日本线上）
        JP_NOW[0] = dcity + '|' + city + '|' + (d.get('stay') or '')
        stay_pt = None
        if dcity != city:
            cg2 = geocode(dcity, dcity, None)
            if cg2: dbase = (cg2['lat'], cg2['lng'])
        sc = (GEO.get(dcity + '|' + d['stay']) or GEO.get(city + '|' + d['stay'])) if d.get('stay') else None   # 住处有人工核对过的坐标就用（原来调用了一个不存在的函数，住处坐标从来没用上）
        stay_ok = bool(sc and km(dbase, (sc['lat'], sc['lng'])) < 60)
        stay_pt = (sc['lat'], sc['lng']) if stay_ok else dbase
        far = lambda p: p and km(p, dbase) > 60   # 当天已经到了另一座城：回住处就留在当地
        RURAL[0] = it['dest'] not in ASIA_CC and dcity not in BIG_CITIES
        t = mm(d.get('start', '09:00')); prev = carry or dbase; rows = []; lunched = t >= 13 * 60; dined = False; drive = 0
        if di == 0 and ABROAD:      # 到达日：第一行写“抵达 + 机场到住处”，之后的行整体顺延这段路（作者写的 start 当作落地的钟点）
            _am = d.get('air_min') or air_min(dcity); rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': f'抵达后从机场到住处约 {_am} 分钟', 'arr': 1}); t += _am
        legmax = 0; legmax_how = ''
        mv = [False]; mvt = ['']; prev_ok = True; lastp = None      # prev_ok：prev 是不是真在“最后一站”（站点没有坐标时 prev 停在更早的点或城市中心，从那里算“到住处”会差几百公里：xl8a 第 2 天旅顺 → 营口 256 公里）

        def _mv():      # 搬家日最后一站 → 当晚住处的车程，一天只算一次（中途先“回住处”歇脚、晚饭后又“回住处”，两处都调用）
            if mv[0] or not prev_ok or not lastp: return None      # 起点只认“最后一个有坐标的站”（lastp）：prev 在中途回住处歇脚、晚饭后会被改成住处 / 城市中心，晚饭后再调用就从城市中心算了（dbdh24 第 23 天五台山 1 公里 → “34 公里”）
            r_ = move_leg(lastp, d, last, rt_, sc, dbase)
            if r_: mv[0] = True; mvt[0] = r_[0]
            return r_
        rt_ = (not last) and (it['days'][di + 1].get('city', city) == dcity) and (not d.get('stay') or stay_ok or (sc is None and dcity in d['stay'])) and (not prev or km(prev, stay_pt) < 60)     # 今天出发时就在今晚住处附近（前一晚住在别处的搬家日不算）；第二天还以同一座城为基点、而且今晚住的就是这座城（或没写住处）：今天是当天来回；写明住在远处的是搬家日
        meal_i = di

        def meal(slot, spec, at):
            global meal_i
            CUR_CITY[0] = dcity + '|' + city
            pool = CITY_FOOD.get(dcity) or CITY_FOOD.get(city) or eat_pool   # 先用当天城市的招牌菜
            dish = (spec or {}).get('dish')
            if dish and dish not in GENERIC_OK and (_notmeal(dish) or _far_dish(dish, dbase) or _offseason(dish, (it.get('start') or [0, 0])[1] + 1) or _wrong_prov(dish)):      # 手写的菜是点心/酒，或出处在远处（锦屏的晚饭写成遵义鸡蛋糕）：换成本地的
                dish = None; spec = {}
            if dish and _dup(dish.split('、')[0].strip(), served) and dish not in GENERIC_OK:      # 手写的菜在同一条行程里已经吃过：换一道，地点也不沿用
                dish = None; spec = {}
            if not dish:
                _rf = REGION_FOOD.get(dest.get('name'), [])
                _here = [f_ for l_ in REGION_FOOD.values() for f_, p_ in l_ if p_ and (p_ in dcity or dcity in p_) and not _wrong_prov(f_)]      # 不管哪个省，只要“拍过”的地点就是今天住的城市
                near = list(dict.fromkeys((CITY_FOOD.get(dcity) or []) + [c_ for c_ in (CITY_FOOD.get(city) or []) if dcity == city or not (_wrong_prov(c_) or _far_dish(c_, dbase))] + _here))      # 路线出发城市的招牌菜只在今天还在那一带时才用（dbdh24 第 3 天在曲阜，吃的是北京的涮羊肉）
                fresh_near = [c_ for c_ in near if not _dup(c_.split('、')[0].strip(), used_dish)]
                big = list(dict.fromkeys(eat_pool + [f_ for f_, p_ in _rf] + list(PROV_FOOD.get(dest.get('name'), []))))
                big = [c_ for c_ in big if not any(t_ in c_ and t_ not in (dcity + city + (it.get('label') or '')) for t_ in CITY_TAGS)]     # 大国的菜名里带着别的城市（“芝加哥深盘披萨”）时，不推荐给不在那座城的行程
                big = [c_ for c_ in big if not _notmeal(c_) and not _far_dish(c_, dbase) and not _offseason(c_, (it.get('start') or [0, 0])[1] + 1) and not _wrong_prov(c_)]      # 点心/酒/调料不当正餐；已知出处在远处的菜（烟台的海肠捞饭排进临沂）不推荐
                near = [c_ for c_ in near if not _notmeal(c_) and not _offseason(c_, (it.get('start') or [0, 0])[1] + 1)]
                fresh_big = [c_ for c_ in big if not _dup(c_.split('、')[0].strip(), used_dish)]
                if not fresh_near and fresh_big:           # 本城的招牌菜吃完了：从本省（本国）的特色菜里按路线编号错开着挑，别每条线都从同一道开始
                    cands = [fresh_big[zlib.crc32((rid + str(meal_i)).encode()) % len(fresh_big)]]
                else:
                    cands = near + big + GENERIC_MEAL
                fresh = [c_ for c_ in cands if not _dup(c_.split('、')[0].strip(), used_dish)]
                dish = fresh[0] if fresh else GENERIC_MEAL[meal_i % len(GENERIC_MEAL)]
            used_dish.update(x_.strip() for x_ in dish.split('、') if x_.strip())
            served.update(x_.strip() for x_ in dish.split('、') if x_.strip())
            meal_i += 1
            place = (spec or {}).get('place') or '附近'
            return {'t': hm(at), 'type': 'eat', 'slot': slot, 'dish': DISH_NOTE.get(dish, dish), 'place': place, 'd': '', 'poi': '', 'dp': dp(city, dish.split('、')[0])}

        for si, st in enumerate(d['stops']):
            g = geocode(st.get('q') or st['name'], dcity, dbase, short(st['name'])); pt = (g['lat'], g['lng']) if g else None
            # 晚上的点：先吃晚饭
            dine_there = bool(st.get('at') and mm(st['at']) >= AT_EVE and (d.get('dinner') or {}).get('place') and (d['dinner']['place'] in st['name'] or d['dinner']['place'] in (st.get('q') or '')))
            if st.get('at') and mm(st['at']) >= AT_EVE and not dined and not last and not dine_there:
                if t < DEP_T - 40:
                    _bl = back_leg(prev, stay_pt, far, rt_, 0 if di == 0 else legmax, '' if di == 0 else legmax_how) or _mv(); rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': _bl[0] if _bl else '回去歇一下'}); drive += (_bl[1] if _bl and _bl[2] else 0); t = max(DEP_T, t + (_bl[1] if _bl else 0)); prev = stay_pt if (stay_ok or _bl) else (prev if far(prev) else stay_pt)
                rows.append(meal('晚饭', d.get('dinner'), max(t, MEAL0))); t = max(t, MEAL0) + 75; dined = True
            # 到了饭点先吃午饭
            if not lunched and t >= 11 * 60 + 40 and st['type'] != 'food':
                if t <= 14 * 60 + 30: rows.append(meal('午饭', d.get('lunch'), t)); t += 60
                lunched = True                                           # 过了两点半就不排“午饭”了，晚上再吃
            how, mins, dist = leg(prev, pt, st.get('via'))
            if ALP and not st.get('via') and how.startswith(('打车', '包车')) and MOUNT_RE.search(st['name']): how, dist = '火车或缆车', None      # 山里：缆车、齿轨火车上去，不打车
            elif ALP and not st.get('via') and how.startswith(('打车', '包车')) and TRAIL_RE.search(st['name']): how, dist = '步行或公交', None
            if dine_there and not dined:
                at0 = max(t + mins, MEAL0)
                if at0 - mins - t >= 60:
                    if not lunched and 11 * 60 <= t <= 14 * 60:          # 先吃午饭再回去歇
                        rows.append(meal('午饭', d.get('lunch'), max(t, 11 * 60 + 30))); t = max(t, 11 * 60 + 30) + 60; lunched = True
                    _bl = back_leg(prev, stay_pt, far, rt_, 0 if di == 0 else legmax, '' if di == 0 else legmax_how) or _mv(); rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': _bl[0] if _bl else '回去歇一下'}); drive += (_bl[1] if _bl and _bl[2] else 0); t += (_bl[1] if _bl else 0); prev = stay_pt if (stay_ok or _bl) else (prev if far(prev) else stay_pt)
                    how, mins, dist = leg(prev, pt, st.get('via'))     # 歇完从住处出发，路程按住处算
                    at0 = max(t + mins, MEAL0)
                t = at0 - mins
            elif st.get('at'):
                gap = mm(st['at']) - mins - t
                if gap >= 60 and rows: rows.append({'t': hm(t), 'type': 'see', 'name': '沿途慢慢走', 'd': dur_txt(gap), 'poi': '', 'dp': ''})   # (d) 等夕照、等开船的空当
                t = max(t, mm(st['at']) - mins)
            if st.get('via') and mins >= legmax and mins >= 60: legmax = mins; legmax_how = how     # 当天最长的一段已写明的去程（时间、方式）
            if how.startswith(('包车', '自驾', '开车')): drive += mins
            rows.append({'t': hm(t), 'type': 'dep', 'to': short(st['name']), 'how': f'{how} {dur_txt(mins)}' + (f' · {dist} 公里' if dist and dist >= 5 else '')})
            if not lunched and t < 12 * 60 and t + mins > 13 * 60:   # 车开过中午：路上吃
                spec = d.get('lunch') or {}
                rows.append({'t': hm(12 * 60 + 30), 'type': 'eat', 'slot': '午饭', 'dish': spec.get('dish') or '路上吃', 'place': spec.get('place') or '沿途', 'd': '', 'poi': '', 'dp': ''}); lunched = True
            t += mins; du = st.get('dur') or DUR[st['type']]
            if dine_there and not dined:
                rows.append(meal('晚饭', d.get('dinner'), t)); t += 75; dined = True
            # (c) 路上过了饭点：到了先吃午饭
            if not lunched and t >= 11 * 60 + 40 and st['type'] != 'food':
                if t <= 14 * 60 + 30: rows.append(meal('午饭', d.get('lunch'), t)); t += 60
                lunched = True
            if st['type'] == 'food':
                slot = '早饭' if t < 10 * 60 else ('午饭' if t < 16 * 60 else '晚饭')
                rows.append({'t': hm(t), 'type': 'eat', 'slot': slot, 'dish': st.get('dish', '小吃'), 'place': short(st['name']), 'd': '', 'poi': st.get('q') or st['name'], 'dp': dp(dcity, short(st['name']))})
                if slot == '午饭': lunched = True
                if slot == '晚饭': dined = True
            else:
                rows.append({'t': hm(t), 'type': 'fun' if st['type'] == 'fun' else 'see', 'name': st['name'], 'd': dur_txt(du), 'poi': st.get('q') or st['name'], 'dp': dp(dcity, short(st['name'])), **({'at': st['at']} if st.get('at') else {})})
                if not lunched and t < 12 * 60 and t + du > 13 * 60:   # 逛得久、跨过中午：在里面简单吃
                    rows.append({'t': hm(max(t + 60, 12 * 60 + 15)), 'type': 'eat', 'slot': '午饭', 'dish': '简单吃一点', 'place': short(st['name']) + '里面', 'd': '', 'poi': '', 'dp': ''}); lunched = True
            t += du; prev = pt or prev; prev_ok = bool(pt)
            if pt: lastp = pt
        if not lunched and 12 * 60 <= t <= 14 * 60 + 30:
            rows.append(meal('午饭', d.get('lunch'), t)); t += 60; lunched = True
        if last and d.get('home_via'):      # 自驾线最后一天开车回出发地（作者写明）：算进当天路上（xl7a 景德镇 → 上海 600 公里、xb96a 郴州 → 深圳）
            _v, _m, _x = leg(None, None, d['home_via']); rows.append({'t': hm(t + 10), 'type': 'dep', 'to': '回程', 'how': f'{_v} {dur_txt(_m)} 回家'}); drive += _m
        elif last:
            rows.append({'t': hm(t + 10), 'type': 'dep', 'to': '回程', 'how': (f'前往机场约 {d.get('air_min') or air_min(dcity)} 分钟，提前 3 小时到' if ABROAD else ('开车回城' if (SELF[0] and it.get('loop')) else '去车站或机场：高铁提前 40 分钟到，飞机提前 2 小时到'))})      # 国内自驾环线：最后一天是开车回出发的城市，不是去车站机场（2026-10-19）
        else:
            if not dined:
                if t < DEP_T - 40:
                    _bl = back_leg(prev, stay_pt, far, rt_, 0 if di == 0 else legmax, '' if di == 0 else legmax_how) or _mv(); rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': _bl[0] if _bl else '回去歇一下'}); drive += (_bl[1] if _bl and _bl[2] else 0); t = max(DEP_T, t + (_bl[1] if _bl else 0)); prev = stay_pt if (stay_ok or _bl) else (prev if far(prev) else stay_pt)
                rows.append({'t': hm(max(t, DEP_T)), 'type': 'dep', 'to': '吃晚饭', 'how': '开车或步行' if SELF[0] else '打车或步行'})
                rows.append(meal('晚饭', d.get('dinner'), max(t, DEP_T) + 20)); t = max(t, DEP_T) + 95
            _bl = back_leg(prev, stay_pt, far, rt_, 0 if di == 0 else legmax, '' if di == 0 else legmax_how) or _mv(); rows.append({'t': hm(t), 'type': 'dep', 'to': '住处', 'how': _bl[0] if _bl else ('开车或步行' if SELF[0] else '打车或步行')}); drive += (_bl[1] if _bl and _bl[2] else 0)
        if mv[0]:      # 这一行是 move_leg 补的（不是“当天往返的回程”）：标 mv，data_checks 第 8 项的去回比 / 2.5 小时判据不管它
            for w_ in rows:
                if w_.get('how') == mvt[0]: w_['mv'] = 1
        # 时间必须单调递增
        ts = [mm(w['t']) for w in rows]
        if ts != sorted(ts): report.append(f'{rid} D{di + 1} 时间倒序')
        first = next((GEO.get(dcity + '|' + (x.get('q') or x['name'])) for x in d['stops'] if GEO.get(dcity + '|' + (x.get('q') or x['name']))), None)
        lat, lng = (first['lat'], first['lng']) if first else base
        drive_tot += drive; longest = max(longest, drive)
        lastg = next((GEO.get(dcity + '|' + (x.get('q') or x['name'])) for x in reversed(d['stops']) if GEO.get(dcity + '|' + (x.get('q') or x['name']))), None)
        carry = (lastg['lat'], lastg['lng']) if lastg else carry
        if d.get('stay'):   # 第二天从住的地方出发：住处查得到就用住处
            sg = (GEO.get(d['stay'] + '|' + d['stay']) or GEO.get(dcity + '|' + d['stay'])) if 'GEO' in globals() else None   # “城市|住处”也认（北京西城、凤凰古城这类）
            # 住处坐标要在“今天的城、明天的城、今天最后一站”任何一处 100 公里内才收（真搬家：当晚住斋浦尔、明天就是斋浦尔；住隔壁镇、丽江古城这类也是真的远）。
            # 在线查询会把“新街口附近”“上野附近”“古城”这类泛称解析到合肥(153 公里)、岐阜(206)、清盛(201)，原来只要离上一站 ≤400 公里就收，
            # 第二天“出发 → 中山陵”就成了 200 公里包车（check_fake_legs.py 守着）。
            _nc = None
            if di + 1 < n:
                _ng = GEO.get(it['days'][di + 1].get('city', city) + '|' + it['days'][di + 1].get('city', city))
                _nc = (_ng['lat'], _ng['lng']) if _ng and _ng.get('lat') is not None else None
            if sg and carry and min(km((sg['lat'], sg['lng']), x_) for x_ in (dbase, carry) + ((_nc,) if _nc else ())) < 100: carry = (sg['lat'], sg['lng'])
            elif carry and dcity in d['stay'] and not last and (GEO.get(dcity + '|' + dcity) or {}).get('lat') is not None and km(carry, (GEO[dcity + '|' + dcity]['lat'], GEO[dcity + '|' + dcity]['lng'])) >= 55:
                # 住处没有可用坐标，但名字里就带着今天的城市（“拉萨老城区”“九寨沟口”）：人睡在城里，明天从城中心出发，不从今天最后一站出发
                # （原来取最后一站：羊八井出发去布达拉宫成了 150 公里自驾）。只在住处坐标缺失或被上面那把尺拒绝、而且最后一站离城中心 ≥55 公里（去了远处的景点）时用；
                # 最后一站就在城里时不动它——有的线“当天城市”只是个枢纽名，人其实在隔壁城（nx3 中卫线住进银川），拉回枢纽中心会凭空多出两百公里。
                _c0 = GEO[dcity + '|' + dcity]; carry = (_c0['lat'], _c0['lng'])
        days.append({'title': d['title'], 'text': d['text'], 'lat': round(lat, 2), 'lng': round(lng, 2), 'elev': d['elev'] if 'elev' in d else (dest['base']['elev'] if km(dbase, (dest['base']['lat'], dest['base']['lng'])) <= 80 else 0),   # 没写海拔：只有当天待的城市就是目的地基准点（拉萨、库斯科、墨西哥城）才用基准海拔；川藏线第 1 天成都 → 雅安不再继承拉萨的 3,649 米（2026-10-19）
                     
                     'clim': ({m: ERA_TAB[dcity][str(m)] for m in range(1, 13) if str(m) in ERA_TAB[dcity]} if dcity in ERA_TAB else {m: dest['climate'][str(m)] for m in (9, 10, 11)}), 'city': dcity, 'navCity': dcity, 'rows': rows, 'stay': [],
                     'driveMin': drive, 'stayName': '' if last else d.get('stay', dcity), 'stayNote': '', 'story': d.get('story'), 'manners': [], 'notes': []})
    tr = TRIPS.get(rid, {}); p = tr.get('price') or {}
    meta = {'id': rid, 'origin': it['city'], 'label': it['label'], 'title': it['title'], 'kicker': it['kicker'], 'alt': it['title'], 'start': it['start'], 'prep': it['prep'],
            'price': (('约 ' if str(p.get('basis', '')).startswith('参考价') else '') + '¥{:,}–{:,}'.format(p['lo'], p['hi'])) if p.get('lo') else '人均另算',
            'img': ('/_blob/' + tr['poster']) if tr.get('poster') else '', 'driveTop': ('自驾' if SELF[0] else '包车') if drive_tot else '不开车', 'drive': SELF[0], 'loop': bool(it.get('loop')),
            'driveSub': (f'最长一天 {longest / 60:.1f} 小时' if drive_tot else '地铁、打车加步行'), 'navApp': 'google' if it['dest'] in ASIA_CC else 'amap', 'cost': None,
            'fit': ((['高海拔，行程最高到 {:,} 米：7 岁以下的孩子、心肺不好的老人慎重'.format(max(x.get('elev') or 0 for x in it['days']))] if max(x.get('elev') or 0 for x in it['days']) >= 3000 else []) + (['有一天要坐 %d 小时以上的车：带孩子要多停几次' % (longest // 60)] if longest >= 180 else [])), 'days': days, 'compiled': True}
    ROUTES[rid] = meta
    if rid not in ORDER: ORDER.append(rid)
hits = sum(1 for k, v in GEO.items() if v and not k.endswith('#tried')); miss = [k for k, v in GEO.items() if not v and not k.endswith('#tried')]
s = re.sub(r'window.ZOUNI_ORDER=\[.*?\];', 'window.ZOUNI_ORDER=' + json.dumps(ORDER) + ';', s, count=1)
s = re.sub(r'window.ZOUNI_ROUTES=.*;\n', lambda m: 'window.ZOUNI_ROUTES=' + json.dumps(ROUTES, ensure_ascii=False, separators=(',', ':')) + ';\n', s, count=1)
open(OUT, 'w', encoding='utf-8').write(s)
print('编译', len(IT), '条；站点坐标', hits, '个，没查到', len(miss), miss[:6], '；问题', report or '无')
