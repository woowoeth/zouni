(function(){
  function ld(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}}
  function sv(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  function toast(t){var d=document.createElement('div');d.className='toast';d.textContent=t;document.body.appendChild(d);setTimeout(function(){d.remove()},1700)}
  // 日出日落：按今天的月份和每天的坐标算
  function sun(lat,lon,dt,rise){var n=Math.round((dt-new Date(dt.getFullYear(),0,0))/864e5),r=Math.PI/180,lh=lon/15,t=n+((rise?6:18)-lh)/24,M=.9856*t-3.289,L=(M+1.916*Math.sin(M*r)+.02*Math.sin(2*M*r)+282.634)%360,RA=(Math.atan(.91764*Math.tan(L*r))/r+360)%360;RA=(RA+(Math.floor(L/90)*90-Math.floor(RA/90)*90))/15;var sd=.39782*Math.sin(L*r),cd=Math.cos(Math.asin(sd)),cH=(Math.cos(90.833*r)-sd*Math.sin(lat*r))/(cd*Math.cos(lat*r));if(cH>1||cH<-1)return'—';var H=(rise?360-Math.acos(cH)/r:Math.acos(cH)/r)/15,T=H+RA-.06571*t-6.622,lo=((T-lh)%24+24+8)%24,h=Math.floor(lo),m=Math.round((lo-h)*60);if(m==60){h++;m=0}return(h<10?'0':'')+h+':'+(m<10?'0':'')+m}
  var now=new Date();
  document.querySelectorAll('.sun').forEach(function(b){var d=b.dataset.date?new Date(b.dataset.date+'T12:00:00'):now;b.textContent=sun(+b.dataset.lat,+b.dataset.lng,d,b.dataset.k==='rise')});

  // ——— 行程页 ———
  var art=document.querySelector('article.trip');
  if(art){
    var me={id:art.dataset.id,label:art.dataset.label,title:art.dataset.title};
    var seen=ld('zouni_seen').filter(function(x){return x.id!==me.id});seen.unshift(me);sv('zouni_seen',seen.slice(0,8));
    // 几个人去
    var p=document.querySelector('.price[data-cost]'),pp=document.querySelector('.pp'),box=document.querySelector('.ppl');
    if(p&&p.dataset.cost&&box){var C=JSON.parse(p.dataset.cost),N=2;
      function upd(){var rooms=Math.ceil(N/2),car=C.perCar?C.carTotal/N:C.tollsPP,lodge=C.lodgeRoom*rooms/N,loc=C.tixPP+C.foodPP+car+lodge,r=function(v){return(Math.round(v/100)*100).toLocaleString('en-US')};p.textContent='¥'+r(loc+C.trans[0])+'–'+r(loc+C.trans[1]);box.querySelector('b').textContent=N+' 人';pp.textContent=N+' 人 · 每人 '+(box.hidden?'›':'▴');var ds=document.querySelector('.dock small');if(ds)ds.textContent=N+' 人 · 每人 '+p.textContent}
      function tog(){box.hidden=!box.hidden;upd()}
      pp.addEventListener('click',tog);p.addEventListener('click',tog);
      box.querySelectorAll('button').forEach(function(x){x.addEventListener('click',function(){N=Math.max(1,Math.min(6,N+(+x.dataset.d)));upd()})})}
    // 出发前打勾
    var pk='zouni_prep_'+me.id,done=ld(pk);
    document.querySelectorAll('.pre input[type=checkbox]').forEach(function(x){x.checked=done.indexOf(+x.dataset.k)>=0;x.addEventListener('change',function(){var d=ld(pk).filter(function(k){return k!==+x.dataset.k});if(x.checked)d.push(+x.dataset.k);sv(pk,d)})});
    // 收进行程
    var fb=document.querySelector('.fav');
    function paint(){var on=ld('zouni_fav').some(function(x){return x.id===me.id});fb.classList.toggle('on',on);fb.textContent=on?'已收进':'收进行程'}
    if(fb){paint();fb.addEventListener('click',function(){var f=ld('zouni_fav'),on=f.some(function(x){return x.id===me.id});f=on?f.filter(function(x){return x.id!==me.id}):[me].concat(f);sv('zouni_fav',f);paint();toast(on?'已从我的行程里拿掉':'已收进，本期页“我的行程”里能找到')})}
    // 分享、复制
    var sh=document.querySelector('.share');if(sh)sh.addEventListener('click',function(){var u=location.href.split('#')[0];if(navigator.share){navigator.share({title:document.title,url:u}).catch(function(){})}else{try{navigator.clipboard.writeText(u);toast('链接已复制')}catch(e){prompt('复制这个链接',u)}}});
    var cp=document.querySelector('.copy');if(cp)cp.addEventListener('click',function(){var out=[document.querySelector('.hero h1').innerText,location.href.split('#')[0],''];
      document.querySelectorAll('.day').forEach(function(d){out.push(d.querySelector('header small').innerText+' · '+d.querySelector('h2').innerText);
        d.querySelectorAll('.tl .r').forEach(function(r){if(r.classList.contains('dep'))return;out.push('  '+r.querySelector('time').innerText+'  '+r.querySelector('.m').innerText.replace(/\s+/g,' ').trim())});out.push('')});
      var txt=out.join('\n');try{navigator.clipboard.writeText(txt).then(function(){toast('行程已复制，可以直接粘贴到微信')},function(){prompt('复制下面的行程',txt)})}catch(e){prompt('复制下面的行程',txt)}});
    // 今晚住：看另外两档
    document.querySelectorAll('.stays .tog').forEach(function(b){b.addEventListener('click',function(){var s=b.parentElement;s.classList.toggle('open');b.textContent=s.classList.contains('open')?'收起另外两档':'看另外两档'})});
    // 天数条高亮
    var nav=document.querySelector('.daynav');if(nav){var as=[].slice.call(nav.querySelectorAll('a'));window.addEventListener('scroll',function(){var cur=0;as.forEach(function(a,i){var s=document.getElementById('d'+(i+1));if(s&&s.getBoundingClientRect().top<140)cur=i+1});as.forEach(function(a,i){a.classList.toggle('on',i+1===cur)})},{passive:true})}
  }

  // ——— 点评：手机上先试 App，打不开（或在微信里）再去网页 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.dp[data-app]');if(!a)return;
    var mobile=/iPhone|iPad|Android/i.test(navigator.userAgent),wx=/MicroMessenger/i.test(navigator.userAgent);if(!mobile||wx)return;
    e.preventDefault();var web=a.href,t=Date.now(),gone=false;function hid(){gone=true}document.addEventListener('visibilitychange',hid,{once:true});
    location.href=a.dataset.app;setTimeout(function(){if(!gone&&!document.hidden&&Date.now()-t<2500)location.href=web},1200)});
  // ——— 本期：现在去正好，按“我有几天”筛、再看更多 ———
  var dc=document.querySelector('.dchips');
  if(dc){var lis=[].slice.call(document.querySelectorAll('.now .items li')),mb=document.querySelector('.moreb'),band='',all=false;
    function show(){var k=0;lis.forEach(function(li){var ok=!band||li.dataset.band===band;if(ok)k++;li.hidden=!ok||(!all&&k>8)});if(mb){var rest=lis.filter(function(li){return(!band||li.dataset.band===band)}).length-8;mb.hidden=all||rest<=0;mb.textContent='再看 '+Math.max(0,rest)+' 条'}}
    dc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;band=b.dataset.b;all=false;dc.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});show()});
    if(mb)mb.addEventListener('click',function(){all=true;show()});show()}
  // ——— 本期：我的行程、最近看过 ———
  document.querySelectorAll('.mine').forEach(function(sec){var ul=sec.querySelector('ul'),k=ul.dataset.k==='fav'?'zouni_fav':'zouni_seen',xs=ld(k);if(!xs.length)return;sec.hidden=false;
    ul.innerHTML=xs.map(function(x){return'<li><a href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+String(x.label).replace(/</g,'&lt;')+' ›</b><span>'+String(x.title).replace(/</g,'&lt;')+'</span></a></li>'}).join('')});

  // ——— 去哪儿 ———
  var flt=document.querySelector('.flt'),mon=document.querySelector('.mon');
  if(flt&&mon){
    var st={fit:true,d:'',low:false,q:'',niche:false,near:false,bud:0,tab:'domestic'},inp=flt.querySelector('input'),cnt=document.querySelector('.cnt'),gl=document.querySelector('.goodline');
    var on=mon.querySelector('button.on');if(on)mon.scrollLeft=on.offsetLeft-(mon.clientWidth-on.offsetWidth)/2;
    function curM(){var b=mon.querySelector('button.on');return b?+b.dataset.m:new Date().getMonth()+1}
    function near(best,m){return best.some(function(x){return Math.abs((x-m+12)%12)===1||Math.abs((m-x+12)%12)===1})}
    function apply(){var m=curM(),n=0,good=[];
      document.querySelectorAll('.scope').forEach(function(sc){sc.hidden=sc.id!==st.tab});
      document.querySelectorAll('.card').forEach(function(c){var best=c.dataset.best.split(',').map(Number),days=c.dataset.days.split(',').map(Number),ok=true,f=c.querySelector('.fit');
        var v=c.dataset.no==='1'?'暂不排':best.indexOf(m)>=0?'正好':near(best,m)?'也行':'不建议';
        f.textContent=v;f.className='fit'+(v==='正好'?'':v==='也行'?' ok':' no');
        var cl=JSON.parse(c.dataset.clim)[m]||['',''];c.querySelector('.cl').textContent=m+' 月：白天 '+cl[0]+'℃，夜里 '+cl[1]+'℃';
        if(st.fit&&(v==='不建议'||v==='暂不排'))ok=false;
        if(st.d==='d1'&&!days.some(function(d){return d>=1&&d<=3}))ok=false;
        if(st.d==='d2'&&!days.some(function(d){return d>=4&&d<=5}))ok=false;
        if(st.d==='d3'&&!days.some(function(d){return d>=6}))ok=false;
        if(st.low&&c.dataset.high==='1')ok=false;
        if(st.niche&&c.dataset.niche==='0')ok=false;
        if(st.bud&&!(c.dataset.plo!==''&&+c.dataset.plo<=st.bud))ok=false;
        if(st.near&&!(c.dataset.km&&+c.dataset.km<=500))ok=false;
        if(st.q&&c.dataset.q.toLowerCase().indexOf(st.q)<0)ok=false;
        var hp=c.querySelector('.hit'),why=st.q?c.dataset.hits.split('|').filter(function(h){return h.toLowerCase().indexOf(st.q)>=0}).slice(0,3):[];hp.hidden=!why.length;hp.textContent=why.length?'有 '+why.join('、'):'';
        c.hidden=!ok;var inTab=c.closest('.scope').id===st.tab;if(ok&&inTab)n++;if(v==='正好'&&inTab)good.push(c.dataset.name)});
      document.querySelectorAll('.reg').forEach(function(r){r.hidden=!r.querySelector('.card:not([hidden])')});
      cnt.textContent=n?('符合的 '+n+' 个'):'没有符合的，去掉一个条件再看看';
      gl.textContent=good.length?(m+' 月正好去 '+good.length+' 个：'+good.slice(0,10).join('、')+(good.length>10?' 等':'')):(m+' 月没有正好去的，看看“也行”的')}
    mon.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});apply()});
    document.querySelectorAll('.tabs button').forEach(function(b){b.addEventListener('click',function(){st.tab=b.dataset.t;document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x===b)});apply()})});
    var ft=document.querySelector('.ftog');ft.addEventListener('click',function(){flt.hidden=!flt.hidden;ft.classList.toggle('on',!flt.hidden);ft.textContent=flt.hidden?'筛选 ▾':'筛选 ▴'});
    inp.addEventListener('input',function(){st.q=inp.value.trim().toLowerCase();apply()});
    flt.querySelectorAll('.row button[data-f]').forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;
      if(f==='fit'||f==='low'||f==='niche'||f==='near'){st[f]=!st[f];b.classList.toggle('on',st[f])}
      else{st.d=st.d===f?'':f;flt.querySelectorAll('[data-f^="d"]').forEach(function(x){x.classList.toggle('on',x.dataset.f===st.d)})}apply()})});
    var bud=flt.querySelector('.bud');bud.addEventListener('change',function(){st.bud=+bud.value||0;apply()});
    var ORG={'北京':[39.9,116.4],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'杭州':[30.27,120.16],'南京':[32.06,118.8],'成都':[30.66,104.06],'重庆':[29.56,106.55],'武汉':[30.59,114.3],'西安':[34.34,108.94],'香港':[22.3,114.17]};
    function km(a,b){var r=Math.PI/180,dl=(b[1]-a[1])*r,p1=a[0]*r,p2=b[0]*r,h=Math.sin((p2-p1)/2)*Math.sin((p2-p1)/2)+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)*Math.sin(dl/2);return Math.round(2*6371*Math.asin(Math.sqrt(h)))}
    var sel=flt.querySelector('select.org'),nearB=flt.querySelector('[data-f="near"]');
    function origin(o){try{localStorage.setItem('zouni_org',o)}catch(e){}nearB.hidden=!o;if(!o){st.near=false;nearB.classList.remove('on')}
      document.querySelectorAll('.cards').forEach(function(ul){var cs=[].slice.call(ul.children);cs.forEach(function(c){var d=o?km(ORG[o],[+c.dataset.lat,+c.dataset.lng]):null,p=c.querySelector('.dist');c.dataset.km=d==null?'':d;p.hidden=d==null;if(d!=null)p.textContent=d<30?'就在'+o:'离'+o+' '+d.toLocaleString('en-US')+' 公里'+(d<=500?' · 周末能去':'')});
        if(o)cs.sort(function(a,b){return(+a.dataset.km)-(+b.dataset.km)}).forEach(function(c){ul.appendChild(c)})});
      document.querySelectorAll('.scope').forEach(function(sc){var regs=[].slice.call(sc.querySelectorAll('.reg'));regs.forEach(function(r,i){if(r.dataset.i==null)r.dataset.i=i;r.dataset.min=o?Math.min.apply(null,[].map.call(r.querySelectorAll('.card'),function(c){return +c.dataset.km})):r.dataset.i});
        regs.sort(function(a,b){return(+a.dataset.min)-(+b.dataset.min)}).forEach(function(r){sc.appendChild(r)})});apply()}
    sel.addEventListener('change',function(){origin(sel.value)});
    try{var o0=localStorage.getItem('zouni_org');if(o0&&ORG[o0]){sel.value=o0;origin(o0)}}catch(e){}
    apply()}
})();
