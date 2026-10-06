const p=require('/tmp/node_modules/puppeteer'); const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ids=['sx2','qinz2','yw2','jhpy2','ssx2','shgl2','wy3','kyt3'];
(async()=>{ const b=await p.launch({args:['--no-sandbox']}); const pg=await b.newPage(); await pg.setViewport({width:390,height:844}); const errs=[]; pg.on('pageerror',e=>errs.push(e.message.slice(0,80))); const bad=[];
  for(const id of ids){ const html=fs.readFileSync('/home/claude/zouni-site/trip/'+id+'/index.html','utf8'); const server=[...html.matchAll(/<li class="r [a-z]+"[^>]*><time>([^<]*)<\/time>/g)].map(m=>m[1]);
    await pg.goto('http://localhost:8765/trip/'+id+'/',{waitUntil:'load'}); await sleep(200);
    const r=await pg.evaluate(()=>({t:[...document.querySelectorAll('.day .tl > .r')].map(r=>r.querySelector('time').textContent),w:document.querySelectorAll('.latewarn').length,map:!!document.querySelector('.hmap'),go:(document.querySelector('section.go li')||{}).innerText||''}));
    const diff=server.filter((x,i)=>x!==r.t[i]).length; bad.push(id+(diff||r.w?' ✗ 改了 '+diff+' 行、提示 '+r.w:' ✓')+(r.map?' · 有地图':' · 无地图')+' · '+r.go.slice(0,28)); }
  console.log(bad.join('\n')+'\n报错 '+JSON.stringify(errs)); await b.close(); })();
