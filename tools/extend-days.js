#!/usr/bin/env node
/* ═══ 天数扩展器 ═══
   22 个族只有一种天数，用户想多待一天却加不了 —— 这是最直接的需求落空。

   做法：给每条线补一个「+1 天」变体。多出来的那天用什么？
     1. 优先用该线已有的 extras（备选点）—— 那本来就是"想去但没排下"的
     2. 其次把原来赶的一天拆成两天（长车程日最值得拆）
     3. 都不行才补新站点

   这个脚本做第 1 类：把 extras 里的备选点提出来，生成 +1 天的 days 定义。
   用法：node extend-days.js <fam>   或   node extend-days.js --report
*/
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname,'..');
const html=fs.readFileSync(ROOT+'/src/index.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/_ext.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
const {ROUTES}=require('/tmp/_ext.js');

/* 每族的候选延长方案：多出来的一天去哪、看什么 */
const PLAN = {
  hlb:{name:'室韦 · 中俄边境',  why:'额尔古纳河对岸就是俄罗斯，木刻楞民居最完整'},
  jz: {name:'若尔盖草原',       why:'川主寺往北两小时，黄河第一湾的日落'},
  yl: {name:'喀拉峻草原',       why:'特克斯旁的空中草原，五花草甸最盛在六月'},
  tl: {name:'河坑土楼群',       why:'南靖境内，北斗七星布局，人比田螺坑少'},
  ts: {name:'邹城孟庙',         why:'曲阜旁半小时，孟子故里，比三孔安静'},
  njg:{name:'红其拉甫口岸',     why:'中巴边境 4700m，需另办边防证'},
  bn: {name:'望天树空中走廊',   why:'勐腊方向，36 米高的树冠廊桥'},
  yy: {name:'建水古城深度',     why:'朱家花园之外还有团山民居与小火车'},
  qd: {name:'小鱼山 · 信号山',  why:'老城两处制高点，红瓦绿树看得最全'},
  wh: {name:'楚河汉街 · 昙华林',why:'城中步行街与老教会区，半天足够'},
  cs: {name:'铜官窑古镇',       why:'长沙北郊，唐代长沙窑遗址'},
  gz: {name:'肇兴侗寨',         why:'黎平方向，五座鼓楼的侗族大歌'},
  sz: {name:'同里古镇',         why:'城南半小时，退思园与三桥'},
  nj: {name:'栖霞山',           why:'城东北，十一月红叶最盛'},
  hz: {name:'西溪湿地',         why:'城西，芦苇荡与摇橹船'},
  cq: {name:'白公馆 · 渣滓洞',  why:'歌乐山半日，近代史现场'},
  xm: {name:'筼筜湖 · 园博苑',  why:'市中心白鹭栖息地'},
  sy: {name:'呀诺达雨林',       why:'保亭方向，热带雨林徒步'},
  sh: {name:'朱家角水乡',       why:'地铁 17 号线终点，放生桥与课植园'},
  bj: {name:'颐和园 · 圆明园',  why:'西郊皇家园林，一天走两处'},
  xa: {name:'华清池 · 骊山',    why:'临潼方向，与兵马俑同线'},
  cd: {name:'三圣乡 · 白鹿镇',  why:'城郊花海与法式小镇'}
};

if(process.argv.includes('--report')){
  const fams={};
  Object.entries(ROUTES).forEach(([id,R])=>{ const f=R.fam; (fams[f]=fams[f]||[]).push(R.days.length); });
  const single=Object.entries(fams).filter(([f,d])=>[...new Set(d)].length===1);
  console.log('══ 只有一种天数的族 ══');
  single.forEach(([f,d])=>{
    const p=PLAN[f];
    console.log(`  ${f.padEnd(5)} ${d[0]} 天  ${p? '→ +1 天：'+p.name : '⚠ 未规划延长方案'}`);
  });
  console.log(`\n  共 ${single.length} 族，已规划 ${single.filter(([f])=>PLAN[f]).length} 个`);
  process.exit(0);
}

console.log('用法：node extend-days.js --report');
