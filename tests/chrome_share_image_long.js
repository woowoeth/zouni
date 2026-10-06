const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms)); const fs=require('fs');
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const pg=await b.newPage(); await pg.emulate(p.KnownDevices['iPhone 13']);
  await pg.goto('http://localhost:8765/trip/g318/',{waitUntil:'networkidle0'}); await sleep(500);
  await pg.evaluate(()=>{const i=document.querySelector('.dpk');i.value='2026-11-03';i.dispatchEvent(new Event('change'))}); await sleep(200);
  await pg.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('#d3 .st').click()}); await sleep(200); await pg.evaluate(()=>document.querySelector('.stg button[data-v="10:00"]').click()); await sleep(200);
  await pg.evaluate(()=>document.querySelector('.share').click()); await sleep(300); await pg.evaluate(()=>document.querySelector('.xd button[data-a="shot"]').click()); await sleep(3000);
  const src=await pg.evaluate(()=>{const im=document.querySelector('.shotv img');return im?im.src:''}); if(src) fs.writeFileSync('/tmp/shot2.png',Buffer.from(src.split(',')[1],'base64'));
  console.log(src?'ok':'没有'); await b.close(); })();
