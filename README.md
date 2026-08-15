# 走你 · Zouni

> 输入去哪儿、几天、多少预算，出一份能直接照着走的攻略——逐日逐站，带车程、开放时间、住哪儿、每天花多少。
> 路上有变，自己就能重排。

线上：https://ourword.ai/zouni/ · 仓库：https://github.com/ourword-ai/zouni

**56 条线路 · 36 个目的地族 · 单文件 646KB**

---

## 快速开始

```bash
npm install          # 只有一个依赖：puppeteer（测试用）
npm start            # 起本地服务，浏览器打开 http://localhost:8080/src/
npm test             # 跑全套 21 项测试（约 4 分钟）
```

不想装依赖也行——`src/index.html` 是单文件的，直接用浏览器打开就能跑。

---

## 目录

```
src/                 产品本体
  index.html         主产物（单文件，可直接双击打开）
  zouni.html         三文件版入口（配合下面两个 js）
  zouni-data.js      数据层：56 条线路
  zouni-engine.js    引擎层：排期、算钱、重排

tests/               21 项测试
  run-all.sh         一键跑全套
  0-21*.js           各项详见下表

tools/               生产工具
  route-factory.js   新增线路的验收器（16 项检查）
  route-compiler.js  数据层等价性编译校验
  route-planner.js   排期规划辅助
  extra-pool.js      备选景点库（108 个，供「+1 天」用）
  extend-days.js     天数扩展规划（--report 看哪些族缺加长方案）
  proposal-scan.js   功能提案自动扫描
  release-log.js     发布日志（强制记录踩坑）
  preserve-external.js  发布前保留外部注入的 SEO 层
  poi-meta*.json     站点元数据

docs/                项目文档（重要，先读 sop.md）
  sop.md             项目 SOP —— 怎么做、什么不做、踩过的坑
  ui-spec.md         UI 方案 —— 尺寸、间距、状态机
  content-audit.md   内容矩阵 —— 56 条线路清单与省份分布
  province-plan.md   省份深度规划 —— 每个省还能补什么
  product-judgment.md   产品判断 —— 什么必须做、什么不做
  competitor-analysis.md  竞品分析
  release-log.md     发布日志 —— 42 次发布的踩坑记录
  proposals.md       功能提案单
  release-checklist.md  发布检查清单
  engine-prd-v1.md   引擎 PRD

photos/              配图工具（独立流程，不进主产物）
  build-photos.js    四级抓取：wiki条目图 → wikidata P18 → commons分类 → OSM地图
  render-map.py      地图渲染：拼 3×3 瓦片再居中裁剪
  make-review.js     生成人工核对表
  apply-review.js    应用核对结果
  covers.js          封面数据（base64 内嵌，35 张）
  photos.json        图源与版权信息
```

---

## 测试体系

`npm test` 会依次跑这 21 项，任一失败就中断：

| # | 名称 | 查什么 |
|---|---|---|
| 0 | slice | 数据层能否独立切出 |
| 1 | engine-sim | 无 DOM 环境下装载与算账 |
| 2 | static | 静态检查（Python）：11 项结构规则 |
| 3 | smoke-single | 单文件版冒烟 |
| 4 | smoke-split | 三文件版冒烟 |
| 5 | visual | 视觉回归截图 |
| 7 | e2e | 端到端流程 |
| 8 | data-audit | 数据完整性 |
| 9 | a11y | 可访问性（对比度、触达、焦点环） |
| 12 | perf-guard | 性能守卫（体积、加载耗时） |
| 13 | crossplat | 跨端兼容（老内核语法、引擎层纯净度） |
| 14 | ui-spec | UI 规范（尺寸阶梯、间距、动效） |
| 15 | color | 色彩一致性 |
| 16 | full-sweep | 全量扫描：每条线路每天每个可点元素 |
| 17 | cross-check | 交叉体检：12 类横向比对 |
| 18 | ui-detail | 界面细节 10 类（对齐、间距、遮挡、时间越界） |
| 19 | rule-regression | 规则回归：26 条历史约定是否仍生效 |
| 20 | stress | **十轮压力测试**（见下） |
| 21 | data-density | **功能数据密度**：15 项功能的真实覆盖率 |

### 第 20 项：十轮压力测试

查的不是「有没有违反规则」，而是「真用起来会不会出事」：

加天极限 · 疯狂切换 · 长会话内存 · 首屏性能 · 渲染性能 · 滚动流畅度 · 极端数据 · 错误恢复 · 并发操作 · 规模预测

当前实测：首屏可交互 366ms · 切天 1.8ms · 200 次操作内存增长 0MB · 滚动掉帧 4%

### 第 21 项：功能数据密度

**这一项是为了防「有壳没料」**——UI 做好了但数据只有几处，测试全绿也查不出来，因为它不报错，只是没内容。

判据：≥80% 健康 / 40–80% 偏薄 / **<40% 空壳，要么补料要么撤掉 UI**

---

## 新增一条线路

1. 读 `docs/sop.md` 的「新增线路必查」和 `docs/content-audit.md` 的 20 条清单
2. 在 `src/index.html` 的数据层写 `XX_DAYS` / `XX_LODGES`
3. 用 `Object.assign(ROUTES, {...})` 挂上，`normRoute()` 包一层
4. 跑验收：`node tools/route-factory.js verify <id>`
5. 首页加卡片（含中英文案）
6. 补 `tools/extra-pool.js` 的备选景点（供 +1 天用）
7. `npm test` 全绿才能发

**验收器会拦住这些高频错误**：必备字段缺失、天签不连号、住宿链项数不符、预算低于实测、地图段自己到自己、统计区与天数格重复。

---

## 发布

```bash
# 1. 先拉线上代码，保留外部 SEO 工作流注入的内容
git clone --depth 1 https://github.com/ourword-ai/zouni.git /tmp/live
node tools/preserve-external.js src/index.html /tmp/live/index.html

# 2. 全套测试
npm test

# 3. 记发布日志（强制记录踩了什么坑）
node tools/release-log.js --ver vNN --what "改了什么" --bug "踩了什么坑" --guard "坑是否升级为守卫"

# 4. 推 GitHub Pages
```

**体积阈值 650KB**。超了按这个顺序降级：只存首页卡片用的封面 → 降尺寸质量 → 最后才考虑换地图缩略图（地图只有实景的 19% 体积）。

按 11.5KB 每条算，单文件版天花板约 100 条（1.1MB / 4G 2.3 秒），再多要走分层交付。

---

## 几条硬规矩

摘自 `docs/sop.md`，违反会被测试拦下：

- **引擎层零浏览器 API** —— 不能出现 `document` / `window` / `localStorage`
- **禁用高版本语法** —— 无 `?.` / `??` / `flatMap` / `.at()`（微信 X5 老内核）
- **artifact 里不用 localStorage** —— 用内存状态
- **能自动算的不留手写字段** —— 手写字段每多一个就多一个会写错的地方
- **做功能前先查数据密度** —— 有 UI 没数据比没这个功能更糟
- **原生控件 API 必须查兼容性** —— `showPicker()` 在 iOS Safari 不支持，桌面 Chrome 测不出来

---

## 推送到 GitHub

用 `tools/ghkit.py`（双 token、限频、密钥脱敏）：

```bash
python3 tools/ghkit.py init --which push-token   # 首次：粘贴 token，不回显不进历史
python3 tools/ghkit.py create-repo zouni --desc "走你 · 旅行攻略"
python3 tools/ghkit.py push . <OWNER>/zouni
python3 tools/ghkit.py pages <OWNER>/zouni       # 开 Pages
python3 tools/ghkit.py status                    # 看配额与今日用量
```

Pages 部署的是仓库根目录，`src/index.html` 不在根上——若要用 Pages，
把 `src/index.html` 复制一份到根目录的 `index.html`（`dist/index.html` 已备好一份）。
