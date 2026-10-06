# 第二十八组：人数改了以后的组合（WebKit）
import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
R=[]
def rec(who, ok, find): R.append({'u':who,'ok':bool(ok),'find':find})
with sync_playwright() as p:
    b=p.webkit.launch()
    def ctx():
        c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100])); return c,pg,errs
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/dali5/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.pp').click(); pg.wait_for_timeout(200); pg.locator('.ppl button').last.click(); pg.wait_for_timeout(150); pg.locator('.ppl button').last.click(); pg.wait_for_timeout(150)
        mine=pg.evaluate("document.querySelector('.dock small').innerText")
        pg.reload(wait_until='networkidle'); pg.wait_for_timeout(400); kept=pg.evaluate("document.querySelector('.dock small').innerText")
        pg.evaluate("()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); navigator.share=undefined; }")
        pg.locator('.share').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-a="link"]').click(); pg.wait_for_timeout(300); link=pg.evaluate("window.__c")
        c2=b.new_context(**p.devices['iPhone 13']); pg2=c2.new_page(); pg2.goto(link,wait_until='load'); pg2.wait_for_timeout(2500); fr=pg2.evaluate("document.querySelector('.dock small').innerText"); c2.close()
        rec('152 小冯 · 大理丽江改成 4 人、刷新、分享',mine==kept==fr and mine.startswith('4 人'),f'我 {mine}；刷新后 {kept}；朋友 {fr}')
        rec('153 小冯 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小冯 · 卡住了',False,str(ex).split('\n')[0][:200])
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/hainl7/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.pp').click(); pg.wait_for_timeout(200); pg.locator('.ppl button').first.click(); pg.wait_for_timeout(150)
        one=pg.evaluate("document.querySelector('.glance .price').innerText"); 
        for k in range(5): pg.locator('.ppl button').last.click(); pg.wait_for_timeout(100)
        six=pg.evaluate("document.querySelector('.glance .price').innerText"); pp=pg.evaluate("document.querySelector('.pp').innerText")
        pg.locator('.pp').click(); pg.wait_for_timeout(200); hid=pg.evaluate("document.querySelector('.ppl').hidden")
        rec('154 小许 · 海南自驾 1 人和 6 人、收起面板',one!=six and hid,f'1 人 {one}；6 人 {six}；按钮“{pp}”；再点收起 {hid}')
        rec('155 小许 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小许 · 卡住了',False,str(ex).split('\n')[0][:200])
    b.close()
print(json.dumps({'R':R},ensure_ascii=False,indent=1))
