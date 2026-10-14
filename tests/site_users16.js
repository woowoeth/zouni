// 第十六组：首页搜索、要预约
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true,hasTouch:true});
  await pg.goto(B+'/',{waitUntil:'networkidle0'}); await sleep(300);
  await pg.type('.hsearch input','兵马俑'); await Promise.all([pg.waitForNavigation({waitUntil:'networkidle0'}).catch(()=>{}), pg.evaluate(()=>document.querySelector('.hsearch button').click())]); await sleep(500);
  const r=await pg.evaluate(()=>({u:location.pathname+location.search,q:document.querySelector('.flt input').value,open:!document.querySelector('.flt').hidden,cards:[...document.querySelectorAll('.card:not([hidden])')].map(c=>c.dataset.name+'（'+(c.querySelector('.hit')?.innerText||'')+'）')}));
  R.push({u:'68 首页搜“兵马俑”',ok:/where/.test(r.u)&&r.q==='兵马俑'&&r.open&&r.cards.some(c=>/陕西/.test(c)),find:`跳到 ${decodeURIComponent(r.u)}，筛选${r.open?'已打开':'没打开'}，搜索框“${r.q}”，结果：${r.cards.join('、')}`});
  await pg.goto(B+'/trip/bj4/',{waitUntil:'networkidle0'}); await sleep(300);
  const bk=await pg.evaluate(()=>({tags:[...document.querySelectorAll('.r .s em.bkn')].map(x=>x.closest('.rb').querySelector('.m').childNodes[0].textContent.trim()),pre:[...document.querySelectorAll('.pre label span')].map(x=>x.innerText)}));
  R.push({u:'69 北京行程的“要预约”',ok:bk.tags.length>=2&&bk.pre.some(x=>/预约/.test(x)),find:`标了：${bk.tags.join('、')}；出发前：${bk.pre.join(' / ')}`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
