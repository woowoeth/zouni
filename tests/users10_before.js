// 十位用户：每人一个真实任务，记录点了几下、找没找到要的信息、卡在哪
const p=require('/tmp/node_modules/puppeteer'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const U='file:///tmp/dc-test/';
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage','--allow-file-access-from-files']});
  const open=async (f)=>{ const pg=await b.newPage(); pg._e=[]; pg.on('pageerror',e=>pg._e.push(e.message.split('\n')[0])); await pg.setViewport({width:390,height:844}); await pg.goto(U+f,{waitUntil:'networkidle0'}); await sleep(1100); return pg; };
  const text=pg=>pg.evaluate(()=>document.body.innerText);
  const R=[];
  // 1 小林：10 月下旬 4 天假，想找“正当季、有完整行程”的地方
  { const pg=await open('Atlas.dc.html'); const t=await text(pg);
    const n=await pg.evaluate(()=>[...document.querySelectorAll('a')].filter(a=>a.innerText.includes('完整行程')).length);
    const good=await pg.evaluate(()=>[...document.querySelectorAll('div')].filter(d=>d.innerText.startsWith('正好')).length);
    R.push({u:'1 小林 · 10 月下旬请 4 天',ok:n>0,find:`10 月“正好”的卡片里能直接翻开完整行程的 ${n} 个；没有“只看有行程的”筛选，要往下翻 34 张卡`,taps:'本期 → 按月份挑 → 往下翻 → 完整行程，约 4 步 + 长滚动'}); await pg.close(); }
  // 2 张阿姨：62 岁怕高原，10 月去哪
  { const pg=await open('Atlas.dc.html'); const hi=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/海拔 [\d,]+ 米/.test(s.innerText)).length);
    const tag=await pg.evaluate(()=>/台阶|老人|高海拔/.test(document.body.innerText));
    R.push({u:'2 张阿姨 · 怕高原、膝盖不好',ok:false,find:`能看到海拔的卡片 ${hi} 张，但“台阶多 / 适不适合老人”在“去哪儿”里没有；本期页的标签（爬山 · 台阶多）没带过来`,taps:'要一张张点进行程才知道'}); await pg.close(); }
  // 3 陈妈妈：带 6 岁孩子
  { let kid=0; for(const rid of ['cd3','sh3','hz3','zjj4','nm4']){ const pg=await open('Route.dc.html#'+rid); if(/孩子|亲子|儿童/.test(await text(pg))) kid++; await pg.close(); }
    R.push({u:'3 陈妈妈 · 带 6 岁孩子',ok:kid>0,find:`5 条行程里提到孩子的 ${kid} 条；只有西藏专题有“带孩子”的替代走法`,taps:'—'}); }
  // 4 阿杰：学生，先看钱
  { const pg=await open('Atlas.dc.html'); const price=await pg.evaluate(()=>/¥\d/.test(document.body.innerText)); await pg.close();
    const pr=await open('Route.dc.html#zjj4'); const budget=await pr.evaluate(()=>[...document.querySelectorAll('span')].some(s=>s.innerText==='中低'));
    R.push({u:'4 阿杰 · 学生，预算紧',ok:false,find:`“去哪儿”里${price?'有':'没有'}价格；行程页里住宿${budget?'有':'没有'}中低档，但每人花多少只按 2 人算`,taps:'—'}); await pr.close(); }
  // 5 老周：自驾，关心路况
  { const pg=await open('Route.dc.html#xj10'); const t=await text(pg); const road=/垭口|测速|加油|检查站|山路|限速/.test(t);
    R.push({u:'5 老周 · 自驾北疆',ok:road,find:`开车时长和长途日标红都有；路况提醒${road?'有':'没有'}（引擎里其实有“沿途”说明没带过来）`,taps:'—'}); await pg.close(); }
  // 6 Lily：4 个人组局
  { const pg=await open('Route.dc.html#jz4'); const step=await pg.evaluate(()=>[...document.querySelectorAll('button')].some(b=>/人$/.test(b.innerText.trim())||b.getAttribute('aria-label')==='多一个人'));
    R.push({u:'6 Lily · 4 人组局',ok:step,find:`行程页${step?'能':'不能'}改人数；自驾线 4 人分摊车费会便宜很多，页面上看不到`,taps:'—'}); await pg.close(); }
  // 7 阿May：摄影
  { const pg=await open('Route.dc.html#hz3'); const t=await text(pg); const sun=/日出[\s\S]{0,6}\d\d:\d\d/.test(t)&&/日落[\s\S]{0,6}\d\d:\d\d/.test(t);
    R.push({u:'7 阿May · 拍照',ok:sun,find:`日出日落每天都有；雷峰塔“夕照”被排在中午，想拍夕照要自己挪`,taps:'—'}); await pg.close(); }
  // 8 Jerry：香港出发去亚洲
  { const pg=await open('Atlas.dc.html'); await pg.evaluate(()=>[...document.querySelectorAll('button')].find(b=>b.innerText.startsWith('亚洲')).click()); await sleep(300);
    const visa=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/免签|签证|落地签|电子签/.test(s.innerText)).length);
    R.push({u:'8 Jerry · 香港出发',ok:visa>0,find:`亚洲 20 国入境要求都写了（${visa} 处）；但写的是大陆护照的规则，港澳居民不同；“含往返”默认从内地出发`,taps:'—'}); await pg.close(); }
  // 9 小周：只有周末 2 天
  { const pg=await open('Atlas.dc.html'); const two=await pg.evaluate(()=>[...document.querySelectorAll('span')].filter(s=>/· 2 天$/.test(s.innerText)).length);
    R.push({u:'9 小周 · 只有周末两天',ok:false,find:`“去哪儿”不能按天数筛，2 天的只有 ${two} 张卡，要一张张找`,taps:'—'}); await pg.close(); }
  // 10 小雨：一个人出行
  { let hostel=0, total=0; for(const rid of ['cd3','sh3','hz3','sz3','zjj4','hk2']){ const pg=await open('Route.dc.html#'+rid); total++; const t=await pg.evaluate(()=>{ [...document.querySelectorAll('button')].filter(b=>b.innerText.includes('看另外')).forEach(b=>b.click()); return document.body.innerText; }); await sleep(200); if(/青旅|床位|客栈/.test(await text(pg))) hostel++; await pg.close(); }
    R.push({u:'10 小雨 · 一个人出行',ok:hostel>=3,find:`6 条城市行程里有青旅或客栈的 ${hostel} 条；没有一个人能不能拼房、拼车的信息`,taps:'—'}); }
  // 本期页数据核对
  { const pg=await open('Main.dc.html'); const t=await text(pg);
    R.push({u:'数据核对 · 本期页',ok:false,find:`台湾 5 天写着人均 ¥5,000–7,000 当普通线路推荐（大陆居民赴台湾本岛旅游尚未恢复）；卡帕多奇亚写“电子签”（土耳其 2026 年 1 月 2 日起免签）；巴拉望写“签证”（菲律宾马尼拉入境试行免签 14 天）`,taps:'—'}); await pg.close(); }
  console.log(JSON.stringify(R,null,1)); await b.close(); })().catch(e=>{console.error('ERR',e.message);process.exit(1);});
