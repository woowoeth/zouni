# 第二十七组：再找 6 个人，专挑“改了很多东西之后”的组合（WebKit / iPhone 13）
import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
R=[]
def rec(who, ok, find): R.append({'u':who,'ok':bool(ok),'find':find})
VIS="(sel)=>[...document.querySelectorAll(sel)].filter(e=>getComputedStyle(e).display!=='none').length"
with sync_playwright() as p:
    b=p.webkit.launch()
    def ctx(**k):
        c=b.new_context(**p.devices['iPhone 13'],**k); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100])); return c,pg,errs
    today=datetime.date.today()
    # 1 小郑：今天出发 → 加自由活动 → 去掉第 2 天 → 按天看今天那格、下一站
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/bj4/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",today.isoformat()); pg.wait_for_timeout(300)
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-free]').click(); pg.wait_for_timeout(800)
        pg.locator('#d2 .rmorig').scroll_into_view_if_needed(); pg.locator('#d2 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(2000)
        d=pg.evaluate("({days:[...document.querySelectorAll('.day')].map(s=>s.querySelector('header small').textContent),dock:document.querySelector('.dock b').innerText,tv:(document.querySelector('.tvbtn')||{}).innerText})")
        pg.locator('.tvbtn').click(); pg.wait_for_timeout(300); t=pg.evaluate("({tabs:[...document.querySelectorAll('.tvtabs button')].map(b=>b.innerText).join(' '),title:document.querySelector('.tvb h2').innerText,head:document.querySelector('.tvd').innerText})")
        ok=len(d['days'])==4 and t['tabs'].startswith('今天') and today.strftime('%-m/%-d') in t['head']
        rec('140 小郑 · 今天出发、加一天、去掉第 2 天、按天看',ok,f"{d}；按天看 {t}")
        rec('141 小郑 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小郑 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 2 小钱：所有修改一起 → 分享 → 朋友打开逐项核对
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/xa3/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.evaluate("()=>{const i=document.querySelector('.dpk');i.value='2026-11-10';i.dispatchEvent(new Event('change'))}"); pg.wait_for_timeout(200)
        if pg.locator('.pp').count():
            pg.locator('.pp').click(); pg.wait_for_timeout(200)
            if pg.locator('.ppl button').count(): pg.locator('.ppl button').last.click(); pg.wait_for_timeout(200)
        n=pg.evaluate("document.querySelector('.dock small').innerText")
        pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-d="30"]').click(); pg.wait_for_timeout(250)
        pg.locator('#d2 .r.see .adj').nth(1).click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-x]').click(); pg.wait_for_timeout(250)
        pg.locator('#d3 .st').scroll_into_view_if_needed(); pg.locator('#d3 .st').click(); pg.wait_for_timeout(200); pg.locator('.stg button[data-v="10:00"]').click(); pg.wait_for_timeout(250)
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
        mine=pg.evaluate("""()=>({days:[...document.querySelectorAll('.day')].map(s=>s.querySelector('h2').childNodes[0].textContent.trim()),d2:[...document.querySelectorAll('#d2 .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('.m').childNodes[0].textContent.trim()).join('/'),st3:(document.querySelector('#d3 .st b')||{}).textContent,dock:document.querySelector('.dock').innerText.replace(/\\n/g,' ')})""")
        pg.evaluate("()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); navigator.share=undefined; }")
        pg.locator('.share').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-a="link"]').click(); pg.wait_for_timeout(300); link=pg.evaluate("window.__c")
        rec('小钱 · 分享出去的链接',bool(link),f'长度 {len(link or "")}：{(link or "")[:90]}…')
        c2,pg2,e2=ctx(); pg2.goto(link,wait_until='load',timeout=20000); pg2.wait_for_timeout(3000)
        fr=pg2.evaluate("""()=>({days:[...document.querySelectorAll('.day')].map(s=>s.querySelector('h2').childNodes[0].textContent.trim()),d2:[...document.querySelectorAll('#d2 .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('.m').childNodes[0].textContent.trim()).join('/'),st3:(document.querySelector('#d3 .st b')||{}).textContent,dock:document.querySelector('.dock').innerText.replace(/\\n/g,' ')})""")
        same=mine['days']==fr['days'] and mine['d2']==fr['d2'] and mine['st3']==fr['st3'] and mine['dock']==fr['dock']
        rec('142 小钱 · 改日期人数时长去站时间加天后分享',same,f"我：{json.dumps(mine,ensure_ascii=False)[:220]} ｜ 朋友：{json.dumps(fr,ensure_ascii=False)[:220]}"); c2.close()
        rec('143 小钱 · 页面报错',not errs and not e2,'；'.join(errs+e2) or '没有'); c.close()
    except Exception as ex: rec('小钱 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 3 小孔：收藏改过的行程 → 首页我的行程 → 出发倒计时 → 点进去还是改过的
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/sz3/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",(today+datetime.timedelta(days=9)).isoformat()); pg.wait_for_timeout(200)
        pg.locator('#d1 .rmorig').scroll_into_view_if_needed(); pg.locator('#d1 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1500)
        pg.locator('.dock .fav').click(); pg.wait_for_timeout(200)
        pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(300); pg.locator('.minebtn').click(); pg.wait_for_timeout(300)
        row=pg.evaluate("[...document.querySelectorAll('.pk a.mr')].map(a=>a.innerText.replace(/\\n/g,' '))")
        pg.locator('.pk a.mr').first.click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(800)
        dd=pg.evaluate("document.querySelectorAll('.day').length")
        rec('144 小孔 · 收藏改过的行程、从我的行程点回去',any('还有 9 天' in x for x in row) and dd==2,f'我的行程 {row}；点回去 {dd} 天')
        rec('145 小孔 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小孔 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 4 小卫：页面之间来回跳，返回键和“走”字
    try:
        c,pg,errs=ctx(); pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.goto(B+'/where/',wait_until='networkidle'); pg.goto(B+'/d/yunnan/',wait_until='networkidle'); pg.goto(B+'/trip/dali5/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.sq').first.click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(300); a=pg.url.replace(B,'')
        pg.goto(B+'/trip/dali5/',wait_until='networkidle'); pg.wait_for_timeout(200)
        home=pg.locator('a.sq:has-text("走"), .home').first
        if home.count(): home.click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(300)
        h=pg.url.replace(B,'')
        pg.goto(B+'/nope/',wait_until='networkidle'); nf=pg.evaluate("document.title+' | '+(document.querySelector('a[href=\"/where/\"]')?'有去哪儿入口':'没有入口')")
        rec('146 小卫 · 返回键、走字回首页、404',a in ('/d/yunnan/','/where/') and h=='/',f'行程页返回到 {a}；“走”回到 {h}；404：{nf}')
        rec('147 小卫 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小卫 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 5 小蒋：下雨备选换上后去掉那一天前面的一天，换的还在不在、对不对
    try:
        c,pg,errs=ctx(); pg.route('**/api.open-meteo.com/**', lambda r: r.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'daily':{'time':['x'],'weathercode':[63],'temperature_2m_max':[16],'temperature_2m_min':[9],'precipitation_probability_max':[85]}})))
        pg.goto(B+'/trip/hz3/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",(today+datetime.timedelta(days=2)).isoformat()); pg.wait_for_timeout(1500)
        sw=pg.locator('#d2 .rainswap')
        if sw.count(): sw.click(); pg.wait_for_timeout(400)
        before=pg.evaluate("[...document.querySelectorAll('.r[data-rain]')].map(r=>r.closest('.day').querySelector('h2').childNodes[0].textContent.trim()+'：'+r.querySelector('.m').childNodes[0].textContent)")
        pg.locator('#d1 .rmorig').scroll_into_view_if_needed(); pg.locator('#d1 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(2000)
        after=pg.evaluate("[...document.querySelectorAll('.r[data-rain]')].map(r=>r.closest('.day').querySelector('h2').childNodes[0].textContent.trim()+'：'+r.querySelector('.m').childNodes[0].textContent)")
        rec('148 小蒋 · 下雨换了室内，再去掉前一天',(not before) or (after and after[0].split('：')[0]==before[0].split('：')[0]),f'换之前后 {before} → 去掉第 1 天后 {after}')
        rec('149 小蒋 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小蒋 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 6 小沈：首页改日期 → 封面换 → 翻开 → 行程出发日跟着 → 替我挑结果按这个日期
    try:
        c,pg,errs=ctx(); pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.hdt').click(); pg.wait_for_timeout(300)
        for k in range(4): pg.locator('.pk-n').click(); pg.wait_for_timeout(80)
        pg.evaluate("()=>{const bs=[...document.querySelectorAll('.pk-g button:not([disabled])')];bs[14].click()}"); pg.wait_for_timeout(500)
        hd=pg.evaluate("document.querySelector('.hdt').innerText.replace(/\\n/g,'')"); cv=pg.evaluate("document.querySelector('.cv h2').innerText.replace(/\\n/g,'')")
        pg.locator('.cv .go').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(400); dt=pg.evaluate("document.querySelector('.dock b').innerText")
        rec('150 小沈 · 首页改日期、翻开封面',hd.split(' ')[0] in dt,f'首页“{hd}”，封面“{cv}”，行程底栏“{dt}”')
        rec('151 小沈 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小沈 · 卡住了',False,str(ex).split('\n')[0][:200])
    b.close()
print(json.dumps({'R':R},ensure_ascii=False,indent=1))
