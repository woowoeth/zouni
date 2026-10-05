# 线路数据 v2

每条线路一份 JSON（`data/routes/<id>.json`），每天一个对象。字段按用户每天要回答的问题组织，不按引擎内部结构。

## 每天要回答的问题 → 字段

| 用户的问题 | 字段 | 来源 |
|---|---|---|
| 几点出发、几点到、去哪 | `timeline[]` 里 `type: dep` 和 `type: see` | 引擎排程（已有） |
| 吃什么、在哪吃、多少钱 | `timeline[]` 里 `type: eat`：`dish` 当地特色，没有就写 `随意`；`place`；`price` | 待补，需逐城核实 |
| 玩点当地的 | `timeline[]` 里 `type: fun`：当地人的活动、夜景、体验 | 待补 |
| 今晚住哪、订没订 | `stay.tiers.luxury / upscale / budget`：名称、卖点、价格、`fits`（和路线顺不顺路） | 引擎只有片区和估价，三档待补 |
| 眼前是什么、有什么规矩 | `story.text`（两三句历史）+ `story.manners[]`（规矩） | 引擎 `vibe` 是草稿，需核实 |
| 光线和海拔 | `facts.altitude_m`、`lat/lng`（日出日落、月相按日期实算）、`facts.temp` | 海拔部分有，坐标按城市补，气温待补 |
| 路上要注意什么 | `notes[]`：区间测速、加油、检查站、山口 | 引擎 `pre.via` 有一部分 |

## timeline 条目

```
{ "t": "09:30", "type": "dep",  "to": "羊卓雍错", "mode": "drive", "min": 90, "km": 65, "via": "甘巴拉垭口 5,030 m" }
{ "t": "11:00", "type": "see",  "name": "羊卓雍错", "dur": 180, "cost": 30, "ticket": "tix", "indoor": false, "lock": null }
{ "t": "12:30", "type": "eat",  "slot": "午饭", "dish": "随意", "place": "湖边小馆", "price": null }
{ "t": "21:00", "type": "fun",  "name": "看星星", "detail": "按月相算" }
{ "t": "晚上",  "type": "stay", "city": "拉萨" }
```

- 每次换地方都要有一条 `dep`，写出发时间、方式、时长。
- `eat.dish` 只写当地特色；当地没有特色或没核实到，写 `随意`，不硬编。
- `see.lock`：定时票、只在工作日、要预约这类硬约束。

## stay

```
"stay": { "city": "拉萨", "nights": 3,
  "tiers": {
    "luxury":  { "name": "...", "sell": "全天供氧", "price": "约 ¥600 起", "fits": true },
    "upscale": { ... },
    "budget":  { ... } },
  "default": "luxury"   // 奢华不顺路时退到下一档，并写明原因
}
```

## 状态字段

每条线路带 `status`，逐项标明来源：`engine`（引擎算的）、`verified`（核实过）、`draft`（草稿待核实）、`todo`（空着）。西藏 `xz7` 是按这套结构核实填满的样板。

## 地理与气候（已补齐）

`data/geo/places.resolved.json`：87 个住宿地点
- 坐标：OpenStreetMap Nominatim；有同名的，按同一条线路其他地点的位置挑最近的候选；相邻两天超过 700 公里的逐个复查
- 海拔：Open-Meteo 高程
- 往年气温：Open-Meteo 历史数据，2016–2025 每月平均最高 / 最低

导出时写进每天的 `lat / lng`、`facts.altitude_m`、`facts.high_altitude`（≥3,000 米）、`facts.temp_by_month`。
