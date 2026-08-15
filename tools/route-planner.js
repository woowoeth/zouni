#!/usr/bin/env node
/* ═══ 走你 · 行程规划器 ═══
   输入意图（去哪些城市、几天、什么偏好、预算档），输出声明（交给编译器编译成完整行程）。

   与编译器的分工：
     规划器 = 决定「每天玩什么」        ← 本文件（带时窗与预算约束的选点）
     编译器 = 把决定变成完整数据结构    ← route-compiler.js
     工厂   = 验收 15 项                ← route-factory.js

   用法：
     node route-planner.js plan intent.json
     node route-planner.js demo            # 内置示例：桂林 5 天 · 拍照+山水
*/
const fs=require('fs'), path=require('path');
const DIR=path.resolve(__dirname);
const LIB=JSON.parse(fs.readFileSync(DIR+'/lib-extracted.json','utf8'));
const META=JSON.parse(fs.readFileSync(DIR+'/poi-meta.json','utf8'));

/* 一天的可用时间（分钟）与转场缓冲 */
const DAY_START=540, DAY_END=1290, SWITCH_BUFFER=25;
const COMFORT_END=1110;   /* 18:30 舒适收工线：装到这里就留给下一天，避免一天塞满、后几天空转 */
/* 用餐窗口：吃饭不是景点，必须落在正确时段 */
const MEALS=[
  {id:'lunch',  from:690,  to:840,  label:'午餐'},   /* 11:30–14:00 */
  {id:'dinner', from:1050, to:1230, label:'晚餐'}    /* 17:30–20:30 */
];
const TIME_ORDER={dawn:0, morning:1, null:2, afternoon:3, sunset:4, night:5};

/* ── 打分：优先级 + 偏好匹配；必看项永远优先 ── */
function score(poi, tastes){
  const prioW=[30,18,8][poi.prio!=null?Math.min(poi.prio,2):2];      /* prio 0=必看 */
  const match=(poi.tags||[]).filter(t=>tastes.includes(t)).length;
  return prioW + match*12;
}

/* ── 单日选点：时窗内贪心装填，必看优先，按时段排序 ── */
function packDay(pool, tastes, budgetPerDay, opts={}){
  const start=opts.start!=null?opts.start:DAY_START;
  const end=opts.end!=null?opts.end:DAY_END;
  const preMin=opts.preMin||0;
  const comfort=opts.comfortEnd!=null?opts.comfortEnd:COMFORT_END;
  let cursor=start+preMin, spent=0;
  const picked=[];

  const usable=pool.filter(p=>p.type!=='logistics' && p.dur>0);
  /* 餐饮单独拿出来，按用餐窗口安排；其余按景点排 */
  const foods=usable.filter(p=>p.cat==='food');
  const sights=usable.filter(p=>p.cat!=='food');

  const must=sights.filter(p=>p.prio===0);
  const rest=sights.filter(p=>p.prio!==0)
    .sort((a,b)=>(score(b,tastes)/Math.max(b.dur,15))-(score(a,tastes)/Math.max(a.dur,15)));

  must.forEach(p=>{
    const need=p.dur+SWITCH_BUFFER;
    if(cursor+need>end) return;
    picked.push(p); cursor+=need; spent+=p.cost;
  });
  rest.forEach(p=>{
    const need=p.dur+SWITCH_BUFFER;
    if(cursor+need>comfort) return;
    if(budgetPerDay!=null && spent+p.cost>budgetPerDay) return;
    picked.push(p); cursor+=need; spent+=p.cost;
  });

  /* ── 餐饮：每个窗口最多一家，按偏好挑（爱吃的选贵的好的，否则选性价比） ── */
  const foodFirst=tastes.includes('food');
  const meals=[];
  MEALS.forEach(w=>{
    if(cursor<w.from && picked.length===0) return;          /* 当天还没开始就到不了这个窗口 */
    if(start+preMin>w.to) return;                            /* 窗口已过（当天出发太晚） */
    const cand=foods.filter(f=>!meals.includes(f))
      .sort((a,b)=> foodFirst ? (b.cost-a.cost) : (score(b,tastes)-score(a,tastes)));
    const pick=cand[0];
    if(!pick) return;
    if(budgetPerDay!=null && spent+pick.cost>budgetPerDay*1.15) return;   /* 吃饭略放宽 */
    meals.push(pick); spent+=pick.cost; cursor+=Math.min(pick.dur,90)*0.5; /* 用餐与游玩部分重叠 */
  });
  const all=[...picked, ...meals];

  /* ── 排序：先按时段（日出→上午→午餐→下午→日落→晚餐→夜） ── */
  const slot=p=>{
    if(p.cat==='food'){
      /* 餐饮插进对应窗口：优先按 bestTime，否则午餐在中间、晚餐靠后 */
      if(p.bestTime==='night') return 5.5;
      return all.filter(x=>x.cat==='food').indexOf(p)===0 ? 2.5 : 4.5;
    }
    return TIME_ORDER[p.bestTime]!=null?TIME_ORDER[p.bestTime]:2;
  };
  all.sort((a,b)=>slot(a)-slot(b));
  return {picked:all, sights:picked, meals, endTime:cursor, spent};
}

/* ── 住宿：按偏好与预算选，不是永远取第一个 ── */
function pickLodge(cityId, tastes, budgetPerDay, LIBCITY){
  const c=LIBCITY[cityId];
  if(!c || !c.lodges.length) return null;
  const sorted=[...c.lodges].sort((a,b)=>(a.price||0)-(b.price||0));
  if(sorted.length===1) return {index:0, opts:false};
  /* 躺平型 → 好房；预算紧 → 便宜；否则给二选一让用户自己定 */
  if(tastes.includes('chill')) return {index:c.lodges.indexOf(sorted[sorted.length-1]), opts:false};
  if(budgetPerDay!=null && sorted[0].price>budgetPerDay*0.45) return {index:c.lodges.indexOf(sorted[0]), opts:false};
  return {index:c.lodges.indexOf(sorted[0]), opts:true};   /* 二选一：贵的在前、便宜的在后 */
}

/* ── 天数分配：按各城 POI 总时长估算，移动日单独占 ── */
function allocDays(cities, totalDays, tastes){
  const load=cities.map(cid=>{
    const pool=Object.entries(META).filter(([k,p])=>p.city===cid && p.type!=='logistics');
    const hours=pool.reduce((s,[k,p])=>s+p.dur,0)/60;
    const fit=pool.reduce((s,[k,p])=>s+((p.tags||[]).filter(t=>tastes.includes(t)).length),0);
    return {cid, hours, fit, pool:pool.length};
  });
  const moveDays=Math.max(0, cities.length-1);      /* 城市间移动天 */
  const stayDays=Math.max(cities.length, totalDays-0);
  /* 按内容量加权分配剩余天数 */
  const totalHours=load.reduce((s,x)=>s+x.hours,0)||1;
  let left=totalDays;
  const alloc=load.map((x,i)=>{
    /* 每城至少 1 天；内容不足 5 小时的城市不给第 2 天 */
    const want=Math.max(1, Math.round(totalDays*x.hours/totalHours));
    const cap=Math.max(1, Math.ceil(x.hours/5));
    return {...x, days:Math.min(want, cap)};
  });
  /* 修正到恰好 totalDays */
  let sum=alloc.reduce((s,x)=>s+x.days,0);
  while(sum>totalDays){ const i=alloc.findIndex(x=>x.days>1); if(i<0) break; alloc[i].days--; sum--; }
  while(sum<totalDays){ const i=alloc.reduce((bi,x,ix)=>x.hours>alloc[bi].hours?ix:bi,0); alloc[i].days++; sum++; }
  return alloc;
}

/* ── 可行性预检：库里的内容够不够撑起请求的天数 ── */
function feasibility(cities, totalDays, tastes){
  const HOURS_PER_DAY=5.5;                    /* 一天合理的游玩内容量（不含赶路） */
  const per=cities.map(cid=>{
    const pool=Object.entries(META).filter(([k,p])=>p.city===cid && p.type!=='logistics' && p.dur>0);
    return {cid, name:(LIB.CITY[cid]||{}).name||cid, n:pool.length,
            hours:pool.reduce((s,[k,p])=>s+p.dur,0)/60};
  });
  const totalHours=per.reduce((s,x)=>s+x.hours,0);
  const moveHours=Math.max(0,cities.length-1)*2.5;         /* 城市间赶路粗估 */
  const supportDays=Math.max(1, Math.round((totalHours+moveHours)/HOURS_PER_DAY));
  const gapHours=Math.max(0, totalDays*HOURS_PER_DAY - moveHours - totalHours);
  return {per, totalHours, supportDays, gapHours,
          ok: supportDays>=totalDays,
          advice: supportDays>=totalDays
            ? null
            : `库里内容只够 ${supportDays} 天。要排 ${totalDays} 天，需补约 ${gapHours.toFixed(1)} 小时内容（约 ${Math.ceil(gapHours/2)} 个站点）`};
}

/* ── 主规划 ── */
function plan(intent){
  const {cities, days:totalDays, tastes=[], budget, id, fam, loop=true}=intent;
  const feas=feasibility(cities, totalDays, tastes);
  const alloc=allocDays(cities, totalDays, tastes);
  const budgetPerDay = budget? Math.round(budget/totalDays) : null;
  const out=[], report=[];
  let dayNo=0;
  alloc.forEach((a,ci)=>{
    const pool=Object.entries(META).filter(([k,p])=>p.city===a.cid)
      .map(([k,p])=>Object.assign({id:k},p));
    const logistics=pool.filter(p=>p.type==='logistics');
    let remaining=pool.filter(p=>p.type!=='logistics');
    for(let d=0; d<a.days; d++){
      dayNo++;
      const isArrival = d===0 && ci>0;                 /* 从上一城移动过来 */
      const from = isArrival? alloc[ci-1].cid : a.cid;
      const legKey=Object.keys(LIB.LEG).find(k=>{
        const c1=LIB.CITY[from], c2=LIB.CITY[a.cid];
        return c1&&c2&&LIB.LEG[k].conn.includes(c1.name)&&LIB.LEG[k].conn.includes(c2.name);
      });
      const preMin = isArrival ? (legKey? LIB.LEG[legKey].min : 180) : 0;
      const r=packDay(remaining, tastes, budgetPerDay, {preMin});
      /* 首日补提车类功能站点 */
      const stops=[...(dayNo===1?logistics.filter(p=>/提车|验车|抵达/.test(p.name)).map(p=>p.id):[]),
                   ...r.picked.map(p=>p.id)];
      remaining=remaining.filter(p=>!r.picked.includes(p));
      const isLastDay = dayNo===totalDays;
      const lg = isLastDay? null : pickLodge(a.cid, tastes, budgetPerDay, LIB.CITY);
      out.push({
        from: isArrival? from : (dayNo===1? cities[0] : a.cid),
        to:   isArrival? a.cid : (isLastDay && loop ? cities[0] : a.cid),
        stay: isLastDay? null : a.cid,
        lodge: lg? lg.index : 0, lodgeOpts: lg? lg.opts : false,
        stops,
        start: DAY_START, hardEnd: DAY_END,
        sub: `${stops.length} 站 · ${Math.round((r.endTime-DAY_START)/60)} 小时`,
        leg: legKey? Object.assign({},LIB.LEG[legKey]) : undefined
      });
      const lgName = lg && LIB.CITY[a.cid] ? (lg.opts? '二选一：'+LIB.CITY[a.cid].lodges.slice(0,2).map(x=>x.city+'¥'+x.price).join(' / ')
                       : (LIB.CITY[a.cid].lodges[lg.index]||{}).city+' ¥'+(LIB.CITY[a.cid].lodges[lg.index]||{}).price) : '—';
      report.push({day:dayNo, city:LIB.CITY[a.cid]?LIB.CITY[a.cid].name:a.cid,
        picked:r.sights.map(p=>`${p.name}(${p.dur}分${p.cost?'¥'+p.cost:''})`),
        meals:r.meals.map(p=>`${p.name}(¥${p.cost})`),
        lodge:lgName, endTime:r.endTime, spent:r.spent, left:remaining.length});
    }
  });
  return {spec:{id, fam, loop, plan:out}, report, alloc, feas};
}

/* ══ CLI ══ */
const [,,cmd,arg]=process.argv;
const demo={
  id:'gl5', fam:'gl', days:5, tastes:['photo','nature'], budget:2200,
  cities:['gl:0','gl:1','gl:3']     /* 桂林 · 龙脊 · 阳朔 */
};
const intent = cmd==='demo' ? demo : JSON.parse(fs.readFileSync(arg,'utf8'));
const r=plan(intent);

console.log(`══ 规划 ${intent.id}：${intent.days} 天 · 偏好 [${(intent.tastes||[]).join(',')}] · 预算 ¥${intent.budget||'不限'} ══`);
console.log('── 可行性 ──');
r.feas.per.forEach(x=>console.log(`  ${x.name.padEnd(8)} ${String(x.n).padStart(2)} 站 · ${x.hours.toFixed(1)} 小时内容`));
console.log(`  合计 ${r.feas.totalHours.toFixed(1)} 小时 → 支撑 ${r.feas.supportDays} 天`);
if(!r.feas.ok) console.log(`  ⚠ ${r.feas.advice}`);
else console.log(`  ✓ 内容量足够`);
console.log('── 天数分配 ──');
r.alloc.forEach(a=>console.log(`  ${(LIB.CITY[a.cid]?LIB.CITY[a.cid].name:a.cid).padEnd(8)} ${a.days} 天（站点 ${a.pool} 个 · 内容 ${a.hours.toFixed(1)} 小时 · 偏好命中 ${a.fit}）`));
console.log('── 每日安排 ──');
r.report.forEach(x=>{
  console.log(`  D${x.day} ${x.city.padEnd(8)} 收工 ${Math.floor(x.endTime/60)}:${String(x.endTime%60).padStart(2,'0')} · ¥${x.spent} · 剩余未排 ${x.left} 个`);
  x.picked.forEach(p=>console.log(`      景 ${p}`));
  (x.meals||[]).forEach(p=>console.log(`      食 ${p}`));
  console.log(`      宿 ${x.lodge}`);
});
const empty=r.report.filter(x=>x.picked.length===0);
if(empty.length){
  console.log(`\n✗ ${empty.length} 天排不出内容（D${empty.map(x=>x.day).join(',D')}）— 不产出声明`);
  console.log(`   ${r.feas.advice||'请减少天数或补充站点数据'}`);
  process.exit(1);
}
fs.writeFileSync('/tmp/planned-'+intent.id+'.json', JSON.stringify(r.spec,null,1));
console.log(`\n→ 声明已写入 /tmp/planned-${intent.id}.json（可交给 route-compiler.js 编译）`);
