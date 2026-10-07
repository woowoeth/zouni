import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.goto('http://localhost:8765/trip/fh3/',wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('.tvbtn').first.click(); pg.wait_for_timeout(500)
    on0=pg.evaluate("(document.querySelector('.tv .tvtabs button.on')||{}).textContent")
    pg.evaluate("""()=>{const tv=document.querySelector('.tv');const el=tv.querySelector('.tvb,.tvbody')||tv;const mk=(type,x)=>{const ev=new Event(type,{bubbles:true});const t={clientX:x,clientY:400};ev.touches=type==='touchend'?[]:[t];ev.changedTouches=[t];el.dispatchEvent(ev)};mk('touchstart',300);mk('touchend',100)}""")
    pg.wait_for_timeout(400)
    on1=pg.evaluate("(document.querySelector('.tv .tvtabs button.on')||{}).textContent")
    print(json.dumps({'滑之前':on0,'往左滑以后':on1,'报错':errs},ensure_ascii=False)); b.close()
