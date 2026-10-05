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
})();
