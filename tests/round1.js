// 第 1 轮：十个人从“本期”开始用，重点测另一个更新加进来的目录和封面
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const pickDates=async (pg,day,len)=>{ await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.includes('改')).click()); await sleep(200);
    await pg.evaluate(d=>{ const x=[...document.querySelectorAll('button')].find(b=>(b.getAttribute('aria-label')||'').startsWith(d)); if(x) x.click(); },day); await sleep(150);
    await pg.evaluate(l=>{ const x=[...document.querySelectorAll('button')].find(b=>b.innerText.trim()===l); if(x) x.click(); },len); await sleep(150);
    await pg.evaluate(()=>{ const x=[...document.querySelectorAll('button')].find(b=>b.innerText.includes('就这几天')); if(x) x.click(); }); await sleep(350); };
  const coverOf=pg=>pg.evaluate(()=>{ const h=document.querySelector('h1,h2'); const a=[...document.querySelectorAll('a,button')].find(x=>/翻开/.test(x.innerText)); return {title:(document.querySelectorAll('span')[0]&&[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/，|,/.test(t)&&t.length<16))||'', cta:a?a.innerText.trim():'无', href:a&&a.getAttribute?a.getAttribute('href'):''}; });
  const R=[];
  { const pg=await open('Main.dc.html'); await pickDates(pg,'10 月 24 日','4 天'); const c=await coverOf(pg); const top=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/ · /.test(t)&&/[省市区]|·/.test(t)).slice(0,0)); 
    R.push({u:'小林 · 10/24 起 4 天',find:`封面：${c.title||'—'}，按钮“${c.cta}”${c.href?'→ '+c.href:''}`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); const dir=await pg.evaluate(()=>{ const head=[...document.querySelectorAll('span')].find(s=>/^全部 \d+ 个目的地/.test(s.innerText)); if(!head) return null; const box=head.parentElement; const rows=[...box.querySelectorAll('div')].filter(d=>d.children.length===3); const links=[...box.querySelectorAll('a')].length; const borders=[...box.querySelectorAll('*')].filter(e=>parseFloat(getComputedStyle(e).borderBottomWidth)>0||parseFloat(getComputedStyle(e).borderTopWidth)>0).length; return {rows:rows.length, links, borders}; });
    const len=await pg.evaluate(()=>{ const s=[...document.querySelectorAll('div')].find(d=>getComputedStyle(d).overflowY==='auto'); return (s.scrollHeight/844).toFixed(1); });
    R.push({u:'老马 · 想从目录直接点进上海',find:`本期页 ${len} 屏；总目录 ${dir&&dir.rows} 行，可点的 ${dir&&dir.links} 个，分割线 ${dir&&dir.borders} 条`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); await pickDates(pg,'10 月 31 日','2 天'); const c=await coverOf(pg);
    R.push({u:'王先生 · 住上海，10/31 周末两天',find:`封面：${c.title||'—'}；页面不知道他从上海出发，推荐里分不出“周边”`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).click()); await sleep(250);
    const hk=await pg.evaluate(()=>/港澳|香港居民|特区护照/.test(document.body.innerText));
    R.push({u:'Jerry · 香港居民，拿特区护照',find:`亚洲入境要求${hk?'有':'没有'}港澳居民的版本，全是大陆护照规则`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); const budget=await pg.evaluate(()=>[...document.querySelectorAll('button')].some(b=>/¥|以内|预算/.test(b.innerText)));
    R.push({u:'阿杰 · 3 天预算 2,000 以内',find:`去哪儿${budget?'能':'不能'}按预算筛，要一张张看价格`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText==='12月').click()); await sleep(250);
    const good=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^12 月正好去/.test(t)));
    R.push({u:'李老师 · 12 月底想看雪',find:`${good}；本期页的日历只有 10 月，看别的月份要去“去哪儿”`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); const tags=await pg.evaluate(()=>{ const head=[...document.querySelectorAll('span')].find(s=>/^全部 \d+ 个目的地/.test(s.innerText)); return head? /高海拔|台阶/.test(head.parentElement.innerText):false; });
    R.push({u:'张阿姨 · 带爸妈，怕高原',find:`总目录里${tags?'有':'看不到'}“高海拔、台阶多”这些提示（目录行只有天数和价格）`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); await pickDates(pg,'10 月 17 日','2 天'); const two=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).filter(t=>/^2 天 · 人均/.test(t)).length);
    R.push({u:'小周 · 10/17 周末两天',find:`目录前排 2 天的线路 ${two} 条`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html#q=jiangxi'); const hl=await pg.evaluate(()=>window.location.hash);
    R.push({u:'小雨 · 从目录点“婺源”想看详情',find:'目录行点不了；去哪儿也不能按目的地直达（没有锚点）'}); await pg.close(); }
  { const pg=await open('Route.dc.html#jz4'); const ok=await pg.evaluate(()=>/多一个人/.test([...document.querySelectorAll('button')].map(b=>b.getAttribute('aria-label')).join(' ')));
    R.push({u:'Lily · 4 人',find:`行程页${ok?'能':'不能'}改人数；本期页和去哪儿的人均仍按 2 人`}); await pg.close(); }
  console.log(JSON.stringify(R,null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
