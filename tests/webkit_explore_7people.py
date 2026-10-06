# 第二十五组：找几个人多操作，组合着用，专门找体验问题和 bug（WebKit / iPhone 13）
import json, sys, datetime, re
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
R=[]; 
def rec(who, ok, find): R.append({'u':who,'ok':bool(ok),'find':find})
V="""(sel)=>[...document.querySelectorAll(sel)].filter(e=>getComputedStyle(e).display!=='none')"""
with sync_playwright() as p:
    b=p.webkit.launch()
    def ctx(**k):
        c=b.new_context(**p.devices['iPhone 13'],**k); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100])); return c,pg,errs
    # 1 小王：改日期 → 加一天 → 去掉原来一天 → 改某天出发时间 → 分享给朋友
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/xa3/',wait_until='networkidle'); pg.wait_for_timeout(400)
        pg.evaluate("()=>{const i=document.querySelector('.dpk');i.value='2026-11-02';i.dispatchEvent(new Event('change'))}"); pg.wait_for_timeout(300)
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
        pg.locator('#d1 .rmorig').scroll_into_view_if_needed(); pg.locator('#d1 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(2200)
        st=pg.evaluate("""()=>({days:[...document.querySelectorAll('.day')].map(s=>s.querySelector('header small').textContent+' '+s.querySelector('h2').childNodes[0].textContent.trim()),dock:document.querySelector('.dock b').innerText,big:document.querySelector('.glance b.big').innerText.replace(/\\n/g,''),nav:document.querySelectorAll('.daynav a').length,ov:document.querySelectorAll('.overview ol > li').length})""")
        ok1=len(st['days'])==3 and st['nav']==3 and st['ov']==3 and '3 天' in st['dock'] and st['big'].startswith('3')
        rec('108 小王 · 改日期+加一天+去掉第 1 天',ok1,json.dumps(st,ensure_ascii=False)[:300])
        pg.locator('#d1 .st').scroll_into_view_if_needed(); pg.locator('#d1 .st').click(); pg.wait_for_timeout(200); pg.locator('.stg button[data-v="10:30"]').click(); pg.wait_for_timeout(300)
        pg.evaluate("()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); navigator.share=undefined; }")
        pg.locator('.share').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-a="link"]').click(); pg.wait_for_timeout(300); link=pg.evaluate("window.__c")
        c2,pg2,e2=ctx(); pg2.goto(link,wait_until='networkidle'); pg2.wait_for_timeout(2500)
        st2=pg2.evaluate("""()=>({days:[...document.querySelectorAll('.day')].map(s=>s.querySelector('h2').childNodes[0].textContent.trim()),start:(document.querySelector('#d1 .st b')||{}).textContent,date:document.querySelector('.dock b').innerText})""")
        rec('109 小王的朋友 · 打开带修改的链接',len(st2['days'])==3 and st2['start']=='10:30' and '11/02' in st2['date'] or '11/2' in st2['date'],json.dumps(st2,ensure_ascii=False)[:300]); c2.close()
        rec('110 小王 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('1 小王 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 2 李姐：同一站多次调整、去掉、加空档、恢复，时间回到原样
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/xa3/',wait_until='networkidle'); pg.wait_for_timeout(400)
        T0=pg.evaluate("()=>[...document.querySelectorAll('#d2 .tl > .r time')].map(t=>t.textContent).join(',')")
        for d in ('30','30','-30'):
            pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator(f'.xd button[data-d="{d}"]').click(); pg.wait_for_timeout(250)
        du=pg.evaluate("()=>{const r=document.querySelector('#d2 .r.see');return [...r.querySelector('.s').childNodes].map(n=>n.textContent).join('')}")
        pg.locator('#d2 .r.see .adj').nth(1).click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-x]').click(); pg.wait_for_timeout(300)
        if pg.locator('#d2 .latewarn .fill').count(): pg.locator('#d2 .latewarn .fill').click(); pg.wait_for_timeout(300)
        pg.locator('#d2 .latewarn .reset').click(); pg.wait_for_timeout(300)
        T1=pg.evaluate("()=>[...document.querySelectorAll('#d2 .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('time').textContent).join(',')")
        names=pg.evaluate("()=>[...document.querySelectorAll('#d2 .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('.m').childNodes[0].textContent.trim()).join('/')")
        rec('111 李姐 · 调整三次、去掉一站、补空档、再恢复',T0==T1 and '空档加的' not in names,f'原来 {T0}；恢复后 {T1}；时长显示 {du[:40]}；{names[:80]}')
        rec('112 李姐 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('2 李姐 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 3 老张：今天出发，按天看，翻天，要办的事打勾，底栏
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/bj4/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",datetime.date.today().isoformat()); pg.wait_for_timeout(300); pg.reload(wait_until='networkidle'); pg.wait_for_timeout(500)
        tb=pg.evaluate("(document.querySelector('.tvbtn')||{}).innerText"); bar=pg.evaluate("!!document.querySelector('.today')")
        pg.locator('.tvbtn').click(); pg.wait_for_timeout(300); tabs=pg.evaluate("[...document.querySelectorAll('.tvtabs button')].map(b=>b.innerText).join(' ')")
        pg.locator('.tvtabs button[data-i="3"]').click(); pg.wait_for_timeout(200); last=pg.evaluate("document.querySelector('.tvb h2').innerText"); pg.locator('.tvx').click(); pg.wait_for_timeout(200)
        lock=pg.evaluate("document.body.classList.contains('pk-open')")
        rec('113 老张 · 今天出发、按天看、关上后能滚动',tb=='今天' and tabs.startswith('今天') and not lock,f'底栏“{tb}”，旅途中提示条{"有" if bar else "没有"}，天数 {tabs}，第 4 天“{last}”，关上后{"还锁着滚动" if lock else "能滚动"}')
        pg.locator('.todoall').scroll_into_view_if_needed(); pg.locator('.todoall').click(); pg.wait_for_timeout(300)
        n_=pg.evaluate("document.querySelectorAll('.tck').length"); pg.locator('.tck').first.click(); pg.wait_for_timeout(200); pg.locator('.tck').nth(1).click(); pg.wait_for_timeout(200)
        prog=pg.evaluate("document.querySelector('.todo .tvd').innerText"); pg.locator('.tvx').click(); pg.wait_for_timeout(200); btn=pg.evaluate("document.querySelector('.todoall').innerText.replace(/\\n/g,'')")
        rec('114 老张 · 要办的事打两项勾',f'2/{n_}' in prog and f'2/{n_}' in btn,f'{prog}；页面按钮 {btn}')
        rec('115 老张 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('3 老张 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 4 阿May：当前位置没给权限 → 提示；选城市 → 结果 → 进行程 → 返回首页答案还在
    try:
        c,pg,errs=ctx(); pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(400)
        pg.locator('.pkr[data-k="o"] button').first.click(); pg.wait_for_timeout(1500); t1=pg.evaluate("(document.querySelector('.toast')||{}).innerText||''")
        pg.locator('.pkr[data-k="o"] button[data-v="北京"]').click(); pg.locator('.pkr[data-k="d"] button[data-v="m"]').click(); pg.locator('.pkr[data-k="w"] button[data-v="c"]').click(); pg.wait_for_timeout(300)
        res=pg.evaluate("[...document.querySelectorAll('.pkres li')].map(l=>l.querySelector('b').innerText)")
        href=pg.evaluate("(document.querySelector('.pkres a')||{}).getAttribute&&document.querySelector('.pkres a').getAttribute('href')")
        if href: pg.goto(B+href,wait_until='networkidle'); pg.wait_for_timeout(300); pg.go_back(wait_until='networkidle'); pg.wait_for_timeout(500)
        kept=pg.evaluate("[...document.querySelectorAll('.pkr .on')].map(b=>b.innerText).join('/')")
        rec('116 阿May · 没给定位、选北京 4–5 天两个人',len(res)==3 and '北京' in kept,f'定位提示“{t1}”；推荐 {res}；返回后还选着 {kept}')
        rec('117 阿May · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('4 阿May · 卡住了',False,str(ex).split('\n')[0][:200])
    # 5 小陈：去哪儿 自驾+预算 → 地图看 → 目的地页筛选 → 行程 → 返回
    try:
        c,pg,errs=ctx(); pg.goto(B+'/where/?f=drive',wait_until='networkidle'); pg.wait_for_timeout(400)
        pg.select_option('.bud','5000'); pg.wait_for_timeout(300); n1=pg.evaluate("document.querySelector('.cnt').innerText")
        pg.locator('.mtog').click(); pg.wait_for_timeout(400); pts=pg.evaluate("document.querySelectorAll('.wmap circle').length")
        pg.goto(B+'/d/yunnan/',wait_until='networkidle'); pg.wait_for_timeout(300); f=pg.evaluate("[...document.querySelectorAll('.tf button')].map(b=>b.innerText).join(' ')")
        pg.locator('.tf button[data-f="d"]').click() if pg.locator('.tf button[data-f="d"]').count() else None; pg.wait_for_timeout(200)
        vis=pg.evaluate("[...document.querySelectorAll('.trips li')].filter(l=>getComputedStyle(l).display!=='none').map(l=>l.querySelector('b').innerText)")
        rec('118 小陈 · 自驾+预算 5K、地图看、云南页只看自驾',pts>0 and len(vis)>=1,f'{n1}；地图 {pts} 个点；云南筛选 {f}；自驾 {vis}')
        rec('119 小陈 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('5 小陈 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 6 刘哥：30 天长线加一天又去掉一天，地图和天数条
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/xbdh30/',wait_until='networkidle'); pg.wait_for_timeout(500)
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-free]').click(); pg.wait_for_timeout(800)
        a=pg.evaluate("({d:document.querySelectorAll('.day').length,nav:document.querySelectorAll('.daynav a').length,leg:document.querySelectorAll('.hmap .hlegend span').length})")
        pg.locator('#d5 .rmorig').scroll_into_view_if_needed(); pg.locator('#d5 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(2500)
        b2=pg.evaluate("({d:document.querySelectorAll('.day').length,nav:document.querySelectorAll('.daynav a').length,leg:document.querySelectorAll('.hmap .hlegend span').length,dock:document.querySelector('.dock b').innerText})")
        rec('120 刘哥 · 30 天加自由活动、再去掉第 5 天',a['d']==31 and a['nav']==31 and b2['d']==30 and b2['nav']==30 and '30 天' in b2['dock'],f'加后 {a}；去掉后 {b2}')
        rec('121 刘哥 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('6 刘哥 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 7 小孙：连续开关各种面板，最后能不能正常滚动
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/cd3/',wait_until='networkidle'); pg.wait_for_timeout(400)
        for sel,close in (('.share','.pk .pk-x'),('#d1 .st','.pk .pk-x'),('.addday .add','.pk .pk-x'),('.tvbtn','.tvx'),('.todoall','.tvx'),('.hmap','.hz-x')):
            if pg.locator(sel).count(): pg.locator(sel).first.scroll_into_view_if_needed(); pg.locator(sel).first.click(); pg.wait_for_timeout(250)
            if pg.locator(close).count(): pg.locator(close).first.click(); pg.wait_for_timeout(200)
        left=pg.evaluate("({lock:document.body.classList.contains('pk-open'),masks:document.querySelectorAll('.pk-mask,.pk,.tv,.hmap-zoom').length})")
        rec('122 小孙 · 连着开关 6 种面板',not left['lock'] and left['masks']==0,f'最后 {left}')
        rec('123 小孙 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex:
        rec('7 小孙 · 卡住了',False,str(ex).split('\n')[0][:200])
    b.close()
print(json.dumps({'R':R},ensure_ascii=False,indent=1))
