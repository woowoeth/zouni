// 第 2 轮：同样十个人再走一遍
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const click=(pg,t)=>pg.evaluate(t=>{ const el=[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()===t||e.getAttribute('aria-label')===t); if(el){el.click();return true;} return false; },t);
  const R=[], errs=[];
  { const pg=await open('Main.dc.html'); const len=await pg.evaluate(()=>{ const s=[...document.querySelectorAll('div')].find(d=>getComputedStyle(d).overflowY==='auto'); return (s.scrollHeight/844).toFixed(1); });
    await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>/个目的地/.test(b.innerText)).click()); await sleep(300);
    const d=await pg.evaluate(()=>{ const links=[...document.querySelectorAll('a')].filter(a=>/Route|Plan|Atlas/.test(a.getAttribute('href')||'')&&/天 ·/.test(a.innerText)); const sh=links.find(a=>a.innerText.startsWith('上海')); const wy=links.find(a=>a.innerText.startsWith('婺源')); return {n:links.length, sh:sh&&sh.getAttribute('href'), wy:wy&&wy.getAttribute('href'), tag:/台阶|高海拔/.test(links.map(a=>a.innerText).join(' '))}; });
    R.push({u:'老马 · 从目录点进上海',find:`本期页收起后 ${len} 屏；展开后 ${d.n} 行都能点，上海 → ${d.sh}`}); R.push({u:'小雨 · 从目录点婺源',find:`婺源 → ${d.wy}`}); R.push({u:'张阿姨 · 目录里看提醒',find:`目录行里${d.tag?'有':'没有'}“台阶多、高海拔”`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html#q=jiangxi&m=10'); await sleep(400); const f=await pg.evaluate(()=>{ const el=document.getElementById('d-jiangxi'); const r=el.getBoundingClientRect(); return {top:Math.round(r.top), ring:getComputedStyle(el).boxShadow.includes('166')}; });
    R.push({u:'小雨 · 定位到婺源卡',find:`打开后婺源卡在屏幕 ${f.top}px 处，${f.ring?'有红框标出':'没标出'}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'从上海'); await sleep(200); await click(pg,'2–3 天'); await sleep(250);
    const near=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/周末能去/.test(s.innerText)).map(s=>s.closest('[id^="d-"]').querySelector('span').innerText).slice(0,6));
    R.push({u:'王先生 · 从上海出发，周末两天',find:`选“从上海”和“2–3 天”，500 公里内的：${[...new Set(near)].join('、')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).click()); await sleep(200); await click(pg,'大陆护照'); await sleep(250);
    const jp=await pg.evaluate(()=>{ const c=document.getElementById('d-japan'); return c? [...c.querySelectorAll('span')].map(s=>s.innerText).find(t=>t.startsWith('香港特区护照')):''; });
    R.push({u:'Jerry · 香港特区护照',find:`切到香港特区护照，日本写：${jp}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'¥2,000 以内'); await sleep(250); const n=await pg.evaluate(()=>[...document.querySelectorAll('[id^="d-"]')].map(c=>c.querySelector('span').innerText));
    R.push({u:'阿杰 · ¥2,000 以内',find:`筛出 ${n.length} 个：${n.slice(0,8).join('、')}`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html#m=12'); await sleep(300); const good=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^12 月正好去/.test(t)));
    R.push({u:'李老师 · 12 月',find:good}); await pg.close(); }
  { const pg=await open('Route.dc.html#jz4'); await click(pg,'多一个人'); await sleep(150); await click(pg,'多一个人'); await sleep(200); const four=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^¥[\d,]+–[\d,]+$/.test(t)));
    R.push({u:'Lily · 4 人',find:`九寨黄龙 4 人每人 ${four}`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); const two=await pg.evaluate(()=>[...document.querySelectorAll('a')].filter(a=>/翻开/.test(a.innerText)).length);
    R.push({u:'小林 · 封面',find:`封面“翻开”和目录里能翻开的入口共 ${two} 个`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
