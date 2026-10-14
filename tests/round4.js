// 第 4 轮：十个人看细节——带着条件进出、返回、没结果、换月份
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1000); return pg; };
  const click=(pg,t)=>pg.evaluate(t=>{ const el=[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()===t||e.getAttribute('aria-label')===t); if(el){el.click();return true;} return false; },t);
  const cardLink=(pg,id)=>pg.evaluate(id=>{ const c=document.getElementById('d-'+id); const a=c&&[...c.querySelectorAll('a')].find(x=>x.innerText.includes('完整行程')); return a? a.getAttribute('href'):null; },id);
  const R=[], errs=[];
  { const pg=await open('Atlas.dc.html'); await click(pg,'11月'); await sleep(200); const href=await cardLink(pg,'hunan');
    await pg.goto(U+href,{waitUntil:'networkidle0'}); await sleep(900);
    const r=await pg.evaluate(()=>({d:[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^第一天/.test(t)), t:[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^往年/.test(t))}));
    R.push({u:'1 张阿姨 · 选 11 月再翻开张家界',ok:/11\//.test(r.d||''),find:`链接 ${href}；第一天：${r.d}；${r.t}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).click()); await sleep(150); await click(pg,'大陆护照'); await sleep(200);
    const href=await cardLink(pg,'japan'); await pg.goto(U+href,{waitUntil:'networkidle0'}); await sleep(900);
    const prep=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/签/.test(t)).slice(0,2));
    R.push({u:'2 Jerry · 香港护照翻开大阪',ok:prep.some(t=>t.includes('香港特区护照')),find:`先办：${prep.join('；')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'从上海'); await sleep(150); await click(pg,'2–3 天'); await sleep(200);
    const href=await cardLink(pg,'zhejiang'); await pg.evaluate(h=>{ location.href=h; },href); await sleep(1300);
    await pg.evaluate(()=>{ const a=document.querySelector('a[aria-label="返回"]'); a.click(); }); await sleep(1300);
    const st=await pg.evaluate(()=>({hash:location.hash, origin:[...document.querySelectorAll('button')].find(b=>b.innerText==='从上海').style.background, cnt:[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^符合的/.test(t))}));
    R.push({u:'3 小林 · 筛完翻开杭州再返回',ok:/o=/.test(st.hash),find:`返回后地址 ${decodeURIComponent(st.hash)}，${st.cnt}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'¥2,000 以内'); await sleep(150); await click(pg,'6 天以上'); await sleep(250);
    const e1=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^现在选了/.test(t))); await click(pg,'清空筛选'); await sleep(250);
    const c2=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^符合的/.test(t)));
    R.push({u:'4 阿杰 · 筛到没结果',ok:!!e1,find:`提示“${e1}”；点“清空筛选”后 ${c2}`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>/个目的地/.test(b.innerText)).click()); await sleep(250);
    await pg.evaluate(()=>[...document.querySelectorAll('a')].find(a=>a.innerText.startsWith('婺源')).click()); await sleep(1300);
    const at=await pg.evaluate(()=>location.pathname.split('/').pop()+location.hash);
    await pg.goBack({waitUntil:'networkidle0'}); await sleep(900); const back=await pg.evaluate(()=>location.pathname.split('/').pop());
    R.push({u:'5 老马 · 目录 → 婺源 → 返回',ok:back==='Main.dc.html',find:`去了 ${decodeURIComponent(at)}，返回到 ${back}`}); await pg.close(); }
  { const a=await open('Route.dc.html#cd3'); const s10=await a.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/^\d\d:\d\d$/.test(t)).slice(1,3)); await a.close();
    const c=await open('Route.dc.html#cd3&m=12'); const s12=await c.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/^\d\d:\d\d$/.test(t)).slice(1,3)); await c.close();
    R.push({u:'6 阿May · 成都 10 月和 12 月的日出日落',ok:s10.join()!==s12.join(),find:`10 月 ${s10.join(' / ')}；12 月 ${s12.join(' / ')}`}); }
  { const pg=await open('Atlas.dc.html'); const c0=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^符合的/.test(t))); await click(pg,'只看有行程'); await sleep(200);
    const c1=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^符合的/.test(t)));
    R.push({u:'7 小周 · 看筛完剩几个',ok:c0!==c1,find:`${c0} → 点“只看有行程”后 ${c1}`}); await pg.close(); }
  { const pg=await open('Route.dc.html#jz4'); await click(pg,'多一个人'); await click(pg,'多一个人'); await sleep(200); const dock=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/人 · 每人/.test(t)));
    R.push({u:'8 Lily · 4 人',ok:/4 人/.test(dock||''),find:`底栏：${dock}`}); await pg.close(); }
  { const pg=await open('Route.dc.html#zjj4&m=11'); const fit=await pg.evaluate(()=>{ const h=[...document.querySelectorAll('span')].find(s=>s.innerText==='带老人孩子'); return h? h.parentElement.innerText.replace(/\n/g,'；'):''; });
    R.push({u:'9 陈妈妈 · 带孩子去张家界',ok:!!fit,find:fit}); await pg.close(); }
  { const pg=await open('Atlas.dc.html#tab=domestic&m=10&o=%E4%B8%8A%E6%B5%B7'); await sleep(300); const g=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/500 公里内$/.test(t)));
    const me=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^就在/.test(t)));
    R.push({u:'10 王先生 · 带着“从上海”的链接直接打开',ok:!!g,find:`${g}；上海卡上写“${me}”`}); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
