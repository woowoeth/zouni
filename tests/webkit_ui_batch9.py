import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); out={}; errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.goto('http://localhost:8765/trip/fh3/',wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';const s=document.querySelector('section.pre:not(.go)');scrollTo(0,s.getBoundingClientRect().top+scrollY-60)}"); pg.wait_for_timeout(200); pg.screenshot(path='/tmp/U1.png')
    pg.evaluate("()=>{const s=document.querySelector('#d1 .tl');scrollTo(0,s.getBoundingClientRect().top+scrollY-200)}"); pg.wait_for_timeout(200); pg.screenshot(path='/tmp/U2.png')
    if pg.locator('.faqmore').count():
        pg.evaluate("()=>{const s=document.querySelector('.faq');scrollTo(0,s.getBoundingClientRect().top+scrollY-200)}"); pg.wait_for_timeout(200)
        pg.locator('.faqmore').click(); pg.wait_for_timeout(300); out['常见问题点开后']=pg.evaluate("({shown:!document.querySelector('.faq dl').hidden,qs:document.querySelectorAll('.faq dt').length,btn:document.querySelector('.faqmore').innerText})"); pg.screenshot(path='/tmp/U3.png')
    out['底栏两个按钮间距']=pg.evaluate("(()=>{const a=document.querySelector('.dock .fav').getBoundingClientRect(),b=document.querySelector('.dock .tvbtn').getBoundingClientRect();return Math.round(b.left-a.right)+' 像素'})()")
    pg.goto('http://localhost:8765/d/guangxi/',wait_until='networkidle'); pg.wait_for_timeout(300)
    pg.evaluate("()=>{document.documentElement.style.scrollBehavior='auto';const s=document.querySelector('.qual.mus');if(s)scrollTo(0,s.getBoundingClientRect().top+scrollY-120)}"); pg.wait_for_timeout(200); pg.screenshot(path='/tmp/U4.png')
    out['报错']=errs; print(json.dumps(out,ensure_ascii=False)); b.close()
from PIL import Image
ims=[Image.open(f'/tmp/U{i}.png') for i in (1,2,3,4)]; ims=[im.resize((300,int(im.height*300/im.width))) for im in ims]
H=max(min(im.height,650) for im in ims); cc=Image.new('RGB',(4*306,H),'white')
for k,im in enumerate(ims): cc.paste(im.crop((0,0,300,min(im.height,H))),(k*306,0))
cc.save('/tmp/UI9.png')
