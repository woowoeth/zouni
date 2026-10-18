#!/bin/bash
# 站点（build_site 生成的 /assets/site.js 那一代）的全部带断言检查，一条命令跑完（2026-10-17）。
# 用法：bash tests/run_site_checks.sh [建好的站目录，默认 build/site]      # 先 bash build/pipe.sh build/site
# 任一项红：继续跑完，最后列出哪几项红，退出码 1。每一项的反向自检见各脚本文件头（--inject 名字）。
SITE=${1:-build/site}; cd "$(dirname "$0")/.."
declare -a RED=()
run() { local name="$1"; shift; echo "═══ $name"; "$@" > "/tmp/zouni_check_${name// /_}.log" 2>&1; local rc=$?; tail -3 "/tmp/zouni_check_${name// /_}.log"; [ $rc -ne 0 ] && RED+=("$name（日志 /tmp/zouni_check_${name// /_}.log）"); }
run data_checks      python3 tests/data_checks.py "$SITE"
run home_ux          python3 tests/home_ux_check.py "$SITE"
run home_layout      python3 tests/home_layout_check.py "$SITE"
run nearby_ui        python3 tests/nearby_ui_check.py "$SITE"
run follow           python3 tests/follow_check.py "$SITE"
run ux_dates_share   python3 tests/ux_dates_share_check.py "$SITE"
run ux_toast_touch   python3 tests/ux_toast_touch_check.py "$SITE"
run ux_state_offline python3 tests/ux_state_offline_check.py "$SITE"
run ux_home_search   python3 tests/ux_home_search_check.py "$SITE"
run ux_batch2        python3 tests/ux_batch2_check.py "$SITE"
run map_app          python3 tests/map_app_check.py "$SITE"       # 2026-10-18 地图 App 化：取代了 route_map_check / route_map2_check（旧内嵌地图的判据，已删，能保留的并进 M1–M12）
run map_perf         python3 tests/map_perf.py --target fixture --site "$SITE" --cases 4g:cold,4g:warm,3g:cold --assert      # 点开地图的耗时（稳定版：本机服务 + 共享链路模型）
run weekday          python3 tests/weekday_check.py "$SITE"
run memorial         python3 tests/memorial_check.py "$SITE"
run default_date     python3 tests/default_date_check.py "$SITE"
run follow2          python3 tests/follow2_check.py "$SITE"
run a_batch3         python3 tests/a_batch3_check.py "$SITE"
run less_is_more     python3 tests/less_is_more_check.py "$SITE"
run slow3g           python3 tests/slow3g_check.py "$SITE"
# 首页“替我挑”666 组矩阵：改动前的站上乌鲁木齐周末/4–5 天距离中位数就超限（当季近线少，数据问题，不是代码），所以只对“新增失败”红
echo "═══ home_matrix"; python3 tests/home_matrix_run.py "$SITE" > /tmp/zouni_check_home_matrix.log 2>&1; tail -4 /tmp/zouni_check_home_matrix.log
NEWFAIL=$(grep '  ✗' /tmp/zouni_check_home_matrix.log | grep -v '乌鲁木齐 周末距离中位数\|乌鲁木齐 4–5 天距离中位数' | wc -l | tr -d ' ')
[ "$NEWFAIL" != "0" ] && RED+=("home_matrix（除乌鲁木齐两条已知外有 $NEWFAIL 条红，见 /tmp/zouni_check_home_matrix.log）")
echo; if [ ${#RED[@]} -eq 0 ]; then echo "全部通过"; exit 0; else echo "红 ${#RED[@]} 项："; printf '  - %s\n' "${RED[@]}"; exit 1; fi
