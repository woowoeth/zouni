const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const open=async u=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/where/'); const c0=await pg.evaluate(()=>document.querySelector('.cnt').innerText); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.select('.bud','2000'); await sleep(250);
    const r=await pg.evaluate(()=>({c:document.querySelector('.cnt').innerText,bad:[...document.querySelectorAll('.card:not([hidden])')].filter(c=>!(c.dataset.plo!==''&&+c.dataset.plo<=2000)).length,names:[...document.querySelectorAll('.card:not([hidden]) h3')].slice(0,8).map(h=>h.innerText)}));
    R.push({u:'36 学生党 · 每人 2,000 以内',ok:r.bad===0,find:`${c0} → ${r.c}：${r.names.join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/kc4/'); const r=await pg.evaluate(()=>({price:document.querySelector('.price').innerText,sub:document.querySelector('.price').nextElementSibling.innerText}));
    R.push({u:'37 看南疆库车的价格',ok:/约 ¥/.test(r.price),find:`${r.price} · ${r.sub}`}); errs.push(...pg._e); await pg.close(); }
  { let o=0; for (const u of ['/trip/ali8/','/trip/kc4/','/d/xinjiang/','/trip/mssl2/','/trip/slmh2/']) { const pg=await open(u); if(await pg.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1)) o++; errs.push(...pg._e); await pg.close(); }
    R.push({u:'38 新页面体检',ok:o===0,find:`横向溢出 ${o} 页`}); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
