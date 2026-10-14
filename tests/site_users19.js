// 第十九组：又找十位用户（iPhone 13 模拟）
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev); return pg; };
  const go=async(pg,u)=>{ await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(350); };
  const nav=async(pg,fn)=>{ await Promise.all([pg.waitForNavigation({waitUntil:'networkidle0'}).catch(()=>{}), pg.evaluate(fn)]); await sleep(350); return pg.url().replace(B,''); };
  // 1 北海道每晚住处
  { const pg=await fresh(); await go(pg,'/trip/hkd5/'); const st=await pg.evaluate(()=>[...document.querySelectorAll('.r.stay .m')].map(m=>m.childNodes[0].textContent.replace('住 · ','').trim()));
    const back=await pg.evaluate(()=>{ const d2=document.getElementById('d2'); const r=[...d2.querySelectorAll('.r.dep')].pop(); return r?r.innerText.replace(/\n/g,' '):''; });
    R.push({u:'82 小野 · 北海道每晚住哪',ok:st.join('/')==='札幌/札幌/旭川/旭川',find:`每晚：${st.join(' / ')}；小樽那天回住处：${back}`}); await pg.close(); }
  // 2 九寨标记已订后刷新
  { const pg=await fresh(); await go(pg,'/trip/jz4/'); await pg.evaluate(()=>document.querySelector('.stays .mk').click()); await sleep(200); await pg.reload({waitUntil:'networkidle0'}); await sleep(300);
    const t=await pg.evaluate(()=>document.querySelector('.stays .mk').innerText); R.push({u:'83 老孙 · 九寨酒店标记已订再打开',ok:/已订/.test(t),find:t}); await pg.close(); }
  // 3 首页搜喀纳斯 → 新疆 → 线路分布图 → 行程
  { const pg=await fresh(); await go(pg,'/'); await pg.type('.hsearch input','喀纳斯'); const w=await nav(pg,()=>document.querySelector('.hsearch button').click());
    const c=await pg.evaluate(()=>[...document.querySelectorAll('.card:not([hidden])')].map(x=>x.dataset.name));
    const d=await nav(pg,()=>{ const card=[...document.querySelectorAll('.card:not([hidden])')].find(x=>x.dataset.name==='新疆'); card.querySelector('a.ch').click(); });
    const t=await nav(pg,()=>document.querySelector('.dmap a').dispatchEvent(new MouseEvent('click',{bubbles:true})));
    R.push({u:'84 阿杰 · 搜喀纳斯一路点进行程',ok:c.includes('新疆')&&d==='/d/xinjiang/'&&t.startsWith('/trip/'),find:`搜到 ${c.join('、')} → ${d} → 分布图点进 ${t}`}); await pg.close(); }
  // 4 去哪儿亚洲地图点日本
  { const pg=await fresh(); await go(pg,'/where/'); await pg.evaluate(()=>{ document.querySelector('.tabs button[data-t="asia"]').click(); document.querySelector('.mtog').click(); }); await sleep(400);
    const names=await pg.evaluate(()=>[...document.querySelectorAll('.wmap a text')].map(t=>t.textContent));
    const j=names.includes('日本')?await nav(pg,()=>{ const a=[...document.querySelectorAll('.wmap a')].find(x=>x.textContent==='日本'); a.dispatchEvent(new MouseEvent('click',{bubbles:true})); }):'';
    R.push({u:'85 Lily · 亚洲地图点日本',ok:j==='/d/japan/',find:`亚洲地图标出 ${names.length} 个：${names.slice(0,8).join('、')}…；点日本进 ${j||'（没标出日本）'}`}); await pg.close(); }
  // 5 点天数条第 3 天，标题不被吸顶条挡住
  { const pg=await fresh(); await go(pg,'/trip/xj10/'); await pg.evaluate(()=>{ document.documentElement.style.scrollBehavior='auto'; document.querySelectorAll('.daynav a')[2].click(); }); await sleep(500);
    const r=await pg.evaluate(()=>{ const h=document.querySelector('#d3 header').getBoundingClientRect(); const n=document.querySelector('.daynav').getBoundingClientRect(); return {h:Math.round(h.top),nav:Math.round(n.bottom)}; });
    R.push({u:'86 老周 · 北疆点天数条第 3 天',ok:r.h>=r.nav,find:`第三天标题在 ${r.h}px，吸顶条底边 ${r.nav}px`}); await pg.close(); }
  // 6 曼谷地图图标是谷歌地图
  { const pg=await fresh(); await go(pg,'/trip/bkk3/'); const r=await pg.evaluate(()=>{ const a=document.querySelector('.r .ic.map'); return {h:a?a.href:'',ios:a&&a.dataset.ios?1:0}; });
    R.push({u:'87 小美 · 曼谷点地图图标',ok:/google\.com\/maps/.test(r.h)&&!r.ios,find:`${r.h.slice(0,70)}（${r.ios?'会调高德':'不调高德'}）`}); await pg.close(); }
  // 7 生成分享图
  { const pg=await fresh(); await go(pg,'/trip/hkd5/'); await pg.tap('.share'); await sleep(300); await pg.evaluate(()=>document.querySelector('.xd button[data-a="shot"]').click()); await sleep(2500);
    const s=await pg.evaluate(()=>{ const i=document.querySelector('.shotv img'); return i?[i.naturalWidth,i.naturalHeight]:null; }); R.push({u:'88 陈哥 · 北海道生成分享图',ok:!!s&&s[0]===1080,find:s?s.join('×'):'没出图'}); await pg.close(); }
  // 8 云南页本月标、点第一条线路
  { const pg=await fresh(); await go(pg,'/d/yunnan/'); const r=await pg.evaluate(()=>({now:document.querySelector('.months li.now b')?.innerText,first:document.querySelector('.trips a b')?.innerText}));
    const t=await nav(pg,()=>document.querySelector('.trips a').click()); R.push({u:'89 何姐 · 云南页',ok:!!r.now&&t.startsWith('/trip/'),find:`本月格子“${r.now}”；第一条“${r.first}”→ ${t}`}); await pg.close(); }
  // 9 收藏两条、选出发日，首页我的行程
  { const pg=await fresh(); await go(pg,'/trip/xa3/'); await pg.evaluate(()=>document.querySelector('.fav').click()); await pg.tap('.dtw'); await sleep(200); await pg.evaluate(()=>document.querySelector('.pk-q button[data-q="1"]').click()); await sleep(200);
    await go(pg,'/trip/cd3/'); await pg.evaluate(()=>document.querySelector('.fav').click()); await go(pg,'/'); const btn=await pg.evaluate(()=>document.querySelector('.minebtn').innerText);
    await pg.tap('.minebtn'); await sleep(300); const rows=await pg.evaluate(()=>[...document.querySelectorAll('.pk a.mr')].map(a=>a.innerText.replace(/\n/g,' ')));
    R.push({u:'90 小林 · 收藏两条看我的行程',ok:/· 2/.test(btn)&&rows.length>=2&&rows.some(x=>/出发 · 还有/.test(x)),find:`按钮“${btn}”；面板：${rows.slice(0,2).join(' ｜ ')}`}); await pg.close(); }
  // 10 断网打开看过的行程（离线缓存要 https，本地只看没网提示）
  { const pg=await fresh(); await go(pg,'/trip/xa3/'); await pg.setOfflineMode(true); await pg.evaluate(()=>window.dispatchEvent(new Event('offline'))); await sleep(200);
    const t=await pg.evaluate(()=>document.querySelector('.offline')?.innerText||''); await pg.setOfflineMode(false); R.push({u:'91 老马 · 山里没信号',ok:/没有网络/.test(t),find:t}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
