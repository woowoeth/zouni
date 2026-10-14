// 第二十一组：长线路的界面
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const B=process.argv[2]||'http://localhost:8765';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; const R=[], errs=[];
  const ctx=await b.createBrowserContext(); const pg=await ctx.newPage(); pg.on('pageerror',e=>errs.push(e.message.split('\n')[0])); await pg.emulate(dev);
  await pg.goto(B+'/trip/xbdh30/',{waitUntil:'networkidle0'}); await sleep(400);
  const a=await pg.evaluate(()=>{ const n=document.querySelector('.daynav'); const c=n.querySelector('a').getBoundingClientRect(); return {long:n.classList.contains('long'),w:Math.round(c.width),sw:n.scrollWidth,cw:n.clientWidth,ov:[...document.querySelectorAll('.overview ol li')].filter(li=>getComputedStyle(li).display!=='none').length}; });
  await pg.evaluate(()=>{ document.documentElement.style.scrollBehavior='auto'; const e=document.getElementById('d20'); window.scrollTo(0,e.getBoundingClientRect().top+scrollY-60); }); await sleep(500);
  const c=await pg.evaluate(()=>{ const n=document.querySelector('.daynav'); const on=n.querySelector('a.on'); const r=on?on.getBoundingClientRect():null; return {sl:Math.round(n.scrollLeft),on:on?on.innerText:'',vis:r?(r.left>=0&&r.right<=innerWidth):false}; });
  await pg.evaluate(()=>{ window.scrollTo(0,0); document.querySelector('.ovmore').click(); }); await sleep(200);
  const ov2=await pg.evaluate(()=>[...document.querySelectorAll('.overview ol li')].filter(li=>getComputedStyle(li).display!=='none').length);
  R.push({u:'97 陈哥 · 30 天的天数条和怎么排',ok:a.long&&a.w>=44&&a.sw>a.cw&&c.on==='20'&&c.vis&&a.ov===10&&ov2===30,find:`天数条每格 ${a.w} 宽、可左右滑（${a.sw}/${a.cw}）；看到第 20 天时格子滑到 ${c.sl}，当前“${c.on}”${c.vis?'在屏幕内':'不在屏幕内'}；怎么排先显示 ${a.ov} 天，点开 ${ov2} 天`});
  await pg.goto(B+'/trip/xa3/',{waitUntil:'networkidle0'}); await sleep(300);
  const s=await pg.evaluate(()=>({long:document.querySelector('.daynav').classList.contains('long'),btn:!!document.querySelector('.ovmore')}));
  R.push({u:'98 小周 · 3 天的不受影响',ok:!s.long&&!s.btn,find:`天数条${s.long?'变成可滑':'照旧平分'}，${s.btn?'有':'没有'}“看全部”按钮`});
  console.log(JSON.stringify({R,errs},null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
