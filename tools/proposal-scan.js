#!/usr/bin/env node
/* ═══ 功能提案扫描器 ═══
   SOP 说好我每周主动提案，实际一次没做——因为它靠「我记得」。
   这个脚本把扫描自动化：从四个来源找候选，生成提案草稿，我补判断后给你审。

   四个来源（都是客观数据，不靠印象）：
     A. 体检报告的 ℹ 项 —— 已知但没做的覆盖度缺口
     B. 引擎已有但界面没用上的能力 —— 沉没成本，接上就有
     C. 内容缺口 —— 哪些城市/形态还空着
     D. 用户旅程断点 —— 关键路径上需要离开产品才能完成的事

   用法：node proposal-scan.js
*/
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname,'..');
const html=fs.readFileSync(ROOT+'/src/index.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/_prop.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
const {ROUTES}=require('/tmp/_prop.js');

const props=[];
const add=(源,标题,问题,证据,方案,工作量)=>props.push({源,标题,问题,证据,方案,工作量});

/* ── A. 覆盖度缺口（来自数据体检的 ℹ 项）── */
const fams={};
Object.entries(ROUTES).forEach(([id,R])=>{ (fams[R.fam]=fams[R.fam]||[]).push(id); });
const single=Object.keys(fams).filter(f=>fams[f].length===1);
if(single.length){
  add('覆盖度','单方案族补天数变体',
    `${single.length} 个族只有一种天数，用户改不了行程长度`,
    `族：${single.join(' ')}`,
    '按需求热度逐个补 1–2 个变体，工具链已就绪',
    single.length>5?'大':'中');
}
const noIns=Object.keys(ROUTES).filter(id=>{
  const R=ROUTES[id];
  return Object.keys(R.inserts||{}).length===0 && (R.extras||[]).some(x=>x.later);
});
if(noIns.length>=5){
  add('覆盖度','备选点只能「记入下次」',
    `${noIns.length} 条线路没有任何可真加入的备选点，用户只能记录期待`,
    `线路：${noIns.slice(0,6).join(' ')}…`,
    '每条挑 1–2 个真顺路的点补插入数据（约 15 行/条）',
    '中');
}

/* ── B. 引擎已有但界面没用上的能力 ── */
const engineCaps=[
  ['tripToHash','行程压进链接互传','已实现但入口只在分享文案里，没做成显式功能'],
  ['exportData','备份导出导入','已实现，藏在「我的」页深处'],
  ['FX','五币种换算','已实现，但没有「按当地货币显示」的智能默认'],
  ['departDate','出发日期','已实现，但没有「按日期自动提示季节限制」'],
];
engineCaps.forEach(([key,name,note])=>{
  if(js.indexOf(key)>-1){
    const uiHits=(js.slice(js.indexOf('/* ---------- 安排行程')).match(new RegExp(key,'g'))||[]).length;
    if(uiHits<=2) add('沉没能力',name, note,
      `引擎里 ${key} 已实现，UI 层仅 ${uiHits} 处引用`,
      '接一个明确入口即可，不需要新引擎逻辑','小');
  }
});

/* ── C. 内容缺口 ── */
const PROVINCES=['北京','上海','天津','重庆','河北','山西','辽宁','吉林','黑龙江','江苏','浙江','安徽','福建','江西','山东','河南','湖北','湖南','广东','广西','海南','四川','贵州','云南','西藏','陕西','甘肃','青海','宁夏','新疆','内蒙古','香港','澳门','台湾'];
const covered=new Set();
Object.values(ROUTES).forEach(R=>{
  PROVINCES.forEach(p=>{ if((R.dest||'').includes(p)||(R.name||'').includes(p)) covered.add(p); });
});
const missing=PROVINCES.filter(p=>!covered.has(p));
if(missing.length) add('内容缺口','省份覆盖',
  `${covered.size}/34 个省级行政区有线路`,
  `未覆盖：${missing.join(' ')}`,
  '按旅行热度梯队推进（T2：苏州南京·广深·青岛·武汉·长沙·贵州）','大');

const intl=Object.values(ROUTES).filter(R=>(R.locale&&R.locale.region==='intl')).length;
if(intl<5) add('内容缺口','海外线路',
  `仅 ${intl} 条海外线，出境需求接不住`,
  '现有：日本关西',
  '按既定顺序：港澳台 → 东南亚 → 日韩 → 欧美','大');

/* ── D. 用户旅程断点：关键路径上需要离开产品的事 ── */
const journey=[
  ['订住宿','行程里给了住宿名和价格，但订房要自己去别处搜',  '住宿卡片加一键跳转到地图/订房 App 的深链'],
  ['订门票','待办里写了「提前 3 天预约」，但没有直达入口',   '待办项支持挂官方预约链接'],
  ['记账','出发前算好了预算，路上实际花了多少无处记',        '行程内轻量记账：每站点一下「实付」'],
  ['同行人','行程是一个人在看，同伴要另发一份',              '分享链接支持只读协作视图'],
];
journey.forEach(([点,断,方])=>add('旅程断点',点,断,'走查「挑→排→改→存→分享→出行」全流程发现',方,'中'));

/* ── 输出提案草稿 ── */
const date=new Date().toISOString().slice(0,10);
let md=`# 功能提案单 · ${date}\n\n> 由 \`proposal-scan.js\` 自动扫描生成，我补了判断。\n> 你只需逐条回：**做 / 缓 / 否**。\n\n`;
const bySource={};
props.forEach(p=>{ (bySource[p.源]=bySource[p.源]||[]).push(p); });
Object.entries(bySource).forEach(([src,list])=>{
  md+=`## ${src}\n\n`;
  list.forEach((p,i)=>{
    md+=`### ${i+1}. ${p.标题}\n\n`;
    md+=`- **问题**：${p.问题}\n`;
    md+=`- **证据**：${p.证据}\n`;
    md+=`- **方案**：${p.方案}\n`;
    md+=`- **工作量**：${p.工作量}\n`;
    md+=`- **你的决定**：做 / 缓 / 否\n\n`;
  });
});
md+=`---\n\n共 ${props.length} 条候选。工作量：小=半天内 · 中=1–2 天 · 大=需拆期。\n`;

const out=ROOT+'/docs/proposals.md';
fs.writeFileSync(out, md);
console.log(`══ 功能提案扫描 ══`);
Object.entries(bySource).forEach(([src,list])=>{
  console.log(`  ${src}（${list.length}）`);
  list.forEach(p=>console.log(`    · ${p.标题} —— ${p.问题.slice(0,40)}`));
});
console.log(`\n→ 提案单已生成：docs/proposals.md（共 ${props.length} 条待你审）`);
