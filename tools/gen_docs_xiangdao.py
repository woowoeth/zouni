# -*- coding: utf-8 -*-
# 《我的美食向导》（陈晓卿主持，腾讯视频）。出处：澎湃新闻、北京日报、搜狐对两季的报道。
# 只收报道里明确写到的地区：第一季 长沙、潮汕、喀什、温州、山西；第二季（2026-10-15 开播）乐山、天津、漳州、拉萨、上海、北海。
# 第一季另有“云之南、杭嘉湖、齐鲁”只见于一篇文章，没有第二个出处，不收。
# 只有乐山一集查到了具体的吃的（钵钵鸡、临江鳝丝、峨眉豆腐脑、跷脚牛肉），其余按“拍过这座城”挂，不编菜名。
# 用法：python3 tools/gen_docs_xiangdao.py   （幂等：先去掉旧的再追加）
import json
P = 'data/catalog/docs_more.json'
SHOW = '我的美食向导'
rows = [
 (1, '长沙', '湖南', ['长沙']), (1, '潮汕', '广东', ['潮汕', '汕头', '潮州']), (1, '喀什', '新疆', ['喀什']),
 (1, '温州', '浙江', ['温州']), (1, '山西', '山西', ['山西']),
 (2, '乐山', '四川', ['乐山']), (2, '天津', '天津', ['天津']), (2, '漳州', '福建', ['漳州']),
 (2, '拉萨', '西藏', ['拉萨']), (2, '上海', '上海', ['上海']), (2, '北海', '广西', ['北海']),
]
d = [x for x in json.load(open(P, encoding='utf-8')) if x.get('show') != SHOW]
for s, place, prov, keys in rows:
    d.append({'show': SHOW, 's': s, 'ep': '', 'food': place, 'place': place, 'prov': prov, 'keys': keys})
for dish in ('钵钵鸡', '临江鳝丝', '峨眉豆腐脑', '跷脚牛肉'):
    d.append({'show': SHOW, 's': 2, 'ep': '', 'food': dish, 'place': '乐山', 'prov': '四川', 'keys': ['乐山']})
json.dump(d, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('写了', len(rows) + 4, '条，docs_more 共', len(d))
