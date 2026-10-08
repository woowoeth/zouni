// 第二十二组：三格对齐、收藏图标、加一天按位置、预约链接、真实酒店
const p=require('puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev); return pg; };
  const go=async(pg,u)=>{ await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(400); };
  { const pg=await fresh(); const res=[];
    for (const t of ['xa3','g318','sc5']) { await go(pg,'/trip/'+t+'/'); res.push(await pg.evaluate(()=>{ const c=[...document.querySelectorAll('.glance>div')]; const a=c.map(x=>[Math.round(x.children[0].getBoundingClientRect().top),getComputedStyle(x.children[0]).fontSize]); const s=c.map(x=>Math.round((x.querySelector('.dt')||x.querySelector('.pp')||x.querySelector('small')).getBoundingClientRect().top)); return {a,s,fit:c.every(x=>x.children[0].scrollWidth<=x.children[0].clientWidth+1)}; })); }
    const ok=res.every(r=>new Set(r.a.map(x=>x.join())).size===1&&new Set(r.s).size===1&&r.fit);
    R.push({u:'99 Jerry · 三格同字号同一行',ok,find:res.map(r=>r.a[0][1]+' 上沿 '+r.a[0][0]+' / 第二行 '+r.s[0]+(r.fit?'，放得下':'，放不下')).join(' ｜ ')}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/xa3/'); const a=await pg.evaluate(()=>{ const f=document.querySelector('.dock .fav'); return {icon:!!f.querySelector('svg.fi'),fill:getComputedStyle(f.querySelector('svg.fi path')).fill}; });
    await pg.evaluate(()=>document.querySelector('.dock .fav').click()); await sleep(200);
    const c=await pg.evaluate(()=>{ const f=document.querySelector('.dock .fav'); return {t:f.innerText,fill:getComputedStyle(f.querySelector('svg.fi path')).fill}; });
    R.push({u:'100 小林 · 收藏图标',ok:a.icon&&a.fill==='none'&&c.fill!=='none'&&/已收进/.test(c.t),find:`书签图标${a.icon?'有':'没有'}，没收时 ${a.fill}，收进后 ${c.fill}、按钮“${c.t}”`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/cd3/'); const cands=await pg.evaluate(()=>JSON.parse(document.getElementById('cands').textContent));
    await pg.evaluate(()=>{document.documentElement.style.scrollBehavior='auto';document.querySelector('.addday .add').scrollIntoView({block:'center'})}); await sleep(300); await pg.tap('.addday .add'); await sleep(300);
    const first=await pg.evaluate(()=>{ const bt=document.querySelector('.xd button[data-rid]'); return bt?bt.innerText.replace(/\n/g,' '):''; });
    await pg.evaluate(()=>document.querySelector('.xd button[data-rid]').click()); await sleep(1500);
    const order=await pg.evaluate(()=>[...document.querySelectorAll('.day')].map(d=>(d.classList.contains('xday')?'[加]':'')+d.querySelector('h2').childNodes[0].textContent.trim()));
    R.push({u:'101 阿杰 · 成都加一天',ok:cands.length>0&&cands.every(c=>c.km<=100)&&/\[加\]/.test(order[order.length-2]),find:`候选 ${cands.map(c=>c.title+' '+c.km+'km').join('、')}；第一个“${first}”；加完顺序 ${order.join(' → ')}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/bj4/'); const r=await pg.evaluate(()=>({tl:[...document.querySelectorAll('.r .s a.bkl')].map(a=>a.href),pre:[...document.querySelectorAll('.pre li a.bkl')].map(a=>a.href),how:[...document.querySelectorAll('.bkh')].map(x=>x.innerText)}));
    R.push({u:'102 张老师 · 北京预约网址',ok:r.tl.some(u=>/ticket\.dpm\.org\.cn/.test(u))&&r.pre.length>=1,find:`时间轴 ${r.tl.length} 个链接（${[...new Set(r.tl)].join('、')}）；出发前 ${r.pre.length} 个；没网址的写 ${[...new Set(r.how)].join('、')}`}); await pg.close(); }
  { const pg=await fresh(); await go(pg,'/trip/lsnmc4/'); const r=await pg.evaluate(()=>{ const c=document.querySelector('.stays'); return {names:[...c.querySelectorAll('b.tg')].map(b=>b.innerText),links:[...c.querySelectorAll('a.tl2')].map(a=>a.href),btn:c.querySelector('.bk .btn').href}; });
    R.push({u:'103 老王 · 拉萨住哪家',ok:r.names.length===3&&r.links.every(u=>/hoteldetail\/\d+\.html/.test(u))&&/hoteldetail/.test(r.btn),find:`${r.names.join(' ｜ ')}；预订 ${r.links[0]}`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
