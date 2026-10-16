#!/usr/bin/env python3
"""状态记忆 + 离线与弱网（2026-10-17，任务单第 5、6 组）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/ux_state_offline_check.py build/site [--shots DIR]
    python3 tests/ux_state_offline_check.py build/site --inject home_state|daynav|sw_silent|sw_reload|banner_fixed|no_precache    # 反向自检

第 5 组 状态记忆
  M1 首页：点“周末 2–3 天”、点“再看 12 条” → 进一条线路 → 浏览器返回：筛选和展开的条数都在；换标签页 / 直接点链接回首页回到默认
  M2 /long/：筛选在 URL hash 里，进线路再返回仍在
  M3 按天看：#d2 进来 → 按天看从第 2 天打开；滚到哪一天，顶部“1 2 3”就高亮哪一天；下次再打开同一条线，提示“回到第 N 天”，点了到那；按天看默认也从上次那天开
第 6 组 离线与弱网（真 Service Worker + 断网）
  O1 第一次安装 Service Worker 时页面不会自己刷新；从旧版升级才刷新一次
  O2 断网点没打开过的行程：出明确的离线页（标题、一句话、回首页、已存的行程），不是静默变首页
  O3 离线横幅不遮挡返回/首页/分享（文档流里把内容往下推）
  O4 “收进行程”把这一页存进离线缓存（先清掉缓存，点收进，缓存里就有了；断网刷新还能开），“已收进”上有 ✓
  O5 断网点“调整”：“在这之后加一个…”“换成…”入口上就写“没网，暂时不能加景点”，点了给提示条
  O6 断网搜索：首页不跳页，词留着，写“没网，搜不了「xx」”；/where/?q=xx 断网用缓存的搜索页，线路那块写“没网，搜不了”
  O7 manifest 和图标都在离线预存里
"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'home_state': ('assets/site.js', "band=/^d[123]$/.test(hs0.band||'')?hs0.band:'';", "band='';"),                                                 # 返回时不恢复筛选
    'daynav': ('assets/site.js', "as.forEach(function(a,i){a.classList.toggle('on',i+1===cur);", "as.forEach(function(a,i){a.classList.toggle('on',i===0);"),   # 顶部天数标签永远高亮第 1 天
    'sw_silent': ('sw.js', "(nav ? caches.match('/offline.html') : undefined)", "(nav ? caches.match('/') : undefined)"),                               # 没存过的页面悄悄给首页
    'sw_reload': ('sw.js', "const upgrade = ks.some(k => k !== V);", "const upgrade = true;"),                                                      # 第一次安装也刷新
    'banner_fixed': ('assets/site.js', "document.body.insertBefore(b,document.body.firstChild)", "b.style.cssText='position:fixed;left:0;right:0;top:0;z-index:40';document.body.appendChild(b)"),   # 横幅又盖在顶上
    'no_precache': ('sw.js', "'/manifest.webmanifest', ", ""),                                                                                            # 预存清单漏了 manifest
}
env = Env(INJ)
check, guard = env.check, env.guard


DEV_SW = "try{localStorage.setItem('zouni_dev_sw','1')}catch(e){}"      # 本机（http://127.0.0.1）默认不注册 Service Worker，这个开关才注册


def sw_ready(pg, timeout=20000):
    pg.wait_for_function("navigator.serviceWorker&&navigator.serviceWorker.controller", timeout=timeout)


with sync_playwright() as p:
    br = p.chromium.launch()

    # ———— M1 首页筛选记忆 ————
    with guard('M1'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/'); home_ready(pg)
        pg.click('.dchips button[data-b="d1"]'); pg.wait_for_timeout(300)
        pg.click('.moreb'); pg.wait_for_timeout(300)
        pg.click('.moreb'); pg.wait_for_timeout(300)
        shown0 = pg.evaluate("document.querySelectorAll('.now .items li:not([hidden])').length")
        bands = pg.evaluate("[...document.querySelectorAll('.now .items li:not([hidden])')].every(l=>l.dataset.band==='d1')")
        check('M1 点“周末”再点两次“再看”后展开了 >8 条（%d）且都是周末的' % shown0, shown0 > 8 and bands, (shown0, bands))
        href = pg.evaluate("document.querySelector('.now .items li:not([hidden]) h3 a').getAttribute('href')")
        pg.click('.now .items li:not([hidden]) h3 a'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(400)
        check('M1 进到了线路页', '/trip/' in pg.url, pg.url)
        pg.go_back(wait_until='networkidle'); pg.wait_for_timeout(1200)
        on = pg.evaluate("document.querySelector('.dchips button.on').dataset.b")
        shown1 = pg.evaluate("document.querySelectorAll('.now .items li:not([hidden])').length")
        check('M1 返回首页后“周末”仍然是选中的', on == 'd1', on)
        check('M1 返回首页后展开的条数还在（%d → %d）' % (shown0, shown1), shown1 == shown0, (shown0, shown1))
        # 换标签页：新页签回到默认
        pg2 = new_page(env, c); goto(env, pg2, '/'); home_ready(pg2)
        on2 = pg2.evaluate("document.querySelector('.dchips button.on').dataset.b"); sh2 = pg2.evaluate("document.querySelectorAll('.now .items li:not([hidden])').length")
        check('M1 换标签页（新会话）回到默认：全部、8 条', on2 == '' and sh2 == 8, (on2, sh2))
        # 同一个标签页里点链接回首页（不是返回）：也回到默认
        pg.goto(env.B + '/trip/xa3/', wait_until='networkidle'); pg.click('.hero .home'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(800)
        on3 = pg.evaluate("document.querySelector('.dchips button.on').dataset.b")
        check('M1 在行程页点“走”回首页（不是浏览器返回）：回到默认', on3 == '', on3)
        c.close()

    # ———— M2 /long/ hash ————
    with guard('M2'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/long/')
        pg.click('.lchips[data-k=m] button[data-m="3"]'); pg.wait_for_timeout(200)
        pg.click('.lchips[data-k=d] button[data-d="a"]'); pg.wait_for_timeout(300)
        h = pg.evaluate("location.hash"); cnt = pg.inner_text('.lcnt')
        check('M2 /long/ 的筛选写进了 URL hash（%s）' % h, 'm=3' in h and 'd=a' in h, h)
        pg.click('.lcards li:not([hidden]) a'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(300)
        pg.go_back(wait_until='networkidle'); pg.wait_for_timeout(600)
        check('M2 返回 /long/：hash 还在', pg.evaluate("location.hash") == h, pg.evaluate("location.hash"))
        check('M2 返回 /long/：筛选按钮和结果数还在', pg.inner_text('.lcnt') == cnt and pg.evaluate("document.querySelectorAll('.lchips button.on').length") >= 2, pg.inner_text('.lcnt'))
        c.close()

    # ———— M3 按天看 / 天数标签 ————
    with guard('M3'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/#d2', wait=1800)
        sy = pg.evaluate("scrollY"); top2 = pg.evaluate("document.getElementById('d2').getBoundingClientRect().top")
        check('M3 带 #d2 打开：滚到第 2 天（离窗口顶 <120px，实测 %dpx）' % top2, abs(top2) < 120, top2)
        on_idx = pg.evaluate("[...document.querySelectorAll('.daynav a')].findIndex(a=>a.classList.contains('on'))")
        check('M3 带 #d2 打开：顶部天数标签高亮“2”', on_idx == 1, on_idx)
        pg.click('.dock .tvbtn'); pg.wait_for_selector('.tv'); pg.wait_for_timeout(300)
        on_tab = pg.evaluate("document.querySelector('.tvtabs .on').innerText.trim()"); hd = pg.inner_text('.tv .tvd')
        check('M3 #d2 进来再点“按天看”：从第 2 天打开', on_tab == '2' and '第二天' in hd, (on_tab, hd))
        pg.click('.tv .tvtabs button:nth-child(3), .tv .tvtabs a:nth-child(3)'); pg.wait_for_timeout(300)
        check('M3 按天看里点“3”：标签高亮“3”、内容换成第三天', pg.evaluate("document.querySelector('.tvtabs .on').innerText.trim()") == '3' and '第三天' in pg.inner_text('.tv .tvd'))
        pg.click('.tv .tvx'); pg.wait_for_timeout(200)
        # 主页面滚动：每一天对应高亮
        res = []
        for i in (1, 2, 3, 2, 1):
            pg.evaluate("(i)=>{const y=document.getElementById('d'+i).getBoundingClientRect().top+scrollY-60;scrollTo({top:y,behavior:'instant'})}", i); pg.wait_for_timeout(450)
            res.append((i, pg.evaluate("[...document.querySelectorAll('.daynav a')].findIndex(a=>a.classList.contains('on'))+1")))
        check('M3 顶部“1 2 3”标签跟着滚动高亮当前天（%s）' % res, all(a == b for a, b in res), res)
        pg.evaluate("(()=>{const y=document.getElementById('d3').getBoundingClientRect().top+scrollY-60;scrollTo({top:y,behavior:'instant'})})()"); pg.wait_for_timeout(1400)
        last = ls(pg, 'zouni_lastday_xa3')
        check('M3 看到第 3 天后记在本机（zouni_lastday_xa3）', last and json.loads(last)['d'] == 3, last)
        # 再次打开同一条线（无 hash）
        pg.goto(env.B + '/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(1500)
        act = pg.locator('.toast .toast-act')
        check('M3 老用户再次打开同一条线：提示“回到第 3 天”', act.count() == 1 and '第 3 天' in act.inner_text(), act.count())
        if act.count():
            act.click(); pg.wait_for_timeout(500)
            t3 = pg.evaluate("document.getElementById('d3').getBoundingClientRect().top")
            check('M3 点“回到第 3 天”后滚到第 3 天（离窗口顶 %dpx）' % t3, abs(t3 - 56) < 80, t3)
        pg.evaluate("scrollTo({top:0,behavior:'instant'})"); pg.wait_for_timeout(300)
        pg.click('.dock .tvbtn'); pg.wait_for_selector('.tv'); pg.wait_for_timeout(300)
        check('M3 没有 hash 时，按天看从上次看到的第 3 天打开', pg.evaluate("document.querySelector('.tvtabs .on').innerText.trim()") == '3', pg.evaluate("document.querySelector('.tvtabs .on').innerText.trim()"))
        c.close()

    # ———— O1 第一次安装不刷新 ————
    with guard('O1'):
        c = br.new_context(viewport={'width': 390, 'height': 844}, service_workers='allow'); c.add_init_script(DEV_SW); pg = c.new_page(); pg.set_default_timeout(15000)
        navs = []; pg.on('framenavigated', lambda f: navs.append(f.url) if f == pg.main_frame else None)
        pg.route(NO_NET, lambda r: r.abort())
        pg.goto(env.B + '/trip/xa3/', wait_until='networkidle'); sw_ready(pg); pg.wait_for_timeout(2500)
        check('O1 第一次安装 Service Worker：页面没有自己刷新（导航次数 %d）' % len(navs), len(navs) == 1, navs)
        keys = pg.evaluate("caches.keys()")
        check('O1 缓存名是 zouni-v3', keys == ['zouni-v3'], keys)
        c.close()
        # 从旧版升级：先种一个旧缓存名，装完应刷新一次（旧页面跑的是旧脚本）
        c = br.new_context(viewport={'width': 390, 'height': 844}, service_workers='allow'); c.add_init_script(DEV_SW); pg = c.new_page(); pg.set_default_timeout(15000)
        pg.route(NO_NET, lambda r: r.abort())
        pg.goto(env.B + '/offline.html', wait_until='networkidle')       # 同源页面，先种旧缓存（不会注册 sw：offline.html 没有 site.js）
        pg.evaluate("caches.open('zouni-v2').then(c=>c.put('/x',new Response('old')))"); pg.wait_for_timeout(300)
        navs = []; pg.on('framenavigated', lambda f: navs.append(f.url) if f == pg.main_frame else None)
        pg.goto(env.B + '/', wait_until='networkidle'); sw_ready(pg); pg.wait_for_timeout(3000)
        check('O1 从旧版升级（有旧缓存）：装好后刷新一次（导航 %d 次）' % len(navs), len(navs) == 2, navs)
        check('O1 升级后旧缓存被清掉', pg.evaluate("caches.keys()") == ['zouni-v3'], pg.evaluate("caches.keys()"))
        c.close()

    # ———— O2–O7 离线 ————
    with guard('O2'):
        c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2, service_workers='allow')
        c.add_init_script(DEV_SW)
        c.add_init_script("(function(){var w={writeText:function(t){window.__clip=t;return Promise.resolve()}};try{Object.defineProperty(navigator,'clipboard',{value:w,configurable:true})}catch(e){}})();")
        pg = new_page(env, c)
        goto(env, pg, '/'); sw_ready(pg)
        goto(env, pg, '/trip/xa3/'); pg.wait_for_timeout(800)
        # 收进行程
        pg.evaluate("caches.open('zouni-v3').then(c=>c.delete('/trip/xa3/'))"); pg.wait_for_timeout(200)
        in0 = pg.evaluate("caches.match('/trip/xa3/').then(r=>!!r)")
        pg.click('.dock .fav'); pg.wait_for_function("document.querySelector('.fav').classList.contains('saved')", timeout=15000)
        in1 = pg.evaluate("caches.match('/trip/xa3/').then(r=>!!r)")
        check('O4 先清掉缓存（%s），点“收进行程”后这一页进了缓存（%s）' % (in0, in1), (not in0) and in1, (in0, in1))
        fl = pg.evaluate("getComputedStyle(document.querySelector('.fav.saved span'),'::after').content")
        check('O4 “已收进”上有 ✓ 的极简反馈', '✓' in fl, fl)
        check('O4 有“已存到手机里，没网也能看”的提示', pg.locator('.toast').count() == 1 and '存到手机' in pg.inner_text('.toast'), pg.locator('.toast').count())
        # O7 预存清单
        pre = pg.evaluate("Promise.all(['/manifest.webmanifest','/img/icon-192.png','/img/icon-512.png','/img/apple-touch-icon.png','/img/favicon.svg','/offline.html','/','/where/'].map(u=>caches.match(u).then(r=>[u,!!r])))")
        check('O7 manifest、图标、离线页、首页、走哪儿都在预存缓存里', all(x[1] for x in pre), [x for x in pre if not x[1]])
        # 断网
        c.set_offline(True)
        pg.goto(env.B + '/trip/gqhx10/', wait_until='load'); pg.wait_for_timeout(600)
        title = pg.title(); body = pg.inner_text('body')
        check('O2 断网点没打开过的行程：出的是离线页（不是首页）', '没有网络' in title and '还没存到手机里' in body and 'gqhx10' in pg.url, (title, pg.url))
        links = pg.evaluate("[...document.querySelectorAll('a')].map(a=>a.innerText.trim()+'>'+a.getAttribute('href'))")
        check('O2 离线页有“回首页”和“已存的行程”入口', '回首页>/' in links and any(x.startswith('已存的行程>') for x in links), links)
        check('O2 离线页列出已存的行程（刚收进的西安 3 天，可点）', pg.evaluate("[...document.querySelectorAll('#list a')].some(a=>a.getAttribute('href')==='/trip/xa3/')"), pg.inner_text('#list'))
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'O2_offline_page.png'))
        # 回首页入口真的能到首页
        pg.click('a.b'); pg.wait_for_load_state('load'); pg.wait_for_timeout(500)
        check('O2 点“回首页”到了缓存的首页', pg.url.rstrip('/') == env.B and '走你' in pg.title(), pg.url)
        # 已存的行程能离线打开 + 横幅
        pg.goto(env.B + '/trip/xa3/', wait_until='load'); pg.wait_for_timeout(1000)
        check('O4 收进过的行程断网刷新照样能开（有时间表）', pg.locator('#d1 .tl .r').count() > 3, pg.title())
        ban = pg.evaluate("(()=>{const b=document.querySelector('.offline');if(!b)return null;const r=b.getBoundingClientRect();const q=s=>{const e=document.querySelector(s);if(!e)return null;const x=e.getBoundingClientRect();return [x.top,x.bottom]};return {pos:getComputedStyle(b).position,top:r.top,bottom:r.bottom,back:q('.hero .back'),home:q('.hero .home'),share:q('.hero .share'),first:document.body.firstElementChild===b}})()")
        check('O3 断网时有横幅', ban is not None)
        if ban:
            ov = [k for k in ('back', 'home', 'share') if ban[k] and not (ban[k][0] >= ban['bottom'] - 0.5)]
            check('O3 横幅在文档流里（不是 fixed），在页面最前面', ban['pos'] != 'fixed' and ban['first'], ban)
            check('O3 横幅不遮挡返回/首页/分享（它们都在横幅下面）', not ov, (ban, ov))
            check('O3 返回/首页/分享仍然点得到（elementFromPoint）', all(pg.evaluate(HIT, pg.locator(s).first.element_handle()) for s in ('.hero .back', '.hero .home', '.hero .share')))
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'O3_offline_banner.png'))
        # O5 断网点“调整”
        pg.locator('#d3 .adj').first.click(); pg.wait_for_selector('.pk'); pg.wait_for_timeout(200)
        btn = pg.locator('.pk [data-np="ins"]'); small = btn.locator('small').inner_text() if btn.count() else ''
        check('O5 断网时“在这之后加一个…”入口上就写“没网，暂时不能加景点”', '没网，暂时不能加景点' in small, small)
        check('O5 断网时“换成…”入口上写“没网”', '没网' in (pg.locator('.pk [data-np="rep"] small').inner_text() if pg.locator('.pk [data-np="rep"] small').count() else ''))
        btn.click(force=True); pg.wait_for_timeout(300)
        check('O5 点了给提示条，不进空的候选页', pg.locator('.toast').count() == 1 and '没网' in pg.inner_text('.toast') and pg.locator('.pk .npc').count() == 0, pg.locator('.toast').count())
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'O5_offline_adjust.png'))
        pg.locator('.pk .pk-xb').click(); pg.wait_for_timeout(200)
        # O6 搜索
        pg.goto(env.B + '/', wait_until='load'); pg.wait_for_timeout(800)
        pg.fill('.hsearch input', '川藏'); pg.click('.hsearch button'); pg.wait_for_timeout(500)
        msg = pg.locator('.hsmsg')
        check('O6 断网在首页搜索：不跳页', pg.url.rstrip('/') == env.B, pg.url)
        check('O6 断网搜索：词还在框里、写“没网，搜不了「川藏」”', pg.input_value('.hsearch input') == '川藏' and msg.count() == 1 and '没网，搜不了「川藏」' in msg.inner_text(), (pg.input_value('.hsearch input'), msg.count()))
        pg.goto(env.B + '/where/?q=%E5%9C%9F%E6%A5%BC', wait_until='load'); pg.wait_for_timeout(1500)
        check('O6 断网打开 /where/?q=土楼：用缓存的搜索页，查询词还在', pg.input_value('.flt input') == '土楼' or '土楼' in pg.inner_text('.orgnote') if pg.locator('.flt input').count() else '土楼' in pg.inner_text('body'), pg.url)
        wtr = pg.locator('.wtr')
        check('O6 线路那块写“没网，搜不了「土楼」”', wtr.count() == 1 and '没网，搜不了' in wtr.inner_text(), wtr.inner_text() if wtr.count() else None)
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'O6_offline_search.png'))
        c.set_offline(False); c.close()
    br.close()
env.finish('状态记忆 / 离线与弱网')
