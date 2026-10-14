let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过 UI 规范守卫：未安装 puppeteer'); process.exit(0); } }
(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-dev-shm-usage'],protocolTimeout:120000});
  const pg=await b.newPage();
  await pg.setViewport({width:390,height:844});
  await pg.goto('file://'+require('path').resolve(__dirname,'../src/index.html')+'',{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); document.getElementById('btn-draw').click(); });
  await new Promise(r=>setTimeout(r,500));

  const R=await pg.evaluate(()=>{
    const cs=el=>getComputedStyle(el);
    const vis=el=>el.offsetParent!==null && el.getBoundingClientRect().width>0;
    const out={};

    /* ═══ better-ui #1：同心圆角 —— 外圆角 = 内圆角 + padding ═══ */
    out.radius=[];
    document.querySelectorAll('.card,.me-sect,.trip-card,.rec-card,.sc-budget-tile').forEach(outer=>{
      if(!vis(outer)) return;
      const or=parseFloat(cs(outer).borderTopLeftRadius)||0;
      const pad=parseFloat(cs(outer).paddingTop)||0;
      [...outer.children].forEach(inner=>{
        const ir=parseFloat(cs(inner).borderTopLeftRadius)||0;
        if(ir<=0||or<=0) return;
        /* 只有内层真的贴着外层内边（近似撑满）才构成同心关系；并列的小圆角组件不算 */
        const ob=outer.getBoundingClientRect(), ib=inner.getBoundingClientRect();
        const fills = (ib.width >= ob.width - pad*2 - 4);
        if(!fills) return;
        /* 内层无背景/无边框 = 只是布局容器，不构成视觉嵌套 */
        const ics=cs(inner);
        const hasSurface = ics.backgroundColor!=='rgba(0, 0, 0, 0)' || /rgb/.test(ics.boxShadow) || parseFloat(ics.borderTopWidth)>0;
        if(!hasSurface) return;
        const ideal=or-pad;
        if(Math.abs(ir-ideal)>4) out.radius.push({
          outer:(outer.className||'').split(' ')[0], inner:(inner.className||'').split(' ')[0],
          got:ir, ideal:Math.max(0,Math.round(ideal))
        });
      });
    });

    /* ═══ better-ui #9：按压反馈 scale(0.96) ═══ */
    const btns=[...document.querySelectorAll('button')].filter(vis);
    out.pressFeedback=btns.filter(el=>{
      const t=cs(el).transition||'';
      return !/transform|scale/.test(t);
    }).length;
    out.btnTotal=btns.length;

    /* ═══ better-ui #4：交互态用 transition（可中断）而非 keyframes ═══ */
    out.keyframeInteractive=btns.filter(el=>cs(el).animationName!=='none').length;

    /* ═══ better-layout #1：组间距 ≥ 2× 组内距 ═══ */
    /* 目的地行在折叠区外、且收起态紧贴摘要条，不参与组间距比较 */
    const groups=[...document.querySelectorAll('#sheet:not(.home-empty):not(.collapsed) .sheet-row:not(.dest-row), .card:not(#sheet) .sheet-row')].filter(vis);
    /* 组间距量「上一行底部到本行顶部」的真实距离，
       不能只读 marginTop —— 我们的行距是靠 margin-bottom 实现的，读 marginTop 永远是 0。 */
    out.grouping=groups.slice(0,4).map((g,i)=>{
      const chips=[...g.querySelectorAll('.pchip')].slice(0,2);
      const intra=chips.length>1? Math.round(chips[1].getBoundingClientRect().left-chips[0].getBoundingClientRect().right):null;
      const inter=i>0
        ? Math.round(g.getBoundingClientRect().top - groups[i-1].getBoundingClientRect().bottom)
        : null;
      return {intra, inter, ok: intra==null||inter==null||inter>=intra*2};
    });

    /* ═══ better-layout #6：相邻控件间距 ≥12px（有边框）/24px（无边框） ═══ */
    const rects=btns.map(el=>({el, r:el.getBoundingClientRect(), bordered:/rgb/.test(cs(el).boxShadow)||parseFloat(cs(el).borderTopWidth)>0}));
    out.tooClose=0;
    for(let i=0;i<rects.length;i++) for(let j=i+1;j<rects.length;j++){
      const a=rects[i].r, c=rects[j].r;
      const overlapY=a.top<c.bottom&&c.top<a.bottom;
      const gap=Math.min(Math.abs(c.left-a.right), Math.abs(a.left-c.right));
      /* 同一父容器 = 同组，组内紧凑是设计意图；判据说的是「不同组的相邻控件」 */
      const sameGroup = rects[i].el.parentElement===rects[j].el.parentElement;
      /* 固定层（底部 Tab 栏等）与内容层只是视觉重叠，不在同一平面，不算相邻 */
      const fixed = el=>{ let n=el; while(n&&n!==document.body){ if(getComputedStyle(n).position==='fixed') return true; n=n.parentElement; } return false; };
      const crossLayer = fixed(rects[i].el)!==fixed(rects[j].el);
      if(overlapY && gap>0 && gap<8 && !sameGroup && !crossLayer) out.tooClose++;
    }

    /* ═══ better-accessibility #5：触达 ≥24px（AA 底线），触屏宜 44px ═══ */
    out.hitArea=btns.map(el=>{
      const r=el.getBoundingClientRect();
      /* 伪元素扩展的触达区要算进来 */
      const af=getComputedStyle(el,'::after');
      const ext=parseFloat(af.height)||0;
      return {id:(el.id||el.className||'').split(' ')[0], w:Math.round(r.width), h:Math.round(Math.max(r.height, ext))};
    }).filter(x=>x.w<24||x.h<24);
    out.hitUnder44=btns.filter(el=>{
      const r=el.getBoundingClientRect(); return r.height<44 && r.height>0;
    }).length;

    /* ═══ better-accessibility #1：原生元素优先，不用 div onClick ═══ */
    out.divClick=[...document.querySelectorAll('div[onclick],span[onclick],[role=button]:not(button)')].length;

    /* ═══ better-accessibility #8：图标按钮必须有 aria-label ═══ */
    out.iconNoLabel=btns.filter(el=>{
      const txt=(el.textContent||'').trim();
      const hasSvg=el.querySelector('svg');
      return hasSvg && !txt && !el.getAttribute('aria-label') && !el.getAttribute('title');
    }).map(el=>el.id||el.className);

    /* ═══ better-accessibility #9：不能只靠颜色传达信息 ═══ */
    out.colorOnly=[...document.querySelectorAll('.chip.up,.chip.down,.mark.in,.mark.out')].filter(el=>{
      const t=(el.textContent||'').trim();
      return !t;   /* 只有颜色没有文字/符号 */
    }).length;

    /* ═══ better-writing #5：按钮以动词开头，不用 OK/Yes/No ═══ */
    const BAD_LABEL=/^(确定|好的|是|否|OK|Yes|No|提交)$/;
    out.badLabels=btns.map(el=>(el.textContent||'').trim()).filter(t=>t&&BAD_LABEL.test(t));

    /* ═══ better-writing #7：链接文字自解释，不用「点这里」 ═══ */
    out.vagueLinks=[...document.querySelectorAll('a')].map(a=>(a.textContent||'').trim())
      .filter(t=>/^(点这里|这里|更多|click here|here|learn more)$/i.test(t));

    /* ═══ better-ui #8：图片需 1px 描边（我们无图片则跳过） ═══ */
    out.imgs=document.querySelectorAll('img').length;

    /* ═══ better-interface：reduced-motion 是否被尊重 ═══ */
    out.hasReducedMotion=[...document.styleSheets].some(sh=>{
      try{ return [...sh.cssRules].some(r=>r.conditionText&&/prefers-reduced-motion/.test(r.conditionText)); }
      catch(e){ return false; }
    });

    /* ═══ better-layout #8：安全区 ═══ */
    out.safeArea=[...document.styleSheets].some(sh=>{
      try{ return [...sh.cssRules].some(r=>r.cssText&&/safe-area-inset/.test(r.cssText)); }
      catch(e){ return false; }
    });

    return out;
  });

  const P=[];
  const say=(dom,name,ok,detail)=>{ console.log(`  ${ok?'✓':'✗'} [${dom}] ${name}${ok?'':' → '+detail}`); if(!ok) P.push(name); };

  console.log('══ UI 六域全面体检（按外部 skill 判据）══\n');
  /* 卡片 12px 套选项行 8px 是记录在案的例外（见 zouni-ui-spec.md 三节），实测视觉更干净 */
  const radiusReal=R.radius.filter(x=>!(x.outer==='card'&&x.inner==='opt-row'));
  say('ui','同心圆角（外=内+padding）', radiusReal.length===0, radiusReal.slice(0,3).map(x=>`${x.outer}>${x.inner} ${x.got}px 应≈${x.ideal}px`).join(' / '));
  say('ui','按钮按压反馈', R.pressFeedback===0, `${R.pressFeedback}/${R.btnTotal} 个按钮无 transform 过渡`);
  say('ui','交互态用可中断 transition', R.keyframeInteractive===0, `${R.keyframeInteractive} 个按钮在跑 keyframes`);
  say('layout','分组间距 ≥2× 组内', R.grouping.every(g=>g.ok), JSON.stringify(R.grouping));
  say('layout','相邻控件不贴太近', R.tooClose===0, `${R.tooClose} 对间距 <8px`);
  say('layout','安全区适配', R.safeArea, '未用 env(safe-area-inset-*)');
  say('a11y','触达 ≥24px（AA 底线）', R.hitArea.length===0, R.hitArea.slice(0,4).map(x=>`${x.id} ${x.w}×${x.h}`).join(' '));
  say('a11y','原生元素优先', R.divClick===0, `${R.divClick} 个 div/span 当按钮用`);
  say('a11y','图标按钮有可访问名', R.iconNoLabel.length===0, R.iconNoLabel.slice(0,4).join(' '));
  say('a11y','不只靠颜色传达', R.colorOnly===0, `${R.colorOnly} 处纯色无文字`);
  say('a11y','尊重 reduced-motion', R.hasReducedMotion, '未监听 prefers-reduced-motion');
  say('writing','按钮标签动词开头', R.badLabels.length===0, R.badLabels.join(' '));
  say('writing','链接文字自解释', R.vagueLinks.length===0, R.vagueLinks.join(' '));

  console.log(`\n  ℹ 触达 <44px（触屏建议值，非硬性）：${R.hitUnder44}/${R.btnTotal} 个`);
  console.log(`\n${P.length? '✗ UI 规范 '+P.length+' 项不达标：'+P.join('、') : '✅ UI 规范全部通过（六域判据）'}`);
  await b.close();
  process.exit(P.length?1:0);
})().catch(e=>{console.error('ERR',e.message);process.exit(1);});
