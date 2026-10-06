// 第二十三组：价格短写、加一天接得上、新地图
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev); return pg; };
  { const pg=await fresh(); await pg.goto(B+'/trip/g318/',{waitUntil:'networkidle0'}); await sleep(400);
    const r=await pg.evaluate(()=>({p:document.querySelector('.glance .price').innerText,fs:getComputedStyle(document.querySelector('.glance .price')).fontSize,dock:document.querySelector('.dock small').innerText}));
    await pg.evaluate(()=>document.querySelector('.pp')&&document.querySelector('.pp').click()); await sleep(200);
    const r2=await pg.evaluate(()=>{ const pl=[...document.querySelectorAll('.ppl button,.pplus,[data-d="1"]')][0]; if(pl) pl.click(); return document.querySelector('.glance .price').innerText; });
    R.push({u:'104 Jerry · 价格短写',ok:/^¥[\d.]+K–[\d.]+K$/.test(r.p)&&r.fs==='20px',find:`概览 ${r.p}（${r.fs}）；底栏 ${r.dock}；改人数后 ${r2}`}); await pg.close(); }
  { const pg=await fresh(); await pg.goto(B+'/trip/cd3/',{waitUntil:'networkidle0'}); await sleep(300);
    await pg.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('.addday .add').scrollIntoView({block:'center'})}); await sleep(300); await pg.tap('.addday .add'); await sleep(300);
    await pg.evaluate(()=>document.querySelector('.xd button[data-rid]').click()); await sleep(1500);
    const x=await pg.evaluate(()=>{ const s=document.querySelector('.xday'); const rows=[...s.querySelectorAll('.tl .r')].map(r=>r.innerText.replace(/\n/g,' ')); return {first:rows[0],last2:rows.slice(-2),stays:!!s.querySelector('.stays')}; });
    R.push({u:'105 阿杰 · 成都加一天接得上',ok:/从.+出发/.test(x.first)&&/回/.test(x.last2[0])&&/住 · /.test(x.last2[1])&&!x.stays,find:`开头：${x.first}；结尾：${x.last2.join(' ｜ ')}；${x.stays?'还带着那天自己的住宿卡':'去掉了那天自己的住宿卡'}`}); await pg.close(); }
  { const pg=await fresh(); const out=[];
    for (const u of ['/trip/g318/','/trip/hainl7/','/d/sichuan/']) { await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(300);
      out.push(await pg.evaluate(u=>{ const s=document.querySelector('.hmap svg'); return u+'：底图 '+s.querySelectorAll('path[stroke="#cfc6b3"]').length+' 块，边框 '+([...s.querySelectorAll('rect')].some(r=>r.getAttribute('stroke')&&+r.getAttribute('width')>=300)?'有':'没有')+'，比例尺 '+(/公里/.test(s.textContent)?'有':'没有'); },u)); }
    R.push({u:'106 Lily · 新地图',ok:out.every(x=>/底图 [1-9]/.test(x)&&/边框 没有/.test(x)),find:out.join(' ｜ ')}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
