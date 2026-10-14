// 第十七组：分享图、地图看
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true,hasTouch:true});
  await pg.goto(B+'/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(400);
  await pg.evaluate(()=>document.querySelector('.share').click()); await sleep(200); await pg.evaluate(()=>document.querySelector('.xd button[data-a="shot"]').click()); await sleep(2500);
  const s=await pg.evaluate(()=>{ const i=document.querySelector('.shotv img'); return i?{len:i.src.length,w:i.naturalWidth,h:i.naturalHeight}:null; });
  if(s){ const data=await pg.evaluate(()=>document.querySelector('.shotv img').src); require('fs').writeFileSync('/tmp/share_xa3.png',Buffer.from(data.split(',')[1],'base64')); }
  R.push({u:'70 西安生成分享图',ok:!!s&&s.w===1080&&s.h===1500&&s.len>100000,find:s?`图 ${s.w}×${s.h}，${Math.round(s.len/1024)} KB`:'没出图'});
  await pg.goto(B+'/where/',{waitUntil:'networkidle0'}); await sleep(400);
  await pg.evaluate(()=>document.querySelector('.mtog').click()); await sleep(400);
  const m=await pg.evaluate(()=>({names:document.querySelectorAll('.wmap a text').length,dots:document.querySelectorAll('.wmap circle').length,list:getComputedStyle(document.querySelector('#domestic')).display}));
  await pg.evaluate(()=>document.querySelector('.mon button[data-m="1"]').click()); await sleep(400);
  const m2=await pg.evaluate(()=>({dots:document.querySelectorAll('.wmap circle').length,first:[...document.querySelectorAll('.wmap a text')].slice(0,6).map(t=>t.textContent)}));
  R.push({u:'71 去哪儿地图看',ok:m.dots>10&&m.list==='none'&&m2.dots>0,find:`10 月 ${m.dots} 个点、标名字 ${m.names} 个，列表${m.list==='none'?'收起':'还在'}；换到 1 月后 ${m2.dots} 个点：${m2.first.join('、')}`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
