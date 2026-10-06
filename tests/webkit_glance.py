import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page()
    out={}
    for t in ('xa3','g318','jz4'):
        pg.goto(f'http://localhost:8765/trip/{t}/', wait_until='networkidle'); pg.wait_for_timeout(400)
        # 量第二行文字本身（不是方框）的上沿：用 Range 取第一个字的位置
        out[t]=pg.evaluate("""()=>[...document.querySelectorAll('.glance>div')].slice(0,3).map(c=>{const s=c.querySelector('.dt')||c.querySelector('.pp')||c.querySelector(':scope>small');if(!s)return null;const r=document.createRange();const tn=[...s.childNodes].find(n=>n.nodeType===3&&n.textContent.trim());if(!tn)return null;r.setStart(tn,0);r.setEnd(tn,1);return Math.round(r.getBoundingClientRect().top)})""")
    pg.goto('http://localhost:8765/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(300); pg.locator('.glance').screenshot(path='/tmp/wk_glance.png')
    pg.locator('.glance .dt').click(); pg.wait_for_timeout(400); out['点了改']=pg.evaluate("!!document.querySelector('.pk-g')")
    pg.goto('http://localhost:8765/trip/jz4/', wait_until='networkidle'); pg.wait_for_timeout(300); pg.locator('.glance').screenshot(path='/tmp/wk_jz.png')
    pg.locator('.glance .pp').click(); pg.wait_for_timeout(300); out['点了人数']=pg.evaluate("!document.querySelector('.ppl')||!document.querySelector('.ppl').hidden")
    print(json.dumps(out,ensure_ascii=False)); b.close()
