import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
T="""(n)=>{const s=document.getElementById('d'+n);return [...s.querySelectorAll('.tl > .r')].filter(r=>!r.hidden).map(r=>r.querySelector('time').textContent+' '+r.querySelector('.m').childNodes[0].textContent.trim()).slice(0,8)}"""
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    # ① 兵马俑少待 30 分钟
    out['原来第2天']=pg.evaluate(T,2)
    pg.locator('#d2 .r.see .adj').first.scroll_into_view_if_needed(); pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(300)
    pg.locator('.xd button[data-d="-30"]').click(); pg.wait_for_timeout(300); out['兵马俑少待30分钟']=pg.evaluate(T,2)
    # 去掉华清宫
    pg.locator('#d2 .r.see .adj').nth(1).click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-x]').click(); pg.wait_for_timeout(300); out['去掉华清宫']=pg.evaluate(T,2)
    # ⑦ 放慢节奏
    pg.locator('.slowbar .slow').scroll_into_view_if_needed(); pg.locator('.slowbar .slow').click(); pg.wait_for_timeout(400)
    out['放慢节奏第1天']=pg.evaluate(T,1); out['放慢提示']=pg.evaluate("(document.querySelector('#d1 .latewarn p')||{}).innerText||''")
    # ③ 分享链接带修改
    pg.evaluate("()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); try{delete navigator.share}catch(e){} navigator.share=undefined; }")
    pg.locator('.share').click(); pg.wait_for_timeout(300); out['分享按钮说明']=pg.evaluate("document.querySelector('.xd button[data-a=\"link\"] small').innerText")
    pg.locator('.xd button[data-a="link"]').click(); pg.wait_for_timeout(300); link=pg.evaluate("window.__c"); out['链接长度']=len(link or '')
    ctx2=b.new_context(**p.devices['iPhone 13']); pg2=ctx2.new_page(); pg2.goto(link, wait_until='networkidle'); pg2.wait_for_timeout(800)
    out['朋友打开第2天']=pg2.evaluate(T,2); out['朋友打开放慢']=pg2.evaluate("document.querySelector('.slowbar .slow').classList.contains('on')"); out['朋友地址栏']=pg2.url.replace(B,'')
    # ④ 天气：把出发日改成明天
    tm=(datetime.date.today()+datetime.timedelta(days=1)).isoformat()
    pg2.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}", tm); pg2.wait_for_timeout(4000)
    out['天气预报']=pg2.evaluate("[...document.querySelectorAll('.day .fc')].map(x=>x.innerText).slice(0,3)")
    # ⑧ 打印样式
    pg2.emulate_media(media='print'); out['打印时隐藏']=pg2.evaluate("['.dock','.daynav','.addday','.slowbar'].map(s=>{const e=document.querySelector(s);return s+':'+(e?getComputedStyle(e).display:'无')})")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
