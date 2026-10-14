/* 从单文件切出引擎供 1-engine-sim.js 使用 */
const fs=require('fs');
const html=fs.readFileSync(__dirname+'/../src/index.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const s=js.indexOf('const FUEL='), e=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/xj_eng.js', js.slice(s,e)+"\nmodule.exports={ROUTES,loadRoute,resolveDay,resolveAll,totals,rt:()=>RT,days:()=>DAYS};");
console.log('引擎切片就绪 → /tmp/xj_eng.js');
