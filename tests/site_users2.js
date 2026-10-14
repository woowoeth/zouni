// 线上第二轮：搜索和筛选
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
  const open=async u=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  const cnt=pg=>pg.evaluate(()=>document.querySelector('.cnt').innerText);
  const R=[], errs=[];
  { const pg=await open('/where/'); const c0=await cnt(pg);
    await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','兵马俑'); await sleep(200); const c1=await cnt(pg); const names=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText));
    R.push({u:'11 小雨 · 搜“兵马俑”',ok:names.includes('陕西'),find:`默认${c0}；搜后${c1}：${names.join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','婺源'); await sleep(200); const names=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText));
    R.push({u:'12 王先生 · 搜“婺源”',ok:names.includes('江西'),find:`找到：${names.join('、')}`}); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>{document.querySelector('.ftog').click();document.querySelector('[data-f="d1"]').click();}); await sleep(200); const c=await cnt(pg);
    R.push({u:'13 小周 · 只看 2–3 天',ok:/符合的 \d+/.test(c),find:c}); await pg.close(); }
  { const pg=await open('/where/'); const c0=await cnt(pg); await pg.evaluate(()=>{document.querySelector('.ftog').click();document.querySelector('[data-f="low"]').click();}); await sleep(200); const c1=await cnt(pg);
    const tib=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].some(h=>/西藏|青海/.test(h.innerText)));
    R.push({u:'14 张阿姨 · 避开高原',ok:!tib,find:`${c0} → ${c1}；西藏、青海${tib?'还在':'已去掉'}`}); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>{document.querySelector('.ftog').click();document.querySelector('[data-f="fit"]').click();}); await sleep(150); const c=await cnt(pg);
    await pg.evaluate(()=>document.querySelector('.mon button[data-m="7"]').click()); await sleep(200); const c7=await cnt(pg);
    R.push({u:'15 李老师 · 看全部，再换到 7 月',ok:true,find:`看全部：${c}；切到 7 月后：${c7}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','zzzz'); await sleep(200); const c=await cnt(pg);
    R.push({u:'16 打错字',ok:/没有符合/.test(c),find:c}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
