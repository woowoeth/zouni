#!/bin/sh
# Chrome 内核回归五组（22 项）。用法：sh tests/run_regression.sh [建站输出目录]
SITE=${1:-/home/claude/zouni-site}; cd "$(dirname "$0")"
NODE_PATH="/tmp/node_modules:$(npm root -g 2>/dev/null):${NODE_PATH}"; export NODE_PATH   # puppeteer 装在 /tmp/node_modules 或全局
python3 -m http.server 8765 --directory "$SITE" >/tmp/http.log 2>&1 &
SRV=$!; sleep 1
for t in site_users15 site_users22 site_users23 site_users13 site_users3; do timeout 120 node $t.js http://localhost:8765 > /tmp/n_$t.json 2>&1; done
kill $SRV 2>/dev/null
python3 - <<'PY'
import json
tot=ok=0
for t in ('site_users15','site_users22','site_users23','site_users13','site_users3'):
    s=open('/tmp/n_%s.json'%t,encoding='utf-8',errors='replace').read()
    try: d=json.loads(s); tot+=len(d['R']); ok+=sum(1 for r in d['R'] if r['ok'])
    except Exception: print(t, '没跑完（多半是加载超时，单独重跑这一组）：', s[:120])
print('Chrome 内核回归', ok, '/', tot)
PY
