// 第二十四组：路线图放大缩小
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev);
  await pg.goto(B+'/trip/g318/',{waitUntil:'networkidle0'}); await sleep(400);
  await pg.evaluate(()=>document.querySelector('.hmap').click()); await sleep(300);
  const w0=await pg.evaluate(()=>Math.round(document.querySelector('.hmap-zoom svg').getBoundingClientRect().width));
  await pg.evaluate(()=>document.querySelector('.hz-p').click()); await sleep(200); const w1=await pg.evaluate(()=>Math.round(document.querySelector('.hmap-zoom svg').getBoundingClientRect().width));
  await pg.evaluate(()=>{ document.querySelector('.hz-m').click(); document.querySelector('.hz-m').click(); }); await sleep(200); const w2=await pg.evaluate(()=>({w:Math.round(document.querySelector('.hmap-zoom svg').getBoundingClientRect().width),dis:document.querySelector('.hz-m').disabled}));
  await pg.evaluate(()=>document.querySelector('.hz-x').click()); await sleep(200); const gone=await pg.evaluate(()=>!document.querySelector('.hmap-zoom'));
  R.push({u:'107 Lily · 路线图放大缩小',ok:w1>w0&&w2.w<w0&&w2.dis&&gone,find:`打开 ${w0} 宽，点＋ ${w1}，点两次－ ${w2.w}（－${w2.dis?'已到最小':'还能点'}），关上${gone?'了':'不了'}`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
