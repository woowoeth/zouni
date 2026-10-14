// 设计稿 vs 网站：逐个组件量样式（字号、字重、行高、字间距、颜色、尺寸、内边距）
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const KEYS=['fontSize','fontWeight','lineHeight','letterSpacing','fontFamily','color','backgroundColor','paddingTop','paddingLeft','paddingBottom'];
const grab=async (pg,specs)=>pg.evaluate((specs,KEYS)=>{
  const byText=(t,tag)=>[...document.querySelectorAll(tag||'*')].find(e=>e.childElementCount===0&&e.textContent.trim()===t)||[...document.querySelectorAll(tag||'*')].find(e=>e.textContent.trim()===t);
  const out={};
  for(const [name,how] of specs){ let el=null;
    try{ if(how.startsWith('css:')) el=document.querySelector(how.slice(4)); else if(how.startsWith('text:')) el=byText(how.slice(5)); else if(how.startsWith('textp:')){ el=byText(how.slice(6)); el=el&&el.parentElement; } else if(how.startsWith('js:')) el=eval(how.slice(3)); }catch(e){}
    if(!el){ out[name]=null; continue; }
    const cs=getComputedStyle(el), r=el.getBoundingClientRect(); const o={w:Math.round(r.width),h:Math.round(r.height)};
    for(const k of KEYS){ let v=cs[k]; if(k==='fontFamily') v=v.split(',')[0].replace(/"/g,''); o[k]=v; } out[name]=o; }
  return out; },specs,KEYS);
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async (u)=>{ const pg=await b.newPage(); await pg.setViewport({width:390,height:844}); await pg.goto(u,{waitUntil:'networkidle0'}); await sleep(1200); return pg; };
  const pairs={
   route:[
    ['hero',            'js:document.querySelector("h1").closest("div").parentElement', 'css:.hero'],
    ['标题',            'js:document.querySelector("h1")', 'css:.hero h1'],
    ['封面小字',        'text:城市慢游 · 三天', 'css:.kick'],
    ['返回方块',        'js:document.querySelector("a[aria-label=\'返回\']")', 'css:.sq.l'],
    ['概览天数',        'js:[...document.querySelectorAll("span")].find(s=>/^3/.test(s.textContent.trim())&&getComputedStyle(s).fontSize==="28px")', 'css:.glance b.big'],
    ['概览说明',        'text:地铁、打车加步行', 'js:[...document.querySelectorAll(".glance small")][1]'],
    ['概览价格',        'text:¥1,800–2,600', 'css:.glance b.price'],
    ['出发前卡',        'textp:出发前', 'css:.pre'],
    ['出发前标',        'text:出发前', 'css:.pre h2'],
    ['出发前条目',      'text:陕西历史博物馆提前在官方渠道预约', 'js:document.querySelector(".pre label span")'],
    ['怎么排标题',      'text:3 天，怎么排', 'css:.overview h2'],
    ['怎么排序号',      'text:01', 'css:.overview b'],
    ['怎么排标题行',    'text:城墙 · 钟鼓楼 · 回民街', 'css:.overview .ot strong'],
    ['怎么排右侧',      'text:13:30 走', 'css:.overview em'],
    ['日大号',          'js:[...document.querySelectorAll("span")].find(s=>s.textContent.trim()==="01"&&parseFloat(getComputedStyle(s).fontSize)>40)', 'css:.day .no'],
    ['日标题',          'js:[...document.querySelectorAll("h2")].find(h=>/城墙/.test(h.textContent))', 'css:.day h2'],
    ['日小字',          'js:[...document.querySelectorAll("span")].find(s=>/^第一天/.test(s.textContent.trim()))', 'css:.day header small'],
    ['数字格标签',      'js:[...document.querySelectorAll("span")].find(s=>s.textContent.trim()==="日出")', 'css:.fx small'],
    ['数字格值',        'js:[...document.querySelectorAll("span")].find(s=>s.textContent.trim()==="日出").nextElementSibling', 'css:.fx b'],
    ['气温行',          'js:[...document.querySelectorAll("span,p,div")].find(s=>s.childElementCount===0&&/^往年/.test(s.textContent.trim()))', 'css:.day .cl'],
    ['每天一句话',      'js:[...document.querySelectorAll("p,span,div")].find(s=>s.childElementCount===0&&/^下午上城墙/.test(s.textContent.trim()))', 'css:.day .lead'],
    ['时间',            'text:13:45', 'js:[...document.querySelectorAll(".r time")].find(t=>t.textContent==="13:45")'],
    ['站名',            'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&s.textContent.trim()==="西安城墙 · 永宁门")', 'js:[...document.querySelectorAll(".r .m")].find(m=>/永宁门/.test(m.textContent))'],
    ['站名下小字',      'text:2 小时 30 分', 'js:[...document.querySelectorAll(".r .s")].find(m=>/2 小时 30 分/.test(m.textContent))'],
    ['出发行文字',      'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&s.textContent.trim()==="出发 → 西安城墙")', 'js:[...document.querySelectorAll(".r.dep .m")][0]'],
    ['地图图标',        'js:document.querySelector("a[aria-label^=\'用高德地图打开\']")', 'js:document.querySelector(".r .ic")'],
    ['懂一点卡',        'textp:懂一点', 'css:.story'],
    ['懂一点文字',      'js:[...document.querySelectorAll("span,p")].find(s=>s.childElementCount===0&&/^西安城墙是明代/.test(s.textContent.trim()))', 'css:.story p'],
    ['底栏',            'js:[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="收进行程").parentElement', 'css:.dock'],
    ['底栏按钮',        'js:[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="收进行程")', 'css:.dock button'],
    ['天数条',          'js:[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="1"&&b.parentElement.childElementCount===3)', 'css:.daynav a']],
   atlas:[
    ['返回本期',        'js:document.querySelector("a[href=\'Main.dc.html\']")', 'css:.pagehead a'],
    ['标题',            'js:document.querySelector("h1")', 'css:.where h1'],
    ['页签',            'js:[...document.querySelectorAll("button")].find(b=>/^国内/.test(b.textContent.trim()))', 'css:.tabs button'],
    ['月份',            'js:[...document.querySelectorAll("button")].find(b=>b.textContent.trim()==="10月")', 'css:.mon button.on'],
    ['推荐语',          'js:[...document.querySelectorAll("span,p")].find(s=>s.childElementCount===0&&/正好去/.test(s.textContent))', 'css:.goodline'],
    ['筛选按钮',        'js:document.querySelector("button[aria-label=\'筛选\']")', 'css:.ftog'],
    ['符合数',          'js:[...document.querySelectorAll("span")].find(s=>/^符合的/.test(s.textContent.trim()))', 'css:.cnt'],
    ['地区标',          'text:华北', 'js:document.querySelector(".rh")'],
    ['卡片',            'js:[...document.querySelectorAll("div")].find(d=>d.style.background&&/235, 232, 223|ebe8df/.test(d.style.background)&&/北京/.test(d.textContent)&&d.textContent.length<400)', 'css:.card a'],
    ['卡片地名',        'js:[...document.querySelectorAll("span,h3")].find(s=>s.childElementCount===0&&s.textContent.trim()==="北京")', 'css:.card h3'],
    ['卡片标签',        'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&s.textContent.trim()==="正好")', 'css:.card .fit'],
    ['卡片气温',        'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&/^10 月：白天 18/.test(s.textContent.trim()))', 'css:.card .cl'],
    ['卡片看',          'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&s.textContent.trim()==="看")', 'js:document.querySelector(".card .kv b")']],
   main:[
    ['刊头',            'js:[...document.querySelectorAll("span,h1,div")].find(s=>s.childElementCount===0&&s.textContent.trim()==="走你")', 'css:.mast h1'],
    ['封面标题',        'js:[...document.querySelectorAll("h1,h2,span")].find(s=>s.childElementCount===0&&/去西藏正好/.test(s.textContent))', 'css:.cv h2'],
    ['翻开按钮',        'js:[...document.querySelectorAll("a,button")].find(b=>/^翻开/.test(b.textContent.trim())&&b.offsetHeight>40)', 'css:.cv .go'],
    ['目录标题',        'text:目录', 'js:document.querySelector(".toc h2")'],
    ['目录序号',        'js:[...document.querySelectorAll("span")].find(s=>s.childElementCount===0&&s.textContent.trim()==="02")', 'css:.items .num'],
    ['目录标题行',      'js:[...document.querySelectorAll("span,h3")].find(s=>s.childElementCount===0&&/^山西 · 平遥/.test(s.textContent.trim()))', 'css:.items h3'],
    ['目录小图',        'js:document.querySelector("img[style*=\'88px\']")||[...document.querySelectorAll("span")].find(s=>s.textContent.trim()==="平遥"&&s.offsetWidth>80)', 'css:.items .tile']]};
  const urls={route:['file:///tmp/dc-test/Route.dc.html#xa3','http://localhost:8765/trip/xa3/'],atlas:['file:///tmp/dc-test/Atlas.dc.html','http://localhost:8765/where/'],main:['file:///tmp/dc-test/Main.dc.html','http://localhost:8765/']};
  const report={};
  for (const k of Object.keys(pairs)) { const a=await open(urls[k][0]); const A=await grab(a,pairs[k].map(x=>[x[0],x[1]])); await a.close(); const s=await open(urls[k][1]); const S=await grab(s,pairs[k].map(x=>[x[0],x[2]])); await s.close(); report[k]={A,S}; }
  require('fs').writeFileSync('/tmp/probe.json',JSON.stringify(report,null,1)); await b.close(); })();
