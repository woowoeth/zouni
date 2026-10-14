// 第八组：改出发日期、标记已订、首页“什么时候去都行”
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const ctx=await b.createBrowserContext(); const R=[], errs=[];
  const open=async u=>{ const pg=await ctx.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/trip/xa3/'); const before=await pg.evaluate(()=>({g:document.querySelector('.dt').innerText,h:document.querySelector('.day header small').innerText,s:document.querySelector('.sun').innerText,dock:document.querySelector('.dock b').innerText}));
    await pg.evaluate(()=>{ const i=document.querySelector('.dpk'); i.value='2026-12-24'; i.dispatchEvent(new Event('change')); }); await sleep(300);
    const after=await pg.evaluate(()=>({g:document.querySelector('.dt').innerText,h:document.querySelector('.day header small').innerText,s:document.querySelector('.sun').innerText,dock:document.querySelector('.dock b').innerText,cl:document.querySelector('.day .cl').innerText,ov:document.querySelector('.overview i').innerText}));
    R.push({u:'39 改成平安夜出发',ok:/12\/24/.test(after.g)&&/12\/24 周四/.test(after.h)&&after.s!==before.s&&/12\/24 出发/.test(after.dock),find:`概览 ${before.g}→${after.g}；第一天 ${before.h}→${after.h}；日出 ${before.s}→${after.s}；底栏 ${after.dock}；${after.cl||'（没有 12 月气温）'}；怎么排 ${after.ov}`}); errs.push(...pg._e); await pg.close();
    const p2=await open('/trip/xa3/'); const kept=await p2.evaluate(()=>document.querySelector('.dt').innerText); R.push({u:'40 再打开还是平安夜',ok:/12\/24/.test(kept),find:kept}); await p2.close(); }
  { const pg=await open('/trip/sz3/'); const t0=await pg.evaluate(()=>{ const b=document.querySelector('.stays .mk'); b.click(); return b.innerText; }); await pg.close();
    const p2=await open('/trip/sz3/'); const t1=await p2.evaluate(()=>document.querySelector('.stays .mk').innerText); R.push({u:'41 苏州酒店标记已订',ok:/已订/.test(t0)&&/已订/.test(t1),find:`点完 ${t0}，再打开 ${t1}`}); errs.push(...p2._e); await p2.close(); }
  { const pg=await open('/'); const r=await pg.evaluate(()=>{ const h=[...document.querySelectorAll('h2')].find(x=>/什么时候去都行/.test(x.innerText)); return h?[...h.parentElement.querySelectorAll('.items h3')].map(x=>x.innerText):[]; });
    R.push({u:'42 首页“什么时候去都行”',ok:r.length>=3,find:r.join('、')}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
