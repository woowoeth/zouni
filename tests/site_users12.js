// 第十二组：改日期点得动、返回回到上一页、随时能回首页
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true,hasTouch:true}); return pg; };
  const go=async(pg,u)=>{ await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); };
  const nav=async(pg,fn)=>{ await Promise.all([pg.waitForNavigation({waitUntil:'networkidle0'}).catch(()=>{}), pg.evaluate(fn)]); await sleep(300); return pg.url().replace(B,''); };
  { const pg=await fresh(); await go(pg,'/trip/xa3/');
    const r=await pg.evaluate(()=>{ const w=document.querySelector('.dtw').getBoundingClientRect(); return {w:Math.round(w.width), h:Math.round(w.height)}; });
    await pg.tap('.dtw'); await sleep(250); const op=await pg.evaluate(()=>!!document.querySelector('.pk'));
    R.push({u:'51 行程页点“改”',ok:op&&r.h>=36,find:`按钮 ${r.w}×${r.h}，点了${op?'弹出站内日期面板':'没反应'}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/');
    await pg.tap('.hdt'); await sleep(250); const r=await pg.evaluate(()=>!!document.querySelector('.pk'));
    R.push({u:'52 首页点日期条',ok:r,find:r?'弹出站内日期面板':'没反应'}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/'); const t=await nav(pg,()=>document.querySelector('.now .items li:not([hidden]) .open').click()); const back=await nav(pg,()=>document.querySelector('a.back').click());
    R.push({u:'53 首页→行程→返回',ok:t.startsWith('/trip/')&&back==='/',find:`${t} → 返回到 ${back}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/sz3/'); const back=await nav(pg,()=>document.querySelector('a.back').click());
    R.push({u:'54 直接打开行程再返回',ok:back==='/',find:`返回到 ${back}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/where/'); const d=await nav(pg,()=>document.querySelector('.card a.ch').click()); const t=await nav(pg,()=>document.querySelector('.trips a').click()); const b1=await nav(pg,()=>document.querySelector('a.back').click()); const b2=await nav(pg,()=>document.querySelector('a.back').click());
    R.push({u:'55 去哪儿→目的地→行程→返回→返回',ok:b1===d&&b2==='/where/',find:`${d} → ${t} → 返回 ${b1} → 返回 ${b2}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/d/yunnan/'); const back=await nav(pg,()=>document.querySelector('a.back').click());
    const pg2=await fresh(); await go(pg2,'/trip/ali8/'); const home=await nav(pg2,()=>document.querySelector('a.home').click()); const pg3=await fresh(); await go(pg3,'/d/xizang/'); const home3=await nav(pg3,()=>document.querySelector('.pagehead a.home').click());
    R.push({u:'56 随时回首页',ok:back==='/'&&home==='/'&&home3==='/',find:`目的地页直接返回 ${back}；行程页“走”方块 ${home}；目的地页“本期” ${home3}`}); await pg.close(); await pg2.close(); await pg3.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
