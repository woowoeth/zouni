import json, datetime
from playwright.sync_api import sync_playwright
B='https://zouni.app'; shots=[]
def snap(pg,name,sel=None):
    path=f'/tmp/A_{len(shots)+1:02d}.png'
    if sel: pg.locator(sel).first.screenshot(path=path)
    else: pg.screenshot(path=path)
    shots.append((path,name))
with sync_playwright() as p:
    b=p.webkit.launch(); ctx=b.new_context(**p.devices['iPhone 13'],geolocation={'latitude':31.23,'longitude':121.47},permissions=['geolocation']); pg=ctx.new_page()
    pg.route('**/api.open-meteo.com/**', lambda r: r.fulfill(status=200, content_type='application/json', headers={'Access-Control-Allow-Origin':'*'}, body=json.dumps({'daily':{'time':['x'],'weathercode':[63],'temperature_2m_max':[16],'temperature_2m_min':[9],'precipitation_probability_max':[85]}})))
    pg.goto(B+'/', wait_until='networkidle'); pg.wait_for_timeout(500)
    for k,v in (('o','上海'),('d','w'),('w','f')): pg.locator(f'.pkr[data-k="{k}"] button[data-v="{v}"]').click(); pg.wait_for_timeout(150)
    snap(pg,'首页 替我挑三条','.pick')
    pg.goto(B+'/trip/hz3/', wait_until='networkidle'); pg.wait_for_timeout(500)
    tm=(datetime.date.today()+datetime.timedelta(days=2)).isoformat()
    pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}", tm); pg.wait_for_timeout(1500)
    snap(pg,'行程 三格+出发前','.glance'); snap(pg,'出发前卡片','section.pre')
    snap(pg,'怎么排+地图','.overview')
    pg.evaluate("()=>{const s=document.querySelector('#d1');scrollTo(0,s.getBoundingClientRect().top+scrollY-50)}"); pg.wait_for_timeout(300); snap(pg,'第1天表头+天气+下雨备选')
    pg.locator('#d1 .r.see .adj').first.click(); pg.wait_for_timeout(300); snap(pg,'调整面板'); pg.locator('.xd button[data-d="30"]').click(); pg.wait_for_timeout(400)
    pg.evaluate("()=>{const s=document.querySelector('#d1 .latewarn');if(s)scrollTo(0,s.getBoundingClientRect().top+scrollY-120)}"); pg.wait_for_timeout(300); snap(pg,'调整后小结')
    pg.locator('#d1 .st').click(); pg.wait_for_timeout(300); snap(pg,'改出发时间面板'); pg.locator('.pk .pk-x').click(); pg.wait_for_timeout(200)
    pg.evaluate("()=>{const s=document.querySelector('#d1 .stays');scrollTo(0,s.getBoundingClientRect().top+scrollY-80)}"); pg.wait_for_timeout(300); snap(pg,'今晚住+去掉这一天')
    pg.locator('.addday .add').scroll_into_view_if_needed(); pg.wait_for_timeout(200); snap(pg,'加一天按钮+底栏')
    pg.locator('.addday .add').click(); pg.wait_for_timeout(300); snap(pg,'加一天面板'); pg.locator('.pk .pk-x').click(); pg.wait_for_timeout(200)
    pg.locator('.share').first.click(); pg.wait_for_timeout(300); snap(pg,'分享面板'); pg.locator('.pk .pk-x').click(); pg.wait_for_timeout(200)
    pg.locator('.tvbtn').click(); pg.wait_for_timeout(400); snap(pg,'按天看'); pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    pg.locator('.todoall').scroll_into_view_if_needed(); pg.locator('.todoall').click(); pg.wait_for_timeout(300); snap(pg,'要办的事'); pg.locator('.tvx').click(); pg.wait_for_timeout(200)
    pg.locator('.hmap').first.click(); pg.wait_for_timeout(400); snap(pg,'地图放大'); pg.locator('.hz-x').click(); pg.wait_for_timeout(200)
    pg.goto(B+'/d/zhejiang/', wait_until='networkidle'); pg.wait_for_timeout(400); pg.evaluate("()=>{const s=document.querySelector('.tf');if(s)scrollTo(0,s.getBoundingClientRect().top+scrollY-100)}"); pg.wait_for_timeout(300); snap(pg,'目的地页筛选')
    b.close()
from PIL import Image, ImageDraw, ImageFont
def sheet(items,out):
    ims=[(Image.open(pth),nm) for pth,nm in items]; ims=[(im.resize((300,int(im.height*300/im.width))),nm) for im,nm in ims]
    H=max(min(im.height,650) for im,_ in ims); c=Image.new('RGB',(4*306,2*(H+26)),'white'); d=ImageDraw.Draw(c)
    try: f=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',14)
    except Exception: f=None
    for k,(im,nm) in enumerate(ims):
        x=(k%4)*306; y=(k//4)*(H+26); d.text((x+4,y+2),nm,fill='black',font=f); c.paste(im.crop((0,0,300,min(im.height,H))),(x,y+22))
    c.save(out)
sheet(shots[:8],'/tmp/AU1.png'); sheet(shots[8:16],'/tmp/AU2.png'); print(len(shots))
