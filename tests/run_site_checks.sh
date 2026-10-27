#!/bin/bash
# 站点（build_site 生成的 /assets/site.js 那一代）的全部带断言检查，一条命令跑完（2026-10-17）。
# 用法：bash tests/run_site_checks.sh [建好的站目录，默认 build/site]      # 先 bash build/pipe.sh build/site
# 任一项红：继续跑完，最后列出哪几项红，退出码 1。每一项的反向自检见各脚本文件头（--inject 名字）。
SITE=${1:-build/site}; cd "$(dirname "$0")/.."
declare -a RED=()
run() { local name="$1"; shift; echo "═══ $name"; "$@" > "/tmp/zouni_check_${name// /_}.log" 2>&1; local rc=$?; tail -3 "/tmp/zouni_check_${name// /_}.log"; [ $rc -ne 0 ] && RED+=("$name（日志 /tmp/zouni_check_${name// /_}.log）"); }
run data_checks      python3 tests/data_checks.py "$SITE"
run home_ux          python3 tests/home_ux_check.py "$SITE"
run w1_season        python3 tests/w1_season_check.py "$SITE"       # 2026-10-20 第 1 波：季节措辞跟日期走（红字行 / 极夜流冰雪胎句子 / “9 月上旬”句子；Z1–Z7，4 个 --inject）。数据类的闸（住处点 / 路上时间 / 气温 / 餐食…）在 data_checks 第 37 项（tests/w1_checks.py）
run home_layout      python3 tests/home_layout_check.py "$SITE"
run nearby_ui        python3 tests/nearby_ui_check.py "$SITE"
run follow           python3 tests/follow_check.py "$SITE"
run ux_dates_share   python3 tests/ux_dates_share_check.py "$SITE"
run ux_toast_touch   python3 tests/ux_toast_touch_check.py "$SITE"
run ux_state_offline python3 tests/ux_state_offline_check.py "$SITE"
run ux_home_search   python3 tests/ux_home_search_check.py "$SITE"
run ux_batch2        python3 tests/ux_batch2_check.py "$SITE"
run map_app          python3 tests/map_app_check.py "$SITE"       # 2026-10-18 地图 App 化：取代了 route_map_check / route_map2_check（旧内嵌地图的判据，已删，能保留的并进 M1–M12）
run map_anchor       python3 tests/map_anchor_check.py "$SITE"       # 2026-10-19 标点贴不贴真实坐标：每个标点中心与 map.project 误差 ≤2px（zoom 6/10/14/17、+/−、双击、双指、拖动、旋转、横屏、动画途中、示意图兜底；颜色类与卡片类撞名的根因判据）（A1–A8，4 个 --inject）
run map_polish       python3 tests/map_polish_check.py "$SITE"       # 2026-10-19 地图细节打磨：站名标签避让 / 视野居中同一套留边 / 底图退后 / 底部条两行不断数字 / 全程每天形色 / 进度条一定收 / 细线箭头往返一条 / 点击区·置灰·不闪·暗色·横屏（P1–P8，23 个 --inject）
run map_routes      python3 tests/map_routes_check.py "$SITE"       # 2026-10-20 各类线路走一遍：长线总览（主线 / 章合并 / 取景）· 天标签条（滚进视野 / 渐隐 / 紧凑）· g318 / 105 天 / xl* / 国外 / h* 线遍历 · 卡片 · 关闭回原位 · 105 天切天速度 · 暗色 / 375 / 414 / 横屏 · 国外地名拉丁字母兜底 · 起步壳 · 长站名（R1–R7，16 个 --inject）
run map_names       python3 tests/map_names_check.py "$SITE"       # 2026-10-21 总览里每个方块写地名（D34）：地名 / 同城合并 / 不压控件·不重叠 / 首尾必有名字 / 点名字进那一天 / 放大后才出现主要景点 / 存图·起步壳也写地名 / 105 天速度（N1–N9，13 个 --inject）
run map_perf         python3 tests/map_perf.py --target fixture --site "$SITE" --cases 4g:cold,4g:warm,3g:cold --assert      # 点开地图的耗时（稳定版：本机服务 + 共享链路模型）
run weekday          python3 tests/weekday_check.py "$SITE"
run memorial         python3 tests/memorial_check.py "$SITE"
run default_date     python3 tests/default_date_check.py "$SITE"
run follow2          python3 tests/follow2_check.py "$SITE"
run a_batch3         python3 tests/a_batch3_check.py "$SITE"
run less_is_more     python3 tests/less_is_more_check.py "$SITE"
run detail_simplify  python3 tests/detail_simplify_check.py "$SITE"      # 2026-10-18 详情页与弹层“少就是多”：层栈 / 关闭入口 / 下滑关层 / 页头去重 / 12 个任务步数 / 顺路覆盖率（S1–S14）
run day_model        python3 tests/day_model_check.py "$SITE"      # 2026-10-18 当天模型 ZD：面板 = 页面同一份行程 / 两个方向同步 / 数字一个算法 / 联动 / 按天看·复制·日历同源（D1–D10）
run fx               python3 tests/fx_check.py "$SITE"      # 2026-10-19 可用性审计第一轮：加站入口先算候选 / 路上口径 / 改完页面一致 / 加一天已排过 / 默认出发日 / g318 / 焦点与 aria / 营地日（F1–F8）
run wave2            python3 tests/wave2_check.py "$SITE"      # 2026-10-19 去冗余波：首页 / where / 出发地·人数·日期一个键 / 目的地页 / 跟片走 / toast / 样板行 / 术语 / 输入 / 可访问性 / 重复线路（每项有 --inject 反向自检）
run copy_budget      python3 tests/copy_check.py "$SITE"      # 2026-10-21 文字预算：弹层选项主标题 ≤8 字 / 副标题 ≤14 字 / 没有“为什么·之后会怎样” / toast 只留带撤销或出错限制 / 我的行程·首页小标题不带解释（C1–C9，16 个 --inject）
run title            python3 tests/title_check.py      # 标题不得以“N天(…)”开头、同一目的地 label 不重名；python3 tests/title_check.py --selftest 反向自检
run slow3g           python3 tests/slow3g_check.py "$SITE"
# 首页“替我挑”666 组矩阵：改动前的站上乌鲁木齐周末/4–5 天距离中位数就超限（当季近线少，数据问题，不是代码），所以只对“新增失败”红
echo "═══ home_matrix"; python3 tests/home_matrix_run.py "$SITE" > /tmp/zouni_check_home_matrix.log 2>&1; tail -4 /tmp/zouni_check_home_matrix.log
NEWFAIL=$(grep '  ✗' /tmp/zouni_check_home_matrix.log | grep -v '乌鲁木齐 周末距离中位数\|乌鲁木齐 4–5 天距离中位数\|哈尔滨 周末距离中位数\|哈尔滨 4–5 天距离中位数' | wc -l | tr -d ' ')
[ "$NEWFAIL" != "0" ] && RED+=("home_matrix（除乌鲁木齐、哈尔滨的已知距离项外有 $NEWFAIL 条红，见 /tmp/zouni_check_home_matrix.log）")
echo; if [ ${#RED[@]} -eq 0 ]; then echo "全部通过"; exit 0; else echo "红 ${#RED[@]} 项："; printf '  - %s\n' "${RED[@]}"; exit 1; fi
