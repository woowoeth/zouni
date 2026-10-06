import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('.todoall').scroll_into_view_if_needed(); out['按钮']=pg.evaluate("document.querySelector('.todoall').innerText.replace(/\\n/g,'')"); pg.locator('.todoall').click(); pg.wait_for_timeout(300)
    out['要办的事']=pg.evaluate("[...document.querySelectorAll('.todo h3')].map(h=>h.innerText+'：'+[...h.nextElementSibling.querySelectorAll('li span')].map(s=>s.innerText.split('\\n')[0]).join(' / '))"); pg.locator('.tvx').click()
    out['出发前链接位置']=pg.evaluate("[...document.querySelectorAll('.pre li a.bkl')].map(a=>{const li=a.closest('li').getBoundingClientRect(),r=a.getBoundingClientRect();return Math.round(li.right-r.right)+'px 离右边'})")
    pg.set_viewport_size({'width':320,'height':568}); pg.goto(B+'/trip/g318/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['320 宽底栏']=pg.evaluate("(()=>{const d=document.querySelector('.dock');const r=d.getBoundingClientRect();return {高:Math.round(r.height),收藏:document.querySelector('.dock .fav').innerText.trim()||'(只有图标)',按天:document.querySelector('.tvbtn').innerText,溢出:d.scrollWidth>d.clientWidth}})()")
    pg.locator('.dock').screenshot(path='/tmp/dock320.png')
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
