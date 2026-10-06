import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/cd3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    first=pg.evaluate("document.querySelector('.xd button[data-rid] b').innerText"); pg.locator('.xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    out['再打开面板']=pg.evaluate("[...document.querySelectorAll('.xd button[data-rid]')].map(b=>b.innerText.split('\\n')[0]+(b.disabled?'（点不了）':''))")
    pg.locator('.xd button[data-rid]').first.click(force=True); pg.wait_for_timeout(500)
    out['加的天数']=pg.evaluate("document.querySelectorAll('.xday').length")
    if pg.locator('.pk .pk-x').count(): pg.locator('.pk .pk-x').click()
    pg.wait_for_timeout(200)
    out['两种去掉按钮']=pg.evaluate("[...document.querySelectorAll('.rmday')].slice(0,4).map(b=>{const s=getComputedStyle(b);return b.innerText+' | '+s.backgroundColor+' | '+s.color+' | '+s.fontSize+' | '+(b.classList.contains('rmorig')?'原来的天':'加的天')})")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
