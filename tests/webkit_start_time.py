import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
T="""(n)=>{const s=document.getElementById('d'+n);return [...s.querySelectorAll('.tl > .r')].filter(r=>!r.hidden).map(r=>r.querySelector('time').textContent+' '+r.querySelector('.m').childNodes[0].textContent.trim()).slice(0,9)}"""
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['西安第2天原来']=pg.evaluate(T,2)
    pg.locator('#d2 .st').scroll_into_view_if_needed(); pg.locator('#d2 .st').click(); pg.wait_for_timeout(300)
    out['面板']=pg.evaluate("[...document.querySelectorAll('.stg button')].map(b=>b.textContent).join(' ')")
    pg.locator('.stg button[data-v="10:30"]').click(); pg.wait_for_timeout(300)
    out['西安第2天改10:30']=pg.evaluate(T,2); out['表头和怎么排']=pg.evaluate("[document.querySelector('#d2 .st b').textContent, document.querySelectorAll('.overview ol li')[1].querySelector('em').textContent, (document.querySelector('#d2 .latewarn')||{}).innerText||'']")
    pg.reload(wait_until='networkidle'); pg.wait_for_timeout(400); out['重新打开']=pg.evaluate(T,2)[:2]
    pg.goto(B+'/trip/bkk3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['曼谷第1天原来']=pg.evaluate(T,1)
    pg.locator('#d1 .st').scroll_into_view_if_needed(); pg.locator('#d1 .st').click(); pg.wait_for_timeout(300); pg.locator('.stg button[data-v="12:00"]').click(); pg.wait_for_timeout(300)
    out['曼谷第1天改12:00']=pg.evaluate(T,1); out['提示']=pg.evaluate("(document.querySelector('#d1 .latewarn')||{}).innerText||''")
    if pg.locator('#d1 .latewarn .drop').count():
        pg.locator('#d1 .latewarn .drop').click(); pg.wait_for_timeout(300); out['去掉最后一站后']=pg.evaluate(T,1); out['提示2']=pg.evaluate("(document.querySelector('#d1 .latewarn')||{}).innerText||''")
    pg.locator('#d1 .latewarn .reset').click(); pg.wait_for_timeout(300); out['恢复后']=pg.evaluate(T,1)[:3]
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
