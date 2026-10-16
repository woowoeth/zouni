#!/usr/bin/env python3
"""行程页“调整 / 去掉一天 / 加一天 / 下雨换室内 / 今天视图 / 分享 / 日历导出”的基线快照与比对。

为什么有这个脚本：`replan()`（site.js，按差值平移时间）是全站时间表的核心，改它之前先把现有 webkit_*.py
的输出存下来，改完逐项比。这台机器没有 WebKit，用 playwright chromium 跑，**不改仓库里原脚本**：
运行时用 monkeypatch 把 `p.webkit` 指到 chromium，并给每个 context 注入固定的“现在”（2026-10-16 14:20 +08:00）
和固定的天气接口响应，这样两次运行的输出才可比。

用法：
  python3 tests/nearby_baseline.py run <站点目录> <输出目录> [--only a,b]     # 起本地服务、依次跑，输出存成 <名字>.out
  python3 tests/nearby_baseline.py compare <基线目录> <新目录>                  # 逐文件比，有差异退出码 1
  python3 tests/nearby_baseline.py run <站> <输出> --inject-diff                # 自检：故意让一个脚本的输出变，compare 必须红

注意：脚本里写死 localhost:8765，所以服务固定起在 8765；端口被占就直接报错，不换端口。
"""
import os, sys, subprocess, time, json, socket, difflib, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = [
    'webkit_add_after', 'webkit_remove_day', 'webkit_remove_day_stays', 'webkit_stay_line',
    'webkit_addday_duration_here', 'webkit_today_todo_pick_fill', 'webkit_go_faq_todo_ics',
    'webkit_adjust_share_weather', 'webkit_start_time', 'webkit_late_replan',
    'webkit_rain_monday_allstart', 'webkit_map_addday', 'webkit_legs_tickets',
    'webkit_nextday', 'webkit_swipe_day',
    'nearby_dom_snapshot',          # 我自己写的：整天时间表/车程/隐藏行/导出内容的全量快照
]
PRELUDE = r'''
import sys, runpy, json, re
from playwright.sync_api import Browser, Playwright
FIX = """(()=>{const RD=Date;const fixed=new RD('2026-10-16T14:20:00+08:00').getTime();class FD extends RD{constructor(...a){if(a.length)super(...a);else super(fixed)}static now(){return fixed}};window.Date=FD})();"""
WX = json.dumps({'daily':{'time':['x'],'weathercode':[3],'temperature_2m_max':[18],'temperature_2m_min':[9],'precipitation_probability_max':[20]}})
Playwright.webkit = property(lambda self: self.chromium)
_nc = Browser.new_context
def nc(self, *a, **k):
    k.setdefault('timezone_id', 'Asia/Shanghai'); k.setdefault('locale', 'zh-CN')
    c = _nc(self, *a, **k)
    c.add_init_script(FIX)
    c.route(re.compile(r'.*(googletagmanager|google-analytics|hm\.baidu).*'), lambda r: r.abort())      # 统计脚本外网请求偶尔挂住，networkidle 就等不到了
    c.route('**/api.open-meteo.com/**', lambda r: r.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin': '*'}, body=WX))
    return c
Browser.new_context = nc
script = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(script, run_name='__main__')
'''


def port_free(p):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.bind(('127.0.0.1', p)); return True
    except OSError:
        return False
    finally:
        s.close()


def run(site, out, only, inject):
    if not port_free(8765):
        sys.exit('端口 8765 被占用：脚本里写死了这个端口，先停掉占用它的服务')
    os.makedirs(out, exist_ok=True)
    srv = subprocess.Popen([sys.executable, '-m', 'http.server', '8765', '--bind', '127.0.0.1', '--directory', site],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    bad = []
    try:
        for name in SCRIPTS:
            if only and name not in only:
                continue
            path = os.path.join(ROOT, 'tests', name + '.py')
            t0 = time.time()
            try:
                r = subprocess.run([sys.executable, '-c', PRELUDE, path, 'http://localhost:8765'], cwd=ROOT,
                                   capture_output=True, text=True, timeout=1200)
                so, se, rc = r.stdout, r.stderr, r.returncode
            except subprocess.TimeoutExpired as e:
                so, se, rc = (e.stdout or b'').decode() if isinstance(e.stdout, bytes) else (e.stdout or ''), 'TIMEOUT', 124
            if inject and name == 'webkit_start_time':
                so += '\nINJECTED-DIFF\n'
            open(os.path.join(out, name + '.out'), 'w', encoding='utf-8').write(so)
            open(os.path.join(out, name + '.err'), 'w', encoding='utf-8').write('rc=%s\n%s' % (rc, se[-3000:]))
            ok = rc == 0 and so.strip() != ''
            if not ok:
                bad.append(name)
            print('%-34s rc=%s  %5.1fs  %6d 字节  %s' % (name, rc, time.time() - t0, len(so), '' if ok else '<-- 没跑通'))
    finally:
        srv.terminate()
    if bad:
        print('没跑通：', bad)
        sys.exit(1)


STALE = {'webkit_adjust_share_weather', 'webkit_rain_monday_allstart', 'webkit_map_addday', 'webkit_nextday'}      # 点的按钮早被删了，改动前就超时；比“怎么超时的”


def _errsig(p):
    """rc + 异常那一行（去掉“重试 N 次”这类每次不同的数字）"""
    try:
        t = open(p, encoding='utf-8').read().splitlines()
    except Exception:
        return 'no .err'
    rc = t[0] if t else ''
    import re as _re
    ex = [_re.sub(r'\d+ms', 'Nms', l) for l in t if l.startswith(('playwright._impl._errors', 'Traceback', 'AssertionError', 'TimeoutError'))]
    wait = [l.strip() for l in t if l.strip().startswith('- waiting for locator')]
    return rc + ' | ' + (ex[-1] if ex else '') + ' | ' + (wait[0] if wait else '')


def compare(a, b, only=None):
    names = sorted(set(f for f in os.listdir(a) if f.endswith('.out')) | set(f for f in os.listdir(b) if f.endswith('.out')))
    if only: names = [f for f in names if f[:-4] in only]
    nd = 0
    for f in names:
        pa, pb = os.path.join(a, f), os.path.join(b, f)
        if not os.path.exists(pa) or not os.path.exists(pb):
            print('缺文件', f); nd += 1; continue
        ta, tb = open(pa, encoding='utf-8').read(), open(pb, encoding='utf-8').read()
        name = f[:-4]
        if name not in STALE and (not ta.strip() or not tb.strip()):       # 两边都是空也不算一致：是“没跑通”（输出空 = 什么都没比）
            nd += 1; print('没跑通（输出为空，不能当一致）', name, '| 基线 %d 字节，新 %d 字节' % (len(ta), len(tb))); continue
        ea, eb = _errsig(pa[:-4] + '.err'), _errsig(pb[:-4] + '.err')     # 本来就跑不通的旧脚本（点的按钮早被删了）：比“怎么不通”，不能因为输出都是空就当一致
        ta += '\n[err] ' + ea; tb += '\n[err] ' + eb
        if ta == tb:
            print('一致  %-34s (%d 字节)' % (f[:-4], len(ta)))
        else:
            nd += 1
            print('有差异 %s' % f[:-4])
            for l in list(difflib.unified_diff(ta.splitlines(), tb.splitlines(), 'base', 'new', lineterm='', n=0))[:40]:
                print('   ' + l[:240])
    print('比对 %d 个文件，差异 %d 个' % (len(names), nd))
    sys.exit(1 if nd else 0)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'compare'])
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--only', default='')
    ap.add_argument('--inject-diff', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'run':
        run(os.path.abspath(a.a), os.path.abspath(a.b), [x for x in a.only.split(',') if x], a.inject_diff)
    else:
        compare(a.a, a.b, [x for x in a.only.split(',') if x] or None)
