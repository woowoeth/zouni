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
      for(var dd=1;dd<=days;dd++){var d=new Date(vy,vm,dd,12),v=iso(d),cls=[];if(v<min)cls.push('off');if(v===val)cls.push('on');if(v===min)cls.push('today');if(inBest(d))cls.push('best');if(d.getDay()===0||d.getDay()===6)cls.push('we');
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
        dtb.firstChild.textContent=fmt(d0)+'–'+fmt(new Date(d0.getTime()+(n-1)*864e5))+' ';
        var db=document.querySelector('.dock b');if(db)db.textContent=fmt(d0)+' 出发 · '+n+' 天'}
      dtb.addEventListener('click',function(){var b0=dtb.dataset.best?dtb.dataset.best.split(','):null;openPicker({value:dk.value,min:dk.dataset.min||dk.getAttribute('min'),best:b0&&b0.length===2?b0:null,onPick:function(v){dk.value=v;dk.dispatchEvent(new Event('change'))}})});
      dk.addEventListener('change',function(){if(!dk.value)return;try{localStorage.setItem(sk,dk.value)}catch(e){}applyStart(dk.value);var d=new Date(dk.value+'T12:00:00');toast('改成 '+fmt(d)+' 出发了')});
      var mn=dk.dataset.min||dk.min;try{var s0=localStorage.getItem(sk)||localStorage.getItem('zouni_home_date');if(s0&&s0>=mn&&s0!==dk.value){dk.value=s0;applyStart(s0)}}catch(e){}
      // ——— 加一天：自由活动，或从同一目的地的其他线路挑一天接上；记在本机，可以去掉 ———
      var addB=document.querySelector('.addday .add');
      if(addB){var ek='zouni_extra_'+me.id,cands=[];try{cands=JSON.parse(document.getElementById('cands').textContent)}catch(e){}
        var CN='一二三四五六七八九十';function cnDay(i){return'第'+(i<10?CN[i]:(i+1))+'天'}
        function renum(){var secs=[].slice.call(document.querySelectorAll('.day'));
          secs.forEach(function(sec,i){sec.id='d'+(i+1);var no=sec.querySelector('.no');if(no)no.textContent=('0'+(i+1)).slice(-2);var sm=sec.querySelector('header small');if(sm){var p=sm.textContent.split(' · ');sm.textContent=cnDay(i)+(p.length>1?' · '+p.slice(1).join(' · '):'')}});
          var nv=document.querySelector('.daynav');if(nv){var a=nv.querySelectorAll('a');for(var k=a.length;k<secs.length;k++)nv.insertAdjacentHTML('beforeend','<a href="#d'+(k+1)+'">'+(k+1)+'</a>');for(var k2=a.length-1;k2>=secs.length;k2--)a[k2].remove()}
          var ol=document.querySelector('.overview ol'),lis=ol?ol.children:[];
          secs.forEach(function(sec,i){if(!sec.dataset.extra)return;var li=ol.querySelector('li[data-x="'+sec.dataset.extra+'"]');if(!li){li=document.createElement('li');li.dataset.x=sec.dataset.extra;ol.appendChild(li)}
            li.innerHTML='<a href="#d'+(i+1)+'"><b>'+('0'+(i+1)).slice(-2)+'</b><i></i><span class="ot"><strong>'+sec.querySelector('h2').childNodes[0].textContent+'</strong><small>加的一天</small></span><em></em></a>'});
          [].slice.call(ol.querySelectorAll('li[data-x]')).forEach(function(li){if(!document.querySelector('.day[data-extra="'+li.dataset.x+'"]'))li.remove()});
          var h=document.querySelector('.overview h2');if(h)h.textContent=secs.length+' 天，怎么排';
          applyStart(dk.value);setTimeout(todayBar,0)}
        function dayShell(x,title,body){var sec=document.createElement('section');sec.className='day xday';sec.dataset.extra=x;
          sec.innerHTML='<header><span class="no"></span><div><small>第几天 · </small><h2>'+title+'</h2></div></header>'+body+'<button type="button" class="rmday">去掉这天</button>';return sec}
        function place(sec){var ad=document.querySelector('.addday');ad.parentNode.insertBefore(sec,ad);
          sec.querySelector('.rmday').addEventListener('click',function(){var xs=ld(ek).filter(function(e){return e.x!==sec.dataset.extra});sv(ek,xs);sec.remove();renum();toast('去掉了')})}
        function build(e){if(e.k==='free'){place(dayShell(e.x,'自由活动','<p class="lead">这天不排行程：睡到自然醒，在住的地方附近走走，补补觉，或者把前几天没逛够的地方再去一次。</p>'));return Promise.resolve()}
          return fetch('/trip/'+e.rid+'/').then(function(r){return r.text()}).then(function(h){var doc=new DOMParser().parseFromString(h,'text/html'),src=doc.getElementById('d'+(e.i+1));if(!src)return;
            var sec=dayShell(e.x,src.querySelector('h2').textContent,'');[].slice.call(src.children).forEach(function(c){if(c.tagName!=='HEADER')sec.insertBefore(c.cloneNode(true),sec.querySelector('.rmday'))});
            sec.querySelector('h2').insertAdjacentHTML('beforeend','<span class="xt">接「'+e.label+'」第 '+(e.i+1)+' 天</span>');place(sec)}).catch(function(){})}
        var chain=Promise.resolve();ld(ek).forEach(function(e){chain=chain.then(function(){return build(e)})});chain.then(renum);
        addB.addEventListener('click',function(){var mask=document.createElement('div');mask.className='pk-mask';var sh=document.createElement('div');sh.className='pk';
          var groups={};cands.forEach(function(c){(groups[c.label]=groups[c.label]||[]).push(c)});
          sh.innerHTML='<div class="pk-h"><b>加一天</b><button type="button" class="pk-x">关上</button></div><div class="xd"><button type="button" data-free="1"><b>自由活动一天</b><small>住原地，不排行程</small></button>'+
            Object.keys(groups).map(function(g){return'<p class="xg">从「'+g+'」挑一天</p>'+groups[g].map(function(c){return'<button type="button" data-rid="'+c.rid+'" data-i="'+c.i+'" data-l="'+g+'"><b>第 '+(c.i+1)+' 天 · '+c.title+'</b></button>'}).join('')}).join('')+'</div>';
          function close(){mask.remove();sh.remove();document.body.classList.remove('pk-open')}
          sh.addEventListener('click',function(ev){var b=ev.target.closest('button');if(!b)return;if(b.classList.contains('pk-x'))return close();
            var e=b.dataset.free?{k:'free',x:'f'+Date.now()}:{k:'r',x:'r'+Date.now(),rid:b.dataset.rid,i:+b.dataset.i,label:b.dataset.l};var xs=ld(ek);xs.push(e);sv(ek,xs);close();
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
      bar.addEventListener('click',function(){var tgt=nxt||sec;tgt.scrollIntoView({block:'center'});tgt.classList.add('flash');setTimeout(function(){tgt.classList.remove('flash')},1600)});
      var dock=document.querySelector('.dock');dock.parentNode.insertBefore(bar,dock);
      var nv=document.querySelectorAll('.daynav a')[idx];if(nv)nv.classList.add('now')}
    todayBar();if(dk)dk.addEventListener('change',function(){setTimeout(todayBar,0)});
    // 今晚住：标记已订
    var bk=ld('zouni_booked');document.querySelectorAll('.stays .mk').forEach(function(b){function pt(){var on=bk.indexOf(b.dataset.k)>=0;b.classList.toggle('on',on);b.textContent=on?'已订 ✓':'标记已订'}pt();
      b.addEventListener('click',function(){var i=bk.indexOf(b.dataset.k);if(i>=0)bk.splice(i,1);else bk.push(b.dataset.k);sv('zouni_booked',bk);pt()})});

    // ——— 生成分享图：封面画 + 标题 + 天数价格出发日 + 前几天安排 + 网址，长按保存发朋友圈 ———
    var shb=document.querySelector('.shot');
    if(shb)shb.addEventListener('click',function(){var W_=1080,H_=1500,cv=document.createElement('canvas');cv.width=W_;cv.height=H_;var x=cv.getContext('2d');
      var BG='#f4f2ec',INK='#1c1d1a',RED='#a63d27',SERIF='"Noto Serif SC",serif',SANS='"Noto Sans SC",sans-serif';
      x.fillStyle=BG;x.fillRect(0,0,W_,H_);
      var im=document.querySelector('.hero img'),title=document.querySelector('.hero h1').innerText,kick=document.querySelector('.hero .kick').innerText;
      function finish(){var g=x.createLinearGradient(0,600,0,980);g.addColorStop(0,'rgba(20,18,16,0)');g.addColorStop(1,'rgba(20,18,16,.85)');x.fillStyle=g;x.fillRect(0,560,W_,420);
        x.fillStyle='#f2c9bf';x.font='700 30px '+SANS;x.fillText(kick,64,860);
        x.fillStyle=BG;var fs=title.length>12?64:80;x.font='900 '+fs+'px '+SERIF;var lines=[],ln='';title.split('').forEach(function(ch){if(x.measureText(ln+ch).width>W_-128){lines.push(ln);ln=ch}else ln+=ch});lines.push(ln);
        lines.slice(-2).forEach(function(l,i,a){x.fillText(l,64,940-(a.length-1-i)*(fs+10))});
        x.fillStyle=INK;x.font='900 44px '+SERIF;var dk=document.querySelector('.dock b');x.fillText(dk?dk.innerText:'',64,1060);
        x.fillStyle='#5d5f59';x.font='30px '+SANS;var pr=document.querySelector('.glance .price');x.fillText('每人 '+(pr?pr.innerText:''),64,1110);
        var ovs=[].slice.call(document.querySelectorAll('.overview li')).slice(0,5);
        ovs.forEach(function(li,i){var y=1180+i*56;x.fillStyle=RED;x.font='900 34px '+SERIF;x.fillText(li.querySelector('b').innerText,64,y);x.fillStyle=INK;x.font='700 32px '+SANS;var t=li.querySelector('strong').innerText;if(t.length>18)t=t.slice(0,18)+'…';x.fillText(t,140,y)});
        x.fillStyle=INK;x.fillRect(64,H_-96,W_-128,2);x.font='700 28px '+SANS;x.fillStyle=INK;x.fillText('走你 · '+location.host+location.pathname,64,H_-48);
        var url=cv.toDataURL('image/png'),m=document.createElement('div');m.className='hmap-zoom shotv';
        m.innerHTML='<button type="button" class="hz-x">关上</button><div class="hz-b"><img alt="分享图" src="'+url+'"></div><p class="shotp">手机上长按图片保存；电脑上 <a download="走你-'+me.label+'.png" href="'+url+'">点这里下载</a></p>';
        document.body.appendChild(m);document.body.classList.add('pk-open');function cl(){m.remove();document.body.classList.remove('pk-open')}m.querySelector('.hz-x').addEventListener('click',cl)}
      if(im){var I=new Image();I.onload=function(){var s=Math.max(W_/I.width,980/I.height),w=I.width*s,h=I.height*s;x.drawImage(I,(W_-w)/2,980-h,w,h);finish()};I.onerror=finish;I.src=im.getAttribute('src')}else{x.fillStyle='#2e3a3f';x.fillRect(0,0,W_,980);finish()}});
    // 今晚住：看另外两档
    document.querySelectorAll('.stays .tog').forEach(function(b){b.addEventListener('click',function(){var s=b.parentElement;s.classList.toggle('open');b.textContent=s.classList.contains('open')?'收起另外两档':'看另外两档'})});
    // 天数条高亮
    var nav=document.querySelector('.daynav');if(nav){window.addEventListener('scroll',function(){var as=[].slice.call(nav.querySelectorAll('a')),cur=0;as.forEach(function(a,i){var s=document.getElementById('d'+(i+1));if(s&&s.getBoundingClientRect().top<140)cur=i+1});as.forEach(function(a,i){a.classList.toggle('on',i+1===cur)})},{passive:true})}
  }

  // ——— 点评：手机上先试 App，打不开（或在微信里）再去网页 ———
  document.addEventListener('click',function(e){var a=e.target.closest('a.dp[data-app]');if(!a)return;
    var mobile=/iPhone|iPad|Android/i.test(navigator.userAgent),wx=/MicroMessenger/i.test(navigator.userAgent);if(!mobile||wx)return;
    e.preventDefault();var web=a.href,t=Date.now(),gone=false;function hid(){gone=true}document.addEventListener('visibilitychange',hid,{once:true});
    location.href=a.dataset.app;setTimeout(function(){if(!gone&&!document.hidden&&Date.now()-t<2500)location.href=web},1200)});
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
      if(!isToday){cvp=ord.filter(function(li){return li.dataset.src&&li.dataset.img==='1'&&li._l>=7})[0]||ord.filter(function(li){return li.dataset.src&&li._l>=7})[0]||ord.filter(function(li){return li.dataset.src})[0];if(cvp){cvp.dataset.cv='1';ord=ord.filter(function(li){return li!==cvp})}}
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
      if(cv&&!today){var img=document.querySelector('.cover img');if(img)img.src=cv.dataset.src;document.querySelector('.cv h2').textContent=cv.dataset.t;
        document.querySelector('.cv .kick').textContent='封面故事 · '+f2(md(cur))+' 出发正当季 · 还剩 '+cv._l+' 天';
        var cl2=JSON.parse(cv.dataset.clim||'{}')[mo]||['',''],chs=document.querySelectorAll('.cv .chips span');if(chs[0])chs[0].textContent=cv.dataset.n+' 天 · 人均 '+cv.dataset.pr;if(chs[1])chs[1].textContent=mo+' 月 '+cl2[0]+'°C / '+cl2[1]+'°C';
        document.querySelector('.cv .go').href=cv.dataset.h}
      document.querySelector('.now .nt').textContent=today?'现在去正好':(f2(md(cur))+' 出发正好去');document.querySelector('.now .ns').textContent=vis+' 条，快过季的先看'}
    dc.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;band=b.dataset.b;all=false;dc.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});show()});
    if(mb)mb.addEventListener('click',function(){all=true;show()});
    if(hk){hb.addEventListener('click',function(){openPicker({value:hk.value,min:hk.dataset.min||hk.min,best:null,onPick:function(v){hk.value=v;hk.dispatchEvent(new Event('change'))}})});
      hk.addEventListener('change',function(){if(!hk.value)return;cur=hk.value;all=false;try{localStorage.setItem('zouni_home_date',cur)}catch(e){}var d=new Date(cur+'T12:00:00');hb.querySelector('b').textContent=(d.getMonth()+1)+'/'+d.getDate()+' 周'+W[d.getDay()]+' 出发';show();document.getElementById('now').scrollIntoView()});
      try{var h0=localStorage.getItem('zouni_home_date');if(h0&&h0>=(hk.dataset.min||hk.min)){hk.value=h0;cur=h0;var d0=new Date(h0+'T12:00:00');hb.querySelector('b').textContent=(d0.getMonth()+1)+'/'+d0.getDate()+' 周'+W[d0.getDay()]+' 出发'}}catch(e){}}
    show()}
  // ——— 路线图点一下放大看（手机上可以拖着看） ———
  document.querySelectorAll('.hmap').forEach(function(f){var svg=f.querySelector('svg');if(!svg)return;f.setAttribute('role','button');f.setAttribute('tabindex','0');f.title='点一下放大看';
    function open(e){if(e.target.closest('a'))return;var m=document.createElement('div');m.className='hmap-zoom';m.innerHTML='<button type="button" class="hz-x">关上</button><div class="hz-b"></div>';m.querySelector('.hz-b').appendChild(svg.cloneNode(true));
      document.body.appendChild(m);document.body.classList.add('pk-open');var b=m.querySelector('.hz-b');b.scrollLeft=(b.scrollWidth-b.clientWidth)/2;
      function cl(){m.remove();document.body.classList.remove('pk-open')}m.querySelector('.hz-x').addEventListener('click',cl);m.addEventListener('click',function(e){if(e.target===m)cl()})}
    f.addEventListener('click',open);f.addEventListener('keydown',function(e){if(e.key==='Enter')open(e)})});
  // ——— 本期：我的行程、最近看过 ———
  function mineEmpty(){var sec=document.getElementById('mine');if(sec&&location.hash==='#mine'&&!ld('zouni_fav').length){sec.hidden=false;sec.querySelector('ul').innerHTML='<li class=empty>还没有收进的行程。打开任意一条行程，点底部“收进行程”，就会出现在这里。</li>'}}
  window.addEventListener('hashchange',mineEmpty);mineEmpty();
  document.querySelectorAll('.mine').forEach(function(sec){var ul=sec.querySelector('ul'),k=ul.dataset.k==='fav'?'zouni_fav':'zouni_seen',xs=ld(k);if(!xs.length)return;sec.hidden=false;
    ul.innerHTML=xs.map(function(x){var s0='';try{s0=localStorage.getItem('zouni_start_'+x.id)||''}catch(e){}var when='';if(s0){var d=new Date(s0+'T12:00:00'),n=new Date();n.setHours(12,0,0,0);var left=Math.round((d-n)/864e5);when='<small>'+(d.getMonth()+1)+'/'+d.getDate()+' 出发 · '+(left>0?'还有 '+left+' 天':left===0?'就是今天':'已出发')+'</small>'}
      return'<li><a href="/trip/'+encodeURIComponent(x.id)+'/"><b>'+String(x.label).replace(/</g,'&lt;')+' ›</b><span>'+String(x.title).replace(/</g,'&lt;')+'</span>'+when+'</a></li>'}).join('')});

  // ——— 去哪儿 ———
  var flt=document.querySelector('.flt'),mon=document.querySelector('.mon');
  if(flt&&mon){
    var st={fit:true,d:'',low:false,q:'',niche:false,near:false,bud:0,tab:'domestic'},inp=flt.querySelector('input'),cnt=document.querySelector('.cnt'),gl=document.querySelector('.goodline');
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
      var Wm=390,Hm=st.tab==='asia'?300:340,pad=34,sx=Math.max((Math.max.apply(0,lo)-Math.min.apply(0,lo))*k,1),sy=Math.max(Math.max.apply(0,la)-Math.min.apply(0,la),1),sc=Math.min((Wm-2*pad)/sx,(Hm-2*pad)/sy),cx=(Math.max.apply(0,lo)+Math.min.apply(0,lo))/2;
      function P(p){return[Wm/2+(p.lo-cx)*k*sc,Hm/2-(p.la-cl)*sc]}
      var o='<svg viewBox="0 0 '+Wm+' '+Hm+'" xmlns="http://www.w3.org/2000/svg"><rect x="1" y="1" width="'+(Wm-2)+'" height="'+(Hm-2)+'" fill="#efe9dc"/><rect x="6" y="6" width="'+(Wm-12)+'" height="'+(Hm-12)+'" fill="none" stroke="#1c1d1a" stroke-width="1.2" opacity=".55"/>',boxes=[];
      pts.sort(function(a,b){return(a.f==='fit'?0:1)-(b.f==='fit'?0:1)}).forEach(function(p){var q=P(p),col=p.f==='fit'?'#1c1d1a':/ok/.test(p.f)?'#4f6233':'#8d8f88',w=p.n.length*12+6;
        o+='<circle cx="'+q[0].toFixed(1)+'" cy="'+q[1].toFixed(1)+'" r="'+(p.f==='fit'?5:4)+'" fill="'+col+'"/>';
        var cand=[[q[0]+8,q[1]+4,'start'],[q[0]-8,q[1]+4,'end'],[q[0],q[1]-9,'middle'],[q[0],q[1]+17,'middle']];
        for(var i=0;i<cand.length;i++){var c=cand[i],x0=c[2]==='start'?c[0]:c[2]==='end'?c[0]-w:c[0]-w/2,x1=x0+w,y0=c[1]-12,y1=c[1]+3;if(x0<10||x1>Wm-10||y0<10||y1>Hm-10)continue;
          if(boxes.some(function(b){return!(x1<b[0]||x0>b[2]||y1<b[1]||y0>b[3])}))continue;boxes.push([x0,y0,x1,y1]);
          o+='<a href="'+p.h+'"><rect x="'+(x0-2)+'" y="'+(y0-10)+'" width="'+(w+4)+'" height="34" fill="#efe9dc" fill-opacity="0"/><text x="'+c[0].toFixed(1)+'" y="'+c[1].toFixed(1)+'" text-anchor="'+c[2]+'" font-family="Noto Serif SC,serif" font-size="12" font-weight="900" fill="'+col+'" paint-order="stroke" stroke="#efe9dc" stroke-width="3">'+p.n+'</text></a>';break}});
      o+='<text x="14" y="'+(Hm-14)+'" font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59">黑点正好去，绿点也行，灰点不建议 · 点名字进去</text></svg>';mapbox.innerHTML=o}
    if(mt)mt.addEventListener('click',function(){var on=!mapbox;if(on){mapbox=document.createElement('div');mapbox.className='wmap hmap';document.querySelector('.wbar').insertAdjacentElement('afterend',mapbox);document.querySelectorAll('.scope').forEach(function(s){s.classList.add('maphide')});drawMap()}
      else{mapbox.remove();mapbox=null;document.querySelectorAll('.scope').forEach(function(s){s.classList.remove('maphide')})}mt.textContent=on?'列表看':'地图看';mt.classList.toggle('on',on)});
    mon.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',x===b)});apply()});
    document.querySelectorAll('.tabs button').forEach(function(b){b.addEventListener('click',function(){st.tab=b.dataset.t;document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x===b)});apply()})});
    var ft=document.querySelector('.ftog'),clr=flt.querySelector('.clr');ft.addEventListener('click',function(){flt.hidden=!flt.hidden;apply()});
    clr.addEventListener('click',function(){st.q='';st.d='';st.low=false;st.niche=false;st.near=false;st.bud=0;st.fit=true;inp.value='';flt.querySelectorAll('.row button').forEach(function(b){b.classList.toggle('on',b.dataset.f==='fit')});flt.querySelector('.bud').value='';apply()});
    inp.addEventListener('input',function(){st.q=inp.value.trim().toLowerCase();apply()});
    flt.querySelectorAll('.row button[data-f]').forEach(function(b){b.addEventListener('click',function(){var f=b.dataset.f;
      if(f==='fit'||f==='low'||f==='niche'||f==='near'){st[f]=!st[f];b.classList.toggle('on',st[f])}
      else{st.d=st.d===f?'':f;flt.querySelectorAll('[data-f^="d"]').forEach(function(x){x.classList.toggle('on',x.dataset.f===st.d)})}apply()})});
    var bud=flt.querySelector('.bud');bud.addEventListener('change',function(){st.bud=+bud.value||0;apply()});
    try{var sv0=JSON.parse(sessionStorage.getItem('zouni_where')||'null');if(sv0){Object.keys(sv0.st).forEach(function(k){st[k]=sv0.st[k]});
      mon.querySelectorAll('button').forEach(function(x){x.classList.toggle('on',+x.dataset.m===sv0.m)});
      document.querySelectorAll('.tabs button').forEach(function(x){x.classList.toggle('on',x.dataset.t===st.tab)});
      inp.value=st.q||'';bud.value=st.bud?String(st.bud):'';flt.hidden=!sv0.open;
      flt.querySelectorAll('.row button[data-f]').forEach(function(b){var f=b.dataset.f;b.classList.toggle('on',(f==='fit'||f==='low'||f==='niche'||f==='near')?!!st[f]:st.d===f)})}}catch(e){}
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
    try{var q0=new URLSearchParams(location.search).get('q');if(q0){st.q=q0.trim().toLowerCase();st.fit=false;inp.value=q0;flt.hidden=false;flt.querySelectorAll('[data-f="fit"]').forEach(function(b){b.classList.remove('on')})}}catch(e){}
    apply()}
})();
