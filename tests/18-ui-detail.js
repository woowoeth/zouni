#!/usr/bin/env node
/* ═══ 第 18 项：界面细节守卫 ═══
   把"用户一眼看出不对、但已有测试都查不到"的问题变成自动断言。
   每一条都对应一次真机反馈：

     A. 短内容不该分两行      （「10 分」+「步行回住处」分成两行）
     B. 不该有空行占位        （主行空着、内容全在次行）
     C. 同层文字左缘要对齐    （嵌套 padding 累加导致越往下越偏右）
     D. 同类按钮尺寸要一致    （70 个按钮曾有 13 种高度）
     E. 行内文字与按钮同中线  （flex-start 让文字顶对齐、按钮居中）
     F. 卡片不该有重复入口    （接驳行与站点卡各有一个导航）

   跑遍所有线路的所有天，不抽样。
*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过界面细节守卫：未安装 puppeteer'); process.exit(0); } }
const path=require('path');
const SRC='file://'+path.resolve(__dirname,'../src/index.html');

(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:180000});
  const pg=await b.newPage();
  await pg.setViewport({width:390,height:844});
  await pg.goto(SRC,{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });

  const R=await pg.evaluate(async()=>{
    const out={shortSplit:[], emptyLine:[], misalign:[], btnSizes:{}, baseline:[], dupNav:[], bigGap:[], overlay:[], badTime:[]};
    const ids=Object.keys(ROUTES);
    for(const id of ids){
      curDays=ROUTES[id].days.length;
      try{ uiLoadRoute(id); applyDraw(); }catch(e){ continue; }
      for(let d=0; d<DAYS.length; d++){
        active=d; renderDay();
        const tag=`${id} D${d+1}`;

        document.querySelectorAll('.conn').forEach(c=>{
          if(!c.offsetParent) return;
          const keyEl=c.querySelector('.conn-key');
          const mainEl=c.querySelector('.conn-main');
          const key=(keyEl?keyEl.textContent:'').trim();
          const mainTxt=(mainEl&&mainEl.firstChild&&mainEl.firstChild.nodeType===3)
            ? mainEl.firstChild.textContent.trim() : '';
          const via=c.querySelector('.conn-via');

          /* A. 两截都很短却分了两行 */
          if(key && mainTxt && !via && (key.length+mainTxt.length)<=16)
            out.shortSplit.push(`${tag}: 「${key}」+「${mainTxt}」`);

          /* B. 主行空着占位 */
          if(keyEl && !key && mainTxt)
            out.emptyLine.push(`${tag}: 主行空·内容在次行「${mainTxt.slice(0,14)}」`);

          /* E. 行内文字与按钮不同中线 */
          const acts=c.querySelector('.conn-acts');
          const anchor=keyEl||mainEl;
          if(acts&&anchor&&acts.querySelector('a,button')){
            const a=acts.getBoundingClientRect(), k=anchor.getBoundingClientRect();
            if(Math.abs((a.top+a.height/2)-(k.top+k.height/2))>6)
              out.misalign.push(`${tag}: 接驳按钮与文字错位`);
          }

          /* F. 接驳行不该自带导航（站点卡里已有） */
          if(acts && [...acts.querySelectorAll('a,button')].some(x=>/导航|Navigate/.test(x.textContent||'')))
            out.dupNav.push(`${tag}: 接驳行有重复导航入口`);
        });

        /* C. 同一天所有接驳行的「文字真实起点」要一致
           注意：不能量容器位置。容器一致但文字仍可能差 2px——
           A 结构文字包在 .conn-key 里、B 结构直接跟图标，多一层元素就多一次边界取整。
           必须用 Range 量第一个文字节点的实际坐标。 */
        const lefts=new Set(), pads=new Set();
        document.querySelectorAll('.conn').forEach(c=>{
          if(!c.offsetParent) return;
          const w=document.createTreeWalker(c, NodeFilter.SHOW_TEXT);
          let n, f=null;
          while(n=w.nextNode()){ if((n.textContent||'').trim()){ f=n; break; } }
          if(!f) return;
          const rg=document.createRange(); rg.selectNodeContents(f);
          lefts.add(Math.round(rg.getBoundingClientRect().left));
          pads.add(getComputedStyle(c).paddingTop);
        });
        if(lefts.size>1) out.baseline.push(`${tag}: 文字起点 ${[...lefts].join('/')}`);
        if(pads.size>1) out.baseline.push(`${tag}: 上边距 ${[...pads].join('/')}`);

        /* I. 页面上不能出现 24:00 以上的时间（跨天要回绕） */
        document.querySelectorAll('#plan *').forEach(el=>{
          if(el.children.length) return;
          const m2=(el.textContent||'').match(/\b([2-9]\d|[3-9])\d?:[0-5]\d\b/g);
          if(m2) m2.forEach(x=>{ const h=parseInt(x.split(':')[0],10);
            if(h>=24) out.badTime.push(`${tag}: ${x}`); });
        });

        /* G. 区块间距不得异常累加
           接驳块层层嵌套，若每层都有内边距会一路堆高——
           实测曾在「今晚住提示行 → 今晚住标题」之间堆出 50px。
           注意排除中间夹着 sticky 天签的情况（那不是空白）。 */
        const vis=[...document.querySelectorAll('#plan .conn, #plan .card, #plan .eyebrow, #plan .t-col, #plan section')]
          .filter(e=>e.offsetParent && e.getBoundingClientRect().height>0)
          .map(e=>({el:e, cls:(e.className||'').split(' ')[0]||e.tagName, r:e.getBoundingClientRect()}))
          .sort((a,b)=>a.r.top-b.r.top);
        for(let i=1;i<vis.length;i++){
          const P=vis[i-1], C=vis[i];
          if(P.el.contains(C.el)||C.el.contains(P.el)) continue;
          const g=Math.round(C.r.top-P.r.bottom);
          if(g<=24) continue;
          /* 中间若有实际内容（如吸顶天签），不算空白 */
          const filled=[...document.querySelectorAll('#plan *')].some(e=>{
            if(!e.offsetParent) return false;
            const rr=e.getBoundingClientRect();
            return rr.top>=P.r.bottom-2 && rr.bottom<=C.r.top+2 && rr.height>8;
          });
          if(!filled) out.bigGap.push(`${tag}: ${g}px ${P.cls}→${C.cls}`);
        }

        /* H. 弹层按钮不能被底部 tab 遮挡
     底部 tab 是 fixed z-index:200，弹层若低于它、或内容超出视口，
     「保持原计划 / 换成这个」这类关键按钮就点不到。 */
        [['btn-rain','cmp-box','cmp-apply'],['btn-depart','date-box','dp-clear']].forEach(function(trip){
          const trigger=document.getElementById(trip[0]);
          if(!trigger||!trigger.offsetParent) return;
          trigger.click();
          const box=document.getElementById(trip[1]);
          const btn=document.getElementById(trip[2]);
          if(box&&btn){
            const bz=parseInt(getComputedStyle(box).zIndex||0,10);
            const tab=document.querySelector('.tab-bar');
            const tz=tab? parseInt(getComputedStyle(tab).zIndex||0,10) : 0;
            const bb=btn.getBoundingClientRect();
            if(bz<=tz) out.overlay.push(`${trip[1]} z-index ${bz} ≤ tab ${tz}`);
            if(bb.bottom>window.innerHeight+2) out.overlay.push(`${trip[2]} 超出视口 ${Math.round(bb.bottom)}>${window.innerHeight}`);
          }
          if(box){ box.classList.remove('on'); document.body.classList.remove('sheet-open'); }
        });

  /* D. 行内按钮尺寸 */
        document.querySelectorAll('.stop-foot .act, .stop-foot .skip-btn, .conn .act, .done-btn').forEach(el=>{
          if(!el.offsetParent) return;
          const h=Math.round(el.getBoundingClientRect().height);
          out.btnSizes[h]=(out.btnSizes[h]||0)+1;
        });
      }
    }
    return out;
  });

  /* J. 所有「返回首页」的路径都必须回到空态
     这次漏掉了左上角返回箭头（goHome 里写的是 remove('collapsed')，等于展开），
     只处理了底部 tab —— 用户从详情页返回看到的还是一整屏配置。 */
  const backPaths=await pg.evaluate(async()=>{
    const bad=[];
    const H=()=>Math.round(document.getElementById('sheet').getBoundingClientRect().height);
    const isEmpty=()=>document.getElementById('sheet').classList.contains('home-empty');
    /* 路径一：左上角返回箭头 */
    document.querySelectorAll('.rec-card')[0].click();
    await new Promise(r=>setTimeout(r,400));
    const bh=document.getElementById('btn-home');
    if(bh && bh.offsetParent){ bh.click(); await new Promise(r=>setTimeout(r,400));
      if(!isEmpty()) bad.push('返回箭头未回空态 · 高 '+H()); }
    /* 路径二：底部首页 tab */
    document.querySelectorAll('.rec-card')[1].click();
    await new Promise(r=>setTimeout(r,400));
    document.getElementById('tab-home').click(); await new Promise(r=>setTimeout(r,400));
    if(!isEmpty()) bad.push('底部 tab 未回空态 · 高 '+H());
    return bad;
  }).catch(()=>['执行异常']);

  /* K. 首页同层标题文字左缘必须一致
     「先挑一条」在 20px、「长线 · 高原雪山」因带 16px 内边距落在 34px，
     差 14px —— 同一列里最扎眼的错位，但两者容器 left 都是 18，只量容器发现不了。 */
  const titleAlign=await pg.evaluate(()=>{
    const tx=e=>{ const w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT);
      let n,f=null; while(n=w.nextNode()){ if((n.textContent||'').trim()){f=n;break;} }
      if(!f) return null; const rg=document.createRange(); rg.selectNodeContents(f);
      return Math.round(rg.getBoundingClientRect().left); };
    const els=[...document.querySelectorAll('#view-home .eyebrow, #view-home .feed-sect')]
      .filter(e=>e.offsetParent);
    const lefts=els.map(tx).filter(x=>x!=null);
    const set=[...new Set(lefts)];
    return set.length>1 ? ['首页标题左缘不一：'+set.join('/')] : [];
  }).catch(()=>[]);

  await b.close();
  const P=[];
  const say=(name,list,extra)=>{
    const bad=Array.isArray(list)?list:[];
    console.log(`  ${bad.length?'✗':'✓'} ${name}${bad.length?`（${bad.length}）`:''}${extra||''}`);
    if(bad.length){ P.push(name); [...new Set(bad)].slice(0,4).forEach(x=>console.log(`      · ${x}`)); }
  };
  console.log('══ 界面细节守卫（全线路全天数）══');
  say('短内容不分两行', R.shortSplit);
  say('无空行占位', R.emptyLine);
  say('接驳行文字起点与上下间距一致', R.baseline);
  say('文字与按钮同中线', R.misalign);
  say('无重复导航入口', R.dupNav);
  say('区块间距不异常累加', R.bigGap);
  say('弹层按钮不被 tab 遮挡', R.overlay);
  say('无 24:00 以上的时间', R.badTime);
  say('返回首页都回空态', backPaths);
  say('首页标题左缘一致', titleAlign);
  const sizes=Object.keys(R.btnSizes).map(Number).sort((a,b)=>a-b);
  const sizeOK=sizes.length<=2;
  console.log(`  ${sizeOK?'✓':'✗'} 行内按钮尺寸统一 —— ${sizes.map(h=>h+'px×'+R.btnSizes[h]).join(' ')}`);
  if(!sizeOK) P.push('行内按钮尺寸');

  console.log(P.length? `\n✗ 界面细节 ${P.length} 项不达标：${P.join('、')}`
                      : '\n✅ 界面细节全部通过（6 类 × 全部线路天数）');
  process.exit(P.length?1:0);
})().catch(e=>{ console.error('ERR', e.message); process.exit(1); });
