/* 数据体检：地图合规 · 往返段可分离 · 价格语义 · 插入覆盖 · 天数变体
   硬错误 → 失败；覆盖度不足 → 只报告（内容 backlog，见发布清单第五节） */
const fs=require('fs'), path=require('path');
const html=fs.readFileSync(path.resolve(__dirname,'../src/index.html'),'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
const tmp='/tmp/_audit_routes.js';
fs.writeFileSync(tmp, js.slice(a,b)+"\nmodule.exports={ROUTES};");
const {ROUTES}=require(tmp);

let hard=0;
const warn=[];
const chk=(name,ok,detail)=>{ console.log((ok?'  ✓ ':'  ✗ ')+name+(ok?'':' → '+JSON.stringify(detail))); if(!ok) hard++; };

/* ── 1. 地图硬错误：索引越界 / 长度错位 / 坐标缺失 ── */
const mapErr=[];
Object.keys(ROUTES).forEach(id=>{
  const R=ROUTES[id], M=R.map||{}, N=(M.nodes||[]).length, days=(R.days||[]).length;
  (M.order||[]).forEach(i=>{ if(i==null||i<0||i>=N) mapErr.push(`${id} order越界:${i}`); });
  const seg=M.seg||[];
  if(seg.length && seg.length!==days) mapErr.push(`${id} seg长度${seg.length}≠天数${days}`);
  seg.forEach((sg,di)=>{
    if(!sg) return;
    (Array.isArray(sg[0])?sg:[sg]).forEach(pair=>{
      if(!Array.isArray(pair)) return;
      pair.forEach(i=>{ if(i==null||i<0||i>=N) mapErr.push(`${id} D${di+1} seg越界:${i}`); });
    });
  });
  const tn=M.tonight||[];
  if(tn.length && tn.length!==days) mapErr.push(`${id} tonight长度${tn.length}≠天数${days}`);
  tn.forEach((i,di)=>{ if(i!=null&&i!==-1&&(i<0||i>=N)) mapErr.push(`${id} D${di+1} tonight越界:${i}`); });
  (M.nodes||[]).forEach((n,i)=>{ if(!n||typeof n.x!=='number'||typeof n.y!=='number') mapErr.push(`${id} node[${i}]坐标缺失`); });
});
chk('地图索引与长度全部合规', !mapErr.length, mapErr.slice(0,6));

/* ── 2. 往返段：数据层允许重复，渲染层必须能分离（drawMap 有 arcGeo）── */
const roundTrip=[];
Object.keys(ROUTES).forEach(id=>{
  const seg=(ROUTES[id].map||{}).seg||[], used={};
  seg.forEach(sg=>{
    if(!sg||sg.length<2) return;
    const k=[sg[0],sg[1]].sort((x,y)=>x-y).join('-');
    used[k]=(used[k]||0)+1;
  });
  Object.keys(used).filter(k=>used[k]>1).forEach(k=>roundTrip.push(`${id}:${k}`));
});
chk('渲染层具备往返分离能力（arcGeo 存在）', js.indexOf('function arcGeo')>-1, 'arcGeo 缺失');
if(roundTrip.length) console.log(`  ℹ 往返段 ${roundTrip.length} 处（弧线分离，非错误）：${roundTrip.join(' ')}`);

/* ── 3. 价格语义：cost=0 的站点不得渲染价格标签 ── */
chk('cost=0 不渲染价格标签', js.indexOf('${s.cost>0?`<span class="stop-cost">')>-1, '模板未做零价判断');

/* ── 4. 二选一容器价格在 opts 内（容器 cost=0 属正常）── */
let optBad=[];
Object.keys(ROUTES).forEach(id=>{
  (ROUTES[id].days||[]).forEach((d,di)=>{
    (d.stops||[]).forEach(st=>{
      if(!st.opts) return;
      st.opts.forEach(o=>{ if(o.cost==null) optBad.push(`${id} D${di+1} ${o.name||'?'}`); });
    });
  });
});
chk('二选一选项均有价格字段', !optBad.length, optBad.slice(0,5));

/* ── 5. 覆盖度报告（backlog，不判失败）── */
const fams={};
Object.keys(ROUTES).forEach(id=>{ const f=ROUTES[id].fam; (fams[f]=fams[f]||[]).push(id); });
const single=Object.keys(fams).filter(f=>fams[f].length===1);
const noIns=Object.keys(ROUTES).filter(id=>{
  const R=ROUTES[id];
  return Object.keys(R.inserts||{}).length===0 && (R.extras||[]).some(x=>x.later);
});
console.log(`  ℹ 单方案族 ${single.length}/${Object.keys(fams).length}：${single.join(' ')}`);
console.log(`  ℹ 无插入能力 ${noIns.length}/${Object.keys(ROUTES).length}：${noIns.join(' ')}`);

console.log(hard? `✗ 数据体检 ${hard} 项硬错误` : '✅ 数据体检通过（硬错误为零；覆盖度见 ℹ 报告）');
process.exit(hard?1:0);
