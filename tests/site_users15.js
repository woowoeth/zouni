// 第十五组：住三档、吃的推荐、导航不重复、加一天
const p=require('puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const R=[], errs=[];
  const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844,isMobile:true,hasTouch:true});
  await pg.goto(B+'/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(300);
  const st=await pg.evaluate(()=>{ const c=document.querySelector('.stays'); const lis=[...c.querySelectorAll('li')]; return {vis:lis.filter(l=>getComputedStyle(l).display!=='none').map(l=>l.innerText.replace(/\n/g,' ')),all:lis.length,ctrip:c.querySelector('.bk .btn')?.href||''}; });
  await pg.evaluate(()=>document.querySelector('.stays .tog').click()); await sleep(150);
  const st2=await pg.evaluate(()=>[...document.querySelector('.stays').querySelectorAll('li')].filter(l=>getComputedStyle(l).display!=='none').length);
  R.push({u:'63 西安第一晚“今晚住”三档',ok:st.all===3&&st.vis.length===1&&st2===3&&/ctrip\.com\/(webapp\/hotels\/list\?city=\d+|html5\/hotel\/hoteldetail\/\d+)/.test(st.ctrip),find:`默认显示：${st.vis[0]}；点“看另外两档”后 ${st2} 档；链接 ${decodeURIComponent(st.ctrip).slice(0,70)}`});
  const food=await pg.evaluate(()=>[...document.querySelectorAll('.r.eat')].map(r=>r.innerText.replace(/\n/g,' ')).slice(0,4));
  R.push({u:'64 西安的饭',ok:food.some(f=>/老店：|点评上找/.test(f)),find:food.join(' ｜ ')});
  const nv=await pg.evaluate(()=>({navText:[...document.querySelectorAll('.r.dep')].filter(r=>/导航/.test(r.innerText)).length,pins:[...document.querySelectorAll('.r .ic[aria-label^="导航去"]')].length}));
  R.push({u:'65 导航不重复',ok:nv.navText===0&&nv.pins>3,find:`出发行里还写“导航”的 ${nv.navText} 行；地图图标就是导航的 ${nv.pins} 个`});
  await pg.evaluate(()=>document.querySelector('.addday .add').click()); await sleep(200);
  const opts=await pg.evaluate(()=>[...document.querySelectorAll('.xd button')].map(x=>x.innerText.replace(/\n/g,' ')).slice(0,4));
  await pg.evaluate(()=>document.querySelector('.xd button[data-free]').click()); await sleep(400);
  await pg.evaluate(()=>document.querySelector('.addday .add').click()); await sleep(200);
  const hasR=await pg.evaluate(()=>!!document.querySelector('.xd button[data-rid]'));
  if(hasR){ await pg.evaluate(()=>document.querySelector('.xd button[data-rid]').click()); await sleep(1500); } else { await pg.evaluate(()=>document.querySelector('.pk-x').click()); }
  const a=await pg.evaluate(()=>({days:document.querySelectorAll('.day').length,dock:document.querySelector('.dock b').innerText,h:document.querySelector('.overview h2').innerText,nav:document.querySelectorAll('.daynav a').length,last:[...document.querySelectorAll('.day')].slice(-2).map(s=>s.querySelector('header small').innerText+' '+s.querySelector('h2').innerText.replace(/\n/g,' '))}));
  R.push({u:'66 加两天（自由活动 + 附近线路的一天）',ok:a.days===5&&/5 天/.test(a.dock)&&/5 天/.test(a.h)&&a.nav===5,find:`可选：${opts.join(' / ')}…；加完 ${a.days} 天，底栏“${a.dock}”，“${a.h}”，天数条 ${a.nav} 格；最后两天：${a.last.join(' ｜ ')}`});
  await pg.reload({waitUntil:'networkidle0'}); await sleep(1500);
  const k1=await pg.evaluate(()=>document.querySelectorAll('.day').length);
  await pg.evaluate(()=>document.querySelector('.xday .rmday').click()); await sleep(300);
  const k2=await pg.evaluate(()=>({d:document.querySelectorAll('.day').length,dock:document.querySelector('.dock b').innerText}));
  await pg.reload({waitUntil:'networkidle0'}); await sleep(1500); const k3=await pg.evaluate(()=>document.querySelectorAll('.day').length);
  R.push({u:'67 重新打开还在、能去掉',ok:k1===5&&k2.d===4&&k3===4,find:`重新打开 ${k1} 天；去掉一天后 ${k2.d} 天（${k2.dock}）；再打开 ${k3} 天`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
