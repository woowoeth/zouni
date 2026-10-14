// 第 A 轮：十个人围着“点评入口和口碑”用一遍，看细节
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async f=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const stat=pg=>pg.evaluate(()=>{ const dps=[...document.querySelectorAll('a')].filter(a=>a.innerText.trim()==='点评'||a.innerText.trim()==='看点评');
    const rows=[...document.querySelectorAll('a[aria-label^="在大众点评看"]')];
    const kb=[...document.querySelectorAll('span')].filter(s=>getComputedStyle(s).color==='rgb(79, 98, 51)'&&/分|榜|招牌|条/.test(s.innerText)).map(s=>s.innerText);
    const small=dps.filter(a=>{ const r=a.getBoundingClientRect(); return r.height<32||r.width<30; }).length;
    const over=dps.filter(a=>a.getBoundingClientRect().right>390).length;
    const bad=dps.filter(a=>!/^https:\/\/www\.dianping\.com\//.test(a.href)).length;
    return {dp:dps.length, kb:kb.length, kbEx:kb.slice(0,2), small, over, bad, sample:rows.slice(0,2).map(a=>decodeURIComponent(a.href).slice(22,70))}; });
  const R=[], errs=[];
  for (const [u,rid] of [['小吴 · 去成都只为吃','cd3'],['林太太 · 挑苏州的酒店','sz3'],['张阿姨 · 先看景点评价再决定','zjj4'],['Jerry · 香港周末','hk2'],['Jerry · 大阪','kansai4'],['阿杰 · 九寨沟吃什么','jz4'],['小雨 · 上海一个人','sh3'],['老周 · 北疆','xj10'],['阿May · 杭州','hz3'],['Lily · 额济纳','nm4']]) {
    const pg=await open('Route.dc.html#'+rid);
    await pg.evaluate(()=>[...document.querySelectorAll('button')].filter(b=>b.innerText.includes('看另外')).forEach(b=>b.click())); await sleep(250);
    const s=await stat(pg); R.push({u,rid,...s}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); const s=await stat(pg); R.push({u:'去哪儿卡片',rid:'atlas',...s}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
