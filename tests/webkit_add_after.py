import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100]))
    pg.goto('http://localhost:8765/trip/xj10/',wait_until='networkidle'); pg.wait_for_timeout(700)
    n_btn=pg.locator('.addafter').count()
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('#d5').scrollIntoView()}"); pg.wait_for_timeout(200)
    pg.locator('#d5 .addafter').click(); pg.wait_for_timeout(500)
    panel=pg.evaluate("()=>{const p=document.querySelector('.pk');return p?p.innerText.replace(/\\s+/g,' ').slice(0,260):null}")
    pg.locator('.pk .xd button[data-rid]').first.click(); pg.wait_for_timeout(1500)
    after=pg.evaluate("()=>({days:document.querySelectorAll('.day').length,d6:(document.querySelector('#d6 h2')||{}).textContent,d5:(document.querySelector('#d5 h2')||{}).textContent,stay6:[...document.querySelectorAll('#d6 .tl > .r')].map(r=>r.innerText.replace(/\s+/g,' ')).filter(t=>/住/.test(t)).slice(-1)[0]||'无',ov:[...document.querySelectorAll('.overview ol>li')].slice(4,7).map(l=>l.innerText.replace(/\\s+/g,' ').slice(0,30)),head:(document.querySelector('.overview h2')||{}).textContent})")
    pg.reload(wait_until='networkidle'); pg.wait_for_timeout(1200)
    again=pg.evaluate("()=>({days:document.querySelectorAll('.day').length,d6:(document.querySelector('#d6 h2')||{}).textContent})")
    print(json.dumps({'每天下面的按钮':n_btn,'面板':panel,'选白哈巴后':after,'刷新后':again,'报错':errs},ensure_ascii=False)); b.close()
