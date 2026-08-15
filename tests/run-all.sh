#!/bin/bash
# 走你 · 发布前自动化五连测（需 node ≥18 + npm i jsdom + python3）
set -e; cd "$(dirname "$0")"
# jsdom 依赖：优先复用 /tmp，缺失则装到本目录
export NODE_PATH="/tmp/node_modules:./node_modules${NODE_PATH:+:$NODE_PATH}"
node -e "require('jsdom')" 2>/dev/null || npm i jsdom --prefix . --no-fund --no-audit >/dev/null
echo "═ 1/5 语法检查"; node -e "const m=require('fs').readFileSync('../src/index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];require('fs').writeFileSync('/tmp/_full.js',m)"; node --check /tmp/_full.js && node --check ../src/zouni-data.js && node --check ../src/zouni-engine.js && echo OK
echo "═ 2/5 引擎仿真（全部路线）"; node 0-slice.js && node 1-engine-sim.js
echo "═ 3/5 静态终检"; python3 2-static.py
echo "═ 4/5 运行时冒烟 · 单文件"; node 3-smoke-single.js
echo "═ 5/5 运行时冒烟 · 三文件"; node 4-smoke-split.js
echo "═ 6/6 视觉回归 · 真渲染"; node 5-visual.js
echo "═ 7/7 E2E · 真浏览器交互链"; node 7-e2e.js
echo "═ 8/8 数据体检 · 地图/价格/覆盖度"; node 8-data-audit.js
echo "═ 9/9 可访问性 · 对比度/语义/焦点"; node 9-a11y.js
echo "═ 10/10 路线工厂 · 15 项结构与地理验收"; node ../tools/route-factory.js verify all
echo "═ 11/11 编排层可推导性 · 编译器往返等价"; node ../tools/route-compiler.js roundtrip all
echo "═ 12/12 性能守卫 · 体积/响应/健壮性"; node 12-perf-guard.js
echo "═ 13/13 跨端就绪 · 引擎零浏览器依赖"; node 13-crossplat.js || exit 1
echo "═ 14/14 UI 规范 · 六域判据"; node 14-ui-spec.js || exit 1
echo "═ 15/15 色彩系统 · APCA 与色相一致性"; node 15-color.js || exit 1
echo "═ 16/16 全量扫描 · 每张卡每一天每个按钮"; node 16-full-sweep.js || exit 1
echo "═ 17/17 交叉一致性 · 横向比对"; node 17-cross-check.js || exit 1
echo "═ 18/18 界面细节 · 六类逐条排查"; node 18-ui-detail.js || exit 1
echo "═ 19/19 规则回归 · 26 条约定仍生效"; node 19-rule-regression.js | tail -3
echo "═ 20/20 压力测试 · 十轮"; node 20-stress.js | tail -13
echo "═ 21/21 数据密度 · 每个功能都有料"; node 21-data-density.js | tail -20
echo "═══ 二十一连测全部通过，可发布 ═══"
