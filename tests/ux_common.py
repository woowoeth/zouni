"""ux_*_check.py 共用的小工具（2026-10-17）：本地静态服务（可现场改 site.js / sw.js 做反向注入）、playwright 上下文、断言记账、点击区实测。

约定：
  - 每个脚本：  python3 tests/ux_xxx_check.py build/site [--shots DIR] [--inject 名字]
  - 全过退出码 0；任一红退出码 1，并逐条列出；脚本自己中途出错也记成一条红（不让后面的场景被吞掉）
  - --inject 名字：只改送到浏览器的 site.js / sw.js（磁盘上的不动），对应判据必须变红；旧串找不到 = 注入没生效 = 也算红（防止“注入点失效却还是绿”）
"""
import functools, http.server, json, os, re, socketserver, sys, threading, traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Env:
    def __init__(self, injects=None, extra_routes=None):
        a = sys.argv[1:]
        self.site = os.path.abspath(a[0]) if a and not a[0].startswith('--') else os.path.join(ROOT, 'build', 'site')
        self.shots = a[a.index('--shots') + 1] if '--shots' in a else None
        self.inject = a[a.index('--inject') + 1] if '--inject' in a else None
        if self.shots: os.makedirs(self.shots, exist_ok=True)
        self.injects = injects or {}
        if self.inject and self.inject not in self.injects: sys.exit('--inject 只认 ' + ' / '.join(self.injects))
        self.fails, self.oks, self.errs, self.notes = [], [], [], []
        env = self

        class Q(http.server.SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
            def send_head(self):
                p = self.translate_path(self.path.split('?')[0].split('#')[0])
                if env.inject:
                    f, old, new = env.injects[env.inject]
                    if p.endswith(os.sep + f.replace('/', os.sep)):
                        import io
                        body = open(p, encoding='utf-8').read()
                        pairs = list(zip(old, new)) if isinstance(old, list) else [(old, new)]
                        for o_, n_ in pairs:
                            if o_ not in body: env.errs.append('INJECT-NOT-APPLIED: ' + env.inject)
                            body = body.replace(o_, n_)
                        data = body.encode('utf-8')
                        self.send_response(200); self.send_header('Content-Type', ('text/css' if f.endswith('.css') else 'application/javascript') + '; charset=utf-8'); self.send_header('Content-Length', str(len(data))); self.end_headers()
                        return io.BytesIO(data)
                return super().send_head()
        socketserver.TCPServer.allow_reuse_address = True
        self.srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=self.site))
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.B = 'http://127.0.0.1:%d' % self.srv.server_address[1]

    def check(self, name, cond, detail=''):
        (self.oks if cond else self.fails).append(name + ('  → ' + str(detail)[:400] if detail != '' and not cond else ''))

    def note(self, s):
        self.notes.append(s); print('  · ' + s)

    def guard(self, name):
        env = self

        class G:
            def __enter__(s): return s
            def __exit__(s, t, v, tb):
                if v is not None:
                    env.fails.append('%s：场景中途出错，后面的判据没跑到（%s: %s）' % (name, type(v).__name__, (str(v).strip().splitlines() or [''])[0][:200]))
                    if os.environ.get('UX_TRACE'): traceback.print_exception(t, v, tb)
                    return True
                return False
        return G()

    def finish(self, title):
        errs = [e for e in self.errs if e.startswith('INJECT-NOT-APPLIED') or not self.inject]   # 反向注入时页面报错是预期的
        bad = list(self.fails) + (['控制台/页面报错：' + e for e in errs[:6]] if errs else [])
        for x in self.oks: print('✓', x)
        for x in bad: print('✗', x)
        print('\n%s：%d 过 · %d 红%s' % (title, len(self.oks), len(bad), ('（--inject ' + self.inject + '）') if self.inject else ''))
        sys.exit(1 if bad else 0)


# 点击区实测：从元素中心向四个方向一格一格试 elementFromPoint，量“真正点得到这个元素”的范围（伪元素、被邻居盖住的都算进去）；盖住中心点返回 null
HIT = """(el)=>{if(!el)return null;el.scrollIntoView({block:'center',behavior:'instant'});
 const r=el.getBoundingClientRect();if(r.width<1||r.height<1)return null;const cx=r.left+r.width/2,cy=r.top+r.height/2;
 const ok=(x,y)=>{const t=document.elementFromPoint(x,y);return t&&(t===el||el.contains(t))};
 if(!ok(cx,cy))return null;const sc=(dx,dy)=>{let n=0;while(n<90&&ok(cx+dx*(n+1),cy+dy*(n+1)))n++;return n};
 return {w:sc(-1,0)+sc(1,0)+1,h:sc(0,-1)+sc(0,1)+1,bw:Math.round(r.width),bh:Math.round(r.height)}}"""

NO_NET = re.compile(r'.*(open-meteo|amap\.com|baidu|googletagmanager|hm\.baidu).*')


def new_ctx(br, p, w=390, h=844, storage=None, dark=False, **kw):
    c = br.new_context(viewport={'width': w, 'height': h}, is_mobile=True, has_touch=True, device_scale_factor=2, color_scheme='dark' if dark else 'light', timezone_id='Asia/Shanghai', locale='zh-CN', **kw)
    c.add_init_script("""(function(){var w={writeText:function(t){window.__clip=t;return Promise.resolve()}};try{Object.defineProperty(navigator,'clipboard',{value:w,configurable:true})}catch(e){}})();""")
    if storage:
        c.add_init_script('try{if(!localStorage.getItem("__seeded")){localStorage.setItem("__seeded","1");' + ''.join('localStorage.setItem(%s,%s);' % (json.dumps(k), json.dumps(v)) for k, v in storage.items()) + '}}catch(e){}')
    return c


def new_page(env, c, hits_errors=True):
    pg = c.new_page(); pg.set_default_timeout(12000)
    if hits_errors:
        pg.on('console', lambda m: env.errs.append('console: ' + m.text[:160]) if m.type == 'error' and 'Failed to load resource' not in m.text and 'open-meteo' not in m.text and 'ERR_INTERNET_DISCONNECTED' not in m.text else None)
        pg.on('pageerror', lambda e: env.errs.append('pageerror: ' + str(e)[:200]))
    pg.route(NO_NET, lambda r: r.abort())
    return pg


def goto(env, pg, path, wait=500):
    pg.goto(env.B + path, wait_until='networkidle')
    pg.wait_for_timeout(wait)


def ls(pg, key):
    return pg.evaluate('(k)=>localStorage.getItem(k)', key)


def home_ready(pg, timeout=15000):
    """首页第 9 条起的数据补齐了（过季那批在页面就绪后才取）"""
    pg.wait_for_function("document.documentElement.getAttribute('data-hb')", timeout=timeout)
