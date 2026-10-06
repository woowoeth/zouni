import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/bj4/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('.todoall').scroll_into_view_if_needed(); pg.locator('.todoall').click(); pg.wait_for_timeout(300)
    out['要预约的']=pg.evaluate("[...document.querySelectorAll('.todo h3')].filter(h=>h.innerText==='要预约的').map(h=>[...h.nextElementSibling.querySelectorAll('li')].map(li=>li.innerText.replace(/\\n/g,' ')))[0]")
    pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    pg.evaluate("()=>{const s=document.querySelector('#d1 .tl');scrollTo(0,s.getBoundingClientRect().top+scrollY-60)}"); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/V1.png')
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
