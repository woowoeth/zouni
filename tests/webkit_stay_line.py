import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80])); pg.on('dialog',lambda d:d.accept())
    pg.goto('http://localhost:8765/trip/slgt8/',wait_until='networkidle'); pg.wait_for_timeout(500)
    a=pg.evaluate("(document.querySelector('.ovstay')||{}).textContent")
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('#d4').scrollIntoView()}"); pg.wait_for_timeout(200)
    pg.locator('#d4 .rmorig').click(); pg.wait_for_timeout(300)
    try: pg.locator('button:has-text(\"去掉\")').last.click()
    except Exception: pass
    pg.wait_for_timeout(900)
    b2=pg.evaluate("(document.querySelector('.ovstay')||{}).textContent")
    print(json.dumps({'原来':a,'去掉第 4 天（张掖）以后':b2,'报错':errs},ensure_ascii=False)); b.close()
