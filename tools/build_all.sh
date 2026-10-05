#!/bin/sh
# 一条命令重建全部数据并体检；任何一步失败就停（不发布）
# 用法：sh tools/build_all.sh <画布 project 目录>
set -e
cd "$(dirname "$0")/.."
OUT=${1:-build}
mkdir -p build
[ -n "$SKIP_EXPORT" ] || timeout 400 node tools/export_v2.js /mnt/user-data/outputs/zouni-xj-10d.html data/routes >/dev/null   # 1 引擎 → 线路骨架
python3 tools/apply_cities.py >/dev/null                                                               # 2 城市表 → 吃住玩
python3 tools/build_routes_js.py build/routes.js | head -1                                             # 3 引擎线路 → 页面数据
python3 tools/compile_itineraries.py build/routes.js                                                   # 4 声明式行程 → 页面数据
python3 tools/build_quality.py | head -1                                                                # 5a 优质景点覆盖率
python3 tools/build_catalog.py build/catalog.js                                                        # 5 目的地 + 线路目录
python3 tools/validate_catalog.py build/routes.js > build/validate.txt; head -1 build/validate.txt   # 6 目录体检（有错误就退出）
cp build/routes.js build/catalog.js "$OUT"/
python3 tools/tag_check.py "$OUT"                                                                      # 7 画板标签配对
echo 完成
