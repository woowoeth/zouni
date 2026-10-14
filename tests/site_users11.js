// 第十一组：旅途中模式、没网提示
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const ctx=await b.createBrowserContext(); const R=[], errs=[];
  const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true});
  await pg.goto(B+'/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(300);
  const none=await pg.evaluate(()=>!!document.querySelector('.today'));
  // 把出发日改成今天
  await pg.evaluate(()=>{ const n=new Date(),i=document.querySelector('.dpk'); i.value=n.getFullYear()+'-'+('0'+(n.getMonth()+1)).slice(-2)+'-'+('0'+n.getDate()).slice(-2); i.dispatchEvent(new Event('change')); }); await sleep(400);
  const t=await pg.evaluate(()=>({bar:document.querySelector('.today')?.innerText.replace(/\n/g,' '),now:document.querySelector('.daynav a.now')?.innerText}));
  await pg.evaluate(()=>document.querySelector('.today').click()); await sleep(600);
  const fl=await pg.evaluate(()=>!!document.querySelector('.flash'));
  R.push({u:'49 今天出发：底部提示今天第几天、下一站',ok:!none&&!!t.bar&&/今天第 1 天/.test(t.bar)&&fl,find:`原来${none?'有':'没有'}提示；改成今天后：“${t.bar}”，天数条“${t.now}”；点了${fl?'跳到并闪了一下':'没反应'}`});
  await pg.setOfflineMode(true); await pg.evaluate(()=>window.dispatchEvent(new Event('offline'))); await sleep(300);
  const off=await pg.evaluate(()=>document.querySelector('.offline')?.innerText||'');
  await pg.setOfflineMode(false); await pg.evaluate(()=>window.dispatchEvent(new Event('online'))); await sleep(300);
  const on=await pg.evaluate(()=>!!document.querySelector('.offline'));
  R.push({u:'50 断网再联网',ok:/没有网络/.test(off)&&!on,find:`断网：“${off}”；联网后提示${on?'还在':'消失'}`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
