const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const ctx=await b.createBrowserContext(); const R=[], errs=[];
  const open=async u=>{ const pg=await ctx.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/'); const a=await pg.evaluate(()=>({t:document.querySelector('.now .nt').innerText,n:document.querySelector('.now .ns').innerText,first:[...document.querySelectorAll('.now .items li:not([hidden]) h3')].slice(0,3).map(h=>h.innerText)}));
    await pg.evaluate(()=>{ const i=document.querySelector('.hdpk'); i.value='2027-01-10'; i.dispatchEvent(new Event('change')); }); await sleep(400);
    const z=await pg.evaluate(()=>({bar:document.querySelector('.hdt b').innerText,t:document.querySelector('.now .nt').innerText,n:document.querySelector('.now .ns').innerText,first:[...document.querySelectorAll('.now .items li:not([hidden])')].slice(0,4).map(li=>li.querySelector('h3').innerText+'（'+li.querySelector('.left').innerText+'）')}));
    R.push({u:'43 首页改成 1 月 10 日出发',ok:/1\/10/.test(z.bar)&&/1\/10 出发正好去/.test(z.t)&&z.first.length>0,find:`今天：${a.t}（${a.n}）${a.first.join('、')}｜改后：${z.bar}；${z.t}（${z.n}）${z.first.join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/xa3/'); const d=await pg.evaluate(()=>document.querySelector('.dt').innerText); R.push({u:'44 打开西安行程，用首页选的日期',ok:/1\/10/.test(d),find:d}); await pg.close(); }
  { const pg=await open('/trip/xz7/').catch(()=>null); if(pg) await pg.close();
    const p2=await open('/trip/kc4/'); const m=await p2.evaluate(()=>[...document.querySelectorAll('.mn li')].map(x=>x.innerText)); R.push({u:'45 南疆行程的当地讲究',ok:m.length>0,find:m.join(' / ')}); errs.push(...p2._e); await p2.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
