import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.goto('http://localhost:8765/trip/fh3/',wait_until='networkidle'); pg.wait_for_timeout(500)
    r1=pg.evaluate("[...document.querySelectorAll('.nextday')].map(a=>a.getAttribute('href')+' '+a.textContent)")
    pg.locator('#d1 .nextday').click(); pg.wait_for_timeout(700)
    top=pg.evaluate("Math.round(document.querySelector('#d2').getBoundingClientRect().top)")
    pg.on('dialog',lambda d:d.accept())
    pg.locator('#d2 .rmorig').click(); pg.wait_for_timeout(300)
    if pg.locator('.rmok, .cfm .ok, button:has-text(\"去掉\")').count(): 
        try: pg.locator('button:has-text(\"去掉\")').last.click()
        except Exception: pass
    pg.wait_for_timeout(800)
    r2=pg.evaluate("[...document.querySelectorAll('.nextday')].map(a=>a.getAttribute('href')+' '+a.textContent)")
    print(json.dumps({'下一天':r1,'点了第2天在屏幕顶部距离':top,'去掉第2天以后':r2,'报错':errs},ensure_ascii=False)); b.close()
