#!/bin/bash
# 入库工具幂等自检：连跑两次，data/ 和 tools/build_site.py 的指纹必须一致。
# 第一次可能带来 SIGHT/DEEP 新增，所以比的是“第一次之后”和“第二次之后”。别的 agent 正往 build/history/ 写文件时，两次之间源文件变了就不是工具的错：脚本会发现并重试（最多 3 次）。
# 用法：bash tools/ingest_idempotent_check.sh      退出码 0 = 幂等
cd "$(dirname "$0")/.."
fl() { find data tools/build_site.py -type f ! -name '.DS_Store' -print0 | sort -z | xargs -0 md5 | sort; }
fp() { fl | md5; }
src() { ls build/history/*.json 2>/dev/null | grep -v '/chk_\|/research_' | xargs md5 -q | md5; }
for try in 1 2 3; do
  S0=$(src); python3 tools/ingest_history.py > /tmp/ingest_a.log 2>&1; S1=$(src); fl > /tmp/idem_a.txt; A=$(md5 -q /tmp/idem_a.txt)
  python3 tools/ingest_history.py > /tmp/ingest_b.log 2>&1; S2=$(src); fl > /tmp/idem_b.txt; B=$(md5 -q /tmp/idem_b.txt)
  echo "第 $try 轮：第一次后 $A · 第二次后 $B"
  if [ "$S0" != "$S1" ] || [ "$S1" != "$S2" ]; then echo "  两次之间 build/history 变了（别的 agent 在写），重试"; continue; fi
  [ "$A" = "$B" ] && { echo "幂等：连跑两次 data/ 无差异"; exit 0; } || { echo "不幂等！差异的文件："; diff /tmp/idem_a.txt /tmp/idem_b.txt; exit 1; }
done
echo "源文件一直在变，没法判定"; exit 3
