(function(){
  // 没网时告诉一声：看的是存在手机上的版本
  function netBar(){var b=document.querySelector('.offline');if(navigator.onLine){if(b)b.remove();return}if(!b){b=document.createElement('div');b.className='offline';b.setAttribute('role','status');b.textContent='现在没有网络，看的是之前打开时存下的版本';document.body.insertBefore(b,document.body.firstChild)}}   // 放在页面最上面的文档流里：把内容往下推，不盖住返回、首页、分享
  window.addEventListener('online',netBar);window.addEventListener('offline',netBar);netBar();
  if('serviceWorker' in navigator&&(location.protocol==='https:'||(/^(localhost|127\.0\.0\.1)$/.test(location.hostname)&&lsGet('zouni_dev_sw')==='1')))window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js').catch(function(){})});   // 线上只在 https 注册；本机只有设了 localStorage.zouni_dev_sw=1 才注册（tests/ux_state_offline_check.py 测离线用；别的测试靠 page.route 造网络故障，Service Worker 会把请求截走）
  function lsGet(k){try{return localStorage.getItem(k)}catch(e){return null}}
  function ld(k){try{return JSON.parse(localStorage.getItem(k)||'[]')}catch(e){return[]}}
  function sv(k,v){try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}
  function zSnap(keys){var o={};keys.forEach(function(k){try{o[k]=localStorage.getItem(k)}catch(e){o[k]=null}});return function(){keys.forEach(function(k){try{if(o[k]==null)localStorage.removeItem(k);else localStorage.setItem(k,o[k])}catch(e){}})}}   // 改之前把几个键拍个快照，撤销时原样写回
  // 某条线现在按哪天出发：这条线自己存的和首页存的，谁新听谁的（旧数据没有时间戳 = 0，这条线自己存的优先）；都没有就用收藏时记下的建议日期
  function zISO(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
  function zEff(id,sd){try{var mn=zISO(new Date()),r=localStorage.getItem('zouni_start_'+id),h=localStorage.getItem('zouni_home_date'),rt=+localStorage.getItem('zouni_startt_'+id)||0,ht=+localStorage.getItem('zouni_home_datet')||0;if(r&&r<mn)r=null;if(h&&h<mn)h=null;var v=(r&&h)?(ht>rt?h:r):(r||h);if(v)return{v:v,sug:false};if(sd&&sd>=mn)return{v:sd,sug:true}}catch(e){}return null}
  function zWhen(x){var e=zEff(x.id,x.sd),n=(/(\d+)\s*天/.exec(x.label||'')||[])[1]||x.n||'';if(!e)return(n?n+' 天 · ':'')+'出发日期还没定，点进去选';var d=new Date(e.v+'T12:00:00'),nn=new Date();nn.setHours(12,0,0,0);var lf=Math.round((d-nn)/864e5);return(n?n+' 天 · ':'')+(e.sug?'建议 ':'')+(d.getMonth()+1)+'/'+d.getDate()+' 周'+'日一二三四五六'.charAt(d.getDay())+' 出发 · '+(lf>0?'还有 '+lf+' 天':lf===0?'就是今天':'已出发')}
  function zjump(y){try{window.scrollTo({top:y,behavior:'instant'})}catch(e){window.scrollTo(0,y)}}
  // 提示条：同一时刻只留一条（新的顶掉旧的）；带“撤销”的停 5 秒；点别处、再点别的按钮立刻收起，不叠在弹层和后续操作上
  function toastOff(){var ts=document.querySelectorAll('.toast');for(var i=0;i<ts.length;i++){clearTimeout(ts[i]._tm);ts[i].remove()}}
  function toast(t,label,fn,ms){toastOff();var d=document.createElement('div');d.className='toast';d.setAttribute('role','status');var sp=document.createElement('span');sp.className='toast-t';sp.textContent=t;d.appendChild(sp);if(label&&fn){d.className='toast act';var b=document.createElement('button');b.type='button';b.className='toast-act';b.textContent=label;b.addEventListener('click',function(){clearTimeout(d._tm);d.remove();fn()});d.appendChild(b)}document.body.appendChild(d);d._tm=setTimeout(function(){d.remove()},ms||(label?5000:1700))}
  document.addEventListener('click',function(e){var ts=document.querySelectorAll('.toast');for(var i=0;i<ts.length;i++){if(!ts[i].contains(e.target)){clearTimeout(ts[i]._tm);ts[i].remove()}}},true);
  // 弹层底部再放一个“关上”：关闭键在右上角，单手够不着；底部这个只是转发给头部那个，各弹层原来的关闭逻辑不变
  (function(){function fix(n,mo){var h=n.querySelector('.pk-x'),x=n.querySelector('.pk-xb');if(!h){if(x)x.remove();return}if(x&&x===n.lastElementChild)return;if(mo)mo.disconnect();if(!x){x=document.createElement('button');x.type='button';x.className='pk-xb';x.textContent='关上'}n.appendChild(x);if(mo)mo.observe(n,{childList:true})}
    function addX(n){if(!n||n.nodeType!==1||!n.classList.contains('pk')||n._xb)return;n._xb=1;var mo=window.MutationObserver?new MutationObserver(function(){fix(n,mo)}):null;fix(n,mo);if(mo)mo.observe(n,{childList:true})}
    if(window.MutationObserver)new MutationObserver(function(ms){for(var i=0;i<ms.length;i++){var a=ms[i].addedNodes;for(var j=0;j<a.length;j++)addX(a[j])}}).observe(document.body||document.documentElement,{childList:true});
    document.addEventListener('click',function(e){var b=e.target.closest&&e.target.closest('.pk-xb');if(!b)return;e.stopPropagation();e.preventDefault();var h=b.parentNode.querySelector('.pk-x');if(h)h.click()},true)})();
  // 日出日落：按今天的月份和每天的坐标算
  // 夏令时：k = eu / us / au / nz / eg，其余不实行；返回当天要加的小时数
  function dstOff(k,dt){if(!k)return 0;var y=dt.getFullYear(),c=new Date(y,dt.getMonth(),dt.getDate()).getTime();
    function nth(mo,wd,n){var x;if(n>0){x=new Date(y,mo,1);x.setDate(1+((wd-x.getDay()+7)%7)+7*(n-1))}else{x=new Date(y,mo+1,0);x.setDate(x.getDate()-((x.getDay()-wd+7)%7))}return x.getTime()}
    if(k==='eu')return c>=nth(2,0,-1)&&c<nth(9,0,-1)?1:0;
    if(k==='us')return c>=nth(2,0,2)&&c<nth(10,0,1)?1:0;
    if(k==='au')return(c>=nth(9,0,1)||c<nth(3,0,1))?1:0;
    if(k==='nz')return(c>=nth(8,0,-1)||c<nth(3,0,1))?1:0;
    if(k==='eg')return c>=nth(3,5,-1)&&c<=nth(9,4,-1)?1:0;
    return 0}
  function sun(lat,lon,dt,rise,tz,dst){tz=(tz===undefined||isNaN(tz))?8:tz;tz+=dstOff(dst,dt);var n=Math.round((dt-new Date(dt.getFullYear(),0,0))/864e5),r=Math.PI/180,lh=lon/15,t=n+((rise?6:18)-lh)/24,M=.9856*t-3.289,L=(M+1.916*Math.sin(M*r)+.02*Math.sin(2*M*r)+282.634)%360,RA=(Math.atan(.91764*Math.tan(L*r))/r+360)%360;RA=(RA+(Math.floor(L/90)*90-Math.floor(RA/90)*90))/15;var sd=.39782*Math.sin(L*r),cd=Math.cos(Math.asin(sd)),cH=(Math.cos(90.833*r)-sd*Math.sin(lat*r))/(cd*Math.cos(lat*r));if(cH>1||cH<-1)return'—';var H=(rise?360-Math.acos(cH)/r:Math.acos(cH)/r)/15,T=H+RA-.06571*t-6.622,lo=((T-lh)%24+24+tz)%24,h=Math.floor(lo),m=Math.round((lo-h)*60);if(m==60){h++;m=0}return(h<10?'0':'')+h+':'+(m<10?'0':'')+m}


  // ——— 行程页顶部三格：放不下时三项一起缩小一号，始终同一个字号 ———
  function fitGlance(){var bs=[].slice.call(document.querySelectorAll('.glance>div>b'));if(!bs.length)return;bs.forEach(function(b){b.style.fontSize=''});var fs=20;
    while(fs>15&&bs.some(function(b){return b.scrollWidth>b.clientWidth+1})){fs--;bs.forEach(function(b){b.style.fontSize=fs+'px'})}}
  fitGlance();window.addEventListener('resize',fitGlance);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(fitGlance);
  var gp=document.querySelector('.glance .price');if(gp&&window.MutationObserver)new MutationObserver(function(){fitGlance()}).observe(gp,{childList:true,characterData:true,subtree:true});
  // ——— 站内日期面板（不用系统控件）：月历、过去的日子不能选、标出最好的日子、几个常用日子一点就选 ———
  function openPicker(o){var W='一二三四五六日',val=o.value,min=o.min,best=o.best,sug=o.sug&&o.sug>=min?o.sug:'',nowY=+min.slice(0,4),nowM=+min.slice(5,7)-1;var cur=new Date(val+'T12:00:00');var vy=cur.getFullYear(),vm=cur.getMonth();
    function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
    function inBest(d){if(!best)return false;var m=('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);return best[0]<=best[1]?(m>=best[0]&&m<=best[1]):(m>=best[0]||m<=best[1])}
    var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';sh.setAttribute('role','dialog');sh.setAttribute('aria-label','选出发日期');
    function sat(k){var d=new Date();d.setHours(12);var add=(6-d.getDay()+7)%7;d.setDate(d.getDate()+add+7*k);return d}
    function nm1(){var d=new Date();d.setHours(12);d.setMonth(d.getMonth()+1,1);return d}
    var quick=[['这周六',sat(0)],['下周六',sat(1)],['下个月 1 号',nm1()]];if(sug)quick.push(['建议',new Date(sug+'T12:00:00')]);
    function render(){var first=new Date(vy,vm,1,12),start=(first.getDay()+6)%7,days=new Date(vy,vm+1,0).getDate(),h='';
      h+='<div class="pk-h"><b>选出发日期</b><button type="button" class="pk-x" aria-label="关上">关上</button></div>';
      h+='<div class="pk-q">'+quick.map(function(q,i){return'<button type="button" data-q="'+i+'" '+(iso(q[1])<min?'disabled':'')+'>'+q[0]+'<small>'+(q[1].getMonth()+1)+'/'+q[1].getDate()+'</small></button>'}).join('')+'</div>';
      h+='<div class="pk-m"><button type="button" class="pk-p" aria-label="上个月">‹</button><b>'+vy+' 年 '+(vm+1)+' 月</b><button type="button" class="pk-n" aria-label="下个月">›</button></div>'+((vy!==nowY||vm!==nowM)?'<p class="pk-jump"><button type="button" class="pk-j" data-jump="1">回到今天所在的月</button></p>':'');
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
      if(b.classList.contains('pk-x'))return close();if(b.classList.contains('pk-p')){vm--;if(vm<0){vm=11;vy--}return render()}if(b.classList.contains('pk-n')){vm++;if(vm>11){vm=0;vy++}return render()}if(b.dataset.jump){vy=nowY;vm=nowM;return render()}
      if(b.dataset.v)return pick(b.dataset.v);if(b.dataset.q)return pick(iso(quick[+b.dataset.q][1]))});
    mask.addEventListener('click',close);document.addEventListener('keydown',function k(e){if(e.key==='Escape'){close();document.removeEventListener('keydown',k)}});
    render();document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open');var f=sh.querySelector('.pk-g .on')||sh.querySelector('.pk-g button:not([disabled])');if(f)f.focus()}
  var now=new Date();
  document.querySelectorAll('.sun').forEach(function(b){var d=b.dataset.date?new Date(b.dataset.date+'T12:00:00'):now;var v=sun(+b.dataset.lat,+b.dataset.lng,d,b.dataset.k==='rise',parseFloat(b.dataset.tz),b.dataset.dst);b.textContent=v;if(b.parentNode)b.parentNode.hidden=(v==='—'||b.dataset.off==='1')});   // 算不出来（极昼极夜）或这天的位置不可靠（长线）：整格不显示，不留“—”

  // ——— 返回：从本站点进来的就退回上一页（筛选和滚动位置都还在） ———
  // 返回：记住这次在站内走过的页面；有上一页就退回上一页，没有（直接打开的）就回首页
  var H=[];try{H=JSON.parse(sessionStorage.getItem('zouni_hist')||'[]')}catch(e){}
  var here=location.pathname;if(H.length>=2&&H[H.length-2]===here)H.pop();else if(H[H.length-1]!==here)H.push(here);H=H.slice(-30);
  try{sessionStorage.setItem('zouni_hist',JSON.stringify(H))}catch(e){}
  document.querySelectorAll('a.back').forEach(function(a){a.addEventListener('click',function(e){e.preventDefault();if(H.length>=2&&history.length>1){history.back()}else{location.href='/'}})});
  // ——— 出发地（首页“替我挑”里选的，或者定位）：怎么去、首页封面都按它来 ———
  var ZORIG={'北京':[39.90,116.40],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'成都':[30.66,104.07],'杭州':[30.27,120.16],'西安':[34.26,108.94],'武汉':[30.59,114.31],'南京':[32.06,118.80],'重庆':[29.56,106.55],'长沙':[28.23,112.94],'兰州':[36.06,103.83],'哈尔滨':[45.80,126.53],'乌鲁木齐':[43.83,87.62],'南宁':[22.82,108.32],'贵阳':[26.65,106.63],'呼和浩特':[40.84,111.75],'银川':[38.49,106.23],'西宁':[36.62,101.78],'海口':[20.04,110.20],'石家庄':[38.04,114.51],'济南':[36.65,117.00],'福州':[26.07,119.30],'南昌':[28.68,115.86],'合肥':[31.82,117.23],'太原':[37.87,112.55],'长春':[43.82,125.32],'大连':[38.91,121.61],'宁波':[29.87,121.54],'郑州':[34.75,113.63],'天津':[39.13,117.20],'苏州':[31.30,120.58],'厦门':[24.48,118.09],'昆明':[25.04,102.71],'沈阳':[41.80,123.43],'青岛':[36.07,120.38],'香港':[22.32,114.17]};
  function zOrigin(){try{var st=JSON.parse(localStorage.getItem('zouni_pick')||'{}');if(st.o==='here'&&st.lat)return{n:'你这里',lat:st.lat,lng:st.lng};var o=st.o||localStorage.getItem('zouni_org');if(o&&ZORIG[o])return{n:o,lat:ZORIG[o][0],lng:ZORIG[o][1]}}catch(e){}return null}
  function zKm(a,b,c,d){var r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
  function zGoWay(g,o,km){if(km<60)return'就在'+o+'附近，当天过去就行';if(+g.ab&&g.dst==='peru')return'从'+o+'坐飞机，要转一到两次机，路上总共 30 小时左右';if(+g.ab&&km>5000&&['norway','croatia','iceland','morocco','mexico','canada','ireland','southafrica'].indexOf(g.dst)>=0)return'从'+o+'坐飞机，要转一次机，路上总共约 '+Math.max(1,Math.round(km/750+3))+' 小时';if(+g.ab&&km>5000)return'从'+o+'坐飞机，约 '+Math.max(1,Math.round(km/750+1))+' 小时';if(+g.ab)return'从'+o+'坐飞机，约 '+Math.max(1,Math.round(km/700+1))+' 小时';if(+g.drv)return'从'+o+'开过去约 '+Math.max(1,Math.round(km*1.25/80))+' 小时；也可以坐高铁或飞机到了再租车';if(+g.isl&&km>250)return'从'+o+'坐飞机，约 '+Math.max(1,Math.round(km/700+1))+' 小时';if(+g.nh&&km>900)return'从'+o+'坐飞机，约 '+Math.max(1,Math.round(km/700+1))+' 小时';if(+g.nh&&km>250)return'从'+o+'坐火车约 '+Math.max(2,Math.round(km*1.25/90))+' 小时，或者坐飞机';if(+g.car&&km<=600)return'从'+o+'坐车约 '+Math.max(1,Math.round(km*1.3/70))+' 小时，包车或坐大巴';if(km<=1200)return'从'+o+'坐高铁约 '+Math.max(1,Math.round(km/230+0.5))+' 小时';return'从'+o+'坐飞机最省事，飞行约 '+Math.max(1,Math.round(km/700+1))+' 小时'}
  // ——— 使用统计：只记“做了什么”（改日期、加一天、分享……），不记人；没配统计地址时什么都不发 ———
  var ZSTATS=(document.querySelector('meta[name="zouni-stats"]')||{}).content||'';
  function ztrack(ev,props){try{var d={e:ev,p:location.pathname,t:Date.now()};if(props)d.x=props;(window.__zq=window.__zq||[]).push(d);if(window.gtag)window.gtag('event',ev,props||{});if(ZSTATS&&navigator.sendBeacon)navigator.sendBeacon(ZSTATS,JSON.stringify(d))}catch(e){}}
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
  // ——— 微信里打不开高德、携程等 App：景点和酒店名旁边放一个“复制”，复制“城市 + 名字”，去别的 App 里粘贴搜索 ———
  // 剪贴板不能用时（微信 X5 内核里 prompt() 可能不弹）：页面里弹一个选中好的文本框，长按复制
  function zCopyBox(txt,title){var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';sh.setAttribute('role','dialog');
    sh.innerHTML='<div class="pk-h"><b>'+title+'</b><button type="button" class="pk-x">关上</button></div><p class="xnote">长按下面的文字，选“复制”</p><textarea class="cpbox" readonly rows="3"></textarea>';
    var ta=sh.querySelector('textarea');ta.value=txt;document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open');
    try{ta.focus();ta.select();ta.setSelectionRange(0,txt.length)}catch(e){}
    function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}sh.querySelector('.pk-x').addEventListener('click',cl);mask.addEventListener('click',cl)}
  function zCopy(txt,msg){var done=function(){if(typeof toast==='function')toast(msg)},fail=function(){zCopyBox(txt,'复制这个名字')};try{navigator.clipboard.writeText(txt).then(done,fail)}catch(e){fail()}}   // 剪贴板被拒绝时弹出让用户自己复制，不说“已复制”
  window.zAddCopy=function(){if(!document.documentElement.classList.contains('wx'))return;[].slice.call(document.querySelectorAll('.tl > li.r.see .m, .tl > li.r.fun .m, .tl > li.r.stay .m, .stays .tg')).forEach(function(m){if(m.querySelector('.cpy'))return;if(m.classList.contains('tg')&&!(m.parentNode&&m.parentNode.querySelector('.tl2')))return;var b=document.createElement('button');b.type='button';b.className='cpy';b.setAttribute('aria-label','复制名字');b.textContent='复制';m.appendChild(b)})};
  if(WXB){document.documentElement.classList.add('wx');window.zAddCopy()}
  document.addEventListener('click',function(e){var b=e.target.closest('.cpy');if(!b)return;e.preventDefault();var m=b.parentNode,nm=(m.childNodes[0]&&m.childNodes[0].textContent||'').replace(/^住\s*·\s*/,'').split(/\s*[·（(]/)[0].trim(),dy=b.closest('.day'),ct=dy&&dy.dataset.city||'';   // 去掉“ · 傍晚”“（…）”这类修饰，粘贴到高德才搜得到
    var own=[].slice.call(document.querySelectorAll('.day[data-city]')).some(function(x){var c=x.dataset.city;return c&&nm.indexOf(c)===0}),txt=(ct&&nm.indexOf(ct)<0&&!own?ct+' ':'')+nm;zCopy(txt,'已复制「'+txt+'」，到高德或小红书里粘贴搜索')});
  document.addEventListener('click',function(e){var a=e.target.closest('a.tl2,.stays .bk a.btn');if(!a||!MOB||WXB)return;   // 订酒店：在携程 App 里打开这家
    e.preventDefault();try{zOpen('ctrip://wireless/h5?url='+btoa(a.href)+'&type=2','携程旅行')}catch(x){}});

  // ——— 每天末尾“下一天 ›”：读完一天直接去下一天（去掉、加一天以后重新算） ———
  function zStay(){var p=document.querySelector('.ovstay');if(!p)return;var ds=[].slice.call(document.querySelectorAll('.day')).filter(function(d){return !d.hidden&&d.offsetParent!==null}),seq=[];   // 去掉、加一天以后重算“住哪、住几晚”
    ds.slice(0,-1).forEach(function(d){var c=d.dataset.stay||d.dataset.city||'';if(!c)return;if(seq.length&&seq[seq.length-1][0]===c)seq[seq.length-1][1]++;else seq.push([c,1])});
    p.hidden=seq.length<3;if(seq.length>=3)p.textContent='住：'+seq.map(function(x){return x[0]+' '+x[1]+' 晚'}).join(' → ')}
  function zNext(){zStay();var ds=[].slice.call(document.querySelectorAll('.day')).filter(function(d){return !d.hidden&&d.offsetParent!==null});
    document.querySelectorAll('.nextday').forEach(function(a){a.remove()});
    }
  if(document.querySelector('.day')){setTimeout(zNext,60);document.addEventListener('click',function(e){if(e.target.closest('.rmday,.addday,.adayok,.restore,.ovrestore,[data-addday]'))setTimeout(zNext,400)})}

  // ——— 行程页 ———
  var art=document.querySelector('article.trip');
  if(art){
    var me={id:art.dataset.id,label:art.dataset.label,title:art.dataset.title};
    // 每天底部“去掉这一天”和“这天后面加一天”放在同一行（.dayact）；first=true 的放左边
    var priceHook=function(){retitle()};     // 天数变了（去掉、加一天）时重算价格和标题里的天数（没有费用明细的线只改标题）
    function dayAct(sec,h,first){var r=null,i;for(i=0;i<sec.children.length;i++)if(sec.children[i].className==='dayact')r=sec.children[i];if(!r){r=document.createElement('div');r.className='dayact';sec.appendChild(r)}r.insertAdjacentHTML(first?'afterbegin':'beforeend',h)}
    var MYKEYS=['zouni_start_','zouni_st_','zouni_drop_','zouni_adj_','zouni_extra_','zouni_slow_','zouni_n_','zouni_rain_','zouni_fill_','zouni_rmday_','zouni_np_'];

    // ——— 分享链接编码：把所有修改打成一个很短的字符串放在 # 后面 ———
    // 新格式 #m=<压缩串>（短键名 + LZ 压缩，中文多的状态比旧的 base64 短 40–60%）；旧格式 #mine=<base64 的 JSON> 仍然能打开
    var SHORTK=['a','b','c','d','e','f','g','h','i','j','k'],LZAL='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_';
    function lzC(s){var dict={},create={},w='',wc,c,enl=2,dsz=3,nb=2,out=[],val=0,pos=0,i,has=Object.prototype.hasOwnProperty;
      function wr(v,n){for(var k=0;k<n;k++){val=(val<<1)|(v&1);v>>=1;if(pos===5){out.push(LZAL.charAt(val));val=0;pos=0}else pos++}}
      function bump(){enl--;if(enl===0){enl=Math.pow(2,nb);nb++}}
      function emit(x){if(has.call(create,x)){var cc=x.charCodeAt(0);if(cc<256){wr(0,nb);wr(cc,8)}else{wr(1,nb);wr(cc,16)}bump();delete create[x]}else wr(dict[x],nb);bump()}
      for(i=0;i<s.length;i++){c=s.charAt(i);if(!has.call(dict,c)){dict[c]=dsz++;create[c]=true}wc=w+c;if(has.call(dict,wc))w=wc;else{emit(w);dict[wc]=dsz++;w=c}}
      if(w!=='')emit(w);wr(2,nb);while(true){val=val<<1;if(pos===5){out.push(LZAL.charAt(val));break}else pos++}return out.join('')}
    function lzD(str){var rev={},i,n=str.length,ix=0,bitv=0,bp=0;for(i=0;i<LZAL.length;i++)rev[LZAL.charAt(i)]=i;
      function rb(k){var v=0,p=1,b;while(k--){if(bp===0){if(ix>=n)throw new Error('eof');bitv=rev[str.charAt(ix++)];if(bitv==null)throw new Error('bad');bp=32}b=bitv&bp;bp>>=1;if(b>0)v|=p;p<<=1}return v}
      var dict=[],enl=4,dsz=4,nb=3,res=[],w,c,entry,next;for(i=0;i<3;i++)dict[i]=i;next=rb(2);
      if(next===0)c=String.fromCharCode(rb(8));else if(next===1)c=String.fromCharCode(rb(16));else return'';
      dict[3]=c;w=c;res.push(c);
      while(true){next=rb(nb);
        if(next===0){dict[dsz++]=String.fromCharCode(rb(8));next=dsz-1;enl--}else if(next===1){dict[dsz++]=String.fromCharCode(rb(16));next=dsz-1;enl--}else if(next===2)return res.join('');
        if(enl===0){enl=Math.pow(2,nb);nb++}
        if(dict[next])entry=dict[next];else if(next===dsz)entry=w+w.charAt(0);else throw new Error('bad');
        res.push(entry);dict[dsz++]=w+entry.charAt(0);enl--;w=entry;if(enl===0){enl=Math.pow(2,nb);nb++}}}
    function linkEnc(o){var a=btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''),sm={};MYKEYS.forEach(function(k,i){if(o[k]!=null)sm[SHORTK[i]]=o[k]});var z='';try{z=lzC(JSON.stringify(sm))}catch(e){}return(z&&z.length+2<a.length+5)?'#m='+z:'#mine='+a}
    function linkDec(h){var m=/#m=([A-Za-z0-9_\-]+)/.exec(h),o={};if(m){var sm=JSON.parse(lzD(m[1]));MYKEYS.forEach(function(k,i){if(sm[SHORTK[i]]!=null)o[k]=sm[SHORTK[i]]});return o}
      m=/#mine=([A-Za-z0-9_\-]+)/.exec(h);if(m)return JSON.parse(decodeURIComponent(escape(atob(m[1].replace(/-/g,'+').replace(/_/g,'/')))));return null}
    window.zLink={enc:linkEnc,dec:linkDec,lzC:lzC,lzD:lzD};
    try{var st_=linkDec(location.hash);if(st_){
      var bk_={},had_=false,diff_=false,bkT_=localStorage.getItem('zouni_startt_'+me.id);MYKEYS.forEach(function(k){var o=localStorage.getItem(k+me.id);bk_[k]=o;if(o!=null&&o!==''&&o!=='{}'&&o!=='[]'){had_=true;var nv=st_[k]==null?null:(typeof st_[k]==='string'?st_[k]:JSON.stringify(st_[k]));if(nv!==o)diff_=true}});   // 先把自己本地的改动备份下来，朋友的版本盖上去之后还能撤销
      MYKEYS.forEach(function(k){var v=st_[k];if(v==null)localStorage.removeItem(k+me.id);else localStorage.setItem(k+me.id,typeof v==='string'?v:JSON.stringify(v))});
      if(st_['zouni_start_']!=null)localStorage.setItem('zouni_startt_'+me.id,String(Date.now()));   // 朋友给的日期算“刚选的”，比首页旧日期新
      history.replaceState(null,'',location.pathname);
      setTimeout(function(){if(!(had_&&diff_)){toast('打开的是朋友改过的版本');return}
        toast('已载入朋友分享的版本','换回我自己的',function(){MYKEYS.forEach(function(k){try{if(bk_[k]==null)localStorage.removeItem(k+me.id);else localStorage.setItem(k+me.id,bk_[k])}catch(e){}});try{if(bkT_==null)localStorage.removeItem('zouni_startt_'+me.id);else localStorage.setItem('zouni_startt_'+me.id,bkT_)}catch(e){}location.reload()},8000)},600)}}catch(e){}
    var RDK='zouni_rmday_'+me.id,RD=[];try{RD=JSON.parse(localStorage.getItem(RDK)||'[]')}catch(e){}
    (function(){var secs=[].slice.call(document.querySelectorAll('.day')),ovl=[].slice.call(document.querySelectorAll('.overview ol > li'));
      secs.forEach(function(s,i){if(s.dataset.oi==null)s.dataset.oi=i});ovl.forEach(function(li,i){if(li.dataset.oi==null)li.dataset.oi=i});
      if(RD.length>=secs.length)RD=[];var gone=[],backRow=null;
      function stayOf(s){var m=s.querySelector('.r.stay .m');return m?m.textContent.replace(/\s+/g,'').replace(/^住·/,''):''}
      // 每天换住处的线（搬家日）：去掉中间一天，前后两天就接不上了，确认框里要说一声
      function moveHit(sec){var all=[].slice.call(document.querySelectorAll('.day')),i=all.indexOf(sec);if(i<=0||i>=all.length-1)return'';var a=stayOf(all[i-1]),b=stayOf(sec);return(a&&b&&a!==b)?'<br>这条线每天换住处，去掉这一天后前后两天可能接不上（路程、住处会对不上），建议只去掉“原地住”的天。':''}
      secs.forEach(function(s,i){if(RD.indexOf(+s.dataset.oi)<0)return;var st=s.querySelector('.stays');
        if(st){var nx=secs[i+1];if(nx&&RD.indexOf(+nx.dataset.oi)<0&&!nx.querySelector('.stays')&&stayOf(nx)===stayOf(s)){var tl2=nx.querySelector('.tl');if(tl2)tl2.parentNode.insertBefore(st,tl2.nextSibling)}}   // 去掉的那天带着住宿卡，而第二天还住同一处：卡片挪到第二天
        gone.push({oi:+s.dataset.oi,t:(s.querySelector('h2').childNodes[0]||{textContent:''}).textContent.trim()});
        if(i===secs.length-1){var bd_=[].slice.call(s.querySelectorAll('.tl > .r.dep')).pop();if(bd_&&/回程|回家|返程/.test(bd_.innerText))backRow=bd_.cloneNode(true)}s.remove()});
      // “连住 N 晚”按剩下的天重算
      var lf=[].slice.call(document.querySelectorAll('.day'));lf.forEach(function(s,i){var st=s.querySelector('.stays');if(!st)return;var sp=st.querySelector('.sh span:last-child');if(!sp)return;var me0=stayOf(s),k=i,nn=0;
        while(k<lf.length-1&&stayOf(lf[k])===me0&&me0){nn++;k++}var base0=sp.textContent.replace(/(^|\s*·\s*)连住\s*\d+\s*晚/g,'').trim();sp.textContent=base0+(nn>1?(base0?' · ':'')+'连住 '+nn+' 晚':'')});
      ovl.forEach(function(li){if(RD.indexOf(+li.dataset.oi)>=0)li.remove()});
      var left=[].slice.call(document.querySelectorAll('.day')),CN='一二三四五六七八九十';
      // 去掉的是最后一天：新的最后一天要变成“回家那天”——不再有“住”和“出发 → 住处”，补上原来最后一天的“出发 → 回程”，总览里写“回家”
      if(backRow&&left.length&&left[left.length-1].dataset.oi!==String(secs.length-1)){var nl=left[left.length-1],ntl=nl.querySelector('.tl');
        if(ntl){var sr=ntl.querySelector(':scope > .r.stay');if(sr)sr.remove();var rs0=[].slice.call(ntl.querySelectorAll(':scope > .r')),lr=rs0[rs0.length-1];if(lr&&lr.classList.contains('dep')&&/住处/.test(lr.innerText)){lr.remove();rs0.pop()}
          var mx=-1;rs0.forEach(function(r){var t=(r.querySelector('time')||{}).textContent||'',m=/^(\d\d):(\d\d)$/.exec(t);if(m&&+m[1]*60+ +m[2]>mx)mx=+m[1]*60+ +m[2]});
          if(mx>=0){var tt=Math.min(mx+60,23*60+30);backRow.querySelector('time').textContent=('0'+Math.floor(tt/60)).slice(-2)+':'+('0'+tt%60).slice(-2)}backRow.setAttribute('data-back','1');ntl.appendChild(backRow)}
        var nst=nl.querySelector('.stays');if(nst)nst.remove();
        var oli=document.querySelectorAll('.overview ol > li');var ol_=oli[oli.length-1],osm=ol_&&ol_.querySelector('.ot small');if(osm&&osm.textContent!=='回家')osm.textContent='回家'}
      if(gone.length){left.forEach(function(s,i){s.id='d'+(i+1);var no=s.querySelector('.no');if(no)no.textContent=('0'+(i+1)).slice(-2);var sm=s.querySelector('header small');if(sm){var p=sm.textContent.split(' · ');sm.textContent='第'+(i<10?CN[i]:(i+1))+'天'+(p.length>1?' · '+p.slice(1).join(' · '):'')}});
        [].slice.call(document.querySelectorAll('.overview ol > li')).forEach(function(li,i){var a=li.querySelector('a');if(a)a.setAttribute('href','#d'+(i+1));var b=li.querySelector('b');if(b)b.textContent=('0'+(i+1)).slice(-2)});
        var nv=document.querySelector('.daynav');if(nv){var as=nv.querySelectorAll('a');for(var k=as.length-1;k>=left.length;k--)as[k].remove();[].slice.call(nv.querySelectorAll('a')).forEach(function(a,i){a.setAttribute('href','#d'+(i+1));a.textContent=i+1})}
        var oh=document.querySelector('.overview h2');if(oh)oh.textContent=left.length+' 天，怎么排';var gb=document.querySelector('.glance b.big');if(gb&&gb.firstChild)gb.firstChild.textContent=left.length;
        var ov=document.querySelector('.overview ol');if(ov)ov.insertAdjacentHTML('afterend','<p class="rmnote">去掉了'+gone.map(function(g){return'「'+g.t+'」'}).join('')+' <button type="button" class="rmback">恢复</button></p>');
        var rb=document.querySelector('.rmback');if(rb)rb.addEventListener('click',function(){try{localStorage.removeItem(RDK)}catch(e){}location.reload()})}
      left.forEach(function(s){if(s.dataset.extra||s.querySelector('.rmorig'))return;if(left.length<2)return;dayAct(s,'<button type="button" class="rmday rmorig">去掉这一天</button>',true)});
      document.addEventListener('click',function(e){var b=e.target.closest('.rmorig');if(!b)return;var s=b.closest('.day'),t=(s.querySelector('h2').childNodes[0]||{textContent:''}).textContent.trim();
        var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
        sh.innerHTML='<div class="pk-h"><b>去掉这一天？</b><button type="button" class="pk-x">算了</button></div><p class="xnote">「'+t+'」整天不去了，后面的天往前挪一天；之后在“怎么排”下面可以恢复</p><p class="xnote">价格和标题里的天数会按剩下的天数改（价格是估的参考价）。'+titleHit(s)+moveHit(s)+'</p><div class="xd"><button type="button" class="rmgo"><b>去掉这一天</b></button></div>';
        function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
        sh.querySelector('.pk-x').addEventListener('click',cl);mask.addEventListener('click',cl);
        sh.querySelector('.rmgo').addEventListener('click',function(){var R2=[];try{R2=JSON.parse(localStorage.getItem(RDK)||'[]')}catch(e){}R2.push(+s.dataset.oi);try{localStorage.setItem(RDK,JSON.stringify(R2));sessionStorage.setItem('zouni_rm_toast',t)}catch(e){}location.reload()});
        document.body.appendChild(mask);document.body.appendChild(sh);document.body.classList.add('pk-open')});
      try{var tt=sessionStorage.getItem('zouni_rm_toast');if(tt){sessionStorage.removeItem('zouni_rm_toast');setTimeout(function(){toast('去掉了「'+tt+'」，后面的天往前挪了','撤销',function(){try{localStorage.removeItem(RDK)}catch(e){}location.reload()})},500)}}catch(e){}})();
    function myState(){var o={},any=false;MYKEYS.forEach(function(k){var v=null;try{v=localStorage.getItem(k+me.id)}catch(e){}if(v!=null&&v!==''&&v!=='{}'&&v!=='[]'){any=true;try{o[k]=JSON.parse(v)}catch(e){o[k]=v}}});
      var dk_=document.querySelector('.dpk');if(dk_&&dk_.value&&window.zDateChosen&&window.zDateChosen()){o['zouni_start_']=dk_.value;any=true}   // 日期是首页选的（这条线自己没存）也要带上，朋友打开才一致
      return any?o:null}
    function myLink(){var o=myState(),u0=location.origin+location.pathname;if(!o)return u0;return u0+linkEnc(o)}
    var seen=ld('zouni_seen').filter(function(x){return x.id!==me.id});seen.unshift(me);sv('zouni_seen',seen.slice(0,8));
    // 天数写在好几个地方：页头小标（城市慢游 · 三天）、大标题（三天，在西安看一千年）、<title>、收藏和最近看过里的名字和副标题——天数变了（去掉、加一天）要一起改
    var T0=document.title,K0=(document.querySelector('.hero .kick')||{}).textContent;
    function cnN(dn){return dn<=10?'零一二三四五六七八九十'.charAt(dn):String(dn)}
    function numFix(txt,dn,asCn){var m=/([一二三四五六七八九十]+|\d+)(\s*)天/.exec(txt);if(!m)return txt;return txt.slice(0,m.index)+(asCn?cnN(dn):dn)+m[2]+'天'+txt.slice(m.index+m[0].length)}
    function retitle(){var n0=+art.dataset.n0||0,dn=document.querySelectorAll('.day').length,h=document.querySelector('.hero-t h1');if(!h||!n0)return;
      var kk=document.querySelector('.hero .kick');if(kk&&K0){var cn_=/[一二三四五六七八九十]/.test((/([一二三四五六七八九十]+|\d+)\s*天/.exec(K0)||[])[1]||'');kk.textContent=dn===n0?K0:numFix(K0,dn,cn_)}   // 页头小标：“城市慢游 · 三天”
      if(dn===n0)document.title=T0;else document.title=T0.replace(/(\d+)(\s*天行程)/,dn+'$2').replace(/：([一二三四五六七八九十]+|\d+)(\s*)天/,'：'+cnN(dn)+'$2天');   // <title>：“西安 3 天行程：三天，…”
      var lab=(me.label||'').replace(/\d+(\s*天)/,dn+'$1'),ttl=me.title&&dn<=10?me.title.replace(/^[一二三四五六七八九十]+天/,cnN(dn)+'天'):me.title;
      if(!art._me0)art._me0={label:me.label,title:me.title};if(dn===n0){lab=art._me0.label;ttl=art._me0.title}
      me.label=lab;me.title=ttl;
      ['zouni_fav','zouni_seen'].forEach(function(k){try{var fv_=JSON.parse(localStorage.getItem(k)||'[]'),ch_=false;fv_.forEach(function(x){if(x.id===me.id&&(x.label!==lab||x.title!==ttl)){x.label=lab;x.title=ttl;ch_=true}});if(ch_)localStorage.setItem(k,JSON.stringify(fv_))}catch(e){}});   // 收藏、最近看过里的名字和副标题跟着改
      var w=cnN(dn),it=document.createTreeWalker(h,NodeFilter.SHOW_TEXT,null,false),nd;
      while((nd=it.nextNode())){var m=/^([一二三四五六七八九十]+|\d+)(\s*)天/.exec(nd.nodeValue);if(m){nd.nodeValue=(/[一二三四五六七八九十]/.test(m[1])&&dn<=10?w:String(dn))+m[2]+'天'+nd.nodeValue.slice(m[0].length);break}}}
    retitle();
    // 几个人去
    var p=document.querySelector('.price[data-cost]'),pp=document.querySelector('.pp'),box=document.querySelector('.ppl');
    if(p&&p.dataset.cost&&box){var C=JSON.parse(p.dataset.cost),N=2;try{var n0=+localStorage.getItem('zouni_n_'+me.id);if(n0>=1&&n0<=12)N=n0}catch(e){}
      function upd(){var n0=+art.dataset.n0||0,dn=document.querySelectorAll('.day').length,rd=(n0>0&&dn>0)?dn/n0:1,rn=n0>1?Math.max(dn-1,0)/(n0-1):1;   // 天数变了：吃、门票、车按天数比例，住宿按晚数，大交通不变（参考价）
        var rooms=Math.ceil(N/2),car=C.perCar?Math.ceil(N/4)*C.carTotal/N:C.tollsPP,lodge=C.lodgeRoom*rooms/N,loc=(C.tixPP+C.foodPP+car)*rd+lodge*rn,r=function(v){var k=Math.round(v/100)/10;return(k<100?(+k.toFixed(1)).toString():Math.round(k).toString())};p.textContent='¥'+r(loc+C.trans[0])+'K–'+r(loc+C.trans[1])+'K';box.querySelector('b').textContent=N+' 人';pp.textContent=N+' 人 · 每人 '+(box.hidden?'›':'▴');var ds=document.querySelector('.dock small');if(ds)ds.textContent=N+' 人 · 每人 '+p.textContent;try{if(N!==2)localStorage.setItem('zouni_n_'+me.id,N);else localStorage.removeItem('zouni_n_'+me.id)}catch(e){}}
      function tog(){box.hidden=!box.hidden;upd()}
      pp.addEventListener('click',tog);p.addEventListener('click',tog);
      box.querySelectorAll('button').forEach(function(x){x.addEventListener('click',function(){N=Math.max(1,Math.min(6,N+(+x.dataset.d)));upd()})});
      priceHook=function(){upd();retitle()};
      if(N!==2||document.querySelectorAll('.day').length!==(+art.dataset.n0||0))upd()}   // 记住的人数、去掉过的天，一打开就算上（原来要点一下才更新，刷新后看起来像没记住）
    // 去掉的这一天里有没有标题点名的景点：有就提醒一句，免得去掉重头戏还以为是原来那条线
    function titleHit(sec){var ti=(me.title||'').replace(/^[一二三四五六七八九十\d]+\s*天[，,、：:]?/,''),tx=((sec.querySelector('h2')||{}).textContent||'')+((sec.querySelector('.lead')||{}).textContent||''),stop='的和与在去看赶一二三四五六七八九十场天玩逛住游到走吃里上下中',i,bg;
      for(i=0;i<ti.length-1;i++){bg=ti.substr(i,2);if(/[\u4e00-\u9fa5]{2}/.test(bg)&&stop.indexOf(bg[0])<0&&stop.indexOf(bg[1])<0&&tx.indexOf(bg)>=0)return'这一天讲到了标题里的「'+bg+'」，去掉后这条线可能就和标题对不上了。'}return''}
    // 出发前打勾
    var pk='zouni_prep_'+me.id,done=ld(pk);
    document.querySelectorAll('.pre input[type=checkbox]').forEach(function(x){x.checked=done.indexOf(+x.dataset.k)>=0;x.addEventListener('change',function(){var d=ld(pk).filter(function(k){return k!==+x.dataset.k});if(x.checked)d.push(+x.dataset.k);sv(pk,d)})});
    // 收进行程
    var fb=document.querySelector('.fav');
    // 收进行程 = 顺便把这一页和它用到的样式、脚本、图存进手机（和 sw.js 同一个缓存名），没网也能打开
    function saveOffline(cb){if(!window.caches){if(cb)cb(false);return}var urls=[location.pathname];try{[].slice.call(performance.getEntriesByType('resource')).forEach(function(e){var u=new URL(e.name);if(u.origin===location.origin&&/\.(css|js|svg|png|woff2?|webp|jpg)$/.test(u.pathname)&&urls.indexOf(u.pathname+u.search)<0)urls.push(u.pathname+u.search)})}catch(e){}
      caches.open('zouni-v3').then(function(c){return Promise.all(urls.slice(0,90).map(function(u,i){return(i?c.match(u).then(function(m){return m||c.add(u)}):c.add(u)).catch(function(){})}))}).then(function(){if(cb)cb(true)},function(){if(cb)cb(false)})}
    function paint(){var on=ld('zouni_fav').some(function(x){return x.id===me.id});fb.classList.toggle('on',on);if(!on)fb.classList.remove('saved');else if(window.caches)caches.match(location.pathname).then(function(m){fb.classList.toggle('saved',!!m)},function(){});var sp=fb.querySelector('span');if(sp)sp.textContent=on?'已收进':'收进行程';else fb.textContent=on?'已收进':'收进行程'}
    if(fb){paint();fb.addEventListener('click',function(){var f=ld('zouni_fav'),on=f.some(function(x){return x.id===me.id});var me2={},kk_;for(kk_ in me)me2[kk_]=me[kk_];var dn2=document.querySelectorAll('.day').length;if(me2.label)me2.label=me2.label.replace(/\d+(\s*天)/,dn2+'$1');me2.n=dn2;me2.sd=art.dataset.start||'';if(me2.title&&dn2<=10)me2.title=me2.title.replace(/^[一二三四五六七八九十]+天/,'零一二三四五六七八九十'.charAt(dn2)+'天');f=on?f.filter(function(x){return x.id!==me.id}):[me2].concat(f);sv('zouni_fav',f);paint();if(on)toast('已从我的行程里拿掉','撤销',function(){var f2=ld('zouni_fav').filter(function(x){return x.id!==me.id});f2=[me2].concat(f2);sv('zouni_fav',f2);paint()});else{toast('已收进，可在首页「我的行程」查看');saveOffline(function(ok){if(!ok)return;fb.classList.add('saved');if(ld('zouni_fav').some(function(x){return x.id===me.id}))toast('已存到手机里，没网也能看')})}})}
    // 分享、复制
    // 分享链接：剪贴板被拒绝（微信、iOS 常见）时不能说“已复制”，改成弹出让用户自己复制
    function shareLink(){var u=myLink();if(navigator.share){navigator.share({title:document.title,url:u}).catch(function(){})}else{try{navigator.clipboard.writeText(u).then(function(){toast('链接已复制')},function(){zCopyBox(u,'复制这个链接')})}catch(e){zCopyBox(u,'复制这个链接')}}}
    var sh=document.querySelector('.share');if(sh)sh.addEventListener('click',function(){var mask=document.createElement('div');mask.className='pk-mask';var s2=document.createElement('div');s2.className='pk';
      s2.innerHTML='<div class="pk-h"><b>分享</b><button type="button" class="pk-x">关上</button></div><div class="xd"><button type="button" data-a="link"><b>发链接给朋友</b><small>'+(myState()?'带上你改过的日期、时间和加的天':'原版行程')+'</small></button><button type="button" data-a="copy"><b>复制整条行程</b><small>按天的时间和地点，可以直接粘贴到微信</small></button><button type="button" data-a="shot"><b>生成分享图</b><small>长按保存，发朋友圈</small></button><button type="button" data-a="print"><b>打印 / 存成 PDF</b><small>一页页的行程单，给家里人或者出门带着</small></button></div>';
      function cl(){mask.remove();s2.remove();document.body.classList.remove('pk-open')}
      s2.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;if(b.classList.contains('pk-x'))return cl();cl();if(b.dataset.a==='link')shareLink();if(b.dataset.a==='copy')copyTrip();if(b.dataset.a==='shot'){if(window.qrcode)shotTrip();else{var sc=document.createElement('script');sc.src='/assets/qr.js';sc.onload=shotTrip;sc.onerror=shotTrip;document.head.appendChild(sc)}}if(b.dataset.a==='print')setTimeout(function(){window.print()},300)});
      mask.addEventListener('click',cl);document.body.appendChild(mask);document.body.appendChild(s2);document.body.classList.add('pk-open')});
    // 复制整条行程：读的是“现在这一页”——去掉的站、加的天、顺路加的站、换的站都按现在的样子；带住处、预约入口、闭馆和提醒
    function cpT(el){return(el&&el.innerText||'').replace(/复制\s*$/,'').replace(/\s+/g,' ').trim()}
    function cpNoBtn(el){var c=el.cloneNode(true);[].slice.call(c.querySelectorAll('button')).forEach(function(b){b.remove()});return cpT(c)}
    function tripText(){var out=[cpT(document.querySelector('.hero h1')),myLink(),''],kk=document.querySelector('.dnote');
      var ds=document.querySelector('.dock b');if(ds)out.push(cpT(ds));if(kk)out.push(cpT(kk));
      var pre=[].slice.call(document.querySelectorAll('section.pre:not(.go) li')).map(function(li){var l=li.querySelector('a.bkl,a.bkn'),t=cpT(li.querySelector('span')||li);t=t.replace(/\s*官网预约\s*›?\s*$/,'');return t?'  · '+t+(l&&l.href?'（入口 '+l.href+'）':''):''}).filter(Boolean);
      if(pre.length){out.push('出发前要办的事：');pre.forEach(function(x){out.push(x)});out.push('')}
      [].slice.call(document.querySelectorAll('.day')).forEach(function(d,di,all){var hs=d.querySelector('header small'),h2=d.querySelector('h2');out.push(cpT(hs)+' · '+cpT(h2));
        [].slice.call(d.querySelectorAll('.fc.mon')).forEach(function(f){out.push('  提醒：'+cpT(f))});
        [].slice.call(d.querySelectorAll('.latewarn p')).forEach(function(f){if(f.classList.contains('sum')||f.classList.contains('gap'))return;var t=cpNoBtn(f);if(t)out.push('  提醒：'+t)});
        var ld=d.querySelector('.lead');if(!d.querySelector('.tl .r')&&ld)out.push('  '+cpT(ld));
        var rows=[].slice.call(d.querySelectorAll('.tl .r')).filter(function(r){return!r.hidden&&!r.closest('[hidden]')});
        rows.forEach(function(r){var tm=cpT(r.querySelector('time')),m=cpT(r.querySelector('.m')),ps=[].slice.call(r.querySelectorAll('.rb > p')).filter(function(p){return!p.classList.contains('m')}).map(cpNoBtn).filter(Boolean),l=r.querySelector('a.bkl,a.bkn');
          if(r.classList.contains('dep')){out.push('  '+tm+'  '+m+(ps.length?'（'+ps.join(' · ')+'）':''));return}
          out.push('  '+tm+'  '+m);ps.forEach(function(x){out.push('        '+x)});if(l&&l.href)out.push('        预约入口：'+l.href)});
        var sy=d.querySelector('.stays');if(sy){var lb=cpT(sy.querySelector('.sh')),rc=sy.querySelector('li .tg');out.push('        '+lb.replace(/^今晚住\s*/,'今晚住：')+(rc?'；'+cpT(sy.querySelector('li .tier'))+' '+cpT(rc):''))}
        else if(d.classList.contains('xday')&&!d.querySelector('.tl .r.stay')){var pv=all[di-1],nmS=d.dataset.city||(pv&&(pv.dataset.stay||pv.dataset.city))||'';out.push('  晚上  住 · '+(nmS||'原来的住处'))}   // 加的自由活动天没有时间表：晚上也要有地方住
        out.push('')});
      return out.join('\n')}
    function copyTrip(){var txt=tripText();try{navigator.clipboard.writeText(txt).then(function(){toast('行程已复制，可以直接粘贴到微信')},function(){zCopyBox(txt,'复制下面的行程')})}catch(e){zCopyBox(txt,'复制下面的行程')}}
    window.zTripText=tripText;
    // 改出发日期：日期、星期、日出日落、往年气温、底栏一起变；记在本机
    var dk=document.querySelector('.dpk'),dtb=document.querySelector('.dt');
    if(dk&&dtb){var sk='zouni_start_'+me.id,W='日一二三四五六';
      function fmt(d){return(d.getMonth()+1)+'/'+d.getDate()}
      function yp(d){return d.getFullYear()>(new Date()).getFullYear()?d.getFullYear()+' 年 ':''}     // 跨年时写完整年份（“2027 年 10/15”），不再写“明年”
      var isSugg=true,srcTxt='';     // isSugg：用户没选过日期，现在显示的是“按最佳季节的建议日期”；srcTxt：选的来源（首页 / 这条线）
      window.zDateChosen=function(){return!isSugg};
      function WD(d){return'周'+W[d.getDay()]}
      function noteTxt(d0){return isSugg?'建议 '+yp(d0)+fmt(d0)+' '+WD(d0)+' 出发（按最佳季节），点日期可改':'按你'+srcTxt+'选的 '+yp(d0)+fmt(d0)+' '+WD(d0)+' 出发排的，点日期可改'}
      function iso(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)}
      function applyStart(v){var d0=new Date(v+'T12:00:00'),secs=[].slice.call(document.querySelectorAll('.day')),n=secs.length;
        secs.forEach(function(sec,i){var di=new Date(d0.getTime()+i*864e5),sm=sec.querySelector('header small');sm.textContent=sm.textContent.split(' · ')[0]+' · '+fmt(di)+' 周'+W[di.getDay()];
          sec.querySelectorAll('.sun').forEach(function(b){b.dataset.date=iso(di);var v=sun(+b.dataset.lat,+b.dataset.lng,di,b.dataset.k==='rise',parseFloat(b.dataset.tz),b.dataset.dst);b.textContent=v;if(b.parentNode)b.parentNode.hidden=(v==='—'||b.dataset.off==='1')});
          var cl=sec.querySelector('.cl');if(cl&&cl.dataset.clim){var c=JSON.parse(cl.dataset.clim)[di.getMonth()+1];cl.textContent=c?('往年 '+(di.getMonth()+1)+' 月平均：白天 '+c[0]+'℃，夜里 '+c[1]+'℃'):''}});
        document.querySelectorAll('.overview i').forEach(function(x,i){x.textContent=fmt(new Date(d0.getTime()+i*864e5))});
        var dN=new Date(d0.getTime()+(n-1)*864e5);dtb.firstChild.textContent=fmt(d0)+(n>1?'–'+(dN.getMonth()===d0.getMonth()?dN.getDate():fmt(dN)):'')+' ';   // 同一个月写 10/15–17，窄屏不挤
        var db=document.querySelector('.dock b');if(db)db.textContent=(isSugg?'建议 ':'')+fmt(d0)+' 出发 · '+n+' 天';var dn_=document.querySelector('.dnote');if(dn_)dn_.textContent=noteTxt(d0)}
      dtb.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();dtb.click()}});
      dtb.addEventListener('click',function(){var b0=dtb.dataset.best?dtb.dataset.best.split(','):null;openPicker({value:dk.value,min:dk.dataset.min||dk.getAttribute('min'),best:b0&&b0.length===2?b0:null,sug:isSugg?dk.value:'',onPick:function(v){dk.value=v;dk.dispatchEvent(new Event('change'))}})});
      dk.addEventListener('change',function(){if(!dk.value)return;isSugg=false;srcTxt='';try{var t_=String(Date.now());localStorage.setItem(sk,dk.value);localStorage.setItem('zouni_startt_'+me.id,t_);localStorage.setItem('zouni_home_date',dk.value);localStorage.setItem('zouni_home_datet',t_)}catch(e){}applyStart(dk.value);var d=new Date(dk.value+'T12:00:00'),un=0;[].slice.call(document.querySelectorAll('.pre li')).forEach(function(li){var x=li.querySelector('input[type=checkbox]'),sp=li.querySelector('span');if(x&&x.checked&&sp&&/车票|机票|高铁票|火车票|船票|订票/.test(sp.textContent)){x.checked=false;x.dispatchEvent(new Event('change'));un++}});[].slice.call(document.querySelectorAll('.stays .mk.on')).forEach(function(b){b.click();un++});try{var TK_='zouni_todo_'+me.id,T_=JSON.parse(localStorage.getItem(TK_)||'[]'),T2_=T_.filter(function(k){return!/^go:/.test(k)});if(T2_.length!==T_.length){localStorage.setItem(TK_,JSON.stringify(T2_));un++}}catch(e){}toast('改成 '+fmt(d)+' 出发了'+(un?'；买票和订房的勾选清掉了，按新日期重新订':''))});
      var mn=dk.dataset.min||dk.min;
      // 出发日期只有一个说法：首页或任何一条线改过，所有线路页都按它；谁改得晚听谁的（旧数据没有时间戳 = 0，和以前一样“这条线自己存的优先”）
      try{var rv_=localStorage.getItem(sk),hv_=localStorage.getItem('zouni_home_date'),rt_=+localStorage.getItem('zouni_startt_'+me.id)||0,ht_=+localStorage.getItem('zouni_home_datet')||0;
        if(rv_&&rv_<mn)rv_=null;if(hv_&&hv_<mn)hv_=null;var ef_=null;
        if(rv_&&hv_)ef_=ht_>rt_?[hv_,'首页']:[rv_,''];else if(rv_)ef_=[rv_,''];else if(hv_)ef_=[hv_,'首页'];
        if(ef_){isSugg=false;srcTxt=ef_[1];if(ef_[0]!==dk.value)dk.value=ef_[0];applyStart(ef_[0])}}catch(e){}
      // 页面是静态生成的：没存过日期、默认日期已经过去时，按今天重新给一个——正当季落在“最好的日子”里（下一个周六），否则顺延一年
      function defStart(v,best){var t=new Date();t.setHours(12,0,0,0);var td=iso(t);if(v>=td)return v;var b=best?best.split(','):null,mons=(art.dataset.mon||'').split(',').filter(Boolean).map(Number),cls=(art.dataset.cl||'').split(',').filter(Boolean).map(function(z){var q=z.split(':');return[+q[0],+q[1]]});
        function fixMon(c,end){if(!mons.length&&!cls.length)return iso(c);var lo=new Date(t.getTime()+864e5),offs=[0],k,x;for(k=1;k<=12;k++)offs.push(k,-k);   // 有“周一闭馆”的去处：默认日期别让那一天落在周一
          for(k=0;k<offs.length;k++){x=new Date(c.getTime()+offs[k]*864e5);if(x<lo||(end&&x>end))continue;if(mons.every(function(i){return new Date(x.getTime()+i*864e5).getDay()!==1})&&cls.every(function(z){return new Date(x.getTime()+z[0]*864e5).getDay()!==z[1]}))return iso(x)}return iso(c)}
        if(b&&b.length===2){var md=td.slice(5),wrap=b[0]>b[1],inside=wrap?(md>=b[0]||md<=b[1]):(md>=b[0]&&md<=b[1]);
          if(inside){var c=new Date(t.getTime());c.setDate(c.getDate()+(6-c.getDay()+7)%7);if(c-t<2*864e5)c.setDate(c.getDate()+7);
            var end=new Date((t.getFullYear()+(wrap&&md>=b[0]?1:0))+'-'+b[1]+'T12:00:00');if(c>end)c=new Date(Math.max(t.getTime()+864e5,end.getTime()));return fixMon(c,end)}}
        var d=new Date(v+'T12:00:00');while(iso(d)<td)d.setFullYear(d.getFullYear()+1);return fixMon(d,null)}
      try{if(isSugg){var nv0=defStart(dk.value,dtb.dataset.best);if(nv0&&nv0!==dk.value){dk.value=nv0}}}catch(e){}
      applyStart(dk.value);   // 页面一打开就按“现在有几天、是建议日期还是你选的”把日期、天数、底栏写对
      // ——— 加一天：自由活动，或从同一目的地的其他线路挑一天接上；记在本机，可以去掉 ———
      var addB=document.querySelector('.addday .add');
      if(addB){var ek='zouni_extra_'+me.id,cands=[];try{cands=JSON.parse(document.getElementById('cands').textContent)}catch(e){}
        var CN='一二三四五六七八九十';function cnDay(i){return'第'+(i<10?CN[i]:(i+1))+'天'}
 var curE=null,pendAfter=null;function origDays(){return[].slice.call(document.querySelectorAll('.day:not(.xday)'))}   // pendAfter：点了某天下面的“这天后面加一天”，记下是第几天（原来的第几天）
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
        function renum(){setTimeout(function(){if(priceHook)priceHook();if(window.zAddCopy)window.zAddCopy()},0);var secs=[].slice.call(document.querySelectorAll('.day'));
          secs.forEach(function(sec,i){sec.id='d'+(i+1);var no=sec.querySelector('.no');if(no)no.textContent=('0'+(i+1)).slice(-2);var sm=sec.querySelector('header small');if(sm){var p=sm.textContent.split(' · ');sm.textContent=cnDay(i)+(p.length>1?' · '+p.slice(1).join(' · '):'')}});
          var nv=document.querySelector('.daynav');if(nv){var a=nv.querySelectorAll('a');for(var k=a.length;k<secs.length;k++)nv.insertAdjacentHTML('beforeend','<a href="#d'+(k+1)+'">'+(k+1)+'</a>');for(var k2=a.length-1;k2>=secs.length;k2--)a[k2].remove()}
          var ol=document.querySelector('.overview ol'),lis=ol?ol.children:[];
          secs.forEach(function(sec,i){if(!sec.dataset.extra)return;var li=ol.querySelector('li[data-x="'+sec.dataset.extra+'"]');if(!li){li=document.createElement('li');li.dataset.x=sec.dataset.extra}ol.insertBefore(li,ol.children[i]||null);
            li.innerHTML='<a href="#d'+(i+1)+'"><b>'+('0'+(i+1)).slice(-2)+'</b><i></i><span class="ot"><strong>'+sec.querySelector('h2').childNodes[0].textContent+'</strong><small>加的一天</small></span><em></em></a>'});
          [].slice.call(ol.querySelectorAll('li[data-x]')).forEach(function(li){if(!document.querySelector('.day[data-extra="'+li.dataset.x+'"]'))li.remove()});
 [].slice.call(ol.children).forEach(function(li,i){var a=li.querySelector('a');if(a)a.setAttribute('href','#d'+(i+1));var nb=li.querySelector('b');if(nb)nb.textContent=('0'+(i+1)).slice(-2)});   // 中间插了一天，后面的序号顺延
          var h=document.querySelector('.overview h2');if(h)h.textContent=secs.length+' 天，怎么排';var gb2=document.querySelector('.glance b.big');if(gb2&&gb2.firstChild)gb2.firstChild.textContent=secs.length;
          applyStart(dk.value);setTimeout(todayBar,0);redrawMap()}
        function dayShell(x,title,body){var sec=document.createElement('section');sec.className='day xday';sec.dataset.extra=x;
          sec.innerHTML='<header><span class="no"></span><div><small>第几天 · </small><h2>'+title+'</h2></div></header>'+body+'<button type="button" class="rmday">去掉这一天</button>';return sec}
        function place(sec){var orig=[].slice.call(document.querySelectorAll('.day:not(.xday)')),last=orig[orig.length-1],tg=(curE&&curE.after!=null)?document.querySelector('.day[data-oi="'+curE.after+'"]'):null;
 if(tg){sec.dataset.after=curE.after;if(curE.k==='free'&&tg.dataset.city)sec.dataset.city=tg.dataset.city;var t=tg;while(t.nextElementSibling&&t.nextElementSibling.classList.contains('xday')&&t.nextElementSibling.dataset.after===String(curE.after))t=t.nextElementSibling;t.parentNode.insertBefore(sec,t.nextSibling)}else last.parentNode.insertBefore(sec,last);
          sec.querySelector('.rmday').addEventListener('click',function(){var orig=ld(ek),xs=orig.filter(function(e){return e.x!==sec.dataset.extra});sv(ek,xs);sec.remove();renum();toast('去掉了加的这一天','撤销',function(){sv(ek,orig);location.reload()})})}
        function build(e){curE=e;if(e.k==='free'){place(dayShell(e.x,'自由活动','<p class="lead">这天不排行程：睡到自然醒，在住的地方附近走走，补补觉，或者把前几天没逛够的地方再去一次。</p>'));return Promise.resolve()}
          return fetch('/trip/'+e.rid+'/').then(function(r){return r.text()}).then(function(h){var doc=new DOMParser().parseFromString(h,'text/html'),src=doc.getElementById('d'+(e.i+1));if(!src)return;
            var sec=dayShell(e.x,src.querySelector('h2').textContent,'');[].slice.call(src.children).forEach(function(c){if(c.tagName!=='HEADER'&&!c.classList.contains('stays')&&!c.classList.contains('tl'))sec.insertBefore(c.cloneNode(true),sec.querySelector('.rmday'))});
            var _anc=(e.after!=null)?document.querySelector('.day[data-oi="'+e.after+'"]'):null,stc=(_anc&&_anc.dataset.city)||(document.querySelector('.addday')||{dataset:{}}).dataset.city||'住处',stl=src.querySelector('.tl');   // 插在中间的：从那天住的地方出发、回那里住
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
 origDays().forEach(function(s,i,a){if(i===a.length-1||s.querySelector('.addafter'))return;dayAct(s,'<button type="button" class="addafter">＋ 这天后面加一天</button>',false)});
 document.addEventListener('click',function(ev){var b=ev.target.closest('.addafter');if(!b)return;var s=b.closest('.day');pendAfter=+s.dataset.oi;addB.click()});
 addB.addEventListener('click',function(ev){if(ev.isTrusted)pendAfter=null},true);   // 点最底下的“加一天”就是加在回程前面
        addB.addEventListener('click',function(){var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
          var origs=origDays(),anc=pendAfter!=null?pendAfter:Math.max(0,origs.length-2),ancSec=document.querySelector('.day[data-oi="'+anc+'"]');
          var cl=cands.filter(function(c){return !c.d||c.d[anc]!=null}).map(function(c){var o={};for(var k in c)o[k]=c[k];if(c.d)o.km=c.d[anc];return o}).sort(function(a,b){return a.km-b.km}).slice(0,10),offl=!navigator.onLine;if(offl)cl=[];   // 断网：别的线路的一天要联网取，入口上就说清楚
          var stc=(pendAfter!=null&&ancSec&&ancSec.dataset.city)||document.querySelector('.addday').dataset.city||'这里';
          sh.innerHTML='<div class="pk-h"><b>加一天</b><button type="button" class="pk-x">关上</button></div><p class="xnote">'+(pendAfter!=null?'加在第 '+(anc+1)+' 天后面，后面的日子往后顺延':'加的一天放在最后一天（回程）前面')+'</p><div class="xd"><button type="button" data-free="1"><b>在'+stc+'多留一天</b><small>自由活动，不排行程</small></button>'+
            (cl.length?'<p class="xg">离这天 100 公里内、可以接上的一天</p>'+cl.map(function(c){var had=ld(ek).some(function(x){return x.k==='r'&&x.rid===c.rid&&+x.i===+c.i});return'<button type="button"'+(had?' disabled class="had"':'')+' data-rid="'+c.rid+'" data-i="'+c.i+'" data-l="'+c.label+'" data-km="'+c.km+'" data-lat="'+(c.lat||'')+'" data-lng="'+(c.lng||'')+'"><b>'+c.title+(had?'<span class="hadt">已加</span>':'')+'</b><small>来自「'+c.label+'」第 '+(c.i+1)+' 天 · 离住处约 '+c.km+' 公里</small></button>'}).join(''):'<p class="xg">'+(offl?'没网，暂时不能接别的线路的一天，可以先选多留一天':'附近没有合适的线路可以接，可以先选多留一天')+'</p>')+'</div>';
          function close(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
          sh.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b||b.disabled)return;if(b.classList.contains('pk-x'))return close();
            if(!b.dataset.free&&ld(ek).some(function(x){return x.k==='r'&&x.rid===b.dataset.rid&&+x.i===+b.dataset.i})){toast('这一天已经加过了');return}
            var e=b.dataset.free?{k:'free',x:'f'+Date.now()}:{k:'r',x:'r'+Date.now(),rid:b.dataset.rid,i:+b.dataset.i,label:b.dataset.l,km:+(b.dataset.km||0),lat:+(b.dataset.lat||0),lng:+(b.dataset.lng||0)};if(pendAfter!=null)e.after=pendAfter;pendAfter=null;var xs=ld(ek);xs.push(e);sv(ek,xs);close();
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
      b.addEventListener('click',function(){bk=ld('zouni_booked');var i=bk.indexOf(b.dataset.k);if(i>=0)bk.splice(i,1);else bk.push(b.dataset.k);sv('zouni_booked',bk);pt()})});

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
      function rowsOf(sec){return[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return r.getAttribute('data-np')!=='v'})}
      function replan(sec){var oi=sec.dataset.oi,S=getS(),D=getD(),tl=sec.querySelector('.tl'),NPX=npSync(sec,D),rows=rowsOf(sec);
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
          function ex(r){var k=r.dataset.k,rd=NPX.rd[k];return(A[k]||0)+(NPX.ld[k]||0)+(rd?rd.d-(rd.d0||spanOf(r)):0)}   // 这一行的时长变化：多待少待 + 被换的站的新停留 + 被改写的车程
          function runV(r){var vs=NPX.vs[r.dataset.k];if(!vs)return;vs.forEach(function(v){var dm=Math.max(15,v.d+(A[v.k]||0)),t=lastT+lastSpan;   // 锚点后面加的站：先一段车程，再停留；后面的行整体往后推
            v.dep.querySelector('time').textContent=m2hm(t);v.dep._t=t;lastT=t+v.l;v.row.querySelector('time').textContent=m2hm(lastT);v.row._t=lastT;lastSpan=dm;shift+=v.l+dm;npDurTxt(v.row,dm)})}
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
            r.querySelector('time').textContent=m2hm(t1);r._t=t1;lastT=t1;var e_=ex(r),fl_=(NPX.ld[r.dataset.k]!=null)?5:15;lastSpan=Math.max(fl_,span+e_);
            if(e_)shift+=Math.max(fl_-span,e_);runV(r)});
          t=lastT==null?start:lastT+lastSpan}
        seq=timed.slice();var lunch=seq.filter(function(r){return r.dataset.meal==='l'&&!r.hidden})[0];
        if(lunch&&hm2m(S[oi])!=null&&start>t0[0]&&start>=660&&seq.indexOf(lunch)>0&&t0[timed.indexOf(lunch)]+(start-t0[0])>840&&t0[timed.indexOf(lunch)]<=840){moveL=lunch}   // 只在自己改晚了出发、把原本两点前的午饭推过两点时   // 出发晚、午饭要拖过两点：先吃午饭再出发
        run(seq);if(moveL){seq.splice(seq.indexOf(moveL),1);seq.unshift(moveL)}
        var t0end=t0[t0.length-1]+60;
        var fin=[];seq.forEach(function(r){fin.push(r);(NPX.vs[r.dataset.k]||[]).forEach(function(v){fin.push(v.dep,v.row)})});   // 顺路加的站紧跟在锚点后面
        var rest=orig.filter(function(r){return seq.indexOf(r)<0});fin.concat(rest).forEach(function(r){tl.appendChild(r)});
        var vis=fin.filter(function(r){return!r.hidden});sec._npRes={vis:vis,start:start,end:t};if(sec._npTrial)return;   // 试算（副本）到这里为止：只要时间表
        var st=sec.querySelector('.st b');if(st)st.textContent=m2hm(start);
        var ov=document.querySelectorAll('.overview ol li')[[].slice.call(document.querySelectorAll('.day')).indexOf(sec)];if(ov){var em=ov.querySelector('em');if(em)em.textContent=m2hm(start)+' 走'}
        var warn=sec.querySelector('.latewarn');if(warn)warn.remove();
        var msgs=[];if(t>22*60+30&&t>t0end+5)msgs.push('按 '+m2hm(start)+' 出发，这天要到 '+m2hm(t)+' 才结束');
        late.forEach(function(r){msgs.push('赶不上「'+r.querySelector('.m').childNodes[0].textContent.trim()+'」原定的 '+r.dataset.at)});
        var changed=(hm2m(S[oi])!=null&&hm2m(S[oi])!==t0[0])||Object.keys(A).length>0||Object.keys(F).length>0;
        var road=0,nsee=0,gapRow=null,gapLen=0;vis.forEach(function(r,i){var nx=vis[i+1],a=r._t,b=nx?nx._t:t;if(r.classList.contains('dep')&&r.dataset.slack!=='1'){var sd_=(r.querySelector('.s')||{}).textContent||'',hh_=/(\d+)\s*小时/.exec(sd_),mn_=/(\d+)\s*分/.exec(sd_),lg_=(hh_||mn_)?(hh_?+hh_[1]*60:0)+(mn_?+mn_[1]:0):(/回去歇一下/.test(sd_)?0:b-a);road+=Math.max(0,lg_)}if((r.classList.contains('see')||r.classList.contains('fun'))&&r.dataset.slack!=='1')nsee++;if(r.dataset.slack==='1'&&b-a>gapLen){gapLen=b-a;gapRow=r}});
        var summary='改完：这天 '+m2hm(t)+' 结束，去 '+nsee+' 个地方，路上约 '+hstr(road||0);
        var sun=sec.querySelector('.sun'),used=[];Object.keys(getF()).forEach(function(d){Object.keys(getF()[d]).forEach(function(k){used.push(getF()[d][k].n)})});
        var fillHint=null;if(gapRow&&gapLen>=150&&NB.length){var sps=[],allD=[].slice.call(document.querySelectorAll('.day')),di=allD.indexOf(sec);[di,di-1].forEach(function(q){var s2=allD[q]&&allD[q].querySelector('.sun[data-k="rise"]');if(s2)sps.push([+s2.dataset.lat,+s2.dataset.lng])});   // 只看这天和前一天住的地方附近
          var tlTxt=[].slice.call(document.querySelectorAll('.tl')).map(function(t){return t.textContent}).join(' ');fillHint=NB.filter(function(x){return used.indexOf(x.n)<0&&x.dur<=gapLen-30&&tlTxt.indexOf(x.n)<0}).map(function(x){return{x:x,d:Math.min.apply(null,sps.map(function(p){return kmz(p[0],p[1],x.lat,x.lng)}))}}).filter(function(z){return z.d<=30}).sort(function(a,b){return a.d-b.d})[0]||null}   // 按离住的地方最近来挑
        
        if(msgs.length||changed||NPX.n||(D[oi]&&D[oi].length)){var lastSee=vis.filter(function(r){return r.classList.contains('see')||r.classList.contains('fun')}).pop();
          var box=document.createElement('div');box.className='latewarn';
          box.className='latewarn'+(msgs.length?' bad':'');
          box.innerHTML=(msgs.length?'<p>'+msgs.join('；')+(lastSee?' <button type="button" class="drop">去掉「'+lastSee.querySelector('.m').childNodes[0].textContent.trim()+'」</button>':'')+'</p>':'')+'<p class="sum">'+summary.replace('改完：','')+' · <button type="button" class="reset">恢复</button></p>'+(fillHint?'<p class="gap">空出 '+hstr(gapLen).trim()+'，可以加「'+fillHint.x.n+'」 <button type="button" class="fill">加上</button></p>':'');
          var tl=sec.querySelector('.tl');tl.parentNode.insertBefore(box,tl);
          var fb=box.querySelector('.fill');if(fb)fb.addEventListener('click',function(){var F2=getF();F2[oi]=F2[oi]||{};F2[oi][gapRow.dataset.k]={n:fillHint.x.n,c:fillHint.x.c};try{localStorage.setItem(FK,JSON.stringify(F2))}catch(e){}replan(sec);toast('加上了「'+fillHint.x.n+'」')});
          var dr=box.querySelector('.drop');if(dr)dr.addEventListener('click',function(){var undo1=zSnap([DK,NK,AK]),lsn=nm(lastSee);if(lastSee.getAttribute('data-np')==='v'){npRemove(oi,+lastSee.dataset.k-1000);replan(sec);toast('去掉了，后面的时间往前挪了','撤销',function(){undo1();replan(sec);toast('撤销了，「'+lsn+'」回来了')});return}var D2=getD(),k=+lastSee.dataset.k,prevR=lastSee.previousElementSibling;npDrop(oi,k);D2[oi]=(D2[oi]||[]).concat([k]);if(prevR&&prevR.classList.contains('dep')&&!prevR.hidden)D2[oi].push(+prevR.dataset.k);try{localStorage.setItem(DK,JSON.stringify(D2))}catch(e){}replan(sec);toast('去掉了，后面的时间往前挪了','撤销',function(){undo1();replan(sec);toast('撤销了，「'+lsn+'」回来了')})});
          box.querySelector('.reset').addEventListener('click',function(){var S2=getS(),D2=getD(),A2=getA(),F3=getF();delete S2[oi];delete D2[oi];delete A2[oi];delete F3[oi];npClear(oi);try{localStorage.setItem(SK,JSON.stringify(S2));localStorage.setItem(DK,JSON.stringify(D2));localStorage.setItem(AK,JSON.stringify(A2));localStorage.setItem(FK,JSON.stringify(F3))}catch(e){}replan(sec);toast('恢复了原来的安排')})}
        npFacts(sec,NPX);if(NPX.n&&window.zAddCopy)window.zAddCopy()}
      // ⑧ 顺路加一站 / 换一站（规则和数字：docs/handoff/design-nearby-stops.md、02-UI规范.md「调整里的顺路景点」；车程模型在 np_model.js，点开才加载）
      //  状态 zouni_np_<线路id> = {v:1, oi:{"<原来第几天>":[操作,…]}}。操作 = {op:'ins'|'rep', ak:锚点行 data-k, an:锚点原名, u:序号, i,n,c,a,o,t,d,s,q,x}：自带快照，不依赖分片还在、也不依赖候选池 id
      //  v 是格式版本：以后改格式要升版并写迁移；读不到、解析失败、版本不认识，一律当“没有”，页面回到原版
      //  应用方式：每次 replan 开头先把这一天还原成静态页面的样子（npRevert），再按状态重新套上（npApply）——撤销、刷新、叠加“去掉一天 / 下雨换 / 多待少待”都走同一条路，没有第二套状态
      var NK='zouni_np_'+me2,NP_CAP=12,NPM=null,NP_LIM={MAX:5,END:1290,SPAN:780},NPV=(function(){var s=document.querySelector('script[src*="/assets/site.js"]'),m=s&&/[?&]v=([0-9a-f]+)/.exec(s.getAttribute('src')||'');return m?m[1]:''})();   // NP_LIM 必须和 np_model.js 的 MAX_NONMEAL / END_LIMIT / SPAN_LIMIT 一致（data_checks 会比）
      var NP_TYPE={sg:'景',pk:'园',st:'街',ms:'馆',fn:'玩',tp:'寺',bc:'滩',mt:'山',lk:'湖',cl:'文',tn:'镇',nt:'夜'};
      var NP_PIN='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/></svg>',
          NP_DP='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3.8l2.45 5.02 5.5.8-3.98 3.88.94 5.48L12 16.4l-4.91 2.58.94-5.48L4.05 9.62l5.5-.8z"/></svg>',
          NP_XHS='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3.5" y="5" width="17" height="14" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="M20.5 15.5l-4.5-4.5-8 8"/></svg>',
          NP_YT='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2.8" y="5.5" width="18.4" height="13" rx="3.4"/><path d="M10 9.2l5 2.8-5 2.8z"/></svg>';
      var NP_LEG=/^(回住处\s*·\s*)?(步行|开车|自驾约|自驾|打车约|打车|包车约|包车)\s*(?:(\d+)\s*小时)?\s*(?:(\d+)\s*分钟?)?(?:\s*·\s*(\d+)\s*公里)?\s*$/,NP_INDOOR=/博物馆|博物院|美术馆|纪念馆|展览馆|科技馆|陈列馆|艺术馆|天文馆|海洋馆|水族馆/,NP_NAVRE=/uri\.amap\.com\/navigation|google\.com\/maps\/dir/;
      function npGet(){var o=null;try{o=JSON.parse(localStorage.getItem(NK)||'null')}catch(e){o=null}if(!o||o.v!==1||!o.oi||typeof o.oi!=='object')return{v:1,oi:{}};return o}
      function npPut(o){try{var k,any=false;for(k in o.oi){if(o.oi[k]&&o.oi[k].length)any=true;else delete o.oi[k]}if(any)localStorage.setItem(NK,JSON.stringify(o));else localStorage.removeItem(NK)}catch(e){}}
      function npTotal(o){var n=0,k;for(k in o.oi)n+=o.oi[k].length;return n}
      function npOps(sec){return sec._npTrial||(npGet().oi[sec.dataset.oi]||[])}
      function npEsc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
      function npEnc(s){return encodeURIComponent(s)}
      function npLL(s){if(!s)return null;var p=String(s).split(',');return p.length===2&&isFinite(+p[0])&&isFinite(+p[1])?[+p[0],+p[1]]:null}
      function npDur(m){return m>=60?Math.floor(m/60)+' 小时'+(m%60?' '+(m%60)+' 分':''):m+' 分钟'}
      function npIsRow(r){return!!r&&r.nodeType===1&&r.classList.contains('r')}
      function npIsDep(r){return r.classList.contains('dep')}
      function npLegOf(dep){var s=dep.querySelector('.s');if(!s)return null;var m=NP_LEG.exec(s.textContent.replace(/\s+/g,' ').trim());if(!m||(!m[3]&&!m[4]))return null;return{pre:m[1]||'',how:m[2],min:(m[3]?+m[3]*60:0)+(m[4]?+m[4]:0)}}
      function npName(r){var m=r.querySelector('.m');return m&&m.childNodes[0]?m.childNodes[0].textContent.trim():''}
      function npCore(s){return String(s||'').replace(/（(空档加的|下雨换的|加的|换的)）$/,'').trim()}
      function npName0(r){if(r.getAttribute('data-np-a')){try{return JSON.parse(r.getAttribute('data-np-a')).n}catch(e){}}return npCore(r.dataset.fo||r.dataset.on||npName(r))}
      function npPR(sec){var tl=sec.querySelector('.tl'),rs=[].slice.call(tl.children).filter(function(r){return npIsRow(r)&&r.dataset.np!=='v'});rs.forEach(function(r,i){if(r.dataset.k==null)r.dataset.k=i});return rs.slice().sort(function(a,b){return a.dataset.k-b.dataset.k})}
      function npGcj(lat,lng){if(!(73.5<lng&&lng<135.1&&3.8<lat&&lat<53.6))return[lat,lng];var a=6378245.0,ee=0.00669342162296594323,pi=Math.PI;
        function tl(x,y){return-100.0+2.0*x+3.0*y+0.2*y*y+0.1*x*y+0.2*Math.sqrt(Math.abs(x))+(20.0*Math.sin(6.0*x*pi)+20.0*Math.sin(2.0*x*pi))*2.0/3.0+(20.0*Math.sin(y*pi)+40.0*Math.sin(y/3.0*pi))*2.0/3.0+(160.0*Math.sin(y/12.0*pi)+320*Math.sin(y*pi/30.0))*2.0/3.0}
        function tg(x,y){return 300.0+x+2.0*y+0.1*x*x+0.1*x*y+0.1*Math.sqrt(Math.abs(x))+(20.0*Math.sin(6.0*x*pi)+20.0*Math.sin(2.0*x*pi))*2.0/3.0+(20.0*Math.sin(x*pi)+40.0*Math.sin(x/3.0*pi))*2.0/3.0+(150.0*Math.sin(x/12.0*pi)+300.0*Math.sin(x/30.0*pi))*2.0/3.0}
        var dl=tl(lng-105.0,lat-35.0),dg=tg(lng-105.0,lat-35.0),rl=lat/180.0*pi,mg=1-ee*Math.pow(Math.sin(rl),2),sm=Math.sqrt(mg);
        dl=(dl*180.0)/((a*(1-ee))/(mg*sm)*pi);dg=(dg*180.0)/(a/sm*Math.cos(rl)*pi);return[Math.round((lat+dl)*1e6)/1e6,Math.round((lng+dg)*1e6)/1e6]}
      // 两点之间一段车程：模型 leg()（和 compile_itineraries 同一张表）× 作者写的那一段和模型的比例 f；返回 {how,min,dist,txt}
      function npLeg(a,b,mode,f,sv,pre){var L=NPM.leg(a,b,mode),how=L[0],mins=L[1],dist=L[2];if(f&&f!==1&&how!=='步行')mins=Math.max(5,NPM.r5(mins*f));if(sv&&how.indexOf('包车')===0)how='自驾'+how.slice(2);
        return{how:how,min:mins,dist:dist,txt:(pre||'')+how+' '+npDur(mins)+(dist&&dist>=5?' · '+dist+' 公里':'')}}
      // 导航链接：和 build_site.navurl / amap_app 同一套写法（国内高德，国外谷歌）；from 是上一个点
      function npNavHref(kw,name,from,to,how){var walk=how==='步行',o={};
        if(art.dataset.app==='google'){o.href='https://www.google.com/maps/dir/?api=1&origin='+from[0]+','+from[1]+'&destination='+to[0]+','+to[1]+'&travelmode='+(walk?'walking':'driving');return o}
        var gf=npGcj(from[0],from[1]),gt=npGcj(to[0],to[1]),q='sourceApplication=zouni&slat='+gf[0]+'&slon='+gf[1]+'&sname='+npEnc('上一站')+'&dlat='+gt[0]+'&dlon='+gt[1]+'&dname='+npEnc(kw)+'&dev=0&t='+(walk?2:0);
        o.href='https://uri.amap.com/navigation?from='+gf[1]+','+gf[0]+','+npEnc('上一站')+'&to='+gt[1]+','+gt[0]+','+npEnc(name)+'&mode='+(walk?'walk':'car')+'&src=zouni&callnative=1';o.ios='iosamap://path?'+q;o.and='amapuri://route/plan/?'+q;return o}
      function npIcons(op,nav){var kw=op.q||op.n,city=op.c||'',core=String(op.n).split(/\s*·\s*/)[0],xk=/[一-鿿]/.test(core)?((city&&core.indexOf(city)<0)?city+' '+core:core):'',q=(city?city+' ':'')+kw,href,ios='',and='';
        if(nav){href=nav.href;ios=nav.ios||'';and=nav.and||''}
        else if(art.dataset.app==='google'){href='https://www.google.com/maps/search/?api=1&query='+op.a+','+op.o}
        else{var g=npGcj(op.a,op.o),q2='sourceApplication=zouni&poiname='+npEnc(kw)+'&lat='+g[0]+'&lon='+g[1]+'&dev=0';href='https://uri.amap.com/marker?position='+g[1]+','+g[0]+'&name='+npEnc(kw)+'&src=zouni&callnative=1';ios='iosamap://viewMap?'+q2;and='androidamap://viewMap?'+q2}
        return'<span class="icg"><a class="ic map" href="'+npEsc(href)+'"'+(ios?' data-ios="'+npEsc(ios)+'" data-and="'+npEsc(and)+'"':'')+' rel="nofollow noopener" target="_blank" aria-label="'+(nav?'导航去 ':'地图上看 ')+npEsc(kw)+'">'+NP_PIN+'</a>'
          +'<a class="ic dp" href="https://www.dianping.com/ai-search?keyword='+npEnc(q)+'" data-app="dianping://searchshoplist?keyword='+npEnc(q)+'" rel="nofollow noopener" target="_blank" aria-label="大众点评上看 '+npEsc(kw)+'">'+NP_DP+'</a>'
          +(xk?'<a class="ic xhs" href="https://www.xiaohongshu.com/search_result?keyword='+npEnc(xk)+'&source=web_explore_feed" data-app="xhsdiscover://search/result?keyword='+npEnc(xk)+'" rel="nofollow noopener" target="_blank" aria-label="小红书上看 '+npEsc(xk)+' 的实景">'+NP_XHS+'</a><a class="ic yt" href="https://www.youtube.com/results?search_query='+npEnc(xk+' 旅行')+'" rel="nofollow noopener" target="_blank" aria-label="YouTube 上搜 '+npEsc(xk)+' 的旅行视频">'+NP_YT+'</a>':'')+'</span>'}
      // 新行的第二行文字：停留 · 门票（只显示，不改总价）· 一句话；格式和 build_site.row_html 一致
      function npTix(x){x=x||{};var tt=String(x.t||'').replace(/(\d[\d,]*)\s*元左右/,'约 $1 元').replace(/^门票\s*/,''),tix='';if(tt)tix=tt.slice(0,6).indexOf('免费')>=0?tt:'门票'+(/^(约|旺季)/.test(tt)?'':' ')+tt;
        if(x.cl!=null)tix=(tix?tix+' · ':'')+'周'+'日一二三四五六'.charAt(x.cl)+'闭馆';return tix}
      function npSub(op){var tix=npTix(op.x),sub=npDur(op.d)+(tix?' · <span class="tix">'+npEsc(tix)+'</span>':'')+(op.s?' · <span class="sn2">'+npEsc(op.s)+'</span>':'');
        if(op.x&&op.x.b)sub='<em class="bkn">要预约</em> · '+sub;return sub+'<button type="button" class="adj" aria-label="调整这一站">调整</button>'}
      function npRb(op,rep,nav){return'<p class="m">'+npEsc(op.n+(rep?'（换的）':'（加的）'))+npIcons(op,nav)+'</p><p class="s">'+npSub(op)+'</p>'}
      function npStopAttrs(r,op){r.setAttribute('data-ll',op.a.toFixed(5)+','+op.o.toFixed(5));r.setAttribute('data-dm',op.d);if(op.t)r.setAttribute('data-ty',op.t);else r.removeAttribute('data-ty');if(op.i)r.setAttribute('data-pid',op.i);else r.removeAttribute('data-pid');
        if(NP_INDOOR.test(op.n))r.setAttribute('data-in','1');else r.removeAttribute('data-in');if(op.x&&op.x.cl!=null)r.setAttribute('data-cw',String(op.x.cl));else r.removeAttribute('data-cw')}
      // 一行附近的前后点和车程：A 前一个点、C 后一个点（没有就用这天的出发点 / 住处）、lb 前面那段车程行、la 后面那段车程行（只有文字是干净的“怎么走 N 分钟 · N 公里”才算）
      function npScan(sec,S,isDrop){var L=[].slice.call(sec.querySelector('.tl').children).filter(npIsRow),i=L.indexOf(S),spt=npLL(sec.dataset.sp),ept=npLL(sec.dataset.ep),A=spt,C=ept,lb=null,la=null,j,m,lg;
        function skip(q){return isDrop(q)||(q.classList.contains('eat')&&!q.dataset.ll)}
        for(j=i-1;j>=0;j--){if(isDrop(L[j]))continue;if(L[j].dataset.ll){A=npLL(L[j].dataset.ll);break}}
        for(j=i+1;j<L.length;j++){if(isDrop(L[j]))continue;if(L[j].dataset.ll){C=npLL(L[j].dataset.ll);break}}
        j=i-1;while(j>=0&&skip(L[j]))j--;if(j>=0&&npIsDep(L[j])){lg=npLegOf(L[j]);if(lg)lb={dep:L[j],lg:lg}}
        j=i+1;while(j<L.length&&skip(L[j]))j++;
        if(j<L.length&&npIsDep(L[j])){lg=npLegOf(L[j]);if(lg){if(lg.pre){if(ept)la={dep:L[j],lg:lg,to:null,pt:ept}}else{m=j+1;while(m<L.length&&skip(L[m]))m++;if(m<L.length&&L[m].dataset.ll)la={dep:L[j],lg:lg,to:L[m],pt:npLL(L[m].dataset.ll)}}}}
        return{A:A,C:C,lb:lb,la:la,L:L,i:i}}
      // ——— 还原：把这一天变回静态页面的样子 ———
      function npRevert(sec){var tl=sec.querySelector('.tl');if(!tl)return;[].slice.call(tl.children).forEach(function(r){if(!npIsRow(r))return;
        if(r.getAttribute('data-np')==='v'){r.parentNode.removeChild(r);return}
        if(r.getAttribute('data-np')==='r'){var rb=r.querySelector('.rb'),a={};if(rb&&r.hasAttribute('data-np-rb'))rb.innerHTML=r.getAttribute('data-np-rb');try{a=JSON.parse(r.getAttribute('data-np-a')||'{}')}catch(e){}
          ['ll','dm','ty','pid','in','cw','d0'].forEach(function(k){if(a[k]==null)r.removeAttribute('data-'+k);else r.setAttribute('data-'+k,a[k])});
          r.removeAttribute('data-np');r.removeAttribute('data-np-rb');r.removeAttribute('data-np-a');r.removeAttribute('data-np-ll0');
          if(a.ord){var vv={};[].forEach.call(r.attributes,function(x){vv[x.name]=x.value});a.ord.forEach(function(n){if(vv[n]!=null){r.removeAttribute(n);r.setAttribute(n,vv[n])}})}}   // 属性顺序也放回原样
        if(r.hasAttribute('data-np-s0')){var s=r.querySelector('.s');if(s)s.innerHTML=r.getAttribute('data-np-s0');r.removeAttribute('data-np-s0')}
        if(r.hasAttribute('data-np-m0')){var m=r.querySelector('.m');if(m)m.innerHTML=r.getAttribute('data-np-m0');r.removeAttribute('data-np-m0')}
        if(r.hasAttribute('data-np-n0')){var n0={},ac=r.querySelector('a.ic.map');try{n0=JSON.parse(r.getAttribute('data-np-n0'))}catch(e){}if(ac&&n0.h){ac.setAttribute('href',n0.h);['ios','and'].forEach(function(k){if(n0[k]==null)ac.removeAttribute('data-'+k);else ac.setAttribute('data-'+k,n0[k])})}r.removeAttribute('data-np-n0')}});
        [].slice.call(sec.querySelectorAll('.fx[data-np]')).forEach(function(f){f.parentNode.removeChild(f)});[].slice.call(sec.querySelectorAll('[data-np-b0]')).forEach(function(b){b.textContent=b.getAttribute('data-np-b0');b.removeAttribute('data-np-b0')});sec.removeAttribute('data-np-dd')}
      // ——— 套上：按状态改行、造虚拟行、改写相邻车程。返回给 replan 的账：ld 每个 dep 行的车程分钟差，rd 每个被换的站的新停留，vs 每个锚点后面的虚拟行，n 套上了几处 ———
      function npApply(sec,ops,drop){var X={ld:{},rd:{},vs:{},n:0},pr=npPR(sec),mode=sec.dataset.lm||'city',sv=art.dataset.sv==='1',byK={};
        function isDrop(r){return r.dataset.np!=='v'&&drop.indexOf(+r.dataset.k)>=0}
        function setLeg(dep,lg,toName){var s=dep.querySelector('.s'),m=dep.querySelector('.m'),old=+dep.dataset.min||0;if(!dep.hasAttribute('data-np-s0'))dep.setAttribute('data-np-s0',s.innerHTML);s.textContent=lg.txt;X.ld[dep.dataset.k]=lg.min-old;
          if(toName!=null){if(!dep.hasAttribute('data-np-m0'))dep.setAttribute('data-np-m0',m.innerHTML);m.textContent='出发 → '+toName}}
        function rename(dep,toName){var m=dep.querySelector('.m');if(!dep.hasAttribute('data-np-m0'))dep.setAttribute('data-np-m0',m.innerHTML);m.textContent='出发 → '+toName}
        function retarget(t,from,how){var a=t&&t.querySelector('a.ic.map'),to=t&&npLL(t.dataset.ll);if(!a||!from||!to||!NP_NAVRE.test(a.getAttribute('href')||''))return;var nm=(a.getAttribute('aria-label')||'').replace(/^导航去 /,'')||npName(t),nv;
          if(!t.hasAttribute('data-np-n0'))t.setAttribute('data-np-n0',JSON.stringify({h:a.getAttribute('href'),ios:a.getAttribute('data-ios'),and:a.getAttribute('data-and')}));
          nv=npNavHref(nm,nm,from,to,how);a.setAttribute('href',nv.href);if(nv.ios){a.setAttribute('data-ios',nv.ios);a.setAttribute('data-and',nv.and)}}
        ops.forEach(function(o){var g=byK[o.ak]||(byK[o.ak]={rep:null,ins:[]});if(o.op==='rep')g.rep=o;else g.ins.push(o)});
        pr.forEach(function(S){var g=byK[S.dataset.k],s0,sc,f,X1,o,nv,wasNav,rb,sv0;if(!g||isDrop(S)||!S.dataset.ll)return;s0=npLL(S.dataset.ll);
          if(g.rep){o=g.rep;sc=npScan(sec,S,isDrop);X1=[o.a,o.o];rb=S.querySelector('.rb');wasNav=NP_NAVRE.test(((S.querySelector('a.ic.map')||{getAttribute:function(){return''}}).getAttribute('href'))||'');
            if(sc.lb){if(sc.A){f=NPM.factor(sc.A,s0,+sc.lb.dep.dataset.min||sc.lb.lg.min,mode);setLeg(sc.lb.dep,npLeg(sc.A,X1,mode,f,sv,sc.lb.lg.pre),o.n)}else rename(sc.lb.dep,o.n)}
            if(rb){S.setAttribute('data-np-rb',rb.innerHTML);S.setAttribute('data-np-ll0',S.dataset.ll);sv0={n:npCore(npName(S)),ll:S.getAttribute('data-ll'),dm:S.getAttribute('data-dm'),ty:S.getAttribute('data-ty'),pid:S.getAttribute('data-pid'),'in':S.getAttribute('data-in'),cw:S.getAttribute('data-cw'),d0:S.getAttribute('data-d0'),ord:[].map.call(S.attributes,function(x){return x.name})};S.setAttribute('data-np-a',JSON.stringify(sv0));
              nv=(wasNav&&sc.A)?npNavHref(o.q||o.n,o.n,sc.A,X1,sc.lb&&sc.lb.lg.how==='步行'?'步行':'开车'):null;rb.innerHTML=npRb(o,true,nv);npStopAttrs(S,o);S.removeAttribute('data-d0');S.setAttribute('data-np','r');X.rd[S.dataset.k]={d:o.d,d0:+sv0.dm||0}}
            if(sc.la){f=NPM.factor(s0,sc.la.pt,+sc.la.dep.dataset.min||sc.la.lg.min,mode);setLeg(sc.la.dep,npLeg(X1,sc.la.pt,mode,f,sv,sc.la.lg.pre),null);retarget(sc.la.to,X1,sc.la.lg.how==='步行'?'步行':'开车')}
            X.n++}
          if(g.ins.length){var list=g.ins.slice().sort(function(a,b){return b.u-a.u}),sPt=npLL(S.dataset.ll),prevPt=sPt,anchor=S,vs=[];sc=npScan(sec,S,isDrop);f=(sc.la&&sc.la.pt)?NPM.factor(sPt,sc.la.pt,+sc.la.dep.dataset.min||sc.la.lg.min,mode):1;
            list.forEach(function(p){var P=[p.a,p.o],lg=npLeg(prevPt,P,mode,f,sv,''),dep=document.createElement('li'),row=document.createElement('li'),nav=npNavHref(p.q||p.n,p.n,prevPt,P,lg.how);
              dep.className='r dep';dep.setAttribute('data-np','v');dep.setAttribute('data-mode',mode);dep.setAttribute('data-min',lg.min);if(lg.dist)dep.setAttribute('data-km',lg.dist);
              dep.innerHTML='<time></time><span class="dot"></span><div class="rb"><p class="m">出发 → '+npEsc(p.n)+'</p><p class="s">'+npEsc(lg.txt)+'</p></div>';
              row.className='r see';row.setAttribute('data-np','v');row.setAttribute('data-k',1000+p.u);row.setAttribute('data-slack','0');npStopAttrs(row,p);row.innerHTML='<time></time><span class="dot"></span><div class="rb">'+npRb(p,false,nav)+'</div>';
              anchor.parentNode.insertBefore(dep,anchor.nextSibling);anchor.parentNode.insertBefore(row,dep.nextSibling);vs.push({dep:dep,row:row,l:lg.min,d:p.d,k:1000+p.u});prevPt=P;anchor=row;X.n++});
            if(sc.la){var lg2=npLeg(prevPt,sc.la.pt,mode,f,sv,sc.la.lg.pre);setLeg(sc.la.dep,lg2,null);retarget(sc.la.to,prevPt,lg2.how==='步行'?'步行':'开车')}
            X.vs[S.dataset.k]=vs}});
        return X}
      // 操作自检：存储里的东西可能是旧版本、别人的链接、被改坏的——字段不对的当没有
      function npValid(o){return!!o&&typeof o==='object'&&(o.op==='ins'||o.op==='rep')&&isFinite(o.ak)&&isFinite(o.u)&&typeof o.n==='string'&&o.n.length>0&&o.n.length<60&&isFinite(o.a)&&isFinite(o.o)&&isFinite(o.d)&&o.d>=5&&o.d<=600&&Math.abs(o.a)<=90&&Math.abs(o.o)<=180&&(o.x==null||typeof o.x==='object')}
      // ——— 入口：每次 replan 开头调用；返回账（没有操作就是空账，页面和原来一模一样）———
      function npModel(){return NPM||(window.ZNP_MODEL?(NPM=window.ZNP_MODEL):null)}
      var npWait=null;function npScript(src,ok,bad){var s=document.createElement('script'),done=false;s.async=true;s.onload=function(){if(!done){done=true;ok()}};s.onerror=function(){if(!done){done=true;if(s.parentNode)s.parentNode.removeChild(s);bad()}};s.src=src;document.head.appendChild(s)}
      function npEnsureModel(ok,bad){if(npModel()){ok();return}npScript('/assets/np_model.js'+(NPV?'?v='+NPV:''),function(){NPM=window.ZNP_MODEL;ok()},bad||function(){})}
      function npSync(sec,D){var oi=sec.dataset.oi,tl=sec.querySelector('.tl'),X={ld:{},rd:{},vs:{},n:0},ops,pr,drop,ok=[],bad=0,L,same=true;if(!tl)return X;
        npRevert(sec);ops=npOps(sec);if(!ops.length)return X;
        if(!npModel()){if(!npWait){npWait=1;npEnsureModel(function(){[].slice.call(document.querySelectorAll('.day')).forEach(function(s){if(s.dataset.oi!=null)replan(s)})},function(){npWait=null})}return X}
        pr=npPR(sec);drop=(D&&D[oi])||[];L=[].slice.call(tl.children).filter(npIsRow);pr.forEach(function(r,i){if(L[i]!==r)same=false});if(!same)pr.forEach(function(r){tl.appendChild(r)});   // 行按原来的顺序放回去（上一次 replan 可能把午饭挪到了最前）
        ops.forEach(function(o){var r=npValid(o)&&pr.filter(function(x){return x.dataset.k==o.ak})[0];if(!r||drop.indexOf(+r.dataset.k)>=0||(o.an&&npName0(r)!==o.an)){bad++;return}ok.push(o)});
        if(bad&&!sec._npTrial){var st=npGet();st.oi[oi]=ok.slice();npPut(st);try{if(!sessionStorage.getItem('zouni_np_bad')){sessionStorage.setItem('zouni_np_bad','1');setTimeout(function(){toast('有一处调整因为行程更新没法套用，已经去掉了')},800)}}catch(e){}}
        return ok.length?npApply(sec,ok,drop):X}
      // 开车时间：这天（和页头“最长一天”）跟着改。只算被我们改过的那几段车程的差，不去动没碰过的数字
      function npDrv(t){var m=/(?:自驾|开车|包车)约?\s*(?:(\d+)\s*小时)?\s*(?:(\d+)\s*分)?/.exec(t||'');return m?((m[1]?+m[1]*60:0)+(m[2]?+m[2]:0)):0}
      function npDrvTxt(m){if(!m)return'';if(art.dataset.lg==='1'&&m<45)return m+' 分钟';var v=Math.round(m/30)/2;return(v%1?v.toFixed(1):String(v))+' 小时'}
      function npFacts(sec,X){var tl=sec.querySelector('.tl'),facts=sec.querySelector('.facts'),dd=0,fx=null,b,total,gd,secs,mx=0,any=false;if(!facts)return;
        if(X.n){[].slice.call(tl.children).forEach(function(r){if(!npIsRow(r)||!npIsDep(r))return;var s=r.querySelector('.s');if(!s)return;
          if(r.getAttribute('data-np')==='v')dd+=npDrv(s.textContent);else if(r.hasAttribute('data-np-s0'))dd+=npDrv(s.textContent)-npDrv(r.getAttribute('data-np-s0'))});
          total=(+sec.dataset.drv||0)+dd;sec.setAttribute('data-np-dd',dd);
          [].slice.call(facts.querySelectorAll('.fx')).forEach(function(f){var sm=f.querySelector('small');if(sm&&sm.textContent==='开车')fx=f});
          if(fx){b=fx.querySelector('b');if(b&&!b.hasAttribute('data-np-b0'))b.setAttribute('data-np-b0',b.textContent);if(b)b.textContent=npDrvTxt(total)}
          else if(total>0){fx=document.createElement('div');fx.className='fx';fx.setAttribute('data-np','1');fx.innerHTML='<small>开车</small><b>'+npDrvTxt(total)+'</b>';facts.insertBefore(fx,facts.children[1]||null)}}
        gd=document.querySelector('.glance [data-gd]');if(!gd)return;secs=[].slice.call(document.querySelectorAll('.day[data-oi]'));
        secs.forEach(function(s){var v=(+s.dataset.drv||0)+(+s.getAttribute('data-np-dd')||0);if(s.hasAttribute('data-np-dd'))any=true;if(v>mx)mx=v});
        var bt=gd.querySelector('b'),sm2=gd.querySelector('small');
        if(any&&mx>0&&bt&&sm2){if(!gd.hasAttribute('data-np-g0'))gd.setAttribute('data-np-g0',bt.textContent+'|'+sm2.textContent);if(bt.textContent==='不开车')bt.textContent=art.dataset.sv==='1'?'自驾':'包车';sm2.textContent='最长一天 '+(mx/60).toFixed(1)+' 小时'}
        else if(gd.hasAttribute('data-np-g0')&&bt&&sm2){var g0=gd.getAttribute('data-np-g0').split('|');bt.textContent=g0[0];sm2.textContent=g0.slice(1).join('|');gd.removeAttribute('data-np-g0')}}
      function npDurTxt(r,m){var s=r.querySelector('.s'),tn=s&&[].slice.call(s.childNodes).filter(function(x){return x.nodeType===3&&/\d+ (小时|分)/.test(x.textContent)})[0];if(tn)tn.textContent=tn.textContent.replace(/\d+ 小时(\s*\d+ 分钟?)?|\d+ 分钟?/,npDur(m))}   // 加的站多待少待后，第二行的停留时间跟着改
      // 改过的状态：撤销、去掉、恢复
      function npClear(oi){var st=npGet();if(st.oi[oi]){delete st.oi[oi];npPut(st)}}
      function npRemove(oi,u,ak,op){var st=npGet(),l=(st.oi[oi]||[]).filter(function(o){return!((u!=null&&o.u===u)||(op&&o.op===op&&o.ak===ak))});st.oi[oi]=l;npPut(st);var A=getA(),ka=u!=null?1000+u:(op==='rep'?ak:null);if(ka!=null&&A[oi]&&A[oi][ka]!=null){delete A[oi][ka];try{localStorage.setItem(AK,JSON.stringify(A))}catch(e){}}}   // 撤销加的站 / 换回原来的：它上面的多待少待也一起清掉
      function npDrop(oi,k){var st=npGet();if(st.oi[oi]){st.oi[oi]=st.oi[oi].filter(function(o){return o.ak!==k});npPut(st)}}
      function npNextU(){var st=npGet(),m=0,k;for(k in st.oi)st.oi[k].forEach(function(o){if(o.u>m)m=o.u});return m+1}
      // ——— 候选：按 tools/nearby_prototype.py::candidates_for 的顺序（国内外分流 → 同城 → 晚上才有 → 范围 → 同处 → 本线已有 → 闭馆日 → 绕路 ≤30 分钟 → 排序），再用 replan 真试算当天时间表检查硬规则 ———
      function npWeekday(sec){var sm=sec.querySelector('header small'),m=sm&&/周([日一二三四五六])/.exec(sm.textContent);return m?'日一二三四五六'.indexOf(m[1]):null}
      function npInRoute(c,known){var cn=[c.n].concat(c.al||[]),cpt=[c.a,c.o],i,j,d,a,seg,pt;
        for(i=0;i<known.length;i++){seg=known[i][0];pt=known[i][1];
          if(!pt){for(j=0;j<cn.length;j++)if(cn[j]===seg)return true;continue}
          d=NPM.km(cpt,pt);if(d<=0.12)return true;
          for(j=0;j<cn.length;j++){a=cn[j];if(a===seg&&d<=15)return true;if(a!==seg&&Math.min(a.length,seg.length)>=3&&(a.indexOf(seg)>=0||seg.indexOf(a)>=0)&&d<=15)return true}}
        return false}
      function npLoadCells(sec,ok,bad){npEnsureModel(function(){
        function go(){var pts=[],mn=[90,180],mx=[-90,-180],cells,need,left,failed=false;
          [].slice.call(sec.querySelectorAll('.tl > .r[data-ll]')).forEach(function(r){var p=npLL(r.dataset.ll);if(p)pts.push(p)});[npLL(sec.dataset.sp),npLL(sec.dataset.ep)].forEach(function(p){if(p)pts.push(p)});
          if(!pts.length){ok([]);return}
          pts.forEach(function(p){if(p[0]<mn[0])mn[0]=p[0];if(p[1]<mn[1])mn[1]=p[1];if(p[0]>mx[0])mx[0]=p[0];if(p[1]>mx[1])mx[1]=p[1]});
          cells=NPM.shardsFor([mn[0],mn[1],mx[0],mx[1]]).filter(function(c){return window.ZNP_CELLS.indexOf(c)>=0});need=cells.filter(function(c){return!(window.ZNP&&window.ZNP[c])});left=need.length;
          if(!left){ok(cells);return}
          need.forEach(function(c){npScript('/assets/np/'+c+'.js',function(){left--;if(!left&&!failed)ok(cells)},function(){if(!failed){failed=true;bad()}})})}
        if(window.ZNP_CELLS)go();else npScript('/assets/np/_index.js',go,bad)},bad)}
      function npPool(cells){var seen={},out=[];cells.forEach(function(c){(window.ZNP[c]||[]).forEach(function(x){if(!seen[x.i]){seen[x.i]=1;out.push(x)}})});return out}
      function npCands(sec,S,kind,pool){var M=NPM,mode=sec.dataset.lm||'city',isF=art.dataset.app==='google',dest=art.dataset.dest||'',pc=sec.dataset.pc||'',sPt=npLL(S.dataset.ll),sc=npScan(sec,S,function(q){return q.hidden}),dayPts=[],lastIdx=-1,known=[],wd=npWeekday(sec),
          title=(sec.querySelector('h2')||{}).textContent||'',out=[],pS=0,t0c=sc.la?sc.la.lg.min:null,t0a=sc.lb?sc.lb.lg.min:null,ref=kind==='ins'?[sPt,sc.A,sc.C]:[sPt],sn=npCore(npName0(S)).split(/\s*·\s*/)[0];
        sc.L.forEach(function(r,i){if(!r.hidden&&r.dataset.ll){dayPts.push(npLL(r.dataset.ll));lastIdx=i}});
        [].slice.call(document.querySelectorAll('.day .tl > .r')).forEach(function(r){if(npIsDep(r)||r.classList.contains('stay')||(r.classList.contains('eat')&&!r.dataset.ll))return;var pt=npLL(r.dataset.ll),ns=[npCore(npName(r))];if(r.getAttribute('data-np-a'))ns.push(npName0(r));
          ns.forEach(function(n){n.split(/\s*·\s*/).forEach(function(seg){if(seg)known.push([seg,pt])})})});
        pool.forEach(function(c){var d0=M.km([c.a,c.o],sPt);if(d0<=0.25||(c.n===sn&&d0<=15))pS=Math.max(pS,c.p||0)});
        pool.forEach(function(c){var X=[c.a,c.o],xx=c.x||{},sp,delta,f;if(!!c.ds!==isF)return;if(isF&&c.ds!==dest)return;if(M.BIG_CITIES.indexOf(pc)>=0&&c.c!==pc)return;
          if(c.ev&&!(kind==='ins'&&sc.i>=lastIdx))return;if(!M.inReach(X,ref))return;sp=M.sameSpot(X,dayPts);if(sp==='same')return;if(npInRoute(c,known))return;
          if(wd!=null&&xx.cl!=null&&M.closedOn(xx.cl,wd))return;if(kind==='rep'&&pS&&(c.p||0)*4<pS)return;   // 换掉的是被很多条线排过的主景点时，新站不能冷门到差 4 倍以上
          if(kind==='ins'){delta=M.detourInsert(sPt,sc.C,X,t0c,mode);if(!M.detourOk(delta))return;f=(sc.C&&t0c)?M.factor(sPt,sc.C,t0c,mode):1}
          else{if(!M.replaceNear(sPt,X,mode))return;delta=M.detourReplace(sc.A,sPt,sc.C,X,t0a,t0c,mode);if(!M.detourOk(delta))return;f=Math.max((t0a&&sc.A)?M.factor(sc.A,sPt,t0a,mode):1,(t0c&&sc.C)?M.factor(sPt,sc.C,t0c,mode):1)}
          out.push({c:c,id:c.i,delta:delta,shown:M.show5(delta),has_s:!!c.s,pop:c.p||0,same:M.sameKind(c.t,c.n,S.dataset.ty||'',sn,title),f:f,approx:!!c.ap,beside:sp==='beside'})});
        return{list:M.rank(out,400),pS:pS,sn:sn}}
      // 当天预算（硬规则）：非吃饭站 ≤5（只限插入）、结束 ≤21:30（用 replan 算出的“这天几点结束”，和页面上“这天要到 N 才结束”的提示同一个数）、第一行到最后一站结束 ≤13 小时（只防荒唐的天）。
      // 行取自 replan 的真试算结果；模型加载了就用 np_model.js 的 dayBudgetOk，没加载（只是看一眼“这天是不是排满了”）用同样的数
      function npBudget(sec,ins){var res=sec._npRes,vis=(res&&res.vis)||[],rows=[],i,j,r,nx,e,k,M=npModel(),b1,b2,lastStop=-1,reason='';
        function chk(rs){var n=0,first=null,last=0,span,rsn='';if(M)return M.dayBudgetOk(rs,ins);
          rs.forEach(function(q){if(q.k==='see'||q.k==='fun')n++;if(first===null||q.s<first)first=q.s;if(q.e>last)last=q.e});span=last-(first||0);
          if(ins&&n>NP_LIM.MAX)rsn='full';else if(last>NP_LIM.END)rsn='late';else if(span>NP_LIM.SPAN)rsn='long';return{ok:rsn==='',reason:rsn,n:n,first:first||0,last:last,span:span}}
        for(i=0;i<vis.length;i++){r=vis[i];if(r.dataset.slack==='1'||r._t==null)continue;nx=null;for(j=i+1;j<vis.length;j++){if(vis[j].dataset.slack!=='1'&&vis[j]._t!=null){nx=vis[j];break}}
          k=npIsDep(r)?'dep':r.classList.contains('eat')?'eat':r.classList.contains('stay')?'stay':r.classList.contains('fun')?'fun':'see';
          e=nx?nx._t:(res.end>r._t?res.end:r._t+15);rows.push({s:r._t,e:e,k:k});if(k==='see'||k==='fun')lastStop=rows.length-1}
        if(!rows.length)return{ok:true,reason:'',n:0,first:0,last:0,span:0};
        b1=chk(rows.concat([{s:res.end,e:res.end,k:'dep'}]));          // 站数、几点结束：整天（含晚饭、回住处）
        b2=chk(rows.slice(0,lastStop+1));                               // 首尾多久：第一行到最后一站结束
        if(b1.reason==='full'||b1.reason==='late')reason=b1.reason;else if(b2.reason==='long')reason='long';
        return{ok:reason==='',reason:reason,n:b1.n,first:b2.first,last:b1.last,span:b2.span}}
      function npHm(m){return m2hm(m)}
      // 弹层里“在这之后加一个”要不要置灰：这天已经 5 个地方，或者已经排到 21:30 之后 / 首尾超过 13 小时
      function npFullWhy(sec){var b=npBudget(sec,true);if(!sec._npRes)return'';
        if(b.n>=NP_LIM.MAX)return'这天已排满（已经有 '+b.n+' 个地方）';if(b.last>NP_LIM.END)return'这天已排满（已经排到 '+npHm(b.last)+'）';if(b.span>NP_LIM.SPAN)return'这天已排满（从出发到结束已超过 '+Math.round(NP_LIM.SPAN/60)+' 小时）';return''}
      function npMkOp(S,kind,c){var op={op:kind,ak:+S.dataset.k,an:npName0(S),u:npNextU(),i:c.i,n:c.n,c:c.c,a:c.a,o:c.o,t:c.t,d:c.d,s:c.s||'',q:c.q||''};if(c.x)op.x=JSON.parse(JSON.stringify(c.x));return op}
      // 真试算：把这个候选套在当天的副本上跑一遍 replan，读出时间表
      function npTry(sec,S,kind,c){var op=npMkOp(S,kind,c),ops=npOps(sec).filter(function(o){return!(kind==='rep'&&o.op==='rep'&&o.ak===op.ak)}).concat([op]),cl=sec.cloneNode(true),b,row,arrive,M=NPM;
        cl._npTrial=ops;replan(cl);b=npBudget(cl,kind==='ins');row=cl.querySelector('.tl > .r[data-k="'+(kind==='ins'?1000+op.u:op.ak)+'"]');arrive=row?row._t:null;
        if(!b.ok)return{ok:false,reason:b.reason,b:b};
        if(arrive!=null&&!M.hoursOk(arrive,c.d,(c.x||{}).h))return{ok:false,reason:'hours',b:b};
        return{ok:true,b:b,arrive:arrive}}
      function npLabel(kind,c){var s=c.shown;if(kind==='ins')return'+'+s+' 分钟';if(c.delta>=5)return'换了多 '+s+' 分钟';if(c.delta<=-10)return'省 '+(-s)+' 分钟';return'路程差不多'}
      function npKindCh(c){var n=c.n||'';if(/寺|庙|观|祠|塔|庵/.test(n))return'寺';if(/山|峰|岭|崖|峡/.test(n))return'山';if(/湖|海|河|江|瀑|泉|潭/.test(n))return'水';return NP_TYPE[c.t]||'景'}
      function npItemHtml(kind,it,i){var c=it.c,x=c.x||{},tag=x.b?'要预约':(x.cl===1?'周一闭馆':(it.beside?'就在旁边':''));
        return'<button type="button" class="npc" data-i="'+i+'"><span class="npr"><span class="npn"><i class="npt">'+npKindCh(c)+'</i><b>'+npEsc(c.n)+'</b></span><i class="npd'+(kind==='ins'||it.delta<5?' ok':'')+'">'+npLabel(kind,it)+'</i></span><small>约 '+npDur(c.d)+(c.s?' · '+npEsc(c.s):'')+(tag?' · '+tag:'')+'</small></button>'}
      function npCommit(sec,S,kind,c){var oi=sec.dataset.oi,st=npGet(),prev=localStorage.getItem(NK),prevA=localStorage.getItem(AK),ops=st.oi[oi]||[],op,row,A0;
        if(npTotal(st)>=NP_CAP&&!(kind==='rep'&&ops.some(function(o){return o.op==='rep'&&o.ak===+S.dataset.k}))){toast('这一版已经改得很多了，先撤销几处再加');return false}
        op=npMkOp(S,kind,c);ops=ops.filter(function(o){return!(kind==='rep'&&o.op==='rep'&&o.ak===op.ak)});ops.push(op);st.oi[oi]=ops;npPut(st);
        if(kind==='rep'){A0=getA();if(A0[oi]&&A0[oi][op.ak]!=null){delete A0[oi][op.ak];try{localStorage.setItem(AK,JSON.stringify(A0))}catch(e){}}}   // 换成别的站：原来那站的多待少待不带过去
        replan(sec);
        row=kind==='ins'?sec.querySelector('.tl > .r[data-k="'+(1000+op.u)+'"]'):sec.querySelector('.tl > .r[data-k="'+op.ak+'"]');
        if(row){zjump(Math.max(0,row.getBoundingClientRect().top+(window.pageYOffset||0)-Math.round(window.innerHeight/3)));row.classList.add('flash');setTimeout(function(){row.classList.remove('flash')},1600)}
        ztrack(kind==='ins'?'顺路·加一站':'顺路·换一站');
        toast((kind==='ins'?'加上了「':'换成了「')+c.n+'」，后面的时间重排了','撤销',function(){try{if(prev==null)localStorage.removeItem(NK);else localStorage.setItem(NK,prev);if(prevA==null)localStorage.removeItem(AK);else localStorage.setItem(AK,prevA)}catch(e){}replan(sec);toast('撤销了')});return true}
      // ① 每一站可以调：多待、少待、去掉，后面的时间按同样规则重排
      function addAdj(sec){[].slice.call(sec.querySelectorAll('.tl > .r.see, .tl > .r.fun')).forEach(function(r){if(r.querySelector('.adj')||/沿途慢慢走/.test(nm(r)))return;var rb=r.querySelector('.rb');if(!rb)return;var s=rb.querySelector('.s');if(!s){s=document.createElement('p');s.className='s';rb.appendChild(s)}
          s.insertAdjacentHTML('beforeend','<button type="button" class="adj" aria-label="调整这一站">调整</button>')})}
      document.addEventListener('click',function(e){var b=e.target.closest('.adj');if(!b)return;e.preventDefault();var r=b.closest('.r'),sec=r.closest('.day'),oi=sec.dataset.oi;if(oi==null)return;var k=r.dataset.k,A2=getA(),cur=(A2[oi]||{})[k]||0,npA=r.getAttribute('data-np'),isV=npA==='v',isR=npA==='r',
          npOk=!isV&&!!r.dataset.ll&&!r.dataset.at&&!r.dataset.rain&&!r.dataset.fo&&!r.dataset.on;   // 定点的站（日落、开船、演出）、下雨换的、空档加的不能替换；虚拟行（加的）不再套娃
        var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk npk';
        function head(t,back){return'<div class="pk-h">'+(back?'<button type="button" class="pk-bk" aria-label="返回">‹</button>':'')+'<b>'+t+'</b><button type="button" class="pk-x">关上</button></div>'}
        function main(){var why=npOk?npFullWhy(sec):'',note=(isV?'这是你加的一站，不在原来的行程里。':isR?'已换成「'+npCore(nm(r)).replace(/（换的）$/,'')+'」，原来是「'+npName0(r)+'」。':'')+(cur?'现在比原来'+(cur>0?'多':'少')+'待 '+Math.abs(cur)+' 分钟。':'')+'改了以后，这天后面的时间会跟着重排';
          var offl=!navigator.onLine;   // 断网：入口上就说“没网，暂时不能加景点”，不要点进去才发现
          sh.innerHTML=head(nm(r))+'<p class="xnote">'+note+'</p><div class="xd">'+(npOk?'<button type="button" data-np="rep"'+(offl?' data-off="换" class="had" aria-disabled="true"':'')+'><b>换成…</b>'+(offl?'<small>没网，暂时不能换景点</small>':'')+'</button><button type="button" data-np="ins"'+(offl?' data-off="加" class="had" aria-disabled="true"':(why?' disabled class="had"':''))+'><b>在这之后加一个…</b>'+(offl?'<small>没网，暂时不能加景点</small>':(why?'<small>'+why+'</small>':''))+'</button>':'')
            +'<button type="button" data-d="30"><b>多待 30 分钟</b></button><button type="button" data-d="-30"><b>少待 30 分钟</b></button>'+(isV?'<button type="button" data-npu="1"><b>撤销这次添加</b></button>':'<button type="button" data-x="1"><b>去掉这一站</b><small>后面的时间往前挪</small></button>')
            +(isR?'<button type="button" data-npr="1"><b>换回原来的</b></button>':'')+(cur?'<button type="button" data-r="1"><b>恢复这一站原来的时长</b></button>':'')+'</div>'}
        function cl(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
        // 候选列表：同一个弹层里原地换内容，左上 ‹ 返回
        function list(kind){var S=r,sn=npCore(npName0(S)),ttl=kind==='ins'?'在「'+npEsc(sn)+'」之后加一个':'把「'+npEsc(sn)+'」换成';sh._kind=kind;sh.innerHTML=head(ttl,true)+'<p class="xnote">正在找附近顺路的地方…</p>';
          npLoadCells(sec,function(cells){var res=npCands(sec,S,kind,npPool(cells)),acc=[],tried=0,why={},nwhy=0,i,t,h,msg,top='';
            for(i=0;i<res.list.length&&acc.length<8&&tried<60;i++){tried++;t=npTry(sec,S,kind,res.list[i].c);
              if(t.ok)acc.push(res.list[i]);else{why[t.reason]=(why[t.reason]||0)+1;nwhy++}}
            h=head(ttl,true);if(kind==='rep'&&res.pS>=4)top='<p class="xnote">「'+npEsc(sn)+'」是这条线的主景点，换掉它，这天就和原来的不一样了。</p>';
            if(acc.length){sh.innerHTML=h+top+'<p class="xnote">'+(kind==='ins'?'都在这天的路上，多绕 30 分钟以内':'和它在同一片，路程差不多')+'</p><div class="xd">'+acc.map(function(it,j){return npItemHtml(kind,it,j)}).join('')+'</div><p class="xnote">开放时间以官网为准</p>';
              sh._acc=acc;return}
            if(nwhy){var rs=why.full?'full':why.late?'late':why.long?'long':'hours';msg=rs==='full'?'这天已经排满了（最多 '+NP_LIM.MAX+' 个地方）':rs==='late'?'这天已经排满了（'+(kind==='ins'?'再加':'换了')+'就会晚于 '+npHm(NP_LIM.END)+'）':rs==='long'?'这天已经排满了（'+(kind==='ins'?'再加':'换了')+'就会超过 '+Math.round(NP_LIM.SPAN/60)+' 小时）':'附近有，但到的时候已经关门了'}
            else msg='附近没有顺路的';
            sh.innerHTML=h+top+'<p class="xnote npe">'+msg+'</p>'},function(){sh.innerHTML=head(ttl,true)+'<p class="xnote npe">没网，稍后再试</p>'})}
        main();
        sh.addEventListener('click',function(ev){var x=ev.target.closest('button');if(!x||x.disabled)return;if(x.classList.contains('pk-x'))return cl();if(x.classList.contains('pk-bk'))return main();
          if(x.dataset.off){toast('没网，暂时不能'+x.dataset.off+'景点，联网后再试');return}
          if(x.dataset.np)return list(x.dataset.np);
          if(x.classList.contains('npc')){var it=sh._acc&&sh._acc[+x.dataset.i];if(it){cl();npCommit(sec,r,sh._kind,it.c)}return}
          var A3=getA();A3[oi]=A3[oi]||{};
          if(x.dataset.d){A3[oi][k]=(A3[oi][k]||0)+(+x.dataset.d);if(!A3[oi][k])delete A3[oi][k];try{localStorage.setItem(AK,JSON.stringify(A3))}catch(e){}cl();replan(sec);toast((+x.dataset.d>0?'多待':'少待')+' 30 分钟，后面的时间重排了');return}
          if(x.dataset.r){delete A3[oi][k];try{localStorage.setItem(AK,JSON.stringify(A3))}catch(e){}cl();replan(sec);toast('恢复了');return}
          if(x.dataset.npu){var nmv=nm(r);npRemove(oi,+k-1000);cl();replan(sec);toast('撤销了「'+npCore(nmv)+'」');return}
          if(x.dataset.npr){npRemove(oi,null,+k,'rep');cl();replan(sec);toast('换回原来的了');return}
          if(x.dataset.x){var undo0=zSnap([DK,NK,AK]),D3=getD();D3[oi]=(D3[oi]||[]).concat([+k]);var pv=r.previousElementSibling;if(pv&&pv.classList.contains('dep')&&!pv.hidden)D3[oi].push(+pv.dataset.k);try{localStorage.setItem(DK,JSON.stringify(D3))}catch(e){}npDrop(oi,+k);var nmx=nm(r);cl();replan(sec);ztrack('去掉一站');toast('去掉了「'+npCore(nmx)+'」，后面的时间往前挪了','撤销',function(){undo0();replan(sec);toast('撤销了，「'+npCore(nmx)+'」回来了')})}});
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
      window.ZR={npBudget:function(sec){var b=npBudget(sec,true);return{n:b.n,last:b.last,span:b.span,first:b.first}},shift:function(sec,mins){var oi=sec.dataset.oi;if(oi==null)return;var S2=getS(),f=rowsOf(sec).filter(function(r){return hm2m(r.dataset.t0||(r.querySelector('time')||{}).textContent)!=null})[0];if(!f)return;var cur=hm2m(S2[oi])!=null?hm2m(S2[oi]):hm2m(f.dataset.t0||f.querySelector('time').textContent);S2[oi]=m2hm(cur+mins);try{localStorage.setItem(SK,JSON.stringify(S2))}catch(e){}replan(sec)}};
      document.addEventListener('click',function(e){var b=e.target.closest('.st');if(!b)return;var sec=b.closest('.day');if(!sec)return;var cur=b.querySelector('b').textContent;
        var opts=[];for(var m=390;m<=960;m+=30)opts.push(m2hm(m));if(opts.indexOf(cur)<0)opts.push(cur),opts.sort();
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
        [].slice.call(document.querySelectorAll('.day')).forEach(function(sec,i){var old=sec.querySelector('.fc');if(old)old.remove();var sun=sec.querySelector('.sun'),cl=sec.querySelector('[data-clim]');if(!sun||!cl||sun.dataset.off==='1')return;   // 长线的 data-lat 是起点城市，查出来的预报不是当天所在地，不显示
          
          var d=new Date(d0.getTime()+i*864e5),gap=Math.round((d-now)/864e5);if(gap<0||gap>15)return;var ds=iso(d),lat=(+sun.dataset.lat).toFixed(2),lng=(+sun.dataset.lng).toFixed(2),ck='wx_'+lat+'_'+lng+'_'+ds;
          function show(w){if(!w)return;var rainy=(w.p!=null&&w.p>=60)||[61,63,65,66,67,80,81,82,95,96,99,71,73,75,85,86].indexOf(w.c)>=0;var p=document.createElement('p');p.className='fc';p.innerHTML='<b>天气预报</b>'+(WMO[w.c]||'')+' · '+Math.round(w.lo)+'–'+Math.round(w.hi)+'°C'+(w.p!=null?' · 降雨 '+w.p+'%':'')+(w.p>=60?'<em>带伞</em>':'')+(w.lo<=0?'<em>注意保暖</em>':'');cl.parentNode.insertBefore(p,cl.nextSibling);if(rainy)rainTip(sec,p)}
          var c=null;try{c=JSON.parse(sessionStorage.getItem(ck)||'null')}catch(e){}if(c)return show(c);
          fetch('https://api.open-meteo.com/v1/forecast?latitude='+lat+'&longitude='+lng+'&daily=weathercode,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=auto&start_date='+ds+'&end_date='+ds).then(function(r){return r.json()}).then(function(j){var dd=j.daily;if(!dd||!dd.time||!dd.time.length)return;var w={c:dd.weathercode[0],hi:dd.temperature_2m_max[0],lo:dd.temperature_2m_min[0],p:dd.precipitation_probability_max?dd.precipitation_probability_max[0]:null};
            try{sessionStorage.setItem(ck,JSON.stringify(w))}catch(e){}show(w)}).catch(function(){})})}
      // 下雨的话：把这天一处室外景点换成附近的室内去处（博物馆这类），可以换回去
      var IND=[];try{IND=JSON.parse((document.getElementById('indoor')||{}).textContent||'[]')}catch(e){}var RK='zouni_rain_'+me.id;
      function getR(){try{return JSON.parse(localStorage.getItem(RK)||'{}')}catch(e){return{}}}
      function km2(a,b,c,d){var r=Math.PI/180,x=(d-b)*r*Math.cos((a+c)/2*r),y=(c-a)*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
      function outdoor(sec){return[].slice.call(sec.querySelectorAll('.tl > .r.see, .tl > .r.fun')).filter(function(r){return!r.hidden&&!r.dataset.in&&!r.dataset.rain&&!r.dataset.np&&!/沿途慢慢走/.test(r.innerText)})[0]}
      function applyRain(sec){var oi=sec.dataset.oi;if(oi==null)return;var R=getR()[oi];[].slice.call(sec.querySelectorAll('.r[data-rain]')).forEach(function(r){var m=r.querySelector('.m').childNodes[0];m.textContent=r.dataset.on;delete r.dataset.rain;var a=r.querySelector('a.ic.map');if(a&&r.dataset.oh){a.href=r.dataset.oh}});
        if(!R)return;var r=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(x){return x.dataset.k==R.k&&!x.dataset.np})[0];if(!r)return;var m=r.querySelector('.m').childNodes[0];r.dataset.on=m.textContent;m.textContent=R.n+'（下雨换的）';r.dataset.rain='1';
        var a=r.querySelector('a.ic.map');if(a){r.dataset.oh=a.href;a.href='https://uri.amap.com/search?keyword='+encodeURIComponent(R.n)+'&city='+encodeURIComponent(R.c||'')+'&callnative=1';a.removeAttribute('data-ios');a.removeAttribute('data-and')}}
      function rainTip(sec,p){var oi=sec.dataset.oi;if(oi==null||!IND.length)return;var R=getR()[oi];var sun=sec.querySelector('.sun');var la=+sun.dataset.lat,lo=+sun.dataset.lng;
        if(R){p.insertAdjacentHTML('beforeend','<span class="rn">已换成「'+R.n+'」<button type="button" class="rainback">换回原来的</button></span>');p.querySelector('.rainback').addEventListener('click',function(){var R2=getR();delete R2[oi];try{localStorage.setItem(RK,JSON.stringify(R2))}catch(e){}applyRain(sec);run();toast('换回原来的了')});return}
        var o=outdoor(sec);if(!o)return;var used=Object.keys(getR()).map(function(k){return getR()[k].n});var best=IND.filter(function(x){return used.indexOf(x.n)<0}).map(function(x){return{x:x,d:km2(la,lo,x.lat,x.lng)}}).filter(function(z){return z.d<=25}).sort(function(a,b){return a.d-b.d})[0];if(!best)return;   // 只推荐 25 公里以内的，太远就不折腾
        p.insertAdjacentHTML('beforeend','<span class="rn">下雨的话，「'+o.querySelector('.m').childNodes[0].textContent.trim()+'」可以换成「'+best.x.n+'」（'+(best.d<1?'就在旁边':'约 '+best.d+' 公里')+'）<button type="button" class="rainswap">换上</button></span>');
        p.querySelector('.rainswap').addEventListener('click',function(){var R2=getR();R2[oi]={k:o.dataset.k,n:best.x.n,c:best.x.c};try{localStorage.setItem(RK,JSON.stringify(R2))}catch(e){}applyRain(sec);run();toast('换成了「'+best.x.n+'」')})}
      // 周一：博物馆多数闭馆，提醒一下
      function monday(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start;if(!s0)return;var d0=new Date(s0+'T12:00:00');
        [].slice.call(document.querySelectorAll('.day')).forEach(function(sec,i){var old=sec.querySelector('.mon');if(old)old.remove();var d=new Date(d0.getTime()+i*864e5);var wk=d.getDay();
          var rs=[].slice.call(sec.querySelectorAll('.tl > .r')).filter(function(r){return!r.hidden}),nm=function(r){return r.querySelector('.m').childNodes[0].textContent.trim()},
              sure=rs.filter(function(r){return/周一闭馆/.test(r.innerText)}).map(nm),
              maybe=(art.dataset.app==='amap')?rs.filter(function(r){return r.dataset.in&&!/周一闭馆/.test(r.innerText)&&!/秦始皇帝陵|兵马俑/.test(nm(r))}).map(nm):[];   // 没标周一闭馆的只给软提示，国外不提示（各国不一样）
          var fcl=rs.filter(function(r){return r.dataset.cw===String(wk)}).map(nm),WN='日一二三四五六',cl0=sec.querySelector('[data-clim]');   // 国外去处每周固定闭馆日（表在 build_site.FOREIGN_CLOSED）
          if(fcl.length&&cl0){var ls=wk===0&&d.getDate()+7>new Date(d.getFullYear(),d.getMonth()+1,0).getDate(),pf=document.createElement('p');pf.className='fc mon';
            pf.innerHTML='<b>这天是周'+WN[wk]+'</b>'+(ls&&fcl.length===1&&/梵蒂冈/.test(fcl[0])?'今天是月底周日，「'+fcl[0]+'」免费开放，但人极多、要排很久；想看得舒服就把出发日期改一天':'「'+fcl.slice(0,2).join('」「')+'」周'+WN[wk]+'闭馆，出发前以官网为准，或者把出发日期改一天');cl0.parentNode.insertBefore(pf,cl0.nextSibling);return}
          if(wk!==1||(!sure.length&&!maybe.length))return;
          var cl=sec.querySelector('[data-clim]');if(!cl)return;var p=document.createElement('p');p.className='fc mon';
          p.innerHTML='<b>这天是周一</b>'+(sure.length?'「'+sure.slice(0,2).join('」「')+'」周一闭馆，出发前查一下，或者把出发日期改一天':'「'+maybe.slice(0,2).join('」「')+'」这类博物馆有的周一闭馆，出发前查一下');cl.parentNode.insertBefore(p,cl.nextSibling)})}
      // 法定假日出行高峰：行程日期和假日窗口相交，就在“出发前”最上面提醒（表在 build_site.HOLIDAYS，放假安排每年 11 月才公布，这里是估的）
      var HOL=[['元旦','2027-01-01','2027-01-03'],['春节','2027-02-04','2027-02-14'],['清明','2027-04-03','2027-04-05'],['五一','2027-05-01','2027-05-05'],['端午','2027-06-09','2027-06-11'],['中秋','2027-09-15','2027-09-17'],['国庆','2027-10-01','2027-10-07'],['元旦','2028-01-01','2028-01-03'],['春节','2028-01-24','2028-02-03'],['清明','2028-04-04','2028-04-06'],['五一','2028-05-01','2028-05-05'],['端午','2028-05-27','2028-05-29'],['国庆','2028-10-01','2028-10-07']];
      function holiday(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start;if(!s0)return;var ul=document.querySelector('.pre:not(.go) ul');if(!ul)return;var old=ul.querySelector('.hol');if(old)old.remove();
        var n=document.querySelectorAll('.day').length,a=new Date(s0+'T12:00:00'),b=new Date(a.getTime()+(n-1)*864e5),iso=function(d){return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2)},
            hit=HOL.filter(function(h){return h[1]<=iso(b)&&iso(a)<=h[2]});if(!hit.length)return;var pre=(ul.parentNode.innerText||'');if(hit.every(function(h){return pre.indexOf(h[0])>=0}))return;   // 出发前已经写了这个节日的（蔚县打树花），不重复
        var li=document.createElement('li');li.className='tip hol';var md=function(x){return+x.slice(5,7)+'/'+ +x.slice(8,10)};li.innerHTML=art.dataset.app==='amap'?'<span>这几天碰上'+hit.map(function(h){return h[0]+'假期（大约 '+md(h[1])+'–'+md(h[2])+'）'}).join('、')+'：机票、住宿、景区门票会涨价，限流也更严，早点订；想避开就改一下出发日期。具体放假和调休以国务院公布的为准。</span>':'<span>这几天碰上国内'+hit.map(function(h){return h[0]+'假期（大约 '+md(h[1])+'–'+md(h[2])+'）'}).join('、')+'：从国内出发的机票会涨价、不好买，早点订；想避开就改一下出发日期。</span>';ul.insertBefore(li,ul.firstChild)}
      [].slice.call(document.querySelectorAll('.day')).forEach(applyRain);
      run();monday();holiday();var inp=document.querySelector('.dpk');if(inp)inp.addEventListener('change',function(){setTimeout(function(){run();monday();holiday()},50)})})();

    // ——— 怎么去、怎么回：换成你自己的出发地 ———
    var goEl=document.querySelector('section.go'),GO=null;try{GO=goEl?JSON.parse(goEl.dataset.go):null}catch(e){}
    function goNow(){if(!GO)return null;var o=zOrigin()||{n:GO.o,lat:null},km=o.lat!=null?zKm(o.lat,o.lng,GO.lat,GO.lng):GO.km;var mode=(+GO.drv)?'drive':(km<60?'near':(+GO.ab||km>1200)?'fly':'train');return{o:o.n,km:km,mode:mode,way:zGoWay(GO,o.n,km)}}
    if(goEl&&GO&&zOrigin()&&!GO.fx){   // 行程里写明了从哪儿出发（先到河内再坐大巴）就不按你的出发地改写var gn=goNow(),sp=goEl.querySelector('.gw span');   // 只有知道你的出发地才改写，不然保留页面上按大城市写的if(sp)sp.textContent=sp.textContent.replace(/^[^。]*。/,gn.way+'。');
      [].slice.call(document.querySelectorAll('.faq dt')).forEach(function(dt){if(/怎么去/.test(dt.textContent)&&dt.nextElementSibling)dt.nextElementSibling.textContent=gn.way+'。'})}
    function fmtD(d){return(d.getMonth()+1)+'/'+d.getDate()}
    function tripDates(){var inp=document.querySelector('.dpk'),s0=(inp&&inp.value)||art.dataset.start,d0=new Date(s0+'T12:00:00'),n=document.querySelectorAll('.day').length;return{d0:d0,dN:new Date(d0.getTime()+(n-1)*864e5),n:n}}
    // ——— 往返车票：放进“要办的事”（高铁提前 15 天开售） ———
    window.zGoItems=function(T,TK){var gn=goNow(),rt=!!(gn&&gn.mode!=='near'&&gn.mode!=='drive');if(!rt&&!(GO&&GO.legs&&GO.legs.length))return[];var td=tripDates(),city=GO.city||'',tr=!!(gn&&gn.mode==='train');
      var sale=new Date(td.d0.getTime()-15*864e5),link=tr?'https://www.12306.cn/index/':'https://m.ctrip.com/html5/flight/swift/index';
      function it(key,t,how){return{g:'往返车票',t:t,how:how,link:link,done:T.indexOf(key)>=0,tog:function(){var T2=[];try{T2=JSON.parse(localStorage.getItem(TK)||'[]')}catch(e){}var i=T2.indexOf(key);if(i>=0)T2.splice(i,1);else T2.push(key);try{localStorage.setItem(TK,JSON.stringify(T2))}catch(e){}}}}
      return(rt?[it('go:去','买去程'+(tr?'高铁票':'机票')+'：'+gn.o+' → '+city+'，'+fmtD(td.d0)+' 上午',tr?'高铁提前 15 天开售，'+fmtD(sale)+' 起能买':'机票越早越便宜'),
             it('go:回','买回程'+(tr?'高铁票':'机票')+'：'+city+' → '+gn.o+'，'+fmtD(td.dN)+' 傍晚',tr?'回程也是提前 15 天开售':'')]:[]).concat((GO.legs||[]).map(function(L){var dd=new Date(td.d0.getTime()+L[0]*864e5),sl=new Date(dd.getTime()-15*864e5),fly=L[3]==='机票';var o=it('leg:'+L[0]+L[1]+L[2],'买第 '+(L[0]+1)+' 天的'+L[3]+'：'+L[1]+' → '+L[2]+'，'+fmtD(dd),fly?'机票越早越便宜':'火车提前 15 天开售，'+fmtD(sl)+' 起能买');o.link=fly?'https://m.ctrip.com/html5/flight/swift/index':'https://www.12306.cn/index/';return o}))};   // 长线中间换城市的那几段，也要提前买票
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
    function openDay(idx){var secs=[].slice.call(document.querySelectorAll('.day'));if(!secs.length)return;var ti=todayIdx();if(idx==null){var hd_=/^#d(\d+)$/.exec(location.hash),ld_=window.zLastDay?window.zLastDay():0;idx=(ti>=0&&ti<secs.length)?ti:(hd_&&+hd_[1]>=1&&+hd_[1]<=secs.length)?+hd_[1]-1:(ld_>=1&&ld_<=secs.length)?ld_-1:0}   // 今天在行程里 > 网址里的 #dN > 上次看到的天 > 第一天
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
        h+=(secs.length>1?'<p class="tvhint">左右滑动换一天</p>':'')+'<button type="button" class="tvx2">回到整条行程</button></div>';m.innerHTML=h;var tx2=m.querySelector('.tvx2');if(tx2)tx2.addEventListener('click',close);m.querySelector('.tvx').addEventListener('click',close);
        var lb=m.querySelector('.tvlate');if(lb)lb.addEventListener('click',function(){window.ZR.shift(sec,+lb.dataset.late);ztrack('晚了重排');toast('按现在重排了，后面的时间都往后挪了');render(i)});[].slice.call(m.querySelectorAll('.tvtabs button')).forEach(function(b){b.addEventListener('click',function(){render(+b.dataset.i)})});
        var on=m.querySelector('.tvtabs .on');if(on)on.scrollIntoView({inline:'center',block:'nearest'});var nxe=m.querySelector('.tvl .nx');if(nxe)nxe.scrollIntoView({block:'center'});cur=i;if(window.zSaveDay)window.zSaveDay(i+1)}
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
    // 天数条高亮：跟着滚动走（含刚打开、从 #dN 进来）；看到哪一天记在本机，下次打开这条线可以“回到第 N 天”
    var nav=document.querySelector('.daynav'),LDK='zouni_lastday_'+me.id;
    function saveLast(d){try{localStorage.setItem(LDK,JSON.stringify({d:d,t:Date.now()}))}catch(e){}}
    window.zSaveDay=saveLast;
    window.zLastDay=function(){try{var o=JSON.parse(localStorage.getItem(LDK)||'null');return o&&o.d>=1?o.d:0}catch(e){return 0}};
    if(nav){var last=-1,tick=0,svT=0;
      function markNav(){var as=[].slice.call(nav.querySelectorAll('a')),cur=0;as.forEach(function(a,i){var s=document.getElementById('d'+(i+1));if(s&&s.getBoundingClientRect().top<140)cur=i+1});as.forEach(function(a,i){a.classList.toggle('on',i+1===cur);if(i+1===cur)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current')});
        if(cur!==last&&cur>0&&nav.classList.contains('long')){var a=as[cur-1];nav.scrollLeft=a.offsetLeft-nav.clientWidth/2+a.offsetWidth/2}
        if(cur>0&&cur!==last){clearTimeout(svT);svT=setTimeout(function(){saveLast(cur)},700)}last=cur}
      window.addEventListener('scroll',function(){if(tick)return;tick=1;requestAnimationFrame(function(){tick=0;markNav()})},{passive:true});window.addEventListener('hashchange',function(){setTimeout(markNav,50)});markNav();
      // 老用户再次打开：不自己跳（会晕），在底部提示“接着上次看到的第 N 天”，点了才去
      setTimeout(function(){var ld=window.zLastDay(),n=document.querySelectorAll('.day').length;if(document.querySelector('.toast'))return;if(ld>=2&&ld<=n&&!/^#d\d+$/.test(location.hash)&&(window.pageYOffset||0)<60&&!document.body.classList.contains('pk-open'))toast('上次看到第 '+ld+' 天','回到第 '+ld+' 天',function(){var e=document.getElementById('d'+ld);if(e)zjump(e.getBoundingClientRect().top+(window.pageYOffset||0)-56)})},900)}
    var ovm=document.querySelector('.ovmore');if(ovm)ovm.addEventListener('click',function(){document.querySelector('.overview').classList.add('open');ovm.remove()});
  }

  // ——— 地图图标：手机上直接调起高德 App（iOS / 安卓），不退回网页 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.ic.map[data-ios],a.tvnav[data-ios]');if(!a)return;var ua=navigator.userAgent,ios=/iPhone|iPad|iPod/i.test(ua),and=/Android/i.test(ua);if((!ios&&!and)||/MicroMessenger/i.test(ua))return;
    e.preventDefault();var web=a.href,gone=false,t0=Date.now();function hid(){if(document.hidden)gone=true}document.addEventListener('visibilitychange',hid);
    zOpen(ios?a.dataset.ios:a.dataset.and,'高德地图')});   // 只走高德 App，不退回网页
  // ——— 点评、小红书：手机上只开 App，电脑和微信里不放入口 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.dp[data-app],a.xhs[data-app]');if(!a)return;   // 点评、小红书一样：手机上先试 App
    var mobile=/iPhone|iPad|Android/i.test(navigator.userAgent),wx=/MicroMessenger/i.test(navigator.userAgent);if(!mobile||wx)return;
    e.preventDefault();var web=a.href,t=Date.now(),gone=false;function hid(){gone=true}document.addEventListener('visibilitychange',hid,{once:true});
    zOpen(a.dataset.app,a.classList.contains('xhs')?'小红书':'大众点评')});   // 只走 App，不退回网页
  // ——— 首页列表第 9 条起不在 HTML 里（体积太大，手机冷启动要等好几十秒）：数据在 assets/home-a.js（正当季的其余）和 home-b.js（不在最好的日子里的，等首页就绪后再取），这里拼成和原来一模一样的 <li> ———
  function hEsc(t){return String(t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;')}
  var TILEC=['#c8432f','#2e5b6b','#4f6233','#5a4a6b','#8a5a2b','#3b5a7a'];
  function hLi(a){var rid=a[0],cl=(window.ZHC&&window.ZHC[a[9]])||'{}',t=a[22],tile=(typeof t==='string'||t===1)?'<a class="tile img" href="/trip/'+rid+'/" tabindex="-1" aria-hidden="true"><img src="/img/'+(t===1?a[19]:t)+'.svg" alt="" loading="lazy"></a>':'<a class="tile" href="/trip/'+rid+'/" tabindex="-1" aria-hidden="true" style="background:'+TILEC[-t-1]+'">'+hEsc(a[25])+'</a>';
    return'<li data-band="'+a[2]+'" data-ws="'+a[3]+'" data-we="'+a[4]+'" data-os="'+a[5]+'" data-oe="'+a[6]+'" data-img="'+a[7]+'" data-comp="'+a[8]+'" data-clim="'+hEsc(cl)+'"'+(a[10]!==''?' data-lat="'+a[10]+'" data-lng="'+a[11]+'"':'')+' data-hi="'+a[12]+'" data-drv="'+a[13]+'" data-sd="'+a[14]+'" data-ab="'+a[15]+'" data-t="'+hEsc(a[16])+'" data-n="'+a[17]+'" data-pr="'+hEsc(a[18])+'" data-src="/img/'+a[19]+'.svg" data-h="/trip/'+rid+'/" data-tg="'+hEsc(a[23])+'" hidden><span class="num">00</span><div class="tx"><div class="kl"><span class="k">'+hEsc(a[1])+'</span><span class="left">'+(a[24]?'四季都能去':'')+'</span></div><h3><a href="/trip/'+rid+'/">'+hEsc(a[20])+'</a></h3><p>'+hEsc(a[21])+'</p><small>'+a[17]+' 天 · 人均 '+hEsc(a[18])+'<span class="c"></span></small></div>'+tile+'</li>'}
  function hLis(rows){var tmp=document.createElement('ol');tmp.innerHTML=rows.map(hLi).join('');return[].slice.call(tmp.children)}
  // ——— 本期：按出发日期和“我有几天”挑；快过季的先放三条，其余有海报的精编线路在前 ———
  var dc=document.querySelector('.dchips');
  if(dc){var ol=document.querySelector('.now .items'),lis=(function(){if(window.ZHA)hLis(window.ZHA).forEach(function(li){ol.appendChild(li)});return[].slice.call(ol.children)})(),mb=document.querySelector('.moreb'),band='',PG=8,shown=PG,W='日一二三四五六';
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
      ord.forEach(function(li){ol.appendChild(li);var ok=!band||li.dataset.band===band;if(!ok)return;k++;li.hidden=k>shown;li.querySelector('.num').textContent=('0'+(k+1)).slice(-2);
        var lf=li.querySelector('.left');if(lf){lf.className='left'+(li._l<=2?' urgent':'');lf.textContent=li._l<=2?(li._l===0?'今天最后一天':'最后 '+li._l+' 天'):'最好 '+f2(li.dataset.ws)+'–'+f2(li.dataset.we)}
        var c=li.querySelector('.c');if(c&&li.dataset.clim){var cl=JSON.parse(li.dataset.clim)[mo];if(cl)c.textContent=' · '+cl[0]+'°/'+cl[1]+'°'}});
      var vis=ord.filter(function(li){return!band||li.dataset.band===band}).length;
      if(mb){var rem=Math.max(0,vis-shown);mb.hidden=rem<=0;mb.textContent='再看 '+Math.min(12,rem)+' 条'+(rem>12?' · 还有 '+(rem-12)+' 条':'')}
      var today=hk&&cur===(hk.dataset.min||hk.min),d=new Date(cur+'T12:00:00');
      // 封面跟着日期换：挑这天正当季、有海报的第一条，封面图、标题、还剩几天、天数价格、当月气温、翻开链接都换
      var cv=cvp;
      if(cv&&(!today||cv._d)){var img=document.querySelector('.cover img');if(img)img.src=cv.dataset.src;var tt=cv.dataset.t,ci=tt.indexOf('，'),h2=document.querySelector('.cv h2');if(ci>0&&ci<tt.length-1){h2.textContent=tt.slice(0,ci+1);var sp=document.createElement('span');sp.className='nw';sp.textContent=tt.slice(ci+1);h2.appendChild(sp)}else h2.textContent=tt;
        document.querySelector('.cv .kick').textContent=cv._d?('从'+cv._o+'过去约 '+cv._d+' 公里 · 正当季 · 还剩 '+cv._l+' 天'):('封面故事 · '+f2(md(cur))+' 出发正当季 · 还剩 '+cv._l+' 天');
        var cl2=JSON.parse(cv.dataset.clim||'{}')[mo]||['',''],chs=document.querySelectorAll('.cv .chips span');if(chs[0])chs[0].textContent=cv.dataset.n+' 天 · 人均 '+cv.dataset.pr;if(chs[1])chs[1].textContent=mo+' 月 '+cl2[0]+'°C / '+cl2[1]+'°C';
        document.querySelector('.cv .go').href=cv.dataset.h}
      document.querySelector('.now .nt').textContent=today?'现在去正好':(f2(md(cur))+' 出发正好去');document.querySelector('.now .ns').textContent=vis+' 条，快过季的先看'}
    document.addEventListener('zouni:origin',function(){show()});
    dc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;band=b.dataset.b;shown=PG;saveHS();dc.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});show()});
    // 进了行程再返回：天数筛选、“再看 N 条”展开了多少都还在（只在返回/刷新时恢复，换标签页、新开首页回到默认）
    var HSK='zouni_home_state';function saveHS(){try{sessionStorage.setItem(HSK,JSON.stringify({band:band,shown:shown}))}catch(e){}}
    function navBack(){try{var n=performance.getEntriesByType('navigation')[0];return!n||n.type==='back_forward'||n.type==='reload'}catch(e){return true}}
    try{var hs0=JSON.parse(sessionStorage.getItem(HSK)||'null');if(hs0&&navBack()){band=/^d[123]$/.test(hs0.band||'')?hs0.band:'';shown=Math.max(PG,Math.min(200,+hs0.shown||PG));[].slice.call(dc.querySelectorAll('button')).forEach(function(x){x.classList.toggle('on',(x.dataset.b||'')===band)})}else sessionStorage.removeItem(HSK)}catch(e){}
    if(mb)mb.addEventListener('click',function(){shown+=12;saveHS();show()});
    function hlab(v){var d=new Date(v+'T12:00:00');return(v===(hk.dataset.min||hk.min)?'今天 ':'')+(d.getMonth()+1)+'/'+d.getDate()+' 周'+W[d.getDay()]+' 出发'}   // 日期条文字和线路页的“按你选的 M/D 周X 出发”同一个写法
    if(hk){hb.addEventListener('click',function(){openPicker({value:hk.value,min:hk.dataset.min||hk.min,best:null,onPick:function(v){hk.value=v;hk.dispatchEvent(new Event('change'))}})});
      hk.addEventListener('change',function(){if(!hk.value)return;cur=hk.value;shown=PG;saveHS();try{localStorage.setItem('zouni_home_date',cur);localStorage.setItem('zouni_home_datet',String(Date.now()))}catch(e){}hb.querySelector('b').textContent=hlab(cur);show();document.getElementById('now').scrollIntoView()});
      try{var h0=localStorage.getItem('zouni_home_date');if(h0&&h0>=(hk.dataset.min||hk.min)){hk.value=h0;cur=h0;hb.querySelector('b').textContent=hlab(h0)}}catch(e){}}
    show();
    // 过季的那批（只给换日期、“替我挑”用）等首页能点了再取：取到后补进列表、重排一次、通知“替我挑”重算
    (function(){var sb=document.querySelector('script[data-b]');if(!sb||!sb.getAttribute('data-b')){document.documentElement.setAttribute('data-hb','1');return}
      setTimeout(function(){var sc=document.createElement('script');sc.src=sb.getAttribute('data-b');sc.onload=function(){if(window.ZHB){var nl=hLis(window.ZHB);nl.forEach(function(li){ol.appendChild(li)});lis=lis.concat(nl)}document.documentElement.setAttribute('data-hb','1');show();document.dispatchEvent(new Event('zouni:home-data'))};sc.onerror=function(){document.documentElement.setAttribute('data-hb','err')};document.head.appendChild(sc)},0)})()}
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
    var C={'北京':[39.90,116.40],'上海':[31.23,121.47],'广州':[23.13,113.26],'深圳':[22.54,114.06],'成都':[30.66,104.07],'杭州':[30.27,120.16],'西安':[34.26,108.94],'武汉':[30.59,114.31],'南京':[32.06,118.80],'重庆':[29.56,106.55],'长沙':[28.23,112.94],'兰州':[36.06,103.83],'哈尔滨':[45.80,126.53],'乌鲁木齐':[43.83,87.62],'南宁':[22.82,108.32],'贵阳':[26.65,106.63],'呼和浩特':[40.84,111.75],'银川':[38.49,106.23],'西宁':[36.62,101.78],'海口':[20.04,110.20],'石家庄':[38.04,114.51],'济南':[36.65,117.00],'福州':[26.07,119.30],'南昌':[28.68,115.86],'合肥':[31.82,117.23],'太原':[37.87,112.55],'长春':[43.82,125.32],'大连':[38.91,121.61],'宁波':[29.87,121.54],'郑州':[34.75,113.63],'天津':[39.13,117.20],'苏州':[31.30,120.58],'厦门':[24.48,118.09],'昆明':[25.04,102.71],'沈阳':[41.80,123.43],'青岛':[36.07,120.38],'香港':[22.32,114.17]};
    var PK='zouni_pick',st={};try{st=JSON.parse(localStorage.getItem(PK)||'{}')}catch(e){}if(!st.o){try{var o0=localStorage.getItem('zouni_org');if(o0&&C[o0])st.o=o0}catch(e){}}
    var sec=document.createElement('section');sec.className='pick';var anc_=document.querySelector('.chan2')||cv;anc_.parentNode.insertBefore(sec,anc_.nextSibling);
    if(st.o==='here'&&st.lat)C['here']=[st.lat,st.lng];
    function chips(k,arr){return'<div class="pkr" data-k="'+k+'">'+arr.map(function(a){return'<button type="button" data-v="'+a[0]+'" class="'+(st[k]===a[0]?'on':'')+'">'+a[1]+'</button>'}).join('')+'</div>'}
    function km(a,b){var r=Math.PI/180,x=(b[1]-a[1])*r*Math.cos((a[0]+b[0])/2*r),y=(b[0]-a[0])*r;return Math.round(Math.sqrt(x*x+y*y)*6371)}
    function pick(){var all=[].slice.call(document.querySelectorAll('.toc .items li')).filter(function(li){return li.dataset.lat&&li.querySelector('a[href^="/trip/"]')}),o=C[st.o],seen={},sc=[];
      all.forEach(function(li){var href=li.querySelector('a[href^="/trip/"]').getAttribute('href');if(seen[href])return;seen[href]=1;var n=+li.dataset.n,d=km(o,[+li.dataset.lat,+li.dataset.lng]),s=0,why=[];
        if(d<60)return;   // 就在出发地的不推荐
        var tdy=new Date(),mdn=('0'+(tdy.getMonth()+1)).slice(-2)+'-'+('0'+tdy.getDate()).slice(-2),ws=li.dataset.ws,we=li.dataset.we;
        var okOnly=false;
        if(ws&&we){var wrp=ws>we,ins=wrp?(mdn>=ws||mdn<=we):(mdn>=ws&&mdn<=we);
          if(!ins){var os=li.dataset.os,oe=li.dataset.oe,owr=os>oe,oins=os&&oe&&(owr?(mdn>=os||mdn<=oe):(mdn>=os&&mdn<=oe));if(!oins)return;okOnly=true}}   // 不在“能去”的日子里的不推荐（原来会把 12 月的冬捕推给 10 月的人）；在“能去”但不是最好的日子里的，后面补位时扣分
        if(st.w==='o'){var cl=null;try{cl=JSON.parse(li.dataset.clim||'{}')[tdy.getMonth()+1]}catch(e){}if(cl&&(cl[1]<=-10||cl[0]<=-3))return}   // 带老人孩子：夜里零下十度以下的不推荐
        // 周末只有两三天：路上超过大半天的往后排；4–5 天也是近的优先（原来 2500 公里内一律同分）
        if(st.d==='w'){if(n>3)return;s+=d<=300?50:d<=500?35:d<=700?12:d<=1200?-10:-40}
        else if(st.d==='m'){if(n<4||n>5)return;s+=d<=500?40:d<=900?30:d<=1500?20:d<=2500?10:0}
        else{if(n<6)return;s+=10+(d<=800?10:d<=2000?5:0)}
        if(st.v==='n'&&li.dataset.sd==='1')return;   // 出行方式选了“不开车”：要自己开车的线不推荐
        if(st.w==='o'&&(li.dataset.hi==='1'||li.dataset.ab==='1'))return;   // 带老人孩子：不上高原、不出国（签证和长途飞行，国外线“出发前”还没做细）
        if(st.w==='o'&&li.dataset.drv==='1'&&n>8)s-=15;
        // 和谁去、怎么走：真的改变推荐，并且写出理由（标签来自行程本身：徒步、爬山、走路多、台阶多、坡多、带娃、海岛、温泉、古镇、红叶、高铁、不开车、自驾……）
        var tg=(li.dataset.tg||'').split('|'),hasT=function(x){return tg.indexOf(x)>=0},phys=['徒步','爬山','走路多','台阶多','坡多'].filter(hasT),whoWhy='';
        if(st.w==='o'){if(phys.length)return;   // 带老人孩子：要徒步、爬山、走很多路、爬很多台阶的线不推荐
          if(hasT('带娃'))s+=14;if(hasT('高铁')||hasT('不开车'))s+=4;whoWhy='带老人孩子：不上高原，没有长爬坡和台阶'+(hasT('带娃')?'，本来就是带娃的线':'')}
        else if(st.w==='c'){var cp=['海岛','温泉','古镇','古城','古村','小城','红叶','海边城市'].filter(hasT);if(cp.length){s+=14*Math.min(cp.length,2);whoWhy='两个人去：有'+cp[0]+'，适合慢慢逛'}if(phys.length)s-=10;if(hasT('带娃'))s-=10}
        else if(st.w==='f'){var hard=['徒步','爬山'].filter(hasT);if(hard.length){s+=10;whoWhy='和朋友去：能'+hard[0]+'，玩得尽兴'}else if(hasT('走路多')){s+=6;whoWhy='和朋友去：适合边走边逛，不用赶'}else if(hasT('自驾')){s+=8;whoWhy='和朋友去：可以自驾，路上更自由'}if(hasT('带娃'))s-=10}
        if(st.v==='n'){if(hasT('高铁')||hasT('不开车')){s+=6;whoWhy+=(whoWhy?'；':'')+'不用自己开车'}}
        else if(st.v==='a'&&(hasT('自驾')||li.dataset.drv==='1'))s+=6;
        var kk=((li.querySelector('.k')||{}).textContent||'').replace(/\s+/g,' ').trim();if(/正当季|最好/.test(kk))s+=12;if(/最后/.test(kk))s+=6;if(li.closest('#drive'))s+=st.d==='l'?10:-5;if(li.dataset.img==='1')s+=3;
        var on2=st.o==='here'?'你这里':st.o;
        if(li.dataset.ab==='1')why.push('从'+on2+'飞过去约 '+Math.max(1,Math.round(d/700+1))+' 小时');else if(d<80)why.push('就在'+on2+'附近');else if(d<=300)why.push(on2+'过去直线约 '+d+' 公里，路上至少 '+Math.max(1,Math.ceil(d/110))+' 小时（山区更久）');else if(d<=800)why.push(on2+'过去直线约 '+d+' 公里，路上要大半天');else why.push(on2+'过去直线约 '+d+' 公里，坐飞机最省事');
        if(li.dataset.ab==='1'&&st.d==='w')s-=8;
        if(okOnly){s-=15;why.push('现在也能去，不是最好的时候')}
        if(kk)why.push(kk);if(whoWhy)why.push(whoWhy);
        sc.push({s:s,li:li,href:href,d:d,why:why.join(' · ')})});
      sc.sort(function(a,b){return b.s-a.s});var top=[],dests={};sc.forEach(function(x){var t=x.li.querySelector('h3').textContent.split(' · ')[0];if(top.length<3&&(dests[t]||0)<2){dests[t]=(dests[t]||0)+1;top.push(x)}});return top}   // 同一个省最多两条（原来只许一条，成都周边几乎全在四川，近的线进不来）
    var op=false,NM={d:{w:'周末 2–3 天',m:'4–5 天',l:'一周以上'},w:{f:'自己或朋友',c:'两个人',o:'带老人孩子'}};
    function row(q,k,arr){return'<div class="pkrow"><span class="pkq">'+q+'</span>'+chips(k,arr)+'</div>'}
    function render(){var ready=st.o&&st.d&&st.w,res=ready?pick():[];
      var sm=ready?(st.o==='here'?'当前位置':st.o)+' · '+NM.d[st.d]+' · '+NM.w[st.w]:'出发地、天数、和谁去';
      sec.className='pick'+(op?' open':'');
      sec.innerHTML='<button type="button" class="pkh" aria-expanded="'+op+'"><b>替我挑三条</b><small>'+sm+'</small><i>'+(op?'收起':'展开')+'</i></button><div class="pkb"'+(op?'':' hidden')+'>'+row('出发','o',[['here','📍 当前位置']].concat(Object.keys(C).filter(function(c){return c!=='here'}).map(function(c){return[c,c]})))+row('几天','d',[['w','周末 2–3 天'],['m','4–5 天'],['l','一周以上']])+row('和谁','w',[['f','自己或朋友'],['c','两个人'],['o','带老人孩子']])+row('出行<small>可不选</small>','v',[['a','自驾也行'],['n','不开车']])+
(ready?(res.length?'<ol class="pkres">'+res.map(function(x,i){var img=x.li.querySelector('img');return'<li><a href="'+x.href+'"><span class="pkn">'+(i+1)+'</span><div><b>'+x.li.querySelector('h3').textContent+'</b><small>'+x.why+'</small></div>'+(img?'<img src="'+(img.getAttribute('src')||img.dataset.src||'')+'" alt="" loading="lazy">':'')+'</a></li>'}).join('')+'</ol><button type="button" class="pkrs">重选</button>'+(st.d==='w'&&res.length&&res.some(function(x){return x.d>450})?'<p class="pkhint">周末只有两三天：你这边当季的近线不多，这几条是现在最近的。</p>':'')+(res.length<3?'<p class="pkhint">按你选的（出发地、天数、当季、'+(st.w==='o'?'避开极寒、高原、爬坡、':'')+'路程）现在只有 '+res.length+' 条合适的；换个“玩几天”或“和谁去”会多一些。</p>':''):'<p class="pkhint">这个时间没找到合适的，换个天数试试，或者把出发日期往后挪</p>'):'<p class="pkhint">选好三项，马上给你三条</p>')+'</div>';
      sec.querySelector('.pkh').addEventListener('click',function(){op=!op;render();if(op)sec.scrollIntoView({block:'nearest'})});
      var on=op&&sec.querySelector('.pkr[data-k="o"] .on');if(on){var pr=on.parentNode;pr.scrollLeft=on.offsetLeft-pr.clientWidth/2+on.offsetWidth/2}
      var rs_=sec.querySelector('.pkrs');if(rs_)rs_.addEventListener('click',function(){st.d='';st.w='';st.v='';op=true;try{localStorage.setItem(PK,JSON.stringify(st))}catch(e){}var y=scrollY;render();scrollTo(0,y)});
      [].slice.call(sec.querySelectorAll('.pkr button')).forEach(function(b){b.addEventListener('click',function(){var k=b.parentNode.dataset.k;
          if(k==='o'&&b.dataset.v==='here'){if(!navigator.geolocation){toast('这个浏览器拿不到位置，选个城市吧');return}b.textContent='📍 定位中…';navigator.geolocation.getCurrentPosition(function(p){st.o='here';st.lat=+p.coords.latitude.toFixed(3);st.lng=+p.coords.longitude.toFixed(3);C['here']=[st.lat,st.lng];try{localStorage.setItem(PK,JSON.stringify(st))}catch(e){}var y=scrollY;render();scrollTo(0,y);document.dispatchEvent(new Event('zouni:origin'))},function(){toast('没拿到位置（可能没给定位权限），选个城市吧');b.textContent='📍 当前位置'},{timeout:8000,maximumAge:600000});return}
          st[k]=b.dataset.v;try{localStorage.setItem(PK,JSON.stringify(st));if(k==='o')localStorage.setItem('zouni_org',b.dataset.v)}catch(e){}var y=scrollY;render();scrollTo(0,y);if(k==='o')document.dispatchEvent(new Event('zouni:origin'));ztrack('替我挑·'+({o:'出发地',d:'天数',w:'和谁',v:'出行方式'}[k]||k))})})}
    document.addEventListener('zouni:home-data',function(){render()});
    render()})();
  // ——— 首页搜索：断网时不跳页（跳过去也是空的），词留在框里，明说“没网，搜不了” ———
  (function(){var f=document.querySelector('form.hsearch');if(!f)return;var msg=null;function off(){if(msg){msg.remove();msg=null}}
    f.addEventListener('submit',function(e){if(navigator.onLine)return;e.preventDefault();var i=f.querySelector('input'),q=(i.value||'').trim();off();msg=document.createElement('p');msg.className='hsmsg';msg.setAttribute('role','status');msg.textContent='没网，搜不了'+(q?'「'+q+'」':'')+'，联网后再搜（你输入的字还在）';f.parentNode.insertBefore(msg,f.nextSibling)});
    window.addEventListener('online',off);f.addEventListener('input',off)})();
  // ——— 首页“长途和自驾”：再看全部 ———
  var dm=document.querySelector('.dmore');if(dm)dm.addEventListener('click',function(){var hs=[].slice.call(document.querySelectorAll('#drive .items li[hidden]'));hs.slice(0,12).forEach(function(li){li.hidden=false});var rem=hs.length-12;if(rem<=0)dm.remove();else dm.textContent='再看 '+Math.min(12,rem)+' 条'+(rem>12?' · 还有 '+(rem-12)+' 条':'')});
  // ——— 本期：刊头“我的行程”打开面板，不占首页 ———
  var mb0=document.querySelector('.minebtn');
  if(mb0){var fv0=ld('zouni_fav');if(fv0.length)mb0.querySelector('span').textContent='我的行程 · '+fv0.length;
    mb0.addEventListener('click',function(){var fv=ld('zouni_fav'),sn=ld('zouni_seen').filter(function(x){return!fv.some(function(f){return f.id===x.id})}).slice(0,5);
      function esc(t){return String(t).replace(/</g,'&lt;')}
      function row(x,withDate){var when='<small class="mw">'+esc(zWhen(x))+'</small>';
        var a_='<a class="mr" href="/trip/'+encodeURIComponent(x.id)+'/"><span class="mt"><b>'+esc(x.label)+'</b><span>'+esc(x.title)+'</span>'+when+'</span><i class="mo">打开 ›</i></a>';return withDate?'<div class="mrw">'+a_+'<button type="button" class="mrx" data-id="'+esc(x.id)+'" aria-label="移除 '+esc(x.label)+'">移除</button></div>':a_}
      var mask=document.createElement('div');mask.className='pk-mask';var s3=document.createElement('div');s3.className='pk';
      s3.innerHTML='<div class="pk-h"><b>我的行程</b><button type="button" class="pk-x">关上</button></div><div class="xd">'+(fv.length?fv.map(function(x){return row(x,true)}).join(''):'<p class="mempty">还没有收进的行程。打开一条行程，点底部“收进行程”就会出现在这里。</p>')+(sn.length?'<p class="xg">最近看过</p>'+sn.map(function(x){return row(x,false)}).join(''):'')+'</div>';
      function cl(){mask.remove();s3.remove();document.body.classList.remove('pk-open')}
      s3.querySelector('.pk-x').addEventListener('click',cl);mask.addEventListener('click',cl);
      function syncN(){var k=ld('zouni_fav').length;mb0.querySelector('span').textContent=k?'我的行程 · '+k:'我的行程'}
      s3.addEventListener('click',function(e){var b=e.target.closest('.mrx');if(!b)return;var id=b.dataset.id,f=ld('zouni_fav'),idx=f.findIndex(function(x){return x.id===id});if(idx<0)return;var item=f[idx];f.splice(idx,1);sv('zouni_fav',f);var rowEl=b.parentNode,parent=rowEl.parentNode,nxt=rowEl.nextSibling;rowEl.remove();syncN();
        toast('已移除「'+item.label+'」','撤销',function(){var f2=ld('zouni_fav');f2.splice(Math.min(idx,f2.length),0,item);sv('zouni_fav',f2);parent.insertBefore(rowEl,nxt&&nxt.parentNode===parent?nxt:null);syncN()})});document.body.appendChild(mask);document.body.appendChild(s3);document.body.classList.add('pk-open')})}
  // ——— 本期：我的行程、最近看过 ———
  function mineEmpty(){var sec=document.getElementById('mine');if(sec&&location.hash==='#mine'&&!ld('zouni_fav').length){sec.hidden=false;sec.querySelector('ul').innerHTML='<li class=empty>还没有收进的行程。打开任意一条行程，点底部“收进行程”，就会出现在这里。</li>'}}
  window.addEventListener('hashchange',mineEmpty);mineEmpty();
  document.querySelectorAll('.mine').forEach(function(sec){var ul=sec.querySelector('ul'),k=ul.dataset.k==='fav'?'zouni_fav':'zouni_seen',xs=ld(k);if(!xs.length)return;sec.hidden=false;
    ul.innerHTML=xs.map(function(x){return'<li><a href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+String(x.label).replace(/</g,'&lt;')+' ›</b><span>'+String(x.title).replace(/</g,'&lt;')+'</span><small>'+zWhen(x).replace(/</g,'&lt;')+'</small></a></li>'}).join('')});

  // ——— 走哪儿 ———
  var flt=document.querySelector('.flt'),mon=document.querySelector('.mon');
  if(flt&&mon){
    var st={fit:true,d:'',low:false,q:'',niche:false,near:false,bud:0,tab:'domestic',drive:false,tag:'',map:false,zoom:''},inp=flt.querySelector('input'),cnt=document.querySelector('.cnt'),gl=document.querySelector('.goodline');
    // ——— 搜索也搜线路（短线长线都在）：索引 /assets/tidx.js 第一次搜索时才加载；每项 [id,名字,天数,价格,名字|标题,全文] ———
    var tr_=document.querySelector('.wtr'),tmore=false;
    var tripSearch=function(){if(!tr_)return;
      if(!st.q){tr_.hidden=true;return}
      if(!window.ZTIDX&&!navigator.onLine){tr_.hidden=false;tr_.querySelector('.rh').textContent='线路 · 没网，搜不了「'+st.q+'」';tr_.querySelector('ul').innerHTML='';tr_.querySelector('.wtm').hidden=true;return}   // 断网：词留着，明说搜不了
      if(!window.ZTIDX){if(!tripSearch.ld){tripSearch.ld=1;var sc=document.createElement('script');sc.src='/assets/tidx.js';sc.onload=function(){tripSearch()};sc.onerror=function(){tripSearch.ld=0;tr_.hidden=false;tr_.querySelector('.rh').textContent='线路 · 没连上网，搜不了「'+st.q+'」';tr_.querySelector('ul').innerHTML='';tr_.querySelector('.wtm').hidden=true};document.head.appendChild(sc)}return}
      var t=st.q.toLowerCase().replace(/[\u3000]/g,' ').split(/\s+/).filter(Boolean),hits=window.ZTIDX.filter(function(x){return t.every(function(k){return x[5].indexOf(k)>=0})});
      // 相关度：名字里有（0）> 名字或标题里有（1）> 只在正文里提到（2，收起来，点“再看”才展开）；同一档里短线在前，15 天以上的长线靠后
      hits.forEach(function(x){x._t=t.every(function(k){return String(x[1]).toLowerCase().indexOf(k)>=0})?0:t.every(function(k){return x[4].indexOf(k)>=0})?1:2});
      hits.sort(function(a,b){return(a._t-b._t)||((a[2]>=15)-(b[2]>=15))||(a[2]-b[2])});
      tr_.hidden=!hits.length;if(!hits.length)return;
      var core=hits.filter(function(x){return x._t<2}),all_=(core.length&&!tmore)?core:hits,lim=tmore?hits.length:10,ul=tr_.querySelector('ul'),mb=tr_.querySelector('.wtm');
      tr_.querySelector('.rh').textContent='线路 · '+(core.length&&!tmore?core.length:hits.length)+' 条';
      ul.innerHTML=all_.slice(0,lim).map(function(x){return'<li><a href="/trip/'+x[0]+'/"><b>'+String(x[1]).replace(/</g,'&lt;')+'</b><span>'+x[2]+' 天 · '+x[3]+'</span></a></li>'}).join('');
      var more_=hits.length-Math.min(all_.length,lim);mb.hidden=more_<=0&&all_.length<=lim;mb.textContent=(core.length&&!tmore&&hits.length>core.length)?'再看 '+(hits.length-Math.min(core.length,lim))+' 条（含只在正文里提到的）':'再看 '+(hits.length-lim)+' 条线路';
      var shown=document.querySelectorAll('#'+st.tab+' .card:not([hidden])').length;if(!shown)cnt.textContent='目的地里没有「'+st.q+'」，线路里有 '+hits.length+' 条';
      };
    if(tr_)tr_.querySelector('.wtm').addEventListener('click',function(){tmore=true;tripSearch()});
    var on=mon.querySelector('button.on');if(on)mon.scrollLeft=on.offsetLeft-(mon.clientWidth-on.offsetWidth)/2;
    function curM(){var b=mon.querySelector('button.on');return b?+b.dataset.m:new Date().getMonth()+1}
    function near(best,m){return best.some(function(x){return Math.abs((x-m+12)%12)===1||Math.abs((m-x+12)%12)===1})}
    function save(){try{var st_=JSON.parse(JSON.stringify(st));st_.q='';sessionStorage.setItem('zouni_where',JSON.stringify({st:st_,m:curM(),open:!flt.hidden}))}catch(e){}}
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
        if(st.tag&&(c.dataset.tags||'').split(',').indexOf(st.tag)<0)ok=false;
        if(st.bud&&!(c.dataset.plo!==''&&+c.dataset.plo<=st.bud))ok=false;
        if(st.near&&!(c.dataset.km&&+c.dataset.km<=500))ok=false;
        if(st.q){var bl_=c.dataset.q.toLowerCase();if(!st.q.split(/\s+/).filter(Boolean).every(function(k){return bl_.indexOf(k)>=0}))ok=false}
        var hp=c.querySelector('.hit'),why=st.q?c.dataset.hits.split('|').filter(function(h){return h.toLowerCase().indexOf(st.q)>=0}).slice(0,3):[];hp.hidden=!why.length;hp.textContent=why.length?'有 '+why.join('、'):'';
        c.hidden=!ok;var inTab=c.closest('.scope').id===st.tab;if(ok&&inTab)n++;if(v==='正好'&&inTab)good.push(c.dataset.name)});
      document.querySelectorAll('.reg').forEach(function(r){r.hidden=!r.querySelector('.card:not([hidden])')});
      if(st.q&&!n&&!apply.sw){var tabs_=[].slice.call(document.querySelectorAll('.tabs button')),other=tabs_.filter(function(b){var sc=document.getElementById(b.dataset.t);return sc&&sc.querySelector('.card:not([hidden])')})[0];if(other){apply.sw=true;other.click();apply.sw=false;return}}   // 搜的东西在别的页签里（搜“巴黎”在国内页签是空的）：自动切过去
      if(st.q)[].slice.call(document.querySelectorAll('.card:not([hidden])')).forEach(function(c){if((c.dataset.name||'').toLowerCase().indexOf(st.q)>=0&&c.parentNode.firstChild!==c)c.parentNode.insertBefore(c,c.parentNode.firstChild)});   // 名字就含搜索词的排最前
      var oth_=st.q?[].slice.call(document.querySelectorAll('.tabs button')).filter(function(b){var sc=document.getElementById(b.dataset.t);return b.dataset.t!==st.tab&&sc&&sc.querySelector('.card:not([hidden])')}).map(function(b){return b.textContent.replace(/\s*·.*$/,'')+' '+document.getElementById(b.dataset.t).querySelectorAll('.card:not([hidden])').length+' 个'}):[];
      var gv_=[].slice.call(document.querySelectorAll('#'+st.tab+' .card:not([hidden]) .fit')).filter(function(f){return f.textContent==='正好'}).length;cnt.textContent=(n?('符合的 '+n+' 个'+(gv_&&gv_<n?'（其中 '+gv_+' 个正好）':'')):(st.q?(oth_.length?'这个页签里没找到「'+st.q+'」':'没找到「'+st.q+'」，试试中文名，或者少写几个字'):'没有符合的，点“清空筛选”再看看'))+(oth_.length?'；别的页签还有：'+oth_.join('、'):'');if(!n&&st.q&&!oth_.length)cnt.innerHTML=cnt.innerHTML+' · <a href="/pian/">去跟片走里找</a>';
      var k=(st.tag?1:0)+(st.q?1:0)+(st.d?1:0)+(st.low?1:0)+(st.niche?1:0)+(st.near?1:0)+(st.bud?1:0)+(st.fit?0:1);ft.textContent=(flt.hidden?'筛选':'收起')+(k?' · '+k:'')+(flt.hidden?' ▾':' ▴');ft.classList.toggle('on',k>0||!flt.hidden);clr.hidden=!k;
      if(typeof drawMap==='function')setTimeout(drawMap,0);
      var og_=flt.querySelector('select.org'),np_=[];if(st.q)np_.push('搜「'+st.q+'」 <button type="button" class="orgx" data-k="q">清除</button>');if(og_&&og_.value)np_.push('已按「'+og_.value+'」出发排序 <button type="button" class="orgx" data-k="o">清除</button>');orgn.hidden=!np_.length;orgn.innerHTML=np_.join(' · ');[].forEach.call(orgn.querySelectorAll('.orgx'),function(b){b.onclick=function(){if(b.dataset.k==='q'){st.q='';inp.value='';apply()}else{og_.value='';og_.dispatchEvent(new Event('change'))}}});
      gl.textContent=good.length?(m+' 月正好去 '+good.length+' 个：'+good.slice(0,10).join('、')+(good.length>10?' 等':'')):(m+' 月没有正好去的，看看“也行”的');tmore=false;tripSearch()}

    // ——— 走哪儿：地图看（按现在的筛选，正好的黑点、也行的绿点；点名字进目的地） ———
    var mt=document.querySelector('.mtog'),mapbox=null;
    var ZOOMS={domestic:[['东部沿海',function(p){return p.lo>=113&&p.la>=22}]],asia:[['东南亚',function(p){return p.lo>=95&&p.la<=24&&p.lo<=125}],['东北亚',function(p){return p.lo>=118&&p.la>=30}]],world:[['欧洲',function(p){return p.lo>=-12&&p.lo<=45&&p.la>=34&&p.la<=72}]]};
    function mercY(a){a=Math.max(-85,Math.min(85,a));return Math.log(Math.tan(Math.PI/4+a*Math.PI/360))*180/Math.PI}
    function loadBase(cb){if(window.ZBASE)return cb();if(loadBase.q){loadBase.q.push(cb);return}loadBase.q=[cb];var sc=document.createElement('script');sc.src='/assets/basemap.js';sc.onload=function(){var q=loadBase.q;loadBase.q=null;q.forEach(function(f){f()})};sc.onerror=function(){loadBase.q=null};document.head.appendChild(sc)}
    function drawMap(){if(!mapbox)return;var cs=[].slice.call(document.querySelectorAll('#'+st.tab+' .card:not([hidden])'));
      if(!cs.length){mapbox.innerHTML='<p class="hint" style="padding:16px">没有符合的目的地</p>';return}
      if(!window.ZBASE)loadBase(function(){if(mapbox)drawMap()});
      var pts=cs.map(function(c){return{la:+c.dataset.lat,lo:+c.dataset.lng,n:c.dataset.name,f:c.querySelector('.fit').className,h:c.querySelector('a.ch').getAttribute('href')}});
      var zs=ZOOMS[st.tab]||[],zcur=null;zs.forEach(function(z){if(z[0]===st.zoom)zcur=z});if(zcur){var zp=pts.filter(zcur[1]);if(zp.length>=2)pts=zp}
      var la=pts.map(function(p){return p.la}),lo=pts.map(function(p){return p.lo}),my=la.map(mercY);
      var Wm=390,Hm=st.tab!=='domestic'?360:420,pad=34,x0_=Math.min.apply(0,lo),x1_=Math.max.apply(0,lo),y0_=Math.min.apply(0,my),y1_=Math.max.apply(0,my),sc=Math.min((Wm-2*pad)/Math.max(x1_-x0_,1),(Hm-2*pad)/Math.max(y1_-y0_,1)),cx=(x0_+x1_)/2,cy=(y0_+y1_)/2;
      function XY(a,b){return[Wm/2+(b-cx)*sc,Hm/2-(mercY(a)-cy)*sc]}
      function P(p){return XY(p.la,p.lo)}
      var u='w'+st.tab,o='<svg viewBox="0 0 '+Wm+' '+Hm+'" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="目的地分布图">'
        +'<defs><clipPath id="c'+u+'"><rect width="'+Wm+'" height="'+Hm+'"/></clipPath></defs><g><g clip-path="url(#c'+u+')"><rect width="'+Wm+'" height="'+Hm+'" class="mp-sea"/>';
      if(window.ZBASE){var vx0=cx-(Wm/2)/sc-1,vx1=cx+(Wm/2)/sc+1,vy0=cy-(Hm/2)/sc-1,vy1=cy+(Hm/2)/sc+1;
        ['w','cn'].forEach(function(key){(window.ZBASE[key]||[]).forEach(function(r){var n=(r.length-1)/2,minx=1e9,maxx=-1e9,miny=1e9,maxy=-1e9,i;for(i=1;i<r.length;i+=2){var X=r[i],Y=r[i+1];if(X<minx)minx=X;if(X>maxx)maxx=X;if(Y<miny)miny=Y;if(Y>maxy)maxy=Y}
          if(maxx<vx0||minx>vx1||mercY(maxy)<vy0||mercY(miny)>vy1)return;
          var d='',lx=-1e9,ly=-1e9,k=0;for(i=1;i<r.length;i+=2){var q=XY(r[i+1],r[i]);if(Math.abs(q[0]-lx)<.6&&Math.abs(q[1]-ly)<.6)continue;lx=q[0];ly=q[1];d+=(k++?'L':'M')+q[0].toFixed(0)+','+q[1].toFixed(0)}
          if(k>2)o+='<path d="'+d+'Z" class="mp-land" stroke-width=".7" stroke-linejoin="round"/>'})})}
      o+='</g></g>';var boxes=[],hits='',unl=[];
      pts.sort(function(a,b){return(a.f==='fit'?0:1)-(b.f==='fit'?0:1)}).forEach(function(p){var q=P(p),cl_=p.f==='fit'?'mk-fit':/ok/.test(p.f)?'mk-ok':'mk-no',w=p.n.length*12+6;
        o+='<circle cx="'+q[0].toFixed(1)+'" cy="'+q[1].toFixed(1)+'" r="'+(p.f==='fit'?5:4)+'" class="'+cl_+'"/>';var nd_=1e9;pts.forEach(function(o2){if(o2!==p){var q2=P(o2),dd=Math.hypot(q2[0]-q[0],q2[1]-q[1]);if(dd<nd_)nd_=dd}});hits+='<a href="'+p.h+'"><title>'+p.n+'</title><circle cx="'+q[0].toFixed(1)+'" cy="'+q[1].toFixed(1)+'" r="'+Math.max(5,Math.min(12,nd_/2)).toFixed(1)+'" fill="#fff" fill-opacity="0"/></a>';
        var placed=false;
        [12,10,9].forEach(function(fs){if(placed)return;var w2=p.n.length*fs+6,dy=fs;
          var cand=[[q[0]+8,q[1]+4,'start'],[q[0]-8,q[1]+4,'end'],[q[0],q[1]-9,'middle'],[q[0],q[1]+dy+5,'middle'],[q[0]+6,q[1]-8,'start'],[q[0]-6,q[1]-8,'end'],[q[0]+6,q[1]+dy+4,'start'],[q[0]-6,q[1]+dy+4,'end'],[q[0]+14,q[1]-12,'start'],[q[0]-14,q[1]-12,'end'],[q[0]+14,q[1]+dy+10,'start'],[q[0]-14,q[1]+dy+10,'end'],[q[0],q[1]-20,'middle'],[q[0],q[1]+dy+16,'middle']];
          for(var i=0;i<cand.length;i++){var c=cand[i],x0=c[2]==='start'?c[0]:c[2]==='end'?c[0]-w2:c[0]-w2/2,x1=x0+w2,y0=c[1]-dy,y1=c[1]+3;if(x0<10||x1>Wm-10||y0<10||y1>Hm-26)continue;
            if(boxes.some(function(b){return!(x1<b[0]||x0>b[2]||y1<b[1]||y0>b[3])}))continue;boxes.push([x0,y0,x1,y1]);placed=true;
            o+='<a href="'+p.h+'"><rect x="'+(x0-3)+'" y="'+(y0-3)+'" width="'+(w2+6)+'" height="'+(dy+10)+'" fill="#fff" fill-opacity="0"/><text x="'+c[0].toFixed(1)+'" y="'+c[1].toFixed(1)+'" text-anchor="'+c[2]+'" font-family="Noto Serif SC,serif" font-size="'+fs+'" font-weight="900" class="'+cl_+' mk-t" paint-order="stroke" stroke-width="3">'+p.n+'</text></a>';break}});if(!placed)unl.push(p)});
      o+=hits;
      o+='<text x="14" y="'+(Hm-14)+'" font-family="Noto Sans SC,sans-serif" font-size="10" class="mk-lg">黑点正好去，绿点也行，灰点不建议 · 点名字进去</text></svg>';
      var zb_='';if(zs.length)zb_='<div class="mzoom"><button type="button" data-z="" class="'+(st.zoom?'':'on')+'">全部</button>'+zs.map(function(z){return'<button type="button" data-z="'+z[0]+'" class="'+(st.zoom===z[0]?'on':'')+'">只看'+z[0]+'</button>'}).join('')+'</div>';
      mapbox.innerHTML=zb_+o+(unl.length?'<p class="mapmore">图上挤得没标名字的：'+unl.map(function(p){return'<a href="'+p.h+'">'+p.n+'</a>'}).join('、')+'</p>':'')}
    if(mt)mt.addEventListener('click',function(){var on=!mapbox;if(on){mapbox=document.createElement('div');mapbox.className='wmap hmap';mapbox.addEventListener('click',function(e){var b=e.target.closest('.mzoom button');if(!b)return;e.stopPropagation();st.zoom=b.dataset.z;save();drawMap()});document.querySelector('.wbar').insertAdjacentElement('afterend',mapbox);document.querySelectorAll('.scope').forEach(function(s){s.classList.add('maphide')});drawMap()}
      else{mapbox.remove();mapbox=null;document.querySelectorAll('.scope').forEach(function(s){s.classList.remove('maphide')})}mt.textContent=on?'列表看':'地图看';mt.classList.toggle('on',on);st.map=on;if(on){flt.hidden=true;apply();setTimeout(function(){if(mapbox)zjump(Math.max(0,mapbox.getBoundingClientRect().top+window.scrollY-130))},30)}else{save()}});
    mon.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});apply()});
    document.querySelectorAll('.tabs button').forEach(function(b){b.addEventListener('click',function(){st.tab=b.dataset.t;document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x===b)});apply();var sc0=document.querySelector('.wbar');if(sc0&&!mapbox){var y0=sc0.getBoundingClientRect().top+window.scrollY-112;if(window.scrollY>y0)zjump(Math.max(0,y0))}})});
    var ft=document.querySelector('.ftog'),clr=flt.querySelector('.clr');if(clr)flt.insertBefore(clr,flt.firstChild);var orgn=document.createElement('p');orgn.className='orgnote';orgn.hidden=true;gl.parentNode.insertBefore(orgn,gl.nextSibling);ft.addEventListener('click',function(){flt.hidden=!flt.hidden;apply()});
    clr.addEventListener('click',function(){st.q='';st.d='';st.low=false;st.niche=false;st.near=false;st.drive=false;st.bud=0;st.fit=true;st.tag='';inp.value='';flt.querySelectorAll('.row button').forEach(function(b){b.classList.toggle('on',b.dataset.f==='fit')});flt.querySelector('.bud').value='';apply()});
    inp.addEventListener('input',function(){st.q=inp.value.trim().toLowerCase();apply()});
    flt.querySelectorAll('.row button[data-f]').forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;
      if(f==='fit'||f==='low'||f==='niche'||f==='near'||f==='drive'){st[f]=!st[f];b.classList.toggle('on',st[f])}
      else if(f.indexOf('t:')===0){st.tag=st.tag===f.slice(2)?'':f.slice(2);flt.querySelectorAll('[data-f^="t:"]').forEach(function(x){x.classList.toggle('on',x.dataset.f==='t:'+st.tag)})}
      else{st.d=st.d===f?'':f;flt.querySelectorAll('[data-f^="d"]').forEach(function(x){x.classList.toggle('on',x.dataset.f===st.d)})}apply()})});
    var bud=flt.querySelector('.bud');bud.addEventListener('change',function(){st.bud=+bud.value||0;apply()});
    try{var sv0=JSON.parse(sessionStorage.getItem('zouni_where')||'null');if(sv0){Object.keys(sv0.st).forEach(function(k){st[k]=sv0.st[k]});
      mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',+x.dataset.m===sv0.m)});
      document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x.dataset.t===st.tab)});
      inp.value=st.q||'';bud.value=st.bud?String(st.bud):'';flt.hidden=!sv0.open;
      flt.querySelectorAll('.row button[data-f]').forEach(function(b){var f=b.dataset.f;b.classList.toggle('on',(f==='fit'||f==='low'||f==='niche'||f==='near'||f==='drive')?!!st[f]:f.indexOf('t:')===0?'t:'+st.tag===f:st.d===f)})}}catch(e){}
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
    try{var q0=new URLSearchParams(location.search).get('q');if(q0){st.q=q0.trim().toLowerCase();st.fit=false;inp.value=q0;flt.querySelectorAll('[data-f="fit"]').forEach(function(b){b.classList.remove('on')})}}catch(e){}
    apply();if(st.map&&mt)mt.click();if(st.q&&location.search.indexOf('q=')>=0){   // 搜索落地：只跳一次，落在“搜「xx」· 符合的 N 个”这一行（吸顶栏下面），结果在它下面；线路索引晚到也只往下长，不会把落点顶走
      var moved=false;['touchstart','wheel','keydown'].forEach(function(ev){window.addEventListener(ev,function(){moved=true},{passive:true,once:true})});
      var land=function(){var a=document.querySelector('.orgnote:not([hidden])')||cnt,sk=document.querySelector('.stick');if(!a)return;zjump(Math.max(0,a.getBoundingClientRect().top+(window.pageYOffset||0)-(sk?sk.offsetHeight:0)-10))};
      setTimeout(land,60);if(document.fonts&&document.fonts.ready)document.fonts.ready.then(function(){if(!moved)land()})}}
})();
(function(){
  function fixTabs(){
    var bar = document.querySelector('.ctabs'), on = bar && bar.querySelector('a.on');
    if (bar && on) bar.scrollLeft = on.offsetLeft - (bar.clientWidth - on.offsetWidth) / 2;
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', fixTabs); else fixTabs();
})();
(function(){
  var bar = document.querySelector('.chan .jump');
  if (!bar) return;
  var links = [].slice.call(bar.querySelectorAll('a')), ticking = false;
  function mark(i){
    links.forEach(function(a, k){ if (k === i) a.classList.add('on'); else a.classList.remove('on'); });
    var on = links[i];
    if (on) bar.scrollLeft = on.offsetLeft - (bar.clientWidth - on.offsetWidth) / 2;
  }
  function spy(){
    ticking = false;
    var cur = 0;
    links.forEach(function(a, k){
      var el = document.getElementById(a.getAttribute('href').slice(1));
      if (el && el.getBoundingClientRect().top <= 120) cur = k;
    });
    mark(cur);
  }
  window.addEventListener('scroll', function(){ if (!ticking) { ticking = true; requestAnimationFrame(spy); } }, {passive: true});
  links.forEach(function(a, k){ a.addEventListener('click', function(){ mark(k); }); });
  mark(0);
})();

(function(){
  // 从别的页面点进来带 #d2：版面稳定后再滚一次（页面脚本会改高度，只靠浏览器原生锚点会停在页首）
  var h=location.hash;
  if(/^#d\d+$/.test(h)){
    var go=function(){var e=document.querySelector(h);if(!e)return;var y=e.getBoundingClientRect().top+window.scrollY;try{window.scrollTo({top:y,behavior:'instant'})}catch(x){window.scrollTo(0,y)}};
    [0,300,900,2200].forEach(function(t){setTimeout(function(){if(t===0||window.scrollY<5)go()},t)});
  }
  // 浮层（按天看、改日期、加一天、去掉这一天…）打开时占一条历史，手机返回键先关浮层，而不是离开页面
  var b=document.body,open=false,pushed=false,popping=false;
  function isOpen(){return b.classList.contains('pk-open')}
  new MutationObserver(function(){
    var o=isOpen();
    if(o&&!open){open=true;try{history.pushState({zov:1},'')}catch(e){}pushed=true}
    else if(!o&&open){open=false;var had=pushed;pushed=false;if(had&&!popping){try{if(history.state&&history.state.zov)history.back()}catch(e){}}}
  }).observe(b,{attributes:true,attributeFilter:['class']});
  window.addEventListener('keydown',function(e){if(e.key==='Escape'&&isOpen()){var x=document.querySelector('.tvx')||document.querySelector('.pk-x')||document.querySelector('.pk-mask');if(x)x.click()}});
  window.addEventListener('popstate',function(){
    if(isOpen()){popping=true;var x=document.querySelector('.tvx')||document.querySelector('.pk-x')||document.querySelector('.pk-mask');if(x)x.click();setTimeout(function(){popping=false},80)}
  });
})();
  // ——— 少即是多：行程页路线图默认折成一行“看路线图” ———
  (function(){try{var ov=document.querySelector('.overview'),hm=ov&&ov.querySelector('.hmap');if(!hm)return;var b=document.createElement('button');b.type='button';b.className='mapfold';b.textContent='看路线图';b.addEventListener('click',function(){ov.classList.toggle('mapopen');b.textContent=ov.classList.contains('mapopen')?'收起路线图':'看路线图'});hm.parentNode.insertBefore(b,hm)}catch(e){}})();

// ——— 长线检索 /long/：三个控件（搜索、天数、出发月份），状态写进 URL hash ———
(function(){
  var root=document.querySelector('.lpg');if(!root)return;
  var ul=root.querySelector('.lcards'),lis=[].slice.call(ul.children),cnt=root.querySelector('.lcnt'),inp=root.querySelector('.lsearch input'),empty=root.querySelector('.lempty');
  var now=new Date(),M0=now.getMonth()+1,st={m:0,d:'',q:''},TOTAL=lis.length;
  function pad(n){return(n<10?'0':'')+n}
  function untilOk(a,b){if(!a)return 0;var md=pad(M0)+'-'+pad(now.getDate()),inside=a<=b?(md>=a&&md<=b):(md>=a||md<=b);if(inside)return 0;
    var y=now.getFullYear(),t0=new Date(y,now.getMonth(),now.getDate()),d=new Date(y,+a.slice(0,2)-1,+a.slice(3));if(d<t0)d=new Date(y+1,+a.slice(0,2)-1,+a.slice(3));return Math.round((d-t0)/864e5)}
  lis.forEach(function(li){var D=li.dataset;li._u=untilOk(D.os,D.oe);li._b=untilOk(D.bs,D.be)===0?0:1;li._n=+D.n;li._ok=(D.ok||'').split(',');li._bm=(D.bm||'').split(',')});
  function pass(li){var n=li._n;
    if(st.m&&li._ok.indexOf(String(st.m))<0)return false;
    if(st.d==='a'&&n>=20)return false;if(st.d==='b'&&(n<20||n>=30))return false;if(st.d==='c'&&n<30)return false;
    var t=st.q.toLowerCase().split(/\s+/).filter(Boolean);for(var i=0;i<t.length;i++)if(li.dataset.q.indexOf(t[i])<0)return false;
    return true}
  function hashOf(){var p=[];if(st.m)p.push('m='+st.m);if(st.d)p.push('d='+st.d);if(st.q)p.push('q='+encodeURIComponent(st.q));return p.join('&')}
  function readHash(){var o={m:0,d:'',q:''};location.hash.replace(/^#/,'').split('&').forEach(function(kv){var i=kv.indexOf('=');if(i<1)return;var k=kv.slice(0,i),v;try{v=decodeURIComponent(kv.slice(i+1))}catch(e){return}
    if(k==='m'&&/^([1-9]|1[0-2])$/.test(v))o.m=+v;else if(k==='d'&&/^[abc]$/.test(v))o.d=v;else if(k==='q')o.q=v});return o}
  function render(){
    var shown=lis.filter(pass);
    shown.sort(function(a,b){
      if(st.m){var ab=a._bm.indexOf(String(st.m))>=0?0:1,bb=b._bm.indexOf(String(st.m))>=0?0:1;if(ab!==bb)return ab-bb;return(a._u-b._u)||(b._n-a._n)}   // 选了月份：这个月最佳的在前，其次只是能去的
      return(a._u-b._u)||(a._b-b._b)||(b._n-a._n)});                                                                                     // 没选：最近能出发的在前
    lis.forEach(function(li){li.hidden=shown.indexOf(li)<0});
    shown.forEach(function(li){ul.appendChild(li)});
    [].forEach.call(root.querySelectorAll('.lchips button'),function(b){var k=b.parentNode.dataset.k,on=k==='m'?(b.dataset.m==='now'?st.m===M0:b.dataset.m===''?!st.m:+b.dataset.m===st.m):b.dataset.d===st.d;b.classList.toggle('on',on)});
    cnt.textContent='找到 '+shown.length+' 条'+((st.m||st.d||st.q)&&shown.length?'（共 '+TOTAL+'）':'');
    empty.hidden=shown.length>0;
    var hs=hashOf();try{history.replaceState(null,'',location.pathname+location.search+(hs?'#'+hs:''))}catch(e){}}
  function load(o){st.m=o.m;st.d=o.d;st.q=o.q;inp.value=o.q}
  root.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;
    if(b.closest('.lchips[data-k=m]')){var v=b.dataset.m;st.m=v===''?0:v==='now'?(st.m===M0?0:M0):(+v===st.m?0:+v)}
    else if(b.closest('.lchips[data-k=d]')){st.d=(b.dataset.d===st.d)?'':b.dataset.d}
    else if(b.classList.contains('lclr')){st.m=0;st.d='';st.q='';inp.value=''}
    else return;
    render()});
  inp.addEventListener('input',function(){st.q=inp.value.trim();render()});
  window.addEventListener('hashchange',function(){if(location.hash.replace(/^#/,'')===hashOf())return;load(readHash());render()});
  load(readHash());render();
})();
try{if(window.performance&&performance.mark)performance.mark('zouni:ready')}catch(e){}   // 脚本就绪标记：tests/slow3g_check.py 量“多久能点”
