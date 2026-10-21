#!/usr/bin/env python3
"""路线地图 · 标点贴不贴真实坐标（2026-10-19，用户：放大缩小之后站点方块的位置都是错的）。会红。

根因（已修）：第 2 天的方块（颜色类 rm-c1）和卡片一句话的类 rm-c1 撞了名，`.rm .rm-c1{margin:0}` 把方块的 -22px 偏移冲掉了，
所有第 2、5、8… 天（rm-c1）的站点方块和“住”整体偏到真实坐标的右下 22px；缩小时看不出（22px≈ 几百米），放大后一眼错位。
现在颜色类改叫 rm-dk*/rm-dt*，并且下面用机器判：每个标点的“中心”和 map.project(lngLat) 的误差 ≤ 2px。

用法（项目根目录；先 bash build/pipe.sh build/site_mp）：
    python3 tests/map_anchor_check.py build/site_mp [--inject 名字]      # 反向自检：每个名字必须变红

A1 CSS 判据（从样式表出发）：每天的颜色类（rm-dk0-2 / rm-dt0-2）作为“被选中的元素本身”时只许出现设置 --dc 的规则，不许再带 margin / width / font 之类（类名撞车就是这么出的事；`.rm-db.rm-dk1 i` 这种选的是里面的 i，不算）
A2 街道底图：第 1 / 2 / 3 天各自在 zoom 6 / 10 / 14 / 17、+ / −、双击、双指缩放、拖动后，每个标点（站 / 住 / 顺路灰点）中心与 map.project 误差 ≤ 2px
A3 动画途中（easeTo 缩放的每一帧）也 ≤ 2px：不是只在 moveend 才更新
A4 旋转 / 横屏 / 地址栏收起（容器改变大小）后 ≤ 2px
A5 总览的名字方块（D34：每个落脚城镇一个；落脚点画小点的位置 ≤ 2px，名字方块要么盖着落脚点、要么离它不超过 60px）；缩放各级都成立
A6 真值：在 maplibre 里放一个原生圆点（GeoJSON circle 图层，用的是渲染器自己的投影），读 canvas 像素找圆点中心，和方块中心 ≤ 2px（z14 / z17，第 2 天）——防“project 和真画出来的不一致”
A7 示意图兜底（瓦片全失败）：同样的缩放 / 拖动 / 双击 ≤ 2px
A8 示意图 ↔ 街道图 同一个摄像机：同一个 camera 下 sch.project 和 map.project 一致（≤1px）；街道图失败回退示意图时摄像机不被夹回去（站点位置不跳）
"""
import json, math, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *
from map_touch import Touch

INJ = {
    'class_collide': ('assets/site.css', ".rm .rm-adj2{flex:none;", ".rm .rm-dk1{margin:0}.rm .rm-adj2{flex:none;"),                       # 当年的事故：颜色类带了别的规则，第 2 天的方块丢了 -22px 偏移
    'topleft_anchor': ('assets/site.css', ".rm .rm-mk{width:44px;height:44px;margin:-22px 0 0 -22px;", ".rm .rm-mk{width:44px;height:44px;margin:0;"),   # 锚点取方块左上角
    'moveend_only': ('assets/routemap.js', "map.on('move', function () { if (inst.map === map) place(inst); });", "map.on('moveend', function () { if (inst.map === map) place(inst); });"),   # 只在 moveend 才重新定位
    'sch_stale': ('assets/routemap.js', "inst.view = inst.sch; inst.sch.onMove(function () { place(inst); });", "inst.view = inst.sch; inst.sch.onMove(function () {});"),     # 示意图移动时不重新定位
}
LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FX = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FX, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}
env = Env(INJ)
check, guard = env.check, env.guard
TOL = 2.0

ERR_JS = """(function(){var z=ZRM.cur(); if(!z||!z.view) return null; var st=z.stage.getBoundingClientRect(), out=[], mx=0, n=0, kinds={};
 z.marks.forEach(function(m){ if(m.tag||!m.kind||m.kind==='lb') return; var q=z.view.project(m.ll); var e=m.el.firstElementChild||m.el; var r=e.getBoundingClientRect();
   if(m.badge){ var b=m.box, dd=Math.max(Math.abs(m.px-q.x),Math.abs(m.py-q.y)); if(b&&m.lead&&Math.hypot(Math.max(b.x-q.x,0,q.x-b.x-b.w),Math.max(b.y-q.y,0,q.y-b.y-b.h))>60) dd=999; n++; kinds[m.kind]=(kinds[m.kind]||0)+1; if(dd>mx) mx=dd; if(dd>2) out.push('day'+(m.day+1)+':'+dd.toFixed(1)); return }      // 总览的名字方块：落脚点（画小点的地方）贴着真实坐标，名字方块要么盖着它、要么离它不超过 60px
  
   var d=Math.max(Math.abs(r.left+r.width/2-st.left-q.x),Math.abs(r.top+r.height/2-st.top-q.y)); n++; kinds[m.kind]=(kinds[m.kind]||0)+1; if(d>mx) mx=d; if(d>2) out.push(m.kind+(m.n||m.day||'')+':'+d.toFixed(1)); });
 return {mx:mx,n:n,kinds:kinds,bad:out.slice(0,6),kind:z.view.kind,z:z.view.cam().z}})()"""


class Stub:
    def __init__(self, c, mode='ok'):
        self.mode = mode
        def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
        def pbf(r):
            if self.mode == 'tiles': return r.abort()
            r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        def other(r):
            if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
            elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
            else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


def mk(br, mode='ok', w=390, h=844):
    c = new_ctx(br, None, w=w, h=h); Stub(c, mode); return c


def ready(pg, t=15000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=t)
def tiles(pg, t=12000): pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().tiles>0", timeout=t)


def open_day(pg, n, wait=True):
    pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % n)
    pg.click('#d%d .rm-open' % n); ready(pg)
    if wait: tiles(pg)
    pg.wait_for_timeout(500)


def err(pg): return pg.evaluate(ERR_JS)


with sync_playwright() as p:
    br = p.chromium.launch(args=LAUNCH)
    _wp = br.new_page(); _wp.goto('about:blank'); _wp.evaluate("document.createElement('canvas').getContext('webgl')"); _wp.close()

    with guard('A1'):
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500)
        pg.evaluate("document.querySelector('#d1 .rm-open').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('#d1 .rm-open'); ready(pg)
        r = pg.evaluate("""(function(){var names=['rm-dk0','rm-dk1','rm-dk2','rm-dt0','rm-dt1','rm-dt2'],bad=[],tot=0;
          function walk(rules){for(var i=0;i<rules.length;i++){var r=rules[i];if(r.cssRules&&!r.selectorText){walk(r.cssRules);continue}if(!r.selectorText)continue;
            names.forEach(function(n){if(r.selectorText.split(',').every(function(sp){var last=sp.trim().split(/[\\s>+~]+/).pop();return last.split('.').indexOf(n)<0})) return;tot++;for(var k=0;k<r.style.length;k++){var pn=r.style[k];if(pn!=='--dc')bad.push(r.selectorText+'{'+pn+'}')}})}}
          for(var s=0;s<document.styleSheets.length;s++){try{walk(document.styleSheets[s].cssRules)}catch(e){}}
          var cls=[];ZRM.cur().marks.forEach(function(m){if(m.el.className)cls.push(m.el.className)});return {bad:bad,tot:tot,cls:cls.slice(0,3)}})()""")
        check('A1 每天的颜色类在样式表里只设 --dc（%d 条规则命中）；撞名会让方块丢偏移' % r['tot'], r['tot'] >= 6 and not r['bad'], r)
        c.close()

    def scenario(pg, T, tag, sch=False):
        res = []
        def rec(label):
            e = err(pg)
            res.append((label, e)); return e
        e0 = rec('初始')
        if not sch:
            for z in (6, 10, 14, 17):
                pg.evaluate("ZRM.cur().map.jumpTo({zoom:%d})" % z); pg.wait_for_timeout(250); rec('zoom%d' % z)
            pg.evaluate("ZRM.cur().view.go({lng:%f,lat:%f,z:13},false)" % tuple(pg.evaluate("(function(){var c=ZRM.cur().days[ZRM.cur().sel].pts[0].ll;return [c[1],c[0]]})()")) ); pg.wait_for_timeout(300)
        else:
            pg.wait_for_timeout(300)      # （刚打开就在当天视野里，“回到视野”是置灰的，不点）
        pg.click('.rm-zi'); pg.wait_for_timeout(700); rec('+')
        pg.click('.rm-zo'); pg.wait_for_timeout(700); rec('−')
        T.double_tap(190, 300); pg.wait_for_timeout(800); rec('双击')
        T.pinch(200, 300, 60, 200); pg.wait_for_timeout(900); rec('双指缩放')
        T.pinch(200, 300, 200, 70); pg.wait_for_timeout(900); rec('双指捏合')
        T.drag(250, 400, 100, 300, dt=0.01); pg.wait_for_timeout(1300); rec('拖动（惯性后）')
        mx = max(e['mx'] for _, e in res if e); worst = max(res, key=lambda x: x[1]['mx'] if x[1] else 0)
        n = res[0][1]['n']; kinds = res[0][1]['kinds']
        check('%s：%d 个标点（%s），%d 个操作后中心与投影最大误差 %.2fpx ≤ %gpx（最差：%s）' % (tag, n, kinds, len(res), mx, TOL, worst[0]), n >= 3 and mx <= TOL, [(l, e['mx'], e['bad']) for l, e in res if e and e['mx'] > TOL])

    with guard('A2'):
        for d in (1, 2, 3):
            c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 500)
            open_day(pg, d); scenario(pg, T, 'A2 街道图 第 %d 天（颜色类 rm-dk%d）' % (d, (d - 1) % 3))
            c.close()

    with guard('A3'):
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
        r = pg.evaluate("""new Promise(function(res){var z=ZRM.cur(),map=z.map,mx=0,fr=0,bad=0;
          function one(){var st=z.stage.getBoundingClientRect(),m0=0;z.marks.forEach(function(m){if(m.tag||!m.kind||m.kind==='lb')return;var q=z.view.project(m.ll),e=m.el.firstElementChild||m.el,r=e.getBoundingClientRect();m0=Math.max(m0,Math.abs(r.left+r.width/2-st.left-q.x),Math.abs(r.top+r.height/2-st.top-q.y))});return m0}
          map.on('render',function(){fr++;var e=one();if(e>mx)mx=e;if(e>2)bad++});
          map.once('moveend',function(){setTimeout(function(){res({mx:mx,fr:fr,bad:bad})},50)});
          map.easeTo({zoom:map.getZoom()+3,duration:900,essential:true})})""")
        check('A3 缩放动画途中（%d 帧）每一帧都贴着：最大误差 %.2fpx，超 2px 的帧 %d' % (r['fr'], r['mx'], r['bad']), r['fr'] >= 5 and r['mx'] <= TOL and r['bad'] == 0, r)
        c.close()

    with guard('A4'):
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
        out = []
        pg.evaluate("ZRM.cur().map.jumpTo({zoom:14})"); pg.evaluate("ZRM.cur().map.setBearing(40)"); pg.wait_for_timeout(400); out.append(('旋转 40°', err(pg)))
        pg.evaluate("ZRM.cur().map.setBearing(0)"); pg.set_viewport_size({'width': 844, 'height': 390}); pg.wait_for_timeout(1400); out.append(('横屏', err(pg)))
        pg.set_viewport_size({'width': 390, 'height': 700}); pg.wait_for_timeout(1400); out.append(('地址栏收起（高 700）', err(pg)))
        pg.set_viewport_size({'width': 390, 'height': 844}); pg.wait_for_timeout(1400); out.append(('恢复', err(pg)))
        mx = max(e['mx'] for _, e in out)
        check('A4 旋转 / 横屏 / 视口高度变化后最大误差 %.2fpx ≤ %gpx（%s）' % (mx, TOL, ', '.join('%s %.1f' % (l, e['mx']) for l, e in out)), mx <= TOL, out)
        c.close()

    with guard('A5'):
        c = mk(br); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 500)
        pg.evaluate("document.querySelector('.mapgo').scrollIntoView({block:'center',behavior:'instant'})"); pg.click('.mapgo'); ready(pg); tiles(pg); pg.wait_for_timeout(600)
        out = [('全程', err(pg))]
        for z in (5, 8, 12, 15): pg.evaluate("ZRM.cur().map.jumpTo({zoom:%d})" % z); pg.wait_for_timeout(300); out.append(('zoom%d' % z, err(pg)))
        mx = max(e['mx'] for _, e in out); nd = out[0][1]['kinds'].get('day', 0)
        check('A5 总览：%d 个名字方块（落脚点位置），缩放各级最大误差 %.2fpx ≤ %gpx' % (nd, mx, TOL), nd >= 1 and mx <= TOL, [(l, e['mx'], e['bad']) for l, e in out if e['mx'] > TOL])
        c.close()

    with guard('A6'):
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
        pg.evaluate("""(function(){var z=ZRM.cur(),map=z.map;var f=z.days[z.sel].pts.map(function(p,i){return {type:'Feature',properties:{},geometry:{type:'Point',coordinates:[p.ll[1],p.ll[0]]}}});
          map.addSource('gt',{type:'geojson',data:{type:'FeatureCollection',features:f}});map.addLayer({id:'gt',type:'circle',source:'gt',paint:{'circle-radius':3,'circle-color':'#00ff00','circle-opacity':1}})})()""")
        outs = []
        for z in (14, 17):
            for k in range(3):
                r = pg.evaluate("""(function(a){var zz=ZRM.cur(),map=zz.map,d=zz.days[zz.sel],p=d.pts[a[1]];map.jumpTo({center:[p.ll[1],p.ll[0]],zoom:a[0]});return new Promise(function(res){map.once('idle',function(){
              var cv=map.getCanvas(),w=cv.width,h=cv.height,kk=w/cv.clientWidth,c2=document.createElement('canvas');c2.width=w;c2.height=h;var x=c2.getContext('2d');x.drawImage(cv,0,0);var q=map.project([p.ll[1],p.ll[0]]);
              var px=Math.round(q.x*kk),py=Math.round(q.y*kk),R=Math.round(10*kk),dd=x.getImageData(0,0,w,h).data,sx=0,sy=0,n=0;
              for(var yy=Math.max(0,py-R);yy<Math.min(h,py+R);yy++)for(var xx=Math.max(0,px-R);xx<Math.min(w,px+R);xx++){var o=(yy*w+xx)*4;if(dd[o]<60&&dd[o+1]>200&&dd[o+2]<60){sx+=xx;sy+=yy;n++}}
              var mk=zz.marks.filter(function(m){return m.kind==='n'&&m.n===p.n})[0],st=zz.stage.getBoundingClientRect(),r=mk.el.firstElementChild.getBoundingClientRect();
              res({n:n,dx:n?r.left+r.width/2-st.left-sx/n/kk:null,dy:n?r.top+r.height/2-st.top-sy/n/kk:null})});map.triggerRepaint()})})""", [z, k])
                outs.append((z, k + 1, r))
        ok = all(o[2]['n'] > 0 and abs(o[2]['dx']) <= TOL and abs(o[2]['dy']) <= TOL for o in outs)
        check('A6 渲染器自己画出来的圆点和方块中心重合（z14/z17 × 3 站，最大偏差 %s）' % (max([max(abs(o[2]['dx']), abs(o[2]['dy'])) for o in outs if o[2]['n']] or [-1])), ok, outs)
        c.close()

    with guard('A7'):
        c = mk(br, mode='tiles'); pg = new_page(env, c); T = Touch(c, pg); goto(env, pg, '/trip/xa3/', 500)
        for d in (1, 2):
            pg.evaluate("document.querySelector('#d%d .rm-open').scrollIntoView({block:'center',behavior:'instant'})" % d); pg.click('#d%d .rm-open' % d); ready(pg)
            pg.wait_for_function("ZRM.cur().failed", timeout=20000); pg.wait_for_timeout(500)
            scenario(pg, T, 'A7 示意图兜底 第 %d 天' % d, sch=True)
            pg.click('.rm-x'); pg.wait_for_timeout(600)
        c.close()

    with guard('A8'):
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
        r = pg.evaluate("""(function(){var z=ZRM.cur(),map=z.map,s=z.sch,out=[],ll=z.days[z.sel].pts[0].ll;
          [[11],[12],[13],[14],[15]].forEach(function(a){map.jumpTo({zoom:a[0]});var c=map.getCenter(),cam={lng:c.lng,lat:c.lat,z:map.getZoom()},ml=map.project([ll[1],ll[0]]);
            s.admit(cam);s.go(cam,false);var sp=s.project(ll);out.push({z:a[0],dx:sp.x-ml.x,dy:sp.y-ml.y,sz:s.cam().z})});return out})()""")
        mx = max(max(abs(o['dx']), abs(o['dy'])) for o in r)
        check('A8 同一个摄像机下示意图和街道图投影一致（最大差 %.2fpx）' % mx, mx <= 1, r)
        c.close()
        # 街道图在放大很多以后失败回退示意图：摄像机不被夹回去（站点位置不跳）
        c = mk(br); pg = new_page(env, c); goto(env, pg, '/trip/xa3/', 500); open_day(pg, 2)
        pg.evaluate("ZRM.cur().map.jumpTo({zoom:17})"); pg.wait_for_timeout(300)
        b = pg.evaluate("(function(){var z=ZRM.cur();return z.view.project(z.days[z.sel].pts[0].ll)})()")
        pg.evaluate("window.__fb=1;document.querySelector('.rm-map canvas').dispatchEvent(new Event('webglcontextlost'))"); pg.wait_for_timeout(800)
        a = pg.evaluate("(function(){var z=ZRM.cur();return {k:z.view.kind,p:z.view.project(z.days[z.sel].pts[0].ll)}})()")
        d = max(abs(a['p']['x'] - b['x']), abs(a['p']['y'] - b['y'])) if a['k'] == 'sch' else 999
        check('A8b 街道图在 z17 失败回退示意图：站点位置不跳（%s，变化 %.1fpx）' % (a['k'], d), a['k'] == 'sch' and d <= 1, (a, b))
        c.close()
    br.close()

env.finish('map_anchor_check')
sys.exit(1 if (env.fails or [e for e in env.errs if e.startswith('INJECT-NOT-APPLIED') or not env.inject]) else 0)
