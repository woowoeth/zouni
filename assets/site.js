(function(){
  // 日出日落：按今天的月份和每天的坐标算
  function sun(lat,lon,dt,rise){var n=Math.round((dt-new Date(dt.getFullYear(),0,0))/864e5),r=Math.PI/180,lh=lon/15,t=n+((rise?6:18)-lh)/24,M=.9856*t-3.289,L=(M+1.916*Math.sin(M*r)+.02*Math.sin(2*M*r)+282.634)%360,RA=(Math.atan(.91764*Math.tan(L*r))/r+360)%360;RA=(RA+(Math.floor(L/90)*90-Math.floor(RA/90)*90))/15;var sd=.39782*Math.sin(L*r),cd=Math.cos(Math.asin(sd)),cH=(Math.cos(90.833*r)-sd*Math.sin(lat*r))/(cd*Math.cos(lat*r));if(cH>1||cH<-1)return'—';var H=(rise?360-Math.acos(cH)/r:Math.acos(cH)/r)/15,T=H+RA-.06571*t-6.622,lo=((T-lh)%24+24+8)%24,h=Math.floor(lo),m=Math.round((lo-h)*60);if(m==60){h++;m=0}return(h<10?'0':'')+h+':'+(m<10?'0':'')+m}
  var now=new Date();
  document.querySelectorAll('.sun').forEach(function(b){b.textContent=sun(+b.dataset.lat,+b.dataset.lng,now,b.dataset.k==='rise')});
  // 几个人去：租车按车分摊，两人一间
  var p=document.querySelector('.price[data-cost]');
  if(p&&p.dataset.cost){var C=JSON.parse(p.dataset.cost),box=document.querySelector('.ppl'),N=2;
    function upd(){var rooms=Math.ceil(N/2),car=C.perCar?C.carTotal/N:C.tollsPP,lodge=C.lodgeRoom*rooms/N,loc=C.tixPP+C.foodPP+car+lodge,r=function(v){return(Math.round(v/100)*100).toLocaleString('en-US')};p.textContent='¥'+r(loc+C.trans[0])+'–'+r(loc+C.trans[1]);box.querySelector('b').textContent=N+' 人';p.nextElementSibling.textContent='每人 · '+N+' 人同行 · 含往返'}
    p.title='点这里改人数';p.addEventListener('click',function(){box.hidden=!box.hidden});
    box.querySelectorAll('button').forEach(function(x){x.addEventListener('click',function(){N=Math.max(1,Math.min(6,N+(+x.dataset.d)));upd()})})}
  // 去哪儿：换月份
  var mon=document.querySelector('.mon');
  if(mon){var on=mon.querySelector('button.on');if(on)mon.scrollLeft=on.offsetLeft-(mon.clientWidth-on.offsetWidth)/2;
    mon.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;var m=+b.dataset.m;mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});
    document.querySelectorAll('.card').forEach(function(c){var best=c.dataset.best.split(',').map(Number),f=c.querySelector('.fit'),cl=JSON.parse(c.dataset.clim)[m]||['',''];
      var v=c.dataset.no==='1'?'暂不排':best.indexOf(m)>=0?'正好':best.some(function(x){return Math.abs((x-m+12)%12)===1||Math.abs((m-x+12)%12)===1})?'也行':'不建议';
      f.textContent=v;f.className='fit'+(v==='也行'?' ok':v==='正好'?'':' no');c.querySelector('.cl').textContent=m+' 月：白天 '+cl[0]+'℃，夜里 '+cl[1]+'℃'})});
    document.querySelectorAll('.card .fit').forEach(function(f){var v=f.textContent;f.className='fit'+(v==='也行'?' ok':v==='正好'?'':' no')})}
  // 去哪儿：搜索和筛选（只看合适的、天数、避开高原）
  var flt=document.querySelector('.flt');
  if(flt){var st={fit:true,d:'',low:false,q:''},inp=flt.querySelector('input'),cnt=flt.querySelector('.cnt');
    function curM(){var b=document.querySelector('.mon button.on');return b?+b.dataset.m:new Date().getMonth()+1}
    function apply(){var m=curM(),n=0;
      document.querySelectorAll('.card').forEach(function(c){var best=c.dataset.best.split(',').map(Number),days=c.dataset.days.split(',').map(Number),ok=true;
        var near=best.some(function(x){return Math.abs((x-m+12)%12)===1||Math.abs((m-x+12)%12)===1});
        if(st.fit&&(c.dataset.no==='1'||(best.indexOf(m)<0&&!near)))ok=false;
        if(st.d==='d1'&&!days.some(function(d){return d>=1&&d<=3}))ok=false;
        if(st.d==='d2'&&!days.some(function(d){return d>=4&&d<=5}))ok=false;
        if(st.d==='d3'&&!days.some(function(d){return d>=6}))ok=false;
        if(st.low&&c.dataset.high==='1')ok=false;
        if(st.q&&c.dataset.q.toLowerCase().indexOf(st.q)<0)ok=false;
        if(st.niche&&c.dataset.niche==='0')ok=false;
        var hp=c.querySelector('.hit');if(hp){var why=st.q?c.dataset.hits.split('|').filter(function(h){return h.toLowerCase().indexOf(st.q)>=0}).slice(0,3):[];hp.hidden=!why.length;hp.textContent=why.length?'有 '+why.join('、'):''}
        if(st.near&&!(c.dataset.km!==''&&+c.dataset.km<=500))ok=false;
        c.hidden=!ok;if(ok)n++});
      document.querySelectorAll('.reg').forEach(function(r){r.hidden=!r.querySelector('.card:not([hidden])')});
      cnt.textContent=n?('符合的 '+n+' 个'):'没有符合的，去掉一个条件再看看'}
    // 从哪出发：每张卡写距离，同一地区里近的排前面；500 公里内可以单独筛
    var ORG={'北京':[39.9,116.4],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'杭州':[30.27,120.16],'南京':[32.06,118.8],'成都':[30.66,104.06],'重庆':[29.56,106.55],'武汉':[30.59,114.3],'西安':[34.34,108.94],'香港':[22.3,114.17]};
    function km(a,b){var r=Math.PI/180,dl=(b[1]-a[1])*r,p1=a[0]*r,p2=b[0]*r,h=Math.sin((p2-p1)/2)*Math.sin((p2-p1)/2)+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)*Math.sin(dl/2);return Math.round(2*6371*Math.asin(Math.sqrt(h)))}
    var sel=flt.querySelector('select'),nearB=flt.querySelector('[data-f="near"]');
    function origin(o){try{localStorage.setItem('zouni_org',o)}catch(e){}nearB.hidden=!o;if(!o){st.near=false;nearB.classList.remove('on')}
      document.querySelectorAll('.cards').forEach(function(ul){var cs=[].slice.call(ul.children);cs.forEach(function(c){var d=o?km(ORG[o],[+c.dataset.lat,+c.dataset.lng]):null,p=c.querySelector('.dist');c.dataset.km=d==null?'':d;p.hidden=d==null;if(d!=null)p.textContent=d<30?'就在'+o:'离'+o+' '+d.toLocaleString('en-US')+' 公里'+(d<=500?' · 周末能去':'')});
        if(o){cs.sort(function(a,b){return(+a.dataset.km)-(+b.dataset.km)}).forEach(function(c){ul.appendChild(c)})}});
      // 地区也按最近的那个排：选了上海，华东排在最前
      document.querySelectorAll('.scope').forEach(function(sc){var regs=[].slice.call(sc.querySelectorAll('.reg'));
        regs.forEach(function(r,i){if(r.dataset.i==null)r.dataset.i=i;r.dataset.min=o?Math.min.apply(null,[].map.call(r.querySelectorAll('.card'),function(c){return +c.dataset.km})):r.dataset.i});
        regs.sort(function(a,b){return o?(+a.dataset.min)-(+b.dataset.min):(+a.dataset.i)-(+b.dataset.i)}).forEach(function(r){sc.appendChild(r)})});
      apply()}
    sel.addEventListener('change',function(){origin(sel.value)});
    nearB.addEventListener('click',function(){st.near=!st.near;nearB.classList.toggle('on',st.near);apply()});
    try{var o0=localStorage.getItem('zouni_org');if(o0&&ORG[o0]){sel.value=o0;origin(o0)}}catch(e){}
    inp.addEventListener('input',function(){st.q=inp.value.trim().toLowerCase();apply()});
    flt.querySelectorAll('.chips button:not([data-f="near"])').forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;
      if(f==='fit'){st.fit=!st.fit;b.classList.toggle('on',st.fit)}else if(f==='low'){st.low=!st.low;b.classList.toggle('on',st.low)}else if(f==='niche'){st.niche=!st.niche;b.classList.toggle('on',st.niche)}
      else{st.d=st.d===f?'':f;flt.querySelectorAll('[data-f^="d"]').forEach(function(x){x.classList.toggle('on',x.dataset.f===st.d)})}apply()})});
    if(mon)mon.addEventListener('click',function(){setTimeout(apply,0)});
    apply()}
  // 收藏、最近看过（只存在这台手机的浏览器里）
  function ld(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}}
  function sv(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  function toast(t){var d=document.createElement('div');d.className='toast';d.textContent=t;document.body.appendChild(d);setTimeout(function(){d.remove()},1600)}
  var art=document.querySelector('article.trip');
  if(art){var pk='zouni_prep_'+art.dataset.id,done=ld(pk);document.querySelectorAll('.pre input[type=checkbox]').forEach(function(x){x.checked=done.indexOf(+x.dataset.k)>=0;x.addEventListener('change',function(){var d=ld(pk).filter(function(k){return k!==+x.dataset.k});if(x.checked)d.push(+x.dataset.k);sv(pk,d)})});var me={id:art.dataset.id,label:art.dataset.label,title:art.dataset.title},seen=ld('zouni_seen').filter(function(x){return x.id!==me.id});seen.unshift(me);sv('zouni_seen',seen.slice(0,8));
    var fb=document.querySelector('.fav');function paint(){var on=ld('zouni_fav').some(function(x){return x.id===me.id});fb.classList.toggle('on',on);fb.textContent=on?'已收藏':'收藏'}paint();
    fb.addEventListener('click',function(){var f=ld('zouni_fav'),on=f.some(function(x){return x.id===me.id});f=on?f.filter(function(x){return x.id!==me.id}):[me].concat(f);sv('zouni_fav',f);paint();toast(on?'已取消收藏':'已收藏，首页能找到')});
    document.querySelector('.share').addEventListener('click',function(){var u=location.href.split('#')[0];if(navigator.share){navigator.share({title:document.title,url:u}).catch(function(){})}else{try{navigator.clipboard.writeText(u);toast('链接已复制')}catch(e){prompt('复制这个链接',u)}}});
    var nav=document.querySelector('.daynav');if(nav){var as=[].slice.call(nav.querySelectorAll('a'));window.addEventListener('scroll',function(){var cur=0;as.forEach(function(a,i){var s=document.getElementById('d'+(i+1));if(s&&s.getBoundingClientRect().top<140)cur=i+1});as.forEach(function(a,i){a.classList.toggle('on',i+1===cur)})},{passive:true})}}
  document.querySelectorAll('.mine').forEach(function(sec){var ul=sec.querySelector('ul'),k=ul.dataset.k==='fav'?'zouni_fav':'zouni_seen',xs=ld(k);if(!xs.length)return;sec.hidden=false;
    ul.innerHTML=xs.map(function(x){return'<li><a href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+String(x.label).replace(/</g,'&lt;')+'</b><span>'+String(x.title).replace(/</g,'&lt;')+'</span></a></li>'}).join('')});
})();
