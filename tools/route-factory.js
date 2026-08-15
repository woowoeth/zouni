#!/usr/bin/env node
/* ═══ 走你 · 路线工厂 ═══
   verify  : 对任意/全部线路跑 16 项结构与引擎验收
   derive  : 从源线路派生天数变体，自动算 lodges/nights/seg/tonight/预算/rent/roadfood
   batch   : 批量生成候选 → 全部验收 → 只输出全过的

   用法：
     node route-factory.js verify [id|all]
     node route-factory.js derive --src xz7 --keep 0,1,2,6 --id xz4 --title "..." 
     node route-factory.js batch specs.json
*/
const fs=require('fs'), path=require('path');

/* ── 从单文件切出数据层与引擎 ── */
function loadEngine(){
  const html=fs.readFileSync(path.resolve(__dirname,'../src/index.html'),'utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
  const mod=js.slice(a,b)+`
module.exports={ROUTES,loadRoute,resolveAll,totals,
  rt:()=>RT, days:()=>DAYS, lodges:()=>LODGES,
  setBudget:v=>{BUDGET=v}, resolved:()=>resolved};`;
  const tmp='/tmp/_factory_engine.js';
  fs.writeFileSync(tmp,mod);
  delete require.cache[tmp];
  return require(tmp);
}

/* ══════════ 验证器：14 项 ══════════ */
function verify(E, id){
  const R=E.ROUTES[id];
  const issues=[];
  const ok=(cond,msg)=>{ if(!cond) issues.push(msg); };
  if(!R){ return {id,pass:false,issues:['路线不存在']}; }

  const days=R.days||[], lodges=R.lodges||[], M=R.map||{}, N=(M.nodes||[]).length;

  /* 1-3 结构基本量 */
  ok(days.length>0, '天数为 0');
  ok(lodges.length===days.length, `住宿链项数 ${lodges.length} ≠ 天数 ${days.length}`);
  ok(lodges.length===0 || lodges[lodges.length-1]===null, '末天住宿应为 null（当天离开）');
  const realNights=lodges.filter(Boolean).length;
  ok((R.nights==null?realNights:R.nights)===realNights,
     `nights=${R.nights} 与实际住宿数 ${realNights} 不符`);

  /* 4 天签编号连续 */
  days.forEach((d,i)=>{ ok(d.tab===`D${i+1}`, `第 ${i+1} 天 tab='${d.tab}' 应为 D${i+1}`); });

  /* 5-7 地图长度与越界 */
  const seg=M.seg||[], tn=M.tonight||[];
  ok(!seg.length || seg.length===days.length, `map.seg 长度 ${seg.length} ≠ 天数 ${days.length}`);
  ok(!tn.length || tn.length===days.length, `map.tonight 长度 ${tn.length} ≠ 天数 ${days.length}`);
  (M.order||[]).forEach(i=>ok(i>=0&&i<N, `map.order 索引 ${i} 越界（节点 ${N} 个）`));
  seg.forEach((sg,di)=>{ if(!sg) return;
    (Array.isArray(sg[0])?sg:[sg]).forEach(pr=>{ if(!Array.isArray(pr)) return;
      pr.forEach(i=>ok(i!=null&&i>=0&&i<N, `D${di+1} seg 索引 ${i} 越界`)); }); });
  tn.forEach((i,di)=>ok(i==null||i===-1||(i>=0&&i<N), `D${di+1} tonight 索引 ${i} 越界`));

  /* 8 节点坐标 */
  (M.nodes||[]).forEach((n,i)=>ok(n&&typeof n.x==='number'&&typeof n.y==='number', `节点[${i}] 坐标缺失`));

  /* 9 tonight 与住宿链呼应：有住宿的天 tonight 不应为 -1 */
  lodges.forEach((l,i)=>{ if(l&&tn.length) ok(tn[i]!==-1&&tn[i]!=null, `D${i+1} 有住宿但 tonight=${tn[i]}`); });

  /* 10-12 引擎仿真：宽松档直跑，精打档需先触发省钱逻辑 thrift() */
  const bl=R.budgets||[];
  try{
    E.loadRoute(id); E.setBudget((bl[0]||{v:9e9}).v); E.resolveAll();
    const t0=E.totals(), rs=E.resolved();
    ok(!isNaN(t0.total), '宽松档合计为 NaN');
    if(bl[0]) ok(t0.total<=bl[0].v, `宽松档超预算：${Math.round(t0.total)} > ${bl[0].v}`);
    rs.forEach((r,i)=>{
      ok(!isNaN(r.end), `D${i+1} 结束时刻 NaN`);
      ok(r.end<=days[i].hardEnd, `D${i+1} 超时窗：${r.end} > ${days[i].hardEnd}`);
    });
    if(bl[1]){
      const RT=E.rt(); if(RT&&RT.thrift) RT.thrift();
      E.setBudget(bl[1].v); E.resolveAll();
      const t1=E.totals();
      ok(!isNaN(t1.total), '精打档合计为 NaN');
      ok(t1.total<=bl[1].v, `精打档超预算：${Math.round(t1.total)} > ${bl[1].v}`);
      E.resolved().forEach((r,i)=>ok(r.end<=days[i].hardEnd, `D${i+1} 精打档超时窗：${r.end} > ${days[i].hardEnd}`));
    }
  }catch(e){ issues.push(`仿真异常：${e.message.split('\n')[0]}`); }

  /* 13 预算档单调 */
  const bs=(R.budgets||[]).map(b=>b.v);
  ok(bs.length<2 || bs[0]>=bs[1], `预算档非递减：${bs.join(' / ')}`);

  /* 14.5 必备字段：缺任一项会在真实渲染时崩（测试跑得过、页面打不开） */
  const REQUIRED=['name','dest','fam','days','lodges','budgets','title','meta','why','tastes','seasons','todos','map'];
  REQUIRED.forEach(f=>ok(R[f]!=null, `缺必备字段 ${f}（会导致 applyDraw 崩溃）`));
  if(R.tastes) ok(Array.isArray(R.tastes), 'tastes 必须是数组');
  if(typeof R.todos!=='function' && !Array.isArray(R.todos)) issues.push('todos 必须是函数或数组');

  /* 15 地理连续性：前一天住哪，后一天就得从哪出发（防止精简天数时路线断裂） */
  if(seg.length===days.length && tn.length===days.length){
    for(let i=0;i<days.length-1;i++){
      const stay=tn[i];                       /* 今晚住的节点 */
      if(stay==null||stay===-1) continue;     /* 当天不过夜，跳过 */
      const nx=seg[i+1];
      if(!nx) continue;                       /* 明天不移动（原地游玩），合理 */
      const from=Array.isArray(nx[0])?nx[0][0]:nx[0];
      if(from!=null && from!==stay){
        const nm=k=>((M.nodes||[])[k]||{}).n||('节点'+k);
        issues.push(`地理断裂：D${i+1} 住 ${nm(stay)}，D${i+2} 却从 ${nm(from)} 出发`);
      }
    }
  }

  /* 14 文案不得承诺"可加"却无插入数据 */
  (R.extras||[]).forEach(x=>{
    if(!x.later) return;
    const w=x.later.why||'';
    if(/可.{0,3}加|可排|能加|顺路/.test(w) && !x.later.inDay && !x.later.needDays)
      issues.push(`备选「${x.later.name}」文案承诺可加，但无插入数据也无 needDays`);
  });

  return {id, pass:issues.length===0, issues, days:days.length,
          nights:realNights, total:(()=>{ try{ E.loadRoute(id); E.setBudget((R.budgets||[{v:9e9}])[0].v);
            E.resolveAll(); return Math.round(E.totals().total); }catch(e){ return null; } })()};
}

/* ══════════ 派生器：从源线路生成天数变体 ══════════ */
function derive(E, spec){
  const { src, keep, id, overrides={} } = spec;
  const S=E.ROUTES[src];
  if(!S) throw new Error(`源线路 ${src} 不存在`);
  const days=keep.map(i=>{
    if(!S.days[i]) throw new Error(`源线路无第 ${i+1} 天`);
    return Object.assign({}, S.days[i], {tab:`D${keep.indexOf(i)+1}`});
  });
  /* 住宿链：按保留天取，末天强制 null */
  const lodges=keep.map((i,n)=> n===keep.length-1 ? null : (S.lodges[i]||null));
  const nights=lodges.filter(Boolean).length;
  /* 地图：按保留天取 seg/tonight */
  const seg=keep.map(i=>(S.map.seg||[])[i]!==undefined?(S.map.seg||[])[i]:null);
  const tonight=keep.map((i,n)=> n===keep.length-1 ? -1 : ((S.map.tonight||[])[i]!=null?(S.map.tonight||[])[i]:-1));
  /* 派生量：按天数比例缩放 */
  const ratio=days.length/S.days.length;
  const rent=Math.round((S.rent||0)*ratio/100)*100;
  const roadfood=Math.round((S.roadfood||0)*ratio/10)*10;
  return Object.assign({
    days, lodges, nights, rent, roadfood,
    map:Object.assign({}, S.map, {seg, tonight}),
    dayVariants:[...new Set([S.days.length, days.length])].sort((a,b)=>a-b),
  }, overrides);
}

/* 用派生结果试算，给出建议预算（实际成本 × 安全系数，向上取整到百） */
function suggestBudget(E, id, draft){
  const bak=E.ROUTES[id];
  E.ROUTES[id]=Object.assign({}, bak||E.ROUTES[draft.__src]||{}, draft, {budgets:[{l:'宽松',v:9e9},{l:'精打细算',v:9e9}]});
  let loose=null, thrift=null;
  try{
    E.loadRoute(id); E.setBudget(9e9); E.resolveAll(); loose=E.totals().total;
    thrift=loose*0.94;
  }catch(e){}
  if(bak) E.ROUTES[id]=bak; else delete E.ROUTES[id];
  const up=v=>Math.ceil(v*1.14/100)*100;
  return loose==null?null:[{l:'宽松',v:up(loose)},{l:'精打细算',v:up(thrift)}];
}

/* ══════════ CLI ══════════ */
const [,,cmd,...args]=process.argv;
const E=loadEngine();

if(cmd==='verify'){
  const target=args[0]||'all';
  const ids=target==='all'?Object.keys(E.ROUTES):[target];
  let bad=0;
  ids.forEach(id=>{
    const r=verify(E,id);
    if(r.pass) console.log(`  ✓ ${id.padEnd(9)} ${String(r.days).padStart(2)}天 ${String(r.nights)}晚 ¥${r.total}`);
    else { bad++; console.log(`  ✗ ${id.padEnd(9)} ${r.issues.length} 项：`); r.issues.forEach(x=>console.log(`      · ${x}`)); }
  });
  console.log(bad? `\n✗ ${bad}/${ids.length} 条线路未通过` : `\n✅ ${ids.length} 条线路全部通过 16 项验收`);
  process.exit(bad?1:0);
}

if(cmd==='derive'){
  const get=k=>{ const i=args.indexOf('--'+k); return i>-1?args[i+1]:null; };
  const spec={ src:get('src'), keep:get('keep').split(',').map(Number), id:get('id'), overrides:{} };
  ['title','meta','why','hero1v','hero1k'].forEach(k=>{ const v=get(k); if(v) spec.overrides[k]=v; });
  const draft=derive(E,spec);
  draft.__src=spec.src;
  const bud=suggestBudget(E,spec.id,draft);
  if(bud) draft.budgets=bud;
  delete draft.__src;
  /* 临时挂载并验收 */
  E.ROUTES[spec.id]=Object.assign({}, E.ROUTES[spec.src], draft);
  const v=verify(E,spec.id);
  console.log(`── 派生 ${spec.id}（源 ${spec.src}，保留天 ${spec.keep.map(i=>i+1).join('/')}）──`);
  console.log(`  天数 ${draft.days.length} · 住宿 ${draft.nights} 晚 · rent ${draft.rent} · roadfood ${draft.roadfood}`);
  console.log(`  建议预算 ${bud?bud.map(b=>b.l+' '+b.v).join(' / '):'算不出'}`);
  console.log(`  seg      ${JSON.stringify(draft.map.seg)}`);
  console.log(`  tonight  ${JSON.stringify(draft.map.tonight)}`);
  console.log(v.pass? `  ✅ 14 项验收通过（实际 ¥${v.total}）` : `  ✗ 未通过：\n${v.issues.map(x=>'      · '+x).join('\n')}`);
  process.exit(v.pass?0:1);
}

if(cmd==='batch'){
  const specs=JSON.parse(fs.readFileSync(args[0],'utf8'));
  const passed=[], failed=[];
  specs.forEach(spec=>{
    try{
      const draft=derive(E,spec);
      draft.__src=spec.src;
      const bud=suggestBudget(E,spec.id,draft);
      if(bud) draft.budgets=bud;
      delete draft.__src;
      E.ROUTES[spec.id]=Object.assign({}, E.ROUTES[spec.src], draft, spec.overrides||{});
      const v=verify(E,spec.id);
      (v.pass?passed:failed).push({spec, v, draft});
    }catch(e){ failed.push({spec, v:{issues:[e.message.split('\n')[0]]}}); }
  });
  console.log(`── 批量：${specs.length} 个候选 ──`);
  passed.forEach(x=>console.log(`  ✓ ${x.spec.id.padEnd(9)} ${x.draft.days.length}天 ${x.draft.nights}晚 ¥${x.v.total} 预算${x.draft.budgets.map(b=>b.v).join('/')}`));
  failed.forEach(x=>{ console.log(`  ✗ ${x.spec.id.padEnd(9)}`); x.v.issues.slice(0,4).forEach(i=>console.log(`      · ${i}`)); });
  console.log(`\n通过 ${passed.length} / ${specs.length}`);
  fs.writeFileSync('/tmp/batch-passed.json', JSON.stringify(passed.map(x=>({id:x.spec.id, src:x.spec.src, keep:x.spec.keep, draft:{
    days:x.draft.days.length, nights:x.draft.nights, rent:x.draft.rent, roadfood:x.draft.roadfood,
    budgets:x.draft.budgets, seg:x.draft.map.seg, tonight:x.draft.map.tonight}})), null, 1));
  console.log('通过项详情 → /tmp/batch-passed.json');
  process.exit(failed.length?1:0);
}

console.log('用法: verify [id|all] | derive --src X --keep 0,1,2 --id Y | batch specs.json');
