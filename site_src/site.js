(function(){
  // 没网时告诉一声：看的是存在手机上的版本
  function netBar(){var b=document.querySelector('.offline');if(navigator.onLine){if(b)b.remove();return}if(!b){b=document.createElement('div');b.className='offline';b.textContent='现在没有网络，看的是之前打开时存下的版本';document.body.appendChild(b)}}
  window.addEventListener('online',netBar);window.addEventListener('offline',netBar);netBar();
  if('serviceWorker' in navigator&&location.protocol==='https:')window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})});
  function ld(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}}
  function sv(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  function toast(t){var d=document.createElement('div');d.className='toast';d.textContent=t;document.body.appendChild(d);setTimeout(function(){d.remove()},1700)}
  // 日出日落：按今天的月份和每天的坐标算
  function sun(lat,lon,dt,rise,tz){tz=(tz===undefined||isNaN(tz))?8:tz;var n=Math.round((dt-new Date(dt.getFullYear(),0,0))/864e5),r=Math.PI/180,lh=lon/15,t=n+((rise?6:18)-lh)/24,M=.9856*t-3.289,L=(M+1.916*Math.sin(M*r)+.02*Math.sin(2*M*r)+282.634)%360,RA=(Math.atan(.91764*Math.tan(L*r))/r+360)%360;RA=(RA+(Math.floor(L/90)*90-Math.floor(RA/90)*90))/15;var sd=.39782*Math.sin(L*r),cd=Math.cos(Math.asin(sd)),cH=(Math.cos(90.833*r)-sd*Math.sin(lat*r))/(cd*Math.cos(lat*r));if(cH>1||cH<-1)return'—';var H=(rise?360-Math.acos(cH)/r:Math.acos(cH)/r)/15,T=H+RA-.06571*t-6.622,lo=((T-lh)%24+24+tz)%24,h=Math.floor(lo),m=Math.round((lo-h)*60);if(m==60){h++;m=0}return(h<10?'0':'')+h+':'+(m<10?'0':'')+m}


  // ——— 行程页顶部三格：放不下时三项一起缩小一号，始终同一个字号 ———
  function fitGlance(){var bs=[].slice.call(document.querySelectorAll('.glance>div>b'));if(!bs.length)return;bs.forEach(function(b){b.style.fontSize=''});var fs=20;
    while(fs>15&&bs.some(function(b){return b.scrollWidth>b.clientWidth+1})){fs--;bs.forEach(function(b){b.style.fontSize=fs+'px'})}}
  fitGlance();window.addEventListener('resize',fitGlance);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fitGlance);
  var gp=document.querySelector('.glance .price');if(gp&&window.MutationObserver)new MutationObserver(function(){fitGlance()}).observe(gp,{childList:true,characterData:true,subtree:true});
  // ——— 站内日期面板（不用系统控件）：月历、过去的日子不能选、标出最好的日子、几个常用日子一点就选 ———
  function openPicker(o){var W='一二三四五六日',val=o.value,min=o.min,best=o.best;var cur=new Date(val+'T12:00:00');var vy=cur.getFullYear(),vm=cur.getMonth();
    function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
    function inBest(d){if(!best)return false;var m=('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);return best[0]<=best[1]?(m>=best[0]&&m<=best[1]):(m>=best[0]||m<=best[1])}
    var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';sh.setAttribute('role','dialog');sh.setAttribute('aria-label','选出发日期');
    function sat(k){var d=new Date();d.setHours(12);var add=(6-d.getDay()+7)%7;d.setDate(d.getDate()+add+7*k);return d}
    function nm1(){var d=new Date();d.setHours(12);d.setMonth(d.getMonth()+1,1);return d}
    var quick=[['这周六',sat(0)],['下周六',sat(1)],['下个月 1 号',nm1()]];
    function render(){var first=new Date(vy,vm,1,12),start=(first.getDay()+6)%7,days=new Date(vy,vm+1,0).getDate(),h='';
      h+='<div class="pk-h"><b>选出发日期</b><button type="button" class="pk-x" aria-label="关上">关上</button></div>';
      h+='<div class="pk-q">'+quick.map(function(q,i){return'<button type="button" data-q="'+i+'" '+(iso(q[1])<min?'disabled':'')+'>'+q[0]+'<small>'+(q[1].getMonth()+1)+'/'+q[1].getDate()+'</small></button>'}).join('')+'</div>';
      h+='<div class="pk-m"><button type="button" class="pk-p" aria-label="上个月">‹</button><b>'+vy+' 年 '+(vm+1)+' 月</b><button type="button" class="pk-n" aria-label="下个月">›</button></div>';
      h+='<div class="pk-w">'+W.split('').map(function(x){return'<span>'+x+'</span>'}).join('')+'</div><div class="pk-g">';
      for(var i=0;i<start;i++)h+='<span></span>';
      for(var dd=1;dd<=days;dd++){var d=new Date(vy,vm,dd,12),v=iso(d),cls=[];if(v<min)cls.push('off');if(v===val)cls.push('on');if(v===min)cls.push('td0');if(inBest(d))cls.push('best');if(d.getDay()===0||d.getDay()===6)cls.push('we');
        h+='<button type="button" data-v="'+v+'" class="'+cls.join(' ')+'" '+(v<min?'disabled':'')+'>'+dd+'</button>'}
      h+='</div>'+(best?'<p class="pk-tip"><i></i>绿色是这条线最好的日子</p>':'<p class="pk-tip">选好就关上，页面会跟着这天重新排</p>');
      sh.innerHTML=h;
      sh.querySelector('.pk-p').disabled=(vy*12+vm)<=(+min.slice(0,4)*12+(+min.slice(5,7)-1))}
    function close(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
    function pick(v){close();o.onPick(v)}
    sh.addEventListener('click',function(e){var b=e.target.closest('button');if(!b||b.disabled)return;
      if(b.classList.contains('pk-x'))return close();if(b.classList.contains('pk-p')){vm--;if(vm<0){vm=11;vy--}return render()}if(b.classList.contains('pk-n')){vm++;if(vm>11){vm=0;vy++}return render()}
      if(b.dataset.v)return pick(b.dataset.v);if(b.dataset.q)return pick(iso(quick[+b.dataset.q][1]))});
    mask.addEventListener('click',close);document.addEventListener('keydown',function k(e){if(e.key==='Escape'){close();document.removeEventListener('keydown',k)}});
    render();document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open');var f=sh.querySelector('.pk-g .on')||sh.querySelector('.pk-g button:not([disabled])');if(f)f.focus()}
  var now=new Date();
  document.querySelectorAll('.sun').forEach(function(b){var d=b.dataset.date?new Date(b.dataset.date+'T12:00:00'):now;b.textContent=sun(+b.dataset.lat,+b.dataset.lng,d,b.dataset.k==='rise',parseFloat(b.dataset.tz))});

  // ——— 返回：从本站点进来的就退回上一页（筛选和滚动位置都还在） ———
  // 返回：记住这次在站内走过的页面；有上一页就退回上一页，没有（直接打开的）就回首页
  var H=[];try{H=JSON.parse(sessionStorage.getItem('zouni_hist')||'[]')}catch(e){}
  var here=location.pathname;if(H.length>=2&&H[H.length-2]===here)H.pop();else if(H[H.length-1]!==here)H.push(here);H=H.slice(-30);
  try{sessionStorage.setItem('zouni_hist',JSON.stringify(H))}catch(e){}
  document.querySelectorAll('a.back').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();if(H.length>=2&&history.length>1){history.back()}else{location.href='/'}})});
  // ——— 出发地（首页“替我挑”里选的，或者定位）：怎么去、首页封面都按它来 ———
  var ZORIG={'北京':[39.90,116.40],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'成都':[30.66,104.07],'杭州':[30.27,120.16],'西安':[34.26,108.94],'武汉':[30.59,114.31],'南京':[32.06,118.80],'重庆':[29.56,106.55],'长沙':[28.23,112.94],'郑州':[34.75,113.63],'天津':[39.13,117.20],'苏州':[31.30,120.58],'厦门':[24.48,118.09],'昆明':[25.04,102.71],'沈阳':[41.80,123.43],'青岛':[36.07,120.38],'香港':[22.32,114.17]};
  function zOrigin(){try{var st=JSON.parse(localStorage.getItem('zouni_pick')||'{}');if(st.o==='here'&&st.lat)return{n:'你这里',lat:st.lat,lng:st.lng};var o=st.o||localStorage.getItem('zouni_org');if(o&&ZORIG[o])return{n:o,lat:ZORIG[o][0],lng:ZORIG[o][1]}}catch(e){}return null}
  function zKm(a,b,c,d){var r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
  function zGoWay(g,o,km){if(km<60)return'就在'+o+'附近，当天过去就行';if(+g.ab&&km>5000)return'从'+o+'坐飞机，约 '+Math.max(1,Math.round(km/750+1))+' 小时'+(km>8500?'，多数要转一次机':'');if(+g.ab)return'从'+o+'坐飞机过去，飞行约 '+Math.max(1,Math.round(km/700+1))+' 小时';if(+g.drv)return'从'+o+'开过去约 '+Math.max(1,Math.round(km*1.25/80))+' 小时；也可以坐高铁或飞机到了再租车';if(km<=1200)return'从'+o+'坐高铁约 '+Math.max(1,Math.round(km/230+0.5))+' 小时';return'从'+o+'坐飞机最省事，飞行约 '+Math.max(1,Math.round(km/700+1))+' 小时'}
  // ——— 使用统计：只记“做了什么”（改日期、加一天、分享……），不记人；没配统计地址时什么都不发 ———
  var ZSTATS=(document.querySelector('meta[name="zouni-stats"]')||{}).content||'';
  function ztrack(ev,props){try{var d={e:ev,p:location.pathname,t:Date.now()};if(props)d.x=props;(window.__zq=window.__zq||[]).push(d);if(ZSTATS&&navigator.sendBeacon)navigator.sendBeacon(ZSTATS,JSON.stringify(d))}catch(e){}}
  ztrack('view');
  document.addEventListener('click',function(e){var a=e.target.closest('a,button');if(!a)return;var c=a.className||'',h=a.getAttribute('href')||'',ev=null;
    if(/ctrip\.com/.test(h))ev='去订酒店';else if(a.classList.contains('bkl')||/12306|flight/.test(h))ev='去预约或买票';else if(c.indexOf('fav')>=0)ev='收藏';else if(c.indexOf('tvbtn')>=0)ev='打开按天看';else if(c.indexOf('todoall')>=0)ev='打开要办的事';
    else if(a.dataset&&a.dataset.a)ev='分享·'+a.dataset.a;else if(c.indexOf('adj')>=0)ev='调整一站';else if(c.indexOf('rmgo')>=0)ev='去掉一天';else if(c.indexOf('addday')>=0||(a.closest('.addday')&&c.indexOf('add')>=0))ev='加一天';
    else if(a.closest('.pkres'))ev='替我挑·点推荐';else if(c.indexOf('xhs')>=0)ev='看实景';else if(c.indexOf('ic map')>=0||c.indexOf('tvnav')>=0)ev='导航';
    if(ev)ztrack(ev)},true);

  // ——— 常见问题：默认收起，点了展开 ———
  document.addEventListener('click',function(e){var b=e.target.closest('.faqmore');if(!b)return;var dl=b.parentNode.querySelector('dl');if(!dl)return;var open=dl.hidden;dl.hidden=!open;b.textContent=open?'收起 ‹':'看 '+dl.querySelectorAll('dt').length+' 个问题 ›';ztrack('看常见问题')});


  // 打开 App：没装的话，过一会儿页面还在前台，就提示一句（不退回网页）
  function zOpen(u,name){var t0=Date.now();location.href=u;setTimeout(function(){if(!document.hidden&&Date.now()-t0<3000&&typeof toast==='function')toast('没打开'+name+'，可能还没装这个 App')},1600)}
  // ——— 导航、订酒店、点评、小红书只走 App：电脑上和微信里打不开 App，就不放这些入口 ———
  var MOB=/iPhone|iPad|Android/i.test(navigator.userAgent),WXB=/MicroMessenger/i.test(navigator.userAgent);
  if(!MOB||WXB)document.documentElement.classList.add('noapp');
  if(WXB){try{if(!sessionStorage.getItem('zouni_wxtip')){sessionStorage.setItem('zouni_wxtip','1');setTimeout(function(){if(typeof toast==='function')toast('微信里打不开高德、携程、点评、小红书：点右上角 ··· 选“在浏览器打开”')},1200)}}catch(e){}}
  document.addEventListener('click',function(e){var a=e.target.closest('a.tl2,.stays .bk a.btn');if(!a||!MOB||WXB)return;   // 订酒店：在携程 App 里打开这家
    e.preventDefault();try{zOpen('ctrip://wireless/h5?url='+btoa(a.href)+'&type=2','携程旅行')}catch(x){}});
  // ——— 行程页 ———
  var art=document.querySelector('article.trip');
  if(art){
    var me={id:art.dataset.id,label:art.dataset.label,title:art.dataset.title};
    var MYKEYS=['zouni_start_','zouni_st_','zouni_drop_','zouni_adj_','zouni_extra_','zouni_slow_','zouni_n_','zouni_rain_','zouni_fill_','zouni_rmday_'];
    try{var hm_=/#mine=([A-Za-z0-9_\-]+)/.exec(location.hash);if(hm_){var js_=decodeURIComponent(escape(atob(hm_[1].replace(/-/g,'+').replace(/_/g,'/'))));var st_=JSON.parse(js_);
      MYKEYS.forEach(function(k){var v=st_[k];if(v==null)localStorage.removeItem(k+me.id);else localStorage.setItem(k+me.id,typeof v==='string'?v:JSON.stringify(v))});
      history.replaceState(null,'',location.pathname);setTimeout(function(){toast('打开的是朋友改过的版本')},600)}}catch(e){}
    var RDK='zouni_rmday_'+me.id,RD=[];try{RD=JSON.parse(localStorage.getItem(RDK)||'[]')}catch(e){}
    (function(){var secs=[].slice.call(document.querySelectorAll('.day')),ovl=[].slice.call(document.querySelectorAll('.overview ol > li'));
      secs.forEach(function(s,i){if(s.dataset.oi==null)s.dataset.oi=i});ovl.forEach(function(li,i){if(li.dataset.oi==null)li.dataset.oi=i});
      if(RD.length>=secs.length)RD=[];var gone=[];
      function stayOf(s){var m=s.querySelector('.r.stay .m');return m?m.textContent.replace(/\s+/g,'').replace(/^住·/,''):''}
      secs.forEach(function(s,i){if(RD.indexOf(+s.dataset.oi)<0)return;var st=s.querySelector('.stays');
        if(st){var nx=secs[i+1];if(nx&&RD.indexOf(+nx.dataset.oi)<0&&!nx.querySelector('.stays')&&stayOf(nx)===stayOf(s)){var tl2=nx.querySelector('.tl');if(tl2)tl2.parentNode.insertBefore(st,tl2.nextSibling)}}   // 去掉的那天带着住宿卡，而第二天还住同一处：卡片挪到第二天
        gone.push({oi:+s.dataset.oi,t:(s.querySelector('h2').childNodes[0]||{textContent:''}).textContent.trim()});s.remove()});
      // “连住 N 晚”按剩下的天重算
      var lf=[].slice.call(document.querySelectorAll('.day'));lf.forEach(function(s,i){var st=s.querySelector('.stays');if(!st)return;var sp=st.querySelector('.sh span:last-child');if(!sp)return;var me0=stayOf(s),k=i,nn=0;
        while(k<lf.length-1&&stayOf(lf[k])===me0&&me0){nn++;k++}var base0=sp.textContent.replace(/(^|\s*·\s*)连住\s*\d+\s*晚/g,'').trim();sp.textContent=base0+(nn>1?(base0?' · ':'')+'连住 '+nn+' 晚':'')});
      ovl.forEach(function(li){if(RD.indexOf(+li.dataset.oi)>=0)li.remove()});
      var left=[].slice.call(document.querySelectorAll('.day')),CN='一二三四五六七八九十';
      if(gone.length){left.forEach(function(s,i){s.id='d'+(i+1);var no=s.querySelector('.no');if(no)no.textContent=('0'+(i+1)).slice(-2);var sm=s.querySelector('header small');if(sm){var p=sm.textContent.split(' · ');sm.textContent='第'+(i<10?CN[i]:(i+1))+'天'+(p.length>1?' · '+p.slice(1).join(' · '):'')}});
        [].slice.call(document.querySelectorAll('.overview ol > li')).forEach(function(li,i){var a=li.querySelector('a');if(a)a.setAttribute('href','#d'+(i+1));var b=li.querySelector('b');if(b)b.textContent=('0'+(i+1)).slice(-2)});
        var nv=document.querySelector('.daynav');if(nv){var as=nv.querySelectorAll('a');for(var k=as.length-1;k>=left.length;k--)as[k].remove();[].slice.call(nv.querySelectorAll('a')).forEach(function(a,i){a.setAttribute('href','#d'+(i+1));a.textContent=i+1})}
        var oh=document.querySelector('.overview h2');if(oh)oh.textContent=left.length+' 天，怎么排';var gb=document.querySelector('.glance b.big');if(gb&&gb.firstChild)gb.firstChild.textContent=left.length;
        var ov=document.querySelector('.overview ol');if(ov)ov.insertAdjacentHTML('afterend','<p class="rmnote">去掉了'+gone.map(function(g){return'「'+g.t+'」'}).join('')+' <button type="button" class="rmback">恢复</button></p>');
        var rb=document.querySelector('.rmback');if(rb)rb.addEventListener('click',function(){try{localStorage.removeItem(RDK)}catch(e){}location.reload()})}
      left.forEach(function(s){if(s.dataset.extra||s.querySelector('.rmorig'))return;if(left.length<2)return;s.insertAdjacentHTML('beforeend','<button type="button" class="rmday rmorig">去掉这一天</button>')});
      document.addEventListener('click',function(e){var b=e.target.closest('.rmorig');if(!b)return;var s=b.closest('.day'),t=(s.querySelector('h2').childNodes[0]||{textContent:''}).textContent.trim();
        var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
        sh.innerHTML='<div class="pk-h"><b>去掉这一天？</b><button type="button" class="pk-x">算了</button></div><p class="xnote">「'+t+'」整天不去了，后面的天往前挪一天；之后在“怎么排”下面可以恢复</p><div class="xd"><button type="button" class="rmgo"><b>去掉这一天</b></button></div>';
        function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
        sh.querySelector('.pk-x').addEventListener('click',cl);mask.addEventListener('click',cl);
        sh.querySelector('.rmgo').addEventListener('click',function(){var R2=[];try{R2=JSON.parse(localStorage.getItem(RDK)||'[]')}catch(e){}R2.push(+s.dataset.oi);try{localStorage.setItem(RDK,JSON.stringify(R2));sessionStorage.setItem('zouni_rm_toast',t)}catch(e){}location.reload()});
        document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')});
      try{var tt=sessionStorage.getItem('zouni_rm_toast');if(tt){sessionStorage.removeItem('zouni_rm_toast');setTimeout(function(){toast('去掉了「'+tt+'」，后面的天往前挪了')},500)}}catch(e){}})();
    function myState(){var o={},any=false;MYKEYS.forEach(function(k){var v=null;try{v=localStorage.getItem(k+me.id)}catch(e){}if(v!=null&&v!==''&&v!=='{}'&&v!=='[]'){any=true;try{o[k]=JSON.parse(v)}catch(e){o[k]=v}}});return any?o:null}
    function myLink(){var o=myState(),u0=location.origin+location.pathname;if(!o)return u0;var b=btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,'');return u0+'#mine='+b}
    var seen=ld('zouni_seen').filter(function(x){return x.id!==me.id});seen.unshift(me);sv('zouni_seen',seen.slice(0,8));
    // 几个人去
    var p=document.querySelector('.price[data-cost]'),pp=document.querySelector('.pp'),box=document.querySelector('.ppl');
    if(p&&p.dataset.cost&&box){var C=JSON.parse(p.dataset.cost),N=2;try{var n0=+localStorage.getItem('zouni_n_'+me.id);if(n0>=1&&n0<=12)N=n0}catch(e){}
      function upd(){var rooms=Math.ceil(N/2),car=C.perCar?Math.ceil(N/4)*C.carTotal/N:C.tollsPP,lodge=C.lodgeRoom*rooms/N,loc=C.tixPP+C.foodPP+car+lodge,r=function(v){var k=Math.round(v/100)/10;return(k<100?(+k.toFixed(1)).toString():Math.round(k).toString())};p.textContent='¥'+r(loc+C.trans[0])+'K–'+r(loc+C.trans[1])+'K';box.querySelector('b').textContent=N+' 人';pp.textContent=N+' 人 · 每人 '+(box.hidden?'›':'▴');var ds=document.querySelector('.dock small');if(ds)ds.textContent=N+' 人 · 每人 '+p.textContent;try{if(N!==2)localStorage.setItem('zouni_n_'+me.id,N);else localStorage.removeItem('zouni_n_'+me.id)}catch(e){}}
      function tog(){box.hidden=!box.hidden;upd()}
      pp.addEventListener('click',tog);p.addEventListener('click',tog);
      box.querySelectorAll('button').forEach(function(x){x.addEventListener('click',function(){N=Math.max(1,Math.min(6,N+(+x.dataset.d)));upd()})});
      if(N!==2)upd()}   // 记住的人数一打开就算上（原来要点一下才更新，刷新后看起来像没记住）
    // 出发前打勾
    var pk='zouni_prep_'+me.id,done=ld(pk);
    document.querySelectorAll('.pre input[type=checkbox]').forEach(function(x){x.checked=done.indexOf(+x.dataset.k)>=0;x.addEventListener('change',function(){var d=ld(pk).filter(function(k){return k!==+x.dataset.k});if(x.checked)d.push(+x.dataset.k);sv(pk,d)})});
    // 收进行程
    var fb=document.querySelector('.fav');
    function paint(){var on=ld('zouni_fav').some(function(x){return x.id===me.id});fb.classList.toggle('on',on);var sp=fb.querySelector('span');if(sp)sp.textContent=on?'已收进':'收进行程';else fb.textContent=on?'已收进':'收进行程'}
    if(fb){paint();fb.addEventListener('click',function(){var f=ld('zouni_fav'),on=f.some(function(x){return x.id===me.id});f=on?f.filter(function(x){return x.id!==me.id}):[me].concat(f);sv('zouni_fav',f);paint();toast(on?'已从我的行程里拿掉':'已收进，本期页“我的行程”里能找到')})}
    // 分享、复制
    function shareLink(){var u=myLink();if(navigator.share){navigator.share({title:document.title,url:u}).catch(function(){})}else{try{navigator.clipboard.writeText(u);toast('链接已复制')}catch(e){prompt('复制这个链接',u)}}}
    var sh=document.querySelector('.share');if(sh)sh.addEventListener('click',function(){var mask=document.createElement('div');mask.className='pk-mask';var s2=document.createElement('div');s2.className='pk';
      s2.innerHTML='<div class="pk-h"><b>分享</b><button type="button" class="pk-x">关上</button></div><div class="xd"><button type="button" data-a="link"><b>发链接给朋友</b><small>'+(myState()?'带上你改过的日期、时间和加的天':'原版行程')+'</small></button><button type="button" data-a="copy"><b>复制整条行程</b><small>按天的时间和地点，可以直接粘贴到微信</small></button><button type="button" data-a="shot"><b>生成分享图</b><small>长按保存，发朋友圈</small></button><button type="button" data-a="print"><b>打印 / 存成 PDF</b><small>一页页的行程单，给家里人或者出门带着</small></button></div>';
      function cl(){mask.remove();s2.remove();document.body.classList.remove('pk-open')}
      s2.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;if(b.classList.contains('pk-x'))return cl();cl();if(b.dataset.a==='link')shareLink();if(b.dataset.a==='copy')copyTrip();if(b.dataset.a==='shot'){if(window.qrcode)shotTrip();else{var sc=document.createElement('script');sc.src='/assets/qr.js';sc.onload=shotTrip;sc.onerror=shotTrip;document.head.appendChild(sc)}}if(b.dataset.a==='print')setTimeout(function(){window.print()},300)});
      mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(s2);document.body.classList.add('pk-open')});
    function copyTrip(){var out=[document.querySelector('.hero h1').innerText,location.href.split('#')[0],''];
      document.querySelectorAll('.day').forEach(function(d){out.push(d.querySelector('header small').innerText+' · '+d.querySelector('h2').innerText);
        d.querySelectorAll('.tl .r').forEach(function(r){if(r.classList.contains('dep'))return;out.push('  '+r.querySelector('time').innerText+'  '+r.querySelector('.m').innerText.replace(/\s+/g,' ').trim())});out.push('')});
      var txt=out.join('\n');try{navigator.clipboard.writeText(txt).then(function(){toast('行程已复制，可以直接粘贴到微信')},function(){prompt('复制下面的行程',txt)})}catch(e){prompt('复制下面的行程',txt)}}
    // 改出发日期：日期、星期、日出日落、往年气温、底栏一起变；记在本机
    var dk=document.querySelector('.dpk'),dtb=document.querySelector('.dt');
    if(dk&&dtb){var sk='zouni_start_'+me.id,W='日一二三四五六';
      function fmt(d){return(d.getMonth()+1)+'/'+d.getDate()}
      function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
      function applyStart(v){var d0=new Date(v+'T12:00:00'),secs=[].slice.call(document.querySelectorAll('.day')),n=secs.length;
        secs.forEach(function(sec,i){var di=new Date(d0.getTime()+i*864e5),sm=sec.querySelector('header small');sm.textContent=sm.textContent.split(' · ')[0]+' · '+fmt(di)+' 周'+W[di.getDay()];
          sec.querySelectorAll('.sun').forEach(function(b){b.dataset.date=iso(di);b.textContent=sun(+b.dataset.lat,+b.dataset.lng,di,b.dataset.k==='rise',parseFloat(b.dataset.tz))});
          var cl=sec.querySelector('.cl');if(cl&&cl.dataset.clim){var c=JSON.parse(cl.dataset.clim)[di.getMonth()+1];cl.textContent=c?('往年 '+(di.getMonth()+1)+' 月平均：白天 '+c[0]+'℃，夜里 '+c[1]+'℃'):''}});
        document.querySelectorAll('.overview i').forEach(function(x,i){x.textContent=fmt(new Date(d0.getTime()+i*864e5))});
        var dN=new Date(d0.getTime()+(n-1)*864e5);dtb.firstChild.textContent=fmt(d0)+'–'+(dN.getMonth()===d0.getMonth()?dN.getDate():fmt(dN))+' ';   // 同一个月写 10/15–17，窄屏不挤
        var db=document.querySelector('.dock b');if(db)db.textContent=fmt(d0)+' 出发 · '+n+' 天'}
      dtb.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();dtb.click()}});
      dtb.addEventListener('click',function(){var b0=dtb.dataset.best?dtb.dataset.best.split(','):null;openPicker({value:dk.value,min:dk.dataset.min||dk.getAttribute('min'),best:b0&&b0.length===2?b0:null,onPick:function(v){dk.value=v;dk.dispatchEvent(new Event('change'))}})});
      dk.addEventListener('change',function(){if(!dk.value)return;try{localStorage.setItem(sk,dk.value)}catch(e){}applyStart(dk.value);var d=new Date(dk.value+'T12:00:00');toast('改成 '+fmt(d)+' 出发了')});
      var mn=dk.dataset.min||dk.min;try{var s0=localStorage.getItem(sk)||localStorage.getItem('zouni_home_date');if(s0&&s0>=mn&&s0!==dk.value){dk.value=s0;applyStart(s0)}}catch(e){}
      // ——— 加一天：自由活动，或从同一目的地的其他线路挑一天接上；记在本机，可以去掉 ———
      var addB=document.querySelector('.addday .add');
      if(addB){var ek='zouni_extra_'+me.id,cands=[];try{cands=JSON.parse(document.getElementById('cands').textContent)}catch(e){}
        var CN='一二三四五六七八九十';function cnDay(i){return'第'+(i<10?CN[i]:(i+1))+'天'}
        [].slice.call(document.querySelectorAll('.day')).forEach(function(s,i){if(!s.dataset.extra&&s.dataset.oi==null)s.dataset.oi=i});
        // 地图跟着重画：加的天也标上（自由活动在原住处，接别的线路的那天画到那里并用虚线连过去），位置重叠的天数合成“1·5”，图下按天重列
        function redrawMap(){var svg=document.querySelector('.hmap svg[data-days]');if(!svg)return;var base=[];try{base=JSON.parse(svg.dataset.days)}catch(e){return}
          var cx=+svg.dataset.cx,cy=+svg.dataset.cy,sc=+svg.dataset.sc,W=+svg.dataset.w,H=+svg.dataset.h;
          function merc(la){la=Math.max(-85,Math.min(85,la));return Math.log(Math.tan(Math.PI/4+la*Math.PI/360))*180/Math.PI}
          function P(la,lo){return[W/2+(lo-cx)*sc,(H-16)/2+4-(merc(la)-cy)*sc]}
          var xs=ld(ek),list=[],prev=null;
          [].slice.call(document.querySelectorAll('.day')).forEach(function(sec){var p=null,nm='',lineFrom=null;
            if(!sec.dataset.extra){var b=base[+sec.dataset.oi];if(b){p=[b[0],b[1]];nm=b[2]}}
            else{var e=xs.filter(function(z){return z.x===sec.dataset.extra})[0];
              if(e&&e.k==='r'&&e.lat){p=P(e.lat,e.lng);nm=sec.querySelector('h2').childNodes[0].textContent.trim();lineFrom=prev;
                var x0=14,y0=14,x1=W-14,y1=H-30;if(prev&&(p[0]<x0||p[0]>x1||p[1]<y0||p[1]>y1)){   // 在图外：标到图边上，图下写明距离
                  var dx=p[0]-prev[0],dy=p[1]-prev[1],t=1;if(dx>0)t=Math.min(t,(x1-prev[0])/dx);if(dx<0)t=Math.min(t,(x0-prev[0])/dx);if(dy>0)t=Math.min(t,(y1-prev[1])/dy);if(dy<0)t=Math.min(t,(y0-prev[1])/dy);
                  p=[prev[0]+dx*t,prev[1]+dy*t];nm+='（约 '+(e.km||'')+' 公里，在图外）'}}
              else{p=prev?prev.slice():null;nm='自由活动'}}
            list.push({p:p,nm:nm,from:lineFrom});if(p&&!lineFrom)prev=p});
          var groups=[];list.forEach(function(it,i){if(!it.p)return;var g=groups.filter(function(g){return Math.abs(g.x-it.p[0])<16&&Math.abs(g.y-it.p[1])<16})[0];if(g)g.ns.push(i+1);else groups.push({x:it.p[0],y:it.p[1],ns:[i+1]})});
          var h='';groups.forEach(function(g){var t=g.ns.join('·'),w=Math.max(17,7+t.length*6.2);h+='<rect x="'+(g.x-w/2).toFixed(1)+'" y="'+(g.y-8.5).toFixed(1)+'" width="'+w.toFixed(1)+'" height="17" rx="8.5" fill="#a63d27" stroke="#fff" stroke-width="1.5"/><text x="'+g.x.toFixed(1)+'" y="'+(g.y+3.6).toFixed(1)+'" text-anchor="middle" font-family="Noto Sans SC,sans-serif" font-size="10" font-weight="700" fill="#fff">'+t+'</text>'});
          var dm=svg.querySelector('.dms');if(dm)dm.innerHTML=h;
          var xl=svg.querySelector('.xl');if(xl)xl.innerHTML=list.filter(function(it){return it.from&&it.p}).map(function(it){return'<path d="M'+it.from[0].toFixed(1)+','+it.from[1].toFixed(1)+' L'+it.p[0].toFixed(1)+','+it.p[1].toFixed(1)+'" fill="none" stroke="#a63d27" stroke-width="2" stroke-dasharray="5 4" stroke-linecap="round"/>'}).join('');
          var lg=svg.parentNode.querySelector('.hlegend');if(lg)lg.innerHTML=list.map(function(it,i){return it.nm?'<span><b>'+(i+1)+'</b>'+String(it.nm).replace(/</g,'&lt;')+'</span>':''}).join('')}
        function renum(){var secs=[].slice.call(document.querySelectorAll('.day'));
          secs.forEach(function(sec,i){sec.id='d'+(i+1);var no=sec.querySelector('.no');if(no)no.textContent=('0'+(i+1)).slice(-2);var sm=sec.querySelector('header small');if(sm){var p=sm.textContent.split(' · ');sm.textContent=cnDay(i)+(p.length>1?' · '+p.slice(1).join(' · '):'')}});
          var nv=document.querySelector('.daynav');if(nv){var a=nv.querySelectorAll('a');for(var k=a.length;k<secs.length;k++)nv.insertAdjacentHTML('beforeend','<a href="#d'+(k+1)+'">'+(k+1)+'</a>');for(var k2=a.length-1;k2>=secs.length;k2--)a[k2].remove()}
          var ol=document.querySelector('.overview ol'),lis=ol?ol.children:[];
          secs.forEach(function(sec,i){if(!sec.dataset.extra)return;var li=ol.querySelector('li[data-x="'+sec.dataset.extra+'"]');if(!li){li=document.createElement('li');li.dataset.x=sec.dataset.extra;ol.appendChild(li)}
            li.innerHTML='<a href="#d'+(i+1)+'"><b>'+('0'+(i+1)).slice(-2)+'</b><i></i><span class="ot"><strong>'+sec.querySelector('h2').childNodes[0].textContent+'</strong><small>加的一天</small></span><em></em></a>'});
          [].slice.call(ol.querySelectorAll('li[data-x]')).forEach(function(li){if(!document.querySelector('.day[data-extra="'+li.dataset.x+'"]'))li.remove()});
          var h=document.querySelector('.overview h2');if(h)h.textContent=secs.length+' 天，怎么排';var gb2=document.querySelector('.glance b.big');if(gb2&&gb2.firstChild)gb2.firstChild.textContent=secs.length;
          applyStart(dk.value);setTimeout(todayBar,0);redrawMap()}
        function dayShell(x,title,body){var sec=document.createElement('section');sec.className='day xday';sec.dataset.extra=x;
          sec.innerHTML='<header><span class="no"></span><div><small>第几天 · </small><h2>'+title+'</h2></div></header>'+body+'<button type="button" class="rmday">去掉这一天</button>';return sec}
        function place(sec){var orig=[].slice.call(document.querySelectorAll('.day:not(.xday)')),last=orig[orig.length-1];last.parentNode.insertBefore(sec,last);
          sec.querySelector('.rmday').addEventListener('click',function(){var xs=ld(ek).filter(function(e){return e.x!==sec.dataset.extra});sv(ek,xs);sec.remove();renum();toast('去掉了')})}
        function build(e){if(e.k==='free'){place(dayShell(e.x,'自由活动','<p class="lead">这天不排行程：睡到自然醒，在住的地方附近走走，补补觉，或者把前几天没逛够的地方再去一次。</p>'));return Promise.resolve()}
          return fetch('/trip/'+e.rid+'/').then(function(r){return r.text()}).then(function(h){var doc=new DOMParser().parseFromString(h,'text/html'),src=doc.getElementById('d'+(e.i+1));if(!src)return;
            var sec=dayShell(e.x,src.querySelector('h2').textContent,'');[].slice.call(src.children).forEach(function(c){if(c.tagName!=='HEADER'&&!c.classList.contains('stays')&&!c.classList.contains('tl'))sec.insertBefore(c.cloneNode(true),sec.querySelector('.rmday'))});
            var stc=(document.querySelector('.addday')||{dataset:{}}).dataset.city||'住处',stl=src.querySelector('.tl');
            function hm2(s){var m=/^(\d\d):(\d\d)$/.exec(s||'');return m?+m[1]*60+ +m[2]:null}function m2(v){v=Math.round(v);return('0'+Math.floor(v/60)%24).slice(-2)+':'+('0'+v%60).slice(-2)}
            function dur(v){return(v>=60?Math.floor(v/60)+' 小时':'')+(v%60?(v>=60?' ':'')+(v%60)+' 分钟':'')}
            if(stl){var all=[].slice.call(stl.querySelectorAll(':scope > .r')),tm=all.map(function(r){return hm2((r.querySelector('time')||{}).textContent)}),items=[];
              all.forEach(function(r,i){var txt=r.innerText;if(r.classList.contains('stay'))return;if(/住处|吃晚饭|歇一下|沿途慢慢走/.test(txt))return;if(r.classList.contains('eat')&&r.dataset.meal!=='l')return;
                var nx=null;for(var j=i+1;j<all.length;j++){if(tm[j]!=null){nx=tm[j];break}}var span=(tm[i]!=null&&nx!=null)?Math.max(10,nx-tm[i]):60;items.push({r:r,span:span})});
              while(items.length&&items[0].r.classList.contains('dep'))items.shift();while(items.length&&items[items.length-1].r.classList.contains('dep'))items.pop();
              var km=e.km||0,drive=Math.round(km*1.3/55*60/5)*5+10,t=9*60,tl=document.createElement('ol');tl.className='tl';
              function row(cls,time,main,sub,src2){var li=src2?src2.cloneNode(true):document.createElement('li');if(!src2){li.className='r '+cls;li.innerHTML='<time></time><span class="dot"></span><div class="rb"><p class="m"></p>'+(sub?'<p class="s"></p>':'')+'</div>';li.querySelector('.m').textContent=main;if(sub)li.querySelector('.s').textContent=sub}li.querySelector('time').textContent=time;tl.appendChild(li);return li}
              var first=items[0]?(((items[0].r.querySelector('.m')||{}).childNodes||[])[0]||{textContent:''}).textContent.trim():'';
              row('dep',m2(t),'从'+stc+'出发 → '+first,'开车约 '+dur(drive)+' · '+km+' 公里');t+=drive;var lunched=false;
              items.forEach(function(it){var r=it.r;if(r.classList.contains('eat')){t=Math.max(t,690);row('','',null,null,r).querySelector('time').textContent=m2(t);t+=60;lunched=true;return}
                if(!lunched&&t>=780&&!r.classList.contains('dep')){row('eat',m2(t),'午饭 · 附近简单吃','');t+=60;lunched=true}
                var li=row('','',null,null,r);li.querySelector('time').textContent=m2(t);t+=it.span});
              row('dep',m2(t),'回'+stc,'开车约 '+dur(drive)+' · '+km+' 公里');t+=drive;
              row('eat',m2(Math.max(t,18*60)),'晚饭 · 回到'+stc+'再吃','');
              row('stay','晚上','住 · '+stc,'接着住原来那家，第二天照原计划走');
              sec.insertBefore(tl,sec.querySelector('.rmday'));var ld0=sec.querySelector('.lead');var note='从'+stc+'过去单程约 '+km+' 公里，来回开车约 '+dur(drive*2)+(drive*2>=240?'，这天会比较累':'')+'。晚上回'+stc+'住。';if(ld0)ld0.textContent=note;else sec.insertBefore(Object.assign(document.createElement('p'),{className:'lead',textContent:note}),tl)}
            sec.querySelector('h2').insertAdjacentHTML('beforeend','<span class="xt">接「'+e.label+'」第 '+(e.i+1)+' 天</span>');place(sec)}).catch(function(){})}
        var chain=Promise.resolve();ld(ek).forEach(function(e){chain=chain.then(function(){return build(e)})});chain.then(renum);
        addB.addEventListener('click',function(){var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
          var groups={};cands.forEach(function(c){(groups[c.label]=groups[c.label]||[]).push(c)});
          var stc=document.querySelector('.addday').dataset.city||'这里';
          sh.innerHTML='<div class="pk-h"><b>加一天</b><button type="button" class="pk-x">关上</button></div><p class="xnote">加的一天放在最后一天（回程）前面</p><div class="xd"><button type="button" data-free="1"><b>在'+stc+'多留一天</b><small>自由活动，不排行程</small></button>'+
            (cands.length?'<p class="xg">附近 100 公里内可以接上的一天</p>'+cands.map(function(c){var had=ld(ek).some(function(x){return x.k==='r'&&x.rid===c.rid&&+x.i===+c.i});return'<button type="button"'+(had?' disabled class="had"':'')+' data-rid="'+c.rid+'" data-i="'+c.i+'" data-l="'+c.label+'" data-km="'+c.km+'" data-lat="'+(c.lat||'')+'" data-lng="'+(c.lng||'')+'"><b>'+c.title+(had?'<span class="hadt">已加</span>':'')+'</b><small>来自「'+c.label+'」第 '+(c.i+1)+' 天 · 离住处约 '+c.km+' 公里</small></button>'}).join(''):'<p class="xg">附近没有合适的线路可以接，可以先选多留一天</p>')+'</div>';
          function close(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
          sh.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b||b.disabled)return;if(b.classList.contains('pk-x'))return close();
            if(!b.dataset.free&&ld(ek).some(function(x){return x.k==='r'&&x.rid===b.dataset.rid&&+x.i===+b.dataset.i})){toast('这一天已经加过了');return}
            var e=b.dataset.free?{k:'free',x:'f'+Date.now()}:{k:'r',x:'r'+Date.now(),rid:b.dataset.rid,i:+b.dataset.i,label:b.dataset.l,km:+(b.dataset.km||0),lat:+(b.dataset.lat||0),lng:+(b.dataset.lng||0)};var xs=ld(ek);xs.push(e);sv(ek,xs);close();
            build(e).then(function(){renum();var s=document.querySelector('.day[data-extra="'+e.x+'"]');if(s)s.scrollIntoView();toast('加好了，日期和底栏都跟着变了')})});
          mask.addEventListener('click',close);document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')})}
}
    // 旅途中：出发日到了，就在底部提示“今天第几天、下一站”
    function todayBar(){var old=document.querySelector('.today');if(old)old.remove();
      var st0=(dk&&dk.value)||art.dataset.start;if(!st0)return;var d0=new Date(st0+'T00:00:00'),nw=new Date(),idx=Math.floor((new Date(nw.getFullYear(),nw.getMonth(),nw.getDate())-d0)/864e5),secs=document.querySelectorAll('.day');
      if(idx<0||idx>=secs.length)return;var sec=secs[idx],hm=('0'+nw.getHours()).slice(-2)+':'+('0'+nw.getMinutes()).slice(-2),nxt=null;
      sec.querySelectorAll('.tl .r:not(.dep)').forEach(function(r){var t=r.querySelector('time');if(!nxt&&t&&/^\d\d:\d\d$/.test(t.textContent)&&t.textContent>=hm)nxt=r});
      var bar=document.createElement('button');bar.type='button';bar.className='today';bar.setAttribute('data-role','today-bar');
      bar.innerHTML=nxt?('<b>今天第 '+(idx+1)+' 天</b><span>下一站 '+nxt.querySelector('time').textContent+' '+nxt.querySelector('.m').childNodes[0].textContent.trim()+'</span><i>去看</i>'):('<b>今天第 '+(idx+1)+' 天</b><span>'+(idx+1<secs.length?'今天的安排走完了，早点休息':'行程最后一天，一路顺风')+'</span><i>看今天</i>');
      bar.addEventListener('click',function(){if(typeof openDay==='function')return openDay(idx);var tgt=nxt||sec;tgt.scrollIntoView({block:'center'});tgt.classList.add('flash');setTimeout(function(){tgt.classList.remove('flash')},1600)});
      var dock=document.querySelector('.dock');dock.parentNode.insertBefore(bar,dock);
      var nv=document.querySelectorAll('.daynav a')[idx];if(nv)nv.classList.add('now')}
    todayBar();if(dk)dk.addEventListener('change',function(){setTimeout(todayBar,0)});
    // 今晚住：标记已订
    var bk=ld('zouni_booked');document.querySelectorAll('.stays .mk').forEach(function(b){function pt(){var on=bk.indexOf(b.dataset.k)>=0;b.classList.toggle('on',on);b.textContent=on?'已订 ✓':'标记已订'}pt();
      b.addEventListener('click',function(){var i=bk.indexOf(b.dataset.k);if(i>=0)bk.splice(i,1);else bk.push(b.dataset.k);sv('zouni_booked',bk);pt()})});

    // ——— 生成分享图：封面画 + 标题 + 天数价格出发日 + 前几天安排 + 网址，长按保存发朋友圈 ———
    function shotTrip(){var W_=1080,H_=1500,cv=document.createElement('canvas');cv.width=W_;cv.height=H_;var x=cv.getContext('2d');
      var BG='#f4f2ec',INK='#1c1d1a',RED='#a63d27',SERIF='"Noto Serif SC",serif',SANS='"Noto Sans SC",sans-serif';
      x.fillStyle=BG;x.fillRect(0,0,W_,H_);
      var im=document.querySelector('.hero img'),title=document.querySelector('.hero h1').innerText,kick=document.querySelector('.hero .kick').innerText;
      function finish(){var g=x.createLinearGradient(0,600,0,980);g.addColorStop(0,'rgba(20,18,16,0)');g.addColorStop(1,'rgba(20,18,16,.85)');x.fillStyle=g;x.fillRect(0,560,W_,420);
        x.fillStyle=BG;var fs=title.length>12?64:80;x.font='900 '+fs+'px '+SERIF;var lines=[],ln='';title.split('').forEach(function(ch){if(x.measureText(ln+ch).width>W_-128){lines.push(ln);ln=ch}else ln+=ch});lines.push(ln);
        var tl2=lines.slice(-2);tl2.forEach(function(l,i,a){x.fillText(l,64,940-(a.length-1-i)*(fs+10))});
        x.fillStyle='#f2c9bf';x.font='700 30px '+SANS;x.fillText(kick,64,940-(tl2.length-1)*(fs+10)-fs-18);
        x.fillStyle=INK;x.font='900 44px '+SERIF;var dk=document.querySelector('.dock b');x.fillText(dk?dk.innerText:'',64,1060);
        x.fillStyle='#5d5f59';x.font='30px '+SANS;var pr=document.querySelector('.glance .price');x.fillText('每人 '+(pr?pr.innerText:''),64,1110);
        var all=[].slice.call(document.querySelectorAll('.overview ol > li')),maxRows=Math.floor((H_-96-40-1180)/56)+1,ovs=all.length>maxRows?all.slice(0,maxRows-1):all;
        ovs.forEach(function(li,i){var y=1180+i*56;x.fillStyle=RED;x.font='900 34px '+SERIF;x.fillText(li.querySelector('b').innerText,64,y);x.fillStyle=INK;x.font='700 32px '+SANS;var t=li.querySelector('strong').innerText;if(t.length>14)t=t.slice(0,14)+'…';x.fillText(t,140,y)});
        if(all.length>ovs.length){x.fillStyle='#5d5f59';x.font='700 30px '+SANS;x.fillText('… 共 '+all.length+' 天',140,1180+ovs.length*56)}
        x.fillStyle=INK;x.fillRect(64,H_-96,W_-128,2);x.font='700 28px '+SANS;x.fillStyle=INK;x.fillText('走你 · '+location.host+location.pathname,64,H_-48);
        if(window.qrcode){try{var q=qrcode(0,'M');q.addData(myLink?myLink():location.href.split('#')[0]);q.make();var nM=q.getModuleCount(),sz=200,cs=sz/nM,qx=W_-64-sz,qy=H_-96-24-sz;   // 右下角二维码：扫了直接打开（带上你改过的）
          x.fillStyle='#fff';x.fillRect(qx-12,qy-12,sz+24,sz+24);x.fillStyle=INK;for(var rr=0;rr<nM;rr++)for(var cc=0;cc<nM;cc++)if(q.isDark(rr,cc))x.fillRect(qx+cc*cs,qy+rr*cs,Math.ceil(cs),Math.ceil(cs));
          x.font='400 22px '+SANS;x.fillStyle='#5d5f59';x.textAlign='right';x.fillText('扫一扫打开行程',W_-64,qy-24);x.textAlign='left'}catch(e){}}
        var url=cv.toDataURL('image/png'),m=document.createElement('div');m.className='hmap-zoom shotv';
        m.innerHTML='<button type="button" class="hz-x">关上</button><div class="hz-b"><img alt="分享图" src="'+url+'"></div><p class="shotp">手机上长按图片保存；电脑上 <a download="走你-'+me.label+'.png" href="'+url+'">点这里下载</a></p>';
        document.body.appendChild(m);document.body.classList.add('pk-open');function cl(){m.remove();document.body.classList.remove('pk-open')}m.querySelector('.hz-x').addEventListener('click',cl)}
      if(im){var I=new Image();I.onload=function(){var s=Math.max(W_/I.width,980/I.height),w=I.width*s,h=I.height*s;x.drawImage(I,(W_-w)/2,980-h,w,h);finish()};I.onerror=finish;I.src=im.getAttribute('src')}else{x.fillStyle='#2e3a3f';x.fillRect(0,0,W_,980);finish()}}

    // ——— 改某天几点出发：后面的时间跟着顺延或提前；午饭不早于 11:30、晚饭不早于 17:30；定点的站（看日落、开船）不提前；太晚了提示，可一键去掉最后一站 ———
    (function(){var me2=me&&me.id;if(!me2)return;var SK='zouni_st_'+me2,DK='zouni_drop_'+me2,AK='zouni_adj_'+me2,LK='zouni_slow_'+me2;
      function getA(){try{return JSON.parse(localStorage.getItem(AK)||'{}')}catch(e){return{}}}
      var FK='zouni_fill_'+me2,NB=[];try{NB=JSON.parse((document.getElementById('nearby')||{}).textContent||'[]')}catch(e){}
      function getF(){try{return JSON.parse(localStorage.getItem(FK)||'{}')}catch(e){return{}}}
      function kmz(a,b,c,d){var r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
      function hstr(m){return(m>=60?Math.floor(m/60)+' 小时':'')+(m%60?' '+(m%60)+' 分':'')}
      try{localStorage.removeItem(LK)}catch(e){}function slow(){return false}   // 放慢节奏已去掉：以前打开过的也清掉，免得悄悄生效
      function nm(r){return((r.querySelector('.m')||{}).childNodes||[{textContent:''}])[0].textContent.trim()}
      function hm2m(s){var m=/^(\d\d):(\d\d)$/.exec(s||'');return m?+m[1]*60+ +m[2]:null}
      function m2hm(v){v=Math.round(v);var h=Math.floor(v/60),m=v%60;if(h>=24)h-=24;return('0'+h).slice(-2)+':'+('0'+m).slice(-2)}
      function getS(){try{return JSON.parse(localStorage.getItem(SK)||'{}')}catch(e){return{}}}
      function getD(){try{return JSON.parse(localStorage.getItem(DK)||'{}')}catch(e){return{}}}
      var secs0=[].slice.call(document.querySelectorAll('.day'));secs0.forEach(function(s,i){if(!s.dataset.extra&&s.dataset.oi==null)s.dataset.oi=i});
      function rowsOf(sec){return[].slice.call(sec.querySelectorAll('.tl > .r'))}
      function replan(sec){var oi=sec.dataset.oi,S=getS(),D=getD(),tl=sec.querySelector('.tl'),rows=rowsOf(sec);
        rows.forEach(function(r,k){var tm=r.querySelector('time');if(tm&&!r.dataset.t0)r.dataset.t0=tm.textContent;if(r.dataset.k==null)r.dataset.k=k;
          if(r.dataset.slack==null)r.dataset.slack=((r.classList.contains('dep')&&/歇一下/.test(r.innerText))||/沿途慢慢走/.test((r.querySelector('.m')||{}).textContent||''))?'1':'0'});
        var orig=rows.slice().sort(function(a,b){return a.dataset.k-b.dataset.k});
        orig.forEach(function(r){r.hidden=!!(D[oi]&&D[oi].indexOf(+r.dataset.k)>=0)});
        var timed=orig.filter(function(r){return hm2m(r.dataset.t0)!=null}),t0=timed.map(function(r){return hm2m(r.dataset.t0)});if(!timed.length)return;
        var F=getF()[oi]||{};orig.forEach(function(r){var f=F[r.dataset.k],mm=r.querySelector('.m');if(!mm)return;if(f){if(!r.dataset.fo){r.dataset.fo=mm.childNodes[0].textContent;r.dataset.fs=r.dataset.slack}mm.childNodes[0].textContent=f.n+'（空档加的）';r.dataset.slack='0';r.classList.add('filled')}else if(r.dataset.fo){mm.childNodes[0].textContent=r.dataset.fo;r.dataset.slack=r.dataset.fs;delete r.dataset.fo;r.classList.remove('filled')}});
        var A=getA()[oi]||{},SL=slow(),start=hm2m(S[oi])!=null?hm2m(S[oi]):t0[0]+(SL?30:0),late=[],t,seq,slowDrop=null;
        orig.forEach(function(r){if(r.dataset.sd){delete r.dataset.sd;r.hidden=!!(D[oi]&&D[oi].indexOf(+r.dataset.k)>=0)}});
        if(SL){var sights=orig.filter(function(r){return(r.classList.contains('see')||r.classList.contains('fun'))&&r.dataset.slack!=='1'&&!r.hidden});
          if(sights.length>=3){slowDrop=sights[sights.length-1];slowDrop.hidden=true;slowDrop.dataset.sd='1';var pv=slowDrop.previousElementSibling;if(pv&&pv.classList.contains('dep')&&!pv.hidden){pv.hidden=true;pv.dataset.sd='1'}}}
        // 按差值平移：每一行 = 原来的时间 + 累计的变化；什么都没改时每一行原样不动
        //  改出发时间 → 整体平移；晚了先吃掉“回去歇一下 / 沿途慢慢走”这些空当；去掉的站把后面往前拉；多待少待把后面往后推 / 往前拉
        //  饭点、定点只在“原来就满足、平移后不满足”时才顶住，不会把原来的安排改掉
        var LSPAN=60,moveL=null,shift=0;
        function spanOf(r){var k=timed.indexOf(r);return k<timed.length-1?Math.max(0,t0[k+1]-t0[k]):60}
        function run(order){shift=start-t0[0];late=[];var lastT=null,lastSpan=0;
          if(moveL){moveL.querySelector('time').textContent=m2hm(start);moveL._t=start;shift+=LSPAN;lastT=start;lastSpan=LSPAN}
          order.forEach(function(r){var k=timed.indexOf(r),tO=t0[k],span=spanOf(r),at=hm2m(r.dataset.at),ml=r.dataset.meal;
            if(r===moveL){shift-=span;return}
            var sl=r.querySelector('.s');if(sl&&(r.classList.contains('see')||r.classList.contains('fun'))){var tn=[].slice.call(sl.childNodes).filter(function(x){return x.nodeType===3&&/\d+ (小时|分)/.test(x.textContent)})[0];
              if(tn){if(r.dataset.d0==null)r.dataset.d0=tn.textContent;var mh=/(\d+) 小时/.exec(r.dataset.d0),mm2=/(\d+) 分/.exec(r.dataset.d0),od=(mh?+mh[1]*60:0)+(mm2?+mm2[1]:0),nd=Math.max(15,od+(A[r.dataset.k]||0));
                tn.textContent=A[r.dataset.k]?r.dataset.d0.replace(/\d+ 小时(\s*\d+ 分钟?)?|\d+ 分钟?/,(nd>=60?Math.floor(nd/60)+' 小时':'')+(nd%60?(nd>=60?' ':'')+(nd%60)+' 分':'')):r.dataset.d0}}
            if(r.hidden&&r.dataset.slack!=='1'){shift-=span;return}                                   // 去掉的站：后面往前挪
            var t1=tO+shift;
            if(r.dataset.slack==='1'){var cut=shift>0?Math.min(span,shift):0;shift-=cut;var left=span-cut;r.hidden=left<15||!!(D[oi]&&D[oi].indexOf(+r.dataset.k)>=0);if(r.hidden){shift-=left;return}   // 空当从前一站结束时开始，只是变短
              r.querySelector('time').textContent=m2hm(t1);r._t=t1;lastT=t1;lastSpan=left;return}
            if(ml==='l'&&tO>=690&&t1<690){shift+=690-t1;t1=690}
            if(ml==='d'&&tO>=1050&&t1<1050){shift+=1050-t1;t1=1050}
            if(at!=null&&tO>=at&&t1<at){shift+=at-t1;t1=at}
            if(at!=null&&tO<=at+30&&t1>at+30)late.push(r);   // 原来赶得上、现在赶不上才提示
            r.querySelector('time').textContent=m2hm(t1);r._t=t1;lastT=t1;lastSpan=Math.max(15,span+(A[r.dataset.k]||0));
            if(A[r.dataset.k])shift+=Math.max(15-span,A[r.dataset.k])});
          t=lastT==null?start:lastT+lastSpan}
        seq=timed.slice();var lunch=seq.filter(function(r){return r.dataset.meal==='l'&&!r.hidden})[0];
        if(lunch&&hm2m(S[oi])!=null&&start>t0[0]&&start>=660&&seq.indexOf(lunch)>0&&t0[timed.indexOf(lunch)]+(start-t0[0])>840&&t0[timed.indexOf(lunch)]<=840){moveL=lunch}   // 只在自己改晚了出发、把原本两点前的午饭推过两点时   // 出发晚、午饭要拖过两点：先吃午饭再出发
        run(seq);if(moveL){seq.splice(seq.indexOf(moveL),1);seq.unshift(moveL)}
        var t0end=t0[t0.length-1]+60;
        var rest=orig.filter(function(r){return seq.indexOf(r)<0});seq.concat(rest).forEach(function(r){tl.appendChild(r)});
        var vis=seq.filter(function(r){return!r.hidden});
        var st=sec.querySelector('.st b');if(st)st.textContent=m2hm(start);
        var ov=document.querySelectorAll('.overview ol li')[[].slice.call(document.querySelectorAll('.day')).indexOf(sec)];if(ov){var em=ov.querySelector('em');if(em)em.textContent=m2hm(start)+' 走'}
        var warn=sec.querySelector('.latewarn');if(warn)warn.remove();
        var msgs=[];if(t>22*60+30&&t>t0end+5)msgs.push('按 '+m2hm(start)+' 出发，这天要到 '+m2hm(t)+' 才结束');
        late.forEach(function(r){msgs.push('赶不上「'+r.querySelector('.m').childNodes[0].textContent.trim()+'」原定的 '+r.dataset.at)});
        var changed=(hm2m(S[oi])!=null&&hm2m(S[oi])!==t0[0])||Object.keys(A).length>0||Object.keys(F).length>0;
        var road=0,nsee=0,gapRow=null,gapLen=0;vis.forEach(function(r,i){var nx=vis[i+1],a=r._t,b=nx?nx._t:t;if(r.classList.contains('dep')&&r.dataset.slack!=='1')road+=Math.max(0,b-a);if((r.classList.contains('see')||r.classList.contains('fun'))&&r.dataset.slack!=='1')nsee++;if(r.dataset.slack==='1'&&b-a>gapLen){gapLen=b-a;gapRow=r}});
        var summary='改完：这天 '+m2hm(t)+' 结束，去 '+nsee+' 个地方，路上约 '+hstr(road||0);
        var sun=sec.querySelector('.sun'),used=[];Object.keys(getF()).forEach(function(d){Object.keys(getF()[d]).forEach(function(k){used.push(getF()[d][k].n)})});
        var fillHint=null;if(gapRow&&gapLen>=150&&NB.length){var sps=[],allD=[].slice.call(document.querySelectorAll('.day')),di=allD.indexOf(sec);[di,di-1].forEach(function(q){var s2=allD[q]&&allD[q].querySelector('.sun[data-k="rise"]');if(s2)sps.push([+s2.dataset.lat,+s2.dataset.lng])});   // 只看这天和前一天住的地方附近
          var tlTxt=[].slice.call(document.querySelectorAll('.tl')).map(function(t){return t.textContent}).join(' ');fillHint=NB.filter(function(x){return used.indexOf(x.n)<0&&x.dur<=gapLen-30&&tlTxt.indexOf(x.n)<0}).map(function(x){return{x:x,d:Math.min.apply(null,sps.map(function(p){return kmz(p[0],p[1],x.lat,x.lng)}))}}).filter(function(z){return z.d<=30}).sort(function(a,b){return a.d-b.d})[0]||null}   // 按离住的地方最近来挑
        
        if(msgs.length||changed||(D[oi]&&D[oi].length)){var lastSee=vis.filter(function(r){return r.classList.contains('see')||r.classList.contains('fun')}).pop();
          var box=document.createElement('div');box.className='latewarn';
          box.className='latewarn'+(msgs.length?' bad':'');
          box.innerHTML=(msgs.length?'<p>'+msgs.join('；')+(lastSee?' <button type="button" class="drop">去掉「'+lastSee.querySelector('.m').childNodes[0].textContent.trim()+'」</button>':'')+'</p>':'')+'<p class="sum">'+summary.replace('改完：','')+' · <button type="button" class="reset">恢复</button></p>'+(fillHint?'<p class="gap">空出 '+hstr(gapLen).trim()+'，可以加「'+fillHint.x.n+'」 <button type="button" class="fill">加上</button></p>':'');
          var tl=sec.querySelector('.tl');tl.parentNode.insertBefore(box,tl);
          var fb=box.querySelector('.fill');if(fb)fb.addEventListener('click',function(){var F2=getF();F2[oi]=F2[oi]||{};F2[oi][gapRow.dataset.k]={n:fillHint.x.n,c:fillHint.x.c};try{localStorage.setItem(FK,JSON.stringify(F2))}catch(e){}replan(sec);toast('加上了「'+fillHint.x.n+'」')});
          var dr=box.querySelector('.drop');if(dr)dr.addEventListener('click',function(){var D2=getD(),k=+lastSee.dataset.k,prevR=lastSee.previousElementSibling;D2[oi]=(D2[oi]||[]).concat([k]);if(prevR&&prevR.classList.contains('dep')&&!prevR.hidden)D2[oi].push(+prevR.dataset.k);try{localStorage.setItem(DK,JSON.stringify(D2))}catch(e){}replan(sec);toast('去掉了，后面的时间往前挪了')});
          box.querySelector('.reset').addEventListener('click',function(){var S2=getS(),D2=getD(),A2=getA(),F3=getF();delete S2[oi];delete D2[oi];delete A2[oi];delete F3[oi];try{localStorage.setItem(SK,JSON.stringify(S2));localStorage.setItem(DK,JSON.stringify(D2));localStorage.setItem(AK,JSON.stringify(A2));localStorage.setItem(FK,JSON.stringify(F3))}catch(e){}replan(sec);toast('恢复了原来的安排')})}}
      // ① 每一站可以调：多待、少待、去掉，后面的时间按同样规则重排
      function addAdj(sec){[].slice.call(sec.querySelectorAll('.tl > .r.see, .tl > .r.fun')).forEach(function(r){if(r.querySelector('.adj')||/沿途慢慢走/.test(nm(r)))return;var rb=r.querySelector('.rb');if(!rb)return;var s=rb.querySelector('.s');if(!s){s=document.createElement('p');s.className='s';rb.appendChild(s)}
          s.insertAdjacentHTML('beforeend','<button type="button" class="adj" aria-label="调整这一站">调整</button>')})}
      document.addEventListener('click',function(e){var b=e.target.closest('.adj');if(!b)return;e.preventDefault();var r=b.closest('.r'),sec=r.closest('.day'),oi=sec.dataset.oi;if(oi==null)return;var k=r.dataset.k,A2=getA(),cur=(A2[oi]||{})[k]||0;
        var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
        sh.innerHTML='<div class="pk-h"><b>'+nm(r)+'</b><button type="button" class="pk-x">关上</button></div><p class="xnote">'+(cur?'现在比原来'+(cur>0?'多':'少')+'待 '+Math.abs(cur)+' 分钟。':'')+'改了以后，这天后面的时间会跟着重排</p><div class="xd"><button type="button" data-d="30"><b>多待 30 分钟</b></button><button type="button" data-d="-30"><b>少待 30 分钟</b></button><button type="button" data-x="1"><b>去掉这一站</b><small>后面的时间往前挪</small></button>'+(cur?'<button type="button" data-r="1"><b>恢复这一站原来的时长</b></button>':'')+'</div>';
        function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
        sh.addEventListener('click',function(ev){var x=ev.target.closest('button');if(!x)return;if(x.classList.contains('pk-x'))return cl();var A3=getA();A3[oi]=A3[oi]||{};
          if(x.dataset.d){A3[oi][k]=(A3[oi][k]||0)+(+x.dataset.d);if(!A3[oi][k])delete A3[oi][k];try{localStorage.setItem(AK,JSON.stringify(A3))}catch(e){}cl();replan(sec);toast((+x.dataset.d>0?'多待':'少待')+' 30 分钟，后面的时间重排了');return}
          if(x.dataset.r){delete A3[oi][k];try{localStorage.setItem(AK,JSON.stringify(A3))}catch(e){}cl();replan(sec);toast('恢复了');return}
          if(x.dataset.x){var D3=getD();D3[oi]=(D3[oi]||[]).concat([+k]);var pv=r.previousElementSibling;if(pv&&pv.classList.contains('dep')&&!pv.hidden)D3[oi].push(+pv.dataset.k);try{localStorage.setItem(DK,JSON.stringify(D3))}catch(e){}cl();replan(sec);toast('去掉了「'+nm(r)+'」，后面的时间往前挪了')}});
        mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')});
      // ⑦ 带老人孩子：放慢节奏（每天晚半小时出发、少去最后一站）
      var ov0=document.querySelector('.overview');if(false&&ov0&&!document.querySelector('.slowbar')){ov0.insertAdjacentHTML('beforebegin','<div class="slowbar"><button type="button" class="slow" aria-pressed="false"><span class="sw"></span><b>带老人孩子，放慢节奏</b></button><small>每天晚半小时出发、少去一站</small></div>');
        var sb=document.querySelector('.slowbar .slow');function paint(){var on=slow();sb.classList.toggle('on',on);sb.setAttribute('aria-pressed',on?'true':'false')}paint();
        var morning=[].slice.call(document.querySelectorAll('.day')).filter(function(s){var r=rowsOf(s).filter(function(x){return hm2m(x.dataset.t0||(x.querySelector('time')||{}).textContent)!=null})[0];return s.dataset.oi!=null&&r&&hm2m(r.dataset.t0||r.querySelector('time').textContent)<=630});
        if(morning.length){document.querySelector('.slowbar').insertAdjacentHTML('beforeend','<div class="allst"><span>整趟每天</span><button type="button" class="allbtn"><b>—</b> 出发 <i>改</i></button><small>到达那天下午出发的不动</small></div>');
          var ab=document.querySelector('.allbtn');function paintAll(){var S3=getS(),vs=morning.map(function(s){return S3[s.dataset.oi]||null}),same=vs.every(function(v){return v===vs[0]});ab.querySelector('b').textContent=same&&vs[0]?vs[0]:(vs.some(function(v){return v})?'各天不同':'按原来')}paintAll();
          ab.addEventListener('click',function(){var opts=[];for(var m=390;m<=720;m+=30)opts.push(m2hm(m));var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
            sh.innerHTML='<div class="pk-h"><b>整趟每天几点出发</b><button type="button" class="pk-x">关上</button></div><p class="xnote">一次改 '+morning.length+' 天，每天后面的时间都会重排；到达那天下午出发的不动</p><div class="stg">'+opts.map(function(o){return'<button type="button" data-v="'+o+'">'+o+'</button>'}).join('')+'</div><div class="xd" style="margin-top:8px"><button type="button" data-v="orig"><b>恢复各天原来的出发时间</b></button></div>';
            function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
            sh.addEventListener('click',function(ev){var x=ev.target.closest('button');if(!x)return;if(x.classList.contains('pk-x'))return cl();if(!x.dataset.v)return;var S4=getS();morning.forEach(function(s){if(x.dataset.v==='orig')delete S4[s.dataset.oi];else S4[s.dataset.oi]=x.dataset.v});try{localStorage.setItem(SK,JSON.stringify(S4))}catch(e){}
              cl();morning.forEach(function(s){replan(s)});paintAll();toast(x.dataset.v==='orig'?'恢复了各天原来的出发时间':'整趟改成每天 '+x.dataset.v+' 出发，时间都重排了')});
            mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')})}
        sb.addEventListener('click',function(){try{if(slow())localStorage.removeItem(LK);else localStorage.setItem(LK,'1')}catch(e){}paint();[].slice.call(document.querySelectorAll('.day')).forEach(function(s){if(s.dataset.oi!=null)replan(s)});toast(slow()?'放慢了：每天晚半小时出发、少去一站':'恢复了正常节奏')})}
      [].slice.call(document.querySelectorAll('.day')).forEach(function(sec){if(sec.dataset.oi!=null){addAdj(sec);replan(sec)}});
      window.ZR={shift:function(sec,mins){var oi=sec.dataset.oi;if(oi==null)return;var S2=getS(),f=rowsOf(sec).filter(function(r){return hm2m(r.dataset.t0||(r.querySelector('time')||{}).textContent)!=null})[0];if(!f)return;var cur=hm2m(S2[oi])!=null?hm2m(S2[oi]):hm2m(f.dataset.t0||f.querySelector('time').textContent);S2[oi]=m2hm(cur+mins);try{localStorage.setItem(SK,JSON.stringify(S2))}catch(e){}replan(sec)}};
      document.addEventListener('click',function(e){var b=e.target.closest('.st');if(!b)return;var sec=b.closest('.day');if(!sec)return;var cur=b.querySelector('b').textContent;
        var opts=[];for(var m=390;m<=720;m+=30)opts.push(m2hm(m));
        var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
        sh.innerHTML='<div class="pk-h"><b>'+sec.querySelector('header small').textContent.split(' · ')[0]+'几点出发</b><button type="button" class="pk-x">关上</button></div><label class="allck"><input type="checkbox" class="allin"> 每天都按这个时间出发</label><div class="stg">'+opts.map(function(o){return'<button type="button" data-v="'+o+'" class="'+(o===cur?'on':'')+'">'+o+'</button>'}).join('')+'</div>';
        function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
        sh.addEventListener('click',function(ev){var x=ev.target.closest('button');if(!x)return;if(x.classList.contains('pk-x'))return cl();if(x.dataset.v){var S2=getS(),all=sh.querySelector('.allin')&&sh.querySelector('.allin').checked,tg=all?[].slice.call(document.querySelectorAll('.day')).filter(function(s){var f=rowsOf(s).filter(function(z){return hm2m(z.dataset.t0||(z.querySelector('time')||{}).textContent)!=null})[0];return s.dataset.oi!=null&&f&&hm2m(f.dataset.t0||f.querySelector('time').textContent)<=630}):[sec];if(tg.indexOf(sec)<0)tg.push(sec);
          tg.forEach(function(s){S2[s.dataset.oi]=x.dataset.v});try{localStorage.setItem(SK,JSON.stringify(S2))}catch(e){}cl();tg.forEach(function(s){replan(s)});toast(all?'每天都改成 '+x.dataset.v+' 出发':'这天改成 '+x.dataset.v+' 出发')}});
        mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')});
      document.addEventListener('keydown',function(e){var b=e.target.closest&&e.target.closest('.st');if(b&&(e.key==='Enter'||e.key===' ')){e.preventDefault();b.click()}});
    })();

    // ④ 出发前 16 天以内：每天显示天气预报（Open-Meteo，免费、不用登录），之外照旧写往年平均
    (function(){var WMO={0:'晴',1:'晴',2:'多云',3:'阴',45:'有雾',48:'有雾',51:'毛毛雨',53:'毛毛雨',55:'毛毛雨',56:'冻毛毛雨',57:'冻毛毛雨',61:'小雨',63:'中雨',65:'大雨',66:'冻雨',67:'冻雨',71:'小雪',73:'中雪',75:'大雪',77:'雪粒',80:'阵雨',81:'阵雨',82:'强阵雨',85:'阵雪',86:'阵雪',95:'雷阵雨',96:'雷阵雨',99:'雷阵雨'};
      function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
      function run(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start;if(!s0)return;var d0=new Date(s0+'T12:00:00'),now=new Date();now.setHours(12,0,0,0);
        [].slice.call(document.querySelectorAll('.day')).forEach(function(sec,i){var old=sec.querySelector('.fc');if(old)old.remove();var sun=sec.querySelector('.sun'),cl=sec.querySelector('[data-clim]');if(!sun||!cl)return;
          var d=new Date(d0.getTime()+i*864e5),gap=Math.round((d-now)/864e5);if(gap<0||gap>15)return;var ds=iso(d),lat=(+sun.dataset.lat).toFixed(2),lng=(+sun.dataset.lng).toFixed(2),ck='wx_'+lat+'_'+lng+'_'+ds;
          function show(w){if(!w)return;var rainy=(w.p!=null&&w.p>=60)||[61,63,65,66,67,80,81,82,95,96,99,71,73,75,85,86].indexOf(w.c)>=0;var p=document.createElement('p');p.className='fc';p.innerHTML='<b>天气预报</b>'+(WMO[w.c]||'')+' · '+Math.round(w.lo)+'–'+Math.round(w.hi)+'°C'+(w.p!=null?' · 降雨 '+w.p+'%':'')+(w.p>=60?'<em>带伞</em>':'')+(w.lo<=0?'<em>注意保暖</em>':'');cl.parentNode.insertBefore(p,cl.nextSibling);if(rainy)rainTip(sec,p)}
          var c=null;try{c=JSON.parse(sessionStorage.getItem(ck)||'null')}catch(e){}if(c)return show(c);
          fetch('https://api.open-meteo.com/v1/forecast?latitude='+lat+'&longitude='+lng+'&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&start_date='+ds+'&end_date='+ds).then(function(r){return r.json()}).then(function(j){var dd=j.daily;if(!dd||!dd.time||!dd.time.length)return;var w={c:dd.weathercode[0],hi:dd.temperature_2m_max[0],lo:dd.temperature_2m_min[0],p:dd.precipitation_probability_max?dd.precipitation_probability_max[0]:null};
            try{sessionStorage.setItem(ck,JSON.stringify(w))}catch(e){}show(w)}).catch(function(){})})}
      // 下雨的话：把这天一处室外景点换成附近的室内去处（博物馆这类），可以换回去
      var IND=[];try{IND=JSON.parse((document.getElementById('indoor')||{}).textContent||'[]')}catch(e){}var RK='zouni_rain_'+me.id;
      function getR(){try{return JSON.parse(localStorage.getItem(RK)||'{}')}catch(e){return{}}}
      function km2(a,b,c,d){var r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
      function outdoor(sec){return[].slice.call(sec.querySelectorAll('.tl > .r.see, .tl > .r.fun')).filter(function(r){return!r.hidden&&!r.dataset.in&&!r.dataset.rain&&!/沿途慢慢走/.test(r.innerText)})[0]}
      function applyRain(sec){var oi=sec.dataset.oi;if(oi==null)return;var R=getR()[oi];[].slice.call(sec.querySelectorAll('.r[data-rain]')).forEach(function(r){var m=r.querySelector('.m').childNodes[0];m.textContent=r.dataset.on;delete r.dataset.rain;var a=r.querySelector('a.ic.map');if(a&&r.dataset.oh){a.href=r.dataset.oh}});
        if(!R)return;var r=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(x){return x.dataset.k==R.k})[0];if(!r)return;var m=r.querySelector('.m').childNodes[0];r.dataset.on=m.textContent;m.textContent=R.n+'（下雨换的）';r.dataset.rain='1';
        var a=r.querySelector('a.ic.map');if(a){r.dataset.oh=a.href;a.href='https://uri.amap.com/search?keyword='+encodeURIComponent(R.n)+'&city='+encodeURIComponent(R.c||'')+'&callnative=1';a.removeAttribute('data-ios');a.removeAttribute('data-and')}}
      function rainTip(sec,p){var oi=sec.dataset.oi;if(oi==null||!IND.length)return;var R=getR()[oi];var sun=sec.querySelector('.sun');var la=+sun.dataset.lat,lo=+sun.dataset.lng;
        if(R){p.insertAdjacentHTML('beforeend','<span class="rn">已换成「'+R.n+'」<button type="button" class="rainback">换回原来的</button></span>');p.querySelector('.rainback').addEventListener('click',function(){var R2=getR();delete R2[oi];try{localStorage.setItem(RK,JSON.stringify(R2))}catch(e){}applyRain(sec);run();toast('换回原来的了')});return}
        var o=outdoor(sec);if(!o)return;var used=Object.keys(getR()).map(function(k){return getR()[k].n});var best=IND.filter(function(x){return used.indexOf(x.n)<0}).map(function(x){return{x:x,d:km2(la,lo,x.lat,x.lng)}}).filter(function(z){return z.d<=25}).sort(function(a,b){return a.d-b.d})[0];if(!best)return;   // 只推荐 25 公里以内的，太远就不折腾
        p.insertAdjacentHTML('beforeend','<span class="rn">下雨的话，「'+o.querySelector('.m').childNodes[0].textContent.trim()+'」可以换成「'+best.x.n+'」（'+(best.d<1?'就在旁边':'约 '+best.d+' 公里')+'）<button type="button" class="rainswap">换上</button></span>');
        p.querySelector('.rainswap').addEventListener('click',function(){var R2=getR();R2[oi]={k:o.dataset.k,n:best.x.n,c:best.x.c};try{localStorage.setItem(RK,JSON.stringify(R2))}catch(e){}applyRain(sec);run();toast('换成了「'+best.x.n+'」')})}
      // 周一：博物馆多数闭馆，提醒一下
      function monday(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start;if(!s0)return;var d0=new Date(s0+'T12:00:00');
        [].slice.call(document.querySelectorAll('.day')).forEach(function(sec,i){var old=sec.querySelector('.mon');if(old)old.remove();var d=new Date(d0.getTime()+i*864e5);if(d.getDay()!==1)return;
          var ms=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return!r.hidden&&(r.dataset.in||/周一闭馆/.test(r.innerText))}).map(function(r){return r.querySelector('.m').childNodes[0].textContent.trim()});if(!ms.length)return;
          var cl=sec.querySelector('[data-clim]');if(!cl)return;var p=document.createElement('p');p.className='fc mon';p.innerHTML='<b>这天是周一</b>「'+ms.slice(0,2).join('」「')+'」这类博物馆多数周一闭馆，出发前查一下，或者和别的天对调';cl.parentNode.insertBefore(p,cl.nextSibling)})}
      [].slice.call(document.querySelectorAll('.day')).forEach(applyRain);
      run();monday();var inp=document.querySelector('.dpk');if(inp)inp.addEventListener('change',function(){setTimeout(function(){run();monday()},50)})})();

    // ——— 怎么去、怎么回：换成你自己的出发地 ———
    var goEl=document.querySelector('section.go'),GO=null;try{GO=goEl?JSON.parse(goEl.dataset.go):null}catch(e){}
    function goNow(){if(!GO)return null;var o=zOrigin()||{n:GO.o,lat:null},km=o.lat!=null?zKm(o.lat,o.lng,GO.lat,GO.lng):GO.km;var mode=(+GO.drv)?'drive':(km<60?'near':(+GO.ab||km>1200)?'fly':'train');return{o:o.n,km:km,mode:mode,way:zGoWay(GO,o.n,km)}}
    if(goEl&&GO&&zOrigin()){var gn=goNow(),sp=goEl.querySelector('.gw span');   // 只有知道你的出发地才改写，不然保留页面上按大城市写的if(sp)sp.textContent=sp.textContent.replace(/^[^。]*。/,gn.way+'。');
      [].slice.call(document.querySelectorAll('.faq dt')).forEach(function(dt){if(/怎么去/.test(dt.textContent)&&dt.nextElementSibling)dt.nextElementSibling.textContent=gn.way+'。'})}
    function fmtD(d){return(d.getMonth()+1)+'/'+d.getDate()}
    function tripDates(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start,d0=new Date(s0+'T12:00:00'),n=document.querySelectorAll('.day').length;return{d0:d0,dN:new Date(d0.getTime()+(n-1)*864e5),n:n}}
    // ——— 往返车票：放进“要办的事”（高铁提前 15 天开售） ———
    window.zGoItems=function(T,TK){var gn=goNow();if(!gn||gn.mode==='near'||gn.mode==='drive')return[];var td=tripDates(),city=GO.city||'',tr=gn.mode==='train';
      var sale=new Date(td.d0.getTime()-15*864e5),link=tr?'https://www.12306.cn/index/':'https://m.ctrip.com/html5/flight/swift/index';
      function it(key,t,how){return{g:'往返车票',t:t,how:how,link:link,done:T.indexOf(key)>=0,tog:function(){var T2=[];try{T2=JSON.parse(localStorage.getItem(TK)||'[]')}catch(e){}var i=T2.indexOf(key);if(i>=0)T2.splice(i,1);else T2.push(key);try{localStorage.setItem(TK,JSON.stringify(T2))}catch(e){}}}}
      return[it('go:去','买去程'+(tr?'高铁票':'机票')+'：'+gn.o+' → '+city+'，'+fmtD(td.d0)+' 上午',tr?'高铁提前 15 天开售，'+fmtD(sale)+' 起能买':'机票越早越便宜'),
             it('go:回','买回程'+(tr?'高铁票':'机票')+'：'+city+' → '+gn.o+'，'+fmtD(td.dN)+' 傍晚',tr?'回程也是提前 15 天开售':'')]};
    // ——— 加到手机日历：每天的安排，加上买票、预约、订住宿的提醒 ———
    window.zIcs=function(){function p2(x){return('0'+x).slice(-2)}function ymd(d){return d.getFullYear()+p2(d.getMonth()+1)+p2(d.getDate())}function esc(s){return String(s).replace(/[\\,;]/g,function(c){return'\\'+c}).replace(/\n/g,'\\n')}
      var td=tripDates(),L=['BEGIN:VCALENDAR','VERSION:2.0','PRODID:-//zouni.app//CN','CALSCALE:GREGORIAN'],uid=0;
      function ev(d,hm,title,desc,alarm){uid++;var s=hm?ymd(d)+'T'+hm.replace(':','')+'00':ymd(d);L.push('BEGIN:VEVENT','UID:'+me.id+'-'+uid+'@zouni.app','DTSTAMP:'+ymd(new Date())+'T000000Z',(hm?'DTSTART:':'DTSTART;VALUE=DATE:')+s,'SUMMARY:'+esc(title));if(desc)L.push('DESCRIPTION:'+esc(desc));if(alarm)L.push('BEGIN:VALARM','ACTION:DISPLAY','DESCRIPTION:'+esc(title),'TRIGGER:-PT0M','END:VALARM');L.push('END:VEVENT')}
      [].slice.call(document.querySelectorAll('.day')).forEach(function(sec,i){var d=new Date(td.d0.getTime()+i*864e5),rows=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return!r.hidden}).map(function(r){return r.querySelector('time').textContent+' '+((r.querySelector('.m').childNodes[0]||{}).textContent||'').trim()});
        ev(d,null,'第 '+(i+1)+' 天 · '+sec.querySelector('h2').childNodes[0].textContent.trim(),rows.join('\n')+'\n'+location.origin+location.pathname,false)});
      var gn=goNow();if(gn&&gn.mode==='train'){var sd=new Date(td.d0.getTime()-15*864e5);if(sd>new Date())ev(sd,'08:00','高铁票开售：'+gn.o+' → '+(GO.city||''),'去 12306 买去程票',true)}
      else if(gn&&gn.mode==='fly'){var fd=new Date(td.d0.getTime()-30*864e5);if(fd>new Date())ev(fd,'20:00','看机票：'+gn.o+' → '+(GO.city||''),'越早越便宜',true)}
      var seen={};[].slice.call(document.querySelectorAll('.tl > .r')).forEach(function(r){if(r.hidden||!r.querySelector('.bkn'))return;var nm=((r.querySelector('.m').childNodes[0]||{}).textContent||'').trim().split(' · ')[0];if(seen[nm])return;seen[nm]=1;var i=[].slice.call(document.querySelectorAll('.day')).indexOf(r.closest('.day')),d=new Date(td.d0.getTime()+(i-7)*864e5);if(d>new Date())ev(d,'20:00','预约 '+nm,'提前 7 天看看能不能约了',true)});
      var hd=new Date(td.d0.getTime()-14*864e5);if(hd>new Date()&&document.querySelector('.stays'))ev(hd,'20:00','订住宿：'+me.label,'旺季早点订',true);
      L.push('END:VCALENDAR');var ics=L.join('\r\n'),a=document.createElement('a');a.href='data:text/calendar;charset=utf-8,'+encodeURIComponent(ics);a.download='走你-'+me.label+'.ics';document.body.appendChild(a);a.click();a.remove();ztrack('加到日历');return ics};
    // ——— ① 「今天」：路上用，只看一天、字大，下一站一键导航，今晚住哪、今天要预约的都在这 ———
    function nm0(r){return(((r.querySelector('.m')||{}).childNodes||[])[0]||{textContent:''}).textContent.trim()}
    function todayIdx(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start;if(!s0)return-1;var d0=new Date(s0+'T00:00:00'),n=new Date();return Math.floor((new Date(n.getFullYear(),n.getMonth(),n.getDate())-d0)/864e5)}
    function openDay(idx){var secs=[].slice.call(document.querySelectorAll('.day'));if(!secs.length)return;var ti=todayIdx();if(idx==null)idx=(ti>=0&&ti<secs.length)?ti:0;
      var m=document.createElement('div');m.className='tv';m.setAttribute('role','dialog');document.body.appendChild(m);document.body.classList.add('pk-open');
      function close(){m.remove();document.body.classList.remove('pk-open')}
      function render(i){var sec=secs[i],head=sec.querySelector('header small').textContent,title=nm0(sec.querySelector('header'))||sec.querySelector('h2').childNodes[0].textContent.trim();
        var rows=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return!r.hidden}),now=new Date(),hm=('0'+now.getHours()).slice(-2)+':'+('0'+now.getMinutes()).slice(-2),isT=(i===ti);
        var nx=isT?rows.filter(function(r){var t=r.querySelector('time').textContent;return/^\d\d:\d\d$/.test(t)&&t>=hm}).filter(function(r){return!r.classList.contains('dep')})[0]:null;
        function esc(s){return String(s).replace(/</g,'&lt;')}
        function navOf(r){var a=r.querySelector('a.ic.map');return a?'<a class="tvnav" href="'+a.href+'"'+(a.dataset.ios?' data-ios="'+esc(a.dataset.ios)+'" data-and="'+esc(a.dataset.and)+'"':'')+' target="_blank" rel="nofollow noopener">导航</a>':''}
        var h='<div class="tvh"><button type="button" class="tvx"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>回到整条行程</button></div><div class="tvtabs">'+secs.map(function(s,k){return'<button type="button" data-i="'+k+'" class="'+(k===i?'on':'')+'">'+(k===ti?'今天':(k+1))+'</button>'}).join('')+'</div>';
        h+='<div class="tvb"><p class="tvd">'+esc(head)+'</p><h2>'+esc(sec.querySelector('h2').childNodes[0].textContent.trim())+'</h2>';
        var fc=sec.querySelector('.fc:not(.mon)'),mon=sec.querySelector('.fc.mon');if(fc)h+='<p class="tvw">'+esc(fc.innerText.replace(/\n/g,' ').replace(/换上|换回原来的/g,'').replace(/^天气预报\s*/,'天气预报 '))+'</p>';if(mon)h+='<p class="tvw red">'+esc(mon.innerText.replace(/\n/g,' '))+'</p>';
        if(nx){var dep=nx.previousElementSibling&&nx.previousElementSibling.classList.contains('dep')?nx.previousElementSibling:null,lt=nx.querySelector('time').textContent,dl=(+lt.slice(0,2)*60+ +lt.slice(3))-(now.getHours()*60+now.getMinutes());
          var pl=dep?dep.querySelector('time').textContent:lt,late=(now.getHours()*60+now.getMinutes())-(+pl.slice(0,2)*60+ +pl.slice(3));
          h+='<div class="tvnext"><small>下一站'+(dl>0?' · '+(dl>=60?Math.floor(dl/60)+' 小时 ':'')+(dl%60)+' 分钟后':'')+'</small><b>'+lt+' '+esc(nm0(nx))+'</b>'+(dep?'<p>'+esc((dep.querySelector('.s')||{}).textContent||'')+'</p>':'')+navOf(nx)+(late>=10&&window.ZR?'<button type="button" class="tvlate" data-late="'+late+'">晚了 '+(late>=60?Math.floor(late/60)+' 小时 ':'')+(late%60?late%60+' 分钟':'')+'，按现在重排今天</button>':'')+'</div>'}
        h+='<ol class="tvl">'+rows.map(function(r){var t=r.querySelector('time').textContent,past=isT&&/^\d\d:\d\d$/.test(t)&&t<hm&&r!==nx,s=r.querySelector('.s');var cls=r.classList.contains('dep')?'dep':r.classList.contains('eat')?'eat':r.classList.contains('stay')?'stay':'see';
          return'<li class="'+cls+(past?' past':'')+(r===nx?' nx':'')+'"><time>'+t+'</time><div><b>'+esc(nm0(r))+'</b>'+(s&&cls!=='dep'?'<small>'+esc(s.textContent.replace(/调整$/,''))+'</small>':cls==='dep'&&s?'<small>'+esc(s.textContent)+'</small>':'')+'</div>'+(cls!=='dep'?navOf(r):'')+'</li>'}).join('')+'</ol>';
        var st=sec.querySelector('.stays');if(st){var tg=st.querySelector('li:not(.more) b.tg'),lk=st.querySelector('.bk .btn'),mk=st.querySelector('.mk');h+='<div class="tvbox"><small>今晚住</small><b>'+esc((st.querySelector('.sh span:last-child')||{}).textContent||'')+(tg?' · '+esc(tg.textContent):'')+'</b>'+(lk?'<a href="'+lk.href+'" target="_blank" rel="nofollow noopener">'+(mk&&mk.classList.contains('on')?'已订 · 看订单':'去订')+' ›</a>':'')+'</div>'}
        var bks=rows.filter(function(r){return r.querySelector('.bkn')});if(bks.length)h+='<div class="tvbox"><small>今天要预约的</small>'+bks.map(function(r){var a=r.querySelector('.bkl'),hw0=r.querySelector('.bkn[data-how]'),hw=hw0?{textContent:hw0.dataset.how+'预约'}:r.querySelector('.bkh');return'<p><b>'+esc(nm0(r))+'</b>'+(a?' <a href="'+a.href+'" target="_blank" rel="nofollow noopener">官网预约 ›</a>':hw?' <span>'+esc(hw.textContent)+'</span>':'')+'</p>'}).join('')+'</div>';
        h+=(secs.length>1?'<p class="tvhint">左右滑动换一天</p>':'')+'</div>';m.innerHTML=h;m.querySelector('.tvx').addEventListener('click',close);
        var lb=m.querySelector('.tvlate');if(lb)lb.addEventListener('click',function(){window.ZR.shift(sec,+lb.dataset.late);ztrack('晚了重排');toast('按现在重排了，后面的时间都往后挪了');render(i)});[].slice.call(m.querySelectorAll('.tvtabs button')).forEach(function(b){b.addEventListener('click',function(){render(+b.dataset.i)})});
        var on=m.querySelector('.tvtabs .on');if(on)on.scrollIntoView({inline:'center',block:'nearest'});var nxe=m.querySelector('.tvl .nx');if(nxe)nxe.scrollIntoView({block:'center'});cur=i}
      var cur=idx,sx=0,sy=0;   // 左右滑动换一天
      m.addEventListener('touchstart',function(e){var t=e.touches[0];sx=t.clientX;sy=t.clientY},{passive:true});
      m.addEventListener('touchend',function(e){var t=e.changedTouches[0],dx=t.clientX-sx,dy=t.clientY-sy;if(Math.abs(dx)>70&&Math.abs(dy)<40&&!e.target.closest('.tvtabs')){var nx2=cur+(dx<0?1:-1);if(nx2>=0&&nx2<secs.length){render(nx2);m.scrollTop=0}}},{passive:true});
      render(idx)}
    var dk2=document.querySelector('.dock');if(dk2&&!dk2.querySelector('.tvbtn')){var ti0=todayIdx(),nd=document.querySelectorAll('.day').length;dk2.insertAdjacentHTML('beforeend','<button type="button" class="tvbtn">'+(ti0>=0&&ti0<nd?'今天':'按天看')+'</button>');dk2.querySelector('.tvbtn').addEventListener('click',function(){openDay()})}
    // ——— ② 出发前要办的事：准备、预约、每晚住宿集中在一处，能打勾，看进度 ———
    (function(){var TK='zouni_todo_'+me.id;function getT(){try{return JSON.parse(localStorage.getItem(TK)||'[]')}catch(e){return[]}}
      function items(){var out=(window.zGoItems?window.zGoItems(getT(),TK):[]),bkNames=[];[].slice.call(document.querySelectorAll('.tl > .r')).forEach(function(r){if(!r.hidden&&r.querySelector('.bkn'))nm0(r).split(/\s*·\s*/).forEach(function(p){if(p)bkNames.push(p.replace(/博物院|博物馆/,''))})});
        [].slice.call(document.querySelectorAll('.pre li')).forEach(function(li){var x=li.querySelector('input');if(!x)return;var tx=li.querySelector('span').textContent;if(/预约|买票|门票|放票/.test(tx)&&bkNames.some(function(b){return b&&tx.indexOf(b)>=0}))return;var a=li.querySelector('a.bkl');out.push({g:'要准备的',t:li.querySelector('span').textContent,link:a?a.href:'',done:x.checked,tog:function(){x.checked=!x.checked;x.dispatchEvent(new Event('change'))}})});
        var seen={},T=getT();[].slice.call(document.querySelectorAll('.tl > .r')).forEach(function(r){if(r.hidden||!r.querySelector('.bkn'))return;var n=nm0(r);if(seen[n])return;seen[n]=1;var dd=(r.closest('.day').querySelector('header small').textContent.split(' · ')[1])||'',a=r.querySelector('.bkl'),hw0=r.querySelector('.bkn[data-how]'),hw=hw0?{textContent:hw0.dataset.how+'预约'}:r.querySelector('.bkh'),key='b:'+n;
          out.push({g:'要预约的',t:n+(dd?'（'+dd+'）':''),link:a?a.href:'',how:hw?hw.textContent:'',done:T.indexOf(key)>=0,tog:function(){var T2=getT(),i=T2.indexOf(key);if(i>=0)T2.splice(i,1);else T2.push(key);try{localStorage.setItem(TK,JSON.stringify(T2))}catch(e){}}})});
        [].slice.call(document.querySelectorAll('.stays')).forEach(function(c){var sec=c.closest('.day'),dd=(sec.querySelector('header small').textContent.split(' · ')[1])||'',area=(c.querySelector('.sh span:last-child')||{}).textContent||'',tg=c.querySelector('li:not(.more) b.tg'),lk=c.querySelector('.bk .btn'),mk=c.querySelector('.mk');if(!mk)return;
          var stm=sec.querySelector('.r.stay .m'),sn=stm?stm.textContent.replace(/^\s*住\s*·\s*/,'').trim():'',ln=/连住\s*(\d+)\s*晚/.exec(area);
          out.push({g:'住宿',t:dd+' 起住'+(sn||area.replace(/\s*·?\s*连住\s*\d+\s*晚/,'')||'')+(ln?'，连住 '+ln[1]+' 晚':'')+(tg?'：'+tg.textContent:''),link:lk?lk.href:'',done:mk.classList.contains('on'),tog:function(){mk.click()}})});return out}
      var pre=document.querySelector('section.pre');if(!pre)return;pre.insertAdjacentHTML('beforeend','<button type="button" class="todoall"></button>');var ta=pre.querySelector('.todoall');
      function paint(){var it=items(),dn=it.filter(function(x){return x.done}).length;ta.innerHTML='<span>出发前要办的事 · 已办 <b>'+dn+'/'+it.length+'</b></span><i>›</i>'}paint();
      ta.addEventListener('click',function(){var m=document.createElement('div');m.className='tv todo';document.body.appendChild(m);document.body.classList.add('pk-open');
        function close(){m.remove();document.body.classList.remove('pk-open');paint()}
        function render(){var it=items(),dn=it.filter(function(x){return x.done}).length,gs=['往返车票','要准备的','要预约的','住宿'];
          m.innerHTML='<div class="tvh"><button type="button" class="tvx"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg>回到整条行程</button></div><div class="tvb"><h2>出发前要办的事</h2><p class="tvd">已办 '+dn+'/'+it.length+(dn===it.length&&it.length?' · 都办好了':'')+'</p><button type="button" class="todoall tvcal"><span>加到手机日历：每天的安排，买票、预约、订住宿的提醒</span><i>›</i></button>'+gs.map(function(g){var xs=it.filter(function(x){return x.g===g});if(!xs.length)return'';
            return'<h3>'+g+'</h3><ul class="tdl">'+xs.map(function(x,k){return'<li class="'+(x.done?'on':'')+'"><button type="button" class="tck" data-g="'+g+'" data-k="'+k+'" aria-label="'+(x.done?'标记没办':'标记办好了')+'"></button><span>'+String(x.t).replace(/</g,'&lt;')+(x.how?'<small>'+x.how+'</small>':'')+'</span>'+(x.link?'<a href="'+x.link+'" target="_blank" rel="nofollow noopener">'+(g==='住宿'?'去订':g==='往返车票'?'去买':'去办')+' ›</a>':'')+'</li>'}).join('')+'</ul>'}).join('')+'</div>';
          m.querySelector('.tvx').addEventListener('click',close);var cb=m.querySelector('.tvcal');if(cb)cb.addEventListener('click',function(){if(window.zIcs)window.zIcs();toast('日历文件好了，打开后选“全部添加”')});[].slice.call(m.querySelectorAll('.tck')).forEach(function(b){b.addEventListener('click',function(){var xs=items().filter(function(x){return x.g===b.dataset.g});xs[+b.dataset.k].tog();setTimeout(render,30)})})}
        render()})})();
    // 今晚住：看另外两档
    document.querySelectorAll('.stays .tog').forEach(function(b){b.addEventListener('click',function(){var s=b.parentElement;s.classList.toggle('open');b.textContent=s.classList.contains('open')?'收起另外两档':'看另外两档'})});
    // 天数条高亮
    var nav=document.querySelector('.daynav');if(nav){var last=-1;window.addEventListener('scroll',function(){var as=[].slice.call(nav.querySelectorAll('a')),cur=0;as.forEach(function(a,i){var s=document.getElementById('d'+(i+1));if(s&&s.getBoundingClientRect().top<140)cur=i+1});as.forEach(function(a,i){a.classList.toggle('on',i+1===cur)});
      if(cur!==last&&cur>0&&nav.classList.contains('long')){var a=as[cur-1];nav.scrollLeft=a.offsetLeft-nav.clientWidth/2+a.offsetWidth/2}last=cur},{passive:true})}
    var ovm=document.querySelector('.ovmore');if(ovm)ovm.addEventListener('click',function(){document.querySelector('.overview').classList.add('open');ovm.remove()});
  }

  // ——— 地图图标：手机上直接调起高德 App（iOS / 安卓），打不开或在微信里就走网页 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.ic.map[data-ios],a.tvnav[data-ios]');if(!a)return;var ua=navigator.userAgent,ios=/iPhone|iPad|iPod/i.test(ua),and=/Android/i.test(ua);if((!ios&&!and)||/MicroMessenger/i.test(ua))return;
    e.preventDefault();var web=a.href,gone=false,t0=Date.now();function hid(){if(document.hidden)gone=true}document.addEventListener('visibilitychange',hid);
    zOpen(ios?a.dataset.ios:a.dataset.and,'高德地图')});   // 只走高德 App，不退回网页
  // ——— 点评：手机上先试 App，打不开（或在微信里）再去网页 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.dp[data-app],a.xhs[data-app]');if(!a)return;   // 点评、小红书一样：手机上先试 App
    var mobile=/iPhone|iPad|Android/i.test(navigator.userAgent),wx=/MicroMessenger/i.test(navigator.userAgent);if(!mobile||wx)return;
    e.preventDefault();var web=a.href,t=Date.now(),gone=false;function hid(){gone=true}document.addEventListener('visibilitychange',hid,{once:true});
    zOpen(a.dataset.app,a.classList.contains('xhs')?'小红书':'大众点评')});   // 只走 App，不退回网页
  // ——— 本期：按出发日期和“我有几天”挑；快过季的先放三条，其余有海报的精编线路在前 ———
  var dc=document.querySelector('.dchips');
  if(dc){var ol=document.querySelector('.now .items'),lis=[].slice.call(ol.children),mb=document.querySelector('.moreb'),band='',all=false,W='日一二三四五六';
    var hk=document.querySelector('.hdpk'),hb=document.querySelector('.hdt'),cur=hk?hk.value:'';
    function md(v){return v.slice(5)}
    function inWin(li,m){var a=li.dataset.ws,b=li.dataset.we;if(!a)return false;return a<=b?(m>=a&&m<=b):(m>=a||m<=b)}
    function left(li,v){var d=new Date(v+'T12:00:00'),b=li.dataset.we,y=d.getFullYear(),e=new Date(y+'-'+b+'T12:00:00');if(e<d)e=new Date((y+1)+'-'+b+'T12:00:00');return Math.round((e-d)/864e5)}
    function f2(s){return(+s.slice(0,2))+'/'+(+s.slice(3))}
    function show(){var m=md(cur),pool=lis.filter(function(li){return inWin(li,m)});
      pool.forEach(function(li){li._l=left(li,cur)});
      var urg=pool.filter(function(li){return li._l<=14}).sort(function(a,b){return(b.dataset.img-a.dataset.img)||(a._l-b._l)}).slice(0,3);
      var rest=pool.filter(function(li){return urg.indexOf(li)<0}).sort(function(a,b){return(b.dataset.img-a.dataset.img)||(a.dataset.comp-b.dataset.comp)||(a._l-b._l)});
      var ord=urg.concat(rest),isToday=hk&&cur===(hk.dataset.min||hk.min),cvp=null;
      lis.forEach(function(li){if(li.dataset.cv)delete li.dataset.cv});
      var zo=zOrigin(),nearCv=null;
      if(zo){nearCv=ord.filter(function(li){return li.dataset.src&&li.dataset.lat&&li._l>=7&&+li.dataset.n<=5&&li.dataset.ab!=='1'}).map(function(li){return{li:li,d:zKm(zo.lat,zo.lng,+li.dataset.lat,+li.dataset.lng)}}).filter(function(x){return x.d>=60&&x.d<=800});nearCv=nearCv.filter(function(x){return x.li.dataset.img==='1'})[0]||nearCv[0]||null}
      if(nearCv){cvp=nearCv.li;cvp._d=nearCv.d;cvp._o=zo.n;cvp.dataset.cv='1';ord=ord.filter(function(li){return li!==cvp})}
      else if(!isToday){cvp=ord.filter(function(li){return li.dataset.src&&li.dataset.img==='1'&&li._l>=7})[0]||ord.filter(function(li){return li.dataset.src&&li._l>=7})[0]||ord.filter(function(li){return li.dataset.src})[0];if(cvp){cvp._d=null;cvp.dataset.cv='1';ord=ord.filter(function(li){return li!==cvp})}}
      var cnt={'':ord.length,d1:0,d2:0,d3:0};ord.forEach(function(li){cnt[li.dataset.band]++});
      dc.querySelectorAll('button').forEach(function(x){x.textContent=x.textContent.replace(/\s*·?\s*\d+$/,'').replace(/\s+\d+$/,'')+(x.dataset.b?' · ':' ')+cnt[x.dataset.b]});
      var k=0,mo=+m.slice(0,2);lis.forEach(function(li){li.hidden=true});
      ord.forEach(function(li){ol.appendChild(li);var ok=!band||li.dataset.band===band;if(!ok)return;k++;li.hidden=!all&&k>8;li.querySelector('.num').textContent=('0'+(k+1)).slice(-2);
        var lf=li.querySelector('.left');if(lf){lf.className='left'+(li._l<=14?' urgent':'');lf.textContent=li._l<=14?(li._l===0?'今天是最后一天':'最后 '+li._l+' 天'):'最好 '+f2(li.dataset.ws)+'–'+f2(li.dataset.we)+' · 还剩 '+li._l+' 天'}
        var c=li.querySelector('.c');if(c&&li.dataset.clim){var cl=JSON.parse(li.dataset.clim)[mo];if(cl)c.textContent=mo+' 月白天 '+cl[0]+'℃，夜里 '+cl[1]+'℃'}});
      var vis=ord.filter(function(li){return!band||li.dataset.band===band}).length;
      if(mb){mb.hidden=all||vis<=8;mb.textContent='再看 '+Math.max(0,vis-8)+' 条'}
      var today=hk&&cur===(hk.dataset.min||hk.min),d=new Date(cur+'T12:00:00');
      // 封面跟着日期换：挑这天正当季、有海报的第一条，封面图、标题、还剩几天、天数价格、当月气温、翻开链接都换
      var cv=cvp;
      if(cv&&(!today||cv._d)){var img=document.querySelector('.cover img');if(img)img.src=cv.dataset.src;var tt=cv.dataset.t,ci=tt.indexOf('，'),h2=document.querySelector('.cv h2');if(ci>0&&ci<tt.length-1){h2.textContent=tt.slice(0,ci+1);var sp=document.createElement('span');sp.className='nw';sp.textContent=tt.slice(ci+1);h2.appendChild(sp)}else h2.textContent=tt;
        document.querySelector('.cv .kick').textContent=cv._d?('从'+cv._o+'过去约 '+cv._d+' 公里 · 正当季 · 还剩 '+cv._l+' 天'):('封面故事 · '+f2(md(cur))+' 出发正当季 · 还剩 '+cv._l+' 天');
        var cl2=JSON.parse(cv.dataset.clim||'{}')[mo]||['',''],chs=document.querySelectorAll('.cv .chips span');if(chs[0])chs[0].textContent=cv.dataset.n+' 天 · 人均 '+cv.dataset.pr;if(chs[1])chs[1].textContent=mo+' 月 '+cl2[0]+'°C / '+cl2[1]+'°C';
        document.querySelector('.cv .go').href=cv.dataset.h}
      document.querySelector('.now .nt').textContent=today?'现在去正好':(f2(md(cur))+' 出发正好去');document.querySelector('.now .ns').textContent=vis+' 条，快过季的先看'}
    document.addEventListener('zouni:origin',function(){show()});
    dc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;band=b.dataset.b;all=false;dc.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});show()});
    if(mb)mb.addEventListener('click',function(){all=true;show()});
    if(hk){hb.addEventListener('click',function(){openPicker({value:hk.value,min:hk.dataset.min||hk.min,best:null,onPick:function(v){hk.value=v;hk.dispatchEvent(new Event('change'))}})});
      hk.addEventListener('change',function(){if(!hk.value)return;cur=hk.value;all=false;try{localStorage.setItem('zouni_home_date',cur)}catch(e){}var d=new Date(cur+'T12:00:00');hb.querySelector('b').textContent=(d.getMonth()+1)+'/'+d.getDate()+' 周'+W[d.getDay()]+' 出发';show();document.getElementById('now').scrollIntoView()});
      try{var h0=localStorage.getItem('zouni_home_date');if(h0&&h0>=(hk.dataset.min||hk.min)){hk.value=h0;cur=h0;var d0=new Date(h0+'T12:00:00');hb.querySelector('b').textContent=(d0.getMonth()+1)+'/'+d0.getDate()+' 周'+W[d0.getDay()]+' 出发'}}catch(e){}}
    show()}
  // ——— 路线图点一下放大看（手机上可以拖着看） ———
  document.querySelectorAll('.hmap').forEach(function(f){var svg=f.querySelector('svg');if(!svg)return;f.setAttribute('role','button');f.setAttribute('tabindex','0');f.title='点一下放大看';
    function open(e){if(e.target.closest('a'))return;var m=document.createElement('div');m.className='hmap-zoom';m.innerHTML='<div class="hz-t"><button type="button" class="hz-m" aria-label="缩小">－</button><button type="button" class="hz-p" aria-label="放大">＋</button><button type="button" class="hz-x">关上</button></div><div class="hz-b"></div>';m.querySelector('.hz-b').appendChild(svg.cloneNode(true));
      document.body.appendChild(m);document.body.classList.add('pk-open');var b=m.querySelector('.hz-b'),sv=b.querySelector('svg'),z=2;
      function zoom(nz){var cxr=(b.scrollLeft+b.clientWidth/2)/b.scrollWidth,cyr=(b.scrollTop+b.clientHeight/2)/b.scrollHeight;z=Math.max(1,Math.min(4,nz));sv.style.width=(z*100)+'vw';b.scrollLeft=cxr*b.scrollWidth-b.clientWidth/2;b.scrollTop=cyr*b.scrollHeight-b.clientHeight/2;m.querySelector('.hz-m').disabled=z<=1;m.querySelector('.hz-p').disabled=z>=4}
      zoom(2);b.scrollLeft=(b.scrollWidth-b.clientWidth)/2;m.querySelector('.hz-p').addEventListener('click',function(){zoom(z+1)});m.querySelector('.hz-m').addEventListener('click',function(){zoom(z-1)});
      function cl(){m.remove();document.body.classList.remove('pk-open')}m.querySelector('.hz-x').addEventListener('click',cl);m.addEventListener('click',function(e){if(e.target===m)cl()})}
    f.addEventListener('click',open);f.addEventListener('keydown',function(e){if(e.key==='Enter')open(e)})});

  // ——— 目的地页：线路多（7 条以上）时，按天数和自驾筛一下 ———
  (function(){var ul=document.querySelector('.trips');if(!ul)return;var lis=[].slice.call(ul.querySelectorAll('li[data-n]'));if(lis.length<7)return;
    var F=[['all','全部',function(){return true}],['s','2–3 天',function(l){return+l.dataset.n<=3}],['m','4–5 天',function(l){var n=+l.dataset.n;return n>=4&&n<=5}],['l','6 天以上',function(l){return+l.dataset.n>=6}],['d','自驾',function(l){return l.dataset.drv==='1'}]];
    var bar=document.createElement('div');bar.className='tf';bar.innerHTML=F.map(function(f,i){var c=lis.filter(f[2]).length;return c?'<button type="button" data-f="'+f[0]+'" class="'+(i?'':'on')+'">'+f[1]+' · '+c+'</button>':''}).join('');ul.parentNode.insertBefore(bar,ul);
    var SK2='zouni_tf_'+location.pathname;function pick(b){var f=F.filter(function(x){return x[0]===b.dataset.f})[0];lis.forEach(function(l){l.hidden=!f[2](l)});[].slice.call(bar.querySelectorAll('button')).forEach(function(x){x.classList.toggle('on',x===b)});try{sessionStorage.setItem(SK2,b.dataset.f)}catch(e){}}
    [].slice.call(bar.querySelectorAll('button')).forEach(function(b){b.addEventListener('click',function(){pick(b)})});
    try{var f0=sessionStorage.getItem(SK2),b0=f0&&bar.querySelector('button[data-f="'+f0+'"]');if(b0){pick(b0);b0.scrollIntoView({inline:'center',block:'nearest'})}}catch(e){}   // 进了行程再返回，筛选还在
  })();
  // ——— 首页：替我挑三条（从哪出发、几天、和谁去 → 三条推荐和理由）———
  (function(){var cv0=document.querySelector('.cv');if(!cv0||document.querySelector('.pick'))return;var cv=cv0.closest('.cover')||cv0.closest('section')||cv0;
    var C={'北京':[39.90,116.40],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'成都':[30.66,104.07],'杭州':[30.27,120.16],'西安':[34.26,108.94],'武汉':[30.59,114.31],'南京':[32.06,118.80],'重庆':[29.56,106.55],'长沙':[28.23,112.94],'郑州':[34.75,113.63],'天津':[39.13,117.20],'苏州':[31.30,120.58],'厦门':[24.48,118.09],'昆明':[25.04,102.71],'沈阳':[41.80,123.43],'青岛':[36.07,120.38],'香港':[22.32,114.17]};
    var PK='zouni_pick',st={};try{st=JSON.parse(localStorage.getItem(PK)||'{}')}catch(e){}if(!st.o){try{var o0=localStorage.getItem('zouni_org');if(o0&&C[o0])st.o=o0}catch(e){}}
    var sec=document.createElement('section');sec.className='pick';cv.parentNode.insertBefore(sec,cv.nextSibling);
    if(st.o==='here'&&st.lat)C['here']=[st.lat,st.lng];
    function chips(k,arr){return'<div class="pkr" data-k="'+k+'">'+arr.map(function(a){return'<button type="button" data-v="'+a[0]+'" class="'+(st[k]===a[0]?'on':'')+'">'+a[1]+'</button>'}).join('')+'</div>'}
    function km(a,b){var r=Math.PI/180,x=(b[1]-a[1])*r*Math.cos((a[0]+b[0])/2*r),y=(b[0]-a[0])*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
    function pick(){var all=[].slice.call(document.querySelectorAll('.toc .items li')).filter(function(li){return li.dataset.lat&&li.querySelector('a[href^="/trip/"]')}),o=C[st.o],seen={},sc=[];
      all.forEach(function(li){var href=li.querySelector('a[href^="/trip/"]').getAttribute('href');if(seen[href])return;seen[href]=1;var n=+li.dataset.n,d=km(o,[+li.dataset.lat,+li.dataset.lng]),s=0,why=[];
        if(d<60)return;   // 就在出发地的不推荐
        if(st.d==='w'){if(n>3)return;s+=d<=600?30:d<=1200?20:d<=2000?5:-40}else if(st.d==='m'){if(n<4||n>5)return;s+=d<=2500?20:0}else{if(n<6)return;s+=10}
        if(st.w==='o'&&li.dataset.hi==='1')return;if(st.w==='o'&&li.dataset.drv==='1'&&n>8)s-=15;
        var kk=((li.querySelector('.k')||{}).textContent||'').replace(/\s+/g,' ').trim();if(/正当季|最好/.test(kk))s+=12;if(/最后/.test(kk))s+=6;if(li.closest('#drive'))s+=st.d==='l'?10:-5;if(li.dataset.img==='1')s+=3;
        var on2=st.o==='here'?'你这里':st.o;
        if(li.dataset.ab==='1')why.push('从'+on2+'飞过去约 '+Math.max(1,Math.round(d/700+1))+' 小时');else if(d<80)why.push('就在'+on2+'附近');else if(d<=1200)why.push(on2+'过去约 '+d+' 公里，高铁约 '+Math.max(1,Math.round(d/230))+' 小时');else why.push(on2+'过去约 '+d+' 公里，坐飞机最省事');
        if(li.dataset.ab==='1'&&st.d==='w')s-=8;
        if(kk)why.push(kk);if(st.w==='o')why.push('不上高原');
        sc.push({s:s,li:li,href:href,why:why.join(' · ')})});
      sc.sort(function(a,b){return b.s-a.s});var top=[],dests={};sc.forEach(function(x){var t=x.li.querySelector('h3').textContent.split(' · ')[0];if(top.length<3&&!dests[t]){dests[t]=1;top.push(x)}});return top}
    function render(){var ready=st.o&&st.d&&st.w,res=ready?pick():[];
      sec.innerHTML='<h2>替我挑三条<small>答三个问题</small></h2>'+'<p class="pkq">从哪出发</p>'+chips('o',[['here','📍 当前位置']].concat(Object.keys(C).filter(function(c){return c!=='here'}).map(function(c){return[c,c]})))+'<p class="pkq">玩几天</p>'+chips('d',[['w','周末 2–3 天'],['m','4–5 天'],['l','一周以上']])+'<p class="pkq">和谁去</p>'+chips('w',[['f','自己或朋友'],['c','两个人'],['o','带老人孩子']])+
        (ready?(res.length?'<ol class="pkres">'+res.map(function(x,i){var img=x.li.querySelector('img');return'<li><a href="'+x.href+'"><span class="pkn">'+(i+1)+'</span><div><b>'+x.li.querySelector('h3').textContent+'</b><small>'+x.why+'</small></div>'+(img?'<img src="'+(img.getAttribute('src')||img.dataset.src||'')+'" alt="" loading="lazy">':'')+'</a></li>'}).join('')+'</ol>':'<p class="pkhint">这个时间没找到合适的，换个天数试试，或者把出发日期往后挪</p>'):'<p class="pkhint">选好三项，马上给你三条</p>');
      var on=sec.querySelector('.pkr[data-k="o"] .on');if(on)on.scrollIntoView({inline:'center',block:'nearest'});
      [].slice.call(sec.querySelectorAll('.pkr button')).forEach(function(b){b.addEventListener('click',function(){var k=b.parentNode.dataset.k;
          if(k==='o'&&b.dataset.v==='here'){if(!navigator.geolocation){toast('这个浏览器拿不到位置，选个城市吧');return}b.textContent='📍 定位中…';navigator.geolocation.getCurrentPosition(function(p){st.o='here';st.lat=+p.coords.latitude.toFixed(3);st.lng=+p.coords.longitude.toFixed(3);C['here']=[st.lat,st.lng];try{localStorage.setItem(PK,JSON.stringify(st))}catch(e){}var y=scrollY;render();scrollTo(0,y);document.dispatchEvent(new Event('zouni:origin'))},function(){toast('没拿到位置（可能没给定位权限），选个城市吧');b.textContent='📍 当前位置'},{timeout:8000,maximumAge:600000});return}
          st[k]=b.dataset.v;try{localStorage.setItem(PK,JSON.stringify(st));if(k==='o')localStorage.setItem('zouni_org',b.dataset.v)}catch(e){}var y=scrollY;render();scrollTo(0,y);if(k==='o')document.dispatchEvent(new Event('zouni:origin'));ztrack('替我挑·'+({o:'出发地',d:'天数',w:'和谁'}[k]||k))})})}
    render()})();
  // ——— 首页“长途和自驾”：再看全部 ———
  var dm=document.querySelector('.dmore');if(dm)dm.addEventListener('click',function(){document.querySelectorAll('#drive .items li[hidden]').forEach(function(li){li.hidden=false});dm.remove()});
  // ——— 本期：刊头“我的行程”打开面板，不占首页 ———
  var mb0=document.querySelector('.minebtn');
  if(mb0){var fv0=ld('zouni_fav');if(fv0.length)mb0.querySelector('span').textContent='我的行程 · '+fv0.length;
    mb0.addEventListener('click',function(){var fv=ld('zouni_fav'),sn=ld('zouni_seen').filter(function(x){return!fv.some(function(f){return f.id===x.id})}).slice(0,5);
      function esc(t){return String(t).replace(/</g,'&lt;')}
      function row(x,withDate){var when='';if(withDate){var s0='';try{s0=localStorage.getItem('zouni_start_'+x.id)||''}catch(e){}if(s0){var d=new Date(s0+'T12:00:00'),nn=new Date();nn.setHours(12,0,0,0);var lf=Math.round((d-nn)/864e5);when='<small class="mw">'+(d.getMonth()+1)+'/'+d.getDate()+' 出发 · '+(lf>0?'还有 '+lf+' 天':lf===0?'就是今天':'已出发')+'</small>'}}
        return'<a class="mr" href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+esc(x.label)+'</b><span>'+esc(x.title)+'</span>'+when+'</a>'}
      var mask=document.createElement('div');mask.className='pk-mask';var s3=document.createElement('div');s3.className='pk';
      s3.innerHTML='<div class="pk-h"><b>我的行程</b><button type="button" class="pk-x">关上</button></div><div class="xd">'+(fv.length?fv.map(function(x){return row(x,true)}).join(''):'<p class="mempty">还没有收进的行程。打开一条行程，点底部“收进行程”就会出现在这里。</p>')+(sn.length?'<p class="xg">最近看过</p>'+sn.map(function(x){return row(x,false)}).join(''):'')+'</div>';
      function cl(){mask.remove();s3.remove();document.body.classList.remove('pk-open')}
      s3.querySelector('.pk-x').addEventListener('click',cl);mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(s3);document.body.classList.add('pk-open')})}
  // ——— 本期：我的行程、最近看过 ———
  function mineEmpty(){var sec=document.getElementById('mine');if(sec&&location.hash==='#mine'&&!ld('zouni_fav').length){sec.hidden=false;sec.querySelector('ul').innerHTML='<li class=empty>还没有收进的行程。打开任意一条行程，点底部“收进行程”，就会出现在这里。</li>'}}
  window.addEventListener('hashchange',mineEmpty);mineEmpty();
  document.querySelectorAll('.mine').forEach(function(sec){var ul=sec.querySelector('ul'),k=ul.dataset.k==='fav'?'zouni_fav':'zouni_seen',xs=ld(k);if(!xs.length)return;sec.hidden=false;
    ul.innerHTML=xs.map(function(x){var s0='';try{s0=localStorage.getItem('zouni_start_'+x.id)||''}catch(e){}var when='';if(s0){var d=new Date(s0+'T12:00:00'),n=new Date();n.setHours(12,0,0,0);var left=Math.round((d-n)/864e5);when='<small>'+(d.getMonth()+1)+'/'+d.getDate()+' 出发 · '+(left>0?'还有 '+left+' 天':left===0?'就是今天':'已出发')+'</small>'}
      return'<li><a href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+String(x.label).replace(/</g,'&lt;')+' ›</b><span>'+String(x.title).replace(/</g,'&lt;')+'</span>'+when+'</a></li>'}).join('')});

  // ——— 去哪儿 ———
  var flt=document.querySelector('.flt'),mon=document.querySelector('.mon');
  if(flt&&mon){
    var st={fit:true,d:'',low:false,q:'',niche:false,near:false,bud:0,tab:'domestic',drive:false},inp=flt.querySelector('input'),cnt=document.querySelector('.cnt'),gl=document.querySelector('.goodline');
    var on=mon.querySelector('button.on');if(on)mon.scrollLeft=on.offsetLeft-(mon.clientWidth-on.offsetWidth)/2;
    function curM(){var b=mon.querySelector('button.on');return b?+b.dataset.m:new Date().getMonth()+1}
    function near(best,m){return best.some(function(x){return Math.abs((x-m+12)%12)===1||Math.abs((m-x+12)%12)===1})}
    function save(){try{sessionStorage.setItem('zouni_where',JSON.stringify({st:st,m:curM(),open:!flt.hidden}))}catch(e){}}
    function apply(){var m=curM(),n=0,good=[];setTimeout(save,0);
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
        if(st.drive&&c.dataset.drive!=='1')ok=false;
        if(st.bud&&!(c.dataset.plo!==''&&+c.dataset.plo<=st.bud))ok=false;
        if(st.near&&!(c.dataset.km&&+c.dataset.km<=500))ok=false;
        if(st.q&&c.dataset.q.toLowerCase().indexOf(st.q)<0)ok=false;
        var hp=c.querySelector('.hit'),why=st.q?c.dataset.hits.split('|').filter(function(h){return h.toLowerCase().indexOf(st.q)>=0}).slice(0,3):[];hp.hidden=!why.length;hp.textContent=why.length?'有 '+why.join('、'):'';
        c.hidden=!ok;var inTab=c.closest('.scope').id===st.tab;if(ok&&inTab)n++;if(v==='正好'&&inTab)good.push(c.dataset.name)});
      document.querySelectorAll('.reg').forEach(function(r){r.hidden=!r.querySelector('.card:not([hidden])')});
      cnt.textContent=n?('符合的 '+n+' 个'):'没有符合的，点“清空筛选”再看看';
      var k=(st.q?1:0)+(st.d?1:0)+(st.low?1:0)+(st.niche?1:0)+(st.near?1:0)+(st.bud?1:0)+(st.fit?0:1);ft.textContent=(flt.hidden?'筛选':'收起')+(k?' · '+k:'')+(flt.hidden?' ▾':' ▴');ft.classList.toggle('on',k>0||!flt.hidden);clr.hidden=!k;
      if(typeof drawMap==='function')setTimeout(drawMap,0);
      gl.textContent=good.length?(m+' 月正好去 '+good.length+' 个：'+good.slice(0,10).join('、')+(good.length>10?' 等':'')):(m+' 月没有正好去的，看看“也行”的')}

    // ——— 去哪儿：地图看（按现在的筛选，正好的黑点、也行的绿点；点名字进目的地） ———
    var mt=document.querySelector('.mtog'),mapbox=null;
    function drawMap(){if(!mapbox)return;var cs=[].slice.call(document.querySelectorAll('#'+st.tab+' .card:not([hidden])'));
      if(!cs.length){mapbox.innerHTML='<p class="hint" style="padding:16px">没有符合的目的地</p>';return}
      var pts=cs.map(function(c){return{la:+c.dataset.lat,lo:+c.dataset.lng,n:c.dataset.name,f:c.querySelector('.fit').className,h:c.querySelector('a.ch').getAttribute('href')}});
      var la=pts.map(function(p){return p.la}),lo=pts.map(function(p){return p.lo}),cl=(Math.max.apply(0,la)+Math.min.apply(0,la))/2,k=Math.cos(cl*Math.PI/180);
      var Wm=390,Hm=st.tab!=='domestic'?300:340,pad=34,sx=Math.max((Math.max.apply(0,lo)-Math.min.apply(0,lo))*k,1),sy=Math.max(Math.max.apply(0,la)-Math.min.apply(0,la),1),sc=Math.min((Wm-2*pad)/sx,(Hm-2*pad)/sy),cx=(Math.max.apply(0,lo)+Math.min.apply(0,lo))/2;
      function P(p){return[Wm/2+(p.lo-cx)*k*sc,Hm/2-(p.la-cl)*sc]}
      var o='<svg viewBox="0 0 '+Wm+' '+Hm+'" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="1" width="'+(Wm-2)+'" height="'+(Hm-2)+'" fill="#efe9dc"/><rect x="6" y="6" width="'+(Wm-12)+'" height="'+(Hm-12)+'" fill="none" stroke="#1c1d1a" stroke-width="1.2" opacity=".55"/>',boxes=[];
      pts.sort(function(a,b){return(a.f==='fit'?0:1)-(b.f==='fit'?0:1)}).forEach(function(p){var q=P(p),col=p.f==='fit'?'#1c1d1a':/ok/.test(p.f)?'#4f6233':'#8d8f88',w=p.n.length*12+6;
        o+='<circle cx="'+q[0].toFixed(1)+'" cy="'+q[1].toFixed(1)+'" r="'+(p.f==='fit'?5:4)+'" fill="'+col+'"/>';
        var placed=false;
        [12,10].forEach(function(fs){if(placed)return;var w2=p.n.length*fs+6,dy=fs;
          var cand=[[q[0]+8,q[1]+4,'start'],[q[0]-8,q[1]+4,'end'],[q[0],q[1]-9,'middle'],[q[0],q[1]+dy+5,'middle'],[q[0]+6,q[1]-8,'start'],[q[0]-6,q[1]-8,'end'],[q[0]+6,q[1]+dy+4,'start'],[q[0]-6,q[1]+dy+4,'end']];
          for(var i=0;i<cand.length;i++){var c=cand[i],x0=c[2]==='start'?c[0]:c[2]==='end'?c[0]-w2:c[0]-w2/2,x1=x0+w2,y0=c[1]-dy,y1=c[1]+3;if(x0<10||x1>Wm-10||y0<10||y1>Hm-26)continue;
            if(boxes.some(function(b){return!(x1<b[0]||x0>b[2]||y1<b[1]||y0>b[3])}))continue;boxes.push([x0,y0,x1,y1]);placed=true;
            o+='<a href="'+p.h+'"><rect x="'+Math.min(x0-2,(x0+x1)/2-24)+'" y="'+(y0-16)+'" width="'+Math.max(w2+4,48)+'" height="46" fill="#efe9dc" fill-opacity="0"/><text x="'+c[0].toFixed(1)+'" y="'+c[1].toFixed(1)+'" text-anchor="'+c[2]+'" font-family="Noto Serif SC,serif" font-size="'+fs+'" font-weight="900" fill="'+col+'" paint-order="stroke" stroke="#efe9dc" stroke-width="3">'+p.n+'</text></a>';break}})});
      o+='<text x="14" y="'+(Hm-14)+'" font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59">黑点正好去，绿点也行，灰点不建议 · 点名字进去</text></svg>';mapbox.innerHTML=o}
    if(mt)mt.addEventListener('click',function(){var on=!mapbox;if(on){mapbox=document.createElement('div');mapbox.className='wmap hmap';document.querySelector('.wbar').insertAdjacentElement('afterend',mapbox);document.querySelectorAll('.scope').forEach(function(s){s.classList.add('maphide')});drawMap()}
      else{mapbox.remove();mapbox=null;document.querySelectorAll('.scope').forEach(function(s){s.classList.remove('maphide')})}mt.textContent=on?'列表看':'地图看';mt.classList.toggle('on',on)});
    mon.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});apply()});
    document.querySelectorAll('.tabs button').forEach(function(b){b.addEventListener('click',function(){st.tab=b.dataset.t;document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x===b)});apply()})});
    var ft=document.querySelector('.ftog'),clr=flt.querySelector('.clr');ft.addEventListener('click',function(){flt.hidden=!flt.hidden;apply()});
    clr.addEventListener('click',function(){st.q='';st.d='';st.low=false;st.niche=false;st.near=false;st.drive=false;st.bud=0;st.fit=true;inp.value='';flt.querySelectorAll('.row button').forEach(function(b){b.classList.toggle('on',b.dataset.f==='fit')});flt.querySelector('.bud').value='';apply()});
    inp.addEventListener('input',function(){st.q=inp.value.trim().toLowerCase();apply()});
    flt.querySelectorAll('.row button[data-f]').forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;
      if(f==='fit'||f==='low'||f==='niche'||f==='near'||f==='drive'){st[f]=!st[f];b.classList.toggle('on',st[f])}
      else{st.d=st.d===f?'':f;flt.querySelectorAll('[data-f^="d"]').forEach(function(x){x.classList.toggle('on',x.dataset.f===st.d)})}apply()})});
    var bud=flt.querySelector('.bud');bud.addEventListener('change',function(){st.bud=+bud.value||0;apply()});
    try{var sv0=JSON.parse(sessionStorage.getItem('zouni_where')||'null');if(sv0){Object.keys(sv0.st).forEach(function(k){st[k]=sv0.st[k]});
      mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',+x.dataset.m===sv0.m)});
      document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x.dataset.t===st.tab)});
      inp.value=st.q||'';bud.value=st.bud?String(st.bud):'';flt.hidden=!sv0.open;
      flt.querySelectorAll('.row button[data-f]').forEach(function(b){var f=b.dataset.f;b.classList.toggle('on',(f==='fit'||f==='low'||f==='niche'||f==='near'||f==='drive')?!!st[f]:st.d===f)})}}catch(e){}
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
    try{if(new URLSearchParams(location.search).get('f')==='drive'){st.drive=true;st.fit=false;flt.hidden=false;var fb=flt.querySelector('[data-f="drive"]');if(fb)fb.classList.add('on');flt.querySelectorAll('[data-f="fit"]').forEach(function(b){b.classList.remove('on')})}}catch(e){}
    try{var q0=new URLSearchParams(location.search).get('q');if(q0){st.q=q0.trim().toLowerCase();st.fit=false;inp.value=q0;flt.hidden=false;flt.querySelectorAll('[data-f="fit"]').forEach(function(b){b.classList.remove('on')})}}catch(e){}
    apply()}
})();
