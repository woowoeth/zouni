// 从携程手机版酒店列表抓每个住处的真实酒店（每档一家）：奢华=5 钻/星、高级=4 钻/星、中低=3 钻及以下里评分高的
// 用法：node tools/fetch_hotels.js keys.json data/hotels/ctrip_hotels.json 秒数
const p=require('/tmp/node_modules/puppeteer'); const fs=require('fs'); const sleep=ms=>new Promise(r=>setTimeout(r,ms));
const [,,KF,OF,SEC]=process.argv; const keys=JSON.parse(fs.readFileSync(KF,'utf8')); const out=fs.existsSync(OF)?JSON.parse(fs.readFileSync(OF,'utf8')):{};
const todo=Object.entries(keys).filter(([k])=>!out[k]||(!out[k].top&&!out[k].retry)).sort((a,b)=>b[1].n-a[1].n); const T0=Date.now(), LIM=(+SEC||240)*1000;
(async()=>{ const b=await p.launch({args:['--no-sandbox','--disable-dev-shm-usage']}); const dev=p.KnownDevices['iPhone 13']; let done=0;
  async function one(pg,k,v){ const kw=v.kw===v.city?'':v.kw; const u='https://m.ctrip.com/webapp/hotels/list?city='+v.cid+(kw?'&keyword='+encodeURIComponent(kw):'');
    await pg.goto(u,{waitUntil:'networkidle2',timeout:35000}).catch(()=>{}); await pg.waitForSelector('a[href*="hoteldetail"]',{timeout:12000}).catch(()=>{});
    await pg.waitForFunction(()=>[...document.images].some(i=>/diamond|star/i.test(i.getAttribute('src')||'')),{timeout:8000}).catch(()=>{});
    const acc=new Map(); const order=[];
    const grab=async()=>{ const part=await pg.evaluate(()=>{ const res=[]; document.querySelectorAll('a[href*="hoteldetail"]').forEach(a=>{ const m=(a.getAttribute('href')||'').match(/hoteldetail\/(\d+)\.html/); if(!m) return;
        let e=a; for(let i=0;i<8&&e.parentElement;i++){ if((e.innerText||'').length>60) break; e=e.parentElement; }
        const t=(e.innerText||'').replace(/\s+/g,' '); const img=[...e.querySelectorAll('img')].map(i=>i.getAttribute('src')||'').find(s=>/diamond|star/i.test(s))||'';
        const lv=(img.match(/(?:diamond|star)(\d)/i)||[])[1]; const sc=(t.match(/\b([345]\.\d)\b/)||[])[1]; const rv=(t.match(/([\d.]+万?)点评/)||[])[1];
        const nm=(a.innerText||'').split('\n')[0].trim()||t.slice(0,30); res.push({id:m[1],name:nm.slice(0,40),lv:lv?+lv:0,score:sc?+sc:0,rev:rv||'',ad:/广告/.test(t.slice(0,60))}); }); return res; });
      part.forEach(c=>{ const o=acc.get(c.id); if(!o){ acc.set(c.id,c); order.push(c.id); } else { if(!o.lv&&c.lv) o.lv=c.lv; if(!o.score&&c.score) o.score=c.score; } }); };
    await grab();
    for(let i=0;i<3;i++){ await pg.evaluate(()=>{ const as=document.querySelectorAll('a[href*="hoteldetail"]'); if(as.length) as[as.length-1].scrollIntoView(); }); await sleep(1200); await grab(); }
    const cards=order.map(id=>acc.get(id)).filter(c=>!c.ad);
    const pick=f=>cards.find(f)||null;
    const lux=pick(c=>c.lv===5), mid=pick(c=>c.lv===4), eco=pick(c=>c.lv>0&&c.lv<=3&&c.score>=4.5)||pick(c=>c.lv>0&&c.lv<=3);
    const top=cards.filter(c=>c.score>=4.6).slice(0,3);
    return {lux,mid,eco,top,n:cards.length,at:new Date().toISOString().slice(0,10)}; }
  async function worker(){ const pg=await b.newPage(); await pg.emulate(dev);
    while(todo.length&&Date.now()-T0<LIM){ const [k,v]=todo.shift(); const had=!!out[k]; try{ out[k]=await one(pg,k,v); if(had) out[k].retry=1; done++; }catch(e){ out[k]={err:String(e).slice(0,60),n:0,at:new Date().toISOString().slice(0,10)}; }
      if(done%5===0) fs.writeFileSync(OF,JSON.stringify(out,null,0)); }
    await pg.close(); }
  await Promise.all([worker(),worker(),worker(),worker()]);
  fs.writeFileSync(OF,JSON.stringify(out,null,0)); const vals=Object.values(out);
  console.log(JSON.stringify({本次:done,累计:vals.length,剩下:todo.length,有奢华:vals.filter(x=>x.lux).length,有高级:vals.filter(x=>x.mid).length,有中低:vals.filter(x=>x.eco).length,空的:vals.filter(x=>!x.n).length}));
  await b.close(); })();
