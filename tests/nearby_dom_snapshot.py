#!/usr/bin/env python3
"""行程页时间表的全量快照：改 replan() 之前后各跑一次，逐项比对（不是断言，输出 JSON 让 compare 去 diff）。

它补的是 webkit_*.py 的缺口：那些脚本只打印前几行，这里把整页每一行的 时间 / 名字 / 第二行文字 / 隐藏与否 / 关键 data 属性
/ 导航链接 / 页头摘要 / 复制行程文本 / 日历文件 / 分享链接 / 今天视图 全部存下来。
状态：原样、改出发时间、多待少待、去掉一站、组合+晚点、去掉一天、加一天（自由活动）、下雨换室内。
单独跑：python3 tests/nearby_dom_snapshot.py [站点根 URL] [trip1,trip2,…]   （要自己先起好站点服务；webkit→chromium 的补丁见 nearby_baseline.py）
"""
import json, sys
from playwright.sync_api import sync_playwright

B = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8765'
TRIPS = (sys.argv[2].split(',') if len(sys.argv) > 2 else ['xa3', 'gqhx10', 'xl9a', 'tk4', 'par5', 'nj3', 'slgt8', 'bkk3'])

# 只收“旧版本就有的”属性：新版本会多出 data-ll 之类，不能算差异
ATTRS = ['data-at', 'data-meal', 'data-in', 'data-cw', 'data-k', 'data-t0', 'data-slack', 'data-fo', 'data-fs', 'data-d0', 'data-rain', 'data-on', 'data-sd']

DUMP = r"""(ATTRS)=>{
  const tx=e=>e?e.textContent.replace(/\s+/g,' ').trim():'';
  const rows=r=>[...r.querySelectorAll(':scope > .tl > .r')].map(r=>{const m=r.querySelector('.m'),s=r.querySelector('.s'),a=r.querySelector('a.ic.map');
    const at={};ATTRS.forEach(k=>{if(r.hasAttribute(k))at[k]=r.getAttribute(k)});
    return {c:r.className.replace(/\s+/g,' ').trim(),h:r.hidden,t:tx(r.querySelector('time')),m:m&&m.childNodes[0]?m.childNodes[0].textContent.trim():'',m2:tx(m),s:tx(s),at:at,map:a?a.getAttribute('href'):''}});
  const days=[...document.querySelectorAll('.day')].map(d=>({id:d.id,oi:d.dataset.oi,extra:d.dataset.extra||'',head:tx(d.querySelector('header')),facts:[...d.querySelectorAll('.facts .fx')].map(f=>f.hidden?'':tx(f)).filter(Boolean),
     st:tx(d.querySelector('.st b')),warn:tx(d.querySelector('.latewarn')),lead:tx(d.querySelector('.lead')),fc:[...d.querySelectorAll('.fc')].map(tx),rows:rows(d)}));
  return {days:days,glance:tx(document.querySelector('.glance')),dock:tx(document.querySelector('.dock b')),dockSmall:tx(document.querySelector('.dock small')),
    ov:[...document.querySelectorAll('.overview ol > li')].map(tx),ovh:tx(document.querySelector('.overview h2')),stay:tx(document.querySelector('.ovstay')),rmnote:tx(document.querySelector('.rmnote')),
    nav:[...document.querySelectorAll('.daynav a')].map(a=>a.textContent).join(','),title:tx(document.querySelector('.hero-t h1')),
    ls:Object.keys(localStorage).filter(k=>/^zouni_/.test(k)&&!/^zouni_(seen|hist|wxtip)/.test(k)).sort().map(k=>k+'='+localStorage.getItem(k))}}"""

CLIP = "()=>{window.__c='';Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t}},configurable:true});try{delete navigator.share}catch(e){};navigator.share=undefined}"


def goto(pg, trip, init=None):
    url = B + '/trip/' + trip + '/'
    pg.goto(url, wait_until='networkidle')
    if init:
        pg.evaluate(init)
        pg.goto(url, wait_until='networkidle')
    pg.wait_for_timeout(500)


def exports(pg):
    """复制行程、日历、分享链接（解码出来的状态）、今天视图第 1 天的文字"""
    out = {}
    pg.evaluate(CLIP)
    pg.locator('.share').scroll_into_view_if_needed()
    pg.locator('.share').click(); pg.wait_for_timeout(200)
    pg.locator('.xd button[data-a="copy"]').click(); pg.wait_for_timeout(300)
    out['copy'] = pg.evaluate('window.__c')
    pg.locator('.share').click(); pg.wait_for_timeout(200)
    pg.locator('.xd button[data-a="link"]').click(); pg.wait_for_timeout(300)
    out['link'] = (pg.evaluate('window.__c') or '').replace(B, '')
    try:
        out['ics'] = pg.evaluate('window.zIcs?window.zIcs():""')
    except Exception as e:
        out['ics'] = 'ERR ' + str(e)[:80]
    pg.wait_for_timeout(100)
    try:
        pg.locator('.tvbtn').click(); pg.wait_for_timeout(300)
        out['today'] = pg.evaluate("[...document.querySelectorAll('.tvl li')].map(l=>l.innerText.replace(/\\s+/g,' '))")
        out['today_nav'] = pg.evaluate("[...document.querySelectorAll('.tvl .tvnav')].map(a=>a.getAttribute('href')).slice(0,6)")
        pg.locator('.tvx').first.click(); pg.wait_for_timeout(150)
    except Exception as e:
        out['today'] = 'ERR ' + str(e)[:80]
    return out


def first_see_k(pg, oi):
    return pg.evaluate("(oi)=>{const s=document.querySelector('.day[data-oi=\"'+oi+'\"]');const r=s&&[...s.querySelectorAll('.tl > .r.see,.tl > .r.fun')].find(r=>r.querySelector('.adj'));return r?+r.dataset.k:-1}", oi)


with sync_playwright() as p:
    b = p.webkit.launch()
    res = {}
    for trip in TRIPS:
        R = res[trip] = {}
        ctx = b.new_context(**p.devices['iPhone 13'])
        pg = ctx.new_page(); errs = []
        pg.set_default_timeout(60000); pg.set_default_navigation_timeout(90000)      # 机器忙的时候（别的构建在跑）加载会慢，不能因此把基线存成半截
        pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
        pg.on('dialog', lambda d: d.accept())
        try:
            goto(pg, trip)
            n = pg.evaluate("document.querySelectorAll('.day').length")
            R['0 原样'] = pg.evaluate(DUMP, ATTRS)
            R['0 原样 · 导出'] = exports(pg)
            ids = {'a': 1 if n > 1 else 0, 'b': 0}
            k1 = first_see_k(pg, ids['a']); k0 = first_see_k(pg, 0)
            # 1 出发时间：第 1、2 天分别改
            ST = "(()=>{localStorage.setItem('zouni_st_%s',JSON.stringify({0:'10:30',%d:'08:00'}))})()" % (trip, ids['a'])
            goto(pg, trip, ST); R['1 出发时间改'] = pg.evaluate(DUMP, ATTRS)
            # 2 多待 30、少待 30（同一天不同站）+ 另一天多待
            AD = "(()=>{const a={};a[%d]={};a[%d][%d]=30;a[0]={};a[0][%d]=-30;localStorage.setItem('zouni_adj_%s',JSON.stringify(a))})()" % (ids['a'], ids['a'], k1, k0, trip)
            goto(pg, trip, "localStorage.clear()"); goto(pg, trip, AD); R['2 多待少待'] = pg.evaluate(DUMP, ATTRS)
            R['2 多待少待 · 导出'] = exports(pg)
            ctx2 = b.new_context(**p.devices['iPhone 13']); pg2 = ctx2.new_page(); pg2.on('dialog', lambda d: d.accept())
            pg2.goto(B + R['2 多待少待 · 导出']['link'], wait_until='networkidle'); pg2.wait_for_timeout(900)      # 朋友打开分享链接：看到的要和分享的人一样
            R['2 朋友打开分享链接'] = pg2.evaluate(DUMP, ATTRS); ctx2.close()
            # 3 去掉一站（和它前面的出发行）
            def dropjs(oi, k):
                return "(()=>{const s=document.querySelector('.day[data-oi=\"%d\"]');const r=[...s.querySelectorAll('.tl > .r')].find(x=>x.dataset.k=='%d');const pv=r.previousElementSibling;const d={};d[%d]=[%d].concat(pv&&pv.classList.contains('dep')?[+pv.dataset.k]:[]);localStorage.setItem('zouni_drop_%s',JSON.stringify(d))})()" % (oi, k, oi, k, trip)
            goto(pg, trip, "localStorage.clear()")
            k1 = first_see_k(pg, ids['a'])
            pg.evaluate(dropjs(ids['a'], k1)); pg.goto(B + '/trip/' + trip + '/', wait_until='networkidle'); pg.wait_for_timeout(500)
            R['3 去掉一站'] = pg.evaluate(DUMP, ATTRS)
            R['3 去掉一站 · 导出'] = exports(pg)
            # 4 组合：晚出发 + 多待 + 去掉
            COMBO = "(()=>{localStorage.setItem('zouni_st_%s',JSON.stringify({%d:'15:00'}));const a={};a[%d]={};a[%d][%d]=30;localStorage.setItem('zouni_adj_%s',JSON.stringify(a))})()" % (trip, ids['a'], ids['a'], ids['a'], k1, trip)
            pg.evaluate(COMBO); pg.goto(B + '/trip/' + trip + '/', wait_until='networkidle'); pg.wait_for_timeout(500)
            R['4 组合（晚出发+多待+去掉）'] = pg.evaluate(DUMP, ATTRS)
            # 5 去掉一天
            goto(pg, trip, "localStorage.clear()")
            if n > 1:
                goto(pg, trip, "localStorage.setItem('zouni_rmday_%s','[1]')" % trip)
                R['5 去掉第2天'] = pg.evaluate(DUMP, ATTRS)
                R['5 去掉第2天 · 导出'] = exports(pg)
            # 6 加一天（自由活动，第 1 天后面）
            goto(pg, trip, "localStorage.clear()")
            if n > 1:
                goto(pg, trip, "localStorage.setItem('zouni_extra_%s',JSON.stringify([{k:'free',x:'f1',after:0}]))" % trip)
                R['6 加一天自由活动'] = pg.evaluate(DUMP, ATTRS)
                R['6 加一天 · 导出'] = exports(pg)
            # 7 下雨换室内：第 1 天的第一个可调的站
            goto(pg, trip, "localStorage.clear()")
            k0 = first_see_k(pg, 0)
            if k0 >= 0:
                goto(pg, trip, "localStorage.setItem('zouni_rain_%s',JSON.stringify({0:{k:%d,n:'某某博物馆',c:'某城'}}))" % (trip, k0))
                R['7 下雨换室内'] = pg.evaluate(DUMP, ATTRS)
                R['7 下雨换室内 · 导出'] = exports(pg)
            # 8 全叠加：去掉一天 + 出发时间 + 多待 + 下雨
            goto(pg, trip, "localStorage.clear()")
            if n > 2:
                goto(pg, trip, "(()=>{localStorage.setItem('zouni_rmday_%s','[2]');localStorage.setItem('zouni_st_%s',JSON.stringify({0:'10:00'}));const a={};a[0]={};a[0][%d]=30;localStorage.setItem('zouni_adj_%s',JSON.stringify(a))})()" % (trip, trip, k0, trip))
                R['8 叠加'] = pg.evaluate(DUMP, ATTRS)
                R['8 叠加 · 导出'] = exports(pg)
                ctx2 = b.new_context(**p.devices['iPhone 13']); pg2 = ctx2.new_page(); pg2.on('dialog', lambda d: d.accept())
                pg2.goto(B + R['8 叠加 · 导出']['link'], wait_until='networkidle'); pg2.wait_for_timeout(900)
                R['8 朋友打开分享链接'] = pg2.evaluate(DUMP, ATTRS); ctx2.close()
        except Exception as e:
            R['ERROR'] = repr(e)[:400]
        if 'ERROR' in R: print('SNAPSHOT-ERROR', trip, R['ERROR'], file=sys.stderr); sys.exit(3)      # 半截的快照不许当基线
        R['报错'] = errs
        ctx.close()
    print(json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True))
    b.close()
