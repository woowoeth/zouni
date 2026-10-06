import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
ST="()=>[...document.querySelectorAll('.day')].map(s=>s.querySelector('h2').childNodes[0].textContent.trim()+' ｜ '+((s.querySelector('.stays .sh span:last-child')||{}).textContent||'（没有住宿卡）'))"
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(500); out['原来']=pg.evaluate(ST)
    pg.locator('#d1 .rmorig').scroll_into_view_if_needed(); pg.locator('#d1 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1000)
    out['去掉第1天（带住宿卡那天）']=pg.evaluate(ST)
    pg.locator('.rmback').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(800)
    pg.locator('#d2 .rmorig').scroll_into_view_if_needed(); pg.locator('#d2 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1000)
    out['去掉第2天']=pg.evaluate(ST)
    pg.locator('.rmback').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(500)
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
