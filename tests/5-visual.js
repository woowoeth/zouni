/* 视觉回归（headless Chrome）：真渲染断言 + 三页截图
   需要 puppeteer（npm i puppeteer）；缺失时跳过并提示 */
let puppeteer;
try{ puppeteer=require('puppeteer'); }
catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过视觉回归：未安装 puppeteer（npm i puppeteer 后重跑）'); process.exit(0); } }
const path=require('path'), fs=require('fs');
(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-setuid-sandbox']});
  const pg=await b.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push('pageerror: '+e.message.split('\n')[0]));
  await pg.setViewport({width:390,height:844,deviceScaleFactor:2});
  await pg.goto('file://'+path.resolve(__dirname,'../src/index.html'),{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
  const dir=path.join(__dirname,'shots'); fs.mkdirSync(dir,{recursive:true});
  const check=async(tab,fn)=>{
    const r=await pg.evaluate((tab)=>{
      switchTab(tab);
      const out={tab, overflowX: document.documentElement.scrollWidth>390+2};
      if(tab!=='home'){
        const v=document.getElementById('view-'+tab), rc=v.getBoundingClientRect();
        out.top=Math.round(rc.top); out.h=v.offsetHeight;
      }
      if(tab==='trips'){
        const a=document.querySelector('.add-trip-card');
        out.addFlex=getComputedStyle(a).display==='flex';
      }
      return out;
    },tab);
    await new Promise(r2=>setTimeout(r2,200));
    await pg.screenshot({path:path.join(dir,tab+'.png')});
    if(r.overflowX) errs.push(tab+': 横向溢出');
    if(r.top!=null && (r.top>120||r.top<-10)) errs.push(tab+': 视图起点异常 top='+r.top);
    if(r.h!=null && r.h<200) errs.push(tab+': 内容高度异常 h='+r.h);
    if(r.addFlex===false) errs.push('trips: add-trip-card 非 flex（CSS 解析疑似被破坏）');
    console.log('  📸',tab, JSON.stringify(r));
  };
  await check('trips'); await check('me'); await check('home');
  await b.close();
  if(errs.length){ console.log('✗ 视觉回归 '+errs.length+' 项:\n'+errs.map((e,i)=>(i+1)+'. '+e).join('\n')); process.exit(1); }
  console.log('✅ 视觉回归全绿（截图在 tests/shots/）');
})().catch(e=>{ console.error('ERR',e.message); process.exit(1); });
