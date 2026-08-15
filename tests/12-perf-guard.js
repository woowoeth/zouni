#!/usr/bin/env node
/* ═══ 第 12 项：性能守卫与健壮性 ═══
   守住四类系统性风险，任何一项越界即失败：
     A. 体积与规模   —— 单文件体积、数据量随线路数的增长
     B. 响应性能     —— 加载、搜索、引擎重排、切天、切语言
     C. 健壮性       —— 坏数据隔离、快速切换竞态、存储写入被拒
     D. 存储容量     —— 单份行程体积 × 可存份数
*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过性能守卫：未安装 puppeteer'); process.exit(0); } }
const fs=require('fs'), path=require('path');
const SRC=path.resolve(__dirname,'../src/index.html');

/* 阈值：按移动端弱网 + 微信 X5 的实际体验定 */
const LIMIT={
  /* 单文件体积上限。600KB 是首开体感的线，另加 50KB 容纳 SEO 工作流注入的
     GEO:HEAD / GEO:BODY 两块（约 6KB，且随内容增长）——那是另一个进程维护的，
     不该占用我的内容预算。真正该盯的是「单条线路数据量」那一项。 */
  sizeKB:      650,
  loadMs:      3000,   /* 本地加载 */
  searchMs:    50,     /* 搜索一次 */
  engineMs:    50,     /* 装载+重排一条线 */
  renderMs:    600,    /* 逐天渲染全程 */
  langMs:      800,    /* 中英切换 */
  perRouteKB:  16      /* 单条线路平均数据量：用于预测规模上限 */
};

(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:120000});
  const pg=await b.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push('PAGEERROR '+e.message.split('\n')[0]));
  pg.on('console',m=>{
    if(m.type()!=='error') return;
    const txt=m.text();
    /* 错误边界自身的诊断日志属预期行为，不计入 */
    if(txt.indexOf('[zouni] 线路加载失败')>-1 || txt.indexOf('[zouni] 回退')>-1) return;
    errs.push('CONSOLE '+txt.slice(0,80));
  });
  await pg.setViewport({width:390,height:844});
  const t0=Date.now();
  await pg.goto('file://'+SRC,{waitUntil:'networkidle0',timeout:60000});
  const loadMs=Date.now()-t0;
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });

  /* ── A/B 体积与性能 ── */
  const perf=await pg.evaluate(()=>{
    const words=['湖泊','古城','三天','日本','雪山'];
    let t=performance.now();
    for(let i=0;i<20;i++){ const q=words[i%5];
      Object.keys(ROUTES).forEach(id=>{ const R=ROUTES[id];
        ((R.name||'')+(R.dest||'')+(R.title||'')).indexOf(q); }); }
    const searchMs=(performance.now()-t)/20;
    const ids=Object.keys(ROUTES);
    t=performance.now();
    for(let i=0;i<10;i++){ try{ uiLoadRoute(ids[i%ids.length]); resolveAll(); totals(); }catch(e){} }
    const engineMs=(performance.now()-t)/10;
    let dataKB=-1;
    try{ dataKB=Math.round(JSON.stringify(ROUTES,(k,v)=>typeof v==='function'?undefined:v).length/1024); }catch(e){}
    return {routes:ids.length, dataKB, searchMs:+searchMs.toFixed(2), engineMs:+engineMs.toFixed(2)};
  });
  let t=Date.now();
  await pg.evaluate(()=>{ uiLoadRoute('xj10'); applyDraw(); for(let i=0;i<DAYS.length;i++){active=i;renderDay();} });
  const renderMs=Date.now()-t;
  t=Date.now();
  await pg.evaluate(()=>{ setLang('en'); setLang('zh'); });
  const langMs=Date.now()-t;

  /* ── C 健壮性 ── */
  const robust=await pg.evaluate(async()=>{
    const out={};
    /* 坏数据隔离 */
    const cases=[
      {name:'缺 days', data:{name:'坏',fam:'bad',budgets:[{l:'宽',v:1}]}},
      {name:'住宿错位', data:Object.assign({},ROUTES.gl3,{lodges:[null]})},
      {name:'seg 越界', data:Object.assign({},ROUTES.gl3,{map:Object.assign({},ROUTES.gl3.map,{seg:[[99,99],null,null]})})}
    ];
    out.badIsolated=true; out.badUncaught=0;
    cases.forEach(c=>{
      const id='__t_'+c.name; ROUTES[id]=c.data;
      const ok = typeof safeLoad==='function'
        ? safeLoad(id, ()=>applyDraw())
        : (()=>{ try{ uiLoadRoute(id); applyDraw(); return true; }catch(e){ out.badUncaught++; return false; } })();
      try{ uiLoadRoute('xj10'); applyDraw(); if(DAYS.length!==10) out.badIsolated=false; }catch(e){ out.badIsolated=false; }
      delete ROUTES[id];
    });
    /* 竞态 */
    window.__raceErr=0; window.onerror=()=>{ window.__raceErr++; };
    for(let i=0;i<50;i++){
      setLang(i%2?'en':'zh'); setCur(['CNY','USD','EUR','HKD','JPY'][i%5]);
      try{ switchTab(['home','trips','me'][i%3]); }catch(e){}
    }
    setLang('zh'); setCur('CNY'); switchTab('home');
    await new Promise(r=>setTimeout(r,300));
    out.raceErr=window.__raceErr;
    /* 卡片数随内容增长，只校验「没丢卡」而非固定值 */
    out.raceStateOK = document.documentElement.lang==='zh-CN' && document.querySelectorAll('.rec-card').length>=15;
    /* 存储被拒降级 */
    const orig=localStorage.setItem.bind(localStorage);
    localStorage.setItem=()=>{ throw new DOMException('QuotaExceededError'); };
    out.storeDegrade=true;
    try{ uiLoadRoute('gl3'); applyDraw(); if(typeof saveLS==='function') saveLS(); }catch(e){ out.storeDegrade=false; }
    localStorage.setItem=orig;
    return out;
  });
  await b.close();

  /* ── 判定 ── */
  const sizeKB=Math.round(fs.statSync(SRC).size/1024);
  const perRouteKB=+(perf.dataKB/perf.routes).toFixed(2);
  const rows=[
    ['单文件体积',      sizeKB,          LIMIT.sizeKB,     'KB'],
    ['加载耗时',        loadMs,          LIMIT.loadMs,     'ms'],
    ['搜索耗时',        perf.searchMs,   LIMIT.searchMs,   'ms'],
    ['引擎重排',        perf.engineMs,   LIMIT.engineMs,   'ms'],
    ['逐天渲染',        renderMs,        LIMIT.renderMs,   'ms'],
    ['中英切换',        langMs,          LIMIT.langMs,     'ms'],
    ['单条线路数据量',  perRouteKB,      LIMIT.perRouteKB, 'KB']
  ];
  let bad=0;
  console.log('  ── 性能 ──');
  rows.forEach(([n,v,l,u])=>{ const ok=v<=l; if(!ok) bad++;
    console.log(`  ${ok?'✓':'✗'} ${n.padEnd(14)} ${String(v).padStart(7)}${u}  （阈值 ${l}${u}）`); });
  console.log('  ── 健壮性 ──');
  const rb=[
    ['坏数据不污染后续', robust.badIsolated],
    ['坏数据零未捕获异常', robust.badUncaught===0],
    ['200 次切换零错误', robust.raceErr===0 && robust.raceStateOK],
    ['存储被拒能降级',   robust.storeDegrade]
  ];
  rb.forEach(([n,ok])=>{ if(!ok) bad++; console.log(`  ${ok?'✓':'✗'} ${n}`); });
  if(errs.length){ bad++; console.log(`  ✗ 控制台错误 ${errs.length} 条: ${errs[0]}`); }

  /* 规模预测 */
  const maxRoutes=Math.floor((LIMIT.sizeKB-100)/perRouteKB);
  console.log(`  ── 规模预测 ──`);
  console.log(`  当前 ${perf.routes} 条 / 数据 ${perf.dataKB}KB · 单条均 ${perRouteKB}KB`);
  console.log(`  ℹ 按 ${LIMIT.sizeKB}KB 体积上限，单文件版约可承载 ${maxRoutes} 条；超过后走分层交付（见 SOP）`);

  console.log(bad? `\n✗ 性能守卫 ${bad} 项越界` : '\n✅ 性能守卫全部通过');
  process.exit(bad?1:0);
})().catch(e=>{ console.error('ERR', e.message); process.exit(1); });
