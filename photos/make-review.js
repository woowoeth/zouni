#!/usr/bin/env node
/* 生成核对表：把 130 张实景图铺出来，一眼扫过去把不对的打叉。
   打叉的会记进 reject.json，重跑构建时自动降级为地图。 */
const fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname);
const db=JSON.parse(fs.readFileSync(ROOT+'/photos.json','utf8'));
/* 图片 base64 内嵌 —— 外链在预览器/CSP 受限环境全都加载不出来，内嵌才可靠 */
const thumbs=fs.existsSync(ROOT+'/thumbs.json')? JSON.parse(fs.readFileSync(ROOT+'/thumbs.json','utf8')) : {};
const src=k=>thumbs[k]? 'data:image/jpeg;base64,'+thumbs[k] : '';

/* 取出每个 key 对应的中文名，方便核对 */
const html=fs.readFileSync(ROOT+'/index.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
fs.writeFileSync('/tmp/_rv.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
const {ROUTES}=require('/tmp/_rv.js');
const names={};
Object.entries(ROUTES).forEach(([id,R])=>{
  names['route:'+id]=(R.title||R.name||id).replace(/^[^\s]+\s/,'');
  (R.days||[]).forEach(d=>(d.stops||[]).forEach(s=>{ if(s.k) names['poi:'+s.k]=s.name||s.k; }));
});

const photos=Object.entries(db).filter(([k,v])=>v.type==='photo');
const maps=Object.entries(db).filter(([k,v])=>v.type==='map');
const blanks=Object.entries(db).filter(([k,v])=>v.type==='none');

const card=(k,v)=>`
<label class="it" data-k="${k}">
  <input type="checkbox" class="cb">
  <div class="im"><img src="${src(k)}" onerror="this.parentElement.classList.add('err')"></div>
  <div class="tx">
    <div class="nm">${names[k]||k}</div>
    <div class="fl">${(v.file||'').replace(/_/g,' ').slice(0,42)}</div>
    <div class="lc">${v.src||''} · ${v.license||''}</div>
  </div>
</label>`;

const out=`<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>配图核对表 · ${photos.length} 张实景图</title>
<style>
:root{--paper:#f0f0ec;--white:#fafaf7;--ink:#2a2e2c;--ink-50:#686e68;--line:rgba(42,46,44,.08);--bad:#994a40}
*{box-sizing:border-box}
body{background:var(--paper);color:var(--ink);margin:0;padding:14px 14px 90px;
  font:13px/1.5 -apple-system,'PingFang SC',sans-serif;-webkit-font-smoothing:antialiased}
h1{font-size:17px;margin:0 0 4px}
.sub{font-size:12px;color:var(--ink-50);margin-bottom:14px;line-height:1.5}
.eyebrow{font-size:11px;font-weight:700;letter-spacing:.07em;color:var(--ink-50);margin:20px 0 8px}
.grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px}
.it{background:var(--white);border-radius:10px;box-shadow:0 0 0 1px var(--line);
  overflow:hidden;display:block;position:relative;cursor:pointer}
.it .cb{position:absolute;left:7px;top:7px;z-index:3;width:20px;height:20px;accent-color:var(--bad);cursor:pointer}
.im{aspect-ratio:4/3;background:#e6e8e1;position:relative}
.im img{width:100%;height:100%;object-fit:cover;display:block}
.im.err::after{content:'加载失败';position:absolute;inset:0;display:flex;align-items:center;
  justify-content:center;font-size:11px;color:var(--ink-50)}
.tx{padding:7px 9px 9px}
.nm{font-size:12px;font-weight:700;line-height:1.3;margin-bottom:2px}
.fl{font-size:10px;color:var(--ink-50);line-height:1.3;word-break:break-all}
.lc{font-size:9px;color:var(--ink-50);opacity:.75;margin-top:3px}
.it:has(.cb:checked){box-shadow:0 0 0 2px var(--bad)}
.it:has(.cb:checked) .im{opacity:.35}
.it:has(.cb:checked)::after{content:'✕ 不对';position:absolute;right:7px;top:7px;z-index:3;
  background:var(--bad);color:#fff;font-size:10px;font-weight:700;padding:2px 6px;border-radius:4px}
.maps{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.mp{background:var(--white);border-radius:8px;box-shadow:0 0 0 1px var(--line);overflow:hidden;text-align:center}
.mp .im{aspect-ratio:1}
.mp .nm{font-size:10px;padding:5px 4px;line-height:1.25}
.bar{position:fixed;left:0;right:0;bottom:0;background:var(--white);
  box-shadow:0 -1px 0 var(--line);padding:11px 14px;display:flex;gap:10px;align-items:center;z-index:9}
.cnt{font-size:12px;color:var(--ink-50);flex:1}
.btn{background:var(--ink);color:#fff;border:0;border-radius:8px;padding:9px 15px;
  font-size:13px;font-weight:700;cursor:pointer}
#prog{position:fixed;left:14px;right:14px;top:10px;z-index:30;background:rgba(42,46,44,.92);
  color:#fff;font-size:12px;padding:8px 12px;border-radius:8px;text-align:center;transition:opacity .4s}
#prog.done{opacity:0;pointer-events:none}
#outbox{position:fixed;inset:8% 6%;background:var(--white);border-radius:12px;padding:16px;
  display:none;z-index:20;box-shadow:0 8px 40px rgba(0,0,0,.2);overflow:auto}
#outbox textarea{width:100%;height:60%;font:11px/1.4 monospace;border:1px solid var(--line);
  border-radius:6px;padding:8px;resize:none}
</style><body>
<h1>配图核对表</h1>
<div class="sub">
  实景图 <b>${photos.length}</b> 张 · 地图 <b>${maps.length}</b> 张 · 无图 <b>${blanks.length}</b> 个<br>
  <b>只需做一件事</b>：扫一遍实景图，把<b>明显不是该景点</b>的勾上。勾中的会自动降级为地图（位置一定准）。<br>
  地图那一栏不用看——坐标是精确的。<br><b>图片已全部内嵌</b>，断网也能看。
</div>

<div class="eyebrow">实景图 · 请核对（${photos.length}）</div>
<div class="grid">${photos.map(([k,v])=>card(k,v)).join('')}</div>

<div class="eyebrow">地图兜底 · 无需核对（${maps.length}）</div>
<div class="maps">${maps.map(([k,v])=>`<div class="mp"><div class="im"><img src="${src(k)}"></div><div class="nm">${names[k]||k}</div></div>`).join('')}</div>

${blanks.length? `<div class="eyebrow">仍无图（${blanks.length}）· 我会再补</div>
<div class="sub">${blanks.map(([k])=>names[k]||k).join(' · ')}</div>`:''}

<div class="bar">
  <span class="cnt" id="cnt">已勾选 0 张</span>
  <button class="btn" onclick="exp()">导出结果</button>
</div>
<div id="outbox">
  <div style="font-size:13px;font-weight:700;margin-bottom:8px">把下面这段发给我即可</div>
  <textarea id="ta" readonly></textarea>
  <div style="margin-top:10px;display:flex;gap:8px">
    <button class="btn" onclick="document.getElementById('ta').select();document.execCommand('copy')">复制</button>
    <button class="btn" style="background:#686e68" onclick="document.getElementById('outbox').style.display='none'">关闭</button>
  </div>
</div>
<script>
const cnt=document.getElementById('cnt');
document.addEventListener('change',()=>{
  const n=document.querySelectorAll('.cb:checked').length;
  cnt.textContent='已勾选 '+n+' 张'+(n?'（将降级为地图）':'');
});
function exp(){
  const bad=[...document.querySelectorAll('.cb:checked')].map(c=>c.closest('.it').dataset.k);
  document.getElementById('ta').value=JSON.stringify(bad,null,0);
  document.getElementById('outbox').style.display='block';
}
</script></body></html>`;

fs.writeFileSync(ROOT+'/review.html', out);
console.log(`核对表已生成：review.html`);
console.log(`  实景图 ${photos.length} 张待核对 · 地图 ${maps.length} 张 · 无图 ${blanks.length} 个`);
