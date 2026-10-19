#!/usr/bin/env python3
"""2026-10-19 “去冗余波”的断言（设计：docs/handoff/design-overdesign-consolidated.md §2；每项都量“信息和操作的数量”，不砍功能）。

用法（项目根目录；先 bash build/pipe.sh build/site_fy）：
    python3 tests/wave2_check.py build/site_fy [--shots DIR]
    python3 tests/wave2_check.py build/site_fy --inject 名字      # 反向自检：把被删的东西在送到浏览器的那一份里加回去，对应判据必须变红
    python3 tests/wave2_check.py build/site_fy --table 旧站目录   # 只打印“前后数字”，不判定（写报告用）

页面全部经本地服务读（不直接读磁盘），所以 --inject 对页面 HTML、site.js、site.css 都有效。

A  首页 / 走哪儿 / 出发地·人数·日期 / 目的地页 / 跟片走 / 弹层·toast / 本地存储
B  行程页内容样板行
C  新用户术语、输入、可访问性、多设备
D  重复线路清理
"""
import json, os, re, sys, urllib.request, concurrent.futures
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

JS, CSS = 'assets/site.js', 'assets/site.css'
INJ = {
    # —— A 首页
    'drive_shelf': ('=index.html', '</article>', '<section class="toc" id="drive"><h2>长途和自驾<small>53 条环线和长线</small></h2></section></article>'),
    'search_btn': ('=index.html', '</form>', '<button type="submit">搜</button></form>'),
    'chip_all': ('=index.html', '<div class="dchips" role="group" aria-label="我有几天（再点一次取消）">', '<div class="dchips" role="group" aria-label="我有几天"><button type="button" data-b="" class="on">全部 5</button>'),
    'open_bar': ('=index.html', '<div class="chips">', '<a class="go2" href="/trip/xa3/">翻开 →</a><div class="chips">'),
    # —— A /where/
    'card_links': ('where/index.html', '<p class="cl">', '<a href="/d/beijing/">a</a><a href="/d/beijing/">b</a><p class="cl">'),
    'where_exact': (JS, 'hits.sort(function(a,b){return(a._x-b._x)||', 'hits.sort(function(a,b){return '),
    'where_fit_hide': (JS, 'if(st.fit&&!st.q&&(v===', 'if(st.fit&&(v==='),
    'orgkey_pick': (JS, "zOrgSet(b.dataset.v);else savePk();", "zLSs('zouni_pick',JSON.stringify({o:b.dataset.v}));zOrgSet(b.dataset.v);"),
    'n_per_line': (JS, "zLSs('zouni_n',String(N));upd()})", "zLSs('zouni_n_'+me.id,String(N));zLSs('zouni_n',String(N));upd()})"),
    'date_legacy_key': (JS, "zDateSet(dk.value);applyStart(dk.value);", "zDateSet(dk.value);zLSs('zouni_home_date',dk.value);applyStart(dk.value);"),
    # —— A 目的地页
    'dest_sjd_p': ('d/guangdong/index.html', '<section class="se">', '<p class="sjd"><b>舌尖上的中国拍过</b>x</p><p class="sjd"><b>风味人间拍过</b>y</p><section class="se">'),
    'dest_legend': ('d/shaanxi/index.html', '<ul class="trips">', '<p class="hlegend"><span><a href="/trip/xa3/">x</a></span></p><ul class="trips">'),
    'dest_5a': ('d/shaanxi/index.html', '<ul class="qual">', '<ul class="qual"><li><span>x</span><small>5A</small></li><li><span>y</span><small>5A</small></li>'),
    'dest_open': ('d/shaanxi/index.html', '<ul class="niche">', '<ul class="niche"><li><div class="nh"><b>x</b><span class="st open">可以去</span></div></li><li><div class="nh"><b>y</b><span class="st open">可以去</span></div></li>'),
    'dest_gb': ('d/shaanxi/index.html', '<ul class="qual mus">', '<ul class="qual mus"><li><span><b>x</b></span><em class=gb>国宝</em></li><li><span><b>y</b></span><em class=gb>国宝</em></li>'),
    'dest_nogroup': ('d/shaanxi/index.html', '<li class="grp">', '<li class="xgrp">'),
    # —— A 跟片走
    'pian_two_links': ('shejian/index.html', '<ul class="sjl">', '<ul class="sjl"><li><b>x</b><small><a href="/trip/xa3/#d1">a</a> <a href="/trip/xa3/#d2">b</a> <a href="/trip/xa3/#d3">c</a></small></li>'),
    'pian_pv_open': ('yingxiang/index.html', '<details class="pvd"', '<h3 id="pvx">x</h3><details class="pvd"'),
    'pian_nh': ('pian/index.html', '<em>', '<em>已排进 3 处 · '),
    'trip_pure_place': ('trip/xa3/index.html', '<p class="lead"', '<p class="sjn"><b>中国影像方志</b>拍过黎平</p><p class="lead"'),
    # —— A toast
    'toast_echo': (JS, "cl();replan(sec);return}", "cl();replan(sec);toast('多待 30 分钟，后面的时间重排了');return}"),
    'toast_fav': (JS, "else{saveOffline(function(ok){if(!ok)return;fb.classList.add('saved')})}})}", "else{toast('已收进，可在首页「我的行程」查看');saveOffline(function(ok){if(!ok)return;fb.classList.add('saved')})}})}"),
    'toast_wx_load': (JS, "var MOB=/iPhone|iPad|Android/i.test(navigator.userAgent),WXB=/MicroMessenger/i.test(navigator.userAgent);", "var MOB=/iPhone|iPad|Android/i.test(navigator.userAgent),WXB=/MicroMessenger/i.test(navigator.userAgent);if(WXB)setTimeout(function(){toast('微信里打不开高德、携程、点评、小红书：点右上角 ··· 选“在浏览器打开”')},900);"),
    # —— B
    'home_row': ('trip/xa3/index.html', '<li class="r stay">', '<li class="r dep"><time>21:10</time><span class="dot"></span><div class="rb"><p class="m">出发 → 住处</p><p class=s>打车或步行</p></div></li><li class="r stay">'),
    'rest_css': (CSS, '.r[data-x="rest"]{min-height:32px;padding:2px 0}', '.r[data-x="rest"]{min-height:60px;padding:12px 0}'),
    'gap_css': (CSS, '.r[data-x="gap"]{min-height:32px;padding:2px 0}', '.r[data-x="gap"]{min-height:70px;padding:14px 0}'),
    'gen_css': (CSS, '.stays.gen{margin-top:10px;background:none;display:flex;', '.stays.gen{margin-top:10px;display:block;'),
    'lead_show': ('trip/g318/index.html', '<p class="lead" hidden>', '<p class="lead">'),
    'alt_long': ('trip/xl9a/index.html', '高反：不喝酒、慢慢走，头疼恶心就往低处走。', '到了先歇一天，别洗澡、别喝酒、别剧烈运动，慢慢走、多喝水；出发前问问医生，备好便携氧气瓶；头疼、恶心、嘴唇发紫别硬撑，马上往低处走。'),
    'alt_flat': ('trip/xl9a/index.html', '<p class="alt hi">', '<p class="alt">'),
    'pfx_all': ('trip/hss1a/index.html', '<p class="fnote">', '<p class="fnote">苏轼：'),
    # —— C
    'word_benqi': ('where/index.html', '<a class="home" href="/">首页</a>', '<a class="home" href="/">本期</a>'),
    'word_route_map': (JS, '<span>看地图</span><i>›</i>', '<span>看路线图</span><i>›</i>'),
    'price_k': ('trip/xa3/index.html', '<b class="price"', '<b class="x">¥1.8K–2.6K</b><b class="price"'),
    'adj_text': (JS, 'aria-label="改这一站">改这站</button>', 'aria-label="调整这一站">调整</button>'),
    'in_toggle': (JS, "st[k]=(k!=='o'&&st[k]===b.dataset.v)?'':b.dataset.v;", "st[k]=b.dataset.v;"),
    'in_ime': (JS, "if(comp_||(e&&e.isComposing))return;st.q=", "st.q="),
    'in_autocomplete': ('where/index.html', '<input type="search" enterkeyhint="search"', '<input type="search"'),
    'in_baddate': (JS, "function zDateGet(){var v=zLS('zouni_date');if(v==null)return null;if(!zDateOk(v)){zLSd('zouni_date');return null}", "function zDateGet(){var v=zLS('zouni_date');if(v==null)return null;"),
    'in_trunc': (JS, "toast('这个链接不完整，现在看到的是原版行程')", "void 0"),
    'in_sug_all': (JS, "<li class=\"hall\">", "<li class=\"hx\">"),
    'a11y_hmap': (JS, "if(!f.querySelector('a')){f.setAttribute('role','button');f.setAttribute('tabindex','0')}", "f.setAttribute('role','button');f.setAttribute('tabindex','0');"),
    'a11y_big': (CSS, '.glance b,.glance b.big,.glance b.price{height:auto;min-height:28px;line-height:28px;line-height:max(28px,1.25em);overflow:visible}', '.glance b,.glance b.big,.glance b.price{height:28px;overflow:hidden}'),
    'a11y_pkmax': (CSS, '.pk{max-height:calc(100vh - 16px);max-height:calc(100dvh - 16px);overflow-y:auto;', '.pk{'),
    'a11y_dock': (CSS, '@media (max-height:500px){.dock{position:static}}', ''),
    'dev_inset': (CSS, '.pk-mask{top:0;right:0;bottom:0;left:0}.tv{top:0;right:0;bottom:0;left:0}.hmap-zoom{top:0;right:0;bottom:0;left:0}', ''),
    'dev_fav320': (CSS, '@media (max-width:359px){.dock .tvbtn{', '@media (max-width:359px){.dock .fav span{display:none}.dock .tvbtn{'),
    # —— D
    'd_title': ('trip/xv02a/index.html', '<h1>五天，', '<h1>5天(五天)，'),
    'd_canon': ('trip/cq3/index.html', '<link rel="canonical" href="https://zouni.app/trip/cq4d/">', '<link rel="canonical" href="https://zouni.app/trip/cq3/">'),
    'd_sisters': ('trip/xa3/index.html', '<p class="sis">', '<p class="sisx">'),
    'd_label': ('trip/xa5d/index.html', 'data-label="西安 5\u00a0天（深度）"', 'data-label="西安 3\u00a0天"'),
    # —— 补充（上面每一类里剩下的判据，各一个）
    'date_row': ('=index.html', '<div class="nowh">', '<div class="nowx">'),
    'wiz_sync': (JS, "if(k==='d'){window.zBandSet=BI[st.d]||'';document.dispatchEvent(new Event('zouni:bandset'))}", "if(k==='d'){}"),
    'where_map_land': (JS, "st.fit=false;st.map=false;inp.value=q0;", "st.fit=false;inp.value=q0;"),
    'where_alias': ('where/index.html', '出国 国外 境外 海外 ', ''),
    'migrate_off': (JS, "if(L.getItem('zouni_v')==='2')return;var ks=[]", "return;var ks=[]"),
    'dest_dot_text': ('d/japan/index.html', '红圈是排好的线路（点名字进去）', '红圈是排好的线路（点名字进去），小黑点是 5A 和世界遗产'),
    'follow_flat': ('long/index.html', '<span class="lb"><h2>', '<span class="lb"><span class="tg">平路</span><h2>'),
    'pv_hash': (JS, "el.classList.contains('pvd'))el.open=true", "el.classList.contains('pvd'))void 0"),
    'store_silent': (JS, "toast('这个浏览器存不下，改动关掉页面就没了')", "void 0"),
    'toast_cal': (JS, "if(window.zIcs)window.zIcs()}if(b.dataset.a==='print')", "if(window.zIcs)window.zIcs();toast('日历文件好了，打开后选“全部添加”')}if(b.dataset.a==='print')"),
    'toast_dur': (JS, "Math.max(1700,Math.min(6000,String(t).length*140))", "1700"),
    'word_sub': ('=index.html', '按月份挑国内外', '按月份挑目的地'),
    'word_pick': (JS, '<b>替我挑三条行程</b>', '<b>替我挑三条</b>'),
    'word_zuijia': ('long/index.html', '<span class="lm">', '<span class="lm">最佳 3–5 月 · '),
    'word_zhixian': (JS, "'离'+on2+'约 '", "on2+'过去直线约 '"),
    'word_left': ('=index.html', ' · 最好到 ', ' · 还剩 5 天 '),
    'in_blur': (JS, "if(e.key==='Enter'||e.keyCode===13)inp.blur()", "void 0"),
    'v_goodline': (CSS, '.wbar .goodline{display:block;-webkit-line-clamp:unset;overflow:visible}', ''),
    'v_heading': ('where/index.html', '<h1>走哪儿</h1>', '<h1>走哪儿</h1><h3>x</h3>'),
    'v_esc': (JS, "if(!ac||ac===B||ac===document.documentElement||!document.contains(ac))try{L.trig.focus({preventScroll:true})}catch(e){}", ""),
}
env = Env(INJ)
check, guard = env.check, env.guard
TABLE = sys.argv[sys.argv.index('--table') + 1] if '--table' in sys.argv else None
_cache = {}


def GET(path):
    if path not in _cache:
        try: _cache[path] = urllib.request.urlopen(env.B + path, timeout=30).read().decode('utf-8', 'replace')
        except Exception as e: _cache[path] = ''
    return _cache[path]


def text(h): return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', h))


ALLTRIPS = sorted(d for d in os.listdir(os.path.join(env.site, 'trip')) if os.path.exists(os.path.join(env.site, 'trip', d, 'index.html')))
ALLDEST = sorted(d for d in os.listdir(os.path.join(env.site, 'd')) if os.path.exists(os.path.join(env.site, 'd', d, 'index.html')))


def prefetch(paths):
    with concurrent.futures.ThreadPoolExecutor(8) as ex: list(ex.map(GET, paths))


def count_trips(pat, flags=0):
    prefetch(['/trip/%s/' % t for t in ALLTRIPS])
    return sum(len(re.findall(pat, GET('/trip/%s/' % t), flags)) for t in ALLTRIPS)


# 浏览器里量“第一屏可点元素个数”：从页顶到“现在去正好”第一张卡之前的所有可见控件
FIRST = """()=>{const H=innerHeight;let n=0;const vis=(e)=>{const r=e.getBoundingClientRect();if(r.width<1||r.height<1)return false;if(r.top>=H||r.bottom<=0)return false;const s=getComputedStyle(e);return s.visibility!=='hidden'&&s.display!=='none'&&!e.closest('[hidden]')};
 const card=document.querySelector('#now .items li:not([hidden])');const cy=card?card.getBoundingClientRect().top:1e9;
 const els=[...document.querySelectorAll('.home a[href],.home button,.home input:not([type=hidden]),.home select,.home summary')].filter(e=>vis(e)&&e.getBoundingClientRect().top<cy-2&&!e.closest('#now .items'));
 return {n:els.length,names:els.map(e=>(e.className||e.tagName)+':'+(e.textContent||e.name||'').trim().slice(0,8)),card:card?Math.round(cy):-1,H:H}}"""


def open_filter(pg):      # /where/ 的“筛选”面板：已经开着（sessionStorage 记得）就不再点（再点会关）
    if pg.evaluate("document.querySelector('.flt').hidden"): pg.click('.ftog')
    pg.wait_for_timeout(150)


def dest_height(pg, did):
    pg.goto(env.B + '/d/%s/' % did, wait_until='networkidle'); pg.wait_for_timeout(300)
    return pg.evaluate('document.documentElement.scrollHeight')


with sync_playwright() as p:
    br = p.chromium.launch()
    c = new_ctx(br, p); pg = new_page(env, c)

    if TABLE:
        import http.server, socketserver, threading, functools
        srv0 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(type('H', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None}), directory=os.path.abspath(TABLE)))
        threading.Thread(target=srv0.serve_forever, daemon=True).start(); B0 = 'http://127.0.0.1:%d' % srv0.server_address[1]
        for label, base in (('旧', B0), ('新', env.B)):
            pg.goto(base + '/', wait_until='networkidle'); pg.wait_for_timeout(1200)
            f = pg.evaluate(FIRST)
            sec = pg.evaluate("[...document.querySelectorAll('.home .toc')].map(s=>s.id||s.querySelector('h2').textContent.slice(0,8))")
            print(label, '首页 首屏可点元素 %d，第一张卡离页顶 %dpx（视口 %d）' % (f['n'], f['card'], f['H']), f['names'], '货架', sec)
            for did in ('guangdong', 'sichuan', 'shaanxi'):
                pg.goto(base + '/d/%s/' % did, wait_until='networkidle'); pg.wait_for_timeout(300)
                print(label, '目的地页 %s 整页高 %dpx' % (did, pg.evaluate('document.documentElement.scrollHeight')))
            pg.goto(base + '/yingxiang/', wait_until='networkidle'); pg.wait_for_timeout(300)
            print(label, '/yingxiang/ 整页高 %dpx' % pg.evaluate('document.documentElement.scrollHeight'))
        sys.exit(0)

    # ═══════════════ A · 首页
    with guard('A1'):
        h = GET('/')
        check('A1 首页没有“长途和自驾”货架（#drive、标题、“按目的地看全部自驾线路”）', 'id="drive"' not in h and '长途和自驾' not in h and '按目的地看全部自驾线路' not in h)
        home_dir = os.path.join(env.site, 'index.html')
        check('A1b 首页 HTML ≤ 400KB（旧 %dKB）' % 0, len(h.encode('utf-8')) <= 400 * 1024)
    with guard('A2'):
        goto(env, pg, '/', 1200); f = pg.evaluate(FIRST)
        check('A2 首页首屏可点元素 ≤ 12（旧 14）：%d  %s' % (f['n'], f['names']), f['n'] <= 12, f)
        check('A2b 第一张卡进首屏（离页顶 %d < 视口 %d；旧 ≈ 770）' % (f['card'], f['H']), 0 < f['card'] < f['H'] - 60, f)
        h = GET('/')
        check('A2c 搜索框没有“搜”按钮（回车搜，enterkeyhint=search）', '<button' not in re.search(r'<form class="hsearch".*?</form>', h, re.S).group(0) and 'enterkeyhint="search"' in h)
        check('A2d 天数键没有“全部”（再点一次取消）：只有 3 个键', len(re.findall(r'<div class="dchips".*?</div>', h, re.S)[0].split('<button')) - 1 == 3 and 'data-b=""' not in h)
        check('A2e 封面没有“翻开 →”整行按钮：封面标题本身是链接（a.go 包 h2）', re.search(r'<a class="go" href="/trip/\w+/"><h2>', h) is not None and '>翻开 →</a>' not in h)
        check('A2f 日期并进“现在去正好”标题行（.nowh 里有 h2 和 .datebar）', re.search(r'<div class="nowh"><h2>.*?</h2><div class="datebar">', h, re.S) is not None)
        # 点天数键再点一次 = 取消
        pg.click('.dchips button[data-b="d1"]'); pg.wait_for_timeout(200); a = pg.evaluate("document.querySelector('.dchips .on')&&document.querySelector('.dchips .on').dataset.b")
        pg.click('.dchips button[data-b="d1"]'); pg.wait_for_timeout(200); b = pg.evaluate("document.querySelector('.dchips .on')")
        check('A2g 天数键：点一次选中（%s），再点一次取消（%s）' % (a, b), a == 'd1' and b is None, (a, b))
    with guard('A2h'):   # 向导“几天”和天数键同一个状态
        goto(env, pg, '/', 1200)
        pg.click('.pkh'); pg.wait_for_timeout(200); pg.click('.pkr[data-k="d"] button[data-v="m"]'); pg.wait_for_timeout(300)
        on = pg.evaluate("document.querySelector('.dchips .on')&&document.querySelector('.dchips .on').dataset.b")
        pg.click('.dchips button[data-b="d3"]'); pg.wait_for_timeout(300)
        wz = pg.evaluate("(document.querySelector('.pkr[data-k=\"d\"] .on')||{}).dataset&&document.querySelector('.pkr[data-k=\"d\"] .on').dataset.v")
        check('A2h 向导“几天”和“现在去正好”的天数键是同一个状态（向导选 4–5 天 → 键 %s；点“一周以上” → 向导 %s）' % (on, wz), on == 'd2' and wz == 'l', (on, wz))

    # ═══════════════ A · /where/
    with guard('A3'):
        h = GET('/where/'); cards = re.findall(r'<li class="card".*?</li>', h, re.S)
        mx = max(len(re.findall(r'href="/d/([\w-]+)/(?:#q)?"', cc)) for cc in cards)
        check('A3 /where/ 每张卡片指向同一个目的地页的链接 ≤ 2（卡头 + 一条；旧 4）：最多 %d（%d 张卡）' % (mx, len(cards)), len(cards) > 60 and mx <= 2, mx)
        check('A3b 卡片里“片里”改叫“拍过”、不再是链接', '<b>片里</b>' not in h and re.search(r'<p class="kv"><b>拍过</b><span>', h) is not None)
        check('A3c “出国 / 国外”能搜到国外目的地（data-q 里有别名）', re.search(r'data-q="[^"]*出国 国外', h) is not None)
        check('A3d 页签叫“欧美及其他”，没有“更远”', '欧美及其他 · ' in h and '更远 ·' not in h)
    with guard('A3e'):
        goto(env, pg, '/where/', 600)
        # 掺一条“天数更少、名字更长”的诱饵进索引：没有精确匹配规则时它会排在 xa3 前面
        def _decoy(route):
            r = route.fetch(); b = r.text().replace('window.ZTIDX=[', 'window.ZTIDX=[["decoy","西安 加长版",2,"¥1","西安3天加长版|x","西安3天加长版x"],', 1)
            route.fulfill(response=r, body=b)
        pg.route('**/assets/tidx.js', _decoy)
        open_filter(pg); pg.fill('.flt input', '西安 3 天'); pg.wait_for_timeout(1500)
        first = pg.evaluate("(document.querySelector('.wtr li a')||{}).getAttribute&&document.querySelector('.wtr li a').getAttribute('href')")
        check('A3e 搜“西安 3 天”：行程精确匹配排第一（%s）' % first, first == '/trip/xa3/', first)
        pg.unroute('**/assets/tidx.js'); pg.fill('.flt input', ''); pg.wait_for_timeout(300)
        pg.click('.mon button[data-m="1"]'); pg.wait_for_timeout(200); pg.fill('.flt input', '西藏'); pg.wait_for_timeout(800)
        n = pg.evaluate("document.querySelectorAll('#domestic .card:not([hidden])').length")
        check('A3f 1 月搜“西藏”：只要搜索框里有字就不再按“只看合适的”悄悄滤掉（%d 张卡）' % n, n >= 1, n)
        # 搜索落地不被地图占掉
        pg.evaluate("sessionStorage.setItem('zouni_where',JSON.stringify({st:{fit:true,d:'',low:false,q:'',niche:false,near:false,bud:0,tab:'domestic',drive:false,tag:'',map:true,zoom:''},m:10,open:false}))")
        pg.goto(env.B + '/where/?q=%E8%A5%BF%E5%AE%89', wait_until='networkidle'); pg.wait_for_timeout(800)
        check('A3g 带 ?q= 落地时不显示地图（即使上次开着地图）', pg.evaluate("!document.querySelector('.wmap')"))
    # 出发地一张表、一个键
    with guard('A4'):
        js = GET('/assets/site.js'); m = re.search(r"var ZORIG=\{(.*?)\};", js, re.S)
        zo = dict((k, (float(a), float(b))) for k, a, b in re.findall(r"'([^']+)':\[([\d.]+),([\d.]+)\]", m.group(1))) if m else {}
        bs = open(os.path.join(ROOT, 'tools', 'build_site.py'), encoding='utf-8').read()
        pm = re.search(r"\nORIGINS = \{(.*?)\}\n", bs, re.S)
        py = dict((k, (float(a), float(b))) for k, a, b in re.findall(r"'([^']+)': \(([\d.]+), ([\d.]+)\)", pm.group(1))) if pm else {}
        bad = [k for k in py if k not in zo or abs(zo[k][0] - py[k][0]) > .02 or abs(zo[k][1] - py[k][1]) > .02]
        check('A4 出发地城市表只有一张：site.js 的 ZORIG（%d 城）；build_site 的“怎么去”默认枢纽表（%d 城）与它同坐标（不同：%s）；走哪儿、向导不再各写一张' % (len(zo), len(py), bad), len(zo) >= 30 and not bad and "var ORG={'北京'" not in js and "var C={'北京'" not in js and 'Object.keys(ZORIG)' in js, bad)
        check('A4b /where/ 的出发地下拉由 ZORIG 补出来：HTML 里只剩“不限”', len(re.findall(r'<option', re.search(r'<select class="org".*?</select>', GET('/where/'), re.S).group(0))) == 1)
    with guard('A4c'):
        c2 = new_ctx(br, p); pg2 = new_page(env, c2); goto(env, pg2, '/where/', 600)
        n_opt = pg2.evaluate("document.querySelectorAll('select.org option').length")
        open_filter(pg2); pg2.select_option('select.org', '成都'); pg2.wait_for_timeout(300)
        org = ls(pg2, 'zouni_org'); pick = ls(pg2, 'zouni_pick')
        check('A4c /where/ 选出发地：全站只写 zouni_org=%s；zouni_pick 里没有 o/lat/lng（%s）；下拉 %d 项' % (org, pick, n_opt), org == '成都' and (not pick or not re.search(r'"(o|lat|lng)"', pick)) and n_opt >= 31, (org, pick, n_opt))
        goto(env, pg2, '/', 1000); pg2.click('.pkh'); pg2.wait_for_timeout(200)
        wz = pg2.evaluate("(document.querySelector('.pkr[data-k=\"o\"] .on')||{}).textContent")
        pg2.click('.pkr[data-k="o"] button[data-v="上海"]'); pg2.wait_for_timeout(300)
        o2, k2 = ls(pg2, 'zouni_org'), ls(pg2, 'zouni_pick')
        check('A4c2 向导里选出发地：也只写 zouni_org=%s，zouni_pick 里没有出发地（%s）' % (o2, k2), o2 == '上海' and (not k2 or '"o"' not in k2), (o2, k2))
        pg2.click('.pkr[data-k="o"] button[data-v="成都"]'); pg2.wait_for_timeout(300)
        goto(env, pg2, '/trip/sz3/', 800)
        tr = pg2.evaluate("(document.querySelector('.ogsel')||{}).value")
        goto(env, pg2, '/where/', 700)
        wh = pg2.evaluate("document.querySelector('select.org').value")
        check('A4d 出发地同源：向导里是“%s”、线路页是“%s”、回到 /where/ 还是“%s”（都是成都）' % (wz, tr, wh), wz == '成都' and tr == '成都' and wh == '成都', (wz, tr, wh))
        # 人数全站一个
        goto(env, pg2, '/trip/xa3/', 800); pg2.click('.pp'); pg2.wait_for_timeout(200); pg2.click('.ppl button[data-d="1"]'); pg2.wait_for_timeout(300)
        keys = pg2.evaluate("Object.keys(localStorage).filter(k=>/^zouni_(n|nt)(_|$)/.test(k)&&k!=='zouni_np_bad'&&!/^zouni_np_/.test(k))")
        goto(env, pg2, '/trip/sz3/', 800); pg2.click('.pp'); pg2.wait_for_timeout(200)
        shown = pg2.evaluate("(document.querySelector('.ppl b')||{}).textContent")
        check('A4e 人数全站一个键 zouni_n（%s）：一条线上改成 3 人，另一条线也是 %s' % (keys, shown), keys == ['zouni_n'] and '3' in (shown or ''), (keys, shown))
        # 日期全站一个键
        goto(env, pg2, '/trip/xa3/', 600)
        pg2.evaluate("(function(){var d=document.querySelector('.dpk');d.value='2027-03-06';d.dispatchEvent(new Event('change'))})()"); pg2.wait_for_timeout(400)
        dk = pg2.evaluate("Object.keys(localStorage).filter(k=>/^zouni_(start|home_date)/.test(k)||k==='zouni_date')")
        goto(env, pg2, '/trip/sz3/', 800); v2 = pg2.evaluate("document.querySelector('.dpk').value")
        goto(env, pg2, '/', 1500); hv = pg2.evaluate("document.querySelector('.hdpk').value")
        check('A4f 日期全站一个键 zouni_date（%s）：改一条线 = 另一条线（%s）和首页（%s）都是 2027-03-06' % (dk, v2, hv), dk == ['zouni_date'] and v2 == '2027-03-06' and hv == '2027-03-06', (dk, v2, hv))
        c2.close()
    with guard('A4g'):   # 旧键第一次打开时并成新键，旧键删掉；分享链接继续认老链接
        fut = (__import__('datetime').date.today() + __import__('datetime').timedelta(days=40)).isoformat()
        c3 = new_ctx(br, p, storage={'zouni_start_xa3': fut, 'zouni_startt_xa3': '5', 'zouni_home_date': '2099-01-01', 'zouni_home_datet': '9', 'zouni_n_xa3': '4', 'zouni_nt_xa3': '3', 'zouni_pick': json.dumps({'o': '武汉', 'd': 'm', 'w': 'c'})})
        pg3 = new_page(env, c3); goto(env, pg3, '/trip/xa3/', 900)
        st = pg3.evaluate("(function(){var o={};Object.keys(localStorage).filter(k=>/^zouni_/.test(k)&&k!=='__seeded').forEach(k=>o[k]=localStorage.getItem(k));return o})()")
        left = [k for k in st if re.match(r'zouni_(start_|startt_|n_|nt_|home_date|home_n)', k)]
        check('A4g 老键并成新键：zouni_date=2099-01-01（首页那条更新）、zouni_n=4、zouni_org=武汉、旧键删光（剩 %s；%s）' % (left, st), st.get('zouni_date') == '2099-01-01' and st.get('zouni_n') == '4' and st.get('zouni_org') == '武汉' and not left and '"o"' not in st.get('zouni_pick', '') and '"w":"c"' in st.get('zouni_pick', ''), st)
        c3.close()
    with guard('A4h'):   # 脏日期（input #5）
        c4 = new_ctx(br, p, storage={'zouni_date': 'abc'}); pg4 = new_page(env, c4)
        goto(env, pg4, '/trip/xa3/', 900); t1 = pg4.evaluate("document.querySelector('.dt').textContent")
        goto(env, pg4, '/', 1500); t2 = pg4.evaluate("document.querySelector('.hdt b').textContent")
        check('A4h 脏日期（localStorage 里是 abc）：线路页 / 首页都不出现 NaN（%s / %s），脏值被清掉（%s）' % (t1.strip(), t2.strip(), ls(pg4, 'zouni_date')), 'NaN' not in t1 and 'NaN' not in t2 and ls(pg4, 'zouni_date') is None, (t1, t2))
        c4.close()
    with guard('A4i'):   # 分享链接：老格式能认；截断的链接要说一声（input #6）
        c5 = new_ctx(br, p); pg5 = new_page(env, c5)
        import base64
        old = base64.urlsafe_b64encode(json.dumps({'zouni_start_': '2099-02-02', 'zouni_n_': 5}).encode()).decode().rstrip('=')
        pg5.goto(env.B + '/trip/xa3/#mine=' + old, wait_until='networkidle'); pg5.wait_for_timeout(1200)
        check('A4i 老格式分享链接 #mine= 继续认：日期 %s、人数 %s' % (ls(pg5, 'zouni_date'), ls(pg5, 'zouni_n')), ls(pg5, 'zouni_date') == '2099-02-02' and ls(pg5, 'zouni_n') == '5')
        pg5.goto(env.B + '/trip/sz3/#m=AAAA', wait_until='networkidle'); pg5.wait_for_timeout(1500)
        tt = pg5.evaluate("(document.querySelector('.toast')||{}).textContent")
        check('A4j 截断 / 乱码的分享链接：弹“这个链接不完整，现在看到的是原版行程”并清掉坏 hash（%s）' % tt, tt and '不完整' in tt and '#' not in pg5.url, (tt, pg5.url))
        c5.close()

    # ═══════════════ A · 目的地页
    with guard('A5'):
        prefetch(['/d/%s/' % d for d in ALLDEST])
        leg = sum(len(re.findall(r'<p class="hlegend">.*?</p>', GET('/d/%s/' % d), re.S)) for d in ALLDEST if '<figure class="hmap dmap">' in GET('/d/%s/' % d))
        check('A5 目的地页地图下面没有无标题的“未上图线路名”链接串（旧 49 页 457 个链接）：%d 段' % leg, leg == 0, leg)
        bad = [d for d in ALLDEST if '小黑点' in GET('/d/%s/' % d) and not re.search(r'<circle[^>]*r="[12](\.\d+)?"', GET('/d/%s/' % d))]
        nodots = sum(1 for d in ALLDEST if '红圈是排好的线路' in GET('/d/%s/' % d) and '小黑点' not in GET('/d/%s/' % d))
        check('A5b 没有黑点的页面不写“小黑点”（%d 页只写红圈；有说明却画不出黑点的：%s）' % (nodots, bad[:3]), not bad and nodots >= 10, bad)
        g = GET('/d/guangdong/index.html'.replace('/index.html', '/'))
        n_det = len(re.findall(r'<details class="sjd sjdd">', g)); n_p = len(re.findall(r'<p class="sjd">', re.sub(r'<details class="sjd sjdd">.*?</details>', '', g, flags=re.S)))
        in_eat = bool(re.search(r'<h2>吃</h2>.*?class="sjd', g.split('</section>')[0 + [i for i, s_ in enumerate(g.split('</section>')) if '<h2>吃</h2>' in s_][0]], re.S)) if '<h2>吃</h2>' in g else False
        check('A5c 广东页：影视挂钩收成一个折叠（details %d），没有一段一段的 p.sjd（%d），也不在“吃”里面' % (n_det, n_p), n_det == 1 and n_p == 0 and not in_eat, (n_det, n_p, in_eat))
        s = GET('/d/shaanxi/')
        five = len(re.findall(r'<small>5A</small>', s)); gb = len(re.findall(r'class=gb', s)); opn = len(re.findall(r'class="st open"[^>]*>可以去', s)); wh = len(re.findall(r'<small>世界遗产</small>', s))
        check('A5d 目的地页默认值标签只在偏离默认时出现：陕西页“5A”标 %d、红框“国宝” %d、“可以去” %d 个（都应 0）；“世界遗产”标仍在 %d 个' % (five, gb, opn, wh), five == 0 and gb == 0 and opn == 0 and wh >= 1, (five, gb, opn, wh))
        pr = open(os.path.join(env.site, 'follow')) if False else None
        fol = [d for d in os.listdir(os.path.join(env.site, 'follow')) if os.path.isdir(os.path.join(env.site, 'follow', d))][:12]
        bad = 0
        for d in fol:
            t = GET('/follow/%s/' % d); bad += len(re.findall(r'<span class="tg[^"]*">平路</span>', t)) + len(re.findall(r'\d+ 月出发', t))
        lg = GET('/long/'); bad += len(re.findall(r'<span class="tg[^"]*">平路</span>', lg)) + len(re.findall(r'最佳', lg))
        check('A5e /follow/<主题>/ 和 /long/ 的卡片没有“平路”标签、“N 月出发”、“最佳”（%d 处）' % bad, bad == 0, bad)
    with guard('A5f'):   # 线路按 group_city 归组
        s = GET('/d/shaanxi/'); k = len(re.findall(r'<li class="grp"><h3>', s)); lis = len(re.findall(r'<li data-n=', s))
        tj = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'trips.json'), encoding='utf-8'))['trips']
        exp = len([t for t in tj if t.get('dest') == 'shaanxi' and re.match(r'Route\.dc\.html#', t.get('page') or '')])
        check('D1 陕西页线路按城市归组（%d 组）、线路一条不少（%d 条；trips.json 里陕西 %d 条）' % (k, lis, exp), k >= 3 and lis >= exp - 3, (k, lis, exp))
        # 过滤时空组标题隐藏
        goto(env, pg, '/d/shaanxi/', 500); pg.click('.tf button[data-f="d"]'); pg.wait_for_timeout(200)
        vis = pg.evaluate("[...document.querySelectorAll('.trips .grp:not([hidden])')].every(g=>{let n=g.nextElementSibling;while(n&&!n.classList.contains('grp')){if(!n.hidden)return true;n=n.nextElementSibling}return false})")
        check('D1b 过滤后没有“只剩标题没有线路”的组', vis)

    # ═══════════════ A · 跟片走
    with guard('A6'):
        pages = ['/shejian/', '/fengwei/', '/guobao/', '/xiangchou/', '/yingxiang/', '/hexi/', '/yuanchandi/', '/zaocan/']
        bad = []
        for pth in pages:
            t = GET(pth)
            for li in re.findall(r'<li>(?:(?!</li>).)*</li>', t, re.S):
                outside = re.sub(r'<details class="gm">.*?</details>', '', li, flags=re.S)
                if len(re.findall(r'href="/trip/', outside)) > 1: bad.append(pth); break
        check('A6 跟片走：每条片子条目只放 1 个主行程链接（其余折叠“另有 N 条”）；超限页：%s' % bad, not bad and any('class="gm"' in GET(x) for x in pages), bad)
        y = GET('/yingxiang/')
        check('A6b 中国影像方志按省折叠：details.pvd %d 个、没有裸的省份 h3' % len(re.findall(r'<details class="pvd"', y)), len(re.findall(r'<details class="pvd"', y)) >= 20 and not re.search(r'<h3 id="pv', y), None)
        check('A6c /pian/ 目录里没有“已排进 N 处”', '已排进' not in GET('/pian/') and '讲过' not in GET('/pian/'))
        pc = count_trips(r'<p class="sjn"><b>中国影像方志</b>(?:拍过|推荐)?[^<（]{1,12}</p>')
        check('A6d 行程页里“中国影像方志拍过 X”纯地名挂钩不显示（旧 1241 行）：%d 行' % pc, pc == 0, pc)
        pn = count_trips(r'<p class="sjn"><b>(?:舌尖上的中国|如果国宝会说话)</b>')
        check('A6e 有具体菜名 / 文物名的挂钩保留（%d 行）' % pn, pn > 500, pn)
    with guard('A6f'):
        goto(env, pg, '/yingxiang/', 600); pg.evaluate("location.hash='#pv3'"); pg.wait_for_timeout(300)
        check('A6f 点上面的省名跳转会把那个省的折叠展开', pg.evaluate("document.getElementById('pv3').open===true"))

    # ═══════════════ A · toast
    with guard('A7'):
        goto(env, pg, '/trip/xa3/', 900)
        pg.click('.fav'); pg.wait_for_timeout(500); t1 = pg.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        check('A7a 收进行程：没有复述类 toast（“已收进，可在首页…”）；按钮已变“已收进”（toast=%s）' % t1, not t1 and pg.evaluate("document.querySelector('.fav').classList.contains('saved')||/已收进/.test(document.querySelector('.fav').textContent)"), t1)
        pg.click('.fav'); pg.wait_for_timeout(500)
        t2 = pg.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent"); u2 = pg.evaluate("!!document.querySelector('.toast .toast-act')")
        check('A7b 取消收藏：只留带“撤销”的 toast（%s，撤销按钮 %s）' % (t2, u2), bool(t2) and u2, (t2, u2))
        pg.evaluate("[...document.querySelectorAll('.toast')].forEach(e=>e.remove())")
        pg.evaluate("document.querySelector('.tl .r.see .adj, .tl .r.see button.adj')&&0")
        # 多待 / 少待
        pg.click('.tl .r.see .adj >> nth=0'); pg.wait_for_timeout(500)
        has = pg.evaluate("!!document.querySelector('.pk [data-d=\"30\"], .pk [data-d=\"-30\"]')")
        if has:
            pg.click('.pk [data-d="30"]'); pg.wait_for_timeout(600)
        t3 = pg.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        check('A7c 多待 30 分钟：没有 toast（时间表本身变了；toast=%s；找得到“多待”按钮 %s）' % (t3, has), has and not t3, (t3, has))
        js = GET('/assets/site.js')
        gone = [x for x in ('改成 \'+fmt(d)+\' 出发了', '加好了，日期和底栏都跟着变了', '日历文件好了', '恢复了原来的安排', '换回原来的了', '按现在重排了') if x in js]
        check('A7d site.js 里复述类 toast 文案都没了（还在：%s）' % gone, not gone, gone)
        check('A7e 日历说明搬进了按钮副标题（“下载后…选“全部添加””出现在 button 里，不在 toast 里）', '下载后打开，选“全部添加”' in js and "toast('日历" not in js)
        check('A7f 没有按钮的 toast 时长按字数（site.js 里有 Math.max(1700,Math.min(6000,String(t).length*140))）', 'Math.max(1700,Math.min(6000,String(t).length*140))' in js)
    with guard('A7g'):   # 微信提示：首次点“复制”才说
        cw = new_ctx(br, p, user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 MicroMessenger/8.0.40 Mobile/15E148')
        pw = new_page(env, cw); goto(env, pw, '/trip/xa3/', 2200)
        t0 = pw.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        pw.evaluate("document.querySelectorAll('.cpy')[0].click()"); pw.wait_for_timeout(500); t1 = pw.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        pw.evaluate("[...document.querySelectorAll('.toast')].forEach(e=>e.remove())"); pw.evaluate("document.querySelectorAll('.cpy')[1].click()"); pw.wait_for_timeout(500); t2 = pw.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        check('A7g 微信里：进页面不弹提示（%s）；第一次点“复制”才说“右上角”（%s）；第二次不再说（%s）' % (t0, (t1 or '')[:40], (t2 or '')[:30]), not t0 and t1 and '右上角' in t1 and t2 and '右上角' not in t2, (t0, t1, t2))
        cw.close()
    with guard('A7h'):   # 存不下时只说一次
        cn = new_ctx(br, p); cn.add_init_script("Storage.prototype.setItem=function(){throw new DOMException('q','QuotaExceededError')}"); pn_ = new_page(env, cn)
        goto(env, pn_, '/trip/xa3/', 900); pn_.click('.fav'); pn_.wait_for_timeout(600)
        t = pn_.evaluate("document.querySelector('.toast')&&document.querySelector('.toast').textContent")
        check('A7h 浏览器存不下（setItem 抛错）时：点“收进行程”说一次“存不下”，不说“已收进”（%s）' % t, bool(t) and '存不下' in t and '已收进' not in t, t)
        cn.close()

    # ═══════════════ B · 行程页样板行
    with guard('B'):
        hm = count_trips(r'<p class="m">出发 → 住处</p><p class=s>打车或步行</p>')
        check('B1 “出发 → 住处 / 打车或步行”样板行不再出现在行程页（旧 3737 行）：%d' % hm, hm == 0, hm)
        rest = count_trips(r'<li class="r dep" data-x="rest"'); rest_old = count_trips(r'<li class="r dep"(?! data-x="rest")[^>]*><time>[^<]*</time><span class="dot"></span><div class="rb"><p class="m">出发 → 住处</p><p class=s>回去歇一下')
        check('B2 “回去歇一下”行都带 rest 类（折成一行小灰字）：%d 行，没带类的 %d' % (rest, rest_old), rest > 2500 and rest_old == 0, (rest, rest_old))
        gap = count_trips(r'<li class="r see"[^>]*data-x="gap"')
        check('B3 “沿途慢慢走”行带 gap 类：%d 行' % gap, gap >= 80, gap)
        gen = count_trips(r'<div class="stays gen"'); named = count_trips(r'<div class="stays"')
        check('B4 没有酒店名的住宿卡带 gen 类（旧 2087 张）：%d；有酒店名的卡不带：%d' % (gen, named), gen > 1500 and named > 1000, (gen, named))
        hid = count_trips(r'<p class="lead" hidden>'); allld = count_trips(r'<p class="lead"')
        check('B5b g318 页有复述标题的导语被隐藏（%d 处）' % GET('/trip/g318/').count('<p class="lead" hidden>'), GET('/trip/g318/').count('<p class="lead" hidden>') >= 1)
        check('B5 复述标题的导语不显示：隐藏 %d / %d 天 = %.0f%%（约 29%%）' % (hid, allld, 100.0 * hid / max(allld, 1)), 0.2 < hid / max(allld, 1) < 0.4, (hid, allld))
    with guard('B6'):   # 浏览器里量高度
        goto(env, pg, '/trip/ae4/', 900)
        o = pg.evaluate("""()=>{const q=(s)=>[...document.querySelectorAll(s)].map(e=>Math.round(e.getBoundingClientRect().height));return {rest:q('.r[data-x=rest]'),stay:q('.stays.gen')}}""")
        check('B6 “回去歇一下”折成一行：每行 ≤ 36px（%s）' % o['rest'][:6], o['rest'] and max(o['rest']) <= 36, o)
        goto(env, pg, '/trip/xa3/', 900)
        o2 = pg.evaluate("""()=>{const q=(s)=>[...document.querySelectorAll(s)].map(e=>Math.round(e.getBoundingClientRect().height));return {gen:q('.stays.gen'),named:q('.stays:not(.gen)')}}""")
        goto(env, pg, '/trip/' + [t for t in ALLTRIPS if '<div class="stays gen"' in GET('/trip/%s/' % t) and 'data-x="gap"' in GET('/trip/%s/' % t)][0] + '/', 900)
        o3 = pg.evaluate("""()=>{const q=(s)=>[...document.querySelectorAll(s)].map(e=>Math.round(e.getBoundingClientRect().height));return {gen:q('.stays.gen:not(.open)'),gap:q('.r[data-x=gap]')}}""")
        check('B6b 无酒店名的住宿卡一行灰字（≤ 64px：%s）；“沿途慢慢走”≤ 36px（%s）' % (o3['gen'][:4], o3['gap'][:4]), o3['gen'] and max(o3['gen']) <= 64 and (not o3['gap'] or max(o3['gap']) <= 36), o3)
    with guard('B7'):   # 高反：第一晚完整，之后一行；≥3500 醒目
        h = GET('/trip/xl9a/'); alts = re.findall(r'<p class="alt( hi)?"><b>海拔 ([\d,]+) 米</b>(.*?)</p>', h)
        first_full = [a for a in alts if len(a[2]) > 60]; short = [a for a in alts if len(a[2]) <= 60]
        hi_ok = all(a[0] or int(a[1].replace(',', '')) < 3500 for a in alts)
        check('B7 高反提醒：整页有 %d 条，完整版 %d 条（含氧气瓶 %s），其余 %d 条都 ≤ 60 字；≥3500 米的都带醒目样式 hi（%s）' % (len(alts), len(first_full), any('氧气' in a[2] for a in first_full), len(short), hi_ok), len(alts) >= 3 and 1 <= len(first_full) <= 2 and any('氧气' in a[2] for a in first_full) and len(short) >= 2 and hi_ok and any(a[0] for a in short), alts[:3])
    with guard('B8'):   # “人物：”前缀只在第一条写
        bad = []
        for rid in ('hss1a', 'hzh1', 'hdu1'):
            h = GET('/trip/%s/' % rid); fn = re.findall(r'<p class="fnote">(.*?)</p>', h, re.S)
            m = re.search(r'<a class="fbn"[^>]*><span>这条行程跟着 <b>(.*?)</b>', h)
            nm = m.group(1) if m else ''
            pf = [x for x in fn if nm and x.startswith(nm + '：')]
            if not (len(fn) >= 3 and len(pf) <= 1): bad.append((rid, len(fn), len(pf)))
        check('B8 站点注释的“人物：”前缀整页只在第一条写（异常：%s）' % bad, not bad, bad)

    # ═══════════════ C · 新用户术语
    with guard('C1'):
        h = GET('/'); ft = ' '.join(GET(x) for x in ('/where/', '/pian/', '/long/', '/trip/xa3/'))
        check('C1 “本期”→“首页”：首页顶部 / 页脚 / 各频道页没有“本期”链接', '>本期</a>' not in h + ft and re.search(r'class="home" href="/">首页</a>', GET('/where/')) is not None)
        check('C2 入口副标：走哪儿“按月份挑国内外”、跟片走“舌尖、国宝、航拍”、跟谁走“苏轼、玄奘、郑和”、长线自驾“15 天以上的自驾路”', all(x in h for x in ('按月份挑国内外', '舌尖、国宝、航拍', '苏轼、玄奘、郑和', '15 天以上的自驾路')) and h.count('<nav class="chan2"') == 1 and len(re.findall(r'<nav class="chan2".*?</nav>', h, re.S)[0].split('<a ')) - 1 == 4)
        check('C3 “替我挑三条”改叫“替我挑三条行程”，副标“选出发地、天数、和谁去”', '替我挑三条行程' in GET('/assets/site.js') and '选出发地、天数、和谁去' in GET('/assets/site.js'))
        tx = GET('/trip/xa3/')
        check('C4 行程页：“看路线图”→“看地图”；“调整”→“改这站 / 改这一天”；日期“改日期”、时间“改时间”', '看路线图' not in GET('/assets/site.js') and '看路线图' not in tx and '<i>改日期</i>' in tx and '<i>改时间</i>' in tx and '改这站</button>' in GET('/assets/site.js') and '改这一天 ›' in GET('/assets/site.js') and '>调整</button>' not in GET('/assets/site.js'))
        prices = [m_ for pth in ('/', '/where/', '/trip/xa3/', '/long/', '/d/shaanxi/', '/trip/xl9a/') for m_ in re.findall(r'¥[\d.]+K', GET(pth))]
        check('C5 价格不写“K”：¥2.6K → ¥2600–3600/人（页面里剩 %d 处 K 写法）' % len(prices), not prices and re.search(r'¥\d{3,5}–\d{3,5}/人', h) is not None, prices[:3])
        check('C6 同一概念叫法：“最佳”→“最好”（/long/ 没有“最佳”）；片子动词“去过/讲过”→“拍过”', '最佳' not in GET('/long/') and '去过 ' not in GET('/pian/') and '讲过 ' not in GET('/pian/'))
        check('C7 “直线约 N 公里”→“离X约 N 公里”', '过去直线约' not in GET('/assets/site.js'))
        cv = re.search(r'<span class="kick">封面故事[^<]*</span>', h).group(0)
        check('C8 封面不写“还剩 N 天”，用日期说“最好到 M/D”：%s' % cv, '还剩' not in cv and '最好到' in cv)
    with guard('C9'):
        goto(env, pg, '/where/', 600); open_filter(pg); pg.fill('.flt input', '国外'); pg.wait_for_timeout(1200)
        tabn = pg.evaluate("document.querySelector('.tabs .on').dataset.t"); nn = pg.evaluate("document.querySelectorAll('.scope:not([hidden]) .card:not([hidden])').length")
        check('C9 搜“国外”进入亚洲 / 欧美及其他（当前页签 %s，%d 张卡）' % (tabn, nn), tabn in ('asia', 'world') and nn >= 3, (tabn, nn))
    # input.md 的高 / 中项
    with guard('I1'):
        h = GET('/where/')
        check('I1 /where/ 搜索框 autocomplete=off、enterkeyhint=search（回车收起键盘；pageshow 同步）；首页、/long/ 的搜索框也有 enterkeyhint', re.search(r'<input type="search" enterkeyhint="search"[^>]*>', h) is not None and 'enterkeyhint="search"' in GET('/long/') and 'enterkeyhint="search"' in GET('/'))
        goto(env, pg, '/where/', 500); open_filter(pg); pg.fill('.flt input', '成都'); pg.press('.flt input', 'Enter'); pg.wait_for_timeout(300)
        check('I1b 在 /where/ 搜索框回车后输入框失焦（键盘收起）', pg.evaluate("document.activeElement.tagName")!='INPUT')
        # 浏览器返回后输入框和列表一致
        pg.fill('.flt input', '西藏'); pg.wait_for_timeout(800); pg.goto(env.B + '/trip/xa3/', wait_until='networkidle'); pg.go_back(); pg.wait_for_timeout(1200)
        a = pg.evaluate("[document.querySelector('.flt input').value,document.querySelector('.cnt').textContent]")
        check('I1c 搜“西藏”→点进去→返回：输入框（%s）和列表一致（%s）' % tuple(a), (a[0] == '') == ('符合的' in a[1] and '2 个' not in a[1]) or (a[0] == '西藏' and re.search(r'符合的 [1-9]\d? 个', a[1]) and '33' not in a[1]), a)
    with guard('I2'):   # 选了能取消
        goto(env, pg, '/', 1200); pg.click('.pkh'); pg.wait_for_timeout(200)
        pg.click('.pkr[data-k="v"] button[data-v="n"]'); pg.wait_for_timeout(100); pg.click('.pkr[data-k="v"] button[data-v="n"]'); pg.wait_for_timeout(200)
        on = pg.evaluate("!!document.querySelector('.pkr[data-k=\"v\"] .on')")
        check('I2 “替我挑三条”里点已选项取消（“出行（可不选）”能回到不选）', not on, on)
    with guard('I3'):   # 首页建议：精确匹配排前面、末尾“搜全部”
        goto(env, pg, '/', 1200); pg.fill('form.hsearch input', '敦煌'); pg.wait_for_function("document.querySelectorAll('.hsug li').length>0", timeout=8000); pg.wait_for_timeout(300)
        rows = pg.evaluate("[...document.querySelectorAll('.hsug li')].map(l=>[l.className,l.textContent.trim().slice(0,16)])")
        check('I3 首页搜“敦煌”：建议里名字贴得最近的排前面、末尾固定一行“搜全部「敦煌」›”（%s）' % rows, rows and rows[-1][0] == 'hall' and '敦煌' in rows[-1][1] and len(rows) <= 6, rows)
        pg.fill('form.hsearch input', 'xyz不存在'); pg.wait_for_timeout(800)
        r2 = pg.evaluate("[...document.querySelectorAll('.hsug li')].map(l=>l.className)")
        check('I3b 没有命中时不再是一片空白：只剩“搜全部”这一行（%s）' % r2, r2 == ['hall'], r2)
    with guard('I4'):   # IME 组合中不过滤
        goto(env, pg, '/where/', 500); open_filter(pg)
        cdp = c.new_cdp_session(pg); pg.focus('.flt input')
        cdp.send('Input.imeSetComposition', {'text': 'chuan', 'selectionStart': 5, 'selectionEnd': 5}); pg.wait_for_timeout(500)
        t = pg.evaluate("document.querySelector('.cnt').textContent")
        check('I4 拼音输入法组合中（chuan 还没上屏）不过滤、不提示“没找到”（%s）' % t, '没找到' not in t, t)
    # a11y / devices
    with guard('V1'):
        goto(env, pg, '/trip/xa3/', 700)
        r = pg.evaluate("(function(){var els=[].slice.call(document.querySelectorAll('.glance, .glance *')),fs=els.map(function(e){return parseFloat(getComputedStyle(e).fontSize)});els.forEach(function(e,i){e.style.setProperty('font-size',fs[i]*2+'px','important')});var out={};['.glance b.big','.glance b.price','.glance [data-gd] b'].forEach(function(q){var e=document.querySelector(q);if(!e)return;var c=getComputedStyle(e);out[q]=[c.height,c.overflow,e.scrollHeight<=e.clientHeight*1.2+1]});return out})()")
        check('V1 大字号下页头“3 天 / 不开车 / ¥价格”不被固定高度裁掉（scrollHeight ≤ clientHeight）：%s' % r, r and all(v[2] for v in r.values()), r)
        pg.goto(env.B + '/where/', wait_until='networkidle'); pg.wait_for_timeout(500)
        gl = pg.evaluate("(function(){var g=document.querySelector('.goodline');return getComputedStyle(g).webkitLineClamp||getComputedStyle(g).getPropertyValue('-webkit-line-clamp')})()")
        check('V2 /where/ 的“N 月正好去…”不再 2 行截断（line-clamp=%s）' % gl, gl in ('none', 'unset', ''), gl)
        hs = pg.evaluate("[...document.querySelectorAll('main h1,main h2,main h3')].slice(0,3).map(h=>h.tagName)")
        pg.goto(env.B + '/long/', wait_until='networkidle'); pg.wait_for_timeout(400)
        hs2 = pg.evaluate("[...document.querySelectorAll('main h1,main h2,main h3')].slice(0,3).map(h=>h.tagName)")
        check('V3 标题层级不跳级：/where/ 前三个标题 %s、/long/ %s（没有 H1 后直接 H3）' % (hs, hs2), 'H3' not in hs[:2] and 'H3' not in hs2[:2], (hs, hs2))
    with guard('V4'):
        goto(env, pg, '/d/shaanxi/', 600)
        hm = pg.evaluate("(function(){var f=document.querySelector('figure.hmap');return f?[f.getAttribute('role'),f.getAttribute('tabindex'),!!f.querySelector('a')]:null})()")
        check('V4 分布图里有站名链接时不当按钮（没有 role=button / tabindex）：%s' % hm, hm and hm[2] and hm[0] is None and hm[1] is None, hm)
        goto(env, pg, '/trip/xa3/', 600)
        hm2 = pg.evaluate("(function(){var f=document.querySelector('figure.hmap');return f?[f.getAttribute('role'),!!f.querySelector('a')]:null})()")
        check('V4b 行程页的路线示意图（里面没有链接）仍是按钮：%s' % hm2, hm2 is None or hm2[0] == 'button' or hm2[1], hm2)
    with guard('V5'):
        c6 = new_ctx(br, p, w=844, h=390); p6 = new_page(env, c6); goto(env, p6, '/trip/xa3/', 700)
        pos = p6.evaluate("getComputedStyle(document.querySelector('.dock')).position")
        p6.focus('.dtw'); p6.keyboard.press('Enter'); p6.wait_for_timeout(500)
        top = p6.evaluate("(function(){var s=document.querySelector('.pk');if(!s)return null;var r=s.getBoundingClientRect();return [Math.round(r.top),Math.round(r.height),getComputedStyle(s).overflowY]})()")
        check('V5 横屏 844×390：底栏不吸底（%s）；日期层不超出视口（top=%s，高 %s，可滚 %s）' % (pos, top and top[0], top and top[1], top and top[2]), pos == 'static' and top and top[0] >= 0 and top[1] <= 390 and top[2] in ('auto', 'scroll'), (pos, top))
        p6.keyboard.press('Escape'); p6.wait_for_timeout(300)
        fo = p6.evaluate("document.activeElement.className||document.activeElement.tagName")
        check('V6 日期层用 Esc 关掉后焦点回到打开它的元素（%s），不掉到 body' % fo, fo != 'BODY' and fo != 'HTML', fo)
        c6.close()
        c7 = new_ctx(br, p, w=320, h=568); p7 = new_page(env, c7); goto(env, p7, '/trip/xa3/', 600)
        sp = p7.evaluate("(function(){var s=document.querySelector('.dock .fav span');return s?getComputedStyle(s).display:null})()")
        check('V7 320 宽：底栏“收进行程”四个字还在（span display=%s）' % sp, sp and sp != 'none', sp)
        c7.close()
    with guard('V8'):
        css = GET('/assets/site.css')
        check('V8 inset 的老内核兜底：遮罩、按天看层、放大层都补了 top/right/bottom/left', all(x in css for x in ('.pk-mask{top:0;right:0;bottom:0;left:0}', '.tv{top:0;right:0;bottom:0;left:0}', '.hmap-zoom{top:0;right:0;bottom:0;left:0}')))

    # ═══════════════ D · 重复线路
    with guard('D'):
        bad = []
        prefetch(['/trip/%s/' % t for t in ALLTRIPS])
        for t in ALLTRIPS:
            m = re.search(r'<h1>(.*?)</h1>', GET('/trip/%s/' % t), re.S)
            if m and re.match(r'^\d+\s*天\s*[(（]', re.sub(r'<[^>]+>', '', m.group(1)).strip()): bad.append(t)
        check('D2 行程页标题不以“N天(…)”开头（旧 52 条）：%d 条 %s' % (len(bad), bad[:4]), not bad, bad)
        x = GET('/trip/xv02a/')
        check('D2b xv02a 的 <h1> 是“五天，从西安到太白山…”', re.sub(r'<[^>]+>', '', re.search(r'<h1>(.*?)</h1>', x, re.S).group(1)).startswith('五天，从西安到太白山'))
        tj = json.load(open(os.path.join(ROOT, 'data', 'catalog', 'trips.json'), encoding='utf-8'))['trips']
        dupl = {}
        for t in tj:
            if re.match(r'Route\.dc\.html#', t.get('page') or ''): dupl.setdefault((t['dest'], re.sub(r'\s+', '', t.get('label') or t.get('title') or '')), []).append(t['id'])
        # 同一目的地下标签相同的行程组（旧 18 组 37 条）：用页面上的 label 查
        lab = {}
        for t in ALLTRIPS:
            m = re.search(r'data-id="%s"[^>]*data-dest="([^"]*)"[^>]*data-label="([^"]*)"' % re.escape(t), GET('/trip/%s/' % t))
            if m: lab.setdefault((m.group(1), m.group(2)), []).append(t)
        same = {k: v for k, v in lab.items() if len(v) > 1}
        check('D3 同一目的地下标签不重名（旧 18 组 37 条）：%d 组 %s' % (len(same), list(same.items())[:2]), len(same) == 0, list(same.items())[:3])
        xa = GET('/trip/xa3/'); sis = re.search(r'<p class="sis">(.*?)</p>', xa, re.S)
        check('D4 姐妹线互链：西安 3 天页有“同一个地方还有…”并链到 xa5d、kbxa3（%s）' % (re.findall(r'href="(/trip/\w+/)"', sis.group(1)) if sis else None), sis is not None and '/trip/xa5d/' in sis.group(1) and '/trip/xa3/' not in sis.group(1), None)
        cq = GET('/trip/cq3/'); co = re.search(r'<link rel="canonical" href="([^"]+)"', cq)
        check('D5 被完整覆盖的行程（cq3 ⊂ cq4d）页面保留，canonical 指向覆盖它的那条（%s）；页面仍有 %d 个天 section' % (co and co.group(1), cq.count('<section class="day"')), co and co.group(1).endswith('/trip/cq4d/') and cq.count('<section class="day"') >= 3, co and co.group(1))
        nc = sum(1 for t in tj if t.get('covered_by') and t['covered_by'] != t['id'])
        pages_canon = sum(1 for t in ALLTRIPS if re.search(r'<link rel="canonical" href="https://zouni.app/trip/(\w+)/"', GET('/trip/%s/' % t)) and re.search(r'<link rel="canonical" href="https://zouni.app/trip/(\w+)/"', GET('/trip/%s/' % t)).group(1) != t)
        check('D5b canonical 指向别的行程的页面数（%d）等于 trips.json 里 covered_by 的条数（%d）；页面一页不少（%d）' % (pages_canon, nc, len(ALLTRIPS)), pages_canon == nc and len(ALLTRIPS) >= 1600, (pages_canon, nc))

    br.close()
env.finish('去冗余波（wave2）')
