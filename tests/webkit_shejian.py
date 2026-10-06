from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:80]))
    pg.goto('http://localhost:8765/trip/yz3/',wait_until='networkidle'); pg.wait_for_timeout(400)
    pg.evaluate("()=>{const s=document.querySelector('#d1');scrollTo(0,s.getBoundingClientRect().top+scrollY-50)}"); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/SJ1.png')
    pg.goto('http://localhost:8765/shejian/',wait_until='networkidle'); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/SJ2.png')
    pg.goto('http://localhost:8765/d/zhejiang/',wait_until='networkidle'); pg.wait_for_timeout(300); pg.evaluate("()=>{const s=document.querySelector('.se');scrollTo(0,s.getBoundingClientRect().top+scrollY-60)}"); pg.wait_for_timeout(300); pg.screenshot(path='/tmp/SJ3.png')
    print('报错', errs); b.close()
from PIL import Image
ims=[Image.open(f'/tmp/SJ{i}.png') for i in (1,2,3)]; ims=[im.resize((300,int(im.height*300/im.width))) for im in ims]
H=max(min(im.height,650) for im in ims); cc=Image.new('RGB',(3*306,H),'white')
for k,im in enumerate(ims): cc.paste(im.crop((0,0,300,min(im.height,H))),(k*306,0))
cc.save('/tmp/SJ.png')
