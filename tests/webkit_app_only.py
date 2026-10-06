import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); out={}
    for name,ctxa in (('iPhone',dict(p.devices['iPhone 13'])),('电脑',{'viewport':{'width':1280,'height':900}}),('微信',dict(p.devices['iPhone 13'],user_agent=p.devices['iPhone 13']['user_agent']+' MicroMessenger/8.0.50'))):
        c=b.new_context(**ctxa); pg=c.new_page(); pg.goto('http://localhost:8765/trip/hz3/',wait_until='networkidle'); pg.wait_for_timeout(1600)
        out[name]=pg.evaluate("({地图:[...document.querySelectorAll('.ic.map')].filter(e=>getComputedStyle(e).display!=='none').length,小红书:[...document.querySelectorAll('.ic.xhs')].filter(e=>getComputedStyle(e).display!=='none').length,携程:[...document.querySelectorAll('.tl2')].filter(e=>getComputedStyle(e).display!=='none').length,提示:(document.querySelector('.toast')||{}).innerText||''})"); c.close()
    print(json.dumps(out,ensure_ascii=False)); b.close()
