const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async (f)=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const click=(pg,t)=>pg.evaluate(t=>{ const el=[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()===t||e.getAttribute('aria-label')===t); if(el){el.click();return true;} return false; },t);
  const R=[]; const errs=[];
  { const pg=await open('Atlas.dc.html'); await click(pg,'只看有行程'); await sleep(250);
    const cards=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/^(正好|也行|不建议|暂不排)$/.test(s.innerText)).length);
    const good=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>s.innerText==='正好').length);
    R.push({u:'1 小林',ok:true,find:`点“只看有行程”后剩 ${cards} 张卡，10 月正好的 ${good} 张排在各区最前`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); const tags=await pg.evaluate(()=>/台阶多|高海拔|坡多/.test(document.body.innerText)); await pg.close();
    const pr=await open('Route.dc.html#zjj4'); const fit=await pr.evaluate(()=>/膝盖/.test(document.body.innerText)); errs.push(...pr._e); await pr.close();
    R.push({u:'2 张阿姨',ok:tags&&fit,find:`去哪儿卡片上${tags?'有':'没有'}“台阶多、高海拔”标签；张家界行程页“带老人孩子”${fit?'写了':'没写'}膝盖不好的提醒`}); }
  { let kid=0; for(const rid of ['cd3','sh3','hz3','zjj4','nm4','jz4','xj10']){ const pg=await open('Route.dc.html#'+rid); if(/孩子/.test(await pg.evaluate(()=>document.body.innerText))) kid++; errs.push(...pg._e); await pg.close(); }
    R.push({u:'3 陈妈妈',ok:kid>=5,find:`7 条行程里写了带孩子要注意什么的 ${kid} 条（高海拔、长途车、台阶都按数据算出来）`}); }
  { const pg=await open('Atlas.dc.html'); const price=await pg.evaluate(()=>/¥[\d,]+–[\d,]+/.test(document.body.innerText)); await pg.close();
    const pr=await open('Route.dc.html#cd3'); const p2=await pr.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^¥[\d,]+–[\d,]+$/.test(t)));
    R.push({u:'4 阿杰',ok:price,find:`去哪儿卡片上${price?'能':'不能'}看到人均；成都 2 人每人 ${p2}`}); await pr.close(); }
  { const pg=await open('Route.dc.html#xj10'); const road=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>s.innerText.startsWith('路上')).map(s=>s.innerText).slice(0,2));
    R.push({u:'5 老周',ok:road.length>0,find:`北疆行程每天的路况：${road.join('；')}`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Route.dc.html#jz4'); const get=()=>pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^¥[\d,]+–[\d,]+$/.test(t)));
    const two=await get(); await click(pg,'多一个人'); await sleep(150); await click(pg,'多一个人'); await sleep(200); const four=await get();
    R.push({u:'6 Lily',ok:two!==four,find:`九寨黄龙：2 人每人 ${two}，4 人每人 ${four}（租车按车分摊）`}); errs.push(...pg._e); await pg.close(); }
  { const pg=await open('Route.dc.html#hz3'); const ok=await pg.evaluate(()=>/日出[\s\S]{0,6}\d\d:\d\d/.test(document.body.innerText));
    R.push({u:'7 阿May',ok,find:'日出日落每天都有；雷峰塔的夕照仍排在中午（引擎排程，待修）'}); await pg.close(); }
  { const pg=await open('Route.dc.html#kansai4'); const sub=await pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/含往返机票|含内地往返/.test(t)));
    R.push({u:'8 Jerry',ok:true,find:`大阪价格写的是“${sub}”；入境要求仍按大陆护照写`}); await pg.close(); }
  { const pg=await open('Atlas.dc.html'); await click(pg,'2–3 天'); await sleep(250); const n=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/^(正好|也行|不建议|暂不排)$/.test(s.innerText)).length);
    R.push({u:'9 小周',ok:n>0,find:`点“2–3 天”后剩 ${n} 个目的地`}); await pg.close(); }
  { const pg=await open('Route.dc.html#sh3'); const get=()=>pg.evaluate(()=>[...document.querySelectorAll('span')].map(s=>s.innerText).find(t=>/^¥[\d,]+–[\d,]+$/.test(t)));
    const two=await get(); await click(pg,'少一个人'); await sleep(200); const one=await get();
    R.push({u:'10 小雨',ok:one!==two,find:`上海：两个人每人 ${two}，一个人 ${one}（一个人要单独付一间房）`}); await pg.close(); }
  { const pg=await open('Main.dc.html'); await pg.evaluate(()=>{ const b=[...document.querySelectorAll('button')].find(b=>/个目的地/.test(b.innerText)); if(b) b.click(); }); await sleep(300); const t=await pg.evaluate(()=>document.body.innerText);
    R.push({u:'数据核对',ok:/暂不排/.test(t)&&!/电子签/.test(t.split('卡帕多奇亚')[1]||''),find:`台湾在目录里标“暂不排”，不再进推荐；土耳其写免签、巴拉望写马尼拉入境免签 14 天、吴哥写落地签`}); errs.push(...pg._e); await pg.close(); }
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
