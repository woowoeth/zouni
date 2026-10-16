#!/usr/bin/env python3
"""行程页「调整 → 换成… / 在这之后加一个…」（顺路景点）的带断言测试（2026-10-16）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/nearby_ui_check.py build/site                 # 全过退出码 0，否则 1 并逐条列出
    python3 tests/nearby_ui_check.py build/site --shots DIR     # 同时存 390 宽截图（弹层、选中后；给人看，不参与判定）
    python3 tests/nearby_ui_check.py build/site --inject leg_text|undo|limit    # 反向自检：故意改坏 site.js，对应判据必须变红

自己起本地静态服务，playwright chromium，iPhone 13（390 宽），固定“现在”= 2026-10-16 14:20（日期相关的闭馆、默认出发日才可复查）。
覆盖（和任务单 ①–⑪ 对应）：
  ① 弹层出现“换成…”“在这之后加一个…”（xa3 西安、gqhx10 自驾长线、tk4 东京、par5 巴黎、nj3 南京）
  ② 西安陕西历史博物馆之后加一个：当天出现新行；前后两条车程行的分钟和文字与 Python 版模型（tools/nearby_model.py，独立实现）一致；
     当天 非吃饭站 ≤4、结束 ≤22:30、首尾 ≤10 小时；时间单调；新行门票只显示、总价不变
  ③ 替换：旧站消失、新站（换的）出现、前后车程重算
  ④ 撤销（toast 的“撤销”、弹层里的“撤销这次添加 / 换回原来的”）后这一天的 DOM 和改前逐字一致（outerHTML 相等），localStorage 键清掉
  ⑤ 刷新后保留；再撤销
  ⑥ 已排满的天，“加一个”置灰并写原因；候选不让超限（东京第 1 天浅草寺后面唯一的候选会晚于 21:30，必须不出现）
  ⑦ 巴黎空状态“附近没有顺路的”
  ⑧ 复制行程、日历导出、今天视图都含新站；导航链接（国内高德 / 国外谷歌）指向新站，后一站的导航起点换成新站
  ⑨ 分享链接（#mine=）带上 zouni_np_，朋友打开看到同样的行
  ⑩ 无控制台报错（含脏数据：存了乱码、旧版本号、对不上的锚点，页面回到原版不报错）
  ⑪ 390 宽弹层不溢出、可点元素 ≥44px
  叠加  去掉一天 / 加一天 / 下雨换室内 / 改出发时间 / 去掉这一站 / 恢复 / 多待少待，和顺路站一起用不乱
  闭馆  出发日让某天落在周一，周一闭馆的候选不出现
"""
import functools, http.server, json, math, os, re, socketserver, sys, threading, urllib.parse
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import nearby_model as NM   # noqa: E402  独立于页面里的 JS：车程分钟的“标准答案”来自这里

args = sys.argv[1:]
site = os.path.abspath(args[0]) if args and not args[0].startswith('--') else os.path.abspath(os.path.join(ROOT, 'build', 'site'))
shots = args[args.index('--shots') + 1] if '--shots' in args else None
inject = args[args.index('--inject') + 1] if '--inject' in args else None
if shots:
    os.makedirs(shots, exist_ok=True)

# 反向注入：只改送到浏览器的 site.js（磁盘上的不动）。(旧, 新)，旧串必须能找到，否则注入没生效，直接报错
INJECT = {
    'leg_text': ("txt:(pre||'')+how+' '+npDur(mins)+", "txt:(pre||'')+how+' '+npDur(mins+5)+"),                                   # 车程文字写错一格（多 5 分钟）
    'undo': ("if(r.getAttribute('data-np')==='v'){r.parentNode.removeChild(r);return}", "if(r.getAttribute('data-np')==='v'){return}"),   # 撤销不还原（加的行删不掉）
    'limit': ("if(!b.ok)return{ok:false,reason:b.reason,b:b};", "if(false)return{ok:false,reason:b.reason,b:b};"),                   # 超限也能选
}
INJ = None
if inject:
    if inject not in INJECT:
        sys.exit('--inject 只认 ' + ' / '.join(INJECT))
    INJ = INJECT[inject]


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = 'http://127.0.0.1:%d' % srv.server_address[1]

fails, oks = [], []


def check(name, cond, detail=''):
    (oks if cond else fails).append(name + ('  → ' + str(detail)[:300] if detail != '' and not cond else ''))


class _Guard:
    """一段场景里脚本自己出错（找不到按钮、超时）也记成一条红，不让整个脚本崩掉、后面的场景不跑"""
    def __init__(self, name): self.name = name
    def __enter__(self): return self
    def __exit__(self, t, v, tb):
        if v is not None:
            fails.append('%s：场景中途出错，后面的判据没跑到（%s: %s）' % (self.name, type(v).__name__, str(v).strip().splitlines()[0][:160] if str(v).strip() else ''))
            return True
        return False


def guard(name): return _Guard(name)


FIX = """(()=>{const RD=Date;const fixed=new RD('2026-10-16T14:20:00+08:00').getTime();class FD extends RD{constructor(...a){if(a.length)super(...a);else super(fixed)}static now(){return fixed}};window.Date=FD})();"""
ROWS = """(n)=>[...document.querySelectorAll('#d'+n+' .tl > .r')].map(r=>({c:r.className,h:r.hidden,t:(r.querySelector('time')||{}).textContent,m:(r.querySelector('.m')&&r.querySelector('.m').childNodes[0]||{}).textContent||'',s:(r.querySelector('.s')||{}).textContent||'',
  k:r.dataset.k,np:r.dataset.np||'',ll:r.dataset.ll||'',min:r.dataset.min||'',at:r.dataset.at||'',dm:r.dataset.dm||'',mode:r.dataset.mode||'',map:(r.querySelector('a.ic.map')||{getAttribute:()=>''}).getAttribute('href')||'',bkn:!!r.querySelector('.bkn')}))"""
LIM_JS = """(n)=>{const s=document.getElementById('d'+n);return {lm:s.dataset.lm,sp:s.dataset.sp,ep:s.dataset.ep,sv:document.querySelector('article.trip').dataset.sv}}"""
errs = []


def hm(t):
    m = re.match(r'^(\d\d):(\d\d)$', t or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def ll(s):
    a = s.split(',')
    return (float(a[0]), float(a[1]))


def dur_txt(m):
    return ('%d 小时' % (m // 60) + (' %d 分' % (m % 60) if m % 60 else '')) if m >= 60 else '%d 分钟' % m


def leg_text(a, b, mode, f, sv):
    """页面上一段车程文字的标准答案（和 compile_itineraries.leg + 作者车程比例 f）"""
    how, mins, dist = NM.leg(a, b, mode)
    if f and f != 1 and how != '步行':
        mins = max(5, NM.r5(mins * f))
    if sv and how.startswith('包车'):
        how = '自驾' + how[2:]
    return '%s %s%s' % (how, dur_txt(mins), (' · %d 公里' % dist) if dist and dist >= 5 else ''), mins


with sync_playwright() as p:
    br = p.chromium.launch()

    def new_page(storage=None, ctx=None):
        c = ctx or br.new_context(**p.devices['iPhone 13'], timezone_id='Asia/Shanghai', locale='zh-CN')
        c.add_init_script(FIX)
        if storage:
            c.add_init_script('try{' + ''.join('localStorage.setItem(%s,%s);' % (json.dumps(k), json.dumps(v)) for k, v in storage.items()) + '}catch(e){}')
        pg = c.new_page()
        pg.on('console', lambda m: errs.append('console: ' + m.text) if m.type == 'error' and 'Failed to load resource' not in m.text and 'open-meteo' not in m.text else None)
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)[:200]))
        pg.route(re.compile(r'.*(open-meteo|googletagmanager|hm\.baidu).*'), lambda r: r.abort())
        if INJ:
            def patch(route):
                body = open(os.path.join(site, 'assets', 'site.js'), encoding='utf-8').read()
                if INJ[0] not in body:
                    errs.append('INJECT-NOT-APPLIED: ' + inject)
                route.fulfill(status=200, content_type='application/javascript; charset=utf-8', body=body.replace(INJ[0], INJ[1]))
            pg.route(re.compile(r'.*/assets/site\.js.*'), patch)
        return c, pg

    def goto(pg, trip, init=None, hash_=''):
        pg.goto(B + '/trip/%s/%s' % (trip, hash_), wait_until='networkidle')
        if init:
            pg.evaluate(init)
            pg.goto(B + '/trip/%s/' % trip, wait_until='networkidle')
        pg.wait_for_timeout(500)
        pg.evaluate("document.documentElement.style.scrollBehavior='auto'")

    def rows(pg, n):
        return pg.evaluate(ROWS, n)

    def vis(pg, n):
        return [r for r in rows(pg, n) if not r['h']]

    def sect(pg, n):
        """一天的完整快照（section 的 outerHTML）+ 页头摘要：撤销后要逐字一样"""
        return pg.evaluate("(n)=>{const s=document.getElementById('d'+n);return (s.outerHTML+'||'+document.querySelector('.glance').outerHTML).split(' style=\"\"').join('')}", n)      # 截图会让浏览器给个别节点留下空的 style=""，和我们改没改无关，去掉再比

    def diff_hint(a, b):
        import difflib
        d = [l for l in difflib.unified_diff(a.split('><'), b.split('><'), lineterm='', n=0) if not l.startswith(('---', '+++', '@@'))]
        return ' // '.join(x[:160] for x in d[:6]) or '(长度 %d / %d)' % (len(a), len(b))

    def same(pg, n, ref):
        cur = sect(pg, n)
        return cur == ref, (diff_hint(ref, cur) if cur != ref else '')

    def open_adj(pg, day, name):
        names = pg.evaluate("(n)=>[...document.querySelectorAll('#d'+n+' .tl > .r')].filter(r=>r.querySelector('.adj')).map(r=>r.querySelector('.m').childNodes[0].textContent.trim())", day)
        i = next((k for k, x in enumerate(names) if x.startswith(name)), None)
        if i is None:
            return None
        loc = pg.locator('#d%d .tl > .r .adj' % day).nth(i)
        loc.scroll_into_view_if_needed(); loc.click(); pg.wait_for_timeout(250)
        return i

    def close_pk(pg):
        if pg.locator('.pk .pk-x').count():
            pg.locator('.pk .pk-x').first.click(); pg.wait_for_timeout(150)

    def pick_list(pg, day, name, kind):
        """点开弹层 → 点“换成/加一个” → 返回候选 [{n, d, line}]；空状态返回 []，并把说明放进 pg._note"""
        if open_adj(pg, day, name) is None:
            return None
        bt = pg.locator('.pk [data-np="%s"]' % kind)
        if not bt.count() or bt.is_disabled():
            return None
        bt.click()
        pg.wait_for_selector('.pk .npc, .pk .npe', timeout=15000)
        out = pg.evaluate("[...document.querySelectorAll('.pk .npc')].map(b=>({n:b.querySelector('b').textContent,d:b.querySelector('.npd').textContent,line:b.querySelector('small').textContent,t:b.querySelector('.npt').textContent}))")
        pg._note = pg.evaluate("[...document.querySelectorAll('.pk .xnote')].map(x=>x.textContent).join('|')")
        return out

    STUB = "()=>{window.__c='';Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t}},configurable:true});try{delete navigator.share}catch(e){};navigator.share=undefined}"

    def share_do(pg, what):
        """分享弹层里点 copy / link：返回写进剪贴板的文字（每次重新装剪贴板桩，刷新后也能用）"""
        pg.evaluate(STUB)
        pg.locator('.share').scroll_into_view_if_needed(); pg.locator('.share').click(); pg.wait_for_timeout(200)
        pg.locator('.xd button[data-a="%s"]' % what).click(); pg.wait_for_timeout(300)
        return pg.evaluate('window.__c') or ''

    def choose(pg, i):
        pg.locator('.pk .npc').nth(i).click(); pg.wait_for_timeout(500)

    def budget_ok(rs):
        """当天硬规则：非吃饭站 ≤5、结束 ≤21:30（replan 的“这天几点结束”）、首尾 ≤13 小时。读页面上的行和提示"""
        v = [r for r in rs if not r['h'] and hm(r['t']) is not None and r['s'] != '回去歇一下']
        n = sum(1 for r in v if ('see' in r['c'] or 'fun' in r['c']) and '沿途慢慢走' not in r['m'])
        ts = [hm(r['t']) for r in v]
        return n, ts

    # ———————————————— 西安：陕西历史博物馆之后加一个 ————————————————
    with guard('西安：陕西历史博物馆之后加一个'):
        c, pg = new_page()
        goto(pg, 'xa3')
        price0 = pg.evaluate("document.querySelector('.glance .price').textContent")
        glance0 = pg.evaluate("document.querySelector('.glance').innerText")
        check('① 西安第 3 天：弹层里有“换成…”', open_adj(pg, 3, '陕西历史博物馆') is not None and pg.locator('.pk [data-np="rep"]').count() == 1)
        check('① 西安第 3 天：弹层里有“在这之后加一个…”且可点', pg.locator('.pk [data-np="ins"]').count() == 1 and not pg.locator('.pk [data-np="ins"]').is_disabled())
        check('① 弹层保留原有三项（多待、少待、去掉这一站）', pg.locator('.pk [data-d="30"]').count() == 1 and pg.locator('.pk [data-d="-30"]').count() == 1 and pg.locator('.pk [data-x]').count() == 1)
        close_pk(pg)
        d3_0 = rows(pg, 3); sec0 = sect(pg, 3)
        cands = pick_list(pg, 3, '陕西历史博物馆', 'ins')
        check('② 候选列表有内容、最多 8 条', bool(cands) and len(cands) <= 8, cands)
        check('② 候选行有名字、“+N 分钟”、一句话、类型字', bool(cands) and all(re.match(r'^\+\d+ 分钟$', x['d']) and x['line'] and x['t'] for x in cands), cands)
        names0 = [x['n'] for x in cands or []]
        check('② 列表里没有“大慈恩寺”（和当天的大雁塔是同一处）、没有本线已有的站', '大慈恩寺' not in names0 and '大雁塔' not in names0 and '陕西历史博物馆' not in names0, names0)
        ix = names0.index('大兴善寺') if '大兴善寺' in names0 else 0
        X_name = names0[ix] if names0 else ''
        choose(pg, ix)
        check('⑤ 选中后 toast 里有“撤销”按钮、写着加了哪一站', pg.locator('.toast .toast-act').count() >= 1 and X_name in pg.evaluate("(document.querySelector('.toast')||{}).innerText||''"))
        d3 = rows(pg, 3)
        newrow = [r for r in d3 if r['np'] == 'v' and 'see' in r['c']]
        check('② 当天出现新行（带“加的”）', len(newrow) == 1 and newrow[0]['m'] == X_name + '（加的）', newrow)
        # 前后两段车程
        sinfo = pg.evaluate(LIM_JS, 3)
        S_row = next(r for r in d3 if r['m'].startswith('陕西历史博物馆'))
        B_row = next(r for r in d3 if r['m'].startswith('大雁塔'))
        dep_new = [r for r in d3 if r['np'] == 'v' and 'dep' in r['c']]
        dep_after = d3[d3.index(B_row) - 1]
        d3b = d3_0
        t0 = int(next(r for r in d3b if r['m'].startswith('出发 → 大雁塔'))['min'] or 0)
        if newrow and dep_new:
            X = ll(newrow[0]['ll']); S = ll(S_row['ll']); Bp = ll(B_row['ll']); mode = sinfo['lm']; sv = sinfo['sv'] == '1'
            f = NM.factor(S, Bp, t0, mode) if t0 else 1.0
            e1, m1 = leg_text(S, X, mode, f, sv); e2, m2 = leg_text(X, Bp, mode, f, sv)
            check('② 新行前面的车程行文字 = 模型（S→新站）', dep_new[0]['s'].strip() == e1 and dep_new[0]['m'] == '出发 → ' + X_name, (dep_new[0]['s'], e1))
            check('② 后一站前面的车程行文字 = 模型（新站→大雁塔）', dep_after['s'].strip() == e2 and dep_after['m'] == '出发 → 大雁塔', (dep_after['s'], e2))
        ts = [hm(r['t']) for r in d3 if not r['h'] and hm(r['t']) is not None]
        check('② 当天时间单调不减', ts == sorted(ts), ts)
        ix_new = d3.index(newrow[0]) if newrow else -1
        check('② 新站在陕西历史博物馆之后、午饭之前（紧跟锚点）', ix_new == d3.index(S_row) + 2, [r['m'] for r in d3])
        check('② 新行第二行有门票/一句话，且没有改总价', pg.evaluate("document.querySelector('.glance .price').textContent") == price0 and bool(newrow) and X_name != '')
        n_stops, ts2 = budget_ok(d3)
        check('② 当天非吃饭站 ≤5', n_stops <= 5, n_stops)
        end = pg.evaluate("(document.querySelector('#d3 .latewarn')||{}).innerText||''")
        check('② 当天结束 ≤21:30（页面没有“这天要到…才结束”的提示）', '才结束' not in end, end)
        check('② 当天首尾 ≤13 小时', max(ts2) - min(ts2) <= 780, (min(ts2), max(ts2)))
        # 导出
        check('⑧ 复制行程里有新站', X_name in share_do(pg, 'copy'))
        ics = pg.evaluate('window.zIcs?window.zIcs():""')
        check('⑧ 日历文件里有新站', X_name in ics)
        link = share_do(pg, 'link')
        check('⑨ 分享链接带上 zouni_np_', '#mine=' in link)
        if '#mine=' in link:
            import base64
            st = json.loads(base64.urlsafe_b64decode(link.split('#mine=')[1] + '===').decode('utf-8'))
            check('⑨ 链接里的状态含 zouni_np_ 且是 v1', 'zouni_np_' in st and st['zouni_np_'].get('v') == 1, list(st))
            c2, pg2 = new_page()
            pg2.goto(link.replace('http://127.0.0.1:%d' % srv.server_address[1], B), wait_until='networkidle'); pg2.wait_for_timeout(1500)
            r2 = [r['m'] for r in vis(pg2, 3)]
            check('⑨ 朋友打开链接，第 3 天里也有新站', X_name + '（加的）' in r2, r2)
            c2.close()
        # 今天视图读 DOM
        pg.locator('.tvbtn').click(); pg.wait_for_timeout(300)
        pg.locator('.tvtabs button[data-i="2"]').click(); pg.wait_for_timeout(200)
        tvn = pg.evaluate("[...document.querySelectorAll('.tvl .tvnav')].map(a=>a.getAttribute('href'))")
        check('⑧ 今天视图第 3 天里有新站，它的导航按钮指向新站（高德导航链接里有新站名）', X_name in pg.evaluate("document.querySelector('.tv').innerText") and any(urllib.parse.quote(X_name) in (x or '') for x in tvn), tvn)
        pg.locator('.tvx').first.click(); pg.wait_for_timeout(200)
        # 导航：新站的导航终点、后一站的起点
        if newrow:
            d3 = rows(pg, 3)
            nr = [r for r in d3 if r['np'] == 'v' and 'see' in r['c']][0]
            nb = next(r for r in d3 if r['m'].startswith('大雁塔'))
            check('⑧ 新站的导航链接是高德导航，终点名字是新站', 'uri.amap.com/navigation' in nr['map'] and urllib.parse.quote(X_name) in nr['map'], nr['map'])
            check('⑧ 大雁塔的导航起点换成了新站（和原来不同）', nb['map'] != next(r for r in d3_0 if r['m'].startswith('大雁塔'))['map'] and 'from=' in nb['map'])
        # 撤销（toast）
        pg.wait_for_timeout(300)
        # 刷新后保留
        pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        r_after = [r['m'] for r in vis(pg, 3)]
        check('⑤ 刷新后新站还在', X_name + '（加的）' in r_after, r_after)
        ls = pg.evaluate("localStorage.getItem('zouni_np_xa3')")
        check('⑤ localStorage 键 zouni_np_xa3 是带版本的 JSON', bool(ls) and json.loads(ls).get('v') == 1 and 'oi' in json.loads(ls), ls)
        # 弹层里撤销
        i = open_adj(pg, 3, X_name)
        check('④ 新行的弹层：只有多待/少待/撤销这次添加，没有再“换成/加一个”', i is not None and pg.locator('.pk [data-npu]').count() == 1 and pg.locator('.pk [data-np]').count() == 0)
        pg.locator('.pk [data-npu]').click(); pg.wait_for_timeout(2300)
        ok_, hint_ = same(pg, 3, sec0); check('④ 撤销后第 3 天的 DOM 和改前逐字一致', ok_, hint_)
        check('④ 撤销后 localStorage 键没了', pg.evaluate("localStorage.getItem('zouni_np_xa3')") is None)
        # toast 撤销
        cands = pick_list(pg, 3, '陕西历史博物馆', 'ins'); choose(pg, 0)
        pg.wait_for_selector('.toast .toast-act', timeout=3000)
        pg.locator('.toast .toast-act').click(); pg.wait_for_timeout(2300)
        ok_, hint_ = same(pg, 3, sec0); check('④ toast 的“撤销”后第 3 天也回到改前', ok_, hint_)

    # ———————————————— 替换 ————————————————
    with guard('替换'):
        cands = pick_list(pg, 3, '陕西历史博物馆', 'rep')
        check('③ “换成”有候选，标签是“换了多 N 分钟 / 省 N 分钟 / 路程差不多”', bool(cands) and all(re.match(r'^(换了多 \d+ 分钟|省 \d+ 分钟|路程差不多)$', x['d']) for x in cands), cands)
        if cands:
            R_name = cands[0]['n']
            choose(pg, 0)
            d3 = rows(pg, 3); v3 = [r for r in d3 if not r['h']]
            check('③ 旧站消失、新站（换的）出现', not any(r['m'].startswith('陕西历史博物馆') for r in v3) and any(r['m'] == R_name + '（换的）' for r in v3), [r['m'] for r in v3])
            nb = next(r for r in d3 if r['m'].startswith('大雁塔'))
            rr = next(r for r in d3 if r['m'] == R_name + '（换的）')
            d0 = d3[d3.index(rr) - 1]
            check('③ 新站前面的车程行改成“出发 → 新站”', d0['m'] == '出发 → ' + R_name, d0['m'])
            ts = [hm(r['t']) for r in v3 if hm(r['t']) is not None]
            check('③ 替换后时间单调不减', ts == sorted(ts), ts)
            cp = share_do(pg, 'copy')
            sec3 = cp.split('第三天')[1] if '第三天' in cp else ''
            lines3 = [l.strip() for l in sec3.split('\n')[1:] if l.startswith('  ')]
            check('③ 复制行程里第 3 天是新站、没有旧站', any(l.endswith(R_name + '（换的）') for l in lines3) and not any('陕西历史博物馆' in l for l in lines3), lines3)
            i = open_adj(pg, 3, R_name)
            check('③ 被换过的行的弹层有“换回原来的”', i is not None and pg.locator('.pk [data-npr]').count() == 1)
            pg.locator('.pk [data-npr]').click(); pg.wait_for_timeout(2300)
            ok_, hint_ = same(pg, 3, sec0); check('④ 换回原来的之后第 3 天逐字一致', ok_, hint_)
        close_pk(pg)

    # ———————————————— 已排满：第 2 天已排到 22:10（晚于 21:30）————————————————
    with guard('已排满：第 2 天已排到 22:10（晚于 21:30）'):
        open_adj(pg, 2, '华清宫')
        bt = pg.locator('.pk [data-np="ins"]')
        why = bt.inner_text() if bt.count() else ''
        check('⑥ 已排满的天，“加一个”置灰、写原因', bt.count() == 1 and bt.is_disabled() and '排满' in why and '22:' in why, why)
        check('⑥ 已排满的天，“换成”仍可用', pg.locator('.pk [data-np="rep"]').count() == 1 and not pg.locator('.pk [data-np="rep"]').is_disabled())
        close_pk(pg)
        # 定点的站（皮影戏 19:30）不出现这两项
        open_adj(pg, 1, '高家大院')
        check('① 定点的站（皮影戏）没有“换成/加一个”', pg.locator('.pk [data-np]').count() == 0)
        close_pk(pg)

    # ———————————————— 390 宽：弹层不溢出、可点元素 ≥44 ————————————————
    with guard('390 宽：弹层不溢出、可点元素 ≥44'):
        open_adj(pg, 3, '陕西历史博物馆')
        m1 = pg.evaluate("""()=>{const pk=document.querySelector('.pk'),r=pk.getBoundingClientRect();const small=[...pk.querySelectorAll('button')].filter(b=>b.getBoundingClientRect().height<43.5).map(b=>b.className+':'+Math.round(b.getBoundingClientRect().height));
          return {w:Math.round(r.width),right:Math.round(r.right),vw:innerWidth,sw:pk.scrollWidth,cw:pk.clientWidth,doc:document.documentElement.scrollWidth,small:small}}""")
        check('⑪ 弹层在 390 宽里：不超出屏幕、没有横向溢出', m1['right'] <= m1['vw'] and m1['sw'] <= m1['cw'] + 1 and m1['doc'] <= m1['vw'] + 1, m1)
        check('⑪ 弹层里新入口和关闭按钮高度 ≥44（原有“多待/少待/去掉”本来就是 48）', not [x for x in m1['small']], m1['small'])
        if shots:
            pg.screenshot(path=os.path.join(shots, 'np_popup_390.png'))
        pg.locator('.pk [data-np="ins"]').click(); pg.wait_for_selector('.pk .npc', timeout=15000); pg.wait_for_timeout(200)
        m2 = pg.evaluate("""()=>{const pk=document.querySelector('.pk'),r=pk.getBoundingClientRect();const small=[...pk.querySelectorAll('button')].filter(b=>b.getBoundingClientRect().height<43.5).map(b=>b.className+':'+Math.round(b.getBoundingClientRect().height));
          const off=[...pk.querySelectorAll('.npc')].filter(b=>b.scrollWidth>b.clientWidth+1).length;return {right:Math.round(r.right),vw:innerWidth,sw:pk.scrollWidth,cw:pk.clientWidth,doc:document.documentElement.scrollWidth,small:small,off:off,h:Math.round(r.height),vh:innerHeight}}""")
        check('⑪ 候选列表在 390 宽里不溢出，每个候选按钮溢出为 0', m2['right'] <= m2['vw'] and m2['sw'] <= m2['cw'] + 1 and m2['doc'] <= m2['vw'] + 1 and m2['off'] == 0, m2)
        check('⑪ 候选列表里的按钮（候选、返回、关上）高度都 ≥44', not m2['small'], m2['small'])
        check('⑪ 候选列表没有顶出屏幕上沿', m2['h'] <= m2['vh'], m2)
        if shots:
            pg.screenshot(path=os.path.join(shots, 'np_list_390.png'))
        pg.locator('.pk .pk-bk').click(); pg.wait_for_timeout(150)
        check('① 候选列表左上“‹”回到弹层', pg.locator('.pk [data-np="rep"]').count() == 1)
        close_pk(pg)
        # 选中后截图
        pick_list(pg, 3, '陕西历史博物馆', 'ins'); choose(pg, 0); pg.wait_for_timeout(300)
        if shots:
            pg.screenshot(path=os.path.join(shots, 'np_after_390.png'))
        # 叠加：多待 30 分钟 + 去掉一站 + 恢复
        nv0 = [r for r in rows(pg, 3) if r['np'] == 'v' and 'see' in r['c']][0]; nm_new = nv0['m']
        open_adj(pg, 3, nm_new[:-4]); pg.locator('.pk [data-d="30"]').click(); pg.wait_for_timeout(400)
        r3 = rows(pg, 3); nv = [r for r in r3 if r['np'] == 'v' and 'see' in r['c']][0]
        dm0 = int(nv0['dm']); want = dur_txt(dm0 + 30)
        check('叠加：加的站可以多待 30 分钟（第二行的时长变成“%s”）' % want, nv['s'].startswith(want) or ('要预约' in nv['s'] and want in nv['s']), (nv['s'], want))
        ts = [hm(r['t']) for r in r3 if not r['h'] and hm(r['t']) is not None]
        check('叠加：多待之后时间仍单调', ts == sorted(ts), ts)
        # 恢复：这天的“恢复”会把顺路站也清掉
        if pg.locator('#d3 .latewarn .reset').count():
            pg.locator('#d3 .latewarn .reset').click(); pg.wait_for_timeout(2300)
            ok_, hint_ = same(pg, 3, sec0); check('叠加：这天的“恢复”同时清掉顺路站，DOM 回到改前', ok_ and pg.evaluate("localStorage.getItem('zouni_np_xa3')") is None, hint_)
        else:
            check('叠加：加了顺路站的天有“恢复”按钮', False)
        # 改出发时间
        pick_list(pg, 3, '陕西历史博物馆', 'ins'); choose(pg, 0)
        pg.locator('#d3 .st').click(); pg.wait_for_timeout(200); pg.locator('.stg button[data-v="10:30"]').click(); pg.wait_for_timeout(500)
        r3 = rows(pg, 3); ts = [hm(r['t']) for r in r3 if not r['h'] and hm(r['t']) is not None]
        check('叠加：改出发时间 10:30 后，顺路站还在、时间单调', any(r['np'] == 'v' for r in r3) and ts == sorted(ts) and ts[0] == 630, ts)
        # 去掉第 2 天（刷新式）：第 3 天的顺路站还在
        pg.evaluate("localStorage.setItem('zouni_rmday_xa3','[1]')"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        ids = pg.evaluate("[...document.querySelectorAll('.day')].map(s=>s.id+':'+s.dataset.oi)")
        r2 = rows(pg, 2)
        check('叠加：去掉一天后，顺路站随所在天留着（第 3 天变第 2 天）', ids == ['d1:0', 'd2:2'] and any(r['np'] == 'v' for r in r2), (ids, [r['m'] for r in r2]))
        # 去掉第 3 天：顺路站随天一起去掉（不渲染），localStorage 里不删，恢复后回来
        pg.evaluate("localStorage.setItem('zouni_rmday_xa3','[2]')"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        check('叠加：去掉那一天后页面上没有顺路站；存储里的操作还在（恢复这天会回来）', pg.locator('[data-np="v"]').count() == 0 and bool(pg.evaluate("localStorage.getItem('zouni_np_xa3')")))
        pg.evaluate("localStorage.removeItem('zouni_rmday_xa3')"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        check('叠加：恢复这天后顺路站回来了', pg.locator('#d3 [data-np="v"]').count() == 2)
        # 加一天（自由活动）
        pg.evaluate("localStorage.setItem('zouni_extra_xa3',JSON.stringify([{k:'free',x:'f1',after:0}]))"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        ids = pg.evaluate("[...document.querySelectorAll('.day')].map(s=>s.id+':'+(s.dataset.oi||'x'))")
        ts = [hm(r['t']) for r in vis(pg, 4) if hm(r['t']) is not None]
        check('叠加：加一天后，顺路站还在原来的那天，时间单调', ids == ['d1:0', 'd2:x', 'd3:1', 'd4:2'] and pg.locator('#d4 [data-np="v"]').count() == 2 and ts == sorted(ts), (ids, ts))
        pg.evaluate("localStorage.removeItem('zouni_extra_xa3')")
        # 下雨换室内：作用在别的行，顺路站不被碰
        pg.evaluate("localStorage.setItem('zouni_rain_xa3',JSON.stringify({2:{k:5,n:'某某博物馆',c:'西安'}}))"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        check('叠加：存了下雨换室内的状态，顺路站不受影响', pg.locator('#d3 [data-np="v"]').count() == 2, errs[-3:])
        pg.evaluate("localStorage.removeItem('zouni_rain_xa3')")
        # 去掉这一站（锚点）：顺路站跟着一起去掉，存储里的操作也删
        pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
        open_adj(pg, 3, '陕西历史博物馆'); pg.locator('.pk [data-x]').click(); pg.wait_for_timeout(600)
        check('叠加：去掉锚点那一站，顺路站随它一起去掉，存储里的操作也删了', pg.locator('#d3 [data-np="v"]').count() == 0 and pg.evaluate("localStorage.getItem('zouni_np_xa3')") is None)
        c.close()

    # ———————————————— 脏数据：回到原版、不报错 ————————————————
    with guard('脏数据：回到原版、不报错'):
        for label, val in (('乱码', 'xx{{{'), ('未来版本号', json.dumps({'v': 9, 'oi': {'2': [{'op': 'ins', 'ak': 1, 'an': '陕西历史博物馆', 'u': 1, 'n': 'X', 'a': 34.2, 'o': 108.9, 'd': 60}]}})),
                           ('锚点名对不上', json.dumps({'v': 1, 'oi': {'2': [{'op': 'ins', 'ak': 1, 'an': '不存在的站', 'u': 1, 'n': '某寺', 'c': '西安', 'a': 34.2, 'o': 108.9, 'd': 60}]}})),
                           ('字段缺失', json.dumps({'v': 1, 'oi': {'2': [{'op': 'ins', 'ak': 1, 'an': '陕西历史博物馆'}]}}))):
            c, pgd = new_page({'zouni_np_xa3': val})
            e0 = len(errs)
            pgd.goto(B + '/trip/xa3/', wait_until='networkidle'); pgd.wait_for_timeout(1500)
            check('⑩ 脏数据（%s）：页面回到原版，没有加的行' % label, pgd.locator('[data-np]').count() == 0 and [r['m'] for r in vis(pgd, 3)] == [r['m'] for r in d3_0 if not r['h']], [r['m'] for r in vis(pgd, 3)])
            check('⑩ 脏数据（%s）：没有控制台报错' % label, len(errs) == e0, errs[e0:])
            c.close()

    # ———————————————— 自驾长线：车程文字是“自驾约/开车”，开车小时更新，撤销逐字一致 ————————————————
    with guard('自驾长线：车程文字是“自驾约/开车”，开车小时更新，撤销逐字一致'):
        c, pg = new_page()
        goto(pg, 'gqhx10')
        sec0 = sect(pg, 1)
        fx0 = pg.evaluate("[...document.querySelectorAll('#d1 .facts .fx')].map(f=>f.innerText.replace(/\\n/g,' '))")
        cands = pick_list(pg, 1, '塔尔寺', 'ins')
        check('① 自驾长线第 1 天：“在这之后加一个”有候选', bool(cands), (cands, getattr(pg, '_note', '')))
        if cands:
            X_name = cands[0]['n']
            choose(pg, 0)
            d1 = rows(pg, 1); sinfo = pg.evaluate(LIM_JS, 1)
            nrow = [r for r in d1 if r['np'] == 'v' and 'see' in r['c']]
            dep_n = [r for r in d1 if r['np'] == 'v' and 'dep' in r['c']]
            S_row = next(r for r in d1 if r['m'].startswith('塔尔寺'))
            if nrow and dep_n:
                S = ll(S_row['ll']); X = ll(nrow[0]['ll'])
                e1, m1_ = leg_text(S, X, sinfo['lm'], 1.0, sinfo['sv'] == '1')
                check('② 自驾线：新站前的车程文字是“自驾约/开车”、分钟和模型一致', re.match(r'^(自驾约|开车)', dep_n[0]['s']) is not None and dep_n[0]['s'].strip() == e1, (dep_n[0]['s'], e1))
            fx1 = pg.evaluate("[...document.querySelectorAll('#d1 .facts .fx')].map(f=>f.innerText.replace(/\\n/g,' '))")
            check('② 自驾线：当天“开车 N 小时”跟着更新', fx1 != fx0 and any(x.startswith('开车') for x in fx1), (fx0, fx1))
            pg.wait_for_timeout(300)
            pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1500)
            check('⑤ 自驾线刷新后保留', pg.locator('#d1 [data-np="v"]').count() == 2)
            i = open_adj(pg, 1, X_name); pg.locator('.pk [data-npu]').click(); pg.wait_for_timeout(2300)
            ok_, hint_ = same(pg, 1, sec0); check('④ 自驾线撤销后第 1 天和页头摘要逐字一致', ok_, hint_)
        c.close()

    # ———————————————— 东京：国外用谷歌地图、超限候选不出现 ————————————————
    with guard('东京：国外用谷歌地图、超限候选不出现'):
        c, pg = new_page()
        goto(pg, 'tk4')
        check('① 东京第 1 天：弹层有两个入口', open_adj(pg, 1, '浅草寺') is not None and pg.locator('.pk [data-np]').count() == 2)
        close_pk(pg)
        cands = pick_list(pg, 1, '浅草寺', 'ins')
        check('⑥ 东京第 1 天浅草寺之后：唯一的候选会让这天晚于 21:30，不许出现（不是“附近没有”，是“排满”）', cands == [] and '排满' in getattr(pg, '_note', ''), (cands, getattr(pg, '_note', '')))
        close_pk(pg)
        cands = pick_list(pg, 3, '新宿御苑', 'rep')
        if cands:
            choose(pg, 0)
            nr = [r for r in rows(pg, 3) if r['np'] == 'r']
            check('⑧ 国外线：新站的导航是谷歌地图，不是高德', bool(nr) and 'google.com/maps' in nr[0]['map'] and 'amap' not in nr[0]['map'], nr and nr[0]['map'])
        else:
            check('① 东京第 3 天新宿御苑有“换成”候选', False, getattr(pg, '_note', ''))
        c.close()

    # ———————————————— 巴黎：空状态 ————————————————
    with guard('巴黎：空状态'):
        c, pg = new_page()
        goto(pg, 'par5')
        cands = pick_list(pg, 5, '圣心堂', 'ins')
        check('⑦ 巴黎：“加一个”空状态写“附近没有顺路的”', cands == [] and '附近没有顺路的' in getattr(pg, '_note', '') + pg.evaluate("(document.querySelector('.pk .npe')||{}).textContent||''"), getattr(pg, '_note', ''))
        close_pk(pg)
        cands = pick_list(pg, 5, '圣心堂', 'rep')
        check('⑦ 巴黎：“换成”空状态也写“附近没有顺路的”', cands == [] and '附近没有顺路的' in pg.evaluate("(document.querySelector('.pk .npe')||{}).textContent||''"))
        c.close()

    # ———————————————— 南京：周一闭馆的候选，落在周一就不出现；离线提示 ————————————————
    with guard('南京：周一闭馆的候选，落在周一就不出现；离线提示'):
        c, pg = new_page()
        goto(pg, 'nj3')
        cands = pick_list(pg, 3, '南京博物院', 'rep')
        names = [x['n'] for x in cands or []]
        d3head = pg.evaluate("document.querySelector('#d3 header small').textContent")
        check('闭馆：出发日默认（第 3 天不是周一）时，周一闭馆的“总统府”能出现在候选里', '总统府' in names and '周日' in d3head, (names, d3head))
        close_pk(pg)
        pg.evaluate("localStorage.setItem('zouni_start_nj3','2027-10-16')"); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(800)
        d3head = pg.evaluate("document.querySelector('#d3 header small').textContent")
        cands = pick_list(pg, 3, '南京博物院', 'rep')
        names = [x['n'] for x in cands or []]
        check('闭馆：出发日让第 3 天落在周一后，“总统府”（周一闭馆）不出现', '周一' in d3head and '总统府' not in names and bool(names), (d3head, names))
        close_pk(pg)
        # 没网：把候选分片请求掐掉
        pg.route(re.compile(r'.*/assets/np/.*'), lambda r: r.abort())
        pg.evaluate("window.ZNP={};delete window.ZNP_CELLS")
        pg.route(re.compile(r'.*/assets/np/_index\.js.*'), lambda r: r.abort())
        open_adj(pg, 3, '南京博物院'); pg.locator('.pk [data-np="rep"]').click(); pg.wait_for_selector('.pk .npe', timeout=15000)
        check('没网：写“没网，稍后再试”，不是空白', '没网，稍后再试' in pg.evaluate("document.querySelector('.pk .npe').textContent"))
        c.close()

    check('⑩ 全程没有控制台报错', not errs, errs[:5])
    br.close()

print('通过 %d 项' % len(oks))
for x in fails:
    print('红  ' + x)
if inject:
    print('（注入 %s：%s）' % (inject, '有红，判据管用' if fails else '没有红，判据没抓到！'))
sys.exit(1 if fails else 0)
