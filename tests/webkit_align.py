import json
from playwright.sync_api import sync_playwright
JS="""(sels)=>sels.map(s=>{const e=document.querySelector(s);if(!e)return [s,null];const r=e.getBoundingClientRect();const cs=getComputedStyle(e);
  // 文字实际起点：取第一个文字节点的位置
  let x=r.left;const w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.textContent.trim()?1:2});const t=w.nextNode();if(t){const rg=document.createRange();rg.selectNodeContents(t);const rr=rg.getClientRects()[0];if(rr)x=rr.left}
  return [s,Math.round(x*10)/10,cs.paddingLeft,cs.marginLeft,cs.letterSpacing,cs.textIndent]})"""
with sync_playwright() as p:
    b=p.webkit.launch(); c=b.new_context(**p.devices['iPhone 13']); pg=c.new_page(); out={}
    pg.goto('http://localhost:8765/',wait_until='networkidle'); pg.wait_for_timeout(400)
    out['首页']=pg.evaluate(JS,['.cover .kick','.cover h1','.cover h2','.hero .kick','.hero h1','.cv .kicker','.cv h2','header .kick'])
    pg.goto('http://localhost:8765/trip/xa5d/',wait_until='networkidle'); pg.wait_for_timeout(400)
    out['行程页']=pg.evaluate(JS,['.hero .kick','.hero h1','.trip .kick','.trip h1','header.hero small','header.hero h1','.hd .kick','.hd h1'])
    pg.goto('http://localhost:8765/where/',wait_until='networkidle'); pg.wait_for_timeout(400)
    out['走哪儿']=pg.evaluate(JS,['.where .kick','.where h1','.where .deck','.where .tabs button','.where .goodline','.where .mchips button','.where .rh'])
    pg.goto('http://localhost:8765/pian/',wait_until='networkidle'); pg.wait_for_timeout(300)
    out['跟片走']=pg.evaluate(JS,['.chan .kick','.chan h1','.chan .deck','.toc li a i','.toc b'])
    print(json.dumps(out,ensure_ascii=False)); b.close()
