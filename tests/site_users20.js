// 第二十组：长途和自驾
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev); return pg; };
  const go=async(pg,u)=>{ await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(350); };
  { const pg=await fresh(); await go(pg,'/'); const r=await pg.evaluate(()=>{ const s=document.getElementById('drive'); if(!s) return null; const lis=[...s.querySelectorAll('.items li')]; return {n:lis.length,vis:lis.filter(l=>!l.hidden).length,first:lis.slice(0,3).map(l=>l.querySelector('.k').innerText+' '+l.querySelector('h3').innerText),all:s.querySelector('.allbar')?.getAttribute('href')}; });
    R.push({u:'92 老王 · 首页找长途自驾',ok:!!r&&r.n>=40&&/全国环线/.test(r.first[0]),find:r?`共 ${r.n} 条（先显示 ${r.vis} 条）：${r.first.join(' ｜ ')}；底部 ${r.all}`:'没有这一栏'}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/where/?f=drive'); const r=await pg.evaluate(()=>({on:!!document.querySelector('[data-f="drive"].on'),cards:[...document.querySelectorAll('.card:not([hidden])')].map(c=>c.dataset.name),cnt:document.querySelector('.cnt').innerText}));
    R.push({u:'93 老王 · 按目的地看全部自驾',ok:r.on&&r.cards.length>=25,find:`“有自驾环线”${r.on?'已选上':'没选上'}；${r.cnt}：${r.cards.slice(0,10).join('、')}…`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/g318/'); const r=await pg.evaluate(()=>({g:document.querySelector('.glance').innerText.replace(/\n/g,' '),legs:[...document.querySelectorAll('.r.dep .s')].map(x=>x.innerText).filter(x=>/自驾约/.test(x)).length,days:document.querySelectorAll('.day').length,map:!!document.querySelector('.hmap svg')}));
    R.push({u:'94 小赵 · 川藏线 14 天',ok:/自驾/.test(r.g)&&r.legs>=10&&r.days===14&&r.map,find:`${r.g.slice(0,40)}…；路上写“自驾约”的 ${r.legs} 段；${r.days} 天；${r.map?'有':'没有'}路线图`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/d/sichuan/'); const r=await pg.evaluate(()=>[...document.querySelectorAll('.trips a')].filter(a=>/自驾/.test(a.innerText)).map(a=>a.querySelector('b').innerText));
    R.push({u:'95 小赵 · 四川页的自驾环线',ok:r.length>=2,find:r.join('、')}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/xbdh30/'); const r=await pg.evaluate(()=>({days:document.querySelectorAll('.day').length,nav:document.querySelectorAll('.daynav a').length,stays:[...document.querySelectorAll('.r.stay .m')].length}));
    R.push({u:'96 陈哥 · 西部大环线 30 天',ok:r.days===30&&r.nav===30&&r.stays===29,find:`${r.days} 天，天数条 ${r.nav} 格，每晚住处 ${r.stays} 个`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
