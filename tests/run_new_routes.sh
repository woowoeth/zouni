#!/bin/sh
# 新线逐条打开检查。用法：sh tests/run_new_routes.sh id1 id2 …   结果在 /tmp/an.txt
SITE=${SITE:-/home/claude/zouni-site}; export SITE; cd "$(dirname "$0")"
NODE_PATH="/tmp/node_modules:$(npm root -g 2>/dev/null):${NODE_PATH}"; export NODE_PATH   # puppeteer 装在 /tmp/node_modules 或全局
python3 -m http.server 8765 --directory "$SITE" >/tmp/http.log 2>&1 &
SRV=$!; sleep 1
timeout 120 node chrome_new_routes_check.js "$@" > /tmp/an.txt 2>&1
kill $SRV 2>/dev/null
cat /tmp/an.txt
