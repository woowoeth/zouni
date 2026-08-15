#!/usr/bin/env node
/* ═══ 图源整合器 ═══
   三级兜底，保证 100% 有图：
     ① 实景图  Wikimedia Commons（CC 授权，需署名）
     ② 地图     OSM 瓦片（真实经纬度，比"地区风景图"诚实——用户能看见点位在哪）
     ③ 色块     纯 CSS，离线或全部失效时兜底

   用法：
     node build-photos.js --probe    试 10 个
     node build-photos.js --all      全量（限速，约 20 分钟）
*/
const https=require('https'), fs=require('fs'), path=require('path');
const ROOT=path.resolve(__dirname);
const OUT=ROOT+'/photos.json';
const UA='ZouniTravelApp/1.0 (https://ourword.ai/zouni/; contact@ourword.ai)';

function get(url){
  return new Promise((res,rej)=>{
    https.get(url,{headers:{'User-Agent':UA,'Accept':'application/json'}},r=>{
      let d=''; r.on('data',c=>d+=c);
      r.on('end',()=>{ try{res(JSON.parse(d))}catch(e){rej(new Error(d.slice(0,36)))} });
    }).on('error',rej);
  });
}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));

/* ── ① 实景图：按准确度从高到低试三种接口 ── */
/* A. 中文维基条目主图 —— 编辑挑过的代表画面，最准 */
async function wikiPageImage(title){
  const u='https://zh.wikipedia.org/w/api.php?action=query&format=json&redirects=1'
    +'&titles='+encodeURIComponent(title)+'&prop=pageimages|imageinfo&piprop=thumbnail|name&pithumbsize=400';
  const j=await get(u);
  const pages=j.query&&j.query.pages;
  if(!pages) return null;
  const p=Object.values(pages)[0];
  if(!p||p.missing!==undefined||!p.thumbnail) return null;
  return {url:p.thumbnail.source, w:p.thumbnail.width, h:p.thumbnail.height,
          src:'wiki', file:p.pageimage||'', matchedTitle:p.title};
}
/* B. Wikidata P18 —— 结构化的实体代表图 */
async function wikidataImage(q){
  const s=await get('https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json&language=zh&limit=1&search='+encodeURIComponent(q));
  if(!s.search||!s.search.length) return null;
  const ent=s.search[0];
  await sleep(400);
  const e=await get('https://www.wikidata.org/w/api.php?action=wbgetclaims&format=json&property=P18&entity='+ent.id);
  const c=e.claims&&e.claims.P18;
  if(!c||!c.length) return null;
  const file=c[0].mainsnak.datavalue.value;
  return {url:'https://commons.wikimedia.org/wiki/Special:FilePath/'+encodeURIComponent(file)+'?width=400',
          w:400,h:0, src:'wikidata', file, matchedTitle:ent.label};
}
/* C. Commons 分类内图片 —— 比全文搜索准，因为分类是人工归的 */
async function commonsCategory(q){
  /* Commons 分类多为英文名，中文查不到时先用 wiki 的语言链接换成英文 */
  let cat=q;
  try{
    const l=await get('https://zh.wikipedia.org/w/api.php?action=query&format=json&redirects=1&titles='
      +encodeURIComponent(q)+'&prop=langlinks&lllang=en');
    const p=Object.values(l.query.pages)[0];
    if(p&&p.langlinks&&p.langlinks[0]) cat=p.langlinks[0]['*'];
  }catch(e){}
  const u='https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=categorymembers'
    +'&gcmtitle='+encodeURIComponent('Category:'+cat)+'&gcmtype=file&gcmlimit=8'
    +'&prop=imageinfo&iiprop=url|extmetadata|size&iiurlwidth=400';
  const j=await get(u);
  const pages=j.query&&j.query.pages;
  if(!pages) return null;
  const list=Object.values(pages).map(p=>{
    const ii=(p.imageinfo||[])[0]||{}, m=ii.extmetadata||{};
    return {url:ii.thumburl||ii.url, w:ii.thumbwidth||0, h:ii.thumbheight||0,
            license:(m.LicenseShortName||{}).value||'', author:((m.Artist||{}).value||'').replace(/<[^>]+>/g,'').trim().slice(0,30),
            src:'commons-cat', file:p.title.replace(/^File:/,''), matchedTitle:cat};
  }).filter(x=>x.url&&x.w>=300);
  return list.filter(x=>x.w>=x.h)[0]||list[0]||null;
}
/* 取图片的版权信息（wiki/wikidata 两条路拿到的是文件名，需补查授权） */
async function fileMeta(file){
  if(!file) return {};
  const u='https://commons.wikimedia.org/w/api.php?action=query&format=json&titles='
    +encodeURIComponent('File:'+file)+'&prop=imageinfo&iiprop=extmetadata';
  try{
    const j=await get(u);
    const p=Object.values(j.query.pages)[0];
    const m=((p.imageinfo||[])[0]||{}).extmetadata||{};
    return {license:(m.LicenseShortName||{}).value||'',
            author:((m.Artist||{}).value||'').replace(/<[^>]+>/g,'').trim().slice(0,30)};
  }catch(e){ return {}; }
}

/* ── ② 地图瓦片 ── */
function tileXY(lat,lon,z){
  return { z,
    x:Math.floor((lon+180)/360*Math.pow(2,z)),
    y:Math.floor((1-Math.log(Math.tan(lat*Math.PI/180)+1/Math.cos(lat*Math.PI/180))/Math.PI)/2*Math.pow(2,z)) };
}
async function geo(q){
  const u='https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=zh&q='+encodeURIComponent(q);
  const j=await get(u);
  if(!j||!j.length) return null;
  return {lat:+j[0].lat, lon:+j[0].lon};
}

/* ── 目标清单 ── */
function targets(){
  const html=fs.readFileSync(ROOT+'/index.html','utf8');
  const js=html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
  const tmp='/tmp/_bp.js';
  fs.writeFileSync(tmp, js.slice(a,b)+'\nmodule.exports={ROUTES};');
  delete require.cache[tmp];
  const {ROUTES}=require(tmp);
  const out=[];
  Object.entries(ROUTES).forEach(([id,R])=>{
    const region=(R.dest||'').split(/[·・]/)[0].trim();
    /* 泛词（省名、"湖畔"这类）会搜到八竿子打不着的图，绝不能进候选 */
    const TOO_GENERIC=/^(新疆|西藏|云南|四川|甘肃|青海|内蒙古|湖南|广西|安徽|浙江|福建|海南|陕西|重庆|北京|上海|香港|日本|湖畔|山中|镇上|城里|市区|沿途|路上)$/;
    const clean=arr=>[...new Set(arr.filter(x=>x&&x.trim()&&!TOO_GENERIC.test(x.trim())))];
    /* 线路封面：用该线最有代表性的站点全名，不用省名 */
    const heroes=(R.days||[]).flatMap(d=>d.stops||[]).filter(s=>s.k&&s.cng).slice(0,2);
    out.push({ key:'route:'+id, kind:'route', region,
      cands:clean(heroes.map(h=>h.name.split(/[·・]/)[0])),
      geoq:clean([heroes[0]&&(heroes[0].q||heroes[0].name)]).concat([region]) });
    (R.days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
      if(!s.k || out.some(x=>x.key==='poi:'+s.k)) return;
      if(/提车|还车|验车|休整|放行李|入住|抵达|返程|购票|出发/.test(s.name||'')) return;
      /* 二选一容器（optLabel + opts）自己没有 name，图取自第一个选项 */
      const src = (!s.name && s.opts && s.opts.length)? s.opts[0] : s;
      const label = s.name || s.optLabel || (src.name||'');
      const main=(label||'').split(/[·・]/)[0].trim();
      /* 候选：主名 → 主名去后缀 → 全名 → 导航词。都要够具体 */
      const bare=main.replace(/(景区|公园|风景区|旅游区|古镇|村|站)$/,'');
      out.push({ key:'poi:'+s.k, kind:'poi', region, name:label,
        cands:clean([main, bare, label, src.q, s.q]),
        /* 地理编码逐级放宽：精确词 → 加地名 → 主名 → 所在地区（保证一定有坐标） */
        geoq:clean([src.q, s.q, main+' '+region, main]).concat([region]) });
    }));
  });
  return out;
}

(async()=>{
  const probe=process.argv.includes('--probe');
  const list=targets();
  const lim=(()=>{ const i=process.argv.indexOf('--limit'); return i>-1? +process.argv[i+1] : 0; })();
  const todo=list.filter(t=>{ const d=fs.existsSync(OUT)? JSON.parse(fs.readFileSync(OUT,'utf8')) : {}; return !(d[t.key]&&d[t.key].type); });
  const work=probe? list.slice(0,10) : (lim? todo.slice(0,lim) : list);
  console.log(`  待处理 ${todo.length} / 总计 ${list.length}`);
  const db=fs.existsSync(OUT)? JSON.parse(fs.readFileSync(OUT,'utf8')) : {};
  console.log(`══ 三级图源构建${probe?'（试 10 个）':`（全量 ${work.length}）`} ══\n`);
  let p1=0,p2=0,p3=0;
  for(let i=0;i<work.length;i++){
    const t=work[i];
    if(db[t.key]&&db[t.key].type){ ({photo:()=>p1++,map:()=>p2++,none:()=>p3++})[db[t.key].type]?.(); continue; }
    let rec=null;
    /* ① 实景图：wiki 条目主图 → wikidata P18 → commons 分类，准确度依次降低 */
    for(const q of t.cands){
      if(rec) break;
      /* 注意：某接口返回卫星图被拒后，必须继续试下一个接口。
         中文维基不少自然景观条目的主图就是卫星图（喀纳斯湖、赛里木湖都是），
         这不是异常，Commons 分类里有大量游客拍的实景。 */
      for(const fn of [wikiPageImage, wikidataImage, commonsCategory]){
        try{
          let r=await fn(q);
          /* 校验：条目名与查询词需有实质重合。取查询词前 2 字为核心，
             「喀纳斯湖」vs「喀纳斯景区」→ 共享「喀纳」，通过；
             「新疆」vs「K2峰」→ 无重合，拒绝。
             注意别过严：之前要求双向包含，把正确结果也误杀了。 */
          if(r&&r.url&&r.matchedTitle){
            const norm=x=>String(x).replace(/[\s·・\-_（）()]/g,'');
            const t1=norm(r.matchedTitle), t2=norm(q);
            const core=t2.slice(0,2);
            const rel = t1.includes(core) || t2.includes(t1.slice(0,2)) ||
                        [...t2].filter(ch=>t1.includes(ch)).length >= Math.min(2, t2.length);
            if(!rel) r=null;
          }
          /* 卫星图、示意图、旗帜、徽章不是用户想看的风景，排除 */
          const BAD_FILE=/satellite|landsat|sentinel|map[_\-\.]|_map|地图|示意图|flag|logo|coat[_\-]of[_\-]arms|seal|diagram|chart|plan[_\-]|location/i;
          if(r&&r.file&&BAD_FILE.test(String(r.file))) r=null;
          if(r&&r.url){
            const meta=(r.license? r : await fileMeta(r.file));
            rec={type:'photo', url:r.url, w:r.w, h:r.h, src:r.src, file:r.file,
                 license:meta.license||r.license||'', author:meta.author||r.author||'',
                 matched:q, title:r.matchedTitle||q};
            break;
          }
        }catch(e){}
        await sleep(700);
      }
    }
    /* ② 地图瓦片 */
    if(!rec){
      for(const q of t.geoq){
        try{ const g=await geo(q); if(g){ const tl=tileXY(g.lat,g.lon,14);
          rec={type:'map', lat:g.lat, lon:g.lon,
               url:`https://tile.openstreetmap.org/${tl.z}/${tl.x}/${tl.y}.png`,
               license:'© OpenStreetMap contributors', matched:q}; break; } }catch(e){}
        await sleep(1200);
      }
    }
    /* ③ 色块 */
    if(!rec) rec={type:'none', label:(t.name||t.region||'').slice(0,2)};
    db[t.key]=rec;
    ({photo:()=>p1++,map:()=>p2++,none:()=>p3++})[rec.type]();
    const icon={photo:'📷',map:'🗺',none:'▨'}[rec.type];
    const via=rec.src? '['+rec.src+']' : '';
    console.log(`  ${icon} ${t.key.padEnd(19)} ${via.padEnd(14)} ${(rec.file||rec.matched||rec.label||'').slice(0,34)}`);
    if(i%8===7) fs.writeFileSync(OUT, JSON.stringify(db,null,1));
  }
  fs.writeFileSync(OUT, JSON.stringify(db,null,1));
  const kb=(Buffer.byteLength(JSON.stringify(db))/1024).toFixed(1);
  console.log(`\n  📷 实景图 ${p1} · 🗺 地图 ${p2} · ▨ 色块 ${p3}`);
  console.log(`  覆盖率 ${(((p1+p2)/(p1+p2+p3))*100).toFixed(0)}% · photos.json ${kb}KB`);
})();
