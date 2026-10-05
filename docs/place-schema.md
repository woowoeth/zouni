# 地点库（data/places.json）

结构定义：data/schema/place.schema.json。一条记录 = 一个地点。

| 字段 | 说明 |
|---|---|
| id | 目的地 id + 短哈希，全库唯一 |
| type | sight 景点 / food 饭馆 / stay 住宿 / fun 当地体验 / dish 当地菜 |
| dest / country / city / area | 归属：目的地（destinations.json 的 id）、国家码、城市、片区 |
| price | {amount, currency, per, text}；日本用 JPY，住宿 per=night |
| tier | 住宿档位 luxury / upscale / budget |
| dishes / hours / slots | 饭馆的菜、营业时间（如 close 13:00）、只排午饭或晚饭 |
| rating | {score, count, source, asOf}，只写公开页面能核实的 |
| rank / signature / highlights | 榜单、招牌、我们自己的话概括（不搬用户评价原文） |
| links | dianping（大众点评）、map（国内高德、海外谷歌）、ctrip（住宿） |
| usedIn / sources / verified | 出现在哪些线路、来源、核实日期 |

生成：`python3 tools/build_places.py`（读城市表、线路里的景点、目的地表、口碑补充表 data/places_enrich.json）。
大众点评链接：上海 / 北京 / 杭州用已核实的城市 id 搜索页（1 / 2 / 3），其余用点评搜索页带城市名。
评价原文：大众点评要登录才能取，且不允许抓取；页面只显示核实过的评分、点评数、榜单、招牌，点“点评”去看全部评价。
