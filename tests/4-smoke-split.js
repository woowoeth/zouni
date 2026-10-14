/* 三文件版冒烟：从文件加载，允许外部 script */
const { JSDOM, VirtualConsole } = require('jsdom');
const errors=[];
const vc=new VirtualConsole();
vc.on('jsdomError',e=>errors.push('[jsdomError] '+String(e.detail?.stack||e.stack||e.message).split('\n').slice(0,2).join(' | ')));
JSDOM.fromFile(__dirname+'/../src/zouni.html',{
  runScripts:'dangerously', resources:'usable', pretendToBeVisual:true, virtualConsole:vc,
}).then(dom=>{
  const {window}=dom, doc=window.document;
  window.HTMLElement.prototype.scrollIntoView=function(){};
  window.scrollTo=function(){};
  setTimeout(()=>{
    try{
      const $=id=>doc.getElementById(id);
      const click=el=>el&&el.dispatchEvent(new window.Event('click',{bubbles:true}));
      /* 首屏是空态（目的地留空），有文案即说明脚本跑起来了 */
      if(!($('dest-txt').textContent||'').trim()) errors.push('三文件版：dest 未渲染（脚本未跑起来）');
      click($('btn-draw'));
      if($('plan').style.display==='none') errors.push('三文件版：安排行程失败');
      window.uiLoadRoute('kansai5'); window.applyDraw();
      if(!$('cost-note').textContent.includes('ICOCA')) errors.push('三文件版：国外线渲染异常');
    }catch(e){ errors.push('三文件交互: '+e.message); }
    console.log(errors.length?('✗ '+errors.length+' 个错误:\n'+errors.map((e,i)=>(i+1)+'. '+e).join('\n')):'✅ 三文件版全绿');
    process.exit(errors.length?1:0);
  },600);
}).catch(e=>{ console.log('加载失败:',e.message); process.exit(1); });
