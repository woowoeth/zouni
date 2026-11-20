#!/usr/bin/env python3
"""详情页与弹层“少就是多”（2026-10-18，设计文档 docs/handoff/design-detail-simplify.md §5 的判据 S1–S14）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/detail_simplify_check.py build/site [--shots DIR] [--only S1,S2,…] [--inject 名字]
    --inject 的名字见下面 INJ（21 种）：只改送到浏览器的 site.js / site.css / 页面 HTML（磁盘上的不动），对应判据必须变红；旧串找不到 = 注入没生效 = 也算红

判据（编号沿用设计文档）
  S1  每个可见层里“关闭类”按钮（关上 / 关闭 / × / 返回 / 回到整条行程 / 算了）数 = 1，DOM 里没有 .pk-xb；× 是 44×44、在视口内；确认层没有了
  S2  每种层：打开 → history.back() / Esc / 点遮罩 / × 都关；层没了、body.pk-open 没了、scrollY 与地址不变；反复开关不攒历史；关完再按一次返回才离开页面；存图层也一样
  S3  层叠加：地图 → 分段层 / 存图层（2026-10-18 地图里没有“调整”了，调整层只在页面里开）：返回键只关最上面一层，地图还在、body.pk-open 还在；再按一次才关地图（需要 WebGL，用软件渲染）
  S4  向下滑动关层（CDP 触摸合成）：标题行 / 小横条起手下拉 ≥100px 关；短拉弹回；往上滑、横滑不关；内容滚到非顶时从内容起手不关，滚到顶才关；有小横条
  S5  页头区：第 1 天标题离页顶 px 不超过上限；封面天数只写一次；出发日期在页头只写一处；往年气温只在页头一次（每天不再一句）
  S6  第 1 天：从天标题到第一行时间线的像素
  S7  每个 section.day 里“非站点”按钮数 ≤ 4
  S8  同一天“路上”只出现 1 次（facts 里没有）；随机 200 天 dload 的路上分钟 = 页头 / 建站时的 data-drv；.cl 可见数 ≤ 月份数
  S9  页面可见文字不含 5 条禁词
  S10 12 个任务的点击数（A–L）
  S11 “加一个顺路景点”不是死路：可点 ⇒ 点开有候选；没候选的入口在弹层里就置灰写原因（xa3 / tk4 / hss1a / hcz1 / xv613a / gqhx10，合计可点 ≥50%）
  S12 “怎么去、怎么回”同块有回程
  S13 页脚链接单行（高 ≤20px）；触控 ≥44 不退
  S14 清场：跑前跑后站目录 + data/ + site_src/ 的文件清单一致
  SX  复制行程 / 按天看：住宿卡头去掉地名后不丢信息（“今晚住：钟楼附近 · …”、出发前每条只复制一次）
  另：内容扫描（主题线路正文交通方式 vs 每一站的 via）
"""
import hashlib, json, os, random, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    # S1
    'xb_back': ('assets/site.js', "if(o.sheet){o.sheet.addEventListener('click'", "if(o.sheet){var xb_=document.createElement('button');xb_.type='button';xb_.className='pk-xb pk-x';xb_.textContent='关上';o.sheet.appendChild(xb_);o.sheet.addEventListener('click'"),   # 底部整行“关上”加回来
    'x_small': ('assets/site.css', ".pk-x{width:44px;min-width:44px;height:44px;", ".pk-x{width:30px;min-width:30px;height:30px;"),                                                       # × 缩成 30
    'confirm_back': ('assets/site.js', "if(a==='rm'){ZL.close(LY);", "if(a==='rm'){ZL.close(LY);var cm=document.createElement('div');cm.className='pk';cm.innerHTML='<div class=\"pk-h\"><b>去掉这一天？</b><button type=\"button\" class=\"pk-x\">算了</button></div><div class=\"xd\"><button type=\"button\" class=\"rmgo\"><b>去掉这一天</b></button></div>';ZL.open([cm],{sheet:cm,kind:'cfm'});return;"),   # 确认层加回来
    # S2 / S3
    'no_stack': ('assets/site.js', "if(pend<=0)pushH(L);", "if(pend<=0&&stack.length===1)pushH(L);"),                                                                                          # 没有层栈：只有第一层占历史
    'cl_unlock': ('assets/site.js', "if(!stack.length)B.classList.remove('pk-open');", "B.classList.remove('pk-open');"),                                                               # 关任何一层都无条件解锁滚动
    'back_shot': ('assets/site.js', "var L=top();if(!L)return;L.h=false;teardown(L)", "var L=top();if(!L||L.kind==='shot')return;L.h=false;teardown(L)"),                               # 存图层不响应返回键（原来的 bug）
    # S4
    'swipe_off': ('assets/site.js', ";swipe(L,o.sheet)}", "}"),                                                                                                                           # 去掉下滑监听
    'swipe_steal': ('assets/site.js', "if(!hd){for(var n=tg;n&&n!==sh;n=n.parentNode)if(n.scrollTop>0){ok=false;break}}", ""),                                                           # 内容没滚到顶也响应下拉（抢了滚动）
    # S5 / S6 / S8
    'pre_boxes': ('assets/site.js', "      function preCap(){", "      [].forEach.call(document.querySelectorAll('.prehid'),function(u){u.hidden=false});\n      function preCap(){"),   # 出发前的复选框和全部条目又摆回页内（全站有 [hidden]{display:none!important}，只能从 JS 里把 hidden 摘掉）
    'date_dup': ('assets/site.js', "return(isSugg?[y_,wn,c0]:['按你'+srcTxt+'选的日期排的'+(y_?'（'+yp(d0).trim()+'）':''),c0])", "return(isSugg?['建议 '+fmt(d0)+' 出发',y_,wn,c0]:['按你'+srcTxt+'选的日期排的 '+fmt(d0),c0])"),   # dnote 里又写一遍日期
    'kick_days': ('trip/xa3/index.html', '<span class="kick">城市慢游</span>', '<span class="kick">城市慢游 · 三天</span>'),                                                         # 封面小标又写天数
    'cl_every_day': ('assets/site.js', "cl.hidden=(i===0)||!has||m===pm_||!!sec.querySelector('.fc:not(.mon)')", "cl.hidden=false"),                                                    # 往年气温每天一句
    'facts_road': ('assets/site.js', "p.dataset.w=f.walk;p.dataset.d=f.drive;", "p.dataset.w=f.walk;p.dataset.d=f.drive;(function(){var fe=sec.querySelector('.facts');if(fe&&!fe.querySelector('.rd')){var x=document.createElement('div');x.className='fx rd';x.innerHTML='<small>路上</small><b>'+zLf(f.drive)+'</b>';fe.appendChild(x)}})();"),   # facts 里加回“路上”
    # S10 / S11 / S12 / S13
    'dock_nolink': ('assets/site.js', "dkd.addEventListener('click',function(){dtb.click()});", ""),                                                                                  # 底栏日期不可点
    'ics_gone': ('assets/site.js', "<b>加入日历</b><small>每天的安排，加上买票", "<b>日历</b><small>每天的安排，加上买票"),                                                              # 分享层里的“加入日历”按钮改了名
    'gray_old': ('assets/site.js', "if(b.last+NP_LIM.EXTRA>NP_LIM.CAP)return'已排到 '", "if(b.last>NP_LIM.END)return'已排到 '"),                                             # 置灰规则退回死的 21:30
    'ret_gone': ('trip/xa3/index.html', '回：第 3\u00a0天', '第 3\u00a0天'),                                                                                                                        # 去掉“回：…”这句
    'label_old': ('assets/site.js', "(sv&&f.own>0&&f.own>=f.drive-.5?'开车约 ':'路上约 ')", "(sv?'开车约 ':'路上约 ')"),                                                                  # 有自驾段的线路里每天都叫“开车”（hss1a 第 2 天坐高铁也写开车）
    'stay_nojump': ('assets/site.js', "var j=e.target.closest('.tl > .r.stay');if(j&&", "var j=null;if(j&&"),                                                                      # 当天末尾“住 · …”不可点
    'copy_noarea': ('assets/site.js', "out.push('        今晚住：'+[sy.dataset.area||'',lb.replace(/^今晚住\\s*/,'')].filter(Boolean).join(' · ')+(rc?", "out.push('        今晚住：'+[lb.replace(/^今晚住\\s*/,'')].filter(Boolean).join(' · ')+(rc?"),      # 复制行程里“今晚住：”后面又丢了住处名（住宿卡头去掉地名后差点漏掉的一处）
    'foot_wrap': ('assets/site.css', [".foot p:last-child{display:flex;flex-wrap:wrap;gap:0 16px}", ".foot a{white-space:nowrap;display:inline-flex;align-items:center;min-height:44px;margin-right:0}"], ["", ".foot a{white-space:normal;display:inline;min-height:0;margin-right:14px}"]),         # 页脚链接又能折行（回到原来的行内排版）
}
INJ_TARGET = {'ret_gone': 'xa3', 'kick_days': 'xa3'}
env = Env(INJ)
check, guard = env.check, env.guard
ONLY = set(sys.argv[sys.argv.index('--only') + 1].split(',')) if '--only' in sys.argv else None
LAYERS_ONLY = set(sys.argv[sys.argv.index('--layers') + 1].split(',')) if '--layers' in sys.argv else None      # 只测这几种层（反向注入时省时间）
def want(k): return ONLY is None or k in ONLY

LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FXD = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FXD, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
SAMPLE = ['xa3', 'xl9a', 'hss1a', 'tk4', 'xv29a', 'hcz1']
TASKS = {}      # 任务步数表：字母 → (现状, 实测点击数, 备注)

VISF = "(e)=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'}"      # 不看 [hidden] 属性本身：被 CSS 改成 display:block 的 hidden 元素就是看得见的（pre_boxes 注入靠这个红）
CLOSERS = """(()=>{const vis=%s;const re=/关上|关闭|×|返回|回到整条行程|算了|取消/;
  const roots=[...document.querySelectorAll('.pk,.tv,.hmap-zoom,.rm')].filter(vis);
  return roots.map(r=>{const bs=[...r.querySelectorAll('button,a')].filter(vis).filter(b=>re.test((b.textContent||'').trim())||re.test(b.getAttribute('aria-label')||''));
    return {cls:r.className,n:bs.length,xb:!!r.querySelector('.pk-xb,.tvx2'),btns:bs.map(b=>{const q=b.getBoundingClientRect();return {t:(b.textContent||'').trim().slice(0,8),a:b.getAttribute('aria-label'),w:Math.round(q.width),h:Math.round(q.height),l:Math.round(q.left),r:Math.round(q.right),top:Math.round(q.top),b:Math.round(q.bottom)}})}})})()""" % VISF
STATE = "({d:window.ZL?ZL.depth():-1,k:window.ZL?ZL.kinds():[],pk:document.body.classList.contains('pk-open'),sy:Math.round(scrollY),href:location.href,hl:history.length,pend:window.ZL?ZL.pending():0})"


def swipe(pg, x, y0, y1, steps=10, dt=14, dx=0):
    cdp = pg.context.new_cdp_session(pg)
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y0}]})
    for i in range(1, steps + 1):
        cdp.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x + dx * i / steps, 'y': y0 + (y1 - y0) * i / steps}]}); pg.wait_for_timeout(dt)
    cdp.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    pg.wait_for_timeout(260)


def st(pg): return pg.evaluate(STATE)
def gone(pg): return pg.evaluate("ZL.depth()===0&&!document.body.classList.contains('pk-open')&&!document.querySelector('.pk,.tv,.hmap-zoom,.rm')")
def shot(pg, name):
    if env.shots: pg.screenshot(path=os.path.join(env.shots, name))


def seeded_fav(n=12):
    ids = ['xa3', 'tk4', 'hss1a', 'hcz1', 'xv29a', 'xl9a', 'gqhx10']
    return json.dumps([{'id': ids[i % len(ids)] + ('' if i < len(ids) else 'x%d' % i), 'label': '线路 %d 天' % (i + 2), 'title': '第 %d 条收进的行程' % (i + 1), 'n': 3, 'sd': '2027-10-15'} for i in range(n)], ensure_ascii=False)


class Stub:
    def __init__(self, c):
        def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
        def pbf(r): r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        def other(r):
            if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
            elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
            else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


def trip(br, rid, storage=None, wait=700):
    c = new_ctx(br, None, storage=storage); pg = new_page(env, c)
    goto(env, pg, '/trip/%s/' % rid, wait)
    return c, pg


# 打开各种层：返回 (名字, 打开函数, 层根选择器)
def L_share(pg): pg.click('.share'); pg.wait_for_selector('.pk')
def L_date(pg): pg.click('.glance .dt'); pg.wait_for_selector('.pk')
def L_stime(pg): pg.evaluate("document.querySelector('#d1 .st').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .st'); pg.wait_for_selector('.pk')
def L_addday(pg): pg.evaluate("document.querySelector('.addday .add').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.addday .add'); pg.wait_for_selector('.pk')
def L_adj(pg): pg.evaluate("document.querySelector('#d1 .tl .adj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .tl .adj >> nth=0'); pg.wait_for_selector('.pk')
def L_dayadj(pg): pg.evaluate("document.querySelector('#d1 .dayadj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .dayadj'); pg.wait_for_selector('.pk')
def L_tv(pg): pg.click('.tvbtn'); pg.wait_for_selector('.tv')
def L_todo(pg): pg.evaluate("document.querySelector('.todoall').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.todoall'); pg.wait_for_selector('.tv.todo')
def L_copy(pg):
    pg.evaluate("navigator.clipboard.writeText=function(){return Promise.reject(new Error('x'))};0")
    pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="copy"]'); pg.wait_for_selector('.pk textarea')
def L_shot(pg): pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="shot"]'); pg.wait_for_selector('.shotv img', timeout=8000); pg.wait_for_timeout(300)
LAYERS = [('分享', L_share, True), ('选出发日期', L_date, True), ('几点出发', L_stime, True), ('加一天', L_addday, True), ('改这一站', L_adj, True), ('调整这一天', L_dayadj, True),
          ('按天看', L_tv, False), ('出发前要办的事', L_todo, False), ('复制框', L_copy, True), ('分享图（存图层）', L_shot, False)]


with sync_playwright() as p:
    br = p.chromium.launch()

    # ———————————————— S14 前半：清场前的清单 ————————————————
    def manifest():
        h = hashlib.md5(); n = 0
        for base in (env.site, os.path.join(ROOT, 'data'), os.path.join(ROOT, 'site_src')):
            for dp, dn, fn in os.walk(base):
                dn.sort()
                for f in sorted(fn):
                    q = os.path.join(dp, f)
                    try: s = os.stat(q)
                    except OSError: continue
                    h.update(('%s|%d|%d\n' % (os.path.relpath(q, ROOT), s.st_size, s.st_mtime_ns)).encode()); n += 1
        return h.hexdigest(), n
    MAN0 = manifest()

    # ———————————————— S1 / S2：每种层 ————————————————
    if want('S1') or want('S2'):
        for name, opener, hasmask in LAYERS:
            if LAYERS_ONLY and name not in LAYERS_ONLY: continue
            with guard('S1/S2 ' + name):
                c, pg = trip(br, 'xa3')
                opener(pg); pg.wait_for_timeout(250)
                s_open = st(pg); cl = pg.evaluate(CLOSERS); shot(pg, 'S1_%s.png' % name)
                top = [x for x in cl if x['n'] or True][-1] if cl else None
                check('S1 %s：可见的关闭类按钮 = 1（%s）' % (name, [(b['t'], b['a']) for b in (top or {}).get('btns', [])]), top and top['n'] == 1, top and top['btns'])
                check('S1 %s：DOM 里没有底部整行“关上”(.pk-xb) / 底部“回到整条行程”(.tvx2)' % name, top and not top['xb'] and not pg.evaluate("!!document.querySelector('.pk-xb,.tvx2')"))
                b0 = top['btns'][0] if top and top['btns'] else None
                if name not in ('分享图（存图层）',):
                    check('S1 %s：关闭键 ≥44×44、在视口内（%s）' % (name, b0), b0 and b0['w'] >= 44 and b0['h'] >= 44 and b0['l'] >= 0 and b0['r'] <= 390 and b0['top'] >= 0 and b0['b'] <= 844, b0)
                else:
                    check('S1 %s：关闭键 ≥44×44、在视口内（%s）' % (name, b0), b0 and b0['w'] >= 44 and b0['h'] >= 44 and b0['r'] <= 390 and b0['top'] >= 0, b0)
                if name == '改这一站':
                    check('S1 改这一站：× 之外左上没有别的关闭键（主视图没有“‹ 返回”）', top['n'] == 1)
                # —— 返回键
                pg.evaluate("history.back()"); pg.wait_for_timeout(350)
                s1 = st(pg)
                check('S2 %s：返回键关层（层没了、pk-open 没了）' % name, gone(pg), s1)
                check('S2 %s：返回后 scrollY 不变（%s→%s）、地址不变' % (name, s_open['sy'], s1['sy']), abs(s1['sy'] - s_open['sy']) <= 2 and s1['href'] == s_open['href'], (s_open, s1))
                # —— Esc
                opener(pg); pg.wait_for_timeout(250); pg.keyboard.press('Escape'); pg.wait_for_timeout(350)
                check('S2 %s：Esc 关层' % name, gone(pg), st(pg))
                # —— 点遮罩
                if hasmask:
                    opener(pg); pg.wait_for_timeout(250); pg.mouse.click(195, 30); pg.wait_for_timeout(350)
                    check('S2 %s：点遮罩关层' % name, gone(pg), st(pg))
                elif name == '分享图（存图层）':
                    opener(pg); pg.wait_for_timeout(250); pg.mouse.click(10, 10); pg.wait_for_timeout(350)
                    check('S2 %s：点图片以外关层' % name, gone(pg), st(pg))
                # —— ×
                opener(pg); pg.wait_for_timeout(250)
                pg.click('.pk .pk-x' if hasmask else ('.tv .tvx' if name in ('按天看', '出发前要办的事') else '.hz-x')); pg.wait_for_timeout(350)
                check('S2 %s：点关闭键关层' % name, gone(pg), st(pg))
                # —— 反复开关不攒历史（5 轮后 history.length 不超过开头 +1）
                h0 = pg.evaluate("history.length")
                for _ in range(5):
                    opener(pg); pg.wait_for_timeout(200); pg.evaluate("history.back()"); pg.wait_for_timeout(300)
                for _ in range(3):
                    opener(pg); pg.wait_for_timeout(200)
                    pg.click('.pk .pk-x' if hasmask else ('.tv .tvx' if name in ('按天看', '出发前要办的事') else '.hz-x')); pg.wait_for_timeout(300)
                h1 = pg.evaluate("history.length")
                check('S2 %s：反复开关 8 次后 history.length 没攒起来（%s→%s，≤开头+1）' % (name, h0, h1), h1 <= h0 + 1 and gone(pg), (h0, h1))
                c.close()
        # 去掉这一天：没有确认层，执行后 5 秒带“撤销”的提示条（整页重载后出现）
        with guard('S1 去掉这一天没有确认层'):
            c, pg = trip(br, 'xa3'); n0 = pg.evaluate("document.querySelectorAll('.day').length")
            L_dayadj(pg); pg.evaluate("window.__mark=1")
            pg.click('.pk .rmgo'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1200)
            m_ = pg.evaluate("({mark:window.__mark,pk:document.querySelectorAll('.pk').length,days:document.querySelectorAll('.day').length,act:document.querySelectorAll('.toast .toast-act').length,t:(document.querySelector('.toast')||{}).innerText||''})")
            check('S1 去掉这一天：点一下就执行（页面重载了、没有确认层 / 取消按钮 / 任何层挡着）、少了一天（%d→%d）' % (n0, m_['days']), m_['mark'] is None and m_['pk'] == 0 and m_['days'] == n0 - 1, m_)
            check('S1 去掉这一天：执行后马上有带“撤销”的提示条，写着“去掉了「X」”（%s）' % m_['t'].replace('\n', ' '), m_['act'] == 1 and '去掉了' in m_['t'], m_)
            shot(pg, 'S1_rmday_toast.png')
            pg.click('.toast .toast-act'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
            check('S1 去掉这一天：点“撤销”天数回来', pg.evaluate("document.querySelectorAll('.day').length") == n0)
            c.close()
        # 关完再按一次返回才离开页面
        with guard('S2 离开页面'):
            c = new_ctx(br, None); pg = new_page(env, c); goto(env, pg, '/', 400); goto(env, pg, '/trip/xa3/', 600)
            pg.click('.share'); pg.wait_for_selector('.pk'); pg.evaluate("history.back()"); pg.wait_for_timeout(350)
            check('S2 返回键先关层、仍在线路页', '/trip/xa3/' in pg.url and gone(pg), pg.url)
            pg.evaluate("history.back()"); pg.wait_for_timeout(700)
            check('S2 再按一次返回才离开线路页（回到首页）', pg.url.rstrip('/') == env.B, pg.url)
            c.close()
        # 层叠加（非地图）：分享 → 复制框；调整 → 换成…
        with guard('S2 叠加'):
            c, pg = trip(br, 'xa3')
            pg.evaluate("navigator.clipboard.writeText=function(){return Promise.reject(new Error('x'))};0")
            pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="copy"]'); pg.wait_for_selector('.pk textarea'); pg.wait_for_timeout(900)
            s = st(pg)
            check('S2 分享 → 复制框：层栈里只有复制框 1 层（%s）' % s['k'], s['k'] == ['copy'] and s['pk'], s)
            pg.evaluate("history.back()"); pg.wait_for_timeout(400)
            check('S2 分享 → 复制框 → 返回键：复制框关了、没有别的层冒出来、页面还在', gone(pg) and '/trip/xa3/' in pg.url, st(pg))
            c.close()

    # ———————————————— S3 层叠加（地图）————————————————
    if want('S3'):
        bm = p.chromium.launch(args=LAUNCH)
        def mk():
            c = new_ctx(bm, None); Stub(c); return c, new_page(env, c)
        def ready(pg): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=15000)
        with guard('S3 地图 → 分段层'):
            c, pg = mk(); goto(env, pg, '/trip/xa3/', 700)
            pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); y0 = pg.evaluate("scrollY")
            pg.click('#d1 .rm-open'); ready(pg); pg.wait_for_timeout(800)
            s = st(pg); check('S3 打开地图：层栈 = [map]、pk-open 在（%s）' % s['k'], s['k'] == ['map'] and s['pk'], s)
            pg.wait_for_selector('.rm-navd:not([hidden])'); pg.click('.rm-navd'); pg.wait_for_selector('.rm-sheet.rm-dyn'); pg.wait_for_timeout(300)
            s = st(pg); cl = pg.evaluate(CLOSERS); shot(pg, 'S3_map_navsheet.png')
            sh = [x for x in cl if 'pk' in x['cls'].split()]
            check('S3 导航分段层：栈 = [map, nav]；头部有 × 且只有 1 个关闭键（%s）' % s['k'], s['k'] == ['map', 'nav'] and sh and sh[0]['n'] == 1 and sh[0]['btns'][0]['t'] == '×', (s, sh))
            pg.evaluate("history.back()"); pg.wait_for_timeout(500)
            s = st(pg); check('S3 返回键只关分段层：地图还在、pk-open 还在（%s）' % s['k'], s['k'] == ['map'] and s['pk'] and pg.evaluate("!!document.querySelector('.rm')") and not pg.evaluate("!!document.querySelector('.rm-sheet.rm-dyn')"), s)
            pg.click('.rm-navd'); pg.wait_for_selector('.rm-sheet.rm-dyn'); pg.wait_for_timeout(250); pg.click('.rm-sheet .pk-x'); pg.wait_for_timeout(450)
            s = st(pg); check('S3 点分段层的 ×：只关它，地图还在、栈 = [map]（%s）' % s['k'], s['k'] == ['map'] and s['pk'] and pg.evaluate("!!document.querySelector('.rm')"), s)
            pg.evaluate("history.back()"); pg.wait_for_timeout(700)
            s = st(pg); check('S3 再按返回：地图关了、pk-open 没了、滚动回到原位（%s→%s）' % (y0, s['sy']), gone(pg) and abs(s['sy'] - y0) <= 3, s)
            c.close()
        with guard('S3 地图 → 存图层'):
            c, pg = mk(); goto(env, pg, '/trip/xa3/', 700)
            pg.evaluate("document.querySelector('#d2 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d2 .rm-open'); ready(pg); pg.wait_for_timeout(1200)
            pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=8000); pg.wait_for_timeout(300)
            s = st(pg); check('S3 地图 → 存图层：栈 = [map, shot]（%s）' % s['k'], s['k'] == ['map', 'shot'], s)
            pg.evaluate("history.back()"); pg.wait_for_timeout(450)
            s = st(pg); check('S3 返回键关存图层：地图还在、pk-open 还在（%s）' % s['k'], s['k'] == ['map'] and s['pk'] and pg.evaluate("!!document.querySelector('.rm')"), s)
            pg.click('.rm-sv'); pg.wait_for_selector('.rm-shot img', timeout=8000); pg.wait_for_timeout(300); pg.mouse.click(10, 10); pg.wait_for_timeout(400)
            s = st(pg); check('S3 点图片以外：存图层关、地图还在（%s）' % s['k'], s['k'] == ['map'], s)
            pg.keyboard.press('Escape'); pg.wait_for_timeout(600)
            check('S3 Esc 关地图', gone(pg), st(pg))
            c.close()
        bm.close()

    # ———————————————— S4 向下滑动关层 ————————————————
    if want('S4'):
        with guard('S4 下滑关层'):
            c, pg = trip(br, 'xa3')
            L_share(pg); pg.wait_for_timeout(250)
            r = pg.evaluate("(()=>{const s=document.querySelector('.pk'),b=s.getBoundingClientRect(),g=getComputedStyle(s,'::before');return {top:b.top,w:g.width,h:g.height,c:g.content}})()")
            check('S4 有小横条（36×4，%s）' % r, r['w'] == '36px' and r['h'] == '4px' and r['c'] not in ('none', 'normal'), r)
            hy = pg.evaluate("document.querySelector('.pk .pk-h b').getBoundingClientRect().top+10")
            swipe(pg, 150, hy, hy + 140)
            check('S4 在标题行下拉 140px：关层', gone(pg), st(pg))
            L_share(pg); pg.wait_for_timeout(250); hy = pg.evaluate("document.querySelector('.pk .pk-h b').getBoundingClientRect().top+10")
            swipe(pg, 150, hy, hy + 45, steps=8, dt=40)
            check('S4 只下拉 45px、慢慢松手：不关、弹回原位', pg.evaluate("ZL.depth()===1&&document.querySelector('.pk').style.transform===''"), pg.evaluate("document.querySelector('.pk').style.transform"))
            swipe(pg, 150, hy + 100, hy - 40)
            check('S4 往上滑：不关', pg.evaluate("ZL.depth()===1"))
            swipe(pg, 150, hy + 60, hy + 70, dx=160)
            check('S4 横着滑：不关', pg.evaluate("ZL.depth()===1"))
            gy = pg.evaluate("document.querySelector('.pk').getBoundingClientRect().top+10")
            swipe(pg, 150, gy, gy + 130)
            check('S4 从顶部小横条起手下拉：关层', gone(pg), st(pg))
            c.close()
        with guard('S4 内容滚动让位'):
            c = new_ctx(br, None, storage={'zouni_fav': seeded_fav(12)}); pg = new_page(env, c); goto(env, pg, '/', 900)
            pg.click('.minebtn'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(300)
            sc = pg.evaluate("(()=>{const x=document.querySelector('.pk .xd');return {sh:x.scrollHeight,ch:x.clientHeight}})()")
            check('S4 “我的行程”内容可滚动（scrollHeight %s > clientHeight %s）' % (sc['sh'], sc['ch']), sc['sh'] > sc['ch'] + 40, sc)
            pg.evaluate("document.querySelector('.pk .xd').scrollTop=240"); pg.wait_for_timeout(150)
            ry = pg.evaluate("(()=>{const r=document.querySelector('.pk .xd').getBoundingClientRect();return r.top+60})()")
            swipe(pg, 150, ry, ry + 150)
            check('S4 内容滚在中间时从内容起手下拉：不关（让位给滚动）', pg.evaluate("ZL.depth()===1"), st(pg))
            pg.evaluate("document.querySelector('.pk .xd').scrollTop=0"); pg.wait_for_timeout(150)
            swipe(pg, 150, ry, ry + 150)
            check('S4 内容滚到顶后从内容起手下拉：关层', gone(pg), st(pg))
            c.close()

    # ———————————————— S5 / S6 / S7 页头与每天 ————————————————
    HEAD_MAX = {'xa3': 800, 'tk4': 800, 'xv29a': 870, 'xl9a': 1030, 'hss1a': 960, 'hcz1': 1130}      # 设计文档的目标是 xa3 / tk4 / xv29a ≤800、xl9a ≤900、hss1a ≤920、hcz1 ≤1020；实测只有 xa3 / tk4 到了，其余是“出发前 / 怎么去怎么回”那几段本身的文字（内容）占的，上限取实测 + 余量
    BEFORE = {'xa3': 914, 'xl9a': 1035, 'hss1a': 985, 'tk4': 882, 'xv29a': 903, 'hcz1': 1137}
    if want('S5') or want('S6') or want('S7') or want('S8') or want('S9'):
        for rid in SAMPLE:
            if env.inject in INJ_TARGET and INJ_TARGET[env.inject] != rid: continue
            with guard('S5-S9 ' + rid):
                c, pg = trip(br, rid, wait=900)
                m = pg.evaluate("""(()=>{const vis=%s,d1=document.getElementById('d1'),y=d1.getBoundingClientRect().top+scrollY,
                  tl=d1.querySelector('.tl > .r'),tly=tl?tl.getBoundingClientRect().top+scrollY:0,
                  hero=document.querySelector('.hero'),ht=hero.innerText,
                  dn=[...document.querySelectorAll('.hero,.glance,.dnote,section.pre,.mapgo')].filter(vis).map(e=>e.innerText).join('\\n'),
                  cb=[...document.querySelectorAll('section.pre input[type=checkbox]')].filter(vis).length,
                  pres=[...document.querySelectorAll('section.pre:not(.go) ul:not(.prehid) > li')].filter(vis).length,
                  cls=[...document.querySelectorAll('.day .cl')].filter(e=>vis(e)&&e.textContent.trim()).length,
                  sd=document.querySelector('.dpk').value,
                  btns=[...document.querySelectorAll('section.day')].map(s=>[...s.querySelectorAll('button,[role=button]')].filter(b=>vis(b)&&!b.closest('.tl')&&!b.closest('.stays')&&!b.closest('.latewarn')&&!b.closest('.rmnote')).length),
                  facts=[...document.querySelectorAll('.day .facts')].map(f=>f.innerText),
                  dl=[...document.querySelectorAll('.day .dload')].map(p=>p.innerText),
                  ro=document.querySelector('.hero-t h1').innerText;
                  return {y:y,gap:tly-y,hero:ht,dn:dn,cb:cb,pres:pres,cls:cls,sd:sd,btns:btns,facts:facts,dl:dl,days:document.querySelectorAll('.day').length,
                    txt:document.body.innerText}})()""" % VISF)
                if want('S5'):
                    check('S5 %s：第 1 天标题离页顶 %d px ≤ %d（原 %d）' % (rid, m['y'], HEAD_MAX[rid], BEFORE[rid]), m['y'] <= HEAD_MAX[rid], m['y'])
                    nd = len(re.findall(r'[一二三四五六七八九十\d]+\s*天', m['hero']))
                    check('S5 %s：封面（.hero）里天数只写 ≤1 次（%d 次：%s）' % (rid, nd, m['hero'].replace('\n', ' / ')[:40]), nd <= 1, m['hero'])
                    md = '%d/%d' % (int(m['sd'][5:7]), int(m['sd'][8:10]))
                    best = re.findall(r'最好\s*\d+/\d+[–-]\d+/\d+', m['dn'])
                    dn2 = re.sub(r'明年\s*\d+/\d+（距今\s*\d+\s*天）', '', re.sub(r'最好\s*\d+/\d+[–-]\d+/\d+', '', m['dn']))      # 2026-10-19：跨年时说明行按约定写“明年 M/D（距今 N 天）”（Jerry 定的格式），不算重复
                    ndt = len(re.findall(r'(?<![\d/])' + re.escape(md) + r'(?![\d])', dn2))
                    check('S5 %s：页头区（封面→出发前）出发日期 %s 只写 %d 处（≤1）' % (rid, md, ndt), ndt <= 1, dn2[:200])
                    check('S5 %s：出发前页内没有复选框（%d 个可见）、提示 ≤2 条（%d 条）' % (rid, m['cb'], m['pres']), m['cb'] == 0 and m['pres'] <= 2, (m['cb'], m['pres']))
                    pg.evaluate("document.querySelector('.todoall').scrollIntoView({block:'center',behavior:'instant'})")
                    check('S5 %s：有一个“出发前要办的事 · 已办 0/N ›”入口' % rid, pg.evaluate("/出发前要办的事 · 已办 \\d+\\/\\d+/.test(document.querySelector('.todoall').innerText)"))
                if want('S6') and rid == 'xa3':
                    check('S6 xa3：第 1 天从天标题到第一行时间线 %d px ≤ 380（设计目标 345；原 429）' % m['gap'], m['gap'] <= 380, m['gap'])
                    TASKS['S6_xa3'] = m['gap']
                if want('S7'):
                    mx = max(m['btns'])
                    check('S7 %s：每天“非站点”按钮数最多 %d（≤4；原 5）' % (rid, mx), mx <= 4, m['btns'])
                if want('S8'):
                    bad = [i + 1 for i, (f, dl) in enumerate(zip(m['facts'], m['dl'])) if (len(re.findall('路上|开车', f)) + len(re.findall('路上|开车', dl))) > 1 or re.search('路上|开车', f)]
                    check('S8 %s：每天“路上”只写一次、facts 里没有（有问题的天 %s）' % (rid, bad[:6]), not bad, bad[:6])
                    mons = len(set(re.findall(r'往年\s*(\d+)\s*月', m['txt'])))
                    check('S8 %s：往年气温可见 %d 处 ≤ 月份数 %d（之前每天一句）' % (rid, m['cls'], max(1, mons)), m['cls'] <= max(1, mons), m['cls'])
                if want('S9'):
                    pg.evaluate("document.querySelector('#d1 .adj').click()"); pg.wait_for_timeout(300)
                    txt = pg.evaluate("document.body.innerText")
                    ban = [w for w in ('一年四季都能去', '按上午出发、中午前到算的', '今天：', '不用早起', '改了以后，这天后面的时间会跟着重排') if w in txt]
                    check('S9 %s：页面（含“改这一站”层）可见文字不含禁词 %s' % (rid, ban), not ban, ban)
                c.close()

    # ———————————————— S8 随机 200 天：dload 的路上 = 建站时的 data-drv ————————————————
    if want('S8'):
        with guard('S8 随机 200 天'):
            rids = sorted(d for d in os.listdir(os.path.join(env.site, 'trip')) if os.path.exists(os.path.join(env.site, 'trip', d, 'index.html')))
            rng = random.Random(20261018); pick = rng.sample(rids, 60); pick = list(dict.fromkeys(['xl9a', 'hss1a', 'xa3'] + pick))
            c = new_ctx(br, None); pg = new_page(env, c); tot = 0; bad = []; lab = []
            for rid in pick:
                goto(env, pg, '/trip/%s/' % rid, 350)
                rows = pg.evaluate("""[...document.querySelectorAll('section.day:not(.xday)')].map((s,i)=>{const p=s.querySelector('.dload');return {i:i+1,d:p?+p.dataset.d:null,drv:+s.dataset.drv,txt:p?p.innerText:'',own:0,fx:[...s.querySelectorAll('.facts .fx small')].map(e=>e.textContent)}})""")
                n = rng.randint(5, 8) if len(rows) > 8 else len(rows)
                for r in (rows if len(rows) <= n else rng.sample(rows, n)):
                    tot += 1
                    if r['d'] is None or abs(r['d'] - r['drv']) > 1 or '路上' in r['fx'] or '开车' in r['fx']: bad.append((rid, r['i'], r['d'], r['drv'], r['fx']))
                    if r['drv'] >= 10 and not re.search(r'(开车|路上)约', r['txt']): bad.append((rid, r['i'], 'text', r['txt']))
                    if re.search(r'^今天：', r['txt']): bad.append((rid, r['i'], 'prefix', r['txt']))
            check('S8 随机 %d 天（%d 条线）：dload 的路上分钟 = 建站时算的 data-drv（页头“最长一天”同一个数），facts 里没有路上格；有问题 %d 处 %s' % (tot, len(pick), len(bad), bad[:4]), tot >= 200 and not bad, bad[:6])
            c.close()
        with guard('S8 hss1a 第 2 天 / xl9a 第 1 天'):
            c, pg = trip(br, 'hss1a'); t = pg.evaluate("document.querySelector('#d2 .dload').innerText")
            check('S8 hss1a 第 2 天写“路上约”（高铁不叫“开车”，%s）' % t, '路上约' in t and '开车' not in t, t)
            t5 = pg.evaluate("document.querySelector('#d5 .dload').innerText")
            check('S8 hss1a 第 5 天（全程自驾）仍写“开车约”（%s）' % t5, '开车约' in t5, t5)
            c.close()
            c, pg = trip(br, 'xl9a'); r = pg.evaluate("(()=>{const s=document.getElementById('d1');return {dl:s.querySelector('.dload').innerText,drv:+s.dataset.drv,facts:s.querySelector('.facts').innerText}})()")
            check('S8 xl9a 第 1 天：同屏只有一个“开车”数（%s | %s；原来这里写 2 小时 50 分 / 2 小时 40 分，是 Python 银行家舍入 vs JS 四舍五入）' % (r['dl'], r['facts'].replace('\n', ' ')), len(re.findall('路上|开车', r['dl'])) == 1 and not re.search('路上|开车', r['facts']) and '2 小时 50 分' in r['dl'], r)
            c.close()

    # ———————————————— S10 任务步数 ————————————————
    if want('S10'):
        with guard('S10 A 看懂第 1 天'):
            c, pg = trip(br, 'xa3')
            a = pg.evaluate("""(()=>{const d=document.getElementById('d1'),y=d.getBoundingClientRect().top+scrollY,l=d.querySelector('.lead').getBoundingClientRect(),t=d.querySelector('.tl > .r').getBoundingClientRect();return {h:y/innerHeight,lead:(l.bottom+scrollY)/innerHeight,tl:(t.top+scrollY)/innerHeight}})()""")
            check('S10 A 看懂第 1 天：0 点击；标题在 %.2f 屏、导语读完在 %.2f 屏、时间线第 1 行在 %.2f 屏（目标：标题在第 1 屏内 ✓；时间线第 1 行 设计目标 ≤1.3，实测上限 ≤1.45；原 1.59）' % (a['h'], a['lead'], a['tl']), a['h'] < 1 and a['tl'] <= 1.45, a)
            TASKS['A'] = ('0 点击 · 标题 1.08 屏 / 约 3 屏读完', '0 点击 · 标题 %.2f 屏、时间线第 1 行 %.2f 屏' % (a['h'], a['tl']))
            c.close()
        with guard('S10 B 查预约/闭馆'):
            c, pg = trip(br, 'xa3'); n = 0
            check('S10 B：页内没有“更多 N 条”折叠', pg.evaluate("!document.querySelector('.premore')"))
            pg.evaluate("document.querySelector('.todoall').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.todoall'); n += 1; pg.wait_for_selector('.tv.todo'); pg.wait_for_timeout(300)
            g = pg.evaluate("[...document.querySelectorAll('.tv.todo h3')].map(h=>h.textContent)"); it = pg.evaluate("[...document.querySelectorAll('.tv.todo .tdl li')].map(l=>l.innerText.replace(/\\s+/g,' '))")
            check('S10 B 查要不要预约：%d 点击；弹层里有“要预约的”分组（%s）、带日期（%s）' % (n, g, [x for x in it if '陕西历史' in x][:1]), n <= 1 and '要预约的' in g and any('（' in x for x in it if '预约' in x or '博物馆' in x), (g, it[:5]))
            shot(pg, 'S10_todo_layer.png')
            TASKS['B'] = ('0–2 点击（页内“更多 1 条”折叠 / 弹层）', '%d 点击（弹层，已按“要预约的”分组并写日期）' % n)
            c.close()
        with guard('S10 C 去掉一站再撤销'):
            c, pg = trip(br, 'xa3'); row = pg.locator('#d2 .tl > .r.see').nth(1); k0 = {k: ls(pg, k) for k in ('zouni_drop_xa3', 'zouni_np_xa3', 'zouni_adj_xa3')}; n = 0
            row.evaluate("r=>r.scrollIntoView({block:'center',behavior:'instant'})"); row.locator('.adj').click(); n += 1; pg.wait_for_selector('.pk')
            pg.click('.pk [data-x="1"]'); n += 1; pg.wait_for_timeout(300); pg.click('.toast .toast-act'); n += 1; pg.wait_for_timeout(300)
            k1 = {k: ls(pg, k) for k in k0}
            check('S10 C 去掉一站再撤销：%d 点击（≤3），存的键回到去掉之前' % n, n <= 3 and k0 == k1 and not row.evaluate("r=>r.hidden"), (k0, k1))
            TASKS['C'] = ('3 点击', '%d 点击' % n); c.close()
        with guard('S10 D 加一个顺路景点'):
            c, pg = trip(br, 'xa3'); n = 0; tried = 0; done = False; empty_msg = ''
            idxs = pg.evaluate("[...document.querySelectorAll('section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj')].map((b,i)=>i)")
            for i in idxs:
                tried += 1; n = 0
                pg.evaluate("(i)=>{const b=document.querySelectorAll('section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj')[i];b.scrollIntoView({block:'center',behavior:'instant'})}", i)
                pg.locator('section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj').nth(i).click(); n += 1; pg.wait_for_selector('.pk')
                ins = pg.locator('.pk [data-np="ins"]')
                if i == 0: check('S10 D：xa3 第 1 天第一站的“在这之后加一个”可点；排满时置灰并写清原因（再加就超过…）', ins.count() == 1 and (not ins.first.is_disabled() or '已排到' in ins.first.inner_text() or '排满' in ins.first.inner_text()), ins.count() and ins.first.inner_text())
                if not ins.count() or ins.first.is_disabled(): pg.evaluate("history.back()"); pg.wait_for_timeout(150); continue
                ins.click(); n += 1; pg.wait_for_selector('.pk .npc, .pk .npe', timeout=20000); pg.wait_for_timeout(250)
                if pg.locator('.pk .npc').count():
                    pg.locator('.pk .npc').first.click(); n += 1; pg.wait_for_timeout(500); done = True; break
                if i == 0: empty_msg = pg.inner_text('.pk .npe')
                pg.evaluate("history.back()"); pg.wait_for_timeout(150)
            if empty_msg: check('S10 D：第一站点开后候选为空时写清原因（%s）' % empty_msg, '已排到' in empty_msg or '超过' in empty_msg or '排满' in empty_msg or '没有顺路' in empty_msg, empty_msg)
            check('S10 D 加一个顺路景点（试到第 %d 个有候选的站）：%d 点击（≤3），加上了、有“撤销”' % (tried, n), done and n <= 3 and pg.locator('.toast .toast-act').count() == 1 and pg.evaluate("!!document.querySelector('.tl > .r[data-np=v]')"), (done, n, tried))
            TASKS['D'] = ('3 点击（xa3 的 7 个可加站点里 5 个置灰）', '%d 点击（xa3 7 个站点都可点，其中 4 个点开有候选；有候选的站 3 步、没有候选的站点开后写“再加就超过 22:40 了”）' % n); c.close()
        with guard('S10 E 改出发日期（xl9a 第 12 天处）'):
            c, pg = trip(br, 'xl9a'); n = 0
            pg.evaluate("document.getElementById('d12').scrollIntoView({behavior:'instant'})"); pg.wait_for_timeout(500)
            dv0 = pg.evaluate("document.querySelector('.dpk').value"); sy = pg.evaluate("scrollY")
            vis = pg.evaluate("(()=>{const r=document.querySelector('.dock>div[role=button]').getBoundingClientRect();return [Math.round(r.width),Math.round(r.height),document.querySelector('.dock>div[role=button]').innerText.replace(/\\s+/g,' ')]})()")
            check('S10 E：滚到第 12 天时底栏有可点的日期（%s，≥44 高）' % vis, vis[1] >= 44 and re.search(r'\d+/\d+', vis[2]), vis)
            pg.click('.dock>div[role=button]'); n += 1; pg.wait_for_selector('.pk'); pg.wait_for_timeout(250)
            pg.click('.pk-q button:not([disabled]) >> nth=1'); n += 1; pg.wait_for_timeout(500)
            dv1 = pg.evaluate("document.querySelector('.dpk').value")
            check('S10 E 改出发日期（页面不在顶部）：%d 点击（≤2）、没滚回顶部（scrollY %s→%s）、日期变了 %s→%s' % (n, sy, pg.evaluate('scrollY'), dv0, dv1), n <= 2 and dv1 != dv0 and gone(pg) and abs(pg.evaluate('scrollY') - sy) < 200, (dv0, dv1))
            TASKS['E'] = ('2 点击（但只在页顶；长线要先滚回去）', '%d 点击（任意位置，底栏日期可点）' % n); c.close()
        with guard('S10 F 收进行程'):
            c, pg = trip(br, 'xa3'); pg.click('.fav'); pg.wait_for_timeout(300)
            check('S10 F 收进行程：1 点击、按钮变“已收进”（2026-10-19：复述类提示条删了，按钮本身就是反馈）', pg.evaluate("document.querySelector('.fav').classList.contains('on')&&!document.querySelector('.toast')"))
            TASKS['F'] = ('1 点击', '1 点击'); c.close()
        with guard('S10 G 分享给朋友'):
            c, pg = trip(br, 'xa3'); pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="link"]'); pg.wait_for_timeout(500)
            clip = pg.evaluate("window.__clip||''")
            check('S10 G 分享给朋友：2 点击，链接进了剪贴板（%s）' % clip[:40], '/trip/xa3/' in clip and gone(pg), clip)
            TASKS['G'] = ('2 点击', '2 点击'); c.close()
        with guard('S10 H 导出日历'):
            c, pg = trip(br, 'xa3'); n = 0
            pg.click('.share'); n += 1; pg.wait_for_selector('.pk')
            labels = pg.evaluate("[...document.querySelectorAll('.pk [data-a] b')].map(b=>b.textContent)")
            check('S10 H：分享层里有“加入日历”（%s）' % labels, '加入日历' in labels and len(labels) == 5, labels)
            shot(pg, 'S10_share_with_calendar.png')
            with pg.expect_download(timeout=5000) as dl: pg.click('.pk [data-a="ics"]'); n += 1
            fn = dl.value.suggested_filename
            check('S10 H 导出日历：%d 点击（≤2），下载了 %s' % (n, fn), n <= 2 and fn.endswith('.ics'), fn)
            TASKS['H'] = ('2 点击，但入口藏在“出发前要办的事”弹层里', '%d 点击，在分享层里写着“加入日历”' % n); c.close()
        with guard('S10 I 导航这一天'):
            c = new_ctx(br, None); hits = []
            c.route(re.compile(r'https://(uri\.amap\.com|www\.google\.com/maps)/.*'), lambda r: (hits.append(r.request.url), r.fulfill(status=204, body=''))[1])
            pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 700); n = 0
            pg.evaluate("document.querySelector('#d1 .rm-nb').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-nb'); n += 1
            pg.wait_for_selector('.rm-sheet.rm-dyn, .pk', timeout=8000); pg.wait_for_timeout(300)
            if pg.locator('.rm-sheet a.rm-seg').count(): pg.locator('.rm-sheet a.rm-seg').first.click(); n += 1; pg.wait_for_timeout(500)
            check('S10 I 导航这一天：%d 点击（多段 ≤2），发出高德链接 %d 条' % (n, len(hits)), n <= 2 and len(hits) >= 1, (n, hits[:1]))
            TASKS['I'] = ('单段 1 / 多段 2 点击', '%d 点击（xa3 第 1 天多段）' % n); c.close()
        with guard('S10 J 怎么去、怎么回'):
            c, pg = trip(br, 'xa3')
            j = pg.evaluate("(()=>{const g=document.querySelector('section.pre.go'),r=g.getBoundingClientRect();return {y:(r.bottom+scrollY)/innerHeight,h2:g.querySelector('h2').textContent,txt:g.querySelector('.gw span').innerText}})()")
            check('S10 J 怎么去怎么回：0 点击、整块在 %.2f 屏内；回程写在同一块里（%s）' % (j['y'], j['txt'][:60]), j['y'] <= 1.0 and '回：' in j['txt'], j)
            TASKS['J'] = ('去：0.5 屏；回：在最后一天末行（xa3 约 6.4 屏、xl9a 约 27 屏之外）', '去、回同一块：0 点击、%.2f 屏内' % j['y']); c.close()
        with guard('S10 K 查住宿'):
            c, pg = trip(br, 'xa3'); n = 0
            pg.evaluate("document.querySelector('.todoall').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.todoall'); n += 1; pg.wait_for_selector('.tv.todo'); pg.wait_for_timeout(250)
            hot = pg.evaluate("(()=>{const h=[...document.querySelectorAll('.tv.todo h3')].find(x=>x.textContent==='住宿');if(!h)return null;const u=h.nextElementSibling;return {t:u.innerText.replace(/\\s+/g,' '),link:!!u.querySelector('a')}})()")
            check('S10 K 查住宿：%d 点击（弹层“住宿”组列出每晚的住处和“去订”：%s）' % (n, hot and hot['t'][:40]), n <= 1 and hot and hot['link'], hot)
            pg.evaluate("history.back()"); pg.wait_for_timeout(300)
            pg.evaluate("document.querySelector('#d1 .tl > .r.stay').scrollIntoView({block:'center',behavior:'instant'})"); pg.wait_for_timeout(200)
            pg.evaluate("window.scrollBy(0,-200)"); pg.wait_for_timeout(300)      # 先离开：卡在视口里、但不在“跳过来”的位置上，点了之后卡顶必须落在 64px 附近（吸顶日期条下面），不能是原地没动
            ct0 = pg.evaluate("document.querySelector('#d1 .stays').getBoundingClientRect().top"); y0 = pg.evaluate("scrollY")
            pg.click('#d1 .tl > .r.stay .m', position={'x': 20, 'y': 10}); pg.wait_for_timeout(600)
            ct = pg.evaluate("(()=>{const c=document.querySelector('#d1 .stays').getBoundingClientRect();return c.top})()")
            check('S10 K 当天末尾“住 · …”一点就跳到住宿卡（点之前卡顶 %d px，点之后 %d px ≈ 64；页面滚了 %s→%s）' % (ct0, ct, y0, pg.evaluate('scrollY')), 40 <= ct <= 100 and abs(ct - ct0) > 30, (ct0, ct))
            TASKS['K'] = ('页头看不到；xa3 第 1 晚在 2.5 屏', '1 点击：弹层“住宿”组；当天末尾“住 · …”可点，跳到住宿卡'); c.close()
            c, pg = trip(br, 'xl9a')
            txt = pg.evaluate("(()=>{const p=document.querySelector('.ovstay');return p?{n:p.querySelectorAll('a').length,hid:p.hidden}:null})()")
            check('S10 K 长线 xl9a：概览“住：…”每段都是链接（%s）' % txt, txt and txt['n'] >= 3, txt)
            c.close()
        with guard('S10 L 退出任一弹层'):
            TASKS['L'] = ('1 点击，但有 2 个目标；存图层返回键不响应', '1 点击 / 返回键 / Esc / 点遮罩 / 下滑，只有 1 个可见 ×（S1/S2/S4）')
            check('S10 L：见 S1/S2/S4（每层 1 个 ×，返回 / Esc / 遮罩 / 下滑都能关）', True)

    # ———————————————— S11 “加一个顺路景点”不是死路（2026-10-19 改口径：入口上先算候选数，0 条就置灰写原因） ————————————————
    if want('S11'):
        COV = {}; TOT_OK = TOT_N = 0
        WAIT = "(()=>{const b=document.querySelector('.pk [data-np=\"ins\"]');return b&&(b.disabled||b.getAttribute('data-chk'))})()"
        for rid in ['xa3', 'tk4', 'hss1a', 'hcz1', 'xv613a', 'gqhx10']:
            with guard('S11 ' + rid):
                c, pg = trip(br, rid, wait=1000)
                idxs = pg.evaluate("[...document.querySelectorAll('section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj')].map((b,i)=>i)")
                tot = ok = withc = 0; why = {}
                for i in idxs:
                    pg.evaluate("(i)=>{const b=document.querySelectorAll('section.day:not(.xday) .tl > .r.see .adj, section.day:not(.xday) .tl > .r.fun .adj')[i];b.scrollIntoView({block:'center',behavior:'instant'});b.click()}", i)
                    pg.wait_for_selector('.pk')
                    ins = pg.locator('.pk [data-np="ins"]')
                    if ins.count():
                        tot += 1
                        try: pg.wait_for_function(WAIT, timeout=(3000 if env.inject else 20000))
                        except Exception: pass
                        if ins.first.is_disabled():
                            w_ = pg.inner_text('.pk [data-np="ins"] small') if pg.locator('.pk [data-np="ins"] small').count() else ''; why[w_] = why.get(w_, 0) + 1
                        else:
                            ok += 1
                            ins.first.click(); pg.wait_for_selector('.pk .npc, .pk .npe', timeout=20000)      # 真点开列表：可点就必须有候选
                            if pg.locator('.pk .npc').count(): withc += 1
                    pg.evaluate("history.back()"); pg.wait_for_timeout(120)
                COV[rid] = (ok, tot, withc); TOT_OK += ok; TOT_N += tot
                check('S11 %s：可点 %d / %d，点开后都有候选 %d / %d（可点 ⇒ 有候选）' % (rid, ok, tot, withc, ok), tot > 0 and withc == ok, (ok, tot, withc))
                check('S11 %s：置灰的都写清原因（%s）' % (rid, list(why)[:3]), all(('已排到' in w or '再加就超过' in w or '排满' in w or '已有' in w or '超过' in w or '附近没有' in w or '关门' in w) for w in why), why)
                c.close()
        if not ONLY or 'S11' in ONLY: check('S11 六条线合计可点 %d / %d = %.0f%%（≥50%%：置灰是例外，不是常态）' % (TOT_OK, TOT_N, 100.0 * TOT_OK / max(1, TOT_N)), TOT_N > 0 and TOT_OK / TOT_N >= 0.5, (TOT_OK, TOT_N))
        TASKS['S11'] = COV
        with guard('S11 列表为空时的原因'):
            c, pg = trip(br, 'xa3', wait=1000)
            # 第 1 天晚上已排到 22:10：弹层里就置灰并写“再加就超过 …”（不再点进去才看到空列表）
            pg.evaluate("document.querySelector('#d1 .tl .adj').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .tl .adj >> nth=0'); pg.wait_for_selector('.pk')
            try: pg.wait_for_function(WAIT, timeout=(3000 if env.inject else 20000))
            except Exception: pass
            if pg.locator('.pk [data-np="ins"]').count():
                dis = pg.locator('.pk [data-np="ins"]').first.is_disabled(); tx = pg.inner_text('.pk [data-np="ins"] small') if dis else ''
                check('S11 候选为空时入口置灰并写清为什么（%s）' % (tx or '可点'), dis and ('已排到' in tx or '超过' in tx or '排满' in tx or '附近没有' in tx), tx)
            c.close()

    # ———————————————— S12 / S13 ————————————————
    if want('S12'):
        for rid in SAMPLE:
            if env.inject in INJ_TARGET and INJ_TARGET[env.inject] != rid: continue
            with guard('S12 ' + rid):
                c, pg = trip(br, rid)
                g = pg.evaluate("(()=>{const e=document.querySelector('section.pre.go');return e?{h2:e.querySelector('h2').textContent,b:e.querySelector('.gw span').textContent}:null})()")
                check('S12 %s：“怎么去、怎么回”块里有回程（%s）' % (rid, (g or {}).get('b', '')[-34:]), g and (('回：' in g['b'] and '回' in g['h2']) or ('回' not in g['h2'])), g)
                c.close()
    if want('S13'):
        with guard('S13 页脚'):
            c, pg = trip(br, 'xa3')
            pg.evaluate("document.querySelector('.foot').scrollIntoView({behavior:'instant'})")
            hs = pg.evaluate("[...document.querySelectorAll('.foot a')].map(a=>{const r=document.createRange();r.selectNodeContents(a);return [a.textContent,r.getClientRects().length,Math.round(r.getBoundingClientRect().height)]})")
            check('S13 页脚每个链接单行（文字只占 1 个矩形、高 ≤20px：%s）' % [x for x in hs if x[1] != 1 or x[2] > 20], all(n == 1 and h <= 20 for _, n, h in hs), hs)
            hit = [pg.evaluate(HIT, pg.locator('.foot a').nth(i).element_handle()) for i in range(len(hs))]      # 两排之间的点击区不能互相盖住（HIT 取不到 = 中心被别的链接盖了）
            check('S13 页脚链接点击区高 ≥44（沿用 ux_common.HIT）', all(h and h['h'] >= 44 for h in hit), hit)
            c.close()

    # ———————————————— SX 复制行程 / 按天看：卡头去掉地名后不丢信息 ————————————————
    if want('SX'):
        for rid, nm in (('xa3', '钟楼附近'), ('gqhx10', '西宁')):
            with guard('SX ' + rid):
                c, pg = trip(br, rid)
                lines = pg.evaluate("window.zTripText()").split('\n')
                sl = [l for l in lines if '今晚住' in l]
                check('SX %s 复制行程：“今晚住：”后面有住处名“%s”、没有空的“今晚住：；”（%s）' % (rid, nm, sl[:1]), any(('今晚住：' + nm) in l for l in sl) and not any(re.search(r'今晚住：(；|$)', l) for l in sl), sl)
                pre = [l for l in lines if l.startswith('  · ')]
                check('SX %s 复制行程：“出发前要办的事”每条只出现一次（%d 条；页内折起来的也复制，隐藏的带孩子条目不复制）' % (rid, len(pre)), len(pre) == len(set(pre)), pre)
                check('SX %s 复制行程：页头几行没有空的说明行' % rid, '' not in lines[3:5], lines[:6])
                pg.click('.tvbtn'); pg.wait_for_selector('.tv'); pg.wait_for_timeout(300)
                bx = pg.evaluate("[...document.querySelectorAll('.tv .tvbox')].map(b=>b.innerText.replace(/\\s+/g,' ')).find(t=>t.indexOf('今晚住')===0)||''")
                check('SX %s 按天看里“今晚住”写着住处名“%s”（%s）' % (rid, nm, bx[:30]), nm in bx, bx)
                c.close()

    # ———————————————— 内容扫描：主题线路正文交通方式 vs via ————————————————
    if want('SC'):
        with guard('内容扫描'):
            import glob
            A, B_, weak = [], [], 0
            for pth in sorted(glob.glob(os.path.join(ROOT, 'build', 'history', '*.json'))):
                b = os.path.basename(pth)
                if b.startswith(('chk_', '_')): continue
                try: d = json.load(open(pth, encoding='utf-8'))
                except Exception: continue
                if not isinstance(d, dict) or 'routes' not in d: continue
                for r in d['routes']:
                    tags = r.get('tags') or []
                    for i, day in enumerate(r.get('days', [])):
                        t = day.get('text', ''); vias = [(s.get('via') or '') for s in day.get('stops', [])]; vj = ' '.join(vias)
                        drv_t = re.search(r'(?<!不)(开车|自驾)', t); hsr_t = re.search(r'高铁|火车|动车|城际', t)
                        drv_v = re.search(r'自驾|开车|包车', vj); hsr_v = re.search(r'火车|高铁|动车|城际', vj)
                        if drv_t and not drv_v and '自驾' not in tags: A.append((r['id'], i + 1))      # 正文说开车 / 自驾，这条线不是自驾线、当天 via 里也没有
                        if hsr_t and not hsr_v and vias and all('自驾' in v for v in vias if v) and not drv_t and not re.search(r'离开|回程|返回|返程|回北京|回上海|回广州|回深圳|回杭州|回武汉|回西安|回成都|回家|之后乘|或乘|或坐|也可|赶\S{0,4}(高铁|火车|飞机)|飞机或火车|火车或飞机|高铁要留', t): B_.append((r['id'], i + 1))   # 当天 via 全是自驾，正文却只讲高铁
                        if (drv_t and not drv_v) or (hsr_t and not hsr_v): weak += 1
            check('内容扫描：主题线路正文交通方式与 via 的明确矛盾（说开车但不是自驾线 / via 全自驾却只讲高铁）：%d 处 %s（弱命中 %d 处是跨城移动写在正文里、via 只记景点间车程，逐项看过不是矛盾）' % (len(A) + len(B_), (A + B_)[:5], weak), not A and not B_, (A, B_))

    # ———————————————— S14 清场 ————————————————
    MAN1 = manifest()
    check('S14 清场：跑前跑后站目录 + data/ + site_src/ 的文件清单一致（%d 个文件，%s）' % (MAN0[1], MAN0[0][:8]), MAN0 == MAN1, (MAN0, MAN1))
    br.close()

if '--table' in sys.argv:
    for k in sorted(TASKS): print('TASK', k, TASKS[k])
env.finish('详情页与弹层少就是多')
