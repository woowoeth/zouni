// 第三轮：从哪出发、收藏、最近看过、天数条、分享
const p=require('puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
  const ctx=await b.createBrowserContext(); const R=[], errs=[];
  const open=async u=>{ const pg=await ctx.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.select('.flt select.org','上海'); await sleep(300);
    const r=await pg.evaluate(()=>{ const c=[...document.querySelectorAll('.card:not([hidden])')]; return {first:c.slice(0,3).map(x=>x.querySelector('h3').innerText+'('+x.querySelector('.dist').innerText+')'), near:!document.querySelector('[data-f="near"]').hidden}; });
    await pg.evaluate(()=>document.querySelector('[data-f="near"]').click()); await sleep(200);
    const nn=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText));
    R.push({u:'17 王先生 · 从上海出发、只看 500 公里内',ok:nn.length>0&&nn.length<15,find:`华东排前面：${r.first.join('、')}；点“500 公里内”剩：${nn.join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); const v=await pg.evaluate(()=>document.querySelector('.flt select.org').value);
    R.push({u:'18 王先生 · 再打开去哪儿',ok:v==='上海',find:`出发地记住了：${v||'没记住'}`}); await pg.close(); }
  { const pg=await open('/trip/xa3/'); await pg.evaluate(()=>document.querySelector('.fav').click()); await sleep(200); const t=await pg.evaluate(()=>document.querySelector('.fav').innerText); await pg.close();
    const h=await open('/'); await h.evaluate(()=>document.querySelector('.minebtn').click()); await sleep(300); const fav=await h.evaluate(()=>['显示:'+[...document.querySelectorAll('.pk a.mr b')].map(b=>b.innerText).join('/')]);
    R.push({u:'19 小林 · 收藏西安，回首页找',ok:/已收进/.test(t)&&fav[0].includes('西安'),find:`按钮变“${t}”；首页：${fav.join('；')}`}); errs.push(...h._e); await h.close(); }
  { const pg=await open('/trip/xj10/'); const nav=await pg.evaluate(()=>document.querySelectorAll('.daynav a').length);
    await pg.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.getElementById('d6').scrollIntoView();}); await sleep(600); const on=await pg.evaluate(()=>{ const a=document.querySelector('.daynav a.on'); return a?a.innerText:''; });
    const top=await pg.evaluate(()=>Math.round(document.querySelector('.daynav').getBoundingClientRect().top));
    R.push({u:'20 老周 · 十天行程跳到第 6 天',ok:nav===10&&on==='6',find:`天数条 ${nav} 格，吸在顶部 ${top}px，当前高亮第 ${on} 天`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/hs2/'); const nav=await pg.evaluate(()=>document.querySelectorAll('.daynav').length);
    R.push({u:'21 小周 · 两天的行程',ok:nav===1,find:`两天的行程${nav?'有':'没有'}天数条（照设计稿，几天都放）`}); await pg.close(); }
  { const pg=await open('/trip/gz3/'); await pg.evaluate(()=>{ navigator.share=undefined; navigator.clipboard={writeText:async()=>{}}; }); await pg.evaluate(()=>{document.querySelector('.share').click();document.querySelector('.xd button[data-a="link"]').click();}); await sleep(300);
    const t=await pg.evaluate(()=>{ const x=document.querySelector('.toast'); return x?x.innerText:''; });
    R.push({u:'22 Lily · 分享广州行程给朋友',ok:/复制/.test(t),find:`提示“${t}”（手机上会弹系统分享）`}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
