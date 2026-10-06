import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); out={}; errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    for t in ('xa3','g318','bkk3'):
        pg.goto(B+f'/trip/{t}/',wait_until='networkidle'); pg.wait_for_timeout(400)
        if not pg.locator('.pp').count(): out[t]='没有人数按钮'; continue
        row=[pg.evaluate("document.querySelector('.glance .price').innerText")]
        pg.locator('.pp').click(); pg.wait_for_timeout(200)
        minus=pg.locator('.ppl button').first; plus=pg.locator('.ppl button').last
        minus.click(); pg.wait_for_timeout(150); row.append('1 人 '+pg.evaluate("document.querySelector('.glance .price').innerText"))
        for k in range(2,7): plus.click(); pg.wait_for_timeout(120); row.append(f'{k} 人 '+pg.evaluate("document.querySelector('.glance .price').innerText"))
        row.append('底栏 '+pg.evaluate("document.querySelector('.dock small').innerText"))
        out[t]=row
    out['报错']=errs
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
