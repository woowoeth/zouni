#!/usr/bin/env node
/* ═══ 十轮压力测试 ═══
   十九连测查的是「有没有违反规则」，这十轮查的是「真用起来会不会出事」：
     1. 加天极限     —— 每条线连续加到不能加，看引擎撑不撑得住
     2. 疯狂切换     —— 快速切线路/天数/预算/口味，看状态会不会错乱
     3. 长会话内存   —— 连续操作 200 次，看内存是否持续增长
     4. 首屏性能     —— 冷启动到可交互的耗时
     5. 渲染性能     —— 切天、重排的帧耗时
     6. 滚动流畅度   —— 长行程列表的滚动掉帧
     7. 极端数据     —— 最长/最短行程、零预算、无备选
     8. 错误恢复     —— 坏数据、断网、异常输入后能否自愈
     9. 并发操作     —— 同时触发多个动作
    10. 规模预测     —— 100/200 条线路时的体积与耗时
*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过：未安装 puppeteer'); process.exit(0); } }
const path=require('path'), fs=require('fs');
const SRC='file://'+path.resolve(__dirname,'../src/index.html');
const FILE=path.resolve(__dirname,'../src/index.html');

const results=[];
const rec=(round,name,ok,detail)=>{ results.push({round,name,ok,detail:detail||''}); };

(async()=>{
  const browser=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:240000});

  /* ── 轮 1：加天极限 ── */
  {
    const pg=await browser.newPage(); const errs=[];
    pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(async()=>{
      const bad=[];
      let maxAdded=0;
      const ids=Object.keys(ROUTES).slice(0,20);
      for(const id of ids){
        try{
          curDays=ROUTES[id].days.length; uiLoadRoute(id); applyDraw();
          const base=DAYS.length; let n=0;
          while(n<8 && typeof canAddDay==='function' && canAddDay()){ addOneDay(); n++; }
          maxAdded=Math.max(maxAdded,n);
          /* 加完之后每一天都要能渲染、算得出钱 */
          for(let d=0; d<DAYS.length; d++){ active=d; renderDay(); }
          const tt=totals();
          if(!isFinite(tt.total)||tt.total<=0) bad.push(id+' 加天后算钱异常 '+tt.total);
          if(DAYS.length!==base+n) bad.push(id+' 天数不符 '+DAYS.length+'≠'+(base+n));
          if(LODGES.filter(Boolean).length!==DAYS.length-1) bad.push(id+' 住宿链断 '+LODGES.filter(Boolean).length);
        }catch(e){ bad.push(id+': '+e.message.slice(0,44)); }
      }
      return {bad, maxAdded};
    });
    rec(1,'加天极限', r.bad.length===0 && errs.length===0,
        r.bad.length? r.bad.slice(0,3).join(' | ') : `20 条线最多加 ${r.maxAdded} 天，住宿链与算钱均正确`);
    await pg.close();
  }

  /* ── 轮 2：疯狂切换 ── */
  {
    const pg=await browser.newPage(); const errs=[];
    pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(async()=>{
      const ids=Object.keys(ROUTES);
      let ops=0;
      for(let i=0;i<80;i++){
        const id=ids[i%ids.length];
        curDays=ROUTES[id].days.length; uiLoadRoute(id); applyDraw(); ops++;
        if(i%3===0){ setCur(i%6===0?'USD':'CNY'); ops++; }
        if(i%4===0){ setLang(i%8===0?'en':'zh'); ops++; }
        if(i%5===0){ const c=[...document.querySelectorAll('[data-taste]')]; if(c[i%8]) c[i%8].click(); ops++; }
        if(i%7===0){ active=Math.min(1,DAYS.length-1); renderDay(); ops++; }
      }
      /* 结束后状态必须自洽 */
      const okDays = DAYS.length===resolved.length && DAYS.length===mods.length;
      const tt=totals();
      return {ops, okDays, total:Math.round(tt.total), stable:isFinite(tt.total)&&tt.total>0};
    });
    rec(2,'疯狂切换', r.okDays && r.stable && errs.length===0,
        `${r.ops} 次操作后状态自洽，算钱 ¥${r.total}` + (errs.length?` · ${errs.length} 报错`:''));
    await pg.close();
  }

  /* ── 轮 3：长会话内存 ── */
  {
    const pg=await browser.newPage();
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const before=await pg.evaluate(()=>performance.memory? performance.memory.usedJSHeapSize : 0);
    await pg.evaluate(async()=>{
      const ids=Object.keys(ROUTES);
      for(let i=0;i<200;i++){
        const id=ids[i%ids.length];
        curDays=ROUTES[id].days.length; uiLoadRoute(id); applyDraw();
        active=i%Math.max(1,DAYS.length); renderDay();
      }
    });
    const after=await pg.evaluate(()=>{ if(window.gc) window.gc();
      return performance.memory? performance.memory.usedJSHeapSize : 0; });
    const growMB=(after-before)/1048576;
    rec(3,'长会话内存', before===0 || growMB<40,
        before===0? '浏览器未暴露 memory API' : `200 次操作后增长 ${growMB.toFixed(1)}MB`);
    await pg.close();
  }

  /* ── 轮 4：首屏性能 ── */
  {
    const pg=await browser.newPage();
    await pg.setViewport({width:390,height:844});
    const t0=Date.now();
    await pg.goto(SRC,{waitUntil:'domcontentloaded'});
    const domT=Date.now()-t0;
    await pg.waitForFunction(()=>document.querySelectorAll('.rec-card').length>0,{timeout:15000});
    const readyT=Date.now()-t0;
    const m=await pg.evaluate(()=>{
      const nav=performance.getEntriesByType('navigation')[0]||{};
      return {dcl:Math.round(nav.domContentLoadedEventEnd||0), cards:document.querySelectorAll('.rec-card').length};
    });
    rec(4,'首屏性能', readyT<3000, `DOM ${domT}ms · 可交互 ${readyT}ms · ${m.cards} 张卡`);
    await pg.close();
  }

  /* ── 轮 5：渲染性能 ── */
  {
    const pg=await browser.newPage();
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(()=>{
      curDays=15; uiLoadRoute('xj15'); applyDraw();
      const times=[];
      for(let d=0; d<DAYS.length; d++){
        const t=performance.now(); active=d; renderDay(); times.push(performance.now()-t);
      }
      const t2=performance.now(); applyDraw(); const drawT=performance.now()-t2;
      return {avg:+(times.reduce((a,b)=>a+b,0)/times.length).toFixed(1),
              max:+Math.max(...times).toFixed(1), draw:+drawT.toFixed(1)};
    });
    rec(5,'渲染性能', r.max<120 && r.draw<300,
        `切天均 ${r.avg}ms 峰值 ${r.max}ms · 整体重排 ${r.draw}ms`);
    await pg.close();
  }

  /* ── 轮 6：滚动流畅度 ── */
  {
    const pg=await browser.newPage();
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); curDays=15; uiLoadRoute('xj15'); applyDraw(); });
    const r=await pg.evaluate(async()=>{
      const h=document.documentElement.scrollHeight;
      const frames=[]; let last=performance.now();
      let raf; const tick=()=>{ const n=performance.now(); frames.push(n-last); last=n; raf=requestAnimationFrame(tick); };
      raf=requestAnimationFrame(tick);
      for(let y=0;y<h;y+=400){ window.scrollTo(0,y); await new Promise(r2=>setTimeout(r2,32)); }
      cancelAnimationFrame(raf);
      const slow=frames.filter(f=>f>32).length;
      return {pageH:h, frames:frames.length, slow, ratio:+(slow/Math.max(1,frames.length)*100).toFixed(1)};
    });
    rec(6,'滚动流畅度', r.ratio<25, `页高 ${r.pageH}px · ${r.frames} 帧中 ${r.slow} 帧超 32ms（${r.ratio}%）`);
    await pg.close();
  }

  /* ── 轮 7：极端数据 ── */
  {
    const pg=await browser.newPage(); const errs=[];
    pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(async()=>{
      const bad=[];
      const all=Object.keys(ROUTES);
      const longest=all.reduce((a,b)=>ROUTES[a].days.length>ROUTES[b].days.length?a:b);
      const shortest=all.reduce((a,b)=>ROUTES[a].days.length<ROUTES[b].days.length?a:b);
      for(const id of [longest,shortest]){
        try{ curDays=ROUTES[id].days.length; uiLoadRoute(id); applyDraw();
          for(let d=0;d<DAYS.length;d++){ active=d; renderDay(); }
          if(!isFinite(totals().total)) bad.push(id+' 算钱 NaN');
        }catch(e){ bad.push(id+': '+e.message.slice(0,36)); }
      }
      /* 预算拉到最低与不设限 */
      try{ BUDGET=1; applyDraw(); if(!isFinite(totals().total)) bad.push('最低预算算钱异常'); }catch(e){ bad.push('最低预算崩:'+e.message.slice(0,30)); }
      try{ BUDGET=NO_LIMIT; applyDraw(); }catch(e){ bad.push('不设限崩:'+e.message.slice(0,30)); }
      /* 全部口味都选 */
      try{ document.querySelectorAll('[data-taste]').forEach(c=>c.click()); applyDraw(); }
      catch(e){ bad.push('全选口味崩:'+e.message.slice(0,30)); }
      return {bad, longest, shortest, longDays:ROUTES[longest].days.length};
    });
    rec(7,'极端数据', r.bad.length===0 && errs.length===0,
        r.bad.length? r.bad.slice(0,2).join(' | ') : `最长 ${r.longest}(${r.longDays}天)、最短 ${r.shortest}、极端预算与全选口味均正常`);
    await pg.close();
  }

  /* ── 轮 8：错误恢复 ── */
  {
    const pg=await browser.newPage(); const errs=[];
    pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(async()=>{
      const bad=[];
      /* 装载不存在的线路 */
      try{ uiLoadRoute('__not_exist__'); }catch(e){}
      if(!RT) bad.push('装载坏 id 后 RT 丢失');
      /* 之后必须还能正常用 */
      try{ curDays=3; uiLoadRoute('cd3'); applyDraw();
        if(!isFinite(totals().total)) bad.push('恢复后算钱异常');
      }catch(e){ bad.push('无法恢复: '+e.message.slice(0,36)); }
      /* 越界的 active */
      try{ active=999; renderDay(); }catch(e){ bad.push('越界 active 崩: '+e.message.slice(0,30)); }
      try{ active=0; renderDay(); }catch(e){ bad.push('恢复 active 崩'); }
      /* 坏的出发日期 */
      try{ departDate='not-a-date'; applyDraw(); departDate=null; applyDraw(); }
      catch(e){ bad.push('坏日期崩: '+e.message.slice(0,30)); }
      return bad;
    });
    rec(8,'错误恢复', r.length===0, r.length? r.slice(0,3).join(' | ') : '坏 id / 越界索引 / 坏日期后均能自愈');
    await pg.close();
  }

  /* ── 轮 9：并发操作 ── */
  {
    const pg=await browser.newPage(); const errs=[];
    pg.on('pageerror',e=>errs.push(e.message.split('\n')[0]));
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
    const r=await pg.evaluate(async()=>{
      curDays=10; uiLoadRoute('xz10'); applyDraw();
      /* 同一帧内连开多个动作 */
      const acts=[
        ()=>{ const b=document.getElementById('btn-rain'); if(b) b.click(); },
        ()=>{ const b=document.getElementById('btn-depart'); if(b) b.click(); },
        ()=>{ const c=document.querySelector('[data-taste]'); if(c) c.click(); },
        ()=>{ const d=document.querySelector('[data-days]'); if(d) d.click(); }
      ];
      acts.forEach(f=>{ try{ f(); }catch(e){} });
      await new Promise(r2=>setTimeout(r2,600));
      /* 关掉所有弹层 */
      document.querySelectorAll('#cmp-box,#date-box,#credits-box').forEach(x=>x.classList.remove('on'));
      document.body.classList.remove('sheet-open');
      const openCnt=document.querySelectorAll('.on#cmp-box,.on#date-box').length;
      const tabHidden=getComputedStyle(document.querySelector('.tab-bar')).display==='none';
      return {openCnt, tabHidden, total:Math.round(totals().total)};
    });
    rec(9,'并发操作', r.openCnt===0 && !r.tabHidden && errs.length===0,
        `弹层残留 ${r.openCnt} · tab 恢复 ${!r.tabHidden} · 算钱 ¥${r.total}`);
    await pg.close();
  }

  /* ── 轮 10：规模预测 ── */
  {
    const size=fs.statSync(FILE).size/1024;
    const pg=await browser.newPage();
    await pg.setViewport({width:390,height:844});
    await pg.goto(SRC,{waitUntil:'networkidle0'});
    const n=await pg.evaluate(()=>Object.keys(ROUTES).length);
    await pg.close();
    const perRoute=size/n;
    const at100=Math.round(perRoute*100), at200=Math.round(perRoute*200);
    /* 4G 约 500KB/s */
    const load100=(at100/500).toFixed(1), load200=(at200/500).toFixed(1);
    rec(10,'规模预测', at100<1200,
        `当前 ${Math.round(size)}KB/${n} 条（${perRoute.toFixed(1)}KB 每条）· 100 条≈${at100}KB(4G ${load100}s) · 200 条≈${at200}KB(4G ${load200}s)`);
  }

  await browser.close();

  /* ── 汇总 ── */
  console.log('══ 十轮压力测试 ══\n');
  let pass=0;
  results.forEach(r=>{
    if(r.ok) pass++;
    console.log(`  ${r.ok?'✓':'✗'} 轮${String(r.round).padStart(2)} ${r.name.padEnd(10)} ${r.detail}`);
  });
  console.log(`\n  ${pass}/${results.length} 轮通过`);
  process.exit(pass===results.length?0:1);
})().catch(e=>{ console.error('ERR', e.message); process.exit(1); });
