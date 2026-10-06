import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/hz3/', wait_until='networkidle'); pg.wait_for_timeout(500)
    out['今晚住标题']=pg.evaluate("[...document.querySelectorAll('.stays .sh span:last-child')].map(s=>s.textContent)")
    out['出发前']=pg.evaluate("[...document.querySelectorAll('.pre li')].map(li=>(li.querySelector('input')?'☐ ':'· ')+li.innerText.replace(/\\n/g,' '))")
    out['要办按钮']=pg.evaluate("document.querySelector('.todoall').innerText.replace(/\\n/g,'｜')")
    pg.locator('.todoall').click(); pg.wait_for_timeout(300)
    out['要办的事']=pg.evaluate("[...document.querySelectorAll('.tdl li span')].map(s=>s.innerText.split('\\n')[0])"); pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    out['有没有路线图']=pg.evaluate("!!document.querySelector('.hmap')")
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    out['多留一天']=pg.evaluate("document.querySelector('.xd button[data-free] b').innerText")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
