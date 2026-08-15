/* 修正跑错省的坐标：查询词加省份前缀 + 结果必须落在省界内，否则退到省会/主城 */
const https=require('https'), fs=require('fs');
const UA='ZouniTravelApp/1.0 (https://ourword.ai/zouni/; contact@ourword.ai)';
function get(u){return new Promise((res,rej)=>{https.get(u,{headers:{'User-Agent':UA,'Accept':'application/json'}},r=>{
  let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){rej(e)}})}).on('error',rej)})}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ZOOM=12;
function tile(lat,lon,z){return{z,x:Math.floor((lon+180)/360*2**z),
  y:Math.floor((1-Math.log(Math.tan(lat*Math.PI/180)+1/Math.cos(lat*Math.PI/180))/Math.PI)/2*2**z)}}
const BOX={新疆:[34,49,73,96],西藏:[26,37,78,99],青海:[31,39,89,103],甘肃:[32,43,92,109],
 内蒙古:[37,53,97,126],四川:[26,34,97,109],云南:[21,29,97,106],湖南:[24,30,108,114],
 广西:[20,26,104,112],安徽:[29,35,114,120],浙江:[27,31,118,123],福建:[23,28,115,121],
 海南:[18,20,108,111],陕西:[31,40,105,111],重庆:[28,32,105,110],北京:[39,41,115,118],
 上海:[30,32,120,122],香港:[22,23,113,115],日本:[24,46,122,146]};
/* 省内兜底中心（查不到时用，至少不会跑到别的省） */
const CENTER={新疆:[43.83,87.62],西藏:[29.65,91.14],青海:[36.62,101.78],甘肃:[36.06,103.83],
 内蒙古:[40.84,111.75],四川:[30.66,104.07],云南:[25.04,102.71],湖南:[28.23,112.94],
 广西:[25.28,110.29],安徽:[29.71,118.34],浙江:[30.25,120.15],福建:[24.48,118.09],
 海南:[18.25,109.51],陕西:[34.34,108.94],重庆:[29.56,106.55],北京:[39.90,116.41],
 上海:[31.23,121.47],香港:[22.28,114.16],日本:[34.69,135.50]};

(async()=>{
  const db=JSON.parse(fs.readFileSync('photos.json','utf8'));
  const js=fs.readFileSync('index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
  const a=js.indexOf('const FUEL='), b=js.indexOf('/* ---------- 安排行程');
  fs.writeFileSync('/tmp/_fg.js', js.slice(a,b)+'\nmodule.exports={ROUTES};');
  const {ROUTES}=require('/tmp/_fg.js');
  const owner={}, label={};
  Object.entries(ROUTES).forEach(([id,R])=>{
    const p=(R.dest||'').split(/[·・]/)[0].trim();
    owner['route:'+id]=p; label['route:'+id]=(R.dest||'').split(/[·・]/).pop().trim();
    (R.days||[]).forEach(d=>(d.stops||[]).forEach(s=>{
      if(!s.k||owner['poi:'+s.k]) return;
      owner['poi:'+s.k]=p; label['poi:'+s.k]=(s.name||'').split(/[·・]/)[0].trim();
    }));
  });
  const inBox=(p,lat,lon)=>{ const b=BOX[p]; return !b || (lat>=b[0]&&lat<=b[1]&&lon>=b[2]&&lon<=b[3]); };
  const bad=Object.entries(db).filter(([k,v])=>v.type==='map'&&v.lat&&!inBox(owner[k],v.lat,v.lon));
  console.log(`══ 修正 ${bad.length} 个跑错省的坐标 ══`);
  let fixed=0, fell=0;
  for(const [k,v] of bad){
    const p=owner[k], nm=label[k]||'';
    let done=false;
    /* 查询词强制带省份，避免同名地点跨省匹配 */
    for(const q of [`${p} ${nm}`, `${nm} ${p}`, `${p}`]){
      if(done||!q.trim()) continue;
      try{
        const j=await get('https://nominatim.openstreetmap.org/search?format=json&limit=3&accept-language=zh&q='+encodeURIComponent(q));
        const hit=(j||[]).map(x=>({lat:+x.lat,lon:+x.lon})).find(x=>inBox(p,x.lat,x.lon));
        if(hit){ const t=tile(hit.lat,hit.lon,ZOOM);
          db[k]={...v, lat:hit.lat, lon:hit.lon, url:`https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`, matched:q};
          console.log(`  ✓ ${k.padEnd(17)} ${hit.lat.toFixed(2)},${hit.lon.toFixed(2)}  ${q}`);
          fixed++; done=true;
        }
      }catch(e){}
      await sleep(1200);
    }
    if(!done && CENTER[p]){
      const [lat,lon]=CENTER[p]; const t=tile(lat,lon,ZOOM);
      db[k]={...v, lat, lon, url:`https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`, matched:p+'（省内兜底）'};
      console.log(`  ~ ${k.padEnd(17)} ${lat.toFixed(2)},${lon.toFixed(2)}  ${p} 省内兜底`);
      fell++;
    }
  }
  fs.writeFileSync('photos.json', JSON.stringify(db,null,1));
  console.log(`\n  精确修正 ${fixed} · 省内兜底 ${fell}`);
})();
