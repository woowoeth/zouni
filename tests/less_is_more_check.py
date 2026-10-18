#!/usr/bin/env python3
"""“少就是多”减法审计的断言（2026-10-18）。只数“信息和操作的数量”，不砍功能；每一项减法都有上限，故意把重复元素加回去会红。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/less_is_more_check.py build/site [--shots DIR]
    python3 tests/less_is_more_check.py build/site --inject 名字       # 反向自检：只改送到浏览器的 site.js / site.css / routemap.js，对应判据必须变红
    python3 tests/less_is_more_check.py build/site --table 改动前的站目录   # 只打印“前后数字”表（不判定），写报告用

怎么数（390×844，亮色）：
  “页头区”= 页面顶端到第 1 天标题之间所有看得见的东西（折叠起来的不算）：可点元素个数 + 文字块个数 + 文字字数 + 高度。
  “第一屏”= 不滚动时视口里的同样三个数。滚屏数 = 某个位置的页面纵坐标 ÷ 844。

L1  线路页页头区（郑和 hzh1 / 红色 hcz4 / 长线 xl9a / 普通 sh5d）：元素、字数、高度都有上限（旧：hzh1 52 个 / 544 字 / 1405px …）
L2  线路页第一屏：底栏不再把页头里的日期价格再写一遍；“这条线路跟着…”横幅不在第一屏；建议出发一行只有一句且带最佳季节；
    “出发前”页内只露 ≤2 条纯文字提示（2026-10-18 起没有“更多 N 条”，待办在弹层里）；礼仪 / 预约 / 闭馆合成一条；“看路线图”只有一个入口（折叠的那个收起来）
L3  站点行：一行下面最多一条注释（主题注释和镇馆之宝不同时出现）
L4  地图：每天小图的图例不再写“第 N 天”；总览不写“每天一种颜色”
L5  导航分段层：只有一个关闭键（头部 ×，2026-10-18 起没有底部“关上”）可见、只有一个主操作（第 1 段实心）、说明一行
L6  /follow/：数量行搜索前不显示；一句话不重复标题；主题页第一屏就有线路入口（不用滚过年表）；“只写有记载的事…”整站只在主题页写一次
L7  /long/：每个控件都是筛选（不能删），只删了一句没信息的数字
L8  文案：新增文案里的套话（“点日期可改”“按最佳季节”“每天一种颜色”“这一屏…”）一条都不能回来
L9  步数：礼仪 / 预约 / 闭馆的提醒第一屏就看得到（0 次滚动）；第 1 天第一站离页顶至少近了 150px
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'dock_text': ('assets/site.css', ".dock.dmin>div:first-child{flex:0 0 0;width:0;min-width:0;overflow:hidden}", ".dock.dmin>div:first-child{flex:1}"),
    'fbn_top': ('assets/site.js', "// ——— 底部固定栏：页头", "(function(){var f=document.querySelector('.fbn'),g=document.querySelector('.glance');if(f&&g)g.parentNode.insertBefore(f,g)})();\n// ——— 底部固定栏：页头"),
    'dnote_long': ('assets/site.js', "return(isSugg?[y_,wn,c0]:['按你'+srcTxt", "return(isSugg?[y_,wn,'按最佳季节，点日期可改',c0]:['按你'+srcTxt"),
    'pre_open': ('assets/site.js', "// ——— 底部固定栏：页头", "[].forEach.call(document.querySelectorAll('.prehid'),function(u){u.hidden=false});\n// ——— 底部固定栏：页头"),
    'pre_dup': ('assets/site.js', "// ——— 底部固定栏：页头", "(function(){var u=document.querySelector('.pre:not(.go) ul');if(u)u.insertAdjacentHTML('beforeend','<li class=\"tip\"><span>多数博物馆、纪念馆周一休馆，热门馆要提前订票，以各馆官网为准。</span></li>')})();\n// ——— 底部固定栏：页头"),
    'mapfold_back': ('assets/site.js', "go.addEventListener('click',function(){start(null)});", "go.addEventListener('click',function(){start(null)});var mf=document.createElement('button');mf.type='button';mf.className='mapfold';mf.textContent='看路线图';mf.addEventListener('click',function(){start(null)});ov.insertBefore(mf,ov.firstChild.nextSibling);"),
    'row_two_notes': ('assets/site.js', "// ——— 底部固定栏：页头", "[].forEach.call(document.querySelectorAll('li.r .fnote'),function(f){var p=document.createElement('p');p.className='s tre';p.textContent='镇馆之宝';f.parentNode.insertBefore(p,f)});\n// ——— 底部固定栏：页头"),
    'leg_color': ('assets/routemap.js', "<span class=\"rm-hdt\"><small>全程</small>", "<span class=\"rm-hdt\"><small>全程 · 每天一种颜色</small>"),
    'leg_day': ('assets/routemap.js', "<small>第 ' + (d.i + 1) + ' 天</small><b>' + esc(d.title)", "<small>第 ' + (d.i + 1) + ' 天</small><b class=\"rm-lgx\">每天一种颜色 · ' + esc(d.title)"),
    'nav_two_close': ('assets/routemap.js', "ZL.open([mask, sh], { sheet: sh, mask: mask, kind: 'nav' });", "var xb2 = el('button', 'pk-x'); xb2.textContent = '关上'; sh.appendChild(xb2); ZL.open([mask, sh], { sheet: sh, mask: mask, kind: 'nav' });"),
    'nav_no_primary': ('assets/site.css', ".rm-sheet .xd .rm-seg:first-child{background:var(--ink);color:var(--bg)}", ".rm-sheet .xd .rm-seg:first-child{background:var(--bg)}"),
    'nav_note_long': ('assets/routemap.js', "<p class=\"xnote\">' + esc(navHint(d)) + '</p>", "<p class=\"xnote\">' + esc(navHint(d)) + '路线按驾车排好，到了地图里可以改成步行或公交。</p>"),
    'fcnt_show': ('assets/site.js', "cnt.hidden=!q.length;", "cnt.hidden=false;"),
    'fl_after': ('assets/site.js', "// ——— 跟谁走 主题页：年表", "(function(){var a=document.querySelector('article.ftp'),u=a&&a.querySelector('ul.fl'),h=u&&u.previousElementSibling;if(u&&h){a.appendChild(h);a.appendChild(u)}})();\n// ——— 跟谁走 主题页：年表"),
}
env = Env(INJ)
check, guard = env.check, env.guard
TABLE = sys.argv[sys.argv.index('--table') + 1] if '--table' in sys.argv else None
BEFORE = {   # 旧站（2026-10-18 本轮开工前的 build/site）实测：页头区 [可点, 文字块, 字数, 元素合计, 高度px]
    'hzh1': [15, 37, 544, 52, 1405], 'hcz4': [22, 47, 728, 69, 1711], 'xl9a': [37, 59, 1151, 96, 2210], 'sh5d': [18, 34, 225, 52, 1024]}
CEIL = {     # 上限 = 本轮实测 + 一点余量（日期、数据微调不至于误红；故意加回一个重复元素会超）。折叠在 details 里的不算（看不见）
    'hzh1': [14, 34, 420, 48, 1010], 'hcz4': [28, 47, 540, 75, 1190], 'xl9a': [40, 58, 500, 98, 1050], 'sh5d': [16, 33, 260, 50, 880]}
# 2026-10-18 第四轮（详情页少就是多）后重设：高度比上一轮上限更低或持平，但字数多了 40–60 字（“怎么去、怎么回”多了回程一句、页头说明行多了往年气温）、可点多了几个（长线概览“住：…”每段做成链接：xl9a / hcz4）——都是把原来藏在深处的功能挪到页头，不是回到重复；
# 旧判据里“高度、元素合计、字数都比 BEFORE 少”仍然成立（z[3] < b[3] and z[2] < b[2]）
BEFORE_Z = {'follow': [14, 18, 109, 32, 426], 'long': [21, 26, 99, 47, 377]}      # 页顶到第一组卡片：旧站实测（--table）
CEIL_Z = {'follow': [14, 17, 95, 31, 400], 'long': [21, 26, 95, 47, 380]}
ZONE = """(sel)=>{const d1=document.querySelector(sel||'#d1');const L=d1?d1.getBoundingClientRect().top+scrollY:1e9;
 const inC=(el)=>{const d=el.closest('details:not([open])');if(!d)return false;const s=d.querySelector(':scope>summary');return !(s&&s.contains(el))};
 const vis=(el)=>{if(inC(el))return false;const r=el.getBoundingClientRect();if(r.width<1||r.height<1)return false;if(r.top+scrollY>=L)return false;const s=getComputedStyle(el);if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0)return false;return true};
 let n=0;document.querySelectorAll('a[href],button,input:not([type=hidden]),select,summary,[role=button]').forEach(e=>{if(vis(e)&&!e.closest('[hidden]'))n++});
 const seen=new Set();let chars=0;const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let t;while(t=w.nextNode()){const s=t.nodeValue.replace(/\\s+/g,'');if(!s)continue;const p=t.parentElement;if(!p||p.closest('script,style,svg,noscript,[hidden]')||inC(p))continue;const rg=document.createRange();rg.selectNodeContents(t);const rs=[...rg.getClientRects()].filter(r=>r.width>0&&r.height>0&&r.top+scrollY<L);if(!rs.length)continue;const cs=getComputedStyle(p);if(cs.visibility==='hidden'||+cs.opacity===0)continue;seen.add(p);chars+=s.length}
 return [n,seen.size,chars,n+seen.size,Math.round(L)]}"""
VIEW = """()=>{const H=innerHeight,W=innerWidth;const inC=(el)=>{const d=el.closest('details:not([open])');if(!d)return false;const s=d.querySelector(':scope>summary');return !(s&&s.contains(el))};
 const vis=(el)=>{if(inC(el))return false;const r=el.getBoundingClientRect();if(r.width<1||r.height<1)return false;if(r.bottom<=0||r.top>=H||r.right<=0||r.left>=W)return false;const s=getComputedStyle(el);if(s.visibility==='hidden'||s.display==='none'||+s.opacity===0)return false;return true};
 let n=0;document.querySelectorAll('a[href],button,input:not([type=hidden]),select,summary,[role=button]').forEach(e=>{if(vis(e)&&!e.closest('[hidden]'))n++});
 const seen=new Set();let chars=0;const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let t;while(t=w.nextNode()){const s=t.nodeValue.replace(/\\s+/g,'');if(!s)continue;const p=t.parentElement;if(!p||p.closest('script,style,svg,noscript,[hidden]')||inC(p))continue;const rg=document.createRange();rg.selectNodeContents(t);const rs=[...rg.getClientRects()].filter(r=>r.width>0&&r.height>0&&r.bottom>0&&r.top<H&&r.right>0&&r.left<W);if(!rs.length)continue;const cs=getComputedStyle(p);if(cs.visibility==='hidden'||+cs.opacity===0)continue;seen.add(p);chars+=s.length}
 return [n,seen.size,chars,n+seen.size]}"""
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tests', 'fixtures')
STYLE = open(os.path.join(FX, 'ofm_liberty_style.json'), 'rb').read(); PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read(); CORS = {'access-control-allow-origin': '*'}


def stub(c):
    c.route('https://tiles.openfreemap.org/styles/liberty', lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=STYLE))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), lambda r: r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14})))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), lambda r: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b''))
    c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites)/.+'), lambda r: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG) if not r.request.url.split('?')[0].endswith('.json') else r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}'))


TRIPS = ['hzh1', 'hcz4', 'xl9a', 'sh5d']

with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    c = new_ctx(br, None); stub(c); pg = new_page(env, c)

    def shot(name):
        if env.shots: pg.screenshot(path=os.path.join(env.shots, name))

    # ─────────── --table：前后数字（不判定）
    if TABLE:
        import http.server, socketserver, threading, functools
        srv0 = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(type('H', (http.server.SimpleHTTPRequestHandler,), {'log_message': lambda *a: None}), directory=os.path.abspath(TABLE)))
        threading.Thread(target=srv0.serve_forever, daemon=True).start(); B0 = 'http://127.0.0.1:%d' % srv0.server_address[1]
        rows = []
        for label, base in (('旧', B0), ('新', env.B)):
            for rid in TRIPS:
                pg.goto(base + '/trip/%s/' % rid, wait_until='networkidle'); pg.wait_for_timeout(600)
                z = pg.evaluate(ZONE); pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); v = pg.evaluate(VIEW)
                y = pg.evaluate("(function(){var e=document.querySelector('#d1 .tl .r');return e?Math.round(e.getBoundingClientRect().top+scrollY):-1})()")
                e_ = pg.evaluate("(function(){var e=document.querySelector('.pre li.etq,.pre li.mus');return e?Math.round(e.getBoundingClientRect().top+scrollY):-1})()")
                rows.append((label, rid, z, v, y, e_)); print(label, rid, '页头区[可点,文字块,字数,合计,px]', z, '第一屏[可点,文字块,字数,合计]', v, '第1天第1站 y=%d (%.2f 屏)' % (y, y / 844), '礼仪/预约行 y=%d' % e_)
        for label, base in (('旧', B0), ('新', env.B)):
            for key, path, sel in (('follow', '/follow/', '.fgrp'), ('long', '/long/', '.lcards')):
                pg.goto(base + path, wait_until='networkidle'); pg.wait_for_timeout(500)
                print(label, key, '页顶到第一组卡片[可点,文字块,字数,合计,px]', pg.evaluate(ZONE, sel))
        sys.exit(0)

    # ─────────── L1 页头区上限
    for rid in TRIPS:
        with guard('L1 ' + rid):
            goto(env, pg, '/trip/%s/' % rid, 700)
            z = pg.evaluate(ZONE); b = BEFORE[rid]; ce = CEIL[rid]
            check('L1 %s 页头区：可点 %d / 文字块 %d / 字数 %d / 合计 %d / 高 %dpx（旧 %s；上限 %s）' % (rid, *z, b, ce),
                  z[0] <= ce[0] and z[1] <= ce[1] and z[2] <= ce[2] and z[3] <= ce[3] and z[4] <= ce[4] and z[4] < b[4] and z[3] <= b[3] + 2, z)      # 2026-10-18：不再要求“字数、元素合计都比旧的少”——页头多了“回程”一句和长线“住：…”链接（+16 字 / +1 个元素），高度仍比旧的低；上限 CEIL 管着不许再长

    # ─────────── L2 线路页第一屏
    for rid in TRIPS:
        with guard('L2 ' + rid):
            goto(env, pg, '/trip/%s/' % rid, 700); pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); pg.wait_for_timeout(250)
            o = pg.evaluate("""()=>{var H=innerHeight,vh=function(e){if(!e)return false;var r=e.getBoundingClientRect();return r.width>0&&r.height>0&&r.top<H&&r.bottom>0},dk=document.querySelector('.dock b'),
              fb=document.querySelector('.fbn'),dn=document.querySelector('.dnote'),pre=document.querySelector('section.pre:not(.go)'),ms=document.querySelector('.premore'),
              lis=pre?[].slice.call(pre.querySelectorAll(':scope > ul > li')):[],all=pre?[].slice.call(pre.querySelectorAll('li')):[],
              mf=document.querySelectorAll('.mapfold').length,gos=document.querySelectorAll('.mapgo').length;
              var rp=all.filter(function(l){var t=l.textContent;return /预约/.test(t)&&/官方|官网/.test(t)&&!l.querySelector('input')});
              return {dockVis:vh(dk)&&dk.getBoundingClientRect().width>0,fbnTop:fb?Math.round(fb.getBoundingClientRect().top+scrollY):-1,dn:dn?dn.textContent.trim():'',visLi:lis.filter(vh).length,ms:ms?{open:ms.open,sum:ms.querySelector('summary').textContent.trim(),hid:ms.querySelectorAll('li').length}:null,
                nli:all.length,rp:rp.length,mfVis:mf,gos:gos,follow:(document.body.innerText.match(/这条线路跟着/g)||[]).length,hasFbn:!!fb}}""")
            check('L2a %s 底栏在页头日期价格还看得见时不重复写（底栏文字不可见）' % rid, not o['dockVis'], o['dockVis'])
            check('L2b %s “这条线路跟着…”横幅不在第一屏（离页顶 %s px，视口 844；没有横幅=-1）、整页只写一遍（%d）' % (rid, o['fbnTop'], o['follow']), (o['fbnTop'] == -1 or o['fbnTop'] >= 844) and o['follow'] <= 1, o)
            check('L2c %s 页头说明一句（%s）：≤60 字（只写最好 X–Y / 往年气温 / 跨年的年份，日期不再重复）、没有“按最佳季节”“点日期可改”“一年四季都能去”“建议”' % (rid, o['dn']), len(o['dn']) <= 60 and '点日期可改' not in o['dn'] and '按最佳季节' not in o['dn'] and '一年四季' not in o['dn'] and '建议' not in o['dn'], o['dn'])
            check('L2d %s “出发前”页内露 ≤2 条纯文字提示（露 %d），没有“更多 N 条”折叠（%s）；待办和其余提示在“出发前要办的事”弹层里' % (rid, o['visLi'], o['ms']), o['visLi'] <= 2 and o['ms'] is None, o)
            check('L2e %s 礼仪 / 预约 / 闭馆的总提醒整页只有一条（说“预约”又说“官方/官网”的非待办行 %d）' % (rid, o['rp']), o['rp'] <= 1, o['rp'])
            check('L2f %s “看路线图”只有一个入口（.mapgo %d 个）：没有第二个“折叠里的看路线图”（.mapfold %d 个）；点它一步直达整屏地图，页面里没有内嵌地图' % (rid, o['gos'], o['mfVis']), o['gos'] == 1 and o['mfVis'] == 0, o)
            if rid == 'hzh1': shot('l2_trip_hzh1.png')

    # ─────────── L3 站点行注释
    for rid in ('hzh1', 'hcz4'):
        with guard('L3 ' + rid):
            goto(env, pg, '/trip/%s/' % rid, 500)
            n = pg.evaluate("(function(){var m=0,t=0;[].forEach.call(document.querySelectorAll('.tl > li.r'),function(r){var f=r.querySelectorAll('p.fnote').length,g=r.querySelectorAll('p.s.tre').length;t++;if(f+g>1)m++});return [m,t,document.querySelectorAll('.tl p.fnote').length]})()")
            check('L3 %s 一行下面最多一条注释（%d 行里 %d 行有两条以上；有注释的 %d 行）' % (rid, n[1], n[0], n[2]), n[0] == 0, n)

    # ─────────── L4 地图图例（2026-10-18 地图 App 化：整屏里不写图例 / 颜色说明；只留一句“线是直线示意”，和导航按钮放一起）
    with guard('L4'):
        goto(env, pg, '/trip/hzh1/', 600)
        pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=15000); pg.wait_for_timeout(500)
        tx = pg.inner_text('.rm-sht'); shot('l4_day_map.png')
        check('L4a 每天的整屏地图：没有图例（.rm-leg 不存在）、不写“每天一种颜色”、不写“第 N 天”色块说明，仍说明是直线示意（%s）' % tx.replace('\n', ' ')[-60:], pg.evaluate("!document.querySelector('.rm-leg')") and '每天一种颜色' not in tx and '直线示意' in pg.inner_text('.rm-hint'), tx[-80:])
        pg.go_back(); pg.wait_for_timeout(500)
        goto(env, pg, '/trip/hcz4/', 600)
        pg.click('.mapgo'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=15000); pg.wait_for_timeout(500)
        tx = pg.inner_text('.rm-sht'); shot('l4_ov_map.png')
        check('L4b 总览（8 天）不写“每天一种颜色”（颜色本来就会重复）；点天数章 / 列表行进那一天（%s）' % tx.replace('\n', ' ')[:50], '每天一种颜色' not in tx and pg.evaluate("document.querySelectorAll('.rm-dr').length") == 8, tx[:80])
        pg.go_back(); pg.wait_for_timeout(300)

    # ─────────── L5 导航分段层
    with guard('L5'):
        goto(env, pg, '/trip/hcz4/', 600)
        pg.evaluate("document.querySelector('#d1 .rm-nb').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-nb'); pg.wait_for_selector('.rm-sheet'); pg.wait_for_timeout(500)
        o = pg.evaluate("""()=>{var s=document.querySelector('.rm-sheet'),vis=function(e){var r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.display!=='none'&&cs.visibility!=='hidden'},
          segs=[].slice.call(s.querySelectorAll('a.rm-seg')),ink=function(){var t=document.createElement('i');t.style.color=getComputedStyle(document.documentElement).getPropertyValue('--ink').trim();document.body.appendChild(t);var c=getComputedStyle(t).color;t.remove();return c}(),
          closes=[].slice.call(s.querySelectorAll('.pk-x,.pk-xb')).filter(vis),note=s.querySelector('.xnote');
          return {closes:closes.length,filled:segs.filter(function(a){return getComputedStyle(a).backgroundColor===ink}).length,segs:segs.length,note:note?note.textContent.trim():'',chars:s.innerText.replace(/\\s+/g,'').length}}""")
        shot('l5_nav_sheet.png')
        check('L5a 分段层只有 1 个“关上”可见（%d）' % o['closes'], o['closes'] == 1, o)
        check('L5b 只有 1 个主操作（实心的段 %d / 共 %d 段）' % (o['filled'], o['segs']), o['segs'] >= 2 and o['filled'] == 1, o)
        check('L5c 说明一行（%d 字：%s）、整层文字 ≤150 字（%d）' % (len(o['note']), o['note'], o['chars']), 0 < len(o['note']) <= 40 and o['chars'] <= 150, o)

    # ─────────── L6 /follow/
    with guard('L6'):
        goto(env, pg, '/follow/', 500); pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); pg.wait_for_timeout(200)
        v = pg.evaluate(VIEW); shot('l6_follow_index.png')
        deck = pg.inner_text('.fidx .deck'); cvis = pg.evaluate("(function(){var e=document.querySelector('.fcnt');return !e.hidden||e.getBoundingClientRect().height>0})()")
        pg.fill('.fidx .fsearch input', '苏'); pg.wait_for_timeout(150); pg.fill('.fidx .fsearch input', ''); pg.wait_for_timeout(200)      # 输入又清空：数量行要跟着收回去
        cvis = cvis or pg.evaluate("(function(){var e=document.querySelector('.fcnt');return !e.hidden||e.getBoundingClientRect().height>0})()")
        check('L6a /follow/ 搜索前不显示“共 N 个”数量行（%s）；一句话 %d 字不重复标题（%s）' % (cvis, len(deck), deck), not cvis and len(deck) <= 28 and '跟着一个人' not in deck, (cvis, deck))
        z = pg.evaluate(ZONE, '.fgrp'); zb = BEFORE_Z['follow']
        check('L6b /follow/ 搜索区（页顶到第一组卡片）：可点 %d、文字块 %d、字数 %d、合计 %d（旧 %s；上限 %s）' % (z[0], z[1], z[2], z[3], zb, CEIL_Z['follow']), z[0] <= CEIL_Z['follow'][0] and z[1] <= CEIL_Z['follow'][1] and z[2] <= CEIL_Z['follow'][2] and z[3] < zb[3] and z[2] < zb[2], z)
        goto(env, pg, '/follow/zhenghe/', 500); pg.evaluate("window.scrollTo({top:0,behavior:'instant'})")
        o = pg.evaluate("(function(){var a=document.querySelector('.fl a'),t=document.querySelector('.ftl');var r=a.getBoundingClientRect();return {cardBottom:Math.round(r.bottom),vh:innerHeight,tl:Math.round(t.getBoundingClientRect().top+scrollY),card:Math.round(r.top+scrollY),fnn:(document.body.innerText.match(/只写有记载的事/g)||[]).length}})()")
        shot('l6_follow_topic.png')
        check('L6c 主题页第一屏就有线路入口（线路卡底 %dpx ≤ 视口 %d），在年表前面（卡 %d < 年表 %d）' % (o['cardBottom'], o['vh'], o['card'], o['tl']), o['cardBottom'] <= o['vh'] and o['card'] < o['tl'], o)
        check('L6d “只写有记载的事，传说会标明相传”在主题页只写一次（%d）' % o['fnn'], o['fnn'] == 1, o)
        goto(env, pg, '/trip/hzh1/', 400)
        check('L6e 线路页里没有这句（%d）' % pg.evaluate("(document.body.innerText.match(/只写有记载的事/g)||[]).length"), pg.evaluate("(document.body.innerText.match(/只写有记载的事/g)||[]).length") == 0)
        # 搜索后数量行才出现
        goto(env, pg, '/follow/', 400); pg.fill('.fidx .fsearch input', '苏'); pg.wait_for_timeout(200)
        check('L6f 输入后才出现“找到 N 个”（%s）' % pg.inner_text('.fcnt'), pg.inner_text('.fcnt').startswith('找到'))

    # ─────────── L7 /long/
    with guard('L7'):
        goto(env, pg, '/long/', 500); pg.evaluate("window.scrollTo({top:0,behavior:'instant'})"); z = pg.evaluate(ZONE, '.lcards'); shot('l7_long.png')
        deck = pg.inner_text('.lpg .deck'); zb = BEFORE_Z['long']
        check('L7 /long/ 筛选区（页顶到第一张卡）：可点 %d（都是筛选，不能删；旧 %s）、字数 %d（旧 %s）、一句话 %d 字（%s）不带“最长 N 天”' % (z[0], zb[0], z[2], zb[2], len(deck), deck), z[0] <= CEIL_Z['long'][0] and z[2] < zb[2] and len(deck) <= 14 and '最长' not in deck, (z, deck))

    # ─────────── L8 文案：套话不能回来
    with guard('L8'):
        bad = ['点日期可改', '按最佳季节', '每天一种颜色', '路线按驾车排好，到了地图里可以改成步行或公交', '这天一共', '手机导航要分']
        hit = []
        for path in ('/trip/hzh1/', '/trip/hcz4/', '/trip/xl9a/', '/follow/', '/follow/zhenghe/', '/long/', '/'):
            goto(env, pg, path, 300); t = pg.evaluate("document.body.innerText")
            hit += [(path, w) for w in bad if w in t]
        goto(env, pg, '/trip/hcz4/', 400); pg.click('.mapgo'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view", timeout=15000); pg.wait_for_timeout(300)
        t = pg.evaluate("document.querySelector('.rm').innerText"); hit += [('hcz4 总览图', w) for w in bad if w in t]
        check('L8 新增文案里的套话一条都没回来（%s）' % hit, not hit, hit)

    # ─────────── L9 步数
    for rid in TRIPS:
        with guard('L9 ' + rid):
            goto(env, pg, '/trip/%s/' % rid, 600)
            y = pg.evaluate("(function(){var e=document.querySelector('.pre li.etq,.pre li.mus');return e?Math.round(e.getBoundingClientRect().top+scrollY):-1})()")
            f = pg.evaluate("(function(){var e=document.querySelector('#d1 .tl .r');return Math.round(e.getBoundingClientRect().top+scrollY)})()")
            old = {'hzh1': 1966, 'hcz4': 2196, 'xl9a': 2805, 'sh5d': 1432}[rid]
            ok = (y == -1 or y < 844) and f <= old - 150
            check('L9 %s 礼仪/预约/闭馆提醒在第一屏（离页顶 %d，视口 844；没有这类提醒=-1），第 1 天第一站 %d px = %.2f 屏（旧 %.2f 屏）' % (rid, y, f, f / 844, old / 844), ok, (y, f, old))
    br.close()
env.finish('less_is_more_check')
