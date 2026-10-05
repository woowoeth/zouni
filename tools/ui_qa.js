const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  for(const f of ['Main.dc.html','Plan.dc.html','Route.dc.html','Prep.dc.html','Today.dc.html']){
    const pg=await b.newPage(); const errs=[]; pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844}); await pg.goto('file:///tmp/dc-test/'+f,{waitUntil:'networkidle0'}); await sleep(1400);
    const r=await pg.evaluate(()=>{
      const out={align:[],gaps:[],overflow:[],overlap:[],small:[]};
      // 1 时间轴：圆点中心和竖线中心
      document.querySelectorAll('span').forEach(sp=>{ const st=sp.getAttribute('style')||''; if(!/left:\s*64px/.test(st)) return;
        const row=sp.parentElement; const dot=[...row.children].find(x=>x!==sp && /border-radius:\s*5px/.test(x.getAttribute('style')||''));
        if(!dot) return; const a=sp.getBoundingClientRect(), d=dot.getBoundingClientRect();
        const dx=Math.abs((a.left+a.width/2)-(d.left+d.width/2)); if(dx>0.6) out.align.push(Math.round(dx*10)/10); });
      // 竖线连续性
      const segs=[...document.querySelectorAll('span')].filter(s=>/left:\s*64px/.test(s.getAttribute('style')||'')).map(s=>s.getBoundingClientRect());
      for(let i=1;i<segs.length;i++){ const g=segs[i].top-segs[i-1].bottom; if(g>0.6 && g<200) out.gaps.push(Math.round(g)); }
      // 2 文字溢出
      [...document.querySelectorAll('span,a,button,h1,p')].forEach(e=>{ const s=getComputedStyle(e); if(s.textOverflow==='ellipsis') return;
        if(e.scrollWidth>e.clientWidth+2 && e.clientWidth>0 && s.overflow!=='visible') out.overflow.push(e.innerText.slice(0,20)); });
      // 3 文字互相压
      const leaves=[...document.querySelectorAll('span,a,h1,p,button')].filter(e=>e.innerText&&e.innerText.trim()&&e.children.length===0&&e.getBoundingClientRect().width>0);
      for(let i=0;i<leaves.length;i++) for(let j=i+1;j<leaves.length;j++){ const A=leaves[i].getBoundingClientRect(), B=leaves[j].getBoundingClientRect();
        const ix=Math.min(A.right,B.right)-Math.max(A.left,B.left), iy=Math.min(A.bottom,B.bottom)-Math.max(A.top,B.top);
        if(ix>3&&iy>3&&!leaves[i].contains(leaves[j])&&!leaves[j].contains(leaves[i])) out.overlap.push(leaves[i].innerText.slice(0,10)+' × '+leaves[j].innerText.slice(0,10)); }
      // 4 太小的可点区域
      [...document.querySelectorAll('a,button')].forEach(e=>{ const r=e.getBoundingClientRect(); if(r.width>0&&(r.height<32||r.width<32)) out.small.push((e.innerText||e.getAttribute('aria-label')||'').slice(0,12)+' '+Math.round(r.width)+'×'+Math.round(r.height)); });
      return {align:out.align.length, alignMax:Math.max(0,...out.align), gaps:out.gaps.slice(0,5), overflow:[...new Set(out.overflow)].slice(0,8), overlap:[...new Set(out.overlap)].slice(0,10), small:[...new Set(out.small)].slice(0,10)};
    });
    console.log(f, JSON.stringify(r), errs.length?('ERR '+errs[0]):'');
    await pg.close();
  }
  await b.close(); })();
