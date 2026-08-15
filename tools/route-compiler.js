#!/usr/bin/env node
/* ═══ 走你 · 路线编译器 ═══
   把"手写整条行程"变成"声明城市序列 + 选站点"，编排层全部推导。

   三层库（我只维护这三层）
     CITY : 城市/节点 —— 名称、地图坐标、住宿选项
     POI  : 站点 —— 时长、价格、类别、文案、所属城市
     LEG  : 城市间接驳 —— 里程、时间、费用、途经说明

   声明式行程（新线路只写这个）
     { id, fam, plan:[ {from,to,stops[],stay} ... ] }

   编译器自动推导（这些正是出过事故的地方）
     tab 天签连号 · lodges 与末天 null · nights · map.seg · map.tonight
     · map.order · 接驳查表 · 里程合计 · 地理连续性（结构上不可能断裂）

   用法：
     node route-compiler.js extract          # 从现有线路反向提取三层库
     node route-compiler.js compile plan.json  # 编译声明 → 完整路线对象
     node route-compiler.js roundtrip gl3    # 反向提取某条线路再编译，验证等价
*/
const fs=require('fs'), path=require('path');

function loadRoutes(){
  const html=fs.readFileSync(path.resolve(__dirname,'../src/index.html'),'utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
  const tmp='/tmp/_compiler_src.js';
  fs.writeFileSync(tmp, js.slice(a,b)+'\nmodule.exports={ROUTES,FUEL};');
  delete require.cache[tmp];
  return require(tmp);
}

/* ══════════ 提取器：从现有线路反向建库 ══════════ */
function extract(ROUTES){
  const CITY={}, POI={}, LEG={};
  Object.keys(ROUTES).forEach(rid=>{
    const R=ROUTES[rid], M=R.map||{}, nodes=M.nodes||[];
    /* 城市：来自地图节点 */
    nodes.forEach((n,i)=>{
      const cid=`${R.fam}:${i}`;
      if(!CITY[cid]) CITY[cid]={name:n.n, x:n.x, y:n.y, lx:n.lx, ly:n.ly, a:n.a, fam:R.fam, idx:i, lodges:[]};
    });
    /* 住宿：按 tonight 归到城市 */
    (R.lodges||[]).forEach((l,di)=>{
      if(!l) return;
      const node=(M.tonight||[])[di];
      const cid=`${R.fam}:${node}`;
      if(!CITY[cid]) return;
      const opts=l.opts||[l];
      opts.forEach(o=>{
        if(!CITY[cid].lodges.some(x=>x.city===o.city))
          CITY[cid].lodges.push({city:o.city, price:o.price, why:o.why, q:o.q});
      });
    });
    /* 站点与接驳 */
    (R.days||[]).forEach((d,di)=>{
      /* 站点归属：优先算「当天到达的城市」（seg 终点），原地游玩天才用住宿地 */
      const sg=(M.seg||[])[di];
      const arrive = sg ? (Array.isArray(sg[0])?sg[0][sg[0].length-1]:sg[sg.length-1]) : null;
      const stayNode=(M.tonight||[])[di];
      const homeNode = arrive!=null ? arrive : stayNode;
      (d.stops||[]).forEach(st=>{
        if(st.k){
          if(!POI[st.k]) POI[st.k]=Object.assign({}, st, {_city:`${R.fam}:${homeNode}`, _from:[rid]});
          else if(!POI[st.k]._from.includes(rid)) POI[st.k]._from.push(rid);
        }else if(st.conn){
          const key=st.conn.replace(/\s+/g,'').slice(0,40);
          if(!LEG[key]) LEG[key]={conn:st.conn, min:st.min, km:st.km||0, cost:st.cost||0, mode:st.mode||'', via:st.via, _from:[rid]};
        }
      });
      ['pre','post'].forEach(k=>{
        const c=d[k]; if(!c||!c.conn) return;
        const key=c.conn.replace(/\s+/g,'').slice(0,40);
        if(!LEG[key]) LEG[key]={conn:c.conn, min:c.min, km:c.km||0, cost:c.cost||0, mode:c.mode||'', via:c.via, _from:[rid]};
      });
    });
  });
  /* 合并人工补充层（永不被 extract 覆盖） */
  try{
    const OV=JSON.parse(require('fs').readFileSync(__dirname+'/lib-override.json','utf8'));
    Object.entries(OV.CITY||{}).forEach(([cid,v])=>{
      if(!CITY[cid]) CITY[cid]=Object.assign({lodges:[]}, v);
      else if(v.lodges) CITY[cid].lodges=[...CITY[cid].lodges, ...v.lodges];
    });
    Object.entries(OV.LEG||{}).forEach(([k,v])=>{ if(!LEG[k]) LEG[k]=v; });
    Object.entries(OV.POI||{}).forEach(([k,v])=>{ POI[k]=Object.assign({},POI[k]||{},v); });
  }catch(e){}
  return {CITY, POI, LEG};
}

/* ══════════ 编译器：声明 → 完整路线对象 ══════════ */
function compile(spec, LIB, base){
  const {CITY, POI, LEG}=LIB;
  const plan=spec.plan;
  const errors=[];

  /* 1. 城市 → 地图节点（去重后按出现顺序建 nodes） */
  const cityOrder=[];
  plan.forEach(p=>{
    [p.from, ...(p.viaCities||[]), p.to, p.stay].forEach(c=>{ if(c && !cityOrder.includes(c)) cityOrder.push(c); });
  });
  const nodes=cityOrder.map(cid=>{
    const c=CITY[cid];
    if(!c){ errors.push(`城市 ${cid} 不在库中`); return {n:cid, x:0, y:0}; }
    return {n:c.name, x:c.x, y:c.y, lx:c.lx!=null?c.lx:12, ly:c.ly!=null?c.ly:4, a:c.a||'middle'};
  });
  const nodeIdx=cid=>cityOrder.indexOf(cid);

  /* 2. 逐日推导 */
  const days=[], lodges=[], seg=[], tonight=[];
  plan.forEach((p,i)=>{
    const isLast = i===plan.length-1;
    /* 2a. 天签自动连号 —— 消除跳号事故 */
    const tab=`D${i+1}`;
    /* 2b. 站点：从 POI 库取，保持声明顺序 */
    const stops=[];
    (p.stops||[]).forEach(sid=>{
      if(typeof sid==='object'){ stops.push(sid); return; }   /* 内联接驳/自定义 */
      const poi=POI[sid];
      if(!poi){ errors.push(`${tab} 站点 ${sid} 不在库中`); return; }
      const cp=Object.assign({}, poi); delete cp._city; delete cp._from;
      stops.push(cp);
    });
    /* 2c. 接驳：from→to 查 LEG 库 */
    let pre=null, post=null;
    if(p.from && p.to && p.from!==p.to){
      const legKey=Object.keys(LEG).find(k=>LEG[k].conn.includes(CITY[p.from]?CITY[p.from].name:'') &&
                                            LEG[k].conn.includes(CITY[p.to]?CITY[p.to].name:''));
      if(p.leg) pre=p.leg;                       /* 声明里显式给了接驳 */
      else if(legKey) pre=Object.assign({}, LEG[legKey], {_key:undefined});
      else errors.push(`${tab} 缺 ${p.from}→${p.to} 的接驳数据（LEG 库无匹配，请在声明里给 leg 字段）`);
    }
    if(p.post) post=p.post;
    days.push(Object.assign({
      tab, name:p.name||`${CITY[p.from]?CITY[p.from].name:''} → ${CITY[p.to]?CITY[p.to].name:''}`,
      sub:p.sub||'', start:p.start!=null?p.start:540, hardEnd:p.hardEnd!=null?p.hardEnd:1320,
      pre, post, stops
    }, p.dayOverrides||{}));

    /* 2d. 住宿链：末天强制 null —— 消除项数错位 */
    if(isLast || !p.stay){ lodges.push(null); }
    else{
      const c=CITY[p.stay];
      const pick=p.lodge!=null ? (c&&c.lodges[p.lodge]) : (c&&c.lodges[0]);
      if(!pick){ errors.push(`${tab} 城市 ${p.stay} 无住宿数据`); lodges.push(null); }
      else if(p.lodgeOpts && c.lodges.length>1)
        lodges.push({opts:c.lodges.slice(0,2).map(o=>({city:o.city,price:o.price,why:o.why,q:o.q}))});
      else lodges.push({city:pick.city, price:pick.price, why:pick.why, q:pick.q});
    }
    /* 2e. 地图 seg / tonight —— 从 from/to/stay 推导，不可能错位 */
    if(p.from && p.to && p.from!==p.to){
      const mid=(p.viaCities||[]).map(nodeIdx).filter(i=>i>=0);
      seg.push(p.roundTrip ? [nodeIdx(p.from), nodeIdx(p.to), nodeIdx(p.from)]
             : mid.length ? [nodeIdx(p.from), ...mid, nodeIdx(p.to)]
             : [nodeIdx(p.from), nodeIdx(p.to)]);
    } else seg.push(null);
    tonight.push(isLast || !p.stay ? -1 : nodeIdx(p.stay));
  });

  /* 3. 地理连续性：结构上校验（上一天 stay 必须 = 下一天 from） */
  for(let i=0;i<plan.length-1;i++){
    const stay=plan[i].stay, nextFrom=plan[i+1].from||plan[i+1].at;
    if(stay && nextFrom && stay!==nextFrom)
      errors.push(`地理断裂：D${i+1} 住 ${stay}，D${i+2} 从 ${nextFrom} 出发`);
  }

  /* 4. 派生量 */
  const nights=lodges.filter(Boolean).length;
  const totalKm=days.reduce((s,d)=>s+((d.pre&&d.pre.km)||0)+((d.post&&d.post.km)||0)+
    (d.stops||[]).reduce((x,st)=>x+(st.km||0),0), 0);

  return {
    route: Object.assign({}, base||{}, {
      days, lodges, nights,
      map:{ nodes, order:cityOrder.map((_,i)=>i), loop:!!spec.loop, seg, tonight }
    }, spec.overrides||{}),
    stats:{ days:days.length, nights, totalKm, cities:cityOrder.length },
    errors
  };
}

/* ══════════ 反向：把现有线路转成声明（用于 roundtrip 验证） ══════════ */
let CITY_CACHE={};
function toPlan(ROUTES, id, LIB){
  if(LIB) CITY_CACHE=LIB.CITY;
  const R=ROUTES[id], M=R.map||{};
  return {
    id, fam:R.fam, loop:!!M.loop,
    plan:(R.days||[]).map((d,i)=>{
      const sg=(M.seg||[])[i], tn=(M.tonight||[])[i];
      const cid=n=>`${R.fam}:${n}`;
      const L=(R.lodges||[])[i];
      /* 住宿：记录是二选一，还是选了该城市的第几个 */
      let lodgeIdx=0, lodgeOpts=false;
      if(L){
        if(L.opts) lodgeOpts=true;
        else{
          const c=CITY_CACHE[`${R.fam}:${tn}`];
          if(c) lodgeIdx=Math.max(0, c.lodges.findIndex(x=>x.city===L.city));
        }
      }
      return {
        from: sg?cid(sg[0]):(i>0?cid((M.tonight||[])[i-1]):null),
        to:   sg ? cid( (sg.length>2 && sg[sg.length-1]===sg[0]) ? sg[1] : sg[sg.length-1] ) : null,
        stay: (tn!=null&&tn!==-1)?cid(tn):null,
        roundTrip: !!(sg && sg.length>2 && sg[2]===sg[0]),
        viaCities: (sg && sg.length>2 && sg[sg.length-1]!==sg[0]) ? sg.slice(1,-1).map(cid) : undefined,
        lodge: lodgeIdx, lodgeOpts,
        stops:(d.stops||[]).filter(s=>s.k).map(s=>s.k),
        name:d.name, sub:d.sub, start:d.start, hardEnd:d.hardEnd,
        leg:d.pre, post:d.post
      };
    })
  };
}

/* ══════════ CLI ══════════ */
const [,,cmd,arg]=process.argv;
const {ROUTES}=loadRoutes();

if(cmd==='extract'){
  const LIB=extract(ROUTES);
  const out=require('path').resolve(__dirname,'lib-extracted.json');
  fs.writeFileSync(out, JSON.stringify({
    CITY:LIB.CITY, POI:Object.fromEntries(Object.entries(LIB.POI).map(([k,v])=>[k,Object.assign({},v,{_from:undefined})])),
    LEG:LIB.LEG
  }, null, 1));
  console.log('══ 三层库提取完成 ══');
  console.log(`  CITY ${Object.keys(LIB.CITY).length} 个（含住宿 ${Object.values(LIB.CITY).reduce((s,c)=>s+c.lodges.length,0)} 项）`);
  console.log(`  POI  ${Object.keys(LIB.POI).length} 个`);
  console.log(`  LEG  ${Object.keys(LIB.LEG).length} 条`);
  console.log(`  → ${out}`);
  process.exit(0);
}

if(cmd==='roundtrip'){
  if(arg==='all'){
    const LIB=extract(ROUTES);
    let ok=0, bad=[];
    Object.keys(ROUTES).forEach(id=>{
      const r=compile(toPlan(ROUTES,id,LIB), LIB, ROUTES[id]);
      const o=ROUTES[id];
      const nm=(arr,nodes)=>(arr||[]).map(v=>v==null?null:(Array.isArray(v)?v.map(i=>(nodes[i]||{}).n):((v===-1)?'-':(nodes[v]||{}).n)));
      const same = JSON.stringify(o.days.map(d=>d.tab))===JSON.stringify(r.route.days.map(d=>d.tab))
        && JSON.stringify(o.lodges.map(l=>l?(l.opts?'opts':l.city):null))===JSON.stringify(r.route.lodges.map(l=>l?(l.opts?'opts':l.city):null))
        && ((o.nights!=null?o.nights:(o.stay&&o.stay.nights!=null?o.stay.nights:(o.lodges||[]).filter(Boolean).length))===r.route.nights)
        && JSON.stringify(nm(o.map.seg,o.map.nodes))===JSON.stringify(nm(r.route.map.seg,r.route.map.nodes))
        && JSON.stringify(nm(o.map.tonight,o.map.nodes))===JSON.stringify(nm(r.route.map.tonight,r.route.map.nodes))
        && JSON.stringify(o.days.map(d=>(d.stops||[]).filter(x=>x.k).map(x=>x.k)))===JSON.stringify(r.route.days.map(d=>(d.stops||[]).filter(x=>x.k).map(x=>x.k)));
      same?ok++:bad.push(id);
    });
    console.log(`══ 全量往返：编译器能否复现手写的编排层 ══`);
    console.log(bad.length? `  ✗ ${bad.length}/${ok+bad.length} 条不等价: ${bad.join(' ')}` : `  ✅ ${ok} 条全部等价`);
    process.exit(bad.length?1:0);
  }
  const id=arg||'gl3';
  const LIB=extract(ROUTES);
  const spec=toPlan(ROUTES,id,LIB);
  const r=compile(spec, LIB, ROUTES[id]);
  const orig=ROUTES[id];
  const diffs=[];
  const cmp=(a,b,label)=>{ if(JSON.stringify(a)!==JSON.stringify(b)) diffs.push(`${label}\n     手写: ${JSON.stringify(a)}\n     编译: ${JSON.stringify(b)}`); };
  cmp(orig.days.map(d=>d.tab), r.route.days.map(d=>d.tab), '天签');
  cmp(orig.lodges.map(l=>l?(l.opts?'opts':l.city):null), r.route.lodges.map(l=>l?(l.opts?'opts':l.city):null), '住宿链');
  const origNights = orig.nights!=null ? orig.nights
    : (orig.stay&&orig.stay.nights!=null ? orig.stay.nights : (orig.lodges||[]).filter(Boolean).length);
  cmp(origNights, r.route.nights, 'nights');
  /* seg/tonight 用城市名比对：编译器只建实际用到的节点，索引值可不同但拓扑须等价 */
  const nm=(arr,nodes)=>(arr||[]).map(v=>v==null?null:(Array.isArray(v)?v.map(i=>(nodes[i]||{}).n):((v===-1)?'-':(nodes[v]||{}).n)));
  cmp(nm(orig.map.seg,orig.map.nodes), nm(r.route.map.seg,r.route.map.nodes), 'map.seg（按城市名）');
  cmp(nm(orig.map.tonight,orig.map.nodes), nm(r.route.map.tonight,r.route.map.nodes), 'map.tonight（按城市名）');
  cmp(orig.days.map(d=>(d.stops||[]).filter(s=>s.k).map(s=>s.k)), r.route.days.map(d=>(d.stops||[]).filter(s=>s.k).map(s=>s.k)), '站点序列');
  console.log(`══ 往返验证 ${id}：手写 vs 编译 ══`);
  if(r.errors.length){ console.log('  编译告警:'); r.errors.forEach(e=>console.log('    · '+e)); }
  if(diffs.length){ console.log(`  ✗ ${diffs.length} 处不一致:`); diffs.forEach(d=>console.log('    · '+d)); }
  else console.log('  ✅ 编排层完全等价（天签/住宿链/nights/seg/tonight/站点序列）');
  process.exit(diffs.length?1:0);
}

if(cmd==='compile'){
  const spec=JSON.parse(fs.readFileSync(arg,'utf8'));
  const LIB=extract(ROUTES);
  const r=compile(spec, LIB, ROUTES[spec.base]||{});
  console.log(`══ 编译 ${spec.id} ══`);
  console.log(`  ${r.stats.days} 天 · ${r.stats.nights} 晚 · ${r.stats.cities} 城 · ${r.stats.totalKm} km`);
  console.log(`  seg     ${JSON.stringify(r.route.map.seg)}`);
  console.log(`  tonight ${JSON.stringify(r.route.map.tonight)}`);
  if(r.errors.length){ console.log(`  ✗ ${r.errors.length} 项问题:`); r.errors.forEach(e=>console.log('    · '+e)); process.exit(1); }
  fs.writeFileSync('/tmp/compiled-'+spec.id+'.json', JSON.stringify(r.route,null,1));
  console.log(`  ✅ 编译通过 → /tmp/compiled-${spec.id}.json`);
  process.exit(0);
}

console.log('用法: extract | compile plan.json | roundtrip [id]');
