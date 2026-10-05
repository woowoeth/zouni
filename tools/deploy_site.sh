#!/bin/sh
# 把 /home/claude/zouni-site 整站发布到 woowoeth/zouni（GitHub Pages：main 分支根目录，域名 zouni.app）
# 令牌只从容器临时文件读（/tmp/.zt_read 抓取、/tmp/.zt_push 推送，权限 600），不写进项目、不打印
set -e
SITE=/home/claude/zouni-site; W=/tmp/zdeploy
[ -s /tmp/.zt_read ] && [ -s /tmp/.zt_push ] || { echo "缺少令牌文件"; exit 1; }
if [ ! -d "$W/repo/.git" ]; then
  rm -rf "$W"; mkdir -p "$W"
  AR=$(printf 'x-access-token:%s' "$(cat /tmp/.zt_read)" | base64 -w0)
  git -c http.extraheader="Authorization: Basic $AR" clone -q --depth 1 https://github.com/woowoeth/zouni.git "$W/repo"
fi
cd "$W/repo"
find . -mindepth 1 -maxdepth 1 ! -name .git ! -name .github -exec rm -rf {} +
cp -R "$SITE"/. .
git add -A
git -c user.name="zouni-bot" -c user.email="bot@zouni.app" commit -q -m "${1:-更新网站}" || { echo "没有变化"; exit 0; }
AP=$(printf 'x-access-token:%s' "$(cat /tmp/.zt_push)" | base64 -w0)
git -c http.extraheader="Authorization: Basic $AP" push -q origin main
echo "已推送：$(git rev-parse --short HEAD)"
# 推完盯一下 Pages 构建：失败或卡住就自动请求重建（2026-10-05 出现过一次卡在 building、最后报错）
python3 - <<'PY'
import json, time, urllib.request, subprocess
def api(path, tok, method='GET'):
    r = urllib.request.Request('https://api.github.com' + path, data=b'' if method == 'POST' else None, method=method,
                               headers={'Authorization': 'Bearer ' + open(tok).read().strip(), 'Accept': 'application/vnd.github+json', 'User-Agent': 'zouni-deploy'})
    with urllib.request.urlopen(r, timeout=30) as x: return json.loads(x.read() or b'{}')
head = subprocess.run(['git', '-C', '/tmp/zdeploy/repo', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
for attempt in range(2):
    for i in range(16):
        time.sleep(15)
        b = api('/repos/woowoeth/zouni/pages/builds/latest', '/tmp/.zt_read')
        if b.get('commit', '').startswith(head[:7]) and b.get('status') in ('built', 'errored'): break
    if b.get('status') == 'built': print('Pages 构建完成', head[:7]); break
    print('Pages 构建', b.get('status'), '→ 请求重建'); api('/repos/woowoeth/zouni/pages/builds', '/tmp/.zt_push', 'POST')
PY
