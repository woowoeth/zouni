import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.goto('http://localhost:8765/trip/fh3/',wait_until='networkidle'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('.todoall').scrollIntoView({block:'center'})}"); pg.wait_for_timeout(200)
    pg.locator('.todoall').first.click(); pg.wait_for_timeout(300)
    before=pg.evaluate("document.querySelector('.todo .tvd').innerText")
    n=pg.evaluate("[...document.querySelectorAll('.tdl li')].findIndex(l=>/起住/.test(l.innerText))")
    if n>=0: pg.locator('.tdl li .tck').nth(n).click(); pg.wait_for_timeout(300)
    after=pg.evaluate("document.querySelector('.todo .tvd').innerText")
    print(json.dumps({'住宿那项打勾前后':[before,after],'报错':errs},ensure_ascii=False)); b.close()
