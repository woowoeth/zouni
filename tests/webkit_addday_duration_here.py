import json, sys
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
V="""(sel)=>[...document.querySelectorAll(sel+' .tl > .r')].filter(r=>getComputedStyle(r).display!=='none').map(r=>r.querySelector('time').textContent+' '+r.querySelector('.m').childNodes[0].textContent.trim()+((r.querySelector('.s')||{}).textContent?' ｜ '+r.querySelector('.s').textContent.replace(/调整$/,''):''))"""
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13'],geolocation={'latitude':31.23,'longitude':121.47},permissions=['geolocation']); pg=ctx.new_page(); out={}
    pg.goto(B+'/trip/hyg2/', wait_until='networkidle'); pg.wait_for_timeout(400)
    cands=pg.evaluate("JSON.parse(document.getElementById('cands').textContent).map(c=>c.title+' '+c.km+'km')"); out['候选']=cands
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300)
    btn=pg.locator('.xd button[data-rid]').filter(has_text='兴坪')
    (btn.first if btn.count() else pg.locator('.xd button[data-rid]').first).click(); pg.wait_for_timeout(1800)
    out['加的那天']=pg.evaluate(V,'.xday'); out['加的那天说明']=pg.evaluate("(document.querySelector('.xday .lead')||{}).textContent||''")
    # 多待 30 分钟，时长跟着变
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.locator('#d2 .r.see .adj').first.scroll_into_view_if_needed(); pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-d="30"]').click(); pg.wait_for_timeout(300)
    out['兵马俑多待30分钟']=pg.evaluate(V,'#d2')[:3]
    pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-d="-30"]').click(); pg.wait_for_timeout(200); pg.locator('#d2 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-d="-30"]').click(); pg.wait_for_timeout(300)
    out['再少待两次（共少 30 分钟）']=pg.evaluate(V,'#d2')[1:2]
    # 首页当前位置
    pg.goto(B+'/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['第一个出发地']=pg.evaluate("document.querySelector('.pkr[data-k=\"o\"] button').innerText")
    pg.locator('.pkr[data-k="o"] button').first.click(); pg.wait_for_timeout(800)
    pg.locator('.pkr[data-k="d"] button[data-v="w"]').click(); pg.locator('.pkr[data-k="w"] button[data-v="f"]').click(); pg.wait_for_timeout(300)
    out['当前位置（上海）推荐']=pg.evaluate("[...document.querySelectorAll('.pkres li')].map(l=>l.innerText.replace(/\\n/g,' '))")
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(300); pg.locator('.tvbtn').click(); pg.wait_for_timeout(300)
    out['返回按钮']=pg.evaluate("(()=>{const b=document.querySelector('.tvx');const s=b.querySelector('svg').getBoundingClientRect();return b.innerText+' 箭头 '+Math.round(s.width)+'×'+Math.round(s.height)})()")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
