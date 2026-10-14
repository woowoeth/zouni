const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const open=async u=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300); return pg; };
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','可可西里'); await sleep(200); await pg.evaluate(()=>document.querySelector('[data-f="fit"]').click()); await sleep(200);
    const n=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText)); R.push({u:'23 搜“可可西里”',ok:n.includes('青海'),find:`找到：${n.join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await sleep(100); await pg.type('.flt input','南极洛'); await sleep(200); await pg.evaluate(()=>document.querySelector('[data-f="fit"]').click()); await sleep(200);
    const n=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden]) h3')].map(h=>h.innerText)); R.push({u:'24 搜“南极洛”',ok:n.includes('云南'),find:`找到：${n.join('、')}`}); await pg.close(); }
  { const pg=await open('/d/qinghai/'); const r=await pg.evaluate(()=>[...document.querySelectorAll('.niche li')].map(li=>li.querySelector('b').innerText+'【'+li.querySelector('.st').innerText+'】'+(li.querySelector('a:not(.ic)')?'→行程':'')));
    R.push({u:'25 青海页的小众',ok:r.length>=5,find:r.join('；')}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/d/yunnan/'); const r=await pg.evaluate(()=>[...document.querySelectorAll('.niche li')].map(li=>li.querySelector('b').innerText+'【'+li.querySelector('.st').innerText+'】'));
    R.push({u:'26 云南页的南极洛',ok:r.some(x=>/南极洛【暂停开放】/.test(x)),find:r.join('；')}); await pg.close(); }
  { const pg=await open('/trip/qzx4/'); const r=await pg.evaluate(()=>({pre:[...document.querySelectorAll('.pre li')].map(l=>l.innerText),rows:[...document.querySelectorAll('#d2 .r .m')].map(m=>m.innerText.replace(/\n/g,'')).slice(0,8),elev:[...document.querySelectorAll('#d2 .facts div')].map(d=>d.innerText.replace(/\n/g,':'))}));
    R.push({u:'27 青藏线可可西里第 2 天',ok:r.rows.some(x=>/索南达杰保护站/.test(x)),find:`出发前：${r.pre.join(' / ')}｜第 2 天：${r.rows.join(' / ')}｜${r.elev.join(' ')}`}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
