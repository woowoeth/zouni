# 第二十六组：又找 8 个人，换着法子用（WebKit / iPhone 13 和小屏 320）
import json, sys, datetime
from playwright.sync_api import sync_playwright
B=sys.argv[1] if len(sys.argv)>1 else 'http://localhost:8765'
R=[]
def rec(who, ok, find): R.append({'u':who,'ok':bool(ok),'find':find})
OVF="()=>({w:document.documentElement.scrollWidth,cw:document.documentElement.clientWidth})"
with sync_playwright() as p:
    b=p.webkit.launch()
    def ctx(small=False, **k):
        d=dict(p.devices['iPhone 13']); 
        if small: d['viewport']={'width':320,'height':568}; d['screen']={'width':320,'height':568}
        c=b.new_context(**d,**k); pg=c.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)[:100])); return c,pg,errs
    # 1 小林（小屏 320）：各种面板打开时有没有横向溢出、按钮挤不挤
    try:
        c,pg,errs=ctx(True); pg.goto(B+'/trip/xa3/',wait_until='networkidle'); pg.wait_for_timeout(400); res=[]
        for name,sel,close in (('页面',None,None),('改出发时间','#d1 .st','.pk .pk-x'),('调整','#d2 .r.see .adj','.pk .pk-x'),('分享','.share','.pk .pk-x'),('加一天','.addday .add','.pk .pk-x'),('按天看','.tvbtn','.tvx'),('要办的事','.todoall','.tvx')):
            if sel: pg.locator(sel).first.scroll_into_view_if_needed(); pg.locator(sel).first.click(); pg.wait_for_timeout(300)
            o=pg.evaluate(OVF); res.append(f"{name}{'溢出' if o['w']>o['cw']+1 else ''}")
            if close and pg.locator(close).count(): pg.locator(close).first.click(); pg.wait_for_timeout(200)
        chips=pg.evaluate("1")
        bad=[x for x in res if '溢出' in x]
        rec('124 小林 · 320 宽打开 7 种界面',not bad,' / '.join(res)); rec('125 小林 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小林 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 2 Lily：曼谷——调整、加一天、按天看、天气、分享
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/bkk3/',wait_until='networkidle'); pg.wait_for_timeout(400)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",(datetime.date.today()+datetime.timedelta(days=3)).isoformat()); pg.wait_for_timeout(2500)
        wx=pg.evaluate("[...document.querySelectorAll('.day .fc:not(.mon)')].map(x=>x.innerText.split('\\n')[0]).slice(0,2)")
        pg.locator('#d1 .r.see .adj').first.click(); pg.wait_for_timeout(200); pg.locator('.xd button[data-d="-30"]').click(); pg.wait_for_timeout(300)
        sumy=pg.evaluate("(document.querySelector('#d1 .latewarn .sum')||{}).innerText||''")
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); cands=pg.evaluate("[...document.querySelectorAll('.xd button')].map(b=>b.innerText.split('\\n')[0])"); pg.locator('.pk .pk-x').click()
        rec('126 Lily · 曼谷天气、少待 30 分钟、加一天候选',len(wx)>=1 and sumy!='',f'天气 {wx}；小结“{sumy}”；加一天 {cands[:4]}')
        rec('127 Lily · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('Lily · 卡住了',False,str(ex).split('\n')[0][:200])
    # 3 老周：川藏线今天出发，按天看 14 天，去掉一天，加自由活动，分享
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/g318/',wait_until='networkidle'); pg.wait_for_timeout(400)
        pg.evaluate("(v)=>{const i=document.querySelector('.dpk');i.value=v;i.dispatchEvent(new Event('change'))}",datetime.date.today().isoformat()); pg.wait_for_timeout(300)
        pg.locator('.tvbtn').click(); pg.wait_for_timeout(300); t=pg.evaluate("({tabs:document.querySelectorAll('.tvtabs button').length,first:document.querySelector('.tvtabs button').innerText,next:(document.querySelector('.tvnext b')||{}).innerText||'没有下一站'})"); pg.locator('.tvx').click()
        pg.locator('#d14 .rmorig').scroll_into_view_if_needed(); pg.locator('#d14 .rmorig').click(); pg.wait_for_timeout(200); pg.locator('.rmgo').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(2000)
        after=pg.evaluate("({d:document.querySelectorAll('.day').length,last:document.querySelector('.day:last-of-type h2').childNodes[0].textContent.trim(),dock:document.querySelector('.dock b').innerText})")
        rec('128 老周 · 川藏线今天出发、去掉最后一天',t['tabs']==14 and after['d']==13,f'按天看 {t}；去掉第 14 天后 {after}')
        rec('129 老周 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('老周 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 4 陈姐：首页搜索 → 去哪儿带着词 → 清空筛选 → 切亚洲 → 换月份 → 返回
    try:
        c,pg,errs=ctx(); pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.fill('.hsearch input','莫高窟'); pg.locator('.hsearch button').click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(500)
        s1=pg.evaluate("({q:document.querySelector('#flt input')&&document.querySelector('#flt input').value||(document.querySelector('.flt input')||{}).value,cards:[...document.querySelectorAll('.card:not([hidden])')].map(c=>c.dataset.name)})")
        if pg.locator('.clr').count() and pg.locator('.clr').is_visible(): pg.locator('.clr').click(); pg.wait_for_timeout(300)
        s2=pg.evaluate("document.querySelector('.cnt').innerText")
        pg.locator('.tabs button[data-t="asia"]').click(); pg.wait_for_timeout(300); pg.locator('.mon button').nth(1).click() if pg.locator('.mon button').count() else None; pg.wait_for_timeout(300)
        s3=pg.evaluate("document.querySelector('.cnt').innerText")
        rec('130 陈姐 · 搜莫高窟、清空、切亚洲换月',('甘肃' in ','.join(s1['cards'])),f'搜到 {s1}；清空后 {s2}；亚洲换月 {s3}')
        rec('131 陈姐 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('陈姐 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 5 小马：替我挑“一周以上 + 带老人孩子”不能推高原；点进去的都不是高原
    try:
        c,pg,errs=ctx(); pg.goto(B+'/',wait_until='networkidle'); pg.wait_for_timeout(300)
        for k,v in (('o','成都'),('d','l'),('w','o')): pg.locator(f'.pkr[data-k="{k}"] button[data-v="{v}"]').click(); pg.wait_for_timeout(150)
        res=pg.evaluate("[...document.querySelectorAll('.pkres a')].map(a=>a.getAttribute('href'))"); hi=[]
        for h in res:
            pg.goto(B+h,wait_until='networkidle'); hi.append(h+(' 有高原' if pg.evaluate("/海拔 [34],\\d{3}/.test(document.body.innerText)") else ''))
        rec('132 小马 · 一周以上带老人孩子',len(res)==3 and not any('高原' in x for x in hi),' / '.join(hi))
        rec('133 小马 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小马 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 6 何姐：目的地页地图点名字进行程 → 返回 → 筛选状态
    try:
        c,pg,errs=ctx(); pg.goto(B+'/d/sichuan/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.tf button[data-f="m"]').click(); pg.wait_for_timeout(200)
        href=pg.evaluate("document.querySelector('.dmap a').getAttribute('href')"); pg.goto(B+href,wait_until='networkidle'); pg.wait_for_timeout(300); pg.go_back(wait_until='networkidle'); pg.wait_for_timeout(400)
        st=pg.evaluate("[...document.querySelectorAll('.tf .on')].map(b=>b.innerText).join('')")
        rec('134 何姐 · 四川页点地图进行程再返回','4–5' in st,f'进 {href}；返回后筛选停在“{st}”（回到“全部”也可以）')
        rec('135 何姐 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('何姐 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 7 赵哥：打印预览带着加的天和去掉的天
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/cd3/',wait_until='networkidle'); pg.wait_for_timeout(300)
        pg.locator('.addday .add').scroll_into_view_if_needed(); pg.locator('.addday .add').click(); pg.wait_for_timeout(300); pg.locator('.xd button[data-rid]').first.click(); pg.wait_for_timeout(1800)
        pg.emulate_media(media='print'); pr=pg.evaluate("({days:[...document.querySelectorAll('.day')].filter(s=>getComputedStyle(s).display!=='none').length,hidden:['.dock','.addday','.rmday','.adj','.tvbtn'].filter(s=>{const e=document.querySelector(s);return e&&getComputedStyle(e).display!=='none'})})")
        rec('136 赵哥 · 加了一天再打印',pr['days']==4 and not pr['hidden'],f'打印时 {pr["days"]} 天，没藏住的 {pr["hidden"]}')
        rec('137 赵哥 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('赵哥 · 卡住了',False,str(ex).split('\n')[0][:200])
    # 8 小吴：同一天连改两次出发时间、勾“每天都”、再改回原来
    try:
        c,pg,errs=ctx(); pg.goto(B+'/trip/qdn5/',wait_until='networkidle'); pg.wait_for_timeout(300)
        o=pg.evaluate("[...document.querySelectorAll('.day .st b')].map(b=>b.textContent).join(',')")
        pg.locator('#d2 .st').scroll_into_view_if_needed(); pg.locator('#d2 .st').click(); pg.wait_for_timeout(200); pg.locator('.stg button[data-v="10:30"]').click(); pg.wait_for_timeout(300)
        pg.locator('#d2 .st').click(); pg.wait_for_timeout(200); pg.locator('.allin').check(); pg.locator('.stg button[data-v="08:00"]').click(); pg.wait_for_timeout(300)
        a=pg.evaluate("[...document.querySelectorAll('.day .st b')].map(b=>b.textContent).join(',')")
        for k in range(1,6):
            if pg.locator(f'#d{k} .latewarn .reset').count(): pg.locator(f'#d{k} .latewarn .reset').click(); pg.wait_for_timeout(200)
        r=pg.evaluate("[...document.querySelectorAll('.day .st b')].map(b=>b.textContent).join(',')")
        rec('138 小吴 · 改两次出发时间、每天都、再恢复',r==o,f'原来 {o}；每天都 8 点后 {a}；逐天恢复后 {r}')
        rec('139 小吴 · 页面报错',not errs,'；'.join(errs) or '没有'); c.close()
    except Exception as ex: rec('小吴 · 卡住了',False,str(ex).split('\n')[0][:200])
    b.close()
print(json.dumps({'R':R},ensure_ascii=False,indent=1))
