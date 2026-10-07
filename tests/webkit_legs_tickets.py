import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.add_init_script("try{localStorage.setItem('zouni_origin',JSON.stringify({n:'上海',lat:31.23,lng:121.47}))}catch(e){}")
    pg.goto('http://localhost:8765/trip/slgt8/',wait_until='networkidle'); pg.wait_for_timeout(500)
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('.todoall').scrollIntoView({block:'center'})}"); pg.wait_for_timeout(200)
    pg.locator('.todoall').first.click(); pg.wait_for_timeout(400)
    items=pg.evaluate("[...document.querySelectorAll('.tdl li')].map(l=>l.innerText.replace(/\\s+/g,' ').slice(0,60)).filter(t=>/票/.test(t))")
    print(json.dumps({'车票这几项':items,'报错':errs},ensure_ascii=False)); b.close()
