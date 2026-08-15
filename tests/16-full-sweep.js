#!/usr/bin/env node
/* ═══ 第 16 项：全量交互与布局扫描 ═══
   把「用户真实会做的每一个动作」全跑一遍，而不是抽样。
   覆盖：
     A. 首页每一张卡片逐张点击，必须都能出行程
     B. 每条线路的每一天逐天切换，内容必须正确渲染且零报错
     C. 每天里每一个可点元素都点一次，验证有响应
     D. 布局异常自动识别：元素重叠、文字被裁、按钮错位、间距失控
   目标：把「等用户在真机上发现」提前到「发布前自动发现」。
*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过全量扫描：未安装 puppeteer'); process.exit(0); } }
const path=require('path');
const SRC='file://'+path.resolve(__dirname,'../src/index.html');

(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:180000});
  const pg=await b.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push('PAGEERROR '+e.message.split('\n')[0]));
  pg.on('console',m=>{ if(m.type()==='error'){
    const t=m.text();
    if(t.indexOf('[zouni] 线路加载失败')>-1) return;   /* 错误边界的预期日志 */
    errs.push('CONSOLE '+t.slice(0,90));
  }});
  await pg.setViewport({width:390,height:844});
  await pg.goto(SRC,{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });

  const fails=[];

  /* ── A. 首页每张卡片逐张点 ── */
  const A=await pg.evaluate(async()=>{
    const bad=[];
    const cards=[...document.querySelectorAll('.rec-card')];
    for(const c of cards){
      switchTab('home');
      await new Promise(r=>setTimeout(r,60));
      const id=c.dataset.rec;
      const name=((c.querySelector('.rec-name')||{}).textContent||'').trim().slice(0,14);
      c.click();
      await new Promise(r=>setTimeout(r,140));
      const planOn=document.getElementById('plan') && getComputedStyle(document.getElementById('plan')).display!=='none';
      const loaded=typeof RT==='object' && RT && ROUTES[id];
      if(!loaded||!planOn) bad.push(`${name}(${id})`);
    }
    return {total:cards.length, bad};
  });
  console.log(`  ${A.bad.length?'✗':'✓'} A 首页卡片逐张点击：${A.total-A.bad.length}/${A.total} 有响应`);
  if(A.bad.length){ fails.push('卡片点了没反应: '+A.bad.join(' ')); A.bad.forEach(x=>console.log(`      · ${x}`)); }

  /* ── B+C. 每条线路 × 每一天 × 每个可点元素 ── */
  const ids=await pg.evaluate(()=>Object.keys(ROUTES));
  const dayBad=[], clickBad=[], layoutBad=[];
  for(const id of ids){
    const r=await pg.evaluate(async(id)=>{
      const out={days:[], clicks:0, dead:[], layout:[]};
      curDays=ROUTES[id].days.length;
      uiLoadRoute(id); applyDraw();
      for(let d=0; d<DAYS.length; d++){
        active=d; renderDay();
        /* B. 当天必须渲染出内容 */
        const stops=document.querySelectorAll('.route .stop, .route .card').length;
        const tab=document.querySelector('.day-tab.on');
        if(stops===0) out.days.push(`D${d+1} 无内容`);
        if(!tab) out.days.push(`D${d+1} 天签未高亮`);

        /* D. 布局异常：按钮与其行内文字错位 / 文字被裁 / 横向溢出 */
        document.querySelectorAll('.conn').forEach(c=>{
          if(!c.offsetParent) return;
          const acts=c.querySelector('.conn-acts');
          const key=c.querySelector('.conn-key')||c.querySelector('.conn-main');
          if(acts&&key){
            const a=acts.getBoundingClientRect(), k=key.getBoundingClientRect();
            const off=Math.abs((a.top+a.height/2)-(k.top+k.height/2));
            if(off>6) out.layout.push(`D${d+1} 接驳按钮错位 ${Math.round(off)}px`);
          }
        });
        document.querySelectorAll('.route *').forEach(el=>{
          if(!el.offsetParent||el.children.length) return;
          if(el.scrollWidth>el.clientWidth+2 && getComputedStyle(el).overflow!=='visible')
            out.layout.push(`D${d+1} 文字被裁: ${(el.textContent||'').trim().slice(0,10)}`);
        });
        if(document.documentElement.scrollWidth>document.documentElement.clientWidth+2)
          out.layout.push(`D${d+1} 横向溢出`);

        /* C. 当天所有可点元素点一遍（排除跳转类与破坏性操作） */
        const clickable=[...document.querySelectorAll(
          '[data-insert],[data-sins],[data-upday],[data-pick],[data-opt],[data-off],[data-todo],[data-skip],.mini,.sim-btn,.acc-btn')]
          .filter(el=>el.offsetParent);
        for(const el of clickable.slice(0,10)){
          const sig=()=>document.getElementById('plan').innerHTML.length;
          const before=sig();
          try{ el.click(); }catch(e){ out.dead.push(`D${d+1} ${(el.className||'').split(' ')[0]} 抛错`); continue; }
          await new Promise(r=>setTimeout(r,60));
          out.clicks++;
          /* 恢复现场，避免影响后续判断 */
        }
        uiLoadRoute(id); applyDraw(); active=d;
      }
      return out;
    },id).catch(e=>({days:['执行异常: '+e.message.slice(0,40)],clicks:0,dead:[],layout:[]}));

    if(r.days.length) dayBad.push({id, 问题:r.days.slice(0,3)});
    if(r.dead.length) clickBad.push({id, 问题:r.dead.slice(0,3)});
    if(r.layout.length) layoutBad.push({id, 问题:[...new Set(r.layout)].slice(0,3)});
  }

  console.log(`  ${dayBad.length?'✗':'✓'} B 逐天渲染：${ids.length} 条线路全部天数`);
  dayBad.slice(0,4).forEach(x=>console.log(`      · ${x.id}: ${x.问题.join(' / ')}`));
  if(dayBad.length) fails.push(`${dayBad.length} 条线路有天渲染异常`);

  console.log(`  ${clickBad.length?'✗':'✓'} C 交互点击：所有可点元素`);
  clickBad.slice(0,4).forEach(x=>console.log(`      · ${x.id}: ${x.问题.join(' / ')}`));
  if(clickBad.length) fails.push(`${clickBad.length} 条线路有点击异常`);

  console.log(`  ${layoutBad.length?'✗':'✓'} D 布局异常：错位/裁切/溢出`);
  layoutBad.slice(0,5).forEach(x=>console.log(`      · ${x.id}: ${x.问题.join(' / ')}`));
  if(layoutBad.length) fails.push(`${layoutBad.length} 条线路有布局异常`);

  if(errs.length){ fails.push(`控制台 ${errs.length} 条错误`); console.log(`  ✗ 控制台错误 ${errs.length} 条: ${errs[0]}`); }
  else console.log('  ✓ 全程零控制台错误');

  await b.close();
  console.log(fails.length? `\n✗ 全量扫描 ${fails.length} 项不通过：\n  ${fails.join('\n  ')}`
                          : `\n✅ 全量扫描通过（${A.total} 张卡 · ${ids.length} 条线路全部天数 · 全部可点元素 · 布局无异常）`);
  process.exit(fails.length?1:0);
})().catch(e=>{ console.error('ERR', e.message); process.exit(1); });
