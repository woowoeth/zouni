// 第 6 轮：新增 8 条行程逐条打开，看时间轴是否连贯、标记点和点评是否齐、有没有破图
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const out=[];
  for (const rid of ['xa3','ly3','sx4','wy3','gz3','xm4','nj3','tj2','bj4','hs2','qd3','es4','gl4','cq3','dali5','dh4','nx3','mo2','tc4','sy4','dl3','kr4','tk4','vn5','sg3']) {
    const pg=await b.newPage(); const errs=[]; pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844});
    await pg.goto('file:///tmp/dc-test/Route.dc.html#'+rid,{waitUntil:'networkidle0'}); await sleep(1000);
    const r=await pg.evaluate(()=>{ const days=[...document.querySelectorAll('[id^="d"]')].filter(e=>/^d\d+$/.test(e.id));
      let backward=0; for(const d of days){ const ts=[...d.querySelectorAll('span')].filter(s=>s.style.width==='48px').map(s=>s.innerText).filter(t=>/^\d\d:\d\d$/.test(t)); const m=ts.map(t=>+t.slice(0,2)*60+ +t.slice(3)); for(let i=1;i<m.length;i++) if(m[i]<m[i-1]) backward++; }
      const imgs=[...document.querySelectorAll('img')].filter(i=>!i.complete||i.naturalWidth===0).length;
      return {h1:document.querySelector('h1').innerText, days:days.length, pins:document.querySelectorAll('a[aria-label*="地图打开"]').length, dp:[...document.querySelectorAll('a')].filter(a=>/dianping/.test(a.href)).length, backward, brokenImg:imgs, stays:[...document.querySelectorAll('span')].filter(s=>/^住 · /.test(s.innerText)).length}; });
    out.push({rid,...r,errs}); await pg.close(); }
  const at=await b.newPage(); await at.setViewport({width:390,height:844}); await at.goto('file:///tmp/dc-test/Atlas.dc.html',{waitUntil:'networkidle0'}); await sleep(1000);
  const links=await at.evaluate(()=>[...document.querySelectorAll('a')].map(a=>a.getAttribute('href')).filter(h=>/Route/.test(h)).map(h=>h.split('#')[1].split('&')[0]));
  console.log(JSON.stringify({routes:out, atlasLinks:links},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
