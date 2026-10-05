# 优质景点库：5A（359）+ 世界遗产（60）→ data/catalog/cn_quality.json，并算行程覆盖率
# 用法：python3 tools/build_quality.py [--geo 秒数]   不带 --geo 只算覆盖率
import json, re, sys, os, time, math, urllib.parse, urllib.request, glob

A = json.load(open('data/catalog/cn_5a.json'))['items']
H = json.load(open('data/catalog/cn_heritage.json'))['items']
GP = 'data/geo/quality.json'
GEO = json.load(open(GP)) if os.path.exists(GP) else {}
WIDE = {'新疆', '西藏', '内蒙古', '青海', '甘肃', '四川', '黑龙江', '云南'}
UA = {'User-Agent': 'zouni-travel-data/1.0 (zouni.app)'}

SUFFIX = r'(风景|国家级旅游度假区|旅游度假区|生态文化旅游区|文化旅游景区|文化旅游区|旅游风景区|风景名胜区|旅游景区|旅游区|风景区|文化园区|景区|游览区|国家地质公园|国家森林公园|国家级自然保护区|自然保护区|旅游度假村)$'


def short(n):
    s = re.sub(r'[（(].*?[)）]', '', n).strip()
    for _ in range(2):
        s = re.sub(r'^.{2,8}?(自治州|市|州|地区|盟)(?=.{2,})', '', s)   # 去掉开头的“XX市/州/盟”（最多两层）
    s = re.sub(r'^.{1,3}?(县|区)(?=.{2,})', '', s)                  # 再去掉“玉山县、江口县”这类
    s = re.sub(SUFFIX, '', s).strip()
    s = re.sub(SUFFIX, '', s).strip()
    return s or n


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def nominatim(q, cc='cn'):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 3, 'countrycodes': cc, 'accept-language': 'zh'})
    try:
        r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    except Exception:
        r = []
    time.sleep(1.1)
    return r


ALIAS = {   # 名字对不上的，用这些词判断有没有排进行程
 '杭州西湖': ['西湖', '断桥', '苏堤', '雷峰塔'], '秦始皇陵及兵马俑坑': ['兵马俑', '秦始皇帝陵'], '秦始皇兵马俑博物馆': ['兵马俑', '秦始皇帝陵'],
 '八达岭—慕田峪长城': ['慕田峪', '八达岭'], '长城': ['慕田峪', '八达岭', '山海关', '嘉峪关'], '明清皇宫': ['故宫'], '苏州古典园林': ['拙政园', '留园', '狮子林', '网师园'], '苏州园林': ['拙政园', '留园', '狮子林'],
 '皖南古村落': ['宏村', '西递'], '福建土楼': ['土楼', '田螺坑'], '武陵源': ['袁家界', '天子山', '武陵源', '十里画廊'], '澳门历史城区': ['大三巴', '议事亭前地'],
 '登封“天地之中”历史建筑群': ['少林寺', '嵩山'], '登封天地之中历史建筑群': ['少林寺', '嵩山'], '新疆天山': ['那拉提', '天山天池', '喀拉峻', '巴音布鲁克'],
 '中国南方喀斯特': ['荔波', '小七孔', '武隆', '漓江', '石林', '金佛山', '环江'], '中国丹霞': ['丹霞山', '崀山', '龟峰', '泰宁', '江郎山', '赤水'],
 '云南三江并流': ['梅里', '虎跳峡', '普达措', '老君山'], '四川大熊猫栖息地': ['卧龙', '四姑娘山', '夹金山'],
 '丝绸之路': ['大雁塔', '小雁塔', '麦积山', '玉门关', '阳关', '交河故城', '高昌故城', '大明宫'], '大运河': ['拱宸桥', '大运河'],
 '明清皇家陵寝': ['十三陵', '明孝陵', '清东陵', '清西陵', '显陵', '北陵'], '承德避暑山庄及其周围寺庙': ['避暑山庄'], '曲阜孔庙': ['三孔', '孔庙', '孔府'],
 '高句丽王城': ['集安', '五女山'], '红河哈尼梯田文化景观': ['元阳', '哈尼梯田', '坝达', '多依树', '老虎嘴'], '泉州': ['开元寺', '清净寺', '泉州'], '北京中轴线': ['天安门', '故宫', '景山', '天坛', '钟鼓楼', '永定门'],
 '土司遗址': ['老司城', '唐崖', '海龙屯'], '中国黄': ['条子泥', '黄海湿地'], '峨眉山': ['峨眉山', '乐山大佛'], '青城山': ['青城山', '都江堰'], '开平碉楼与村落': ['开平碉楼', '自力村'],
 '花山岩画': ['花山'], '庐山国家公园': ['庐山', '牯岭', '三叠泉', '含鄱口', '如琴湖'], '庐山': ['牯岭', '三叠泉', '含鄱口', '如琴湖'], '武当山': ['武当山'],
 '三清山': ['三清山', '南清园'], '五台山': ['显通寺', '塔院寺', '黛螺顶', '台怀'], '武夷山': ['天游峰', '九曲溪', '大红袍'], '大足石刻': ['宝顶山', '北山石刻'],
 '神农架': ['神农顶', '大九湖', '木鱼镇'], '嵩山少林': ['少林寺'], '高句丽文物古迹': ['丸都山城', '国内城', '好太王碑', '将军坟'], '扎龙生态': ['扎龙'], '环球恐龙城': ['中华恐龙园'], '周恩来故里': ['周恩来故居', '周恩来纪念馆'], '木兰文化生态': ['木兰天池'], '汶川特别': ['映秀', '水磨古镇'], '法门文化': ['法门寺'], '延安革命纪念地': ['宝塔山', '枣园', '延安革命纪念馆'], '青铜峡黄河大峡谷': ['108塔', '一百零八塔'], '观澜湖': ['观澜湖'], '天涯海角': ['天涯海角'], '青海可可西里': ['索南达杰保护站', '楚玛尔河', '昆仑山口'], '明故城三孔': ['孔庙', '孔府', '孔林'], '安仁古镇': ['刘氏庄园', '建川博物馆'], '嘉峪关文物': ['嘉峪关关城', '悬壁长城', '长城第一墩'], '华侨城': ['世界之窗'], '孙中山故里': ['孙中山故居'], '星湖': ['七星岩'], '奥帆海洋': ['奥帆中心'], '镇北堡西部影视城': ['镇北堡'], '可可托海': ['三号矿坑', '额尔齐斯大峡谷', '可可托海'], '龙虎山': ['泸溪河', '仙水岩', '天师府'], '武功山': ['武功山'], '横店影视城': ['横店'], '晋祠天龙山': ['晋祠'], '赛里木湖': ['赛里木湖'], '樟江': ['小七孔', '大七孔'], '赤水丹霞': ['赤水大瀑布', '佛光岩'], '泰宁': ['大金湖', '上清溪'], '中国共产党一大': ['中共一大'], '火山热海': ['热海'], '中俄边境': ['满洲里国门', '套娃广场'], '阿尔山': ['阿尔山'], '天下第一泉': ['趵突泉', '大明湖', '黑虎泉'], '古徽州': ['棠樾', '呈坎', '唐模', '徽州古城'], '岳麓山': ['岳麓山', '橘子洲', '岳麓书院'], '韶山': ['毛泽东同志故居'], '山海关': ['天下第一关', '老龙头'], '三孔': ['孔庙', '孔府', '孔林'], '长白山': ['长白山天池', '长白瀑布'], '喀什噶尔老城': ['喀什老城', '喀什古城'], '帕米尔': ['卡拉库里湖', '石头城', '塔县'], '天山天池': ['天山天池'], '普达措': ['普达措'], '镇远古城': ['镇远'], '四姑娘山': ['双桥沟', '长坪沟', '四姑娘山'], '中国丹霞': ['丹霞山', '崀山', '龟峰', '泰宁', '江郎山', '赤水'], '东方明珠': ['陆家嘴'], '黄鹤楼': ['黄鹤楼'], '泰山': ['南天门', '玉皇顶', '岱庙', '十八盘'], '避暑山庄': ['避暑山庄', '普宁寺', '普陀宗乘']}

items = []
for a in A:
    items.append({'name': a['name'], 'short': short(a['name']), 'prov': a['prov'], 'tags': ['5A'], 'year': a['year']})
for h in H:
    core = re.split(r'[—：、（]', h['name'])[0].replace('“', '').replace('”', '')
    hit = next((x for x in items if x['prov'] == h['prov'] and (core in x['short'] or x['short'] in h['name'])), None)
    if hit:
        hit['tags'].append('世界遗产'); hit['heritage'] = h['name']
    else:
        items.append({'name': h['name'], 'short': core, 'prov': h['prov'], 'tags': ['世界遗产'], 'year': h['year'], 'heritage': h['name']})
for i, x in enumerate(items): x['id'] = 'q%03d' % (i + 1)

# —— 坐标（可分几次跑完）——
if '--geo' in sys.argv:
    budget = int(sys.argv[sys.argv.index('--geo') + 1]); t0 = time.time()
    for p in sorted({x['prov'] for x in items}):
        if 'P|' + p not in GEO:
            r = nominatim(p + ('市' if p in ('北京', '天津', '上海', '重庆') else ''), 'cn,mo,hk')
            GEO['P|' + p] = {'lat': float(r[0]['lat']), 'lng': float(r[0]['lon'])} if r else None
    for x in items:
        if time.time() - t0 > budget: break
        k = x['prov'] + '|' + x['short']
        if k in GEO: continue
        pc = GEO.get('P|' + x['prov']); lim = 1500 if x['prov'] in WIDE else 700; got = None
        for q in (x['short'], x['prov'] + ' ' + x['short'], x['name']):
            for r in nominatim(q, 'mo' if x['prov'] == '澳门' else 'cn'):
                pt = (float(r['lat']), float(r['lon']))
                if not pc or km((pc['lat'], pc['lng']), pt) <= lim:
                    got = {'lat': pt[0], 'lng': pt[1], 'hit': r['display_name'][:50], 'q': q}; break
            if got: break
        GEO[k] = got
        json.dump(GEO, open(GP, 'w'), ensure_ascii=False, indent=1)

# —— 覆盖：现有行程里出现过就算覆盖 ——
stops = []   # (线路, 文本)
IT = json.load(open('data/itineraries.json'))['itineraries']
for rid, it in IT.items():
    for d in it['days']:
        for s in d['stops']: stops.append((rid, s['name'] + ' ' + (s.get('q') or '')))
s = open('build/routes.js', encoding='utf-8').read()
R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', s).group(1))
for rid, r in R.items():
    if r.get('compiled'): continue
    for d in r['days']:
        for w in d['rows']:
            if w['type'] in ('see', 'fun', 'eat'): stops.append((rid, (w.get('name') or '') + ' ' + (w.get('place') or '') + ' ' + (w.get('poi') or '')))
for n in ('布达拉宫', '大昭寺', '罗布林卡', '色拉寺', '羊卓雍错', '纳木错', '扎什伦布寺', '卡若拉冰川'):
    stops.append(('xz7', n))
GENERIC = {'古城', '古镇', '公园', '博物馆', '大峡谷', '风景', '湖', '山'}
for x in items:
    base_keys = {x['short'], re.sub(r'(古城|古镇|遗址|公园|博物院|博物馆)$', '', x['short'])} | set(re.split(r'[-—·、－•]', x['short']))
    for a_k, toks in ALIAS.items():
        if a_k == x['short'] or x['short'].startswith(a_k) or (len(a_k) >= 3 and a_k in x['short'] and a_k not in ('大运河', '丝绸之路')) or a_k in (x.get('heritage') or '') or (x['short'] in a_k and len(x['short']) >= 3) or ('世界遗产' in x['tags'] and a_k in x['name']): base_keys |= set(toks)
    keys = [k for k in base_keys if len(k) >= 2 and k not in GENERIC]
    def hit(t):
        if any(k in t for k in keys): return True
        toks = [w for w in re.split(r'[\s·•（）()]+', t) if len(w) >= 3 and w not in ('博物馆', '风景区', '步行街', '古城墙', '回程')]
        return any(w in x['short'] for w in toks)
    x['covered'] = sorted({rid for rid, t in stops if hit(t)})
    g = GEO.get(x['prov'] + '|' + x['short'])
    if g: x['lat'], x['lng'] = round(g['lat'], 4), round(g['lng'], 4)
json.dump({'note': '优质景点 = 国家 5A（359）∪ 世界遗产（60）；covered 是已经排进行程的线路', 'count': len(items), 'items': items},
          open('data/catalog/cn_quality.json', 'w'), ensure_ascii=False, indent=1)
cov = sum(1 for x in items if x['covered']); geo = sum(1 for x in items if 'lat' in x)
print('优质景点', len(items), '· 有坐标', geo, '· 已排进行程', cov, '(%.0f%%)' % (100 * cov / len(items)))
from collections import defaultdict
P = defaultdict(lambda: [0, 0])
for x in items: P[x['prov']][1] += 1; P[x['prov']][0] += bool(x['covered'])
print(' '.join(f'{p}{a}/{b}' for p, (a, b) in sorted(P.items(), key=lambda kv: kv[1][0] / kv[1][1])))
hh = [x['short'] for x in items if '世界遗产' in x['tags'] and not x['covered']]
print('没排进行程的世界遗产', len(hh), '：', '、'.join(hh))
