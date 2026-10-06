const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms)); const fs=require('fs');
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const pg=await b.newPage(); await pg.emulate(p.KnownDevices['iPhone 13']);
  await pg.goto('http://localhost:8765/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(600);
  // 分享图
  await pg.evaluate(()=>document.querySelector('.share').click()); await sleep(300);
  await pg.evaluate(()=>document.querySelector('.xd button[data-a="shot"]').click()); await sleep(2500);
  const src=await pg.evaluate(()=>{const im=document.querySelector('.shotv img');return im?im.src:''});
  if(src.startsWith('data:image')) fs.writeFileSync('/tmp/shot.png',Buffer.from(src.split(',')[1],'base64'));
  console.log('分享图', src?src.slice(0,30)+'… '+src.length:'没找到');
  // 打印成 PDF
  const pg2=await b.newPage(); await pg2.setViewport({width:800,height:1200}); await pg2.goto('http://localhost:8765/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(500);
  await pg2.pdf({path:'/tmp/trip.pdf',format:'A4',printBackground:true}); console.log('PDF', fs.statSync('/tmp/trip.pdf').size);
  await b.close(); })();
