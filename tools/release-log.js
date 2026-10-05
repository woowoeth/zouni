#!/usr/bin/env node
/* ═══ 发布日志 ═══
   SOP 说「每次发布后 5 分钟复盘」，实际零记录——因为它靠自觉。
   这个脚本把复盘变成发布的必经步骤：不填就没法生成日志，日志缺失下次发布会提醒。

   用法：
     node release-log.js --ver v43 --what "改了什么" --bug "踩了什么坑" --guard "加了哪条守卫"
     node release-log.js --check     # 检查上次发布有没有留下复盘
*/
const fs=require('fs'), path=require('path');
const LOG=path.resolve(__dirname,'../docs/release-log.md');
const args=process.argv.slice(2);
const get=k=>{ const i=args.indexOf('--'+k); return i>-1?args[i+1]:null; };

if(args.includes('--check')){
  if(!fs.existsSync(LOG)){ console.log('⚠ 尚无发布日志'); process.exit(0); }
  const txt=fs.readFileSync(LOG,'utf8');
  const rows=txt.split('\n').filter(l=>l.startsWith('| v'));
  const last=rows[rows.length-1]||'';
  const cols=last.split('|').map(x=>x.trim());
  const missing=[];
  if(!cols[3]||cols[3]==='—') missing.push('踩了什么坑');
  if(!cols[4]||cols[4]==='—') missing.push('加了哪条守卫');
  console.log(`  最近发布：${cols[1]||'?'}`);
  console.log(missing.length? `  ⚠ 复盘不完整，缺：${missing.join('、')}` : '  ✓ 复盘完整');
  console.log(`  累计发布 ${rows.length} 次`);
  process.exit(0);
}

const ver=get('ver'), what=get('what');
if(!ver||!what){
  console.log('用法: node release-log.js --ver v43 --what "改了什么" [--bug "踩了什么坑"] [--guard "加了哪条守卫"]');
  process.exit(1);
}
const bug=get('bug')||'—';
const guard=get('guard')||'—';
const date=new Date().toISOString().slice(0,10);

if(!fs.existsSync(LOG)){
  fs.writeFileSync(LOG, `# 走你 · 发布日志

> 每次发布必填。SOP 里「发布后 5 分钟复盘」曾经零执行，因为它靠自觉；
> 现在焊进发布流程：不填就没有日志，下次发布前 \`--check\` 会提醒。
>
> **三个问题**：这轮改了什么 · 踩了什么坑 · 坑是否已升级为自动守卫。
> 第三列长期是「—」，说明在重复踩坑而没有沉淀。

| 版本 | 日期 | 改了什么 | 踩了什么坑 | 升级为守卫 |
|---|---|---|---|---|
`);
}
fs.appendFileSync(LOG, `| ${ver} | ${date} | ${what} | ${bug} | ${guard} |\n`);

/* 统计：多少次发布留下了坑与守卫 */
const rows=fs.readFileSync(LOG,'utf8').split('\n').filter(l=>l.startsWith('| v'));
const withBug=rows.filter(l=>{ const c=l.split('|').map(x=>x.trim()); return c[4]&&c[4]!=='—'; }).length;
const withGuard=rows.filter(l=>{ const c=l.split('|').map(x=>x.trim()); return c[5]&&c[5]!=='—'; }).length;
console.log(`✓ 已记入发布日志：${ver}`);
console.log(`  累计 ${rows.length} 次发布 · ${withBug} 次记录了踩坑 · ${withGuard} 次升级为守卫`);
if(withBug>withGuard) console.log(`  ⚠ 有 ${withBug-withGuard} 次踩坑没有沉淀成守卫，同类问题会复发`);
