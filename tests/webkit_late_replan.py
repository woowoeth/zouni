import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
FAKE="""(()=>{const RD=Date;const fixed=new RD('2026-10-06T17:57:00').getTime();class FD extends RD{constructor(...a){if(a.length)super(...a);else super(fixed)}static now(){return fixed}};window.Date=FD})();"""
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); c.add_init_script(FAKE); pg=c.new_page(); out={}; errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100]))
    pg.goto(B+'/trip/xa3/',wait_until='networkidle'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{const i=document.querySelector('.dpk');i.value='2026-10-06';i.dispatchEvent(new Event('change'))}"); pg.wait_for_timeout(300)
    pg.locator('.tvbtn').click(); pg.wait_for_timeout(400)
    out['下一站卡片（现在 17:57）']=pg.evaluate("(document.querySelector('.tvnext')||{}).innerText||''")
    if pg.locator('.tvlate').count():
        before=pg.evaluate("[...document.querySelectorAll('.tvl li')].map(l=>l.querySelector('time').textContent).join(',')")
        pg.locator('.tvlate').click(); pg.wait_for_timeout(500)
        out['点了以后']=pg.evaluate("[...document.querySelectorAll('.tvl li')].map(l=>l.querySelector('time').textContent).join(',')")
        out['点之前']=before
        out['卡片']=pg.evaluate("(document.querySelector('.tvnext')||{}).innerText||''")
        pg.locator('.tvx').click(); pg.wait_for_timeout(200)
        out['页面上第 1 天顶部']=pg.evaluate("(document.querySelector('#d1 .latewarn')||{}).innerText||''")
    out['报错']=errs
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
