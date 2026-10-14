// 界面自查：文字被截断、同一行里的元素互相压住、超出卡片、点按区域太小
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
  const fs=require('fs'); const trips=fs.readdirSync('/home/claude/zouni-site/trip'); const dests=fs.readdirSync('/home/claude/zouni-site/d');
  const pick=(a,n)=>a.filter((_,i)=>i%Math.ceil(a.length/n)===0);
  const pages=['/','/where/'].concat(pick(trips,40).map(t=>'/trip/'+t+'/')).concat(pick(dests,12).map(d=>'/d/'+d+'/'));
  const out={};
  for (const u of pages) { const pg=await b.newPage(); await pg.setViewport({width:320,height:568,isMobile:true}); await pg.goto('http://localhost:8765'+u,{waitUntil:'networkidle0'}); await sleep(250);
    if(u==='/where/') await pg.evaluate(()=>{document.querySelector('.ftog').click()});
    const r=await pg.evaluate(()=>{ const issues=[]; const vis=e=>{const s=getComputedStyle(e);return s.display!=='none'&&s.visibility!=='hidden'&&e.offsetParent!==null};
      // 1 横向截断（单行元素里的字超出）
      document.querySelectorAll('h1,h2,h3,b,strong,span,small,p,a,button,time').forEach(e=>{ if(!vis(e)) return; const s=getComputedStyle(e); if(e.scrollWidth>e.clientWidth+2 && s.overflow!=='visible' && s.overflowX!=='auto' && e.clientWidth>0) issues.push('截断:'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+':'+(e.innerText||e.textContent||'').slice(0,14)); });
      // 2 同一行兄弟元素互相压住
      document.querySelectorAll('.ch,.nh,.glance,.dock,.overview a,.stays li,.r,.tr a,.mast,.cv .chips,.items li').forEach(row=>{ if(!vis(row)) return; const kids=[...row.children].filter(vis); for(let i=0;i<kids.length;i++) for(let j=i+1;j<kids.length;j++){ const a=kids[i].getBoundingClientRect(), c=kids[j].getBoundingClientRect(); const ox=Math.min(a.right,c.right)-Math.max(a.left,c.left), oy=Math.min(a.bottom,c.bottom)-Math.max(a.top,c.top); if(ox>3&&oy>3) issues.push('重叠:'+row.className+':'+(kids[i].className||kids[i].tagName)+'/'+(kids[j].className||kids[j].tagName)+':'+(row.innerText||'').slice(0,16).replace(/\n/g,' ')); } });
      // 3 超出屏幕
      if(document.documentElement.scrollWidth>window.innerWidth+1) issues.push('横向溢出');
      // 4 过小点按
      document.querySelectorAll('a,button').forEach(e=>{ if(!vis(e)||e.closest('.foot,.crumbs')) return; const r=e.getBoundingClientRect(); if(r.width>0&&(r.height<30||r.width<28)) issues.push('小点按:'+(e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className)+':'+(e.innerText||e.textContent||'').slice(0,10)); });
      return [...new Set(issues)].slice(0,12); });
    if(r.length) out[u]=r; await pg.close(); }
  fs.writeFileSync('/tmp/uiaudit.json',JSON.stringify(out,null,1)); await b.close(); })();
