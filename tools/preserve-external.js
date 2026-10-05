#!/usr/bin/env node
/* ═══ 发布前：保留其他进程注入的内容 ═══
   线上 index.html 有另一个 SEO 工作流在注入 <!--GEO:HEAD--> 与 <!--GEO:BODY--> 两块。
   我直接覆盖 index.html 会把它冲掉，对方下次跑又加回来 —— 来回打架。
   发布前先从线上取回这两块，合进我的产物再推。

   用法：node preserve-external.js <本地产物> <线上index.html>
*/
const fs=require('fs');
const [,,localPath, livePath]=process.argv;
if(!localPath||!livePath){ console.log('用法: node preserve-external.js local.html live.html'); process.exit(1); }

const BLOCKS=[
  {name:'GEO:HEAD', re:/<!--GEO:HEAD:START-->[\s\S]*?<!--GEO:HEAD:END-->/, anchor:'</head>', where:'before'},
  {name:'GEO:BODY', re:/<!--GEO:BODY:START-->[\s\S]*?<!--GEO:BODY:END-->/, anchor:'</body>', where:'before'}
];

let mine=fs.readFileSync(localPath,'utf8');
const live=fs.existsSync(livePath)? fs.readFileSync(livePath,'utf8') : '';
if(!live){ console.log('  线上文件不存在，跳过'); process.exit(0); }

let kept=0, already=0;
BLOCKS.forEach(b=>{
  const m=live.match(b.re);
  if(!m){ console.log(`  – ${b.name} 线上没有，跳过`); return; }
  if(b.re.test(mine)){
    /* 已有则用线上最新版替换，保证不落后 */
    mine=mine.replace(b.re, m[0]);
    already++;
    console.log(`  ↻ ${b.name} 已存在，更新为线上版（${m[0].length} 字节）`);
  }else{
    const i=mine.lastIndexOf(b.anchor);
    if(i<0){ console.log(`  ✗ ${b.name} 找不到锚点 ${b.anchor}`); return; }
    mine=mine.slice(0,i)+m[0]+'\n'+mine.slice(i);
    kept++;
    console.log(`  ✓ ${b.name} 已保留（${m[0].length} 字节）`);
  }
});

/* 冲突标记检查：曾经有一次 merge conflict 被提交进 index.html */
const conflicts=(mine.match(/<{7}|>{7}|^={7}$/gm)||[]).length;
if(conflicts){ console.log(`  ✗ 检测到 ${conflicts} 处冲突标记，中止`); process.exit(1); }

fs.writeFileSync(localPath, mine);
console.log(`  保留 ${kept} 块 · 更新 ${already} 块 · 产物 ${(mine.length/1024).toFixed(0)}KB`);
