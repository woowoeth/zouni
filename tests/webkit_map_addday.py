import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/hkd5/', wait_until='networkidle'); pg.wait_for_timeout(500)
    q="""()=>{const s=document.querySelector('.hmap svg');return {marks:[...s.querySelectorAll('.dms text')].map(t=>t.textContent),legend:[...document.querySelectorAll('.overview .hlegend span')].map(x=>x.innerText.replace(/\\n/g,' ')),price:document.querySelector('.glance .price').innerText}}"""
    out['原来']=pg.evaluate(q)
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    pg.locator('.xd button[data-free]').click(); pg.wait_for_timeout(600)
    out['加自由活动后']=pg.evaluate(q)
    pg.locator('.hmap').screenshot(path='/tmp/wk_hkd5.png')
    pg.goto(B+'/trip/cd3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    pg.locator('.xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
    out['成都加三星堆后']=pg.evaluate("""()=>{const s=document.querySelector('.hmap svg');return {marks:[...s.querySelectorAll('.dms text')].map(t=>t.textContent),dash:s.querySelectorAll('.xl path').length,legend:[...document.querySelectorAll('.overview .hlegend span')].map(x=>x.innerText.replace(/\\n/g,' '))}}""")
    pg.locator('.hmap').screenshot(path='/tmp/wk_cd3.png')
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
