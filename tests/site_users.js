// 新网站：十个人在手机上用（本地预览）
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const ctx=await b.createBrowserContext();
  const open=async u=>{ const pg=await ctx.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); pg.on('console',m=>{ if(m.type()==='error') pg._e.push(m.text()); }); await pg.setViewport({width:390,height:844,isMobile:true}); await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(400); return pg; };
  const ov=pg=>pg.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  const small=pg=>pg.evaluate(()=>[...document.querySelectorAll('a,button')].filter(e=>{const r=e.getBoundingClientRect(); return r.width>0&&(r.width<32||r.height<32)&&e.offsetParent!==null&&!e.closest('.crumbs,.tags,.foot,.top');}).length);
  const R=[]; const errs=[];
  { const pg=await open('/'); const cover=await pg.evaluate(()=>document.querySelector('.cv h2')?.innerText); const n=await pg.evaluate(()=>document.querySelectorAll('.items li').length);
    R.push({u:'1 小林 · 打开首页',ok:!!cover&&n>5,find:`封面“${cover}”，这个月正好去的行程 ${n} 条；横向溢出 ${await ov(pg)}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/where/'); const before=await pg.evaluate(()=>document.querySelector('.card[data-best] .fit').innerText);
    await pg.evaluate(()=>document.querySelector('.mon button[data-m="1"]').click()); await sleep(200); const after=await pg.evaluate(()=>[...document.querySelectorAll('.card .fit')].filter(f=>f.innerText==='正好').length);
    R.push({u:'2 李老师 · 去哪儿换到 1 月',ok:after>0,find:`第一张卡原来“${before}”；换到 1 月后“正好”的 ${after} 个；溢出 ${await ov(pg)}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/d/beijing/'); const r=await pg.evaluate(()=>({m:document.querySelectorAll('.months li').length,on:document.querySelectorAll('.months li.on').length,q:document.querySelectorAll('.qual li').length,t:document.querySelectorAll('.trips a').length}));
    R.push({u:'3 张阿姨 · 看北京什么时候去',ok:r.m===12&&r.q>0,find:`12 个月气温 ${r.m} 格（标出最好的 ${r.on} 个月），5A 和世界遗产 ${r.q} 处，排好的行程 ${r.t} 条`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/jz4/'); const p0=await pg.evaluate(()=>document.querySelector('.price').innerText); await pg.evaluate(()=>document.querySelector('.pp').click()); await sleep(100);
    await pg.evaluate(()=>{ const x=document.querySelector('.ppl button[data-d="1"]'); x.click(); x.click(); }); await sleep(100); const p4=await pg.evaluate(()=>document.querySelector('.price').innerText);
    R.push({u:'4 Lily · 九寨 4 个人',ok:p0!==p4,find:`2 人每人 ${p0} → 4 人每人 ${p4}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/xa3/'); const r=await pg.evaluate(()=>({sun:[...document.querySelectorAll('.sun')].slice(0,2).map(s=>s.innerText),rows:document.querySelectorAll('.r').length,ic:document.querySelectorAll('.r .ic').length}));
    R.push({u:'5 阿May · 西安的日出日落',ok:/\d\d:\d\d/.test(r.sun[0]),find:`第一天日出 ${r.sun[0]}、日落 ${r.sun[1]}；时间轴 ${r.rows} 行，地图和点评图标 ${r.ic} 个；过小的可点区域 ${await small(pg)}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/#trip=xj10'); await sleep(800); const u=pg.url();
    R.push({u:'6 老用户 · 用老链接 #trip=xj10',ok:/\/trip\/xj10\//.test(u),find:`跳到 ${u.replace(B,'')}`}); await pg.close(); }
  { const pg=await open('/trip/kansai4/'); const g=await pg.evaluate(()=>[...document.querySelectorAll('.r .ic')][0]?.href||'');
    R.push({u:'7 Jerry · 大阪行程的地图',ok:/google/.test(g),find:`地点图标打开 ${g.slice(0,40)}…`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/trip/hs2/'); const r=await pg.evaluate(()=>({crumb:[...document.querySelectorAll('script[type="application/ld+json"]')].map(s=>s.textContent).find(t=>/BreadcrumbList/.test(t))?.match(/"name": ?"[^"]+"/g)?.map(x=>x.split('"')[3]).join(' › '),pre:document.querySelector('.pre')?.innerText.split('\n').length}));
    R.push({u:'8 小周 · 黄山两天',ok:!!r.crumb,find:`面包屑“${r.crumb}”；出发前 ${r.pre} 行`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('/no-such-page/'); const t=await pg.evaluate(()=>document.querySelector('h1')?.innerText);
    R.push({u:'9 走错路的人',ok:/没找到/.test(t||''),find:`看到“${t}”和去“去哪儿”的按钮`}); await pg.close(); }
  { let o=0, s=0; for(const u of ['/','/where/','/d/sichuan/','/trip/sc5/','/trip/cd3/','/trip/xj10/','/d/japan/']){ const pg=await open(u); if(await ov(pg)) o++; s+=await small(pg); errs.push(...pg._e); await pg.close(); }
    R.push({u:'10 体检 · 7 个典型页面',ok:o===0&&s===0,find:`横向溢出 ${o} 页，过小可点区域 ${s} 个`}); }
  console.log(JSON.stringify({R,errs:[...new Set(errs)].slice(0,5)},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
