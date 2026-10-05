# 走你 · 目的地与线路目录（结构化）

一份数据，两种视图：本期页（按假期挑）和“去哪儿”（按月份、出发地、预算、天数挑）都从这里生成，不再在页面里写死。

## 文件
| 文件 | 内容 |
|---|---|
| data/catalog/destinations.json | 56 个目的地：国内 34 个省级行政区（省 23、自治区 5、直辖市 4、特别行政区 2）+ 亚洲 22 国 |
| data/catalog/trips.json | 60 条线路（本期页用），每条挂在一个目的地下 |
| data/catalog/schema.json | 两种记录的字段定义（JSON Schema） |
| tools/build_catalog.py | 生成画布用的 catalog.js：ZOUNI_CATALOG（全量）、ZOUNI_ATLAS（去哪儿）、ZOUNI_MAIN_R（本期） |
| tools/validate_catalog.py | 体检：缺字段、引用断了、日期格式、价格上下限、坐标海拔范围、12 个月气温、季节自洽 |

## 目的地（destination）
- id、name、scope（domestic / asia）、kind（province / autonomous / municipality / sar / country）、region
- base：落脚城市 name、lat、lng、elev（米）、geoSource（nominatim / curated）
- months.best：最好的月份（1–12）
- days：{min, max} 建议天数
- see[]、eat[]
- entry：{cn: 大陆护照, hk: 香港特区护照}，核实不到写“出发前查”
- tip、status（ok / blocked，台湾为 blocked）
- climate：{"1": [白天平均最高, 夜里平均最低], …, "12": […]}，Open-Meteo 2016–2025
- trips[]：挂在下面的线路 id；engineRoutes[]：引擎里已有的路线；page：有完整页面时的地址

## 线路（trip）
- id、dest、name、region、days
- title、headline、dek、why
- price：{lo, hi, currency: CNY, basis: 每人·2 人同行·含往返大交通}
- tags[]：如 ["高海拔", "自驾"]
- season：{ok: [MM-DD, MM-DD], best: [MM-DD, MM-DD]}；anytime=true 时为 null
- status（ok / blocked）、page、engineRoute、poster（画布资源 id）

## 改数据的流程
1. 改 data/destinations.json / data/geo/destinations.json / data/catalog/trips.json
2. python3 tools/build_catalog.py <画布>/project/catalog.js
3. python3 tools/validate_catalog.py build/routes.js（有错误不发布）
