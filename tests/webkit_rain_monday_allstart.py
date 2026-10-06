import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13']); pg=ctx.new_page(); out={}
    # 假装接下来都下雨（拦下天气接口）
    pg.route('**/api.open-meteo.com/**', lambda r: r.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'daily':{'time':['x'],'weathercode':[63],'temperature_2m_max':[16],'temperature_2m_min':[9],'precipitation_probability_max':[85]}})))
    pg.goto(B+'/trip/xa3/', wait_until='networkidle'); pg.wait_for_timeout(400)
    out['门票']=pg.evaluate("[...document.querySelectorAll('.r .s.tix')].map(x=>x.innerText).slice(0,3)")
    # 整趟改 10:00
    pg.locator('.allbtn').scroll_into_view_if_needed(); pg.locator('.allbtn').click(); pg.wait_for_timeout(300)
    pg.locator('.stg button[data-v="10:00"]').click(); pg.wait_for_timeout(400)
    out['整趟改10点']=pg.evaluate("[1,2,3].map(n=>document.querySelector('#d'+n+' .st b').textContent)"); out['按钮']=pg.evaluate("document.querySelector('.allbtn').innerText")
    # 出发日改成明天，看天气 + 下雨备选；找个周一
    today=datetime.date.today(); tm=today+datetime.timedelta(days=1)
    nm=today+datetime.timedelta(days=(7-today.weekday())%7 or 7); st=nm-datetime.timedelta(days=2)   # 让第三天（陕历博）落在周一
    st=max(st, tm)
    pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}", st.isoformat()); pg.wait_for_timeout(1500)
    out['出发日']=st.isoformat()+' 周'+'一二三四五六日'[st.weekday()]
    out['天气和下雨备选']=pg.evaluate("[...document.querySelectorAll('.day .fc:not(.mon)')].map(x=>x.innerText.replace(/\\n/g,' ')).slice(0,2)")
    out['周一提醒']=pg.evaluate("[...document.querySelectorAll('.day .fc.mon')].map(x=>x.innerText)")
    if pg.locator('.rainswap').count():
        pg.locator('.rainswap').first.click(); pg.wait_for_timeout(600)
        out['换上以后']=pg.evaluate("[...document.querySelectorAll('.r[data-rain]')].map(r=>r.querySelector('.m').childNodes[0].textContent+' → '+r.querySelector('a.ic.map').href.slice(0,60))")
        out['换回按钮']=pg.evaluate("[...document.querySelectorAll('.rainback')].length")
    print(json.dumps(out,ensure_ascii=False,indent=1)); b.close()
