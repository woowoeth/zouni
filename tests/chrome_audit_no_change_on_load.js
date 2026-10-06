// 全站排查：没改过任何东西时，页面打开后的时间要和生成的一模一样；不能冒出提示框
const p=require('/tmp/node_modules/puppeteer'); const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ids=fs.readdirSync('/home/claude/zouni-site/trip').filter(x=>fs.existsSync('/home/claude/zouni-site/trip/'+x+'/index.html')).sort();
const part=+process.argv[2]||0, parts=+process.argv[3]||1; const mine=ids.filter((_,i)=>i%parts===part);
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const pg=await b.newPage(); await pg.setViewport({width:390,height:844});
  const bad=[]; let n=0;
  for(const id of mine){ const html=fs.readFileSync('/home/claude/zouni-site/trip/'+id+'/index.html','utf8');
    const server=[...html.matchAll(/<li class="r [a-z]+"[^>]*><time>([^<]*)<\/time>/g)].map(m=>m[1]);
    try{ await pg.goto('http://localhost:8765/trip/'+id+'/',{waitUntil:'load',timeout:15000}); await sleep(150);
      const r=await pg.evaluate(()=>({times:[...document.querySelectorAll('.day .tl > .r')].map(r=>r.querySelector('time').textContent),warn:[...document.querySelectorAll('.latewarn')].map(w=>w.innerText.replace(/\n/g,' ').slice(0,60)),hid:[...document.querySelectorAll('.day .tl > .r')].filter(r=>r.hidden).length}));
      const diff=[]; for(let i=0;i<Math.max(server.length,r.times.length);i++){ if(server[i]!==r.times[i]) diff.push(`${server[i]}→${r.times[i]}`); }
      if(diff.length||r.warn.length||r.hid) bad.push({id,diff:diff.slice(0,4),ndiff:diff.length,warn:r.warn.slice(0,2),hid:r.hid});
    }catch(e){ bad.push({id,err:e.message.slice(0,60)}); }
    n++; }
  console.log(JSON.stringify({checked:n,bad})); await b.close(); })();
