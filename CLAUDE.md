# 给 Claude Code 的项目说明

## 这是什么

「走你」是一个旅行攻略产品：用户选目的地和天数，产出逐日逐站的可执行行程（含车程、开放时间、住宿、费用）。
单文件 HTML，无构建步骤，无后端。

## 动手之前必读

1. **`docs/sop.md`** —— 项目 SOP。什么该做、什么明确不做、42 次发布踩过的坑
2. **`docs/ui-spec.md`** —— UI 方案。按钮三档尺寸、间距节奏、配置区三态
3. **`docs/product-judgment.md`** —— 产品判断。核心价值是"排得开、算得准、有变能改"

## 改完必须跑

```bash
npm test      # 21 项，约 4 分钟，任一失败就中断
```

不要跳过。这套测试拦下过：老内核语法、住宿链断裂、统计区字段重复、
弹层被 tab 遮挡、时间越界（25:01）、功能空壳、内存泄漏。

## 几个容易踩的坑

- **数据层与引擎层严格分离**：引擎层不能出现 `document`/`window`/`localStorage`，
  否则第 1 项和第 13 项会失败
- **禁用高版本语法**：`?.` `??` `flatMap` `.at()` 都会被第 13 项拦下（微信 X5 老内核）
- **改布局方向要清旧边距**：竖排改横排后，原来的 `margin-bottom` 会变成看不出来源的偏移
- **CSS 三态特异性要一致**：配置区有空态/收起/展开三种，写 `!important` 容易把其中一态压死
- **新增线路先跑 `node tools/route-factory.js verify <id>`**，它会拦住 16 类错误

## 发布前

```bash
# 线上有另一个 SEO 工作流在改同一个 index.html，必须先保留它注入的内容
node tools/preserve-external.js src/index.html <线上的 index.html>
```

## 当前状态

56 条线路 · 36 族 · 646KB · 21 项测试全绿 · 省份覆盖 23/34

下一步按 `docs/province-plan.md` 推进内容，按 `docs/product-judgment.md` 补执行断点。
