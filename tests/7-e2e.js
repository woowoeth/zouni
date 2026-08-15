/* E2E · 真浏览器交互链（webapp-testing 方法论：networkidle → 侦察 → 真点击 → 断言）*/
let puppeteer;
try{ puppeteer=require('puppeteer'); }catch(e){ try{ puppeteer=require('/tmp/node_modules/puppeteer'); }
catch(e2){ console.log('⚠ 跳过 E2E：未安装 puppeteer'); process.exit(0); } }
const path=require('path');
(async()=>{
  const b=await puppeteer.launch({args:['--no-sandbox','--disable-setuid-sandbox']});
  const pg=await b.newPage();
  const errs=[];
  pg.on('pageerror',e=>errs.push('pageerror: '+e.message.split('\n')[0]));
  pg.on('console',m=>{ if(m.type()==='error') errs.push('console: '+m.text().slice(0,120)); });
  await pg.setViewport({width:390,height:844});
  await pg.goto('file://'+path.resolve(__dirname,'../src/index.html'),{waitUntil:'networkidle0'});
  await pg.evaluate(()=>{ setLang('zh'); setCur('CNY'); });
  const step=async(name,fn)=>{ try{ await fn(); console.log('  ✓',name); }
    catch(e){ errs.push(`[${name}] ${e.message.split('\n')[0]}`); console.log('  ✗',name); } };
  const vis=sel=>pg.evaluate(s=>{ const el=document.querySelector(s);
    if(!el) return false; const r=el.getBoundingClientRect();
    return r.width>0&&r.height>0&&getComputedStyle(el).visibility!=='hidden'; },sel);

  await step('真点「安排行程」→ 计划页可见', async()=>{
    await pg.click('#btn-draw');
    if(!await vis('#plan')) throw new Error('plan 不可见');
    if(!await vis('.day-tab.on')) throw new Error('天签不可见');
  });
  await step('真点 D3 天签 → 内容切换', async()=>{
    const before=await pg.$eval('#day-sub',e=>e.textContent);
    await pg.evaluate(()=>document.querySelectorAll('.day-tab')[2].click());
    await new Promise(r=>setTimeout(r,450));
    const after=await pg.$eval('#day-sub',e=>e.textContent);
    if(before===after) throw new Error('切天无变化');
  });
  await step('目的地按钮 → 搜索覆层 → 真输入过滤', async()=>{
    await pg.click('#btn-home'); await pg.click('#dest');
    await pg.type('#search-input','张家界',{delay:20});
    await new Promise(r=>setTimeout(r,120));
    if(!await vis('[data-srid="zjj4"]')) throw new Error('结果未出现');
  });
  await step('结果 → 配置面板 → 生成（跨层全链）', async()=>{
    await pg.click('[data-srid="zjj4"]');
    if(!await vis('#sc-go')) throw new Error('配置未开');
    await pg.click('#sc-go');
    await new Promise(r=>setTimeout(r,200));
    const fam=await pg.evaluate(()=>RT.fam);
    if(fam!=='zjj') throw new Error('装载错: '+fam);
    if(!await vis('#plan')) throw new Error('结果不可见');
  });
  await step('行程 Tab → 卡片存在 → 两步删除', async()=>{
    await pg.click('#tab-trips');
    if(!await vis('.trip-card:not(.draft)')) throw new Error('无行程卡');
    await pg.click('[data-tripdel]'); await pg.click('[data-tripdel].confirm');
    await new Promise(r=>setTimeout(r,120));
  });
  await step('我的 Tab → 真点语言行 → 英文态', async()=>{
    await pg.click('#tab-me'); await pg.click('#me-lang');
    await new Promise(r=>setTimeout(r,120));
    const tt=await pg.$eval('[data-i18n="me.head"]',e=>e.textContent);
    if(tt!=='Me') throw new Error('未切英文: '+tt);
    await pg.click('#me-lang');
  });
  await step('页面全程零控制台错误', async()=>{
    const hard=errs.filter(e=>/pageerror|console/.test(e));
    if(hard.length) throw new Error(hard[0]);
  });
  await b.close();
  if(errs.length){ console.log('✗ E2E '+errs.length+' 项:\n'+errs.map((e,i)=>(i+1)+'. '+e).join('\n')); process.exit(1); }
  console.log('✅ E2E 真浏览器全链零错误');
})().catch(e=>{ console.error('ERR',e.message); process.exit(1); });
