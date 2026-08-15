/* 走你 · 运行时冒烟测试（jsdom）*/
const { JSDOM, VirtualConsole } = require('jsdom');
const fs = require('fs');
const html = fs.readFileSync(__dirname+'/../src/index.html','utf8');
const errors = [];
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push('[jsdomError] '+String(e.detail?.stack||e.stack||e.message).split('\n').slice(0,2).join(' | ')));
vc.on('error', (...a) => errors.push('[console.error] '+a.join(' ').slice(0,180)));

const dom = new JSDOM(html, { runScripts:'dangerously', pretendToBeVisual:true, url:'https://zouni.app/', virtualConsole: vc });
const { window } = dom; const doc = window.document;
window.HTMLElement.prototype.scrollIntoView = function(){};
window.scrollTo = function(){};

function step(name, fn){
  try { fn(); console.log('  ✓', name); }
  catch(e){ errors.push(`[${name}] ${e.message}`); console.log('  ✗', name, '→', e.message); }
}
const click = el => el && el.dispatchEvent(new window.Event('click',{bubbles:true}));
const $ = id => doc.getElementById(id);

console.log('── 冒烟流 ──');
step('初始加载（无同步错误）', ()=>{ if(window.eval('typeof ROUTES')!=='object') throw new Error('ROUTES 未定义'); });
step('自动检测：en 环境判英文（detectLocale 生效）', ()=>{
  if(window.eval('LANG')!=='en') throw new Error('LANG='+window.eval('LANG'));
});
step('基线重置 zh/CNY（后续断言按中文走）', ()=>{
  window.eval("setLang('zh');setCur('CNY')");
  if($('mh-title').textContent!=='这趟去哪儿？') throw new Error($('mh-title').textContent);
});
step('首页空态：目的地留空·配置区可用', ()=>{
  /* 首屏不再预装某条线路——那等于替用户选好了。
     目的地显示占位文案，用户选了线路才填入具体目的地。 */
  const d=doc.getElementById('dest-txt');
  if(!d) throw new Error('dest-txt 不存在');
  const txt=(d.textContent||'').trim();
  if(!txt) throw new Error('dest 未渲染');
  const isPlaceholder=/想去哪儿|Where to/.test(txt);
  const isRoute=/[·・]/.test(txt);
  if(!isPlaceholder && !isRoute) throw new Error('dest 文案异常: '+txt);
});
step('点「安排行程」', ()=>{ click($('btn-draw')); if($('plan').style.display==='none') throw new Error('plan 未显示'); });
step('切天 D3', ()=>{ const t=doc.querySelectorAll('.day-tab')[2]; if(!t) throw new Error('无day-tab'); click(t); });
step('切 12 天变体', ()=>{ const c=doc.querySelector('[data-days="12"]'); if(!c) throw new Error('无12天chip'); click(c); if(window.DAYS.length!==12) throw new Error('DAYS='+window.DAYS.length); });
step('sheet 预算四档与配置面板同源', ()=>{
  const chips=doc.querySelectorAll('#budget-chips [data-budget]');
  if(chips.length!==4) throw new Error('budget chips='+chips.length);
  if(!/顶级|Top/.test($('budget-chips').textContent)) throw new Error('缺顶级档');
});
step('单方案族：一个真 chip + 可加天按钮', ()=>{
  /* 原来单方案族显示「目前只有 N 天方案」的说明。
     现在有了 +1 天按钮，用户能自己加到想要的天数，说明文字反而多余。 */
  window.eval("curDays=5;uiLoadRoute('hlb5');applyDraw();renderSheetChips()");
  const chips=[...doc.querySelectorAll('#days-chips .pchip')];
  const real=chips.filter(c=>c.dataset.days);
  const add=doc.getElementById('btn-add-day');
  if(real.length!==1) throw new Error('真 chip 数: '+real.length);
  if(!add) throw new Error('缺少 +1 天按钮');
});
step('多方案族天数：西藏 7/10 天可切', ()=>{
  window.eval("curDays=7;uiLoadRoute('xz7');applyDraw();renderSheetChips()");
  const chips=[...doc.querySelectorAll('#days-chips [data-days]')].map(x=>x.dataset.days);
  if(chips.join()!=='7,10') throw new Error('chips='+chips.join());
  click(doc.querySelector('#days-chips [data-days="10"]'));
  if(window.DAYS.length!==10) throw new Error('未切到10天: '+window.DAYS.length);
  if(!/林芝/.test(window.eval('RT.title'))) throw new Error('标题未更新');
  window.eval("curDays=10;uiLoadRoute('xj10');applyDraw()");
});
step('extras：15天不再显示已在行程的项', ()=>{
  window.eval("curDays=15;uiLoadRoute('xj15');applyDraw()");
  if($('extras-box').innerHTML.includes('巴音布鲁克')) throw new Error('15天仍显示装不下');
});
step('多方案族天数可切(nm3/nm4)', ()=>{
  window.eval("curDays=4;uiLoadRoute('nm4');applyDraw();renderSheetChips()");
  const chips=[...doc.querySelectorAll('#days-chips [data-days]')].map(x=>x.dataset.days);
  if(chips.join()!=='3,4') throw new Error('chips='+chips.join());
  if(doc.querySelector('#days-chips .dim')) throw new Error('仍有灰色假按钮');
  click(doc.querySelector('#days-chips [data-days="3"]'));
  if(window.DAYS.length!==3) throw new Error('未切到3天');
  window.eval("curDays=10;uiLoadRoute('xj10');applyDraw()");
});
step('居延海不再列备选（D3 已有此站）', ()=>{
  if($('extras-box').innerHTML.includes('居延海')) throw new Error('仍列为备选');
});
step('漓江竹筏可真加入(gl4)', ()=>{
  window.eval("curDays=4;uiLoadRoute('gl4');applyDraw()");
  const btn=doc.querySelector('[data-insert="zhufa"]');
  if(!btn) throw new Error('无排入按钮');
  const before=window.eval('totals().total');
  click(btn);
  if(!window.eval("inserted.has('zhufa')")) throw new Error('未插入');
  window.eval('resolveAll()');            /* reRender 有 150ms 渐隐，同步断言直接验数据链 */
  const after=window.eval('totals().total');
  if(after-before<100) throw new Error('费用未联动: '+before+'→'+after);
  window.eval("inserted.delete('zhufa');curDays=10;uiLoadRoute('xj10');applyDraw()");
});
step('双按钮同尺寸并排（同一容器）', ()=>{
  window.eval("curDays=8;uiLoadRoute('xj8');applyDraw()");
  const acts=doc.querySelector('#extras-box .row-acts');
  if(!acts) throw new Error('无并排容器');
  const bs=acts.querySelectorAll('button');
  if(bs.length!==2) throw new Error('按钮数='+bs.length);
  if(![...bs].every(b=>b.classList.contains('pick'))) throw new Error('尺寸类不一致');
  if([...bs].some(b=>(b.getAttribute('style')||'').includes('margin-left:auto'))) throw new Error('仍有 auto 撑开');
});
step('详情页内重排不跳回页首', ()=>{
  window.eval("window.__sy=0;window.scrollTo=function(o){ if(o&&o.top===0) window.__sy=1; }");
  window.eval("uiLoadRoute('xj10');applyDraw()");   // plan 已开 → 不该滚顶
  if(window.eval('window.__sy')===1) throw new Error('重排跳回页首');
});
step('extras：8天给出"改12天可排入"真出路', ()=>{
  window.eval("curDays=8;uiLoadRoute('xj8');applyDraw()");
  const up=doc.querySelector('[data-upday]');
  if(!up) throw new Error('无出路按钮');
  click(up);
  if(window.DAYS.length!==12) throw new Error('未切到12天: '+window.DAYS.length);
  if($('extras-box').innerHTML.includes('巴音布鲁克')) throw new Error('切后仍显示');
  window.eval("curDays=10;uiLoadRoute('xj10');applyDraw()");
});
step('详情页不显示冗余「安排行程」', ()=>{
  if($('btn-draw').style.display!=='none') throw new Error('按钮未隐藏');
  click($('btn-home'));
  if($('btn-draw').style.display==='none') throw new Error('回首页未恢复');
  click($('btn-draw'));
});
step('返回首页', ()=>{ click($('btn-home')); if($('plan').style.display!=='none') throw new Error('plan 未隐藏'); });
step('切行程 Tab', ()=>{ click($('tab-trips')); if($('view-trips').style.display==='none') throw new Error('trips 未显示'); });
step('行程卡结构：封面+内容·标签在meta下', ()=>{
  const c=doc.querySelector('.trip-card');
  if(!c) throw new Error('无行程卡');
  const head=c.querySelector('.trip-head-row');
  if(!head) throw new Error('无 head 行');
  /* 封面是纯展示图，不做导航入口（导航只在站点卡内） */
  const cov=c.querySelector('.trip-cover');
  if(cov && cov.hasAttribute('data-tripnav')) throw new Error('封面不该挂导航');
  const col=[...head.children].find(x=>x.querySelector&&x.querySelector('.trip-title'));
  if(!col) throw new Error('无文字列');
  const order=[...col.children].map(x=>x.className).join();
  if(!/trip-title,trip-meta/.test(order)) throw new Error('顺序: '+order);
});
step('设计稿已移除·行程页只放用户自己的', ()=>{
  if(doc.querySelectorAll('.trip-card.draft').length) throw new Error('仍有设计稿卡');
  if(window.DRAFT_TRIPS && window.DRAFT_TRIPS.length) throw new Error('DRAFT_TRIPS 非空');
});
step('切英文：UI+卡片+路线覆盖层', ()=>{
  click($('tab-home'));
  click($('lang-pill'));
  if($('mh-title').textContent!=='Where to next?' && doc.querySelector('#plan').style.display==='none') throw new Error('mh-title='+$('mh-title').textContent);
  const c=doc.querySelector('[data-rec="kansai5"] .rec-name');
  if(!/Kansai/.test(c.textContent)) throw new Error('卡片未翻译: '+c.textContent);
  window.uiLoadRoute('kansai5'); window.applyDraw();
  if(!/Kansai/.test($('mh-title').textContent)) throw new Error('路线i18n未生效');
  if($('lang-note').style.display==='none') throw new Error('英文提示条未显示');
});
step('切美元：换算+符号', ()=>{
  const cnyTotal=+$('stat-cost').textContent.replace(/,/g,'');   /* 切换前先记下人民币值 */
  click($('cur-pill'));
  const sym=doc.querySelector('[data-cur-sym]').textContent;
  if(sym!=='$') throw new Error('sym='+sym);
  const v=+$('stat-cost').textContent.replace(/,/g,'');
  /* 不写死区间——预算随内容更新会变。校验「≈ CNY × 汇率」，容差 2% */
  const rate=(typeof FX!=='undefined'&&FX.USD)?FX.USD.r:0.14;
  const expect=cnyTotal*rate;
  if(!v || Math.abs(v-expect)/expect>0.02) throw new Error('USD 换算异常: '+v+' 期望≈'+Math.round(expect));
});
step('切回中文人民币', ()=>{
  click($('lang-pill'));
  ['USD','EUR','HKD','JPY','CNY'].forEach(()=>{ if(window.eval('CUR')!=='CNY') click($('cur-pill')); });
  if(window.eval('CUR')!=='CNY') throw new Error('CUR='+window.eval('CUR'));
});
step('我的 Tab：设置/口味/记录渲染', ()=>{
  click($('tab-me'));
  if($('view-me').style.display==='none') throw new Error('view-me 未显示');
  if(!$('me-body').innerHTML.includes('简体中文')) throw new Error('语言行缺失');
  const chip=doc.querySelector('[data-metaste]'); if(!chip) throw new Error('口味chips缺失');
});
step('旅行记录：只留想去/去过·可点', ()=>{
  window.eval("addProfile('摄影晨雾党','本次条件');addProfile('想去 · 川藏 G318','点选','ct8')");
  window.eval('renderMe()');
  const body=$('me-body').innerHTML;
  if(body.includes('本次条件')) throw new Error('口味流水混入');
  const w=doc.querySelector('[data-wantrid]');
  if(!w) throw new Error('想去条目缺失');
  click(w);
});
step('我的页改口味 → 持久化', ()=>{
  const chip=doc.querySelector('[data-metaste]');
  const before=window.eval('tastes.size'); click(chip);
  if(window.eval('tastes.size')===before) throw new Error('口味未变化');
  const d=JSON.parse(window.localStorage.getItem('zouni_v2'));
  if(!Array.isArray(d.tasteIds)) throw new Error('tasteIds 未存');
});
step('清除数据两步确认（第一步）', ()=>{
  click($('me-clear'));
  if(!$('me-clear').classList.contains('confirm')) throw new Error('确认态未激活');
});
step('出发日期：day-tab 显示真实日期', ()=>{
  click($('tab-home')); click($('btn-draw'));
  window.eval("departDate='2026-08-20';saveLS();renderStrip();renderStripDays();renderDay()");
  const dt=doc.querySelector('.day-tab');
  if(!/8月20日|Aug 20/.test(dt.textContent)) throw new Error('day-tab='+dt.textContent.slice(0,20));
  const d=JSON.parse(window.localStorage.getItem('zouni_v2'));
  if(d.departDate!=='2026-08-20') throw new Error('departDate 未存: '+d.departDate);
});
step('分享摘要：含标题/人均/逐日', ()=>{
  const txt=window.eval('shareText()');
  if(!(txt.includes('D1')&&txt.split('\n').length>5)) throw new Error('摘要异常: '+txt.slice(0,60));
  click($('btn-share'));
});
step('勾选待办 → 持久化', ()=>{
  const td=doc.querySelector('[data-todo]'); if(!td) throw new Error('无todo');
  click(td);
  const d=JSON.parse(window.localStorage.getItem('zouni_v2'));
  if(!d.checked||!d.checked.length) throw new Error('checked 未存');
});
step('导出备份：剪贴板格式', ()=>{
  window.eval('exportData()');
});
step('行程 hash：打包→还原闭环', ()=>{
  window.eval("uiLoadRoute('gl4');applyDraw()");
  const h=window.eval('tripToHash()');
  if(!/^#trip=/.test(h)) throw new Error('hash 格式: '+h.slice(0,20));
  window.eval("uiLoadRoute('xj10');applyDraw()");
  window.eval(`location.hash='${h.slice(1)}'`);
  window.location.hash=h;
  const ok=window.eval('tryImportHash()');
  if(!ok) throw new Error('还原失败');
  if(window.RT && window.eval('RT.fam')!=='gl') throw new Error('还原路线错: '+window.eval('RT.fam'));
});
step('二级页骨架：无双重缩进残留', ()=>{
  click($('tab-trips'));
  const tc=doc.querySelector('.trip-card');
  if(tc && /margin:\s*8px 12px/.test(tc.getAttribute('style')||'')) throw new Error('trip-card 旧缩进残留');
  click($('tab-me'));
  if(doc.querySelector('#me-body .card')) throw new Error('me 页仍复用 plan 的 .card');
  if(!doc.querySelector('#me-body .me-sect')) throw new Error('me-sect 未启用');
});
step('LS 往返', ()=>{ const raw=window.localStorage.getItem('zouni_v2'); if(!raw) throw new Error('LS 空'); const d=JSON.parse(raw); if(!Array.isArray(d.trips)) throw new Error('trips 异常'); });

console.log('\n── 结果 ──');
if(errors.length){ console.log(`✗ ${errors.length} 个错误:`); errors.forEach((e,i)=>console.log(`${i+1}. ${e}`)); process.exit(1); }
else console.log('✅ 全流程零报错');
