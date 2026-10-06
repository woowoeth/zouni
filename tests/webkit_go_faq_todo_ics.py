import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13'],timezone_id='Asia/Shanghai'); pg=c.new_page(); out={}; errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100]))
    pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(400); out['封面（没选出发地）']=pg.evaluate("document.querySelector('.cv .kick').innerText+' ｜ '+document.querySelector('.cv h2').innerText.replace(/\\n/g,'')")
    pg.locator('.pkr[data-k="o"] button[data-v="上海"]').click(); pg.wait_for_timeout(500)
    out['封面（选了上海）']=pg.evaluate("document.querySelector('.cv .kick').innerText+' ｜ '+document.querySelector('.cv h2').innerText.replace(/\\n/g,'')")
    pg.goto(B+'/trip/wy3/',wait_until='networkidle'); pg.wait_for_timeout(500)
    out['三格']=pg.evaluate("document.querySelector('.glance').innerText.replace(/\\n/g,' ')")
    out['怎么去']=pg.evaluate("[...document.querySelectorAll('section.go li')].map(l=>l.innerText)")
    out['常见问题']=pg.evaluate("[...document.querySelectorAll('.faq dt')].map(d=>d.innerText+'｜'+d.nextElementSibling.innerText.slice(0,40))")
    out['看实景图标']=pg.evaluate("document.querySelectorAll('.ic.xhs').length+' 个，第一个 '+(document.querySelector('.ic.xhs')||{}).href")
    pg.locator('.todoall').first.scroll_into_view_if_needed(); pg.locator('.todoall').first.click(); pg.wait_for_timeout(300)
    out['要办的事']=pg.evaluate("[...document.querySelectorAll('.todo h3')].map(h=>h.innerText+'：'+[...h.nextElementSibling.querySelectorAll('li')].map(l=>l.innerText.replace(/\\n/g,' ')).join(' / '))")
    ics=pg.evaluate("window.zIcs?window.zIcs():''"); out['日历文件']=f"{ics.count('BEGIN:VEVENT')} 条：" + ' / '.join(l[8:] for l in ics.split('\r\n') if l.startswith('SUMMARY:'))[:300]
    pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    # 今天出发，看“晚了”按钮
    pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}", datetime.date.today().isoformat()); pg.wait_for_timeout(300)
    pg.locator('.tvbtn').click(); pg.wait_for_timeout(400)
    out['按天看下一站']=pg.evaluate("(document.querySelector('.tvnext')||{}).innerText||'今天没有下一站了'")
    if pg.locator('.tvlate').count():
        before=pg.evaluate("[...document.querySelectorAll('.tvl li time')].map(t=>t.textContent).join(',')"); pg.locator('.tvlate').click(); pg.wait_for_timeout(500)
        out['晚了重排']=before+' → '+pg.evaluate("[...document.querySelectorAll('.tvl li time')].map(t=>t.textContent).join(',')")
    out['报错']=errs
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
