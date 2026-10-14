// 第 5 轮：十个人试点评入口——认不认得出、点不点得中、去的对不对
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const audit=pg=>pg.evaluate(()=>{ const L=[...document.querySelectorAll('a')].filter(a=>/dianping\.com/.test(a.href));
    const bad=[], small=[], out=[], kws=[];
    for(const a of L){ const r=a.getBoundingClientRect(); if(r.width<32||r.height<32) small.push(a.getAttribute('aria-label')); if(r.right>390.5) out.push(a.getAttribute('aria-label'));
      const kw=decodeURIComponent((a.href.split('keyword=')[1]||'')); kws.push(kw); if(!kw||/提车|放行李|回住处|还车|出发|随意/.test(kw)) bad.push(kw); }
    return {n:L.length, icon:L.filter(a=>a.querySelector('svg')).length, small, out, bad, sample:kws.slice(0,4)}; });
  const R=[], errs=[];
  for (const f of ['Route.dc.html#cd3','Route.dc.html#jz4','Route.dc.html#kansai4','Route.dc.html#hk2','Plan.dc.html','Today.dc.html','Atlas.dc.html']) {
    const pg=await open(f); const a=await audit(pg); R.push({page:f, ...a}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Route.dc.html#jz4'); const kb=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/携程|榜第/.test(t)).slice(0,2)); R.push({page:'口碑行（九寨）', sample:kb}); await pg.close(); }
  { const pg=await open('Plan.dc.html'); const stay=await pg.evaluate(()=>[...document.querySelectorAll('a')].filter(a=>a.innerText.includes('看点评')).map(a=>decodeURIComponent(a.href.split('keyword=')[1]))); R.push({page:'专题住宿卡', sample:stay.slice(0,3)}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
