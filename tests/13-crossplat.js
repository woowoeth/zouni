#!/usr/bin/env node
/* ═══ 跨端兼容体检 ═══
   目标：确认「数据层 + 引擎层」可脱离浏览器运行，将来能直接搬进小程序。
   小程序环境无 DOM、无 window、无 localStorage、无 innerHTML、无内联 SVG。
*/
const fs=require('fs'), path=require('path');
const html=fs.readFileSync(path.resolve(__dirname,'../src/index.html'),'utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
const core=js.slice(a,b);          /* 数据层 + 引擎层 */
const ui=js.slice(b);              /* UI 层 */

const BROWSER_API=[
  ['document\\.',        'document'],
  ['window\\.',          'window'],
  ['localStorage',       'localStorage'],
  ['innerHTML',          'innerHTML'],
  ['querySelector',      'querySelector'],
  ['addEventListener',   'addEventListener'],
  ['getElementById',     'getElementById'],
  ['navigator\\.',       'navigator'],
  ['location\\.',        'location'],
  ['setTimeout|setInterval', '定时器'],
  ['createElement',      'createElement'],
  ['classList',          'classList'],
  ['performance\\.',     'performance'],
  ['\\balert\\(|\\bprompt\\(|\\bconfirm\\(', '弹窗 API']
];

function scan(code, label){
  const found=[];
  BROWSER_API.forEach(([re,name])=>{
    const m=code.match(new RegExp(re,'g'));
    if(m) found.push({name, n:m.length});
  });
  return found;
}

console.log('══ 1. 数据层 + 引擎层：浏览器 API 依赖 ══');
const coreDeps=scan(core);
if(!coreDeps.length) console.log('  ✅ 零依赖 —— 可直接搬进小程序 / Node / 任何 JS 环境');
else coreDeps.forEach(d=>console.log(`  ✗ ${d.name.padEnd(16)} ${d.n} 处 ← 需剥离`));

console.log(`\n  核心体积 ${Math.round(core.length/1024)}KB（数据 + 引擎）`);

console.log('\n══ 2. UI 层：浏览器 API 依赖（小程序需重写，属预期）══');
scan(ui).forEach(d=>console.log(`  · ${d.name.padEnd(16)} ${d.n} 处`));
console.log(`  UI 体积 ${Math.round(ui.length/1024)}KB ← 小程序版需重写这部分`);

console.log('\n══ 3. 实证：引擎在纯 Node 环境（无 DOM，等价小程序沙箱）能否跑通 ══');
const tmp='/tmp/_crossplat_core.js';
fs.writeFileSync(tmp, core+`
module.exports={ROUTES,loadRoute,resolveAll,totals,rt:()=>RT,days:()=>DAYS,setBudget:v=>{BUDGET=v}};`);
let ok=true, detail='';
try{
  delete require.cache[tmp];
  const E=require(tmp);
  const ids=Object.keys(E.ROUTES);
  let pass=0;
  ids.forEach(id=>{
    try{
      E.loadRoute(id);
      E.setBudget(E.ROUTES[id].budgets[0].v);
      E.resolveAll();
      const t=E.totals();
      if(!isNaN(t.total) && t.total>0) pass++;
    }catch(e){ detail+=`\n     ${id}: ${e.message.split('\n')[0].slice(0,50)}`; }
  });
  console.log(`  ${pass===ids.length?'✅':'✗'} ${pass}/${ids.length} 条线路在无 DOM 环境完成装载与算账${detail}`);
  ok = pass===ids.length;
}catch(e){ console.log('  ✗ 引擎无法在纯 Node 加载:', e.message.split('\n')[0]); ok=false; }

console.log('\n══ 4. 语法兼容（小程序基础库 / 微信 X5 / iOS Safari 共同底线）══');
const SYNTAX=[
  ['\\?\\.',            '可选链 ?.'],
  ['\\?\\?',            '空值合并 ??'],
  ['replaceAll',        'String.replaceAll'],
  ['\\.flatMap',        'Array.flatMap'],
  ['\\.at\\(',          'Array.at'],
  ['structuredClone',   'structuredClone'],
  ['globalThis',        'globalThis'],
  ['BigInt',            'BigInt']
];
let synBad=0;
SYNTAX.forEach(([re,name])=>{
  const m=(core+ui).match(new RegExp(re,'g'));
  if(m){ synBad++; console.log(`  ✗ ${name} ${m.length} 处`); }
});
if(!synBad) console.log('  ✅ 无高版本语法 —— 小程序基础库与老内核均可运行');

console.log('\n══ 5. 跨端就绪度总结 ══');
const ready = !coreDeps.length && ok && !synBad;
console.log(`  数据层 + 引擎层：${!coreDeps.length&&ok?'✅ 已就绪，小程序可直接复用':'✗ 需剥离浏览器依赖'}`);
console.log(`  UI 层：需按平台重写（web 用 DOM，小程序用 WXML）—— 这是预期的，不算问题`);
console.log(`  平台能力（存储/分享/导航/剪贴板）：${/localStorage/.test(core)?'✗ 已渗入引擎':'✅ 仅在 UI 层，可做适配层'}`);
process.exit(ready?0:1);
