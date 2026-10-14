#!/usr/bin/env node
/* ═══ 规则回归检查 ═══
   这个 session 里定过的规则，逐条验证是否仍在生效。
   测试跑绿 ≠ 规则还在——有些规则是"约定"而非"断言"，容易在后续改动中被悄悄破坏。
*/
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname,'..');
const html=fs.readFileSync(ROOT+'/src/index.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/_rules.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
delete require.cache['/tmp/_rules.js'];
const {ROUTES}=require('/tmp/_rules.js');

const R=[];
const rule=(area,name,pass,detail)=>R.push({area,name,pass:!!pass,detail:detail||''});

/* ── 跨端纪律 ── */
const core=js.slice(a,b);
rule('跨端','引擎层零浏览器 API',
  !/document\.|window\.|localStorage|innerHTML/.test(core),
  (core.match(/document\.|window\.|localStorage/g)||[]).slice(0,3).join(' '));
const HIGH=/\?\.|\?\?|replaceAll|\.flatMap|\.at\(|structuredClone|globalThis/;
const hits=(js.match(HIGH)||[]);
rule('跨端','禁用高版本语法', !hits.length, hits.slice(0,3).join(' '));

/* ── 数据结构纪律 ── */
const REQUIRED=['name','dest','fam','days','lodges','budgets','title','meta','why','tastes','seasons','todos','map'];
const missField=[];
Object.entries(ROUTES).forEach(([id,r])=>{
  REQUIRED.forEach(f=>{ if(r[f]==null) missField.push(`${id}.${f}`); });
});
rule('数据','必备字段齐全', !missField.length, missField.slice(0,4).join(' '));

const tabBad=[];
Object.entries(ROUTES).forEach(([id,r])=>{
  (r.days||[]).forEach((d,i)=>{ if(d.tab!==`D${i+1}`) tabBad.push(`${id} ${d.tab}≠D${i+1}`); });
});
rule('数据','天签连号', !tabBad.length, tabBad.slice(0,3).join(' '));

const lodgeBad=[];
Object.entries(ROUTES).forEach(([id,r])=>{
  const L=r.lodges||[];
  if(L.length!==(r.days||[]).length) lodgeBad.push(`${id} 住宿${L.length}≠天数${(r.days||[]).length}`);
  else if(L.length && L[L.length-1]!==null) lodgeBad.push(`${id} 末天非 null`);
});
rule('数据','住宿链项数与末天', !lodgeBad.length, lodgeBad.slice(0,3).join(' '));

/* ── 展示纪律 ── */
const cardIds=[...new Set([...html.matchAll(/data-rec="([\w-]+)"/g)].map(m=>m[1]))];
const dangling=cardIds.filter(id=>!ROUTES[id]);
rule('展示','卡片指向真实线路', !dangling.length, dangling.join(' '));

const zhIdx=js.indexOf('I18N.zh.cards={'), enIdx=js.indexOf('I18N.en.cards={');
const pick=i=>new Set(((js.slice(i, js.indexOf('\n};',i)).match(/^\s*([\w-]+):\[/gm))||[]).map(x=>x.trim().replace(':[','')));
const zhC=zhIdx>0?pick(zhIdx):new Set(), enC=enIdx>0?pick(enIdx):new Set();
const missEn=[...zhC].filter(x=>!enC.has(x));
rule('展示','中英卡片文案成对', !missEn.length, missEn.slice(0,3).join(' '));

const famDays={};
Object.values(ROUTES).forEach(r=>{ const f=r.fam; (famDays[f]=famDays[f]||[]).push((r.days||[]).length); });
const rangeBad=[];
cardIds.forEach(id=>{
  const r=ROUTES[id]; if(!r) return;
  const m=html.match(new RegExp('data-rec="'+id+'"[\\s\\S]{0,200}?rec-name">([^<]+)<'));
  if(!m) return;
  const dm=m[1].match(/(\d+)(?:[–-](\d+))?\s*[天日]/);
  if(!dm) return;
  const avail=[...new Set(famDays[r.fam])].sort((x,y)=>x-y);
  const lo=+dm[1], hi=dm[2]?+dm[2]:+dm[1];
  if(lo!==avail[0]||hi!==avail[avail.length-1]) rangeBad.push(`${id}「${dm[0]}」≠${avail.join('/')}天`);
});
rule('展示','卡片天数区间与实际一致', !rangeBad.length, rangeBad.slice(0,3).join(' '));

/* ── 文案纪律 ── */
const fakePromise=[];
Object.entries(ROUTES).forEach(([id,r])=>{
  (r.extras||[]).forEach(x=>{
    if(!x.later) return;
    const w=x.later.why||'';
    if(/可.{0,3}加|可排|能加|顺路/.test(w) && !x.later.inDay && !x.later.needDays)
      fakePromise.push(`${id}「${x.later.name}」`);
  });
});
rule('文案','无假承诺', !fakePromise.length, fakePromise.slice(0,3).join(' '));

const placeholder=[];
Object.entries(ROUTES).forEach(([id,r])=>{
  const t=JSON.stringify(r,(k,v)=>typeof v==='function'?undefined:v);
  ['TODO','待补','xxx','undefined','待定'].forEach(w=>{ if(t.includes(w)) placeholder.push(`${id}:${w}`); });
});
rule('文案','无占位符残留', !placeholder.length, [...new Set(placeholder)].slice(0,3).join(' '));

/* ── 视觉纪律（静态可查的部分）── */
rule('视觉','变化数字用等宽',
  /font-variant-numeric:\s*tabular-nums/.test(html),
  '');
rule('视觉','焦点环存在且不进过渡',
  /:focus-visible/.test(html) && !/transition-property:[^;]*box-shadow/.test(html),
  '');
rule('视觉','输入框 ≥16px',
  !/(<input[^>]*font-size:\s*(1[0-5]|[0-9])px)/.test(html), '');
rule('视觉','viewport 未禁用缩放',
  !/maximum-scale=1|user-scalable=no/.test(html), '');
rule('视觉','接驳行用网格统一坐标',
  /\.conn\{[^}]*display:\s*grid/.test(html.replace(/\s+/g,' ')), '');
rule('视觉','嵌套容器内边距归零',
  /\.conn\{[^}]*padding-top:\s*0/.test(html.replace(/\s+/g,' ')), '');

/* ── 交互纪律 ── */
rule('交互','行程页无设计稿',
  /const DRAFT_TRIPS=\[\]/.test(js), '');
rule('交互','行程按线路族去重',
  /famOf/.test(js), '');
rule('交互','导航直接起导航',
  /keywordNavi/.test(js), '');
rule('交互','接驳行无导航按钮',
  !/conn-acts">\$\{A\(navQ/.test(js), '');
rule('交互','错误边界存在',
  /function safeLoad/.test(js), '');
rule('交互','滚动锚点保持',
  /keepScrollAnchor/.test(js), '');

/* ── 内容纪律 ── */
rule('内容','热门目的地自动生成',
  /function hotDests/.test(js) && !/const HOT_DESTS=\[/.test(js), '');
rule('内容','封面数据存在',
  /const COVERS=/.test(js), '');

/* ── 协作纪律 ── */
rule('协作','保留外部 SEO 注入',
  html.includes('GEO:HEAD:START') && html.includes('GEO:BODY:START'), '');
rule('协作','无冲突标记',
  !/^<{7}|^>{7}|^={7}$/m.test(html), '');

/* ── 输出 ── */
const areas={};
R.forEach(r=>{ (areas[r.area]=areas[r.area]||[]).push(r); });
let bad=0;
console.log('══ 规则回归检查 ══');
Object.entries(areas).forEach(([area,list])=>{
  const f=list.filter(x=>!x.pass).length;
  console.log(`\n  【${area}】${f?`✗ ${f}/${list.length}`:`✓ ${list.length} 条全过`}`);
  list.forEach(x=>{ if(!x.pass){ bad++; console.log(`     ✗ ${x.name}  ${x.detail}`); } });
});
console.log(bad? `\n✗ ${bad}/${R.length} 条规则失效` : `\n✅ ${R.length} 条规则全部仍在生效`);
process.exit(bad?1:0);
