// 第 3 轮：换一批人和任务
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); if(/Atlas/.test(f)) { await pg.evaluate(()=>{ const b=document.querySelector('button[aria-label="筛选"]'); if(b) b.click(); }); await sleep(150); } return pg; };
  const click=(pg,t)=>pg.evaluate(t=>{ const el=[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()===t); if(el){el.click();return true;} return false; },t);
  const firstGroup=pg=>pg.evaluate(()=>{ const head=[...document.querySelectorAll('span')].find(s=>/500 公里内$/.test(s.innerText)); if(!head) return null; const box=head.parentElement; return {head:head.innerText, items:[...box.querySelectorAll('[id^="d-"]')].map(c=>c.querySelector('span').innerText+'（'+([...c.querySelectorAll('span')].map(x=>x.innerText).find(t=>/^离.+公里/.test(t))||'').replace(/^离\S+ /,'')+'）')}; });
  const R=[], errs=[];
  for (const [u,org,extra] of [['赵姐 · 广州出发，11 月 3 天','广州',['11月','2–3 天']],['小陈 · 成都出发，周末','成都',['2–3 天']],['王先生 · 上海出发，周末','上海',['2–3 天']],['老两口 · 北京出发，不去高原','北京',['避开高原']]]) {
    const pg=await open('Atlas.dc.html'); await click(pg,org); await sleep(150); for(const e of extra){ await click(pg,e); await sleep(150); } await sleep(200);
    const g=await firstGroup(pg); R.push({u,find:g?`${g.head}：${g.items.join('、')}`:'没有 500 公里内的'}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).click()); await sleep(200); await click(pg,'2,000–5,000'); await sleep(250);
    const n=await pg.evaluate(()=>[...new Set([...document.querySelectorAll('[id^="d-"]')].map(c=>c.querySelector('span').innerText))]);
    R.push({u:'情侣 · 亚洲 4 天，每人 5,000 以内',find:`筛出：${n.join('、')}`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html#q=japan&m=11'); await sleep(400); const st=await pg.evaluate(()=>({tab:[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).style.background, top:Math.round(document.getElementById('d-japan').getBoundingClientRect().top)}));
    R.push({u:'Jerry · 从本期目录点“北海道”',find:`直接打开亚洲页 11 月，日本卡在 ${st.top}px 处`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'避开高原'); await sleep(250); const left=await pg.evaluate(()=>[...new Set([...document.querySelectorAll('[id^="d-"]')].map(c=>c.querySelector('span').innerText))]);
    R.push({u:'张阿姨 · 避开高原',find:`国内剩 ${left.length} 个，西藏、青海${left.includes('西藏')||left.includes('青海')?'还在':'已去掉'}`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
