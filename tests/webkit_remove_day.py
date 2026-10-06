import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
ST="""()=>({天:[...document.querySelectorAll('.day')].map(s=>s.querySelector('header small').textContent+' '+s.querySelector('h2').childNodes[0].textContent.trim()),
  怎么排:[...document.querySelectorAll('.overview ol > li')].map(li=>li.innerText.replace(/\\n/g,' ').slice(0,26)),天数条:[...document.querySelectorAll('.daynav a')].map(a=>a.textContent).join(''),
  顶部:document.querySelector('.glance b.big').innerText.replace(/\\n/g,''),底栏:document.querySelector('.dock b').innerText,地图:[...document.querySelectorAll('.hmap .hlegend span')].map(s=>s.innerText.replace(/\\n/g,' ')),
  提示:(document.querySelector('.rmnote')||{}).innerText||''})"""
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(600)
    out['原来']=pg.evaluate(ST)
    pg.locator('#d2 .rmorig').scroll_into_view_if_needed(); pg.locator('#d2 .rmorig').click(); pg.wait_for_timeout(300)
    out['确认']=pg.evaluate("document.querySelector('.pk').innerText.replace(/\\n/g,' ')")
    pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1200)
    out['去掉第2天后']=pg.evaluate(ST)
    pg.locator('.rmback').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1000)
    out['恢复后']=pg.evaluate("[...document.querySelectorAll('.day')].length+' 天'")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
