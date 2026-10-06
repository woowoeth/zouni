const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const pg=await b.newPage(); await pg.emulate(p.KnownDevices['iPhone 13']); const errs=[]; pg.on('pageerror',e=>errs.push(e.message));
  await pg.goto('http://localhost:8765/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(400); await pg.tap('.tvbtn'); await sleep(300);
  const h=()=>pg.evaluate(()=>document.querySelector('.tvb h2').innerText);
  const swipe=dx=>pg.evaluate(dx=>{const m=document.querySelector('.tv'),el=m.querySelector('.tvl')||m;const T=(x,y)=>new Touch({identifier:1,target:el,clientX:x,clientY:y});
    el.dispatchEvent(new TouchEvent('touchstart',{bubbles:true,touches:[T(200,400)],changedTouches:[T(200,400)]}));el.dispatchEvent(new TouchEvent('touchend',{bubbles:true,touches:[],changedTouches:[T(200+dx,405)]}))},dx);
  const out=[await h()]; await swipe(-120); await sleep(200); out.push(await h()); await swipe(-120); await sleep(200); out.push(await h()); await swipe(-120); await sleep(200); out.push(await h()+'（已经是最后一天）'); await swipe(120); await sleep(200); out.push(await h());
  await swipe(-30); await sleep(200); out.push(await h()+'（滑得短不算）');
  console.log(JSON.stringify({out,errs})); await b.close(); })();
