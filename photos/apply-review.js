/* 应用核对结果：打叉的实景图降级为地图；同时统一地图缩放级别 */
const https=require('https'), fs=require('fs');
const UA='ZouniTravelApp/1.0 (https://ourword.ai/zouni/; contact@ourword.ai)';
function get(u){return new Promise((res,rej)=>{https.get(u,{headers:{'User-Agent':UA,'Accept':'application/json'}},r=>{
  let d='';r.on('data',c=>d+=c);r.on('end',()=>{try{res(JSON.parse(d))}catch(e){rej(e)}})}).on('error',rej)})}
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const ZOOM=12;   /* 14 太近只看得见一个路口；12 约 5km 视野，能看出点位在城/湖/山的哪一侧 */
function tile(lat,lon,z){return{z,x:Math.floor((lon+180)/360*2**z),
  y:Math.floor((1-Math.log(Math.tan(lat*Math.PI/180)+1/Math.cos(lat*Math.PI/180))/Math.PI)/2*2**z)}}

const REJECT=JSON.parse(process.argv[2]||'[]');
/* 打叉项的地理查询词（用景点全名，比 key 准） */
const Q={
  'poi:dukezong':'香格里拉 独克宗古城',
  'poi:artpark':'成都 人民公园',
  'poi:peak':'香港 太平山顶',
  'poi:zhaosu-tian':'昭苏县 新疆',
  'poi:taian':'都江堰 泰安古镇'
};
(async()=>{
  const db=JSON.parse(fs.readFileSync('photos.json','utf8'));
  console.log(`══ 应用核对结果：${REJECT.length} 项降级 ══`);
  for(const k of REJECT){
    if(!db[k]){ console.log(`  ? ${k} 不存在`); continue; }
    const q=Q[k]||k.replace(/^poi:/,'');
    try{
      const j=await get('https://nominatim.openstreetmap.org/search?format=json&limit=1&accept-language=zh&q='+encodeURIComponent(q));
      if(j&&j.length){
        const lat=+j[0].lat, lon=+j[0].lon, t=tile(lat,lon,ZOOM);
        db[k]={type:'map', lat, lon, url:`https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`,
               license:'© OpenStreetMap contributors', matched:q, wasPhoto:true};
        console.log(`  ✓ ${k.padEnd(18)} → 地图 ${lat.toFixed(3)},${lon.toFixed(3)}  ${q}`);
      } else console.log(`  ✗ ${k.padEnd(18)} 查不到坐标 ${q}`);
    }catch(e){ console.log(`  ! ${k.padEnd(18)} ${String(e.message).slice(0,26)}`); }
    await sleep(1300);
  }
  /* 统一所有地图的缩放级别 */
  let rez=0;
  Object.entries(db).forEach(([k,v])=>{
    if(v.type!=='map'||!v.lat) return;
    const t=tile(v.lat,v.lon,ZOOM);
    const nu=`https://tile.openstreetmap.org/${t.z}/${t.x}/${t.y}.png`;
    if(v.url!==nu){ v.url=nu; rez++; }
  });
  fs.writeFileSync('photos.json', JSON.stringify(db,null,1));
  const p=Object.values(db).filter(v=>v.type==='photo').length;
  const m=Object.values(db).filter(v=>v.type==='map').length;
  console.log(`\n  地图缩放统一为 z${ZOOM}（重算 ${rez} 张）`);
  console.log(`  📷 实景图 ${p} · 🗺 地图 ${m} · 覆盖率 100%`);
})();
