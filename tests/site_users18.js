// 第十八组：十位用户用 iPhone 体验一遍
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const fresh=async()=>{ const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev); return pg; };
  const go=async(pg,u)=>{ await pg.goto(B+u,{waitUntil:'networkidle0'}); await sleep(350); };
  const nav=async(pg,fn)=>{ await Promise.all([pg.waitForNavigation({waitUntil:'networkidle0'}).catch(()=>{}), pg.evaluate(fn)]); await sleep(350); return pg.url().replace(B,''); };
  // 1 王姐：北京行程改日期，日历每格对齐
  { const pg=await fresh(); await go(pg,'/trip/bj4/'); await pg.tap('.dtw'); await sleep(400);
    const g=await pg.evaluate(()=>{ const bs=[...document.querySelectorAll('.pk-g button')]; const td=document.querySelector('.pk-g .td0')||document.querySelector('.pk-g .on'); const i=bs.indexOf(td); const nb=bs[i+1]||bs[i-1]; const a=td.getBoundingClientRect(),c=nb.getBoundingClientRect(); return {w:[Math.round(a.width),Math.round(c.width)],h:[Math.round(a.height),Math.round(c.height)],top:[Math.round(a.top),Math.round(c.top)],nextColor:getComputedStyle(document.querySelector('.pk-n')).color}; });
    R.push({u:'72 王姐 · 北京行程点“改”',ok:g.w[0]===g.w[1]&&g.h[0]===g.h[1]&&g.top[0]===g.top[1]&&!/0, 122, 255|0, 0, 255/.test(g.nextColor),find:`今天那格 ${g.w[0]}×${g.h[0]}、旁边一格 ${g.w[1]}×${g.h[1]}，上沿 ${g.top.join(' / ')}；翻月按钮颜色 ${g.nextColor}`}); await pg.close(); }
  // 2 小陈：预算 2,000 → 地图看 → 点地名 → 返回状态还在
  { const pg=await fresh(); await go(pg,'/where/'); await pg.evaluate(()=>document.querySelector('.ftog').click()); await pg.select('.bud','2000'); await sleep(300); await pg.evaluate(()=>document.querySelector('.mtog').click()); await sleep(400);
    const n0=await pg.evaluate(()=>document.querySelectorAll('.wmap circle').length); const d=await nav(pg,()=>document.querySelector('.wmap a').dispatchEvent(new MouseEvent('click',{bubbles:true}))); const bk=await nav(pg,()=>document.querySelector('a.back').click());
    const st=await pg.evaluate(()=>({bud:document.querySelector('.bud').value,cnt:document.querySelector('.cnt').innerText}));
    R.push({u:'73 小陈 · 预算 2,000 看地图再返回',ok:n0>0&&d.startsWith('/d/')&&bk==='/where/'&&st.bud==='2000',find:`地图 ${n0} 个点，点进 ${d}，返回 ${bk}，预算还在 ${st.bud}（${st.cnt}）`}); await pg.close(); }
  // 3 李叔：九寨导航、点评、订酒店
  { const pg=await fresh(); await go(pg,'/trip/jz4/'); const r=await pg.evaluate(()=>({ios:document.querySelectorAll('a.ic.map[data-ios^="iosamap://"]').length,and:document.querySelectorAll('a.ic.map[data-and]').length,star:document.querySelector('a.ic.dp svg path')?.getAttribute('d').slice(0,12),hotel:document.querySelector('.stays .bk .btn')?.href||''}));
    R.push({u:'74 李叔 · 九寨导航和订酒店',ok:r.ios>3&&/(city=\d+|hoteldetail\/\d+)/.test(r.hotel),find:`能直接调起高德的图标 ${r.ios} 个；点评图标 ${r.star}…；订酒店 ${decodeURIComponent(r.hotel).slice(0,70)}`}); await pg.close(); }
  // 4 阿May：首页选 1/10，封面换，打开封面行程出发日跟着
  { const pg=await fresh(); await go(pg,'/'); await pg.tap('.hdt'); await sleep(300); for(let k=0;k<3;k++){ await pg.evaluate(()=>document.querySelector('.pk-n').click()); await sleep(80); }
    await pg.evaluate(()=>{ const bs=[...document.querySelectorAll('.pk-g button:not([disabled])')]; bs[9].click(); }); await sleep(500);
    const cv=await pg.evaluate(()=>({t:document.querySelector('.cv h2').innerText.replace(/\n/g,''),h:document.querySelector('.cv .go').getAttribute('href')}));
    const t=await nav(pg,()=>document.querySelector('.cv .go').click()); const dt=await pg.evaluate(()=>document.querySelector('.dt').innerText.replace(/\n/g,''));
    R.push({u:'75 阿May · 首页选 1 月 10 日出发',ok:/^\/trip\//.test(t)&&/1\/10/.test(dt),find:`封面“${cv.t}”，翻开 ${t}，行程出发日“${dt}”`}); await pg.close(); }
  // 5 小周：只看周末 2–3 天
  { const pg=await fresh(); await go(pg,'/'); await pg.evaluate(()=>document.querySelector('.dchips button[data-b="d1"]').click()); await sleep(300);
    const ds=await pg.evaluate(()=>[...document.querySelectorAll('.now .items li:not([hidden]) small')].map(s=>parseInt(s.innerText)));
    R.push({u:'76 小周 · 只看周末 2–3 天',ok:ds.length>0&&ds.every(x=>x<=3),find:`列出 ${ds.length} 条，天数 ${[...new Set(ds)].join('、')}`}); await pg.close(); }
  // 6 老赵：大理丽江每晚住处
  { const pg=await fresh(); await go(pg,'/trip/dali5/'); const st=await pg.evaluate(()=>[...document.querySelectorAll('.r.stay .m')].map(m=>m.childNodes[0].textContent.trim()));
    R.push({u:'77 老赵 · 大理丽江每晚住哪',ok:st.length>=4&&st.every(x=>/大理|丽江|喜洲|双廊|古城/.test(x)),find:st.join(' ｜ ')}); await pg.close(); }
  // 7 Lily：清迈当地时间、曼谷订酒店
  { const pg=await fresh(); await go(pg,'/trip/cm5/'); const s1=await pg.evaluate(()=>[...document.querySelectorAll('#d1 .sun')].map(x=>x.innerText).join('/'));
    await go(pg,'/trip/bkk3/'); const h=await pg.evaluate(()=>document.querySelector('.stays .bk .btn')?.href||'');
    R.push({u:'78 Lily · 清迈日出日落、曼谷订酒店',ok:/^0[56]:\d\d\/1[78]:\d\d$/.test(s1)&&/(city=\d+|hoteldetail\/\d+)/.test(h),find:`清迈第一天 ${s1}（当地时间）；曼谷 ${decodeURIComponent(h).slice(0,64)}`}); await pg.close(); }
  // 8 张老师：陕西博物馆国宝、要预约进出发前
  { const pg=await fresh(); await go(pg,'/d/shaanxi/'); const mus=await pg.evaluate(()=>[...document.querySelectorAll('.qual.mus li')].filter(li=>li.querySelector('.gb')).map(li=>li.querySelector('b').innerText));
    await go(pg,'/trip/xa3/'); const pre=await pg.evaluate(()=>[...document.querySelectorAll('.pre label span')].map(x=>x.innerText).filter(x=>/预约|买票/.test(x)));
    R.push({u:'79 张老师 · 博物馆和预约',ok:mus.length>=3&&pre.length>=1,find:`陕西标国宝的博物馆：${mus.join('、')}；西安出发前：${pre.join(' / ')}`}); await pg.close(); }
  // 9 阿杰：加一天再去掉
  { const pg=await fresh(); await go(pg,'/trip/xa3/'); await pg.evaluate(()=>document.querySelector('.addday .add').scrollIntoView()); await pg.tap('.addday .add'); await sleep(300);
    await pg.evaluate(()=>document.querySelector('.xd button[data-free]').click()); await sleep(400); const a=await pg.evaluate(()=>document.querySelector('.dock b').innerText);
    await pg.evaluate(()=>document.querySelector('.xday .rmday').click()); await sleep(300); const c=await pg.evaluate(()=>document.querySelector('.dock b').innerText);
    R.push({u:'80 阿杰 · 加一天又去掉',ok:/4 天/.test(a)&&/3 天/.test(c),find:`加了 ${a}；去掉后 ${c}`}); await pg.close(); }
  // 10 陈阿姨：分享 → 复制整条行程
  { const pg=await fresh(); await go(pg,'/trip/cd3/'); await pg.evaluate(()=>{ window.__c=''; Object.defineProperty(navigator,'clipboard',{value:{writeText:async t=>{window.__c=t;}},configurable:true}); });
    await pg.tap('.share'); await sleep(300); await pg.evaluate(()=>document.querySelector('.xd button[data-a="copy"]').click()); await sleep(300);
    const c=await pg.evaluate(()=>window.__c); R.push({u:'81 陈阿姨 · 复制成都行程发家人',ok:/第一天 · \d+\/\d+/.test(c)&&c.split('\n').length>8,find:c.split('\n').slice(0,4).join(' ｜ ')}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
