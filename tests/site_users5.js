const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const ctx=await b.createBrowserContext(); const R=[], errs=[];
  const open=async u=>{ const pg=await ctx.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','冰川'); await sleep(200); await pg.evaluate(()=>document.querySelector('[data-f="fit"]').click()); await sleep(200);
    const r=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden])')].slice(0,4).map(c=>c.querySelector('h3').innerText+'：'+c.querySelector('.hit').innerText));
    R.push({u:'28 搜“冰川”看命中了什么',ok:r.length>0&&r.every(x=>/有 /.test(x)),find:r.join('；')}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await pg.evaluate(()=>document.querySelector('[data-f="fit"]').click()); await pg.evaluate(()=>document.querySelector('[data-f="niche"]').click()); await sleep(200);
    const r=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText)); R.push({u:'29 只看有小众的',ok:r.length>0&&r.length<15,find:r.join('、')}); await pg.close(); }
  { const pg=await open('/trip/zf4/'); await pg.evaluate(()=>document.querySelector('.pre input').click()); await sleep(150); await pg.close();
    const p2=await open('/trip/zf4/'); const c=await p2.evaluate(()=>[...document.querySelectorAll('.pre input')].map(x=>x.checked));
    R.push({u:'30 珠峰：办了边防证打个勾',ok:c[0]===true,find:`再打开后：${c.map(x=>x?'☑':'☐').join(' ')}`}); errs.push(...p2._e); await p2.close(); }
  { const pg=await open('/'); const r=await pg.evaluate(()=>{ return [...document.querySelectorAll('.now .items li')].filter(li=>li.querySelector('.k')?.innerText==='小众').map(li=>li.querySelector('h3').innerText); });
    R.push({u:'31 首页里的小众行程',ok:r.length>=5,find:r.join('、')}); await pg.close(); }
  { const pg=await open('/d/xizang/'); const r=await pg.evaluate(()=>[...document.querySelectorAll('.niche li')].map(li=>li.querySelector('b').innerText+'【'+li.querySelector('.st').innerText+'】'));
    R.push({u:'32 西藏页的小众',ok:r.length>=3,find:r.join('；')}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
