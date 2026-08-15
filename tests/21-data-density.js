#!/usr/bin/env node
/* ═══ 功能数据密度扫描 ═══
   雨天方案的教训：UI 做好了，但全站只有 4 处数据 —— 56 条里 52 条点开是空的。
   这类「有壳没料」的功能，测试全绿也查不出来，因为它没报错，只是没内容。

   这个扫描器把每个依赖数据的功能列出来，算真实覆盖率：
     ≥80%  健康
     40-80% 偏薄，要补
     <40%  空壳，要么补料要么撤掉 UI
*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过：未安装 puppeteer'); process.exit(0); } }
const path=require('path');
const SRC='file://'+path.resolve(__dirname,'../src/index.html');

(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:240000});
  const pg=await b.newPage();
  await pg.setViewport({width:390,height:844});
  await pg.goto(SRC,{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });

  const R=await pg.evaluate(async()=>{
    const ids=Object.keys(ROUTES);
    const fams={};
    ids.forEach(id=>{ fams[ROUTES[id].fam||id]=id; });
    const famIds=Object.values(fams);
    const out={};

    /* 1. 备选点：要么能加进当天（inserts），要么能用 +1 天排成新一天（EXTRA_POOL）。
       两条路都没有才叫空壳 —— 文案现在会如实说明是哪一种。 */
    let hasExtraPath=0;
    famIds.forEach(id=>{
      const ins=Object.keys(ROUTES[id].inserts||{}).length;
      const pool=(typeof EXTRA_POOL!=='undefined' && (EXTRA_POOL[ROUTES[id].fam]||[]).length)||0;
      if(ins||pool) hasExtraPath++;
    });
    out['备选点有真实去处']={有:hasExtraPath, 总:famIds.length, 单位:'族'};

    /* 2. 备选池（+1 天用） */
    let hasPool=0;
    famIds.forEach(id=>{ const f=ROUTES[id].fam;
      if(typeof EXTRA_POOL!=='undefined' && (EXTRA_POOL[f]||[]).length>=2) hasPool++; });
    out['+1 天备选池 ≥2 个']={有:hasPool, 总:famIds.length, 单位:'族'};

    /* 3. 雨天方案（刚修的） */
    let rainDays=0, allDays=0;
    for(const id of famIds){
      curDays=ROUTES[id].days.length;
      try{ uiLoadRoute(id); applyDraw(); }catch(e){ continue; }
      for(let d=0; d<DAYS.length; d++){
        allDays++;
        mods[d].rain=true; resolveAll();
        const rr=resolved[d];
        if(rr.sched.some(e=>e.s.rainFlag||e.s.swapped)||rr.alted) rainDays++;
        mods[d].rain=false; resolveAll();
      }
    }
    out['雨天方案有内容']={有:rainDays, 总:allDays, 单位:'天'};

    /* 4. 二选一站点
       注意：没有 opts 的天不会露出空选择器（有才显示），
       所以低覆盖不算「空壳」，只是「不是每天都有得选」——这是合理的。
       真正要查的是：**声明了有选择，但点开是空的**。 */
    let optClaimed=0, optReal=0;
    famIds.forEach(id=>{
      (ROUTES[id].days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
        if(!s.opts) return;
        optClaimed++;
        if(Array.isArray(s.opts) && s.opts.length>=2) optReal++;
      }));
    });
    out['二选一声明了就有内容']={有:optReal, 总:Math.max(1,optClaimed), 单位:'处'};

    /* 5. 季节提示 */
    let hasSeason=0;
    famIds.forEach(id=>{ if((ROUTES[id].seasons||[]).length>=2) hasSeason++; });
    out['季节提示 ≥2 条']={有:hasSeason, 总:famIds.length, 单位:'族'};

    /* 6. 待办直达链接 */
    let todoTotal=0, todoUrl=0, todoNeedUrl=0;
    for(const id of famIds){
      curDays=ROUTES[id].days.length;
      try{ uiLoadRoute(id); applyDraw(); }catch(e){ continue; }
      const td=typeof RT.todos==='function'? RT.todos():[];
      td.forEach(t=>{ todoTotal++;
        if(t.url) todoUrl++;
        else if(/预约|官网|购票|订票|办证|抢票|放票/.test(String(t.text))) todoNeedUrl++; });
    }
    out['待办该有链接的已有']={有:todoUrl, 总:todoUrl+todoNeedUrl, 单位:'条'};

    /* 7. 站点导航词 */
    let stopTotal=0, stopQ=0;
    famIds.forEach(id=>{
      (ROUTES[id].days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
        if(!s.k) return; stopTotal++; if(s.q) stopQ++; }));
    });
    out['站点有导航词']={有:stopQ, 总:stopTotal, 单位:'站'};

    /* 8. 住宿二选一 —— 同理，没 opts 的晚不显示选择器，低覆盖不是问题。
       查的是：声明了 opts 就必须真有两个可选。 */
    let lodgeClaimed=0, lodgeReal=0;
    famIds.forEach(id=>{
      (ROUTES[id].lodges||[]).forEach(L=>{ if(!L||!L.opts) return;
        lodgeClaimed++;
        if(Array.isArray(L.opts) && L.opts.length>=2) lodgeReal++; });
    });
    out['住宿二选一有内容']={有:lodgeReal, 总:Math.max(1,lodgeClaimed), 单位:'处'};

    /* 8b. 每条线至少有一处让用户选（否则全程无得选，体验僵硬） */
    let hasAnyChoice=0;
    famIds.forEach(id=>{
      const R2=ROUTES[id];
      const s1=(R2.days||[]).some(d=>(d.stops||[]).some(s=>s.opts));
      const s2=(R2.lodges||[]).some(L=>L&&L.opts);
      if(s1||s2) hasAnyChoice++;
    });
    out['每条线至少一处可选']={有:hasAnyChoice, 总:famIds.length, 单位:'族'};

    /* 9. 封面图（首页卡片） */
    const cards=[...document.querySelectorAll('.rec-card')].map(c=>c.dataset.rec);
    let hasCover=0;
    cards.forEach(id=>{ if(typeof COVERS!=='undefined' && COVERS.img[id]) hasCover++; });
    out['首页卡片有封面']={有:hasCover, 总:cards.length, 单位:'卡'};

    /* 10. 大交通提示 */
    let hasArrive=0;
    famIds.forEach(id=>{ if(typeof arriveNoteOf==='function' && arriveNoteOf(ROUTES[id])) hasArrive++; });
    out['大交通参考价']={有:hasArrive, 总:famIds.length, 单位:'族'};

    /* 11. 双语卡片文案 */
    let enCards=0;
    cards.forEach(id=>{
      try{ const en=I18N.en.cards&&I18N.en.cards[id]; if(en) enCards++; }catch(e){}
    });
    out['卡片有英文文案']={有:enCards, 总:cards.length, 单位:'卡'};

    /* 12. 站点有 vibe 描述（不是干巴巴的名字） */
    let vibeN=0, vibeTotal=0;
    famIds.forEach(id=>{
      (ROUTES[id].days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
        if(!s.k) return; vibeTotal++; if(s.vibe && s.vibe.length>=10) vibeN++; }));
    });
    out['站点有场景描述']={有:vibeN, 总:vibeTotal, 单位:'站'};

    /* 13. 站点有必看/必吃提示 */
    let mustN=0;
    famIds.forEach(id=>{
      (ROUTES[id].days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
        if(!s.k) return; if(s.must && s.must.length>=2) mustN++; }));
    });
    out['站点有必看提示']={有:mustN, 总:vibeTotal, 单位:'站'};

    /* 14. 图标不重复 */
    const icons={};
    famIds.forEach(id=>{ const i=crIcon(ROUTES[id]); icons[i]=(icons[i]||0)+1; });
    const uniqIcons=Object.keys(icons).length;
    out['族图标不重复']={有:uniqIcons, 总:famIds.length, 单位:'族'};

    return out;
  });

  await b.close();

  console.log('══ 功能数据密度扫描 ══\n');
  const rows=Object.entries(R).map(([k,v])=>({
    name:k, has:v.有, all:v.总, unit:v.单位,
    pct: v.总? Math.round(v.有/v.总*100) : 0
  })).sort((a,b)=>a.pct-b.pct);

  let hollow=0, thin=0;
  rows.forEach(r=>{
    const tag = r.pct>=80? '✓ 健康' : (r.pct>=40? '⚠ 偏薄' : '✗ 空壳');
    if(r.pct<40) hollow++; else if(r.pct<80) thin++;
    console.log(`  ${tag}  ${String(r.pct).padStart(3)}%  ${r.name.padEnd(18)} ${r.has}/${r.all} ${r.unit}`);
  });

  console.log(`\n  空壳 ${hollow} 项 · 偏薄 ${thin} 项 · 健康 ${rows.length-hollow-thin} 项`);
  if(hollow) console.log('  空壳的要么补料，要么撤掉 UI —— 有壳没料比没有更糟');
  process.exit(hollow>0?1:0);
})().catch(e=>{ console.error('ERR', e.message); process.exit(1); });
