/* ═══ 交叉一致性体检 ═══
   已有测试查的是「有没有违反已知规则」，这个脚本查的是「同类信息之间对不对得上」。
   三亚统计区重复那种问题，单条看都合法，只有横向比对才暴露。
*/
const fs=require('fs');
const path=require('path');
const html=fs.readFileSync(path.resolve(__dirname,'../src/index.html'),'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/_cross.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
const {ROUTES}=require('/tmp/_cross.js');

const P=[];
const flag=(name,list)=>{ if(list.length){ P.push(name); console.log(`  ✗ ${name}（${list.length}）`); list.slice(0,6).forEach(x=>console.log(`      · ${x}`)); } else console.log(`  ✓ ${name}`); };

/* 1. 统计区 hero 与天数格重复（成都犯过、三亚又犯） */
flag('统计区首格与天数格重复', Object.entries(ROUTES).filter(([id,R])=>{
  const h=(R.hero1v||'').replace(/<[^>]+>/g,'').trim();
  return h && new RegExp(`^${R.days.length}\\s*天?$`).test(h);
}).map(([id,R])=>`${id}: hero="${(R.hero1v||'').replace(/<[^>]+>/g,'')}" 与「${R.days.length}天」重复`));

/* 2. 卡片标价 vs 实际精打档预算 */
const cardPrices={};
html.replace(/data-rec="([\w-]+)"\s+data-price="(\d+)"/g,(m,id,p)=>{ cardPrices[id]=+p; });
flag('卡片标价与精打档预算不符', Object.entries(cardPrices).filter(([id,p])=>{
  const R=ROUTES[id]; if(!R||!R.budgets||!R.budgets[1]) return false;
  return Math.abs(p-R.budgets[1].v)>1;
}).map(([id,p])=>`${id}: 卡片 ¥${p} vs 预算 ¥${ROUTES[id].budgets[1].v}`));

/* 3. 卡片天数区间 vs 该族实际方案 */
const fams={};
Object.entries(ROUTES).forEach(([id,R])=>{ (fams[R.fam]=fams[R.fam]||[]).push(R.days.length); });
const cardNames={};
html.replace(/data-rec="([\w-]+)"[\s\S]{0,200}?rec-name">([^<]+)</g,(m,id,n)=>{ cardNames[id]=n.trim(); });
flag('卡片天数区间与实际方案不符', Object.entries(cardNames).filter(([id,n])=>{
  const R=ROUTES[id]; if(!R) return false;
  const avail=[...new Set(fams[R.fam])].sort((a,b)=>a-b);
  const m=n.match(/(\d+)(?:[–-](\d+))?\s*天/);
  if(!m) return false;
  const lo=+m[1], hi=m[2]?+m[2]:+m[1];
  return lo!==avail[0] || hi!==avail[avail.length-1];
}).map(([id,n])=>`${id}: 卡片「${n}」 vs 实际 ${[...new Set(fams[ROUTES[id].fam])].sort((a,b)=>a-b).join('/')}天`));

/* 4. meta 里的天数/晚数 vs 实际 */
flag('meta 天数晚数与实际不符', Object.entries(ROUTES).filter(([id,R])=>{
  const m=(R.meta||'').match(/(\d+)\s*天\s*(\d+)\s*晚/);
  if(!m) return false;
  const nights=(R.lodges||[]).filter(Boolean).length;
  return +m[1]!==R.days.length || +m[2]!==nights;
}).map(([id,R])=>`${id}: meta「${R.meta}」 vs 实际 ${R.days.length}天${(R.lodges||[]).filter(Boolean).length}晚`));

/* 5. title 里的天数 vs 实际 */
flag('title 天数与实际不符', Object.entries(ROUTES).filter(([id,R])=>{
  const m=(R.title||'').match(/(\d+)\s*天/);
  return m && +m[1]!==R.days.length;
}).map(([id,R])=>`${id}: title「${R.title}」 vs 实际 ${R.days.length} 天`));

/* 6. tastes 里 apply 引用的 sels key 必须真实存在 */
const selBad=[];
Object.entries(ROUTES).forEach(([id,R])=>{
  const ids=new Set();
  (R.days||[]).forEach(d=>(d.stops||[]).forEach(st=>{ if(st.id) ids.add(st.id); }));
  (R.tastes||[]).forEach(t=>{
    const src=(t.apply||'').toString();
    const m=src.match(/sels\['([\w-]+)'\]/g)||[];
    m.forEach(x=>{ const k=x.match(/'([\w-]+)'/)[1]; if(!ids.has(k)) selBad.push(`${id}: tastes 引用 sels['${k}'] 但无此二选一站点`); });
  });
  Object.keys(R.defSels||{}).forEach(k=>{ if(!ids.has(k)) selBad.push(`${id}: defSels['${k}'] 无对应站点`); });
});
flag('口味/默认选项引用了不存在的站点', selBad);

/* 7. 同一族内 title 雷同（复制粘贴没改） */
const titleDup=[];
Object.entries(fams).forEach(([f,_])=>{
  const rs=Object.entries(ROUTES).filter(([id,R])=>R.fam===f);
  const seen={};
  rs.forEach(([id,R])=>{ if(seen[R.title]) titleDup.push(`${f}: ${seen[R.title]} 与 ${id} 标题相同「${R.title}」`); else seen[R.title]=id; });
});
flag('同族内标题重复', titleDup);

/* 8. 文案里的占位符与半成品 */
const placeholder=[];
Object.entries(ROUTES).forEach(([id,R])=>{
  const text=JSON.stringify(R,(k,v)=>typeof v==='function'?undefined:v);
  ['TODO','待补','xxx','XXX','undefined','null 分','¥0/晚','待定'].forEach(w=>{
    if(text.includes(w)) placeholder.push(`${id}: 含「${w}」`);
  });
});
flag('文案含占位符或半成品', [...new Set(placeholder)]);

/* 9. 住宿价格为 0 或缺失 */
const lodgeBad=[];
Object.entries(ROUTES).forEach(([id,R])=>{
  (R.lodges||[]).forEach((l,i)=>{
    if(!l) return;
    const opts=l.opts||[l];
    opts.forEach(o=>{ if(!o.price||o.price<=0) lodgeBad.push(`${id} D${i+1}: ${o.city} 价格 ${o.price}`);
                      if(!o.city) lodgeBad.push(`${id} D${i+1}: 住宿缺城市名`); });
  });
});
flag('住宿价格缺失或为零', lodgeBad);

/* 10. 每天必须有至少一个非功能性站点 */
const emptyDay=[];
Object.entries(ROUTES).forEach(([id,R])=>{
  (R.days||[]).forEach((d,i)=>{
    /* dur:0 且有 openMin 的是弹性站点（引擎按剩余时间伸缩），不是空站 */
    const real=(d.stops||[]).filter(s=>s.k && (s.dur>0 || s.openMin>0 || (s.opts&&s.opts.length))).length;
    /* 纯赶路日（长途转场，pre 里就是几百公里）没有景点是合理的，
       只有「既无站点又无长途接驳」才是真的空 */
    const preKm=(d.pre&&d.pre.km)||0;
    const connKm=(d.stops||[]).reduce((n,x)=>n+(x.km||0),0);
    const isTransferDay = (preKm+connKm)>=150;
    if(real===0 && !isTransferDay) emptyDay.push(`${id} D${i+1} ${d.name}: 无实质站点且非转场日`);
  });
});
flag('存在没有实质内容的天', emptyDay);

/* 11. 时窗：出发时间必须早于硬结束 */
const timeBad=[];
Object.entries(ROUTES).forEach(([id,R])=>{
  (R.days||[]).forEach((d,i)=>{
    if(d.start>=d.hardEnd) timeBad.push(`${id} D${i+1}: start ${d.start} ≥ hardEnd ${d.hardEnd}`);
    /* 看日出的天必须摸黑出发（泰山 4:00、元阳 5:30），这是刻意的不是错误 */
    const isSunrise=/日出|sunrise/i.test((d.name||'')+(d.sub||''))
      || (d.stops||[]).some(x=>/日出|云海/.test(x.name||''));
    if(isSunrise && d.start>=200) return;
    if(d.start<300||d.start>900) timeBad.push(`${id} D${i+1}: 出发时间 ${Math.floor(d.start/60)}:${String(d.start%60).padStart(2,'0')} 不合常理`);
  });
});
flag('时窗设置异常', timeBad);

/* 11.5 同一站点在多条线路里的数据必须一致
   省份多线是常态（四川已有 4 条），同一个地方被不同线路引用时，
   名称/时长/价格若各写一套，用户切线路会看到矛盾信息。 */
const stopUse={};
Object.entries(ROUTES).forEach(([id,R])=>{
  (R.days||[]).forEach(d=>(d.stops||[]).forEach(st=>{
    if(!st.k||!st.dur) return;
    (stopUse[st.k]=stopUse[st.k]||[]).push({id, name:st.name, dur:st.dur, cost:st.cost||0});
  }));
});
const inconsistent=[];
Object.entries(stopUse).forEach(([k,uses])=>{
  if(uses.length<2) return;
  const names=[...new Set(uses.map(u=>u.name))];
  const durs=[...new Set(uses.map(u=>u.dur))];
  const costs=[...new Set(uses.map(u=>u.cost))];
  if(names.length>1) inconsistent.push(`${k} 名称不一：${names.join(' / ')}`);
  /* 同族天数变体之间时长可以不同（长天数版更宽松），跨族才算问题 */
  const fams=[...new Set(uses.map(u=>(ROUTES[u.id]||{}).fam))];
  if(durs.length>1 && fams.length>1) inconsistent.push(`${k} 跨族时长不一：${durs.join('/')}分（${uses.map(u=>u.id).join(',')}）`);
  if(costs.length>1) inconsistent.push(`${k} 价格不一：${costs.join('/')}（${uses.map(u=>u.id).join(',')}）`);
});
flag('跨线路同名站点数据一致', inconsistent);

/* 12. 双语卡片文案是否成对 —— 真实结构是 I18N.zh.cards / I18N.en.cards */
function cardIds(marker){
  const i=js.indexOf(marker);
  if(i<0) return null;
  const seg=js.slice(i, js.indexOf('\n};', i));
  return new Set((seg.match(/^\s*([\w-]+):\[/gm)||[]).map(x=>x.trim().replace(':[','')));
}
const zhIds=cardIds('I18N.zh.cards={'), enIds=cardIds('I18N.en.cards={');
if(!zhIds||!enIds){
  P.push('双语卡片结构未找到');
  console.log('  ✗ 双语卡片结构未找到（检测器需更新）');
}else{
  const missEn=[...zhIds].filter(x=>!enIds.has(x));
  const missZh=[...enIds].filter(x=>!zhIds.has(x));
  flag('中文卡片缺对应英文', missEn.map(x=>`${x} 无英文文案`));
  flag('英文卡片缺对应中文', missZh.map(x=>`${x} 无中文文案`));
  /* 卡片 id 也必须是真实线路 */
  flag('卡片文案 id 非真实线路', [...zhIds].filter(x=>!ROUTES[x]).map(x=>`${x} 不是线路 id`));
}

console.log(P.length? `\n✗ 交叉体检 ${P.length} 类问题` : `\n✅ 交叉体检全部通过（${Object.keys(ROUTES).length} 条线路 × 12 类横向比对）`);
process.exit(P.length?1:0);
