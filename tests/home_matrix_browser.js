// 首页“替我挑三条”矩阵断言（在浏览器里跑：打开首页，在控制台粘贴整个文件，返回结果对象）
// 37 个出发城市 × 3 种天数 × 3 种同行 × 2 种出行方式，每组读前三条，断言：
//  (a) 每组恰好 3 条（不足时页面有说明）  (b) 同一省最多 2 条  (c) 选“不开车”时前三条都不要自己开车（li.dataset.sd==='0'）
//  (d) 选“带老人孩子”时前三条最高天标 <2,500 米、不出国（li.dataset.hi==='0' && ab==='0'）
//  (e) 每个出发城市，直线距离中位数：周末 ≤600、4–5 天 ≤900 公里（2026-10 实测最大 546 / 847；严格单调太脆弱，相邻档位小波动是正常的）
//  (f) 周末的前三条里有 >450 公里的，页面必须有“这几条是现在最近的”的说明
//  (g) 带老人孩子推荐出的每个页面，抓来看页面自己的最高海拔（“行程最高到 N 米”/每天提示）必须 <2,500 米（不能只信首页条目的 data-hi：它出错时检测不到）
// 用法：把这段贴到浏览器控制台；返回 {组数, 失败: [...], 中位数: {...}}。无头环境（puppeteer）里同样可以 page.evaluate 这段。
(async()=>{
  const w=ms=>new Promise(r=>setTimeout(r,ms)), pk=document.querySelector('.pick'); if(!pk) return {错误:'没找到 .pick'};
  const cities=[...pk.querySelectorAll('.pkr[data-k="o"] button')].map(b=>b.dataset.v).filter(v=>v!=='here');
  const click=(k,v)=>{const b=pk.querySelector('.pkr[data-k="'+k+'"] button[data-v="'+v+'"]'); if(b) b.click()};
  const fails=[], med={}; let n=0;
  const findLi=href=>[...document.querySelectorAll('.toc .items li')].find(l=>{const a=l.querySelector('a[href^="/trip/"]');return a&&a.getAttribute('href')===href});
  const dist=txt=>{const m=/直线约 (\d+) 公里/.exec(txt); return m?+m[1]:null};
  for(const o of cities){ med[o]={};
    for(const d of ['w','m','l']){ const ds=[];
      for(const x of ['f','c','o']) for(const v of ['a','n']){
        click('o',o);click('d',d);click('w',x);click('v',v); await w(25); n++;
        const items=[...document.querySelectorAll('.pkres li')], tag=o+'/'+d+'/'+x+'/'+v;
        if(items.length!==3 && !document.querySelector('.pkhint')) fails.push(tag+' 只有 '+items.length+' 条且没有说明');
        if(d==='w'&&items.some(it=>(dist(it.innerText)||0)>450)&&!/最近的/.test((document.querySelector('.pkres')||{}).parentNode.innerText||'')) fails.push(tag+' 周末有 >450 公里的推荐却没有说明');
        const provs={}; items.forEach(it=>{const h3=it.querySelector('b').innerText.split(' · ')[0]; provs[h3]=(provs[h3]||0)+1; if(provs[h3]>2) fails.push(tag+' 同省超过 2 条：'+h3);
          const a=it.querySelector('a'), li=findLi(a.getAttribute('href'));
          if(!li){fails.push(tag+' 找不到条目 '+a.getAttribute('href'));return}
          if(v==='n'&&li.dataset.sd==='1') fails.push(tag+' 不开车却推了自驾线 '+a.getAttribute('href'));
          if(x==='o'&&(li.dataset.hi==='1'||li.dataset.ab==='1')) fails.push(tag+' 带老人孩子却推了高原/国外线 '+a.getAttribute('href'));
          const km=dist(it.innerText); if(km!=null) ds.push(km)});
      }
      ds.sort((a,b)=>a-b); med[o][d]=ds.length?ds[Math.floor(ds.length/2)]:null;
    }
    const m=med[o]; if(m.w!=null&&m.w>600) fails.push(o+' 周末距离中位数 '+m.w+' > 600'); if(m.m!=null&&m.m>900) fails.push(o+' 4–5 天距离中位数 '+m.m+' > 900');
  }
  const eld=new Set(); // 带老人孩子推荐过的页面
  for(const o of cities) for(const d of ['w','m','l']){ click('o',o);click('d',d);click('w','o');click('v','a'); await w(25); [...document.querySelectorAll('.pkres a')].forEach(a=>eld.add(a.getAttribute('href'))); }
  for(const h of eld){ try{ const t=await (await fetch(h)).text(); const ms=[...t.matchAll(/行程最高到 ([\d,]+) 米/g)].map(m=>+m[1].replace(/,/g,'')).concat([...t.matchAll(/<p class="alt"><b>海拔 ([\d,]+) 米/g)].map(m=>+m[1].replace(/,/g,''))); if(ms.length&&Math.max(...ms)>=2500) fails.push('带老人孩子推荐了页面最高 '+Math.max(...ms)+' 米的线 '+h); }catch(e){ fails.push('抓不到 '+h) } }
  return {组数:n, 城市数:cities.length, 失败:fails.slice(0,40), 失败总数:fails.length, 中位数示例:Object.fromEntries(Object.entries(med).slice(0,5))};
})()
