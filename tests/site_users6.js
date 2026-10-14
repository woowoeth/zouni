const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const open=async u=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/trip/ali8/'); await pg.evaluate(()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); }); await pg.evaluate(()=>document.querySelector('.share').click()); await sleep(200); await pg.evaluate(()=>document.querySelector('.xd button[data-a="copy"]').click()); await sleep(300);
    const r=await pg.evaluate(()=>({t:window.__c, toast:(document.querySelector('.toast')||{}).innerText}));
    const lines=r.t.split('\n'); R.push({u:'33 复制阿里行程发群里',ok:lines.length>20&&/冈仁波齐/.test(r.t),find:`提示“${r.toast}”；共 ${lines.length} 行，前几行：${lines.slice(0,6).join(' ⏎ ')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/d/yunnan/'); const r=await pg.evaluate(()=>[...document.querySelectorAll('.niche li')].map(li=>li.querySelector('b').innerText+'【'+li.querySelector('.st').innerText+'】'));
    R.push({u:'34 云南页的小众',ok:r.some(x=>/丙中洛/.test(x))&&r.some(x=>/独龙江【有条件】/.test(x)),find:r.join('；')}); await pg.close(); }
  { const pg=await open('/trip/ali8/'); const r=await pg.evaluate(()=>({nav:document.querySelectorAll('.daynav a').length,pre:[...document.querySelectorAll('.pre li')].map(l=>l.innerText),e:[...document.querySelectorAll('.day .facts')].map(f=>(f.innerText.match(/海拔\s*([\d,]+)/)||[])[1]).join('/')}));
    R.push({u:'35 阿里南线 8 天',ok:r.nav===8,find:`天数条 ${r.nav} 格；每天海拔 ${r.e}；出发前：${r.pre.join(' / ')}`}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
