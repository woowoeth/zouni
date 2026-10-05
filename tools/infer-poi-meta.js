#!/usr/bin/env node
/* POI 元数据推断 v2
   产出两个文件，职责分离：
     poi-meta-inferred.json —— 机器推断，可随时重跑覆盖
     poi-meta-override.json —— 人工校正，永不被覆盖，优先级更高
   最终元数据 = inferred 叠加 override
*/
const fs=require('fs'), path=require('path');
const DIR=path.resolve(__dirname);
const LIB=JSON.parse(fs.readFileSync(DIR+'/lib-extracted.json','utf8'));

/* ── 功能性站点：提车/还车/休整/购票，无偏好属性，不参与选点 ── */
const LOGISTICS=/提车|还车|验车|休整|放行李|购票|进山|取票|入住|出发|抵达|返程|登机|check/i;

/* ── 偏好标签：用词组不用单字，避免「观鱼台」被判成美食 ── */
const TAG_RULES={
  photo : /机位|拍照|出片|摄影|观景台|倒影|镜面|光影|云海|日照金山|打卡点/,
  food  : /夜市|小吃|美食|餐|饭|馆子|老店|烧烤|火锅|面馆|茶室|早茶|酒馆|必点|人均¥|吃一顿|大排档/,
  history:/寺|庙|宫|塔|石窟|古城|古镇|遗址|博物馆|美术馆|故居|陵|碑林|城墙|书院|祠堂|殿|道观|老街|王府|转经|经堂/,
  nature: /湖|雪山|峡谷|草原|冰川|瀑布|森林|沙漠|雅丹|丹霞|海岸|河谷|溪|温泉|林海|沙滩|岛|山峰|溶洞|地质|梯田|花海|湿地|胡杨/,
  hike  : /徒步|栈道|登顶|步道|穿越|环线徒步|台阶|天梯|绕岛|爬升|下切|山路/,
  chill : /泡汤|发呆|慢下来|温泉|连住|晒太阳|下午茶|闲逛|不赶路|躺/,
  /* 人文 = 在地生活（与 history 的「遗存」互补：这里管人怎么过日子） */
  folk  : /村寨|苗寨|侗寨|民俗|集市|巴扎|辩经|非遗|手工艺|少数民族|藏族|蒙古|哈萨克|锅庄|木刻楞|老街生活|市井|赶集|作坊|茶馆|烟火气|当地人|夜生活|工坊|窑/,
  star  : /星空|银河|观星|极光/
};
/* ── 最佳时段：影响排序（日出排最早、日落排最晚） ── */
const TIME_RULES=[
  ['dawn',    /日出|晨雾|清晨|破晓|朝阳|早起看/],
  ['sunset',  /日落|日照金山|黄昏|晚霞|落日|等光/],
  ['night',   /夜市|夜景|银河|星空|灯光|晚上/],
  ['morning', /上午|早茶|开园|趁人少|清早/],
  ['afternoon',/午后|下午/]
];

function textOf(p){
  const src = p.opts ? p.opts[0] : p;   /* 二选一容器：取第一个选项的文案 */
  return [src.name, src.era, src.vibe, (src.must||[]).join(' '),
          (src.chips||[]).map(c=>Array.isArray(c)?c[1]:c).join(' '), p.optLabel||''].join(' ');
}

const inferred={};
const stats={tags:{}, time:{}, logistics:0, noTag:[]};
Object.entries(LIB.POI).forEach(([k,p])=>{
  const text=textOf(p);
  const name=(p.opts?p.opts[0].name:p.name)||p.optLabel||k;
  /* 功能性站点 */
  if(LOGISTICS.test(name) || (p.cat==='tix' && !p.cost && LOGISTICS.test(text))){
    inferred[k]={name, city:p._city, dur:p.dur||0, cost:p.cost||0, cat:p.cat, prio:p.prio,
                 type:'logistics', tags:[], bestTime:null, indoor:!!p.indoor};
    stats.logistics++; return;
  }
  const tags=[];
  Object.entries(TAG_RULES).forEach(([tag,re])=>{ if(re.test(text)) tags.push(tag); });
  if(p.cat==='food' && !tags.includes('food')) tags.push('food');
  if(!tags.length) stats.noTag.push(k+' · '+name);
  let bestTime=null;
  for(const [t,re] of TIME_RULES){ if(re.test(text)){ bestTime=t; break; } }
  tags.forEach(t=>stats.tags[t]=(stats.tags[t]||0)+1);
  if(bestTime) stats.time[bestTime]=(stats.time[bestTime]||0)+1;
  const rep = p.opts ? p.opts[0] : p;                 /* 二选一容器：用首个选项作代表 */
  inferred[k]={name, city:p._city,
               dur: p.dur || rep.dur || 0,
               cost: p.cost || rep.cost || 0,
               cat:p.cat, prio:p.prio,
               type:p.opts?'choice':'poi',
               choices: p.opts? p.opts.map(o=>({name:o.name,dur:o.dur,cost:o.cost})) : undefined,
               tags, bestTime, indoor:!!p.indoor};
});

fs.writeFileSync(DIR+'/poi-meta-inferred.json', JSON.stringify(inferred,null,1));

/* 人工覆盖层：不存在则建空壳（带说明） */
const OV=DIR+'/poi-meta-override.json';
if(!fs.existsSync(OV)){
  fs.writeFileSync(OV, JSON.stringify({
    "_说明":"人工校正层。这里写的字段覆盖机器推断，重跑推断不会丢。只写要改的字段。",
    "_示例":{"guanyu":{"tags":["photo","nature"],"_why":"观鱼台是观景不是吃鱼，去掉 food"}}
  },null,1));
}
const override=JSON.parse(fs.readFileSync(OV,'utf8'));
const final={};
Object.entries(inferred).forEach(([k,v])=>{
  final[k]=override[k] ? Object.assign({},v,override[k]) : v;
});
fs.writeFileSync(DIR+'/poi-meta.json', JSON.stringify(final,null,1));

console.log('══ 推断结果（188 个站点）══');
console.log(`  功能性站点 ${stats.logistics} 个（提车/还车/休整，不参与偏好选点）`);
Object.entries(stats.tags).sort((a,b)=>b[1]-a[1]).forEach(([t,n])=>console.log(`  ${t.padEnd(9)} ${String(n).padStart(3)} 个`));
console.log(`  无标签 ${stats.noTag.length} 个:`);
stats.noTag.slice(0,10).forEach(x=>console.log(`     · ${x}`));
console.log('\n══ 时段（影响排序）══');
Object.entries(stats.time).sort((a,b)=>b[1]-a[1]).forEach(([t,n])=>console.log(`  ${t.padEnd(11)} ${String(n).padStart(3)} 个`));
console.log(`\n  人工覆盖 ${Object.keys(override).filter(k=>!k.startsWith('_')).length} 条`);
console.log('  → poi-meta-inferred.json（可重跑覆盖）/ poi-meta-override.json（人工，永久）/ poi-meta.json（合并结果）');
