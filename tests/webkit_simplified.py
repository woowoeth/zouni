import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
V="""(n)=>[...document.querySelectorAll('#d'+n+' .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('time').textContent+' '+r.querySelector('.m').childNodes[0].textContent.trim())"""
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/qdn5/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['放慢和整趟那一行']=pg.evaluate("[!!document.querySelector('.slowbar'),!!document.querySelector('.allst')]")
    out['出发前']=pg.evaluate("[...document.querySelectorAll('.pre li')].map(li=>(li.querySelector('input')?'☐ ':'· ')+li.innerText.replace(/\\n/g,' '))")
    pg.locator('.todoall').click(); pg.wait_for_timeout(300); out['要办的事']=pg.evaluate("[...document.querySelectorAll('.todo h3')].map(h=>h.innerText+'：'+[...h.nextElementSibling.querySelectorAll('li span')].map(s=>s.innerText.split('\\n')[0]).join(' / '))"); pg.locator('.tvx').click()
    out['第2天原来（看得见的）']=pg.evaluate(V,2)
    pg.locator('#d2 .r.see .adj').first.scroll_into_view_if_needed(); nm=pg.evaluate("document.querySelector('#d2 .r.see .m').childNodes[0].textContent.trim()")
    pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-x]').click(); pg.wait_for_timeout(400)
    out['去掉「'+nm+'」后（看得见的）']=pg.evaluate(V,2); out['顶部提示']=pg.evaluate("(document.querySelector('#d2 .latewarn')||{}).innerText||''")
    pg.locator('#d2 .latewarn').screenshot(path='/tmp/wk_lw.png')
    pg.locator('#d3 .st').scroll_into_view_if_needed(); pg.locator('#d3 .st').click(); pg.wait_for_timeout(200)
    out['时间面板']=pg.evaluate("document.querySelector('.pk').innerText.replace(/\\n/g,' ').slice(0,80)")
    pg.locator('.allin').check(); pg.locator('.stg button[data-v="10:00"]').click(); pg.wait_for_timeout(400)
    out['每天都 10:00']=pg.evaluate("[...document.querySelectorAll('.day .st b')].map(b=>b.textContent)")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
