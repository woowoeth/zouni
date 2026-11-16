# 2026-11-13：batch_1113 五条线入库后的补丁（add_routes_json.py 不带 air_min，菜要手写——自动挑的是全美菜池，黄石会排到“马里兰蟹饼”）。幂等。菜名不能以地名开头（“三明治”被当成福建三明、“墨西哥卷饼”被当成外地菜换掉），同一条线不重复。
import json
p = 'data/itineraries.json'; J = json.load(open(p, encoding='utf-8')); it = J['itineraries']
D = lambda dish, place: {'dish': dish, 'place': place}
P = {
 'xy701a': [{'air_min': 120, 'lunch': D('汉堡', '老忠实游客村的餐厅'), 'dinner': D('牛排', '西黄石镇上')}, {'lunch': D('热狗', '峡谷村的餐厅'), 'dinner': D('烤鳟鱼', '西黄石镇上')}, {'air_min': 100, 'lunch': D('披萨', '猛犸游客村的餐厅')}],
 'xy702a': [{'lunch': D('蛤蜊浓汤', '派克市场里'), 'dinner': D('烤三文鱼', '市中心')}, {'lunch': D('汉堡', '飞行博物馆的餐厅')}],
 'xy703a': [{'lunch': D('汉堡', '斯普林代尔镇上'), 'dinner': D('烤肋排', '斯普林代尔镇上')}, {'air_min': 170}],
 'xy704a': [{'lunch': D('皿乌冬', '浦上一带'), 'dinner': D('土耳其饭', '市中心')}, {'lunch': D('长崎什锦面', '新地中华街一带')}],
 'xy705a': [{'start': '09:00', 'air_min': 150, 'lunch': D('汤波荞麦面', '东武日光站到神桥的路上'), 'dinner': D('汤波料理', '日光市区')}, {'air_min': 180}],
}
for rid, ds in P.items():
    for d, u in zip(it[rid]['days'], ds): d.update(u)
T = {('xy704a', 0): ('傍晚去稻佐山，坐缆车上山顶展望台，看长崎港两边的山坡亮灯。', '下午去稻佐山，坐缆车上山顶展望台，看长崎港和两岸山坡上的房子；缆车晚上也开，想看夜景可以晚饭后再上来。'),
     ('xy702a', 1): ('傍晚打车上安妮女王山的凯瑞公园', '然后打车上安妮女王山的凯瑞公园')}
for (rid, i), (a, b) in T.items():
    d = it[rid]['days'][i]
    if a in d['text']: d['text'] = d['text'].replace(a, b)
json.dump(J, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
