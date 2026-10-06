import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    # ③ 首页替我挑三条
    pg.goto(B+'/', wait_until='networkidle'); pg.wait_for_timeout(500)
    for k,v in (('o','上海'),('d','w'),('w','o')):
        pg.locator(f'.pkr[data-k="{k}"] button[data-v="{v}"]').click(); pg.wait_for_timeout(150)
    out['上海周末带老人孩子']=pg.evaluate("[...document.querySelectorAll('.pkres li')].map(l=>l.innerText.replace(/\\n/g,' '))")
    pg.locator('.pkr[data-k="o"] button[data-v="成都"]').click(); pg.locator('.pkr[data-k="d"] button[data-v="l"]').click(); pg.locator('.pkr[data-k="w"] button[data-v="f"]').click(); pg.wait_for_timeout(200)
    out['成都一周以上和朋友']=pg.evaluate("[...document.querySelectorAll('.pkres li')].map(l=>l.innerText.replace(/\\n/g,' '))")
    out['替我挑在第几屏']=pg.evaluate("(()=>{const s=document.querySelector('.pick');return +((s.getBoundingClientRect().top+scrollY)/innerHeight).toFixed(1)})()")
    # ① 今天：把出发日设成今天
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}", datetime.date.today().isoformat()); pg.wait_for_timeout(500)
    pg.reload(wait_until='networkidle'); pg.wait_for_timeout(500)
    out['底栏按钮']=pg.evaluate("(document.querySelector('.tvbtn')||{}).innerText")
    pg.locator('.tvbtn').click(); pg.wait_for_timeout(400)
    out['今天页']=pg.evaluate("({tabs:[...document.querySelectorAll('.tvtabs button')].map(b=>b.innerText),next:(document.querySelector('.tvnext')||{}).innerText||'（今天行程已过或还没到时间）',rows:document.querySelectorAll('.tvl li').length,past:document.querySelectorAll('.tvl li.past').length,stay:(document.querySelector('.tvbox')||{}).innerText||''})")
    pg.locator('.tvtabs button[data-i="1"]').click(); pg.wait_for_timeout(200); out['切到第2天']=pg.evaluate("document.querySelector('.tvb h2').innerText+' · '+document.querySelectorAll('.tvl li').length+' 行'")
    pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    # ② 要办的事
    pg.locator('.todoall').scroll_into_view_if_needed(); out['要办的按钮']=pg.evaluate("document.querySelector('.todoall').innerText"); pg.locator('.todoall').click(); pg.wait_for_timeout(300)
    out['要办的事']=pg.evaluate("[...document.querySelectorAll('.todo h3')].map(h=>h.innerText+' '+h.nextElementSibling.querySelectorAll('li').length+' 项')")
    pg.locator('.tck').first.click(); pg.wait_for_timeout(200); out['勾一项后']=pg.evaluate("document.querySelector('.todo .tvd').innerText")
    pg.locator('.tvx').click(); pg.wait_for_timeout(200); out['回到页面按钮']=pg.evaluate("document.querySelector('.todoall').innerText")
    # ④ 去掉华清宫后的小结和空档推荐
    pg.locator('#d2 .r.see .adj').nth(1).scroll_into_view_if_needed(); pg.locator('#d2 .r.see .adj').nth(1).click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-x]').click(); pg.wait_for_timeout(400)
    out['小结和空档']=pg.evaluate("(document.querySelector('#d2 .latewarn')||{}).innerText||''")
    if pg.locator('#d2 .latewarn .fill').count():
        pg.locator('#d2 .latewarn .fill').click(); pg.wait_for_timeout(400); out['加上以后']=pg.evaluate("[...document.querySelectorAll('#d2 .tl > .r')].filter(r=>!r.hidden).map(r=>r.querySelector('time').textContent+' '+r.querySelector('.m').childNodes[0].textContent.trim()).slice(2,7)")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
