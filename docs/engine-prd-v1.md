# 走你 · 攻略引擎 PRD v1.0

> 文档范围：前端 vanilla JS 单文件引擎，支撑「走你 - 计划赶得上变化」七条线路的行程推算与实时重排。  
> 对应交付物：`zouni-xj-10d.html`（含全部线路数据与引擎源码）  
> 最后更新：2026-08-03

---

## 1. 核心概念

### 1.1 一等公民层级

```
ROUTE（线路）
  └── DAY（日程天） × N
        ├── pre（当天入城/行驶段，可含班次 dep）
        ├── STOP[] × M（景点 / 餐饮 / 接驳）
        ├── CONN[] × M-1（站间接驳）
        └── post（当天出城/返回段）
  └── LODGE[] × N（住宿，最后一天为 null）
  └── CLUSTER（多选片区，仅 XJ 系）
  └── INSERTS{}（可选插入段，仅 XJ 系）
```

### 1.2 时间单位

全引擎统一用 **分钟数**（`0 = 00:00`）。`start=600` 表示 10:00 出发，`hardEnd=1320` 表示 22:00 必须抵店。

---

## 2. Stop 字段字典

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `k` | string | ✅ | 唯一 key，在天内唯一即可 |
| `name` | string | ✅ | 显示名，格式 `景点名 · 副标题` |
| `era` | string | ✅ | 一行白描（朝代/特征） |
| `dur` | number | ✅ | 建议停留分钟；`0` = 弹性停留（受 openMin/openMax 控制） |
| `prio` | number | ✅ | 让位优先级，`0` = 不让位，数字越大越先被砍 |
| `cost` | number | ✅ | 门票/餐饮费用（人均） |
| `cat` | `'tix'` \| `'food'` \| `'free'` | ✅ | 费用分类 |
| `indoor` | boolean | ✅ | 是否室内（用于雨天替身判断） |
| `vibe` | string | ✅ | 一句话氛围描写 |
| `must` | `[label, text]` | ✅ | 必看/必做项，`label` 显示为 chip |
| `chips` | `[[tag, text], ...]` | ✅ | 补充信息 chip 列表，tag 为 `'up'`/`'down'`/`''` |
| `q` | string | ✅ | 导航搜索词（高德/Google） |
| `earliest` | number | — | 最早到达时间（景区开门） |
| `latest` | number | — | 最晚离开时间（景区关门） |
| `openUntil` | number | — | 弹性停留模式：最晚结束时间 |
| `openMin` | number | — | 弹性停留模式：最少停留分钟 |
| `openMax` | number | — | 弹性停留模式：最多停留分钟（封顶，防止撑到天黑） |
| `dep` | `{first, every, last}` | — | **班次吸附**：first/every/last 均为分钟数；到达时间 snap 到最近的班次 |
| `rainAlt` | Stop 子集 | — | 雨天替身：覆盖当前 stop 的部分字段 |
| `detail` | string | — | 展开详情（HTML 片段） |
| `km` | number | — | 本 stop 贡献的里程（仅 `erhai-loop` 类环游场景） |
| `id` | string | — | chooser 专用：同 `k`，用于 selector 状态追踪 |
| `opts` | Stop[] | — | chooser 模式：多选一，替代 `name/cost/...` 直接字段 |
| `optLabel` | string | — | chooser 标题（如 `'敦煌晚饭 · 选一家'`） |
| `prio`（chooser） | number | — | chooser 整体让位优先级 |
| `cat`（chooser） | `'food'` | — | chooser 分类 |

**chooser 模式**：stop 含 `opts[]` 时，当前选中项由 `sels[stop.id]` 决定（index）。`profile` 字段可触发口味记录。`why` 字段解释为何这个选项更合适。

---

## 3. Conn 字段字典

接驳件是**一等公民**，出现在三个位置：`day.pre`、`day.post`、`day.stops[]`（停之间的 `{conn:...}` 行）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | ✅ | `walk` / `metro` / `tram` / `drive` / `shuttle` / `train` / `ferry` / `cable` |
| `conn` | string | ✅ | 显示文字，格式 `起点 → 终点 · Xkm · 约Y分` |
| `min` | number | ✅ | 行程分钟（引擎计时用） |
| `cost` | number | ✅ | 接驳费用（人均） |
| `km` | number | — | **仅 `drive` 计油**；其他 mode 不填 |
| `via` | string | — | 小字提示（加油点、注意事项、班次提醒） |
| `dep` | `{first, every, last}` | — | **班次吸附**；区间车/渡轮/缆车/火车同机制（见 §5） |
| `alt` | Conn | — | 雨天/管制替身；`alt.km` / `alt.cost` 会联动油费路桥 |

---

## 4. Lodge 字段字典

LODGES 是与 DAYS 等长的数组，最后一天为 `null`（无住宿）。

**单项 Lodge：**
```js
{ city: '西宁力盟街区', price: 280, why: '步行 5 分到夜市', q: '搜索词' }
```

**二选一 Lodge：**
```js
{ opts: [
    { city: '双廊 · 海景房', price: 420, why: '...', q: '...' },
    { city: '双廊 · 巷内房', price: 300, why: '...', q: '...' }
  ]
}
```

`lodge4` 为全局 int（0/1），thrift 策略设为 1 以自动选便宜项。`lodgeOf(di)` 返回当前选中的 lodge 对象。

---

## 5. 班次吸附机制（snapDep）

```js
function snapDep(c, t) {
  if (!c || !c.dep) return t;
  const d = c.dep;
  if (t <= d.first) return d.first;
  if (t > d.last) return t;          // 过末班：时间不倒流，如实延误
  const n = d.first + Math.ceil((t - d.first) / d.every) * d.every;
  return Math.min(n, d.last);
}
```

**适用对象**：stop.dep（莫高窟批次/双桥沟区间车/普达措/山顶缆车）& conn.dep（天星小轮/独山子区间车）  
**过末班行为**：返回当前到达时间（不吸附），引擎如实延误，让位循环接管。

---

## 6. resolveDay 主逻辑（伪代码）

```
resolveDay(di):
  1. dayMaterial(di) → 展开 cluster 多选 + inserts 插入段 → {rs, cs}
  2. 计算出发时间 t：
     - 未出发：t = day.start + mods.off
     - 已出发（m.done.preDepart）：t = done.anchor + pre.min + carry.min
     - 已出发（后续接驳定格）：t = done.anchor + carry.min
  3. 如有 pre，t = snapDep(pre, t) + pre.min
  4. 冻结已走站（doneKeys）；剩余站入 rem[]
  5. walk（顺推）：
     for s in rem:
       if s.dep: arr = snapDep(s, t)  // stop 上的班次
       if s.earliest: arr = max(arr, earliest)
       if s.openUntil 且 arr > openUntil - openMin: → 违约
       dur = s.dur || clamp(openUntil-arr, openMin, openMax)
       if s.latest 且 arr+dur > latest: → 违约
       out.push({arr, dur}); t = arr + dur
       if i < len-1: t = snapDep(conns[i], t) + conns[i].min
  6. 违约让位（循环直到无违约或无可让）：
     - 仅 prio > 0 且未 pinned 的站可被砍
     - 场次违约：只从该站之前挑最高 prio 的砍
     - cutConns：砍首站 → 折 carry；砍中段 → 合并接驳；砍末站 → 删进站
     - 里程守恒：切中段时合并 km
  7. post：t += post.min（不吸附，按均值）
  8. cats 统计：tix/food（已走+未走）、tolls（所有 conn.cost）、km（drive conn + stop.km）
  9. 返回 {sched, conns, dropped, emptyAt, cats, end, pre, post, doneCount}
```

**关键约定**：
- `prio=0` 永不让位（镇店之宝）
- `done` 定格后仅重排后续，定格站不可回退
- `rain=true` 时所有 `alt` 字段生效，`alt` 里的 conn 同样走 snapDep

---

## 7. 出口清单（高德 / Google 双栈）

```js
const navQ = q => (RT && RT.nav === 'google')
  ? `https://www.google.com/maps/search/?api=1&query=${gq(q)}`
  : `https://uri.amap.com/search?keyword=${gq(q)}`;
```

| route.nav | 适用场景 |
|-----------|---------|
| `'amap'`  | 境内所有线路（新疆/青甘/川西/滇西北） |
| `'google'` | 境外或香港（Google Maps） |

导航链接出现在：接驳件「导航」按钮 + todo 项 `url` 字段。

---

## 8. 线路注册表字段规格（ROUTES）

```js
{
  name: string,          // '北疆环线'，地图/UI 用
  dest: string,          // 输入框默认值，'新疆 · 北疆环线'
  fam: string,           // 路线族，'xj'/'qg'/'cx'/'dxb'/'hk'
  title: string,         // 计划页标题 Emoji + 名称
  meta: string,          // 计划页副标题（天数 · 出发日期）
  why: string,           // 行程逻辑白话（计划页说明卡）
  weather: string,       // 天气行（含温度范围 · 日落时间）
  days: DAY[],           // 日程数组
  lodges: LODGE[],       // 住宿数组（与 days 等长，最后 null）
  nights: number,        // 住宿晚数（用于统计展示）
  cluster: CLUSTER|null, // 多选片区，非 XJ 为 null
  inserts: {[id]:INSERT}|null, // 可插入站，非 XJ 为 null
  defSels: object,       // chooser 默认选中 index
  defSelsM: number[]|null, // cluster 默认多选 index 列表
  rent: number,          // 全程租车费（总价，/2 = 人均）
  roadfood: number,      // 路餐口径（总价，已含入 food 底数）
  perCar: boolean,       // true=自驾分摊；false=逐人按实计（香港）
  nav: 'amap'|'google',  // 导航栈
  strength: '轻'|'中'|'重', // 强度展示
  carLabel: string,      // 费用表「交通」行标签
  tixLabel: string,      // 费用表「门票」行标签
  foodLabel: string,     // 费用表「餐饮」行标签
  hero1v: string|null,   // 非驾车线路的 stat1v（如 '2<small>晚</small>'）
  hero1k: string|null,   // 非驾车线路的 stat1k（如 '住佐敦不挪窝'）
  overTip: string,       // 超预算时的修改提示文字
  budgets: [{l,v}],      // 预算两档：[{l:'宽松',v:7500},{l:'精打细算',v:6800}]
  thrift: function|null, // 精打细算策略函数（设 lodge4=1、改 sels 等）
  tastes: TASTE[],       // 口味偏好选项
  seasons: SEASON[],     // 赶季节模块
  extras: EXTRA[],       // 路上还有模块
  extrasSub: string,     // extras 小标签（'备着的还有 玩X · 吃Y · 住Z'）
  todos: function,       // 出发清单生成函数 → TODO[]
  map: MAP               // 地图配置（见下）
}
```

### 8.1 MAP 字段

```js
{
  nodes: [{n, x, y, lx, ly, a}],  // 节点列表；坐标系 640×320px
  order: number[],                 // 参与当前拼法的节点 index（环线图顺序）
  loop: boolean,                   // true = 闭合 Z 路径
  base: string|undefined,          // SVG path 覆盖（非环线路用，如香港三辐条）
  seg: (null|[from,to])[],        // 每天的高亮段（null = 当天不移动）
  tonight: number[],              // 每天今晚住宿节点 index；-1 = 还车/无住
}
```

节点标签锚点字段 `a`：`'start'`/`'middle'`/`'end'`（对应 SVG text-anchor）

---

## 9. Cluster 字段字典（仅 XJ）

```js
CLUSTER = {
  label: string,           // 多选说明文字
  opts: [{
    name, era, dur, cost,  // 同 stop
    prio, cat, vibe, must, chips, q,
    profile: string,       // 口味档案写入词
    join: CONN,            // 与前一个选项的连接段
    ...stopFields
  }],
  emptyConn: CONN|null     // 空选时替换掉原 conn 的接驳（走直达段）
}
```

空选（selsM 为空）时：渲染 `cluster-empty` 占位，移除前置 conn，插入 emptyConn（若有）。

---

## 10. Insert 字段字典（仅 XJ）

```js
INSERTS = {
  [id: string]: {
    day: number,       // 插入哪天（0-indexed）
    afterK: string,    // 插在哪个 stop.k 之后
    label: string,     // 按钮文案，'排进 D4'
    brief: string,     // extras 卡里的摘要说明
    profile: string,   // 口味档案写入词
    stop: STOP,        // 要插入的站点对象
    conns: [CONN, CONN] // [入站前接驳, 入站后接驳]（替换原来的那一段 conn）
  }
}
```

---

## 11. TODO 字段字典

`todos()` 函数返回 `TODO[]`，每项：

```js
{
  k: string,          // 唯一 key
  tag: [style, text], // chip，style='up'/'down'/''
  text: string,       // 一句话说明
  v: string,          // 右侧附加文字（如 '更新 08-02'）
  url: string|null    // 可选跳转链接
}
```

---

## 12. 费用计算规则

```
totals():
  tix   = Σ resolved[i].cats.tix    （已走+未走的 tix 站合计）
  food  = ROADFOOD + Σ cats.food    （路餐底数 + 餐饮站）
  tolls = Σ cats.tolls              （所有 conn.cost）
  km    = Σ cats.km                 （所有 drive conn.km + stop.km）

  car   = perCar=false → tolls      （香港：地铁/渡轮人均实付）
          perCar=true  → (RENT + km×FUEL + tolls) / 2  （自驾：/2 人均）

  lodge = Σ lodgeOf(i).price / 2    （房价/2 = 人均）

  total = tix + food + car + lodge
```

**FUEL 常量**：`0.65` 元/km（含油耗 + 小额保养折算）

---

## 13. 七条线路速查表

| id | 名称 | 天数 | km | 宽松 | 精打 | nav | perCar |
|----|------|------|-----|------|------|-----|--------|
| xj8 | 北疆环线 8天 | 8 | 2,884 | ≤6,500 | ≤5,900 | amap | ✅ |
| xj10 | 北疆环线 10天 | 10 | 2,947 | ≤7,500 | ≤6,800 | amap | ✅ |
| xj12 | 北疆环线 12天 | 12 | 3,002 | ≤8,800 | ≤8,000 | amap | ✅ |
| qg8 | 青甘大环线 | 8 | 2,226 | ≤5,400 | ≤4,900 | amap | ✅ |
| cx5 | 川西小环线 | 5 | 963 | ≤3,200 | ≤2,900 | amap | ✅ |
| dxb6 | 滇西北 | 6 | 767 | ≤3,800 | ≤3,400 | amap | ✅ |
| hk3 | 香港周末 | 3 | 0 | ≤2,000 | ≤1,750 | google | ❌ |

---

## 14. 已知边角与规则约定

| 场景 | 当前行为 | 是否接受 |
|------|---------|--------|
| D1 无 pre 时「现在出发」键缺位 | 靠拨盘调整出发偏移，第一站后的 conn 上有按钮 | ✅ 可接受 |
| post conn 的 dep 不吸附 | 天星小轮回程按 dep.every 均值估算 | ✅ 可接受 |
| budget chips 在抽卡后不可见 | 需点「修改行程」展开折叠区才能切换预算 | ✅ 可接受 |
| xj8 换档（curDays）时 inserts/tastes 清零 | loadRoute 调用 inserted.clear() / tastes.clear() | ✅ 设计如此 |
| 过末班后「现在出发」时间不倒流 | snapDep 护栏：over last → 返回原始到达时间 | ✅ |

---

## 附录 A：接驳三形态对照

| mode | km 计油 | dep 吸附 | cost 计算方式 | 典型案例 |
|------|---------|---------|-------------|--------|
| `drive` | ✅ | ❌ | 统一进 tolls | 景区间自驾 |
| `shuttle` | ❌ | ✅ | 统一进 tolls | 双桥沟区间车 |
| `metro` | ❌ | ❌ | 统一进 tolls | 香港地铁 |
| `tram` | ❌ | ❌ | 统一进 tolls | 叮叮车 |
| `ferry` | ❌ | ✅ | 统一进 tolls | 天星小轮 |
| `cable` | ❌ | ✅ | 统一进 tolls | 山顶缆车 |
| `train` | ❌ | ✅ | 统一进 tolls | 火车（暂无案例） |
| `walk` | ❌ | ❌ | 0 | 景区内步行 |

---

## 附录 B：地图节点坐标系

所有路线共用一套 640×320 px 坐标系（SVG viewBox）。  
节点标签对齐：`lx`/`ly` = 相对节点中心的偏移量；`a` = SVG text-anchor（`start`/`middle`/`end`）。  
环线路的 `loop:true` 在 path 末尾追加 `Z`；非环线路（川西/滇西北折线）`loop:false` 不闭合；  
香港辐条型路线用 `base` 字段直接传入 SVG path 字符串（三条辐条显式 `M...L`）。

---

*以上内容从 `zouni-xj-10d.html` 源码提取，随代码同步更新。*
