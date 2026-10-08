// 第十三组：站内日期面板、首页换日期封面跟着换
const p=require('puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true,hasTouch:true}); return pg; };
  { const pg=await fresh(); await pg.goto(B+'/trip/jz4/',{waitUntil:'networkidle0'}); await sleep(300);
    await pg.tap('.dtw'); await sleep(300);
    const r=await pg.evaluate(()=>({open:!!document.querySelector('.pk'),title:document.querySelector('.pk-h b')?.innerText,best:document.querySelectorAll('.pk-g .best').length,off:document.querySelectorAll('.pk-g .off').length,native:document.querySelector('input[type=date]')?'有':'没有'}));
    await pg.evaluate(()=>document.querySelector('.pk-n').click()); await sleep(150);
    const m=await pg.evaluate(()=>document.querySelector('.pk-m b').innerText);
    await pg.evaluate(()=>{ const bs=[...document.querySelectorAll('.pk-g button:not([disabled])')]; bs[3].click(); }); await sleep(300);
    const a=await pg.evaluate(()=>({open:!!document.querySelector('.pk'),dt:document.querySelector('.dt').innerText,h:document.querySelector('.day header small').innerText}));
    R.push({u:'57 九寨行程点“改”打开站内面板',ok:r.open&&r.native==='没有'&&!a.open&&/改/.test(a.dt),find:`面板“${r.title}”，绿色最好的日子 ${r.best} 个、过去不能选 ${r.off} 个，系统日期控件${r.native}；翻到 ${m}，点一天后面板关上，概览“${a.dt}”，第一天“${a.h}”`}); await pg.close(); }
  { const pg=await fresh(); await pg.goto(B+'/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(300); await pg.tap('.dtw'); await sleep(200);
    await pg.evaluate(()=>document.querySelector('.pk-q button[data-q="1"]').click()); await sleep(300);
    const a=await pg.evaluate(()=>({dt:document.querySelector('.dt').innerText,dock:document.querySelector('.dock b').innerText}));
    R.push({u:'58 一点“下周六”',ok:/出发/.test(a.dock),find:`概览 ${a.dt}；底栏 ${a.dock}`}); await pg.close(); }
  { const pg=await fresh(); await pg.goto(B+'/',{waitUntil:'networkidle0'}); await sleep(300);
    const c0=await pg.evaluate(()=>({t:document.querySelector('.cv h2').innerText,src:document.querySelector('.cover img').getAttribute('src')}));
    await pg.tap('.hdt'); await sleep(250);
    for (let k=0;k<3;k++){ await pg.evaluate(()=>document.querySelector('.pk-n').click()); await sleep(80); }
    await pg.evaluate(()=>{ const bs=[...document.querySelectorAll('.pk-g button:not([disabled])')]; bs[9].click(); }); await sleep(500);
    const c1=await pg.evaluate(()=>({bar:document.querySelector('.hdt b').innerText,t:document.querySelector('.cv h2').innerText,k:document.querySelector('.cv .kick').innerText,src:document.querySelector('.cover img').getAttribute('src'),chips:[...document.querySelectorAll('.cv .chips span')].map(x=>x.innerText).join(' / '),go:document.querySelector('.cv .go').getAttribute('href'),now:document.querySelector('.now .nt').innerText}));
    R.push({u:'59 首页换到三个月后，封面跟着换',ok:c1.t!==c0.t&&c1.src!==c0.src&&/出发正当季/.test(c1.k),find:`原封面“${c0.t}”→ ${c1.bar}：“${c1.t}”（${c1.k}；${c1.chips}；翻开 ${c1.go}）；列表标题“${c1.now}”`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
