#!/usr/bin/env python3
"""ghkit — 双 token GitHub 工具（抓取/推送分离，严格限频，密钥不外流）"""
from __future__ import annotations

import argparse, base64, json, os, random, re, stat, subprocess, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

HOME = os.path.expanduser("~/.ghkit")
STATE = os.path.join(HOME, "state.json")
FETCH_FILE = os.path.join(HOME, "fetch.token")
PUSH_FILE = os.path.join(HOME, "push.token")
API = "https://api.github.com"

FETCH_MIN_INTERVAL = 2.5
FETCH_DAILY_MAX = 400
SEARCH_MIN_INTERVAL = 6.0
SEARCH_DAILY_MAX = 120
PUSH_MIN_INTERVAL = 20.0
PUSH_DAILY_MAX = 40
BACKOFF_BASE = 20
BACKOFF_MAX_TRIES = 4

_SECRETS: list = []

def _remember(secret):
    if secret and secret not in _SECRETS: _SECRETS.append(secret)
    return secret

def redact(text) -> str:
    s = str(text)
    for sec in _SECRETS:
        if sec: s = s.replace(sec, "***TOKEN***")
    s = re.sub(r"gh[pousr]_[A-Za-z0-9]{16,}", "***TOKEN***", s)
    s = re.sub(r"github_pat_[A-Za-z0-9_]{20,}", "***TOKEN***", s)
    s = re.sub(r"(x-access-token|oauth2):[^@\s]+@", r"\1:***TOKEN***@", s)
    return s

def say(*parts): print(redact(" ".join(str(p) for p in parts)))

def die(msg, code=1):
    print(redact("✗ " + str(msg)), file=sys.stderr); sys.exit(code)

def _read_token(path, env, label):
    tok = os.environ.get(env, "").strip()
    if not tok and os.path.exists(path):
        with open(path) as f: tok = f.read().strip()
    if not tok: die(f"缺少{label}。先跑 `ghkit.py init --which {label}` 或设环境变量 {env}")
    return _remember(tok)

def fetch_token(): return _read_token(FETCH_FILE, "GH_FETCH_TOKEN", "fetch-token")
def push_token(): return _read_token(PUSH_FILE, "GH_PUSH_TOKEN", "push-token")

def cmd_init(a):
    os.makedirs(HOME, mode=0o700, exist_ok=True)
    import getpass
    target = FETCH_FILE if a.which == "fetch-token" else PUSH_FILE
    tok = getpass.getpass(f"粘贴 {a.which}（输入不回显）: ").strip()
    if not tok: die("空值，未写入")
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: f.write(tok)
    os.chmod(target, stat.S_IRUSR | stat.S_IWUSR)
    say(f"✓ 已写入 {target}（权限 600，内容不回显）")

def _today(): return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _load_state():
    try:
        with open(STATE) as f: st = json.load(f)
    except Exception: st = {}
    if st.get("day") != _today():
        st = {"day": _today(), "fetch": 0, "search": 0, "push": 0,
              "last_fetch": 0, "last_search": 0, "last_push": 0}
    return st

def _save_state(st):
    os.makedirs(HOME, mode=0o700, exist_ok=True)
    tmp = STATE + ".tmp"
    with open(tmp, "w") as f: json.dump(st, f)
    os.replace(tmp, STATE)

def _gate(kind):
    limits = {"fetch": (FETCH_DAILY_MAX, FETCH_MIN_INTERVAL),
              "search": (SEARCH_DAILY_MAX, SEARCH_MIN_INTERVAL),
              "push": (PUSH_DAILY_MAX, PUSH_MIN_INTERVAL)}
    cap, interval = limits[kind]
    st = _load_state()
    if st[kind] >= cap:
        die(f"今日 {kind} 已达上限 {cap} 次（UTC 日切自动重置）。这是防封保护，不建议绕过。")
    wait = interval - (time.time() - st.get("last_" + kind, 0))
    if wait > 0: time.sleep(wait)
    st[kind] += 1
    st["last_" + kind] = time.time()
    _save_state(st)

def _request(url, token, method="GET", body=None, accept="application/vnd.github+json"):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Accept": accept,
        "User-Agent": "ghkit", "X-GitHub-Api-Version": "2022-11-28"})
    for attempt in range(BACKOFF_MAX_TRIES):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                raw = r.read()
                return r.status, (json.loads(raw) if raw else {})
        except urllib.error.HTTPError as e:
            raw = e.read()
            if e.code in (403, 429) and attempt < BACKOFF_MAX_TRIES - 1:
                delay = BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 5)
                reset = e.headers.get("x-ratelimit-reset")
                say(f"  ⏳ {e.code} 限流，退避 {delay:.0f}s"
                    + (f"（配额重置 {datetime.fromtimestamp(int(reset), timezone.utc):%H:%M}Z）" if reset else ""))
                time.sleep(delay); continue
            try: msg = json.loads(raw).get("message", "")
            except Exception: msg = raw[:160].decode("utf-8", "ignore")
            return e.code, {"message": msg}
        except Exception as e:
            if attempt < BACKOFF_MAX_TRIES - 1:
                time.sleep(BACKOFF_BASE * (2 ** attempt)); continue
            return "ERR", {"message": redact(e)}
    return "ERR", {"message": "重试耗尽"}

def api_fetch(path, search=False):
    _gate("search" if search else "fetch")
    return _request(API + path, fetch_token())

def api_push(path, method="GET", body=None):
    if method != "GET": _gate("push")
    return _request(API + path, push_token(), method, body)

def cmd_status(a):
    st = _load_state()
    say(f"今日用量（UTC {st['day']}）")
    for k, cap in (("fetch", FETCH_DAILY_MAX), ("search", SEARCH_DAILY_MAX), ("push", PUSH_DAILY_MAX)):
        say(f"  {k:7s} {st.get(k,0):>4}/{cap}")
    for label, tok in (("抓取", fetch_token()), ("推送", push_token())):
        code, d = _request(API + "/rate_limit", tok)
        if code == 200:
            c, s = d["resources"]["core"], d["resources"]["search"]
            who = _request(API + "/user", tok)[1].get("login", "?")
            say(f"  {label} token（{who}）: core {c['remaining']}/{c['limit']}  search {s['remaining']}/{s['limit']}")
        else:
            say(f"  {label} token: 异常 {code} {d.get('message','')}")

def cmd_search(a):
    q = urllib.parse.quote(a.query)
    code, d = api_fetch(f"/search/repositories?q={q}&per_page={a.n}", search=True)
    if code != 200: die(f"搜索失败 {code}: {d.get('message','')}")
    for r in d.get("items", []):
        say(f'★{r["stargazers_count"]:<6} {r["full_name"]:44s} {(r.get("description") or "")[:80]}')
    say(f"（共 {d.get('total_count',0)} 条，取前 {a.n}）")

def cmd_get(a):
    code, d = api_fetch(a.path)
    say(f"HTTP {code}")
    say(json.dumps(d, ensure_ascii=False, indent=1)[:4000])

def cmd_create_repo(a):
    code, d = api_push("/user/repos", "POST", {
        "name": a.name, "private": bool(a.private), "auto_init": False,
        "has_wiki": False, "has_projects": False, "description": a.desc or ""})
    if code in (200, 201): say(f"✓ 已建仓库 {d.get('full_name')}")
    elif code == 422: say(f"仓库已存在或名称无效：{d.get('message','')}")
    else: die(f"建仓库失败 {code}: {d.get('message','')}")

def cmd_push(a):
    repo_dir = os.path.abspath(a.dir)
    if not os.path.isdir(os.path.join(repo_dir, ".git")): die(f"不是 git 仓库：{repo_dir}")
    _gate("push")
    tok = push_token()
    url = f"https://github.com/{a.target}.git"
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_ASKPASS="", GH_TOK=tok)
    helper = '!f(){ echo username=x-access-token; echo password=$GH_TOK; }; f'
    cmd = ["git", "-c", f"credential.helper={helper}", "push", url, f"{a.branch}:{a.branch}"]
    if a.force: cmd.append("--force")
    p = subprocess.run(cmd, cwd=repo_dir, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True)
    out = redact(p.stdout)
    if p.returncode == 0:
        say(f"✓ 已推送 {a.branch} → {a.target}")
        if out.strip(): say(out.strip()[:600])
    else: die(f"推送失败：\n{out.strip()[:800]}")

def cmd_pages(a):
    code, d = api_push(f"/repos/{a.target}/pages", "POST",
                       {"source": {"branch": a.branch, "path": "/"}})
    if code in (200, 201): say(f"✓ 已开启 Pages：{d.get('html_url')}")
    elif code == 409: say("Pages 已经开着")
    else: say(f"开启 Pages 返回 {code}: {d.get('message','')}")

def cmd_secret(a):
    code, key = api_fetch(f"/repos/{a.target}/actions/secrets/public-key")
    if code != 200: die(f"取公钥失败 {code}: {key.get('message','')}")
    try: from nacl import encoding, public
    except ImportError: die("需要 pynacl 来加密：pip install pynacl --break-system-packages")
    pk = public.PublicKey(key["key"].encode(), encoding.Base64Encoder())
    sealed = public.SealedBox(pk).encrypt(a.value.encode())
    code, d = api_push(f"/repos/{a.target}/actions/secrets/{a.name}", "PUT",
                       {"encrypted_value": base64.b64encode(sealed).decode(), "key_id": key["key_id"]})
    if code in (201, 204): say(f"✓ Secret {a.name} 已写入 {a.target}（值已加密，未记录明文）")
    else: die(f"写 Secret 失败 {code}: {d.get('message','')}")

def main():
    ap = argparse.ArgumentParser(description="双 token GitHub 工具：抓取/推送分离 · 严格限频 · 密钥脱敏")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init"); p.add_argument("--which", choices=["fetch-token","push-token"], required=True); p.set_defaults(func=cmd_init)
    p = sub.add_parser("status"); p.set_defaults(func=cmd_status)
    p = sub.add_parser("search"); p.add_argument("query"); p.add_argument("-n", type=int, default=10); p.set_defaults(func=cmd_search)
    p = sub.add_parser("get"); p.add_argument("path"); p.set_defaults(func=cmd_get)
    p = sub.add_parser("create-repo"); p.add_argument("name"); p.add_argument("--private", action="store_true"); p.add_argument("--desc", default=""); p.set_defaults(func=cmd_create_repo)
    p = sub.add_parser("push"); p.add_argument("dir"); p.add_argument("target"); p.add_argument("--branch", default="main"); p.add_argument("--force", action="store_true"); p.set_defaults(func=cmd_push)
    p = sub.add_parser("pages"); p.add_argument("target"); p.add_argument("--branch", default="main"); p.set_defaults(func=cmd_pages)
    p = sub.add_parser("secret"); p.add_argument("target"); p.add_argument("name"); p.add_argument("value"); p.set_defaults(func=cmd_secret)
    a = ap.parse_args()
    try: a.func(a)
    except KeyboardInterrupt: sys.exit(130)
    except BrokenPipeError:
        try: sys.stdout.close()
        except Exception: pass
    except SystemExit: raise
    except Exception as e: die(f"未处理异常：{type(e).__name__}: {redact(e)}")

if __name__ == "__main__": main()
