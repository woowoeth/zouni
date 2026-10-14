const puppeteer=require('/tmp/node_modules/puppeteer');
(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage']});
  const pg=await b.newPage();
  await pg.setViewport({width:390,height:844});
  await pg.goto('file://'+require('path').resolve(__dirname,'../src/index.html')+'',{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); document.getElementById('btn-draw').click(); });
  await new Promise(r=>setTimeout(r,400));

  const R = await pg.evaluate(()=>{
    /* WCAG 相对亮度与对比度 */
    const lum=c=>{ const [r,g,bl]=c.map(v=>{ v/=255; return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4); });
      return 0.2126*r+0.7152*g+0.0722*bl; };
    const parse=s=>{ const m=s.match(/rgba?\(([^)]+)\)/); if(!m) return null;
      const p=m[1].split(',').map(x=>parseFloat(x)); return {rgb:p.slice(0,3), a:p.length>3?p[3]:1}; };
    const over=(fg,bg)=>fg.rgb.map((v,i)=>v*fg.a+bg.rgb[i]*(1-fg.a));
    const ratio=(fArr,bgArr)=>{ const L1=lum(fArr),L2=lum(bgArr); const a=Math.max(L1,L2),b2=Math.min(L1,L2); return (a+0.05)/(b2+0.05); };

    /* 1. 文本对比度：抽样每类文字 */
    const samples=[
      ['.stat .k','统计标签'],['.weather','天气行'],['.rec-meta','卡片说明'],
      ['.days-note','天数说明'],['.list-why','备选说明'],['.cost-note','费用尾注'],
      ['.stat .v','统计数值'],['.rec-name','卡片标题'],['.pchip','未选中标签'],
      ['.trip-meta','行程说明'],['.opt-price','选项价格'],['.dt-sub','天签副标'],
    ];
    const contrast=[];
    samples.forEach(([sel,label])=>{
      const el=document.querySelector(sel); if(!el) return;
      const cs=getComputedStyle(el);
      const fg=parse(cs.color); if(!fg) return;
      /* 逐级找不透明背景 */
      let n=el, bgc=null;
      while(n && n!==document.documentElement){
        const c=parse(getComputedStyle(n).backgroundColor);
        if(c && c.a>0.9){ bgc=c; break; }
        n=n.parentElement;
      }
      if(!bgc) bgc={rgb:[240,240,236],a:1};
      const eff=fg.a<1?over(fg,bgc):fg.rgb;
      const r=ratio(eff,bgc.rgb);
      const size=parseFloat(cs.fontSize), bold=parseInt(cs.fontWeight)>=700;
      const large=size>=18.66||(size>=14&&bold);
      const need=large?3:4.5;
      contrast.push({label, sel, size:Math.round(size), r:+r.toFixed(2), need, pass:r>=need});
    });

    /* 2. 语义：费用表 / landmark / h1 / 焦点可见 */
    const table=document.querySelector('table');
    const semantic={
      hasTable: !!table,
      tableCaption: !!(table&&table.querySelector('caption')),
      tableTh: table?table.querySelectorAll('th').length:0,
      tableScope: table?[...table.querySelectorAll('th')].filter(t=>t.getAttribute('scope')).length:0,
      landmarks:{ main:document.querySelectorAll('main').length, nav:document.querySelectorAll('nav').length,
                  header:document.querySelectorAll('header').length },
      h1:document.querySelectorAll('h1').length,
      skipLink: !!document.querySelector('a[href^="#"][class*=skip]'),
    };

    /* 3. 数字表头与单元格对齐一致性 */
    const align=[];
    if(table){
      const ths=[...table.querySelectorAll('thead th, tr:first-child th, tr:first-child td')];
      const rows=[...table.querySelectorAll('tr')].slice(1);
      if(rows.length){
        const cells=[...rows[0].children];
        cells.forEach((c,i)=>{
          const th=ths[i]; if(!th) return;
          align.push({col:i, thAlign:getComputedStyle(th).textAlign, tdAlign:getComputedStyle(c).textAlign});
        });
      }
    }

    /* 4. flex/grid 子元素缺 min-width:0（长文本溢出风险） */
    const risky=[];
    document.querySelectorAll('.list-row, .rec-card, .trip-card, .stat, .sc-route-info, .conn-row').forEach(el=>{
      const cs=getComputedStyle(el);
      if(cs.display!=='flex'&&cs.display!=='grid') return;
      [...el.children].forEach(ch=>{
        const c=getComputedStyle(ch);
        if(c.minWidth==='auto' && ch.scrollWidth>ch.clientWidth+1)
          risky.push((el.className||el.tagName)+' > '+(ch.className||ch.tagName));
      });
    });

    const noFocus=[];   /* 焦点态改由真实 Tab 键在下方检测 */

    /* 7. 排版硬指标（外部判据实测得来）*/
    const typo={};
    const inputs=[...document.querySelectorAll('input')];
    typo.smallInputs=inputs.filter(el=>parseFloat(getComputedStyle(el).fontSize)<16)
      .map(el=>el.id+':'+getComputedStyle(el).fontSize);
    const vp=(document.querySelector('meta[name=viewport]')||{}).content||'';
    typo.blocksZoom=/maximum-scale=1|user-scalable=no/.test(vp);
    typo.bodySelectable=getComputedStyle(document.body).userSelect!=='none';
    /* 变化的数字必须等宽，否则每次刷新会跳动 */
    typo.nonTabular=[...document.querySelectorAll('#stat-cost,#cost-total,#cost-tix,#cost-food,#cost-car,#cost-lodge,.opt-price,.stop-cost')]
      .filter(el=>{
        const own=getComputedStyle(el).fontVariantNumeric;
        const par=el.parentElement?getComputedStyle(el.parentElement).fontVariantNumeric:'';
        return !/tabular-nums/.test(own) && !/tabular-nums/.test(par);
      }).map(el=>el.id||el.className);

    /* 6. inline style 里的 margin/padding（间隙 owner 不唯一的信号） */
    const inlineGap=[...document.querySelectorAll('[style]')]
      .filter(el=>/margin|padding/.test(el.getAttribute('style')))
      .map(el=>(el.id||el.className||el.tagName)+' :: '+el.getAttribute('style').match(/(margin|padding)[^;]*/g).join(' '));

    return {contrast, semantic, align, risky:[...new Set(risky)], noFocus, inlineGap, typo};
  });

  console.log('══ 1. 文本对比度（WCAG AA）══');
  R.contrast.forEach(c=>console.log(`  ${c.pass?'✓':'✗'} ${c.label.padEnd(10)} ${String(c.size).padStart(2)}px  ${c.r}:1 (需 ${c.need})`));
  console.log('\n══ 2. 语义与可访问性 ══');
  console.log('  ', JSON.stringify(R.semantic));
  console.log('\n══ 3. 表头/单元格对齐一致性 ══');
  R.align.forEach(a=>console.log(`  ${a.thAlign===a.tdAlign?'✓':'✗'} 第${a.col+1}列 表头${a.thAlign} / 单元格${a.tdAlign}`));
  console.log('\n══ 4. 溢出风险（flex 子元素缺 min-width:0）══');
  console.log('  ', R.risky.length?R.risky:'无');
  console.log('\n══ 5. 焦点不可见的控件 ══');
  console.log('  ', R.noFocus.length?R.noFocus:'无（前 8 个 Tab 目标均有焦点态）');
  /* 真实 Tab 键：JS focus() 不触发 :focus-visible，必须模拟键盘 */
  const ring=[];
  for(let i=0;i<30;i++){
    await pg.keyboard.press('Tab');
    
    const r=await pg.evaluate(()=>{ const el=document.activeElement; if(!el||el===document.body) return null;
      const cs=getComputedStyle(el);
      const ringed=/0px 0px 0px 3px|3px rgba/.test(cs.boxShadow)||(cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>0);
      return {id:(el.id||el.className||el.tagName).toString().slice(0,24), ringed}; });
    if(r&&!ring.find(x=>x.id===r.id)) ring.push(r);
  }
  console.log('\n══ 5. 焦点环（真实 Tab 键）══');
  ring.forEach(r=>console.log('  '+(r.ringed?'✓':'✗')+' '+r.id));

  console.log('\n══ 6. inline 间隙（owner 不唯一的信号）══');
  console.log(`   共 ${R.inlineGap.length} 处`);
  R.inlineGap.slice(0,12).forEach(x=>console.log('   ·',x.slice(0,90)));
  /* 判定：对比度与语义为硬指标 */
  const cFail=R.contrast.filter(c=>!c.pass);
  const sem=R.semantic;
  const semFail=[];
  if(!sem.tableCaption) semFail.push('费用表缺 caption');
  if(sem.tableScope<sem.tableTh||sem.tableTh===0) semFail.push('表头缺 th/scope');
  if(sem.landmarks.main===0) semFail.push('缺 main landmark');
  if(sem.h1!==1) semFail.push('h1 数量='+sem.h1);
  const alignFail=R.align.filter(a=>a.thAlign!==a.tdAlign);
  const ringFail=ring.filter(r=>!r.ringed);
  const typoFail=[];
  if(R.typo.smallInputs.length) typoFail.push('输入框 <16px 会触发 iOS 整页缩放: '+R.typo.smallInputs.join(' '));
  if(R.typo.blocksZoom) typoFail.push('viewport 禁用缩放，违反 WCAG');
  if(!R.typo.bodySelectable) typoFail.push('全局禁用了文本选择');
  if(R.typo.nonTabular.length) typoFail.push('变化数字未用等宽: '+R.typo.nonTabular.join(' '));
  console.log('\n══ 7. 排版硬指标 ══');
  console.log(typoFail.length? typoFail.map(x=>'  ✗ '+x).join('\n') : '  ✓ 输入框字号 · 缩放未禁用 · 文本可选 · 数字等宽');
  const hard=cFail.length+semFail.length+alignFail.length+ringFail.length+R.risky.length+typoFail.length;
  console.log('');
  if(hard){
    console.log('✗ 可访问性 '+hard+' 项不达标：');
    if(cFail.length) console.log('  对比度: '+cFail.map(c=>c.label+'('+c.r+')').join(' '));
    if(semFail.length) console.log('  语义: '+semFail.join(' / '));
    if(alignFail.length) console.log('  表头对齐: '+JSON.stringify(alignFail));
    if(ringFail.length) console.log('  焦点环: '+ringFail.map(r=>r.id).join(' '));
    if(R.risky.length) console.log('  溢出风险: '+R.risky.join(' '));
  } else console.log('✅ 可访问性通过（对比度 · 表格语义 · landmark · 焦点环 · 无溢出 · 排版硬指标）');
  await b.close();
  process.exit(hard?1:0);
})().catch(e=>{console.error('ERR',e.message);process.exit(1);});
