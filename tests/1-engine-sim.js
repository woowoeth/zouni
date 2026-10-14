const E=require('/tmp/xj_eng.js');
const ids=Object.keys(E.ROUTES);
let pass=0,fail=0;
for(const id of ids){
  E.loadRoute(id);
  const R=E.rt(),D=E.days();
  const over=[]; let nan=false;
  D.forEach((d,i)=>{const r=E.resolveDay(i);
    if(r.end>d.hardEnd) over.push(`${d.tab}+${r.end-d.hardEnd}`);
    r.sched.forEach(x=>{if(!isFinite(x.arr))nan=true;});});
  const t0=E.totals(); if(R.thrift)R.thrift(); E.resolveAll(); const t1=E.totals();
  const ok = !over.length && !nan && t0.total<=R.budgets[0].v && t1.total<=R.budgets[1].v;
  ok?pass++:fail++;
  console.log((ok?'✓':'✗'), id.padEnd(5), String(D.length).padStart(2)+'天',
    over.length?'超时'+over.join(','):'', nan?'NaN':'',
    `宽${Math.round(t0.total)}/${R.budgets[0].v}`, `精${Math.round(t1.total)}/${R.budgets[1].v}`);
  // 地图数组边界
  const M=R.map;
  if(M){
    const badT=(M.tonight||[]).filter(i=>i>=M.nodes.length);
    const badS=(M.seg||[]).filter(sg=>sg&&(sg[0]>=M.nodes.length||(sg[1]!=null&&sg[1]>=M.nodes.length)));
    if(badT.length||badS.length){ console.log('   ⚠ 地图越界', id, badT, JSON.stringify(badS)); fail++; }
    if((M.tonight||[]).length!==D.length) { console.log('   ⚠ tonight长度≠天数', id, M.tonight.length, D.length); fail++; }
  }
  if(R.lodges.length!==D.length) { console.log('   ⚠ lodges长度≠天数', id, R.lodges.length, D.length); fail++; }
}
console.log(`\n${pass}✓ / ${fail}✗ / 共${ids.length}线`);
