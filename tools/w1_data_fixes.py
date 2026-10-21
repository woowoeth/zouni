#!/usr/bin/env python3
"""2026-10-20 第 1 波数据与逻辑真实性：driver/follow/abroad/family 用户测试报告里逐条查实的数据修正（幂等，可重跑）。
每一条都写了证据来源（Nominatim = openstreetmap 地名检索，2026-10-20 用 curl 查；OSRM = router.project-osrm.org；报告 = usability2/*.md）。
改的是 data/geo/pois.json 和 data/itineraries.json；先备份在 build/bak_w1/data/。"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
GP = 'data/geo/pois.json'; IP = 'data/itineraries.json'
G = json.load(open(GP, encoding='utf-8')); IJ = json.load(open(IP, encoding='utf-8')); IT = IJ['itineraries']
log = []


def setp(key, lat, lng, hit, q=None):
    old = G.get(key)
    if old and abs(old['lat'] - lat) < 1e-4 and abs(old['lng'] - lng) < 1e-4:
        if old.get('src') == 'w1': old['src'] = 'curated'; log.append(f'坐标 {key}: src w1 → curated')
        return
    G[key] = {'lat': lat, 'lng': lng, 'hit': hit, 'q': q or key.split('|', 1)[1], 'src': 'curated'}      # 人工核对过（Nominatim / 报告 + 查证），data_checks 第 3 项的“离城市中心 400 公里”不算它（和 茶卡、唐古拉山口 同一类）
    log.append(f'坐标 {key}: {old and (round(old["lat"], 3), round(old["lng"], 3))} → ({lat}, {lng})')


# —— 坐标（Nominatim 核对）
setp('深圳|湖光岩风景名胜区', 21.1463, 110.28029, 'Nominatim 湖光岩, 湖光镇, 麻章区, 湛江市（原坐标在深圳大鹏，差约 400 公里；driver D1）')
setp('北京|北京钟鼓楼', 39.93931, 116.38974, 'Nominatim 鼓楼, 东城区（原坐标是怀柔区同名点，离市区 52 公里；driver D2）')
setp('广元|春熙路', 30.65918, 104.07529, 'Nominatim 春熙路, 锦江区, 成都市（原坐标在广元昭化；driver D3）')
setp('会理|会理红军长征纪念馆', 26.667, 102.262, '近似：同会理会议纪念地（data 里 攀枝花|会理会议纪念地 的人工核对点，会理古城内）；原坐标是禄劝皎平渡渡江纪念馆，离古城 45 公里（follow #2）。待真人核对馆址')
setp('儋州|儋州东坡书院', 19.74231, 109.35364, 'Nominatim 东坡书院, 中和镇, 儋州市（原近似坐标偏南约 6 公里；follow）')
for k in ('三十里营房|康西瓦烈士陵园', '叶城|康西瓦烈士陵园', '大红柳滩|康西瓦烈士陵园'):
    setp(k, 36.21744, 78.75615, 'Nominatim 康西瓦烈士陵园, 昆岭镇, 和康县（原坐标偏西南约 80 公里；driver D7）')
setp('三十里营房|三十里营房', 36.34987, 78.03291, 'Nominatim 三十里营房, 昆岭镇, 和康县（原 35.9,78.35 偏南 50 公里）')
# 新藏线上的 xb96a 第 43 天：红柳滩出发先过康西瓦（78.76°E），再到三十里营房（78.03°E）；原来第 44 天又回头去康西瓦（多开约 65 公里折返）
d43 = IT['xb96a']['days'][42]; d44 = IT['xb96a']['days'][43]
if [s['name'] for s in d43['stops']] == ['三十里营房']:
    d43['stops'] = [{'name': '康西瓦烈士陵园', 'q': '康西瓦烈士陵园', 'type': 'sight', 'dur': 30, 'via': '自驾约 3 小时 30 分钟'},
                    dict(d43['stops'][0], via='自驾约 1 小时 30 分钟')]       # 合计仍是作者原来的 5 小时（OSRM 在新藏线不准：红柳滩到营房只给 88 分钟，高海拔山路作者按 5 小时）
    d43['title'] = '康西瓦烈士陵园 · 三十里营房'
    log.append('xb96a 第 43 天：康西瓦并入，顺序 红柳滩 → 康西瓦 → 三十里营房')
if d44['stops'][0]['name'] == '康西瓦烈士陵园':
    d44['stops'] = d44['stops'][1:]
    d44['stops'][0] = dict(d44['stops'][0], via='自驾约 2 小时 30 分钟')
    d44['title'] = '麻扎 · 库地达坂'
    log.append('xb96a 第 44 天：去掉回头的康西瓦')
# 红海滩到兴城：OSRM 178 公里 / 2 小时 30 分，作者写 1 小时 35 分（driver D12 补充）
for s in IT['xl8a']['days'][2]['stops']:
    if s['name'] == '兴城古城' and s.get('via') != '自驾约 2 小时 30 分钟': s['via'] = '自驾约 2 小时 30 分钟'; log.append('xl8a 第 3 天 兴城古城 via → 2 小时 30 分钟（OSRM 2h30）')
# 龙门石窟：15:00 到、停 3 小时、日落 17:27，傍晚停止入场（driver D11）
for s in IT['dbdh24']['days'][20]['stops']:
    if s['name'] == '龙门石窟' and s.get('dur') != 120: s['dur'] = 120; log.append('dbdh24 第 21 天 龙门石窟 停留 3 小时 → 2 小时')
# xbdh30 第 17、18 天：每天 city 是前一晚住处（第 16 天住那曲、第 17 天住沱沱河），原来写成格尔木；住宿城市因此成了格尔木（driver D4）
x = IT['xbdh30']['days']
if x[16].get('city') == '格尔木': x[16]['city'] = '那曲'; log.append('xbdh30 第 17 天 city 格尔木 → 那曲')
if x[17].get('city') == '格尔木': x[17]['city'] = '沱沱河'; log.append('xbdh30 第 18 天 city 格尔木 → 沱沱河')
for s in x[17]['stops']:
    k0 = '格尔木|' + (s.get('q') or s['name']); k1 = '沱沱河|' + (s.get('q') or s['name'])
    if k1 not in G and G.get(k0): G[k1] = dict(G[k0]); log.append(f'坐标键复制 {k0} → {k1}')
for s in x[16]['stops']:
    k0 = '格尔木|' + (s.get('q') or s['name']); k1 = '那曲|' + (s.get('q') or s['name'])
    if k1 not in G and G.get(k0): G[k1] = dict(G[k0]); log.append(f'坐标键复制 {k0} → {k1}')


def setd(rid, di, **kw):
    d = IT[rid]['days'][di - 1]
    for k, v in kw.items():
        if d.get(k) != v: d[k] = v; log.append(f'{rid} 第 {di} 天 {k} → {v if len(str(v)) < 40 else str(v)[:38] + "…"}')


def setstop(rid, di, name, **kw):
    for s_ in IT[rid]['days'][di - 1]['stops']:
        if s_['name'] == name:
            for k, v in kw.items():
                if s_.get(k) != v: s_[k] = v; log.append(f'{rid} 第 {di} 天 {name} {k} → {v}')


def addprep(rid, txt, front=False):
    pr = IT[rid]['prep']
    if txt not in pr: (pr.insert(0, txt) if front else pr.append(txt)); log.append(f'{rid} prep + {txt[:24]}…')


# —— 机场 / 车站到住处的分钟数：原来是按城市类型套的模板（45/60/75），不是这条线的实际路程。
# OSRM 驾车分钟（2026-10-20，router.project-osrm.org；机场坐标取公开资料），公共交通在驾车分钟上加缓冲：
#   特罗姆瑟机场→市区 6 公里 10 分；青森机场→青森站 14 公里 18 分；花卷机场→盛冈 36 公里 28 分；驫木→青森机场 83 公里 75 分；
#   熊本机场→熊本站 20 公里 21 分；开闻岳→鹿儿岛机场 95 公里 128 分；高松机场→高松站 19 公里 35 分；尾道→广岛机场 39 公里 43 分（冈山机场 86 分）；女满别机场→网走 22 公里 21 分
for rid, a, b in (('xv612a', 20, 20), ('xv611a', 35, 35), ('xv611b', 45, 100), ('xv613a', 45, 140), ('xv614a', 40, 60), ('xv610a', 30, 30)):
    setd(rid, 1, air_min=a); setd(rid, len(IT[rid]['days']), air_min=b)

# —— xv612a 特罗姆瑟（abroad.md #2）：极夜期天光只有中午前后 2–3 小时，原来第 2、3 天各排 5 小时夜间冰路自驾，而且特罗姆瑟 → 森雅岛 OSRM 只要 3 小时 46 分
# 重排：第 2 天 09:30 出发（约 4 小时，前半程在蓝调天光里），第 3 天 09:30 起、10:10 就出发，下午两点出头到；写明“第一次在北欧冬天开车的人不要自驾”
setd('xv612a', 2, start='09:30', text='早上九点半出发，开车往南到森雅岛，约 4 小时：前半程在蓝调天光里，后半程天色渐暗，开慢点，遇到驯鹿让它们先过。下午到岛上的住处，晚饭自己做，窗外就是峡湾，生起壁炉看火光，夜里关了灯看看有没有极光，没有也别勉强。')
setstop('xv612a', 2, '森雅岛峡湾海岸', via='自驾约 4 小时', dur=90)
setd('xv612a', 3, start='09:30', text='早上天亮后在住处周围的峡湾边走半小时，看海、雪山和结了冰的瀑布，十点出头出发，沿原路开回特罗姆瑟，约 4 小时，下午两点出头到，最后一段天色已经暗下来，不要拖到更晚。到市区还车或入住，晚上在餐馆吃一顿热饭。')
setstop('xv612a', 3, '森雅岛峡湾边', dur=30)
setstop('xv612a', 3, '特罗姆瑟市中心', via='自驾约 4 小时')
pr = IT['xv612a']['prep']
for i_, t_ in enumerate(pr):
    if t_.startswith('森雅岛离特罗姆瑟路程长'):
        pr[i_] = '这条线有两段各约 4 小时的冬季冰路自驾，一天里只有中午前后三个小时左右有天光，其余时间路上是黑的：第一次在北欧冬天开车的人不要自驾，改成当地巴士加一日团（特罗姆瑟有去森雅岛的一日游），把第 2、3 天换成当天往返；自驾的话中午前后上路，到达后别再往更偏的地方开，住处选路边有人住的小屋或民宿。'; log.append('xv612a prep 森雅岛自驾那条改写')
# —— xv613a 九州慢车（abroad.md #4）：开口行程、末日赶机场、傍晚等日落
addprep('xv613a', '这是开口行程：熊本进、鹿儿岛出。订机票时进出是两个机场（熊本机场进，鹿儿岛机场出），第 3 天从开闻岳到鹿儿岛机场约 2 小时多，航班放在晚上。', front=True)
setstop('xv613a', 2, '西大山站', **{'at': '18:40', 'dur': 60})
setd('xv613a', 3, text='早上坐首班车到开闻站，从车站走到登山口开始爬开闻岳，海拔 924 米，山路上有火山地貌，一边是海，爬到山腰以后视野开阔，山顶常在云里看不见海，也不要硬撑。中午前下山，从开闻站坐车往鹿儿岛机场（约 2 小时多，先查好班次，不要赶最后一班）。夏季上午就热，登山要早。')
# —— tk4 东京（abroad.md #8）：标“地铁”却全是打车、住处写上野但酒店不在、标题写赶红叶但 10 月下旬没有红叶
for di, nm, via in ((1, '浅草寺', '地铁约 20 分钟'), (1, '东京晴空塔', '步行约 20 分钟'), (2, '明治神宫', '地铁约 30 分钟'), (2, '原宿竹下通', '步行约 10 分钟'), (2, '涩谷十字路口', '步行约 20 分钟'),
                    (3, '新宿御苑', '地铁约 30 分钟'), (3, '东京都厅展望台', '地铁约 15 分钟'), (4, '筑地场外市场', '地铁约 25 分钟')):
    setstop('tk4', di, nm, via=via)
for di in (1, 2, 3): setd('tk4', di, stay='东京')      # 推荐的三家酒店（东京湾洲际 / ONE@Tokyo / 羽田美居）都不在上野：不再写“上野附近”，没有按片区核对过的名字就不推荐具体酒店
IT['tk4']['title'] = '四天，东京走一遍'
setd('tk4', 3, text='上午在新宿御苑慢慢走（11 月下旬到 12 月初园里是红叶，别的季节看草坪和温室），傍晚上东京都厅展望台，免费看夜景。')
# —— bkk3 曼谷：周末市场落在周一；酒店不在湄南河边
setd('bkk3', 3, text='逛恰图恰市场（周六、周日才开，周五晚上只开一部分），下午去机场。')
IT['bkk3']['start'] = [2026, 10, 12]      # 11/12 周四：第 3 天正好是周六
addprep('bkk3', '恰图恰市场只在周末开：出发日选周四，第 3 天正好是周六。')
for di in (1, 2): setd('bkk3', di, stay='曼谷')
# —— 三十里营房 / 泰山：见后面的段落


# —— 泰山：“住·泰山顶”（family.md #4）。“泰安|泰山顶” 原坐标在玉皇顶以北 2.6 公里（山里没路），酒店卡片是山下泰安的三家。
setp('泰安|泰山顶', 36.25623, 117.10253, 'Nominatim 神憩宾馆, 天街, 泰前街道（山顶住宿集中在天街一带）')
HP = 'data/hotels/ctrip_hotels.json'; HJ = json.load(open(HP, encoding='utf-8'))
_gone = [k for k in HJ if re.search('山上|山顶|峰顶', k.split('|', 1)[1])]
for k in _gone: del HJ[k]
if _gone:
    json.dump(HJ, open(HP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    log.append('hotels：删 ' + '、'.join(_gone) + '（携程按“城市+关键词”搜出来的是山下 / 市区的酒店：泰山 → 泰安天外村、黄山 → 汤口南大门、三清山 → 上饶市区，和“住山上”矛盾；没有按片区核对过的名字就只给档位参考价）')
for rid in ('ts4', 'sdgt6'):
    addprep(rid, '山顶住宿只有天街一带的几家宾馆（如神憩宾馆），条件简单、旺季要提前订；订不到就住山下泰安，凌晨坐班车和索道上山看日出，日出前要早起。')


# —— 同一路段在不同线路里时间不一致（driver.md #7；tests/w1_checks.py 的 seg 闸）：取中位数统一
for rid, di in (('dxl10', 6), ('g214', 3), ('zl4d', 6), ('xl2a', 4), ('hcm1', 4)):
    setstop(rid, di, '独克宗古城', via='自驾约 2 小时 30 分钟')      # 丽江 → 独克宗：五条线写 2 / 2 / 2 小时 40 分 / 2 小时 30 分 / 3 小时，OSRM 115 分钟（165 公里，山路按 1.3 倍）


# —— 自驾线最后一天开车回家，原来只写在正文里、“路上”不算（compile 的 home_via）：正文里的小时数就是作者写的
setd('xl7a', 15, home_via='自驾约 7 小时')      # 景德镇 → 上海约 600 公里（正文：开车约 7 小时）
setd('xb96a', 105, home_via='自驾约 4 小时')     # 南华寺 → 深圳：正文全天 6 小时 30 分，郴州 → 南华寺已算 2 小时 30 分


# —— 香港的“九龙”和四川的九龙县同名：城市中心键“九龙|九龙”是四川九龙县（29.0,101.5），香港线的住处点（xw70a 第 3 天 ep）被拉到四川，隔 1468 公里。
# 香港线的 city 改叫“香港九龙”，坐标键复制一份，中心取九龙半岛中部（旺角一带，人工核对）
setp('香港九龙|香港九龙', 22.3193, 114.1694, '人工核对（九龙半岛中部，旺角一带）')
for rid_, it_ in IT.items():
    if it_['dest'] != 'hongkong': continue
    for d_ in it_['days']:
        if d_.get('city') == '九龙':
            d_['city'] = '香港九龙'; log.append(f'{rid_} city 九龙 → 香港九龙')
            for s_ in d_['stops']:
                k0 = '九龙|' + (s_.get('q') or s_['name']); k1 = '香港九龙|' + (s_.get('q') or s_['name'])
                if G.get(k0) and k1 not in G: G[k1] = dict(G[k0])


setd('xb96a', 23, stay_via='自驾约 7 小时')      # 察隅 → 然乌：正文写行车约 7 小时（约 300 公里山路），直线只有 110 公里，估算会写成 2 小时多：按作者的


# —— sdgt6 济南泰山曲阜青岛：第 2 天“爬泰山”按走路分钟口径不到 150（红门停留被当景点），但就是爬山：补“爬山”标签，带老人孩子就不推荐、也不会写“没有长爬坡和台阶”
_tp = 'data/catalog/trips.json'; _ts = open(_tp, encoding='utf-8').read(); _i = _ts.index('"id": "sdgt6"'); _j = _ts.index('"tags": [', _i); _k = _ts.index(']', _j)
if '爬山' not in _ts[_j:_k]:
    _ts = _ts[:_k].rstrip() + ',\n    "爬山"\n   ' + _ts[_k:]; open(_tp, 'w', encoding='utf-8').write(_ts); log.append('sdgt6 trips.tags + 爬山')


# —— 站点没有“城市|站名”坐标键（在线地名查询在本机证书失败、缓存成 None）：编译器拿不到最后一站在哪，“到住处”的车程没法算（第一版拿城市中心当起点，旅顺 → 营口写成 256 公里）。
# 页面上的图钉本来就用 build_site.coord() 的回退（只按站名查 places.resolved / 别的城市的同名键），这里把同一个回退结果写成“城市|站名”键（离当天出发城或当晚住的城 ≤200 公里才收），
# 编译器和页面用同一个点。只补缺的，不改已有的。
_PL = json.load(open('data/geo/places.resolved.json', encoding='utf-8'))
_byname = {}
for _k, _v in G.items():
    if _v and '|' in _k and '#' not in _k and isinstance(_v, dict) and _v.get('lat') is not None: _byname.setdefault(_k.split('|', 1)[1], _v)
import math
def _km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
for _k in [k_ for k_, v_ in G.items() if isinstance(v_, dict) and v_.get('src') == 'by_name_fallback']: del G[_k]      # 重算（幂等）：第一版 600 公里的半径收进了赛里木湖（离乌鲁木齐 518 公里）、敦煌沙洲夜市（挂在大柴旦名下 261 公里）
_filled = 0
for _rid, _it in IT.items():
    for _d in _it['days']:
        _c = _d.get('city', _it['city']); _cc = G.get(_c + '|' + _c)
        for _s in _d['stops']:
            _q = _s.get('q') or _s['name']; _key = _c + '|' + _q; _g = G.get(_key)
            if _g and isinstance(_g, dict) and _g.get('lat') is not None: continue
            _cand = _PL.get(_q) or _byname.get(_q)
            _sk = (_d.get('stay') or '').strip(); _sg = G.get(_sk + '|' + _sk) if _sk else None
            _near = _cand and _cc and (_km((_cand['lat'], _cand['lng']), (_cc['lat'], _cc['lng'])) <= 200 or (isinstance(_sg, dict) and _sg.get('lat') is not None and _km((_cand['lat'], _cand['lng']), (_sg['lat'], _sg['lng'])) <= 200))      # 离当天出发城或当晚住的城 ≤200 公里才收
            if _near:
                G[_key] = {'lat': _cand['lat'], 'lng': _cand['lng'], 'hit': '按站名回退：' + _q + '（和页面图钉同一个点；离出发城或住的城 ≤200 公里）', 'q': _q, 'src': 'by_name_fallback', 'curated': 1}; _filled += 1
if _filled: log.append(f'坐标键补 {_filled} 个（按站名回退，和页面图钉同一个点）')


# —— 住处没有“城市|城市”中心键：住处点（data-ep）退回当天所在城，而编译器按真实住处算了回程（S11：lzl5 第 4 天 / xo3d 第 3 天 / xw94a 第 6 天）。Nominatim 核对：
setp('工布江达|工布江达', 29.88839, 93.24481, 'Nominatim 工布江达镇, 工布江达县, 林芝市（县城）')
setp('安卡拉|安卡拉', 39.92077, 32.85405, 'Nominatim 安卡拉, Çankaya, 土耳其')
setp('死海|死海', 31.64063, 35.57468, 'Nominatim 死海（البحر الميت）, 马代巴省, 约旦（东岸酒店区）')

json.dump(G, open(GP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
json.dump(IJ, open(IP, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n'.join(log) or '无变化（已应用过）')
