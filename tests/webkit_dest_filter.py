import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/d/sichuan/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['筛选']=pg.evaluate("[...document.querySelectorAll('.tf button')].map(b=>b.innerText)")
    pg.locator('.tf button[data-f="d"]').click(); pg.wait_for_timeout(200)
    out['自驾']=pg.evaluate("[...document.querySelectorAll('.trips li')].filter(l=>getComputedStyle(l).display!=='none').map(l=>l.querySelector('b').innerText)")
    pg.locator('.tf button[data-f="s"]').click(); pg.wait_for_timeout(200)
    out['2–3 天']=pg.evaluate("[...document.querySelectorAll('.trips li')].filter(l=>getComputedStyle(l).display!=='none').length")
    pg.evaluate("()=>{const s=document.querySelector('.tf');scrollTo(0,s.getBoundingClientRect().top+scrollY-80)}"); pg.wait_for_timeout(200); pg.screenshot(path='/tmp/W1.png')
    pg.goto(B+'/d/ningxia/', wait_until='networkidle'); pg.wait_for_timeout(300); out['宁夏（线路少）有筛选吗']=pg.evaluate("!!document.querySelector('.tf')")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
