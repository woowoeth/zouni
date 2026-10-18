/* 路线地图 · 地图 App 式整屏界面（2026-10-18 重写）。点开“看路线图 / 本日地图”才加载（空闲时可能预取）；街道底图 maplibre 再按需加载。
 * 规则和坑：docs/handoff/02-UI规范.md「路线地图」、05-注意事项.md「路线地图」。ES5 only（禁 ?. ?? flatMap .at() 箭头函数 let/const），data_checks 会扫。
 *
 * 结构：一份“模型”（从页面 DOM 读：每天的站、标题、出发/住的大概位置、车程）→ 一个整屏图层 Inst（同一时间只有一个，省 WebGL 上下文）
 *  图层 = 地图舞台（底下示意图 / 街道底图淡入，上面一张 canvas 画线和点，再上面是编号方块）+ 底部面板（三档吸附：收起 / 半屏 / 拉满；点一站换成站点卡片）+ 左上“×”、右侧控件、右下署名。
 *  点开立刻有（site.js 先放一个同款“起步壳”：×、示意图、半屏面板框），routemap.js 到了再接手；街道底图加载好后淡入覆盖示意图，不闪白。
 *  示意图和街道底图用同一套摄像机数学（Web 墨卡托，512 像素世界），所以淡入前后线和方块的位置一模一样。 */
(function () {
  if (window.ZRM) return;
  var D = document, W = window, B = D.body;
  var HOST = W.ZRM_HOST || {};
  var ART = D.querySelector('article.trip');
  var APP = ART ? ART.getAttribute('data-app') : 'amap';
  var VER = ''; try { var _m = /[?&]v=(\w+)/.exec(D.currentScript.src); VER = _m ? _m[1] : ''; } catch (e) {}
  var STYLE_URL = '/assets/map/style.json';      // 自托管（tools/map_assets.py 从 OpenFreeMap 的 liberty 取来，边界 / 国家 / 省级图层已隐藏、标注已改中文优先）
  var OFM = 'https://tiles.openfreemap.org';
  var ML_JS = '/assets/maplibre/maplibre-gl.js', ML_CSS = '/assets/maplibre/maplibre-gl.css';
  var MINZ = 2, MAXZ = 17, FITMAX = 15;
  // 合规：边界线图层（含争议边界）和国家 / 省级标注一律隐藏——现在在 tools/map_assets.py 里改进自托管样式；这里留一份同样的规则，运行时再核一遍（样式被人换成没隐藏的就不画，退回示意图）
  var HIDE_RE = /boundary|country|state|disputed/;
  var ATTR_HTML = '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
  var NOTE_OFF = '街道地图加载失败，已改用示意图';      // 有网也会失败（瓦片服务器连不上、被拦），所以不写“需要联网”
  var NOTE_NET = '没有网络，已改用示意图';
  var NOTE_LOAD = '街道地图加载中…';
  var SLOW_MS = 12000, HARD_MS = 20000;      // 以收到的瓦片数为准：地图建好后 12 秒内一块瓦片都没收到才退示意图（有瓦片在到就一直等）；脚本 / 样式每一步各等 20 秒（取到一步重新计时）
  var IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var WS = 512;      // 世界宽度（zoom 0）像素，和 maplibre 一致
  var ICON_RS = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>';
  var ICON_CP = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M12 3l4 9h-8z" fill="currentColor"/><path d="M8 12l4 9 4-9"/></svg>';

  // ——— 小工具 ———
  function qs(s, r) { return (r || D).querySelector(s); }
  function qsa(s, r) { return [].slice.call((r || D).querySelectorAll(s)); }
  function el(t, c, h) { var e = D.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pll(s) { if (!s) return null; var p = String(s).split(','); var a = parseFloat(p[0]), o = parseFloat(p[1]); return (isNaN(a) || isNaN(o)) ? null : [a, o]; }
  function rad(x) { return x * Math.PI / 180; }
  function kmd(a, b) { var dl = rad(b[1] - a[1]), p1 = rad(a[0]), p2 = rad(b[0]); return 2 * 6371 * Math.asin(Math.sqrt(Math.pow(Math.sin((p2 - p1) / 2), 2) + Math.cos(p1) * Math.cos(p2) * Math.pow(Math.sin(dl / 2), 2))); }
  function toast(t, l, f) { if (HOST.toast) HOST.toast(t, l, f); }
  function jump(y) { if (HOST.jump) HOST.jump(y); else { try { W.scrollTo({ top: y, behavior: 'instant' }); } catch (e) { W.scrollTo(0, y); } } }
  function fmt(m) { m = Math.round(m); if (m < 60) return m + ' 分钟'; var h = Math.floor(m / 60), r = m % 60; return h + ' 小时' + (r ? ' ' + r + ' 分' : ''); }
  function dayLabel(i, n) { return n <= 7 ? '第 ' + (i + 1) + ' 天' : String(i + 1); }
  function noStr(n) { return n < 100 ? ('0' + n).slice(-2) : String(n); }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }
  function now() { return W.performance && performance.now ? performance.now() : Date.now(); }
  function raf(f) { return (W.requestAnimationFrame || function (g) { return setTimeout(g, 16); })(f); }
  function kmTxt(k) { return k < 1 ? Math.round(k * 10) * 100 + ' 米' : (k < 10 ? (Math.round(k * 10) / 10) : Math.round(k)) + ' 公里'; }

  // ——— 模型：从页面读（所以去掉一站 / 顺路加站 / 换景点 / 加一天 / 去掉一天后，重读一遍就是对的，不另存状态）———
  function titleOf(sec) { var h = qs('h2', sec); if (!h) return ''; var t = ''; [].forEach.call(h.childNodes, function (n) { if (n.nodeType === 3) t += n.textContent; }); return (t || h.textContent).trim(); }
  function nameOf(r) { var m = qs('.rb > .m', r) || qs('.m', r); if (!m) return ''; var t = ''; [].forEach.call(m.childNodes, function (n) { if (n.nodeType === 3) t += n.textContent; }); return t.replace(/\s+/g, ' ').trim(); }
  function loadOf(sec) {
    var w = 0, d = 0;
    qsa('.tl > .r.dep', sec).forEach(function (r) {
      if (r.hidden) return; var mn = +r.getAttribute('data-min') || 0, s = (qs('.s', r) || {}).textContent || '';
      if (/^步行/.test(s)) w += mn; else if (/^(自驾|开车|打车|包车)/.test(s)) d += mn;
    });
    var p = []; if (w >= 5) p.push('走路约 ' + fmt(w)); if (d >= 5) p.push('开车约 ' + fmt(d)); return p;
  }
  function stayOf(sec) { var s = qs('.stays .sh span:not(.lbl)', sec); var t = s ? s.textContent.split(' · ')[0].trim() : ''; return t; }
  function siblingRow(r, dir) { var x = dir > 0 ? r.nextElementSibling : r.previousElementSibling; while (x) { if (x.classList && x.classList.contains('r') && !x.hidden) return x; x = dir > 0 ? x.nextElementSibling : x.previousElementSibling; } return null; }
  function legOf(r, dir) {      // 这一站前 / 后那一格“步行 15 分钟 / 开车 40 分钟”（站与站之间的 dep 行，名字写成“A → B”）；回住处那一格、中间隔着别的站的不算
    var x = siblingRow(r, dir);
    while (x && !x.classList.contains('dep') && !x.getAttribute('data-ll')) x = siblingRow(x, dir);
    if (!x || !x.classList.contains('dep') || nameOf(x).indexOf('→') < 0) return null;
    var s = ((qs('.s', x) || {}).textContent || '').replace(/\s+/g, ' ').trim(), mn = +x.getAttribute('data-min') || 0;
    if (!s || (!mn && !/\d+ ?(分钟|小时|分)/.test(s))) return null;      // “回去歇一下”“打车或步行”这种不是“到下一站多久”
    return { txt: s, min: mn };
  }
  function plain(p) { var c = p.cloneNode(true); qsa('.adj,button,a,.bkn,.bkl,.bkh', c).forEach(function (n) { n.parentNode.removeChild(n); }); return (c.textContent || '').replace(/\s+/g, ' ').replace(/^[\s·]+|[\s·]+$/g, ''); }
  function oneOf(r) {      // 一句话：时间格里除“待多久”以外的第一条说明（镇馆之宝 / 老店 …）；没有就只写待多久（去掉“调整”按钮、预约链接这些）
    var dur = '', extra = '';
    qsa('.rb > p', r).forEach(function (p) {
      if (p.classList.contains('m') || p.classList.contains('clw')) return;
      var t = plain(p); if (!t) return;
      if (/^\d+(\.\d+)? ?(小时|分)/.test(t) && !/[一-鿿]{3}/.test(t.replace(/小时|分钟|分/g, ''))) { if (!dur) dur = t; } else if (!extra) extra = t;
    });
    return [dur, extra].filter(Boolean).join(' · ');
  }
  function readDay(sec, i) {
    var pts = [];
    qsa('.tl > .r[data-ll]', sec).forEach(function (r) {
      if (r.hidden) return; var p = pll(r.getAttribute('data-ll')); if (!p) return;
      var eat = r.classList.contains('eat'), ty = r.getAttribute('data-ty') || '', txt = r.textContent || '', cl = /周[一二三四五六日](?:陵寝)?闭馆/.exec(txt), tm = qs('time', r);
      pts.push({ n: pts.length + 1, row: r, ll: p, name: nameOf(r), kind: eat ? 'eat' : (ty === 'ms' ? 'mu' : 'sg'), dm: +r.getAttribute('data-dm') || 0, book: !!qs('.bkn,.bkl', r), closed: cl ? cl[0] : '', one: oneOf(r), tm: tm ? tm.textContent.trim() : '', next: legOf(r, 1), prev: legOf(r, -1), nav: qs('a.ic.map', r) });
    });
    var nopos = qsa('.tl > .r.see, .tl > .r.fun', sec).filter(function (r) { return !r.hidden && !r.getAttribute('data-ll') && !/沿途/.test(nameOf(r)); }).length;
    var pv = sec.previousElementSibling; while (pv && !(pv.matches && pv.matches('section.day'))) pv = pv.previousElementSibling;
    var ps = pv ? stayOf(pv) : '', cy = sec.getAttribute('data-city') || '';
    var spName = pv ? (ps ? '昨晚住处（' + ps + '）' : '昨晚住处') : (cy ? '起点（' + cy + '）' : '起点');      // 导航起点：不叫“出发地”，写昨晚住处或具体名
    return { i: i, sec: sec, title: titleOf(sec), pts: pts, sp: pll(sec.getAttribute('data-sp')), ep: pll(sec.getAttribute('data-ep')), stay: stayOf(sec), load: loadOf(sec), nopos: nopos, spName: spName };
  }
  function readDays() { return qsa('section.day').filter(function (s) { return !s.hidden && !s.closest('[hidden]'); }).map(readDay); }
  function sig(days) { return days.map(function (d) { return d.title + '#' + d.pts.map(function (p) { return p.ll.join(',') + p.name; }).join('|'); }).join('~'); }

  // ——— 摄像机数学（Web 墨卡托，和 maplibre 同一套：512 像素世界，zoom z 时世界宽 512·2^z）———
  function lx(lng) { return (lng + 180) / 360; }
  function ly(lat) { var s = Math.sin(rad(clamp(lat, -85.0511, 85.0511))); return 0.5 - Math.log((1 + s) / (1 - s)) / (4 * Math.PI); }
  function ilng(x) { return x * 360 - 180; }
  function ilat(y) { var n = Math.PI - 2 * Math.PI * y; return 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n))); }
  function camProject(c, w, h, ll) { var s = WS * Math.pow(2, c.z); return { x: (lx(ll[1]) - lx(c.lng)) * s + w / 2, y: (ly(ll[0]) - ly(c.lat)) * s + h / 2 }; }
  // 把站点范围装进（留边后的）可视区；offset 让范围落在留边框的中心（摄像机中心 = 视口中心）
  function fitCam(b, w, h, pad, maxZ) {
    var x0 = lx(b.w), x1 = lx(b.e), y0 = ly(b.n), y1 = ly(b.s), bw = x1 - x0, bh = y1 - y0;
    var aw = Math.max(40, w - pad.l - pad.r), ah = Math.max(40, h - pad.t - pad.b), z = maxZ;
    if (bw > 1e-9 || bh > 1e-9) z = Math.min(maxZ, Math.log(Math.min(bw > 1e-9 ? aw / (bw * WS) : 1e9, bh > 1e-9 ? ah / (bh * WS) : 1e9)) / Math.LN2);
    z = clamp(z, MINZ, maxZ);
    var s = WS * Math.pow(2, z), cx = (x0 + x1) / 2 - (pad.l - pad.r) / 2 / s, cy = (y0 + y1) / 2 - (pad.t - pad.b) / 2 / s;
    return { lng: ilng(cx), lat: ilat(cy), z: z };
  }
  function centerCam(ll, z, w, h, pad) { var s = WS * Math.pow(2, z); return { lng: ilng(lx(ll[1]) - (pad.l - pad.r) / 2 / s), lat: ilat(ly(ll[0]) - (pad.t - pad.b) / 2 / s), z: z }; }
  function bbox(ll) { var s = 90, w = 180, n = -90, e = -180; ll.forEach(function (p) { if (p[0] < s) s = p[0]; if (p[0] > n) n = p[0]; if (p[1] < w) w = p[1]; if (p[1] > e) e = p[1]; }); return { s: s, w: w, n: n, e: e }; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }

  // ——— 样式：自托管的 style.json（sprite / glyphs 补上 origin）；忘了隐藏边界的样式不用 ———
  var STY = null;
  function styleOk(st) {
    if (!st || !st.layers) return false; var ok = true;
    st.layers.forEach(function (l) { if (HIDE_RE.test(l.id) && !(l.layout && l.layout.visibility === 'none')) ok = false; });
    return ok;
  }
  function getStyle(cb) {
    if (STY) return cb(STY);
    var x = new XMLHttpRequest(), done = false;
    function fin(v) { if (done) return; done = true; if (v) STY = v; cb(v); }
    x.open('GET', STYLE_URL + (VER ? '?v=' + VER : '')); x.timeout = 20000;
    x.onload = function () {
      var j = null; try { j = JSON.parse(x.responseText); } catch (e) {}
      if (x.status === 200 && styleOk(j)) { j.sprite = location.origin + j.sprite; j.glyphs = location.origin + j.glyphs; fin(j); } else fin(null);
    };
    x.onerror = x.ontimeout = function () { fin(null); };
    try { x.send(); } catch (e) { fin(null); }
  }
  var MLQ = null;
  function loadML(cb) {
    if (W.maplibregl) return cb(true);
    if (MLQ) { MLQ.push(cb); return; }
    MLQ = [cb];
    function end(ok) { var q = MLQ; MLQ = null; q.forEach(function (f) { f(ok); }); }
    var v = VER ? '?v=' + VER : '';
    if (!qs('link[href*="maplibre-gl.css"]')) { var l = el('link'); l.rel = 'stylesheet'; l.href = ML_CSS + v; D.head.appendChild(l); }
    var s = qs('script[src*="maplibre-gl.js"]');      // 起步壳（site.js）点开时已经先发了脚本请求：接着等它，不发第二次
    if (!s) { s = el('script'); s.src = ML_JS + v; D.head.appendChild(s); }
    s.addEventListener('load', function () { end(!!W.maplibregl); }); s.addEventListener('error', function () { end(false); });
  }
  function glOk() { try { var c = D.createElement('canvas'); return !!(c.getContext('webgl') || c.getContext('experimental-webgl')); } catch (e) { return false; } }
  function weakDevice() {
    var c = navigator.connection || {}, slow = /(^|-)2g|3g/.test(c.effectiveType || '') || c.saveData;
    return !!(slow || (navigator.deviceMemory && navigator.deviceMemory <= 2) || (navigator.hardwareConcurrency && navigator.hardwareConcurrency <= 4 && (W.devicePixelRatio || 1) > 2));
  }
  var CJK_FONT = '"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC","Noto Sans SC","Source Han Sans SC","WenQuanYi Micro Hei",sans-serif';

  // ——— 视图：同一套接口，两种实现（街道底图 maplibre / 自画示意图）；摄像机一致 ———
  function mlView(inst, map) {
    return {
      kind: 'ml', map: map,
      project: function (ll) { var p = map.project([ll[1], ll[0]]); return { x: p.x, y: p.y }; },
      cam: function () { var c = map.getCenter(); return { lng: c.lng, lat: c.lat, z: map.getZoom() }; },
      go: function (c, anim, ms) { if (anim) map.easeTo({ center: [c.lng, c.lat], zoom: c.z, duration: ms || 400, essential: true }); else map.jumpTo({ center: [c.lng, c.lat], zoom: c.z }); },
      fly: function (c, ms) { map.flyTo({ center: [c.lng, c.lat], zoom: c.z, duration: ms || 700, essential: true, curve: 1.2 }); },
      zoom: function () { return map.getZoom(); },
      zoomBy: function (d) { map.zoomTo(clamp(map.getZoom() + d, MINZ, MAXZ), { duration: 220, essential: true }); },
      resize: function () { map.resize(); },
      atMax: function () { return map.getZoom() >= MAXZ - 0.01; }, atMin: function () { return map.getZoom() <= MINZ + 0.01; },
      onMove: function (cb) { map.on('move', cb); },
      destroy: function () {      // 关地图时还有请求在路上：maplibre 取消它们会再发 error 事件（AbortError），remove() 之后没人听了，它就 console.error 一行。先把 error 事件吞掉再 remove
        try { var f = map.fire; map.fire = function (ev) { return (ev && ev.type === 'error') ? this : f.apply(this, arguments); }; map.remove(); } catch (e) {}
      }
    };
  }
  // 示意图版：自己的摄像机 + 单指拖 / 双指缩放 / 双击放大 / 双指轻点缩小（pointer events）
  function schView(inst) {
    var c = { lng: 105, lat: 34, z: 4 }, cb = null, anim = 0, lim = null, z0 = 4;
    function size() { return { w: inst.sw || inst.stage.clientWidth || 390, h: inst.mh || inst.sh2 || inst.stage.clientHeight || 600 }; }      // 地图容器的高（刚开时只有“面板上方露出来的那块”，见 growMap）
    function fire() { if (cb) cb(); }
    function clampC() { if (!lim) return; c.lng = clamp(c.lng, lim.w, lim.e); c.lat = clamp(c.lat, lim.s, lim.n); c.z = clamp(c.z, Math.max(MINZ, z0 - 1.5), Math.min(MAXZ, z0 + 4)); }
    var v = {
      kind: 'sch',
      project: function (ll) { var s = size(); return camProject(c, s.w, s.h, ll); },
      cam: function () { return { lng: c.lng, lat: c.lat, z: c.z }; },
      setLimit: function (b, z) { var dx = Math.max(0.02, (b.e - b.w) * 0.6), dy = Math.max(0.02, (b.n - b.s) * 0.6); lim = { w: b.w - dx, e: b.e + dx, s: b.s - dy, n: b.n + dy }; z0 = z; },
      go: function (n, animate, ms) { if (anim && W.cancelAnimationFrame) W.cancelAnimationFrame(anim); anim = 0; if (!animate) { c.lng = n.lng; c.lat = n.lat; c.z = n.z; clampC(); fire(); return; } v.tween(n, ms || 400); },
      fly: function (n, ms) { v.tween(n, ms || 600); },
      tween: function (n, ms) {
        var a = { lng: c.lng, lat: c.lat, z: c.z }, t0 = now(), s0 = size();
        function step() { var t = Math.min(1, (now() - t0) / ms), e = easeOut(t); c.lng = a.lng + (n.lng - a.lng) * e; c.lat = a.lat + (n.lat - a.lat) * e; c.z = a.z + (n.z - a.z) * e; clampC(); fire(); if (t < 1) anim = raf(step); else anim = 0; }
        if (anim && W.cancelAnimationFrame) W.cancelAnimationFrame(anim); anim = raf(step);
      },
      zoom: function () { return c.z; },
      zoomAt: function (d, px, py) {      // 以屏幕点 (px,py) 为中心缩放
        var s = size(), nz = clamp(c.z + d, Math.max(MINZ, z0 - 1.5), Math.min(MAXZ, z0 + 4)), k = Math.pow(2, nz - c.z);
        var sc = WS * Math.pow(2, c.z), cx = lx(c.lng), cy = ly(c.lat), mx = cx + (px - s.w / 2) / sc, my = cy + (py - s.h / 2) / sc, ns = WS * Math.pow(2, nz);
        c.lng = ilng(mx - (px - s.w / 2) / ns); c.lat = ilat(my - (py - s.h / 2) / ns); c.z = nz; clampC(); fire();
      },
      zoomBy: function (d) { var s = size(); v.zoomAt(d, s.w / 2, s.h / 2); },
      panBy: function (dx, dy) { var sc = WS * Math.pow(2, c.z); c.lng = ilng(lx(c.lng) - dx / sc); c.lat = ilat(ly(c.lat) - dy / sc); clampC(); fire(); },
      resize: function () { fire(); },
      atMax: function () { return c.z >= Math.min(MAXZ, z0 + 4) - 0.01; }, atMin: function () { return c.z <= Math.max(MINZ, z0 - 1.5) + 0.01; },
      onMove: function (f) { cb = f; }, destroy: function () { if (anim && W.cancelAnimationFrame) W.cancelAnimationFrame(anim); }
    };
    return v;
  }
  function wireSch(inst) {      // 示意图版的手势；街道底图在用时（view.kind==='ml'）这些监听什么都不做
    var P = {}, st = null, last = 0, lastXY = null, two0 = 0, el0 = inst.stage;
    function xy(e) { var r = el0.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; }
    function act() { return inst.view && inst.view.kind === 'sch'; }
    el0.addEventListener('pointerdown', function (e) {
      if (!act()) return;
      try { el0.setPointerCapture(e.pointerId); } catch (x) {}
      P[e.pointerId] = xy(e); var ids = Object.keys(P);
      st = { moved: false, n: ids.length, d0: 0, mx: 0, my: 0 };
      if (ids.length === 2) { var a = P[ids[0]], b = P[ids[1]]; st.d0 = Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2)); st.mx = (a.x + b.x) / 2; st.my = (a.y + b.y) / 2; two0 = now(); }
    });
    el0.addEventListener('pointermove', function (e) {
      if (!act() || !P[e.pointerId] || !st) return; var p = xy(e), o = P[e.pointerId], ids = Object.keys(P);
      if (ids.length === 1) { var dx = p.x - o.x, dy = p.y - o.y; if (!st.moved && Math.abs(dx) + Math.abs(dy) < 4) return; st.moved = true; P[e.pointerId] = p; inst.view.panBy(dx, dy); }
      else if (ids.length === 2) {
        P[e.pointerId] = p; var a = P[ids[0]], b = P[ids[1]], d = Math.sqrt(Math.pow(a.x - b.x, 2) + Math.pow(a.y - b.y, 2)), mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        if (st.d0 > 8 && d > 8) { st.moved = true; inst.view.panBy(mx - st.mx, my - st.my); inst.view.zoomAt(Math.log(d / st.d0) / Math.LN2, mx, my); st.d0 = d; st.mx = mx; st.my = my; }
      }
    });
    function up(e) {
      if (!P[e.pointerId]) return; var p = xy(e), was = st, n = Object.keys(P).length;
      delete P[e.pointerId];
      if (!act() || !was) { st = null; return; }
      if (!was.moved && n === 2 && now() - two0 < 280) inst.view.zoomBy(-1);      // 双指轻点：缩小
      else if (!was.moved && n === 1) {
        var t = now(), q = lastXY;
        if (q && t - last < 320 && Math.abs(q.x - p.x) < 28 && Math.abs(q.y - p.y) < 28) { inst.view.zoomAt(1, p.x, p.y); last = 0; lastXY = null; }      // 双击放大
        else { last = t; lastXY = p; onTap(inst, p.x, p.y); }
      }
      if (!Object.keys(P).length) st = null; else st.moved = true;
    }
    el0.addEventListener('pointerup', up); el0.addEventListener('pointercancel', function (e) { delete P[e.pointerId]; st = null; });
  }

  // ——— 颜色：每天一种（红 / 墨 / 琥珀轮换，更多天同色系深浅），类名在 CSS 里 ———
  function dayCls(i) { return 'rm-c' + (i % 3) + ' rm-s' + (Math.floor(i / 3) % 3); }
  function readPal(inst) {
    var probe = el('span', 'rm-probe'); probe.style.cssText = 'position:absolute;width:0;height:0;visibility:hidden'; inst.root.appendChild(probe);
    var cs0 = getComputedStyle(D.documentElement), g = function (n, f) { return (cs0.getPropertyValue(n) || '').trim() || f; };
    inst.pal = []; var i, k;
    for (i = 0; i < 9; i++) { probe.className = 'rm-probe ' + dayCls(i); inst.pal.push((getComputedStyle(probe).getPropertyValue('--dc') || '').trim() || '#a63d27'); }
    inst.cl = { bg: g('--bg', '#f4f2ec'), ink: g('--ink', '#1c1d1a'), line: g('--line2', 'rgba(28,29,26,.16)'), sub: g('--sub', '#5d5f59'), mute: g('--mute', '#8d8f88') };
    inst.root.removeChild(probe);
  }

  // ——— 实例 ———
  var CUR = null;
  function build(inst) {
    var root = el('div', 'rm rm-fs rm-' + inst.type);
    root.setAttribute('role', 'dialog'); root.setAttribute('aria-label', '路线地图'); root.setAttribute('aria-modal', 'true');
    root.innerHTML =
      '<div class="rm-stage"><canvas class="rm-gr" aria-hidden="true"></canvas><div class="rm-map"></div><canvas class="rm-cv" aria-hidden="true"></canvas><div class="rm-pts"></div></div>' +
      '<div class="rm-prog" aria-hidden="true"><i></i></div>' +
      '<button type="button" class="rm-b rm-x pk-x" aria-label="关闭地图" title="关闭">×</button>' +
      '<button type="button" class="rm-b rm-sv" aria-label="把这张图存成图片" title="存成图片">存图</button>' +
      '<p class="rm-load" role="status"></p>' +
      '<p class="rm-note" role="status" hidden><span></span><button type="button" class="rm-rt">重试</button></p>' +
      '<div class="rm-col"><button type="button" class="rm-b rm-cp" aria-label="指北针，点一下转回正北" hidden>' + ICON_CP + '</button>' +
      '<button type="button" class="rm-b rm-rs" aria-label="回到当天 / 全程视野" title="回到视野">' + ICON_RS + '</button>' +
      '<button type="button" class="rm-b rm-zi" aria-label="放大">+</button><button type="button" class="rm-b rm-zo" aria-label="缩小">−</button></div>' +
      '<div class="rm-at"><p class="rm-atx" hidden>' + ATTR_HTML + '<button type="button" class="rm-b rm-ax" aria-label="关闭署名">×</button></p><button type="button" class="rm-b rm-ai" aria-label="地图数据署名" aria-expanded="false">i</button></div>' +
      '<div class="rm-sht m-list"><div class="rm-grab" aria-hidden="true"><i></i></div><div class="rm-tabs"></div><div class="rm-sum"></div><div class="rm-body"></div>' +
      '<div class="rm-foot"><a class="btn rm-navd" href="#" role="button">导航这一天 ›</a><p class="rm-hint"></p></div></div>';
    inst.root = root; inst.stage = qs('.rm-stage', root); inst.mapEl = qs('.rm-map', root); inst.gr = qs('.rm-gr', root); inst.cv = qs('.rm-cv', root); inst.pts = qs('.rm-pts', root);
    inst.note = qs('.rm-note', root); inst.load = qs('.rm-load', root); inst.prog = qs('.rm-prog i', root); inst.sheet = qs('.rm-sht', root); inst.tabs = qs('.rm-tabs', root); inst.sum = qs('.rm-sum', root);
    inst.bodyEl = qs('.rm-body', root); inst.foot = qs('.rm-foot', root); inst.navd = qs('.rm-navd', root); inst.hint = qs('.rm-hint', root); inst.col = qs('.rm-col', root);
    return root;
  }
  function curDay(inst) { return inst.sel >= 0 ? inst.days[inst.sel] : null; }
  function curPt(inst) { var d = curDay(inst); return d && inst.cur ? d.pts[inst.cur - 1] : null; }
  function dayPts(inst) {
    var d = curDay(inst), a = [];
    if (d) { d.pts.forEach(function (p) { a.push(p.ll); }); if (d.ep) a.push(d.ep); }
    else inst.days.forEach(function (x) { x.pts.forEach(function (p) { a.push(p.ll); }); });
    return a;
  }
  function safe() {
    var p = el('div'); p.style.cssText = 'position:fixed;left:0;top:0;width:0;height:0;visibility:hidden;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)'; B.appendChild(p);
    var cs = getComputedStyle(p), r = { t: parseFloat(cs.paddingTop) || 0, b: parseFloat(cs.paddingBottom) || 0 }; B.removeChild(p); return r;
  }
  function measure(inst) {
    var r = inst.root, sf = safe(); inst.st = sf.t; inst.sb = sf.b; inst.vw = r.clientWidth || W.innerWidth; inst.vh = r.clientHeight || W.innerHeight;
    inst.sw = inst.stage.clientWidth || inst.vw; inst.sh2 = inst.stage.clientHeight || inst.vh; inst.mh = inst.sh2 - (inst.mb || 0);
    var dpr = Math.min(W.devicePixelRatio || 1, 2); inst.dpr = dpr;
    [inst.cv, inst.gr].forEach(function (c) { var w = Math.round(inst.sw * dpr), h = Math.round(inst.sh2 * dpr); if (c.width !== w || c.height !== h) { c.width = w; c.height = h; } });
    inst.cx = inst.cv.getContext('2d'); inst.gx = inst.gr.getContext('2d');
  }

  // 摄像机留边：四周让出 ×、右侧控件、底部面板的位置，站点落在能看到的那一块里
  function padFor(inst) { var ov = Math.max(0, (inst.sheetH || 0) - (inst.mb || 0)); return { t: inst.st + 60, b: Math.min(ov + 20, inst.mh - 140), l: 36, r: 88 }; }      // 面板盖住地图容器的那一截（容器已经缩到面板上方时是 0）
  // 地图容器的高：刚打开时只到面板上沿（半屏时 6 块瓦片变 4 块，慢网下省一半字节）；面板一往下拖 / 收到卡片 / 收起，就长到整屏（growMap）。长大时摄像机中心会跟着容器中心挪，要把内容挪回去
  function growMap(inst) {
    if (!inst.mb) return; var old = inst.mh; inst.mb = 0; inst.mh = inst.sh2; inst.mapEl.style.bottom = '0px';
    var v = inst.view, d = (inst.mh - old) / 2;
    if (v && v.kind === 'ml') { try { v.map.resize(); v.map.panBy([0, d], { animate: false }); } catch (e) {} }
    else if (v) v.panBy(0, -d);
    if (inst.sch && v !== inst.sch) { /* 示意图的摄像机在街道底图出来时已同步过，不再动 */ }
  }
  function fitView(inst, anim) {
    if (!inst.view) return; var a = dayPts(inst); if (!a.length) return;
    var b = bbox(a), cam = fitCam(b, inst.sw, inst.mh, padFor(inst), FITMAX);
    if (b.s === b.n && b.w === b.e) cam.z = 14;
    inst.fitCam = cam; if (inst.sch && inst.sch.setLimit) inst.sch.setLimit(b, cam.z);
    inst.view.go(cam, anim, 450);
  }
  function flyToPt(inst, ll) {      // 平滑飞到这一站：缩放不改太大（至少 12，最多 15，当前已更近就不动），落点在“面板上方露出来的那块地图”的中央
    if (!inst.view) return; var z = inst.view.zoom(), t = clamp(Math.max(z, 12), 12, FITMAX);
    var cam = centerCam(ll, t, inst.sw, inst.mh, padFor(inst));
    var q = inst.view.project(ll), vis = padFor(inst), cx = inst.sw / 2 + (vis.l - vis.r) / 2, cy = vis.t + (inst.mh - vis.t - vis.b) / 2;
    if (Math.abs(t - z) < 0.3 && Math.abs(q.x - cx) < 6 && Math.abs(q.y - cy) < 6) return;
    inst.view.fly(cam, 650);
  }

  // ——— 叠层：一张 canvas 画线和点（几百个点也不卡），编号方块是少量 DOM ———
  function paintCv(inst) {
    var v = inst.view, c = inst.cx; if (!v || !c || !inst.pal) return;
    c.setTransform(inst.dpr, 0, 0, inst.dpr, 0, 0); c.clearRect(0, 0, inst.sw, inst.sh2); c.lineJoin = 'round'; c.lineCap = 'butt';
    var sel = inst.sel, i, j, d, q, col, dim, P;
    for (i = 0; i < inst.days.length; i++) {
      d = inst.days[i]; col = inst.pal[i % 9]; dim = sel >= 0 && sel !== i; P = d.pts;
      if (P.length >= 2) {
        c.beginPath(); for (j = 0; j < P.length; j++) { q = v.project(P[j].ll); if (j) c.lineTo(q.x, q.y); else c.moveTo(q.x, q.y); }
        c.setLineDash([]); c.globalAlpha = dim ? .22 : .85; c.strokeStyle = inst.cl.bg; c.lineWidth = 7; c.stroke();
        c.setLineDash([7, 5]); c.globalAlpha = dim ? .3 : 1; c.strokeStyle = col; c.lineWidth = 3; c.stroke();
      }
      if (sel !== i) { c.setLineDash([]); c.globalAlpha = dim ? .4 : 1; c.fillStyle = col; for (j = 0; j < P.length; j++) { q = v.project(P[j].ll); c.fillRect(q.x - 4, q.y - 4, 8, 8); } }
    }
    c.globalAlpha = 1; c.setLineDash([]);
  }
  function niceKm(max) { var n = [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000], k = n[0], i; for (i = 0; i < n.length; i++) if (n[i] <= max) k = n[i]; return k; }
  function paintGr(inst) {      // 示意图底：细经纬线（纸色底上的方格）+ 比例尺 + 北；街道底图出来以后盖住它
    var v = inst.view, g = inst.gx; if (!g || !v) return; var w = inst.sw, h = inst.sh2;
    g.setTransform(inst.dpr, 0, 0, inst.dpr, 0, 0); g.clearRect(0, 0, w, h);
    if (inst.mapShown) return;
    var c = v.cam(), s = WS * Math.pow(2, c.z), kmpp = 111.32 * Math.cos(rad(c.lat)) / (s / 360), k, x, y;
    var degs = [0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20], deg = degs[degs.length - 1];
    for (k = 0; k < degs.length; k++) if (degs[k] * s / 360 >= 70) { deg = degs[k]; break; }
    var lng0 = ilng(lx(c.lng) - w / 2 / s), lng1 = ilng(lx(c.lng) + w / 2 / s), lat1 = ilat(ly(c.lat) - h / 2 / s), lat0 = ilat(ly(c.lat) + h / 2 / s);
    g.strokeStyle = inst.cl.line; g.lineWidth = 1; g.beginPath();
    for (x = Math.ceil(lng0 / deg) * deg; x <= lng1; x += deg) { var px = Math.round(v.project([c.lat, x]).x) + .5; g.moveTo(px, 0); g.lineTo(px, h); }
    for (y = Math.ceil(lat0 / deg) * deg; y <= lat1; y += deg) { var py = Math.round(v.project([y, c.lng]).y) + .5; g.moveTo(0, py); g.lineTo(w, py); }
    g.stroke();
    var km = niceKm(kmpp * 110), wpx = Math.max(24, Math.round(km / kmpp)), by = h - (inst.sheetH || 0) - 16, bx = 12;
    g.strokeStyle = inst.cl.ink; g.lineWidth = 1.5; g.beginPath(); g.moveTo(bx, by - 6); g.lineTo(bx, by); g.lineTo(bx + wpx, by); g.lineTo(bx + wpx, by - 6); g.stroke();
    g.fillStyle = inst.cl.ink; g.font = '700 12px sans-serif'; g.textBaseline = 'alphabetic'; g.fillText((km < 1 ? Math.round(km * 1000) + ' 米' : km + ' 公里') + '　北 ↑', bx + wpx + 8, by);
  }
  function draw(inst) {      // 状态变了（选天 / 选站 / 重读模型）：重建方块；地图移动只重新定位
    inst.pts.innerHTML = ''; inst.marks = [];
    var sel = inst.sel;
    function add(e, ll, meta) { inst.pts.appendChild(e); var m = { el: e, ll: ll, badge: e.className.indexOf('rm-db') >= 0 }, k; if (meta) for (k in meta) if (meta.hasOwnProperty(k)) m[k] = meta[k]; inst.marks.push(m); return m; }
    if (sel < 0) inst.days.forEach(function (d, i) {
      if (!d.pts.length) return;
      var b = el('button', 'rm-mk rm-db ' + dayCls(i), '<i>' + (i + 1) + '</i>'); b.type = 'button'; b.setAttribute('data-day', i); b.tabIndex = -1; b.setAttribute('aria-label', '第 ' + (i + 1) + ' 天：' + d.title);
      add(b, d.pts[0].ll, { kind: 'day', day: i, label: '第 ' + (i + 1) + ' 天：' + (d.title || '') });
    });
    var d = curDay(inst);
    if (d) {
      (inst.gray || []).forEach(function (g, gi) { var e = el('button', 'rm-mk rm-gy' + (inst.curG === gi + 1 ? ' rm-cur' : ''), '<i></i>'); e.type = 'button'; e.setAttribute('data-g', gi); e.tabIndex = -1; e.setAttribute('aria-label', '顺路可去：' + g.c.n); add(e, g.ll, { kind: 'g', gi: gi, label: '顺路可去：' + g.c.n, small: true }); });
      if (d.ep) { var h = el('button', 'rm-mk rm-hm ' + dayCls(sel) + (inst.curH ? ' rm-cur' : ''), '<i>住</i>'); h.type = 'button'; h.setAttribute('data-hm', '1'); h.tabIndex = -1; h.setAttribute('aria-label', '住 · 约' + (d.stay ? '（' + d.stay + '，大概位置）' : '')); add(h, d.ep, { kind: 'hm', label: '住 · 约' + (d.stay ? ' ' + d.stay : '') }); }   // 先画住：和某一站重叠时站在上面
      d.pts.forEach(function (p) {
        var cls = 'rm-mk ' + dayCls(sel) + (p.kind === 'mu' ? ' rm-mu' : '') + (p.kind === 'eat' ? ' rm-eat' : '') + (inst.cur === p.n ? ' rm-cur' : '');
        var b = el('button', cls, '<i>' + p.n + '</i>'); b.type = 'button'; b.setAttribute('data-n', p.n); b.tabIndex = -1; b.setAttribute('aria-label', p.n + ' ' + p.name); add(b, p.ll, { kind: 'n', n: p.n, label: p.n + ' ' + p.name });
      });
    }
    paintTag(inst, true); place(inst);
  }
  function paintTag(inst, quiet) {      // 选中一站：标记旁边显示名字小标签
    inst.marks = (inst.marks || []).filter(function (m) { if (m.tag) { if (m.el.parentNode) m.el.parentNode.removeChild(m.el); return false; } return true; });
    var p = curPt(inst); if (!p) { if (!quiet) place(inst); return; }
    var e = el('i', 'rm-tg', '<span>' + esc(p.name) + '</span>'); e.setAttribute('aria-hidden', 'true'); inst.pts.appendChild(e); inst.marks.push({ el: e, ll: p.ll, tag: true });
    if (!quiet) place(inst);
  }
  var placing = 0;
  function place(inst) {
    var v = inst.view; if (!v || !inst.alive || !inst.marks) return;
    var W_ = inst.sw, t0_ = inst.pf ? now() : 0;
    inst.marks.forEach(function (m) {
      var q = v.project(m.ll); m.px = q.x; m.py = q.y; m.el.style.transform = 'translate(' + Math.round(q.x) + 'px,' + Math.round(q.y) + 'px)';
      if (m.tag) m.el.classList.toggle('rm-tgl', q.x > W_ - 150);
    });
    if (inst.sel < 0) cullBadges(inst); else denseMarks(inst);
    paintCv(inst); paintGr(inst); if (v.kind === 'sch') schLabels(inst); else if (inst.lbs) clearLabels(inst);
    zoomBtns(inst); compass(inst);
    if (inst.pf) { var dt_ = now() - t0_; inst.pf.n++; inst.pf.ms += dt_; if (dt_ > inst.pf.max) inst.pf.max = dt_; }
  }
  function denseMarks(inst) {      // 标记挤在一起（相距 <30px）：缩成 22px
    var nums = inst.marks.filter(function (m) { return m.kind === 'n' || m.kind === 'hm'; });
    nums.forEach(function (m) {
      var tight = nums.some(function (o) { return o !== m && Math.abs(o.px - m.px) < 30 && Math.abs(o.py - m.py) < 30; });
      m.small = tight; m.el.classList.toggle('rm-sm', tight);
    });
  }
  function rangeLabel(a) {
    a = a.slice().sort(function (x, y) { return x - y; }); var out = [], i = 0, j;
    while (i < a.length) { j = i; while (j + 1 < a.length && a[j + 1] === a[j] + 1) j++; out.push(j > i ? a[i] + '–' + a[j] : String(a[i])); i = j + 1; }
    return out.join('·');
  }
  function cullBadges(inst) {      // 总览：挤在一起的天数章只留一个，写成“2–5”；被合并的天仍能点到（点击挑选）
    var kept = [];
    inst.marks.forEach(function (m) {
      if (!m.badge) return; var x = m.px, y = m.py, hide = false, i;
      for (i = 0; i < kept.length; i++) if (Math.abs(kept[i].x - x) < 30 && Math.abs(kept[i].y - y) < 30) { hide = true; kept[i].g.push(m.day + 1); break; }
      m.el.style.visibility = hide ? 'hidden' : ''; if (!hide) kept.push({ x: x, y: y, m: m, g: [m.day + 1] });
    });
    kept.forEach(function (k) {
      var t = k.g.length > 1 ? rangeLabel(k.g) : String(k.m.day + 1), ie = k.m.el.firstChild;
      if (ie && ie.textContent !== t) ie.textContent = t;
      k.m.el.setAttribute('aria-label', (k.g.length > 1 ? '第 ' + t + ' 天（位置相近）' : '第 ' + t + ' 天') + '：' + (inst.days[k.m.day].title || ''));
    });
  }
  function clearLabels(inst) { qsa('.rm-lb', inst.pts).forEach(function (e) { e.parentNode.removeChild(e); }); inst.lbs = false; }
  function schLabels(inst) {      // 示意图版：站名小标签（贪心，不重叠）
    clearLabels(inst); var d = curDay(inst); if (!d) return; inst.lbs = true; var boxes = [];
    d.pts.forEach(function (p) {
      var m = inst.marks.filter(function (k) { return k.kind === 'n' && k.n === p.n; })[0]; if (!m || m.px < 0 || m.px > inst.sw || m.py < 0 || m.py > inst.sh2 - (inst.sheetH || 0)) return;
      var nm = p.name.length > 9 ? p.name.slice(0, 9) + '…' : p.name, w = nm.length * 12 + 12, x = m.px + 16, y = m.py - 9;
      if (x + w > inst.sw - 4) x = m.px - 16 - w;
      var hit = boxes.some(function (b) { return x < b.x + b.w && x + w > b.x && y < b.y + 18 && y + 18 > b.y; }); if (hit) return;
      boxes.push({ x: x, y: y, w: w }); var e = el('span', 'rm-lb', esc(nm)); e.style.cssText = 'left:' + Math.round(x) + 'px;top:' + Math.round(y) + 'px'; inst.pts.appendChild(e);
    });
  }
  function zoomBtns(inst) { var v = inst.view; if (!v) return; var zi = qs('.rm-zi', inst.root), zo = qs('.rm-zo', inst.root); zi.disabled = v.atMax(); zo.disabled = v.atMin(); }
  function compass(inst) {
    var v = inst.view, b = qs('.rm-cp', inst.root); if (!b) return; var br = v && v.kind === 'ml' ? v.map.getBearing() : 0;
    b.hidden = Math.abs(br) < 0.5; if (!b.hidden) b.firstChild.style.transform = 'rotate(' + (-br) + 'deg)';
  }
  // 点按（地图上）：挑离点击位置最近的标记；一处只有一个 → 当作点了它；挤在一起有几个 → 弹列表选；点空白 → 取消选中
  function onTap(inst, x, y) {
    var c = [];
    inst.marks.forEach(function (m) {
      if (m.dot || m.tag || !m.kind) return; var dx = m.px - x, dy = m.py - y, d = Math.sqrt(dx * dx + dy * dy);
      if (d <= (m.small ? 20 : 26)) c.push({ m: m, d: d });
    });
    if (!c.length) { closeAt(inst); if (inst.cur || inst.curG || inst.curH) deselect(inst); return; }
    c.sort(function (a, b) { return a.d - b.d; });
    if (c.length === 1 || c[1].d - c[0].d > 12) { pickMark(inst, c[0].m); return; }
    showPick(inst, c);
  }
  function pickMark(inst, m) {
    if (m.kind === 'day') return selectDay(inst, m.day);
    if (m.kind === 'n') return selectStop(inst, m.n, { fly: true });
    if (m.kind === 'g') return selectGray(inst, m.gi);
    if (m.kind === 'hm') return selectHome(inst);
  }
  function showPick(inst, c) {
    inst.pick = c.map(function (x) { return x.m; }); var pk = inst.pickEl;
    if (!pk) { pk = inst.pickEl = el('div', 'rm-pk'); inst.root.appendChild(pk); }
    pk.innerHTML = '<span class="rm-pt">这里有 ' + c.length + ' 处，点选一个</span>' + c.slice(0, 6).map(function (x, i) { return '<button type="button" class="rm-pi" data-pi="' + i + '">' + esc(x.m.label) + '</button>'; }).join('');
    pk.hidden = false;
  }
  function closeAt(inst) { if (inst.pickEl) inst.pickEl.hidden = true; }

  // ——— 底部面板：标签条、信息头、站点列表、站点卡片、三档吸附 ———
  function paintTabs(inst) {
    var n = inst.days.length, h = '<button type="button" class="rm-tb' + (inst.sel < 0 ? ' on' : '') + '" data-i="-1">全程</button>';
    inst.days.forEach(function (d, i) { h += '<button type="button" class="rm-tb' + (inst.sel === i ? ' on' : '') + '" data-i="' + i + '">' + dayLabel(i, n) + '</button>'; });
    inst.tabs.innerHTML = h; inst.tabs.className = 'rm-tabs' + (n > 6 ? ' long' : '');
    var on = qs('.rm-tb.on', inst.tabs); if (on && inst.tabs.scrollWidth > inst.tabs.clientWidth) inst.tabs.scrollLeft = Math.max(0, on.offsetLeft - inst.tabs.clientWidth / 2 + on.offsetWidth / 2);      // 选中项始终可见
  }
  function paintSum(inst) {      // 收起时露出来的一条：选中的站名，没有就写今天 / 全程的标题
    var d = curDay(inst), p = curPt(inst), t;
    if (p) t = '<b>' + p.n + '</b><span>' + esc(p.name) + '</span>';
    else if (inst.curH && d) t = '<b>住</b><span>住 · 约' + (d.stay ? ' ' + esc(d.stay) : '') + '</span>';
    else if (d) t = '<b>' + noStr(d.i + 1) + '</b><span>' + esc(d.title || '第 ' + (d.i + 1) + ' 天') + '</span>';
    else t = '<b>' + noStr(inst.days.length) + '</b><span>全程 共 ' + inst.days.length + ' 天</span>';
    inst.sum.innerHTML = t;
  }
  function paintList(inst) {
    var d = curDay(inst), h = '', n = inst.days.length;
    if (!d) {
      h = '<div class="rm-hd"><span class="rm-no">' + (n < 100 ? noStr(n) : n) + '</span><span class="rm-hdt"><small>全程</small><b>共 ' + n + ' 天</b></span></div><div class="rm-rows">';
      inst.days.forEach(function (x, i) { h += '<button type="button" class="rm-row rm-dr" data-i="' + i + '"><b>' + noStr(i + 1) + '</b><span class="rm-t"><strong>' + esc(x.title || '第 ' + (i + 1) + ' 天') + '</strong><small>' + x.pts.length + ' 个有位置的地方' + (x.stay ? ' · 住 ' + esc(x.stay) : '') + '</small></span></button>'; });
      h += '</div>';
    } else {
      var info = d.load.slice(); if (d.stay) info.push('住 ' + d.stay);
      h = '<div class="rm-hd"><span class="rm-no">' + noStr(d.i + 1) + '</span><span class="rm-hdt"><small>第 ' + (d.i + 1) + ' 天</small><b>' + esc(d.title) + '</b></span></div>' + (info.length ? '<p class="rm-ld">今天：' + esc(info.join(' · ')) + '</p>' : '') + '<div class="rm-rows">';
      d.pts.forEach(function (p) {
        var tags = (p.book ? '<em>要预约</em>' : '') + (p.closed ? '<em class="rm-cl">' + esc(p.closed) + '</em>' : '');
        h += '<button type="button" class="rm-row' + (inst.cur === p.n ? ' on' : '') + '" data-n="' + p.n + '"><b>' + p.n + '</b><span class="rm-t"><strong>' + esc(p.name) + '</strong><small>' + esc(p.one || (p.kind === 'mu' ? '博物馆' : (p.kind === 'eat' ? '吃饭' : ''))) + '</small></span><span class="rm-r">' + tags + (p.next ? '<i>' + esc(p.next.txt) + '</i>' : '') + '</span></button>';
      });
      if (d.ep) h += '<button type="button" class="rm-row rm-hrow" data-hm="1"><b>住</b><span class="rm-t"><strong>住 · 约' + (d.stay ? ' ' + esc(d.stay) : '') + '</strong><small>大概位置，不是酒店</small></span></button>';
      h += '</div>';
    }
    inst.bodyEl.innerHTML = h; inst.bodyEl.scrollTop = 0; inst.bodyEl.className = 'rm-body rm-list';
  }
  function cardOf(inst, p, i, total) {
    var tags = (p.book ? '<em>要预约</em>' : '') + (p.closed ? '<em class="rm-cl">' + esc(p.closed) + '</em>' : '') + (p.kind === 'mu' ? '<em class="rm-q">博物馆</em>' : (p.kind === 'eat' ? '<em class="rm-q">吃饭</em>' : ''));
    var legs = [];
    if (p.prev) legs.push('<span>上一站 · ' + esc(p.prev.txt) + '</span>'); else if (i === 0) legs.push('<span>第一站</span>');
    if (p.next) legs.push('<span>下一站 · ' + esc(p.next.txt) + '</span>'); else if (i === total - 1) legs.push('<span>这天最后一站</span>');
    var d = curDay(inst), prevLL = i > 0 ? d.pts[i - 1].ll : null, nextLL = i < total - 1 ? d.pts[i + 1].ll : null, km = [];
    if (prevLL) km.push('离上一站 ' + kmTxt(kmd(prevLL, p.ll))); if (nextLL) km.push('离下一站 ' + kmTxt(kmd(p.ll, nextLL)));
    return '<article class="rm-card" data-n="' + p.n + '"><div class="rm-ch"><b>' + p.n + '</b><span class="rm-cname">' + esc(p.name) + '</span><button type="button" class="rm-cb" data-act="list">全部站点</button></div>' +
      (p.one ? '<p class="rm-c1">' + esc(p.one) + '</p>' : '') + (tags ? '<p class="rm-c2">' + tags + '</p>' : '') +
      '<p class="rm-c3">' + legs.join('') + (km.length ? '<small>直线：' + km.join(' · ') + '</small>' : '') + '</p>' +
      '<div class="rm-ca"><button type="button" class="rm-go" data-act="go">导航到这里</button><button type="button" class="rm-adj2" data-act="adj">调整这一站</button></div>' +
      '<p class="rm-cn2">' + p.n + ' / ' + total + (total > 1 ? '　左右滑动换一站' : '') + '</p></article>';
  }
  function paintCards(inst) {
    var d = curDay(inst), h = '', k = 0;
    if (inst.curG) {
      var g = inst.gray[inst.curG - 1]; if (!g) return;
      h = '<div class="rm-cards one"><article class="rm-card rm-gcard"><div class="rm-ch"><b class="rm-gq"></b><span class="rm-cname">' + esc(g.c.n) + '</span><button type="button" class="rm-cb" data-act="list">全部站点</button></div><p class="rm-c1">顺路可去 · ' + esc(g.label) + '</p><div class="rm-ca"><button type="button" class="rm-go" data-act="addg">加到这天</button></div></article></div>';
    } else if (inst.curH && d) {
      h = '<div class="rm-cards one"><article class="rm-card"><div class="rm-ch"><b>住</b><span class="rm-cname">住 · 约' + (d.stay ? ' ' + esc(d.stay) : '') + '</span><button type="button" class="rm-cb" data-act="list">全部站点</button></div><p class="rm-c1">大概位置，不是酒店</p></article></div>';
    } else if (d) {
      h = '<div class="rm-cards">'; d.pts.forEach(function (p, i) { h += cardOf(inst, p, i, d.pts.length); }); h += '</div>';
    }
    inst.bodyEl.innerHTML = h; inst.bodyEl.className = 'rm-body rm-cardsw';
    var cs = qs('.rm-cards', inst.bodyEl); inst.cards = cs; inst.cardH = 0;
    if (cs) qsa('.rm-card', cs).forEach(function (c) { inst.cardH = Math.max(inst.cardH, c.offsetHeight); });
    if (cs && inst.cur && !inst.curG && !inst.curH) { cs.scrollLeft = (inst.cur - 1) * cs.clientWidth; }
    wireCards(inst);
  }
  function wireCards(inst) {
    var cs = inst.cards; if (!cs || cs.className.indexOf('one') >= 0) return; var t = 0, until = 0, down = false;
    // 只有“用户自己在滑卡片”（手指按着 / 刚松手的惯性 / 滚轮）引起的滚动才换站；程序设 scrollLeft、面板高度变化后的重新吸附都不算（否则会把刚选的站又改回去）
    cs.addEventListener('touchstart', function () { down = true; }, { passive: true });
    cs.addEventListener('touchend', function () { down = false; until = now() + 700; }, { passive: true });
    cs.addEventListener('touchcancel', function () { down = false; until = now() + 700; }, { passive: true });
    cs.addEventListener('wheel', function () { until = now() + 700; }, { passive: true });
    cs.addEventListener('scroll', function () {
      if (inst.progScroll || !(down || now() < until)) return; clearTimeout(t);
      t = setTimeout(function () { if (!cs.clientWidth) return; var i = Math.round(cs.scrollLeft / cs.clientWidth) + 1, d = curDay(inst); if (d && i >= 1 && i <= d.pts.length && i !== inst.cur) selectStop(inst, i, { fly: true, keepCards: true }); }, 110);
    }, { passive: true });
  }
  function paintFoot(inst) {
    var d = curDay(inst), nv = !!d && navSegs(d).length > 0; inst.navd.hidden = !nv; inst.hint.hidden = !nv; inst.foot.hidden = !nv;
    if (nv) { var sg = navSegs(d), ht = navHint(d); inst.hint.textContent = (ht ? ht + ' ' : '') + '图上的线是站与站之间的直线示意，不是行车路线。'; inst.hint.hidden = false; inst.navd.setAttribute('href', sg.length === 1 ? sg[0].url : '#'); navState(inst); }
  }
  // 断网：“导航这一天”置灰写明原因，点它不弹分段层
  function navState(inst) {
    if (!inst || !inst.navd) return; var off = navigator.onLine === false;
    inst.navd.classList.toggle('off', off); inst.navd.setAttribute('aria-disabled', off ? 'true' : 'false'); inst.navd.textContent = off ? '没网，暂时不能导航' : '导航这一天 ›';
  }
  W.addEventListener('online', function () { navState(CUR); if (CUR && CUR.failed && CUR.why === 'offline') retry(CUR); });
  W.addEventListener('offline', function () { navState(CUR); });
  function paintSheet(inst) {
    var card = inst.mode === 'card';
    inst.sheet.className = 'rm-sht ' + (card ? 'm-card' : 'm-list') + (inst.sheetCls || '');
    paintTabs(inst); paintSum(inst);
    if (card) paintCards(inst); else paintList(inst);
    paintFoot(inst); if (inst.sheetH) setSheet(inst, inst.sheetH, false);      // className 整个重写了，把 s0 / sfull 等状态类补回来
  }
  // 三档吸附：收起 / 半屏 / 拉满（高度，px）。卡片模式两档：卡片 / 收起一条名字
  function dets(inst) {
    var H = inst.vh, grab = 20, tabs = 44, sum = 46, sb = inst.sb;
    var c = grab + tabs + sum + sb, full = H - inst.st - 64, half = Math.round(H * .5);
    half = clamp(half, c + 150, Math.max(c + 150, full - 90));
    var cardH = grab + 218 + sb, s1 = grab + 46 + sb;
    if (inst.cardH > 80) cardH = grab + inst.cardH + sb;
    cardH = Math.min(cardH, Math.max(c, half));
    return inst.mode === 'card' ? [s1, cardH] : [c, half, full];
  }
  function setSheet(inst, h, anim) {
    var s = inst.sheet; s.classList.toggle('snap', !!anim); s.classList.toggle('drag', !anim);
    inst.sheetH = Math.round(h); s.style.height = inst.sheetH + 'px'; inst.root.style.setProperty('--sh', inst.sheetH + 'px');
    var d = dets(inst), lowest = d[0];
    inst.root.classList.toggle('rm-drg', !anim);
    s.classList.toggle('s0', inst.sheetH < lowest + 30); s.classList.toggle('sfull', inst.mode === 'list' && inst.sheetH > inst.vh * .8);
    inst.root.classList.toggle('rm-sfull', inst.mode === 'list' && inst.sheetH > inst.vh * .8);
  }
  function snapTo(inst, idx, anim) {
    var d = dets(inst); idx = clamp(idx, 0, d.length - 1); inst.snap = idx; if (inst.mode === 'list') inst.lastList = idx;
    if (inst.mb && d[idx] < inst.mb) growMap(inst);
    setSheet(inst, d[idx], anim !== false);
    if (anim !== false) settle(inst);
  }
  function settle(inst) { [0, 330].forEach(function (t) { setTimeout(function () { if (inst.alive) { measure(inst); place(inst); } }, t); }); }
  function defaultSnap(inst) { return inst.vh >= 700 ? 1 : 0; }      // 按屏高选：够高半屏（地图露上半），矮屏收起，保证地图主体可见

  // 面板手势：touch + 鼠标。标题条 / 手柄 / 标签条竖向拖 = 拉面板；列表：拉满时正常滚，滚到顶继续下拉才收起；没拉满时往上拉先把面板拉起来
  function wireSheet(inst) {
    var sh = inst.sheet, g = null;
    function inBody(t) { return !!(t.closest && t.closest('.rm-body')); }
    function ts(ev) { return ev && ev.timeStamp ? ev.timeStamp : now(); }      // 用事件自带的时间戳算速度（主线程忙的时候“处理时间”会挤在一起，速度就算成 0）
    function start(y, x, target, ev) {
      g = { y0: y, x0: x, y: y, h0: inst.sheetH, mode: null, t: target, samples: [{ y: y, t: ts(ev) }], lastY: y, list: inst.mode === 'list' && inBody(target), cards: !!(target.closest && target.closest('.rm-cards')), tabs: !!(target.closest && target.closest('.rm-tabs')), top: inst.bodyEl.scrollTop <= 0 };
    }
    function move(y, x, ev) {
      if (!g) return false;
      var dy = y - g.y0, dx = x - g.x0, d = dets(inst), max = d[d.length - 1], min = d[0];
      if (g.mode === null) {
        if (Math.abs(dy) < 6 && Math.abs(dx) < 6) return false;
        if ((g.tabs || g.cards) && Math.abs(dx) > Math.abs(dy)) g.mode = 'native';
        else if (g.list && inst.snap === d.length - 1 && !(dy > 0 && g.top)) g.mode = 'native';      // 拉满了：列表自己滚
        else g.mode = 'drag';
        if (g.mode === 'drag') { g.y0 = y; g.h0 = inst.sheetH; dy = 0; g.samples = [{ y: y, t: ts(ev) }]; growMap(inst); }      // 一开始拖面板就把地图容器长到整屏（面板往下走会露出下面的地图）
      }
      if (g.mode === 'native') {
        if (g.list && inst.snap === d.length - 1 && inst.bodyEl.scrollTop <= 0 && y > g.lastY + 1) { g.mode = 'drag'; g.y0 = y; g.h0 = inst.sheetH; dy = 0; g.samples = [{ y: y, t: ts(ev) }]; }      // 滚到顶了还在下拉：交给面板
        else { g.lastY = y; return false; }
      }
      g.lastY = y; if (ev && ev.cancelable) ev.preventDefault();
      var h = g.h0 - dy;
      if (h > max) h = max + (h - max) * .3; else if (h < min) h = min - (min - h) * .3;      // 阻尼
      setSheet(inst, h, false); g.samples.push({ y: y, t: ts(ev) }); if (g.samples.length > 8) g.samples.shift();
      return true;
    }
    function end() {
      if (!g) return; var was = g; g = null; if (was.mode !== 'drag') return;
      var d = dets(inst), s = was.samples, v = 0, a = s[0], b = s[s.length - 1];
      for (var i = s.length - 1; i >= 0; i--) { if (b.t - s[i].t > 90) break; a = s[i]; }
      if (b.t - a.t > 1) v = (b.y - a.y) / (b.t - a.t);      // px/ms，向上为负
      var proj = inst.sheetH - v * 240, best = 0, bd = 1e9, k;
      for (k = 0; k < d.length; k++) { var dd = Math.abs(d[k] - proj); if (dd < bd) { bd = dd; best = k; } }
      if (Math.abs(v) > .35) { var cur = 0; for (k = 0; k < d.length; k++) if (Math.abs(d[k] - inst.sheetH) < Math.abs(d[cur] - inst.sheetH)) cur = k; best = clamp(v < 0 ? Math.max(cur + 1, best) : Math.min(cur - 1, best), 0, d.length - 1); }
      snapTo(inst, best, true);
      if (inst.mode === 'list') { inst.bodyEl.scrollTop = best === d.length - 1 ? inst.bodyEl.scrollTop : 0; }
    }
    sh.addEventListener('touchstart', function (e) { if (e.touches.length !== 1) { g = null; return; } start(e.touches[0].clientY, e.touches[0].clientX, e.target, e); }, { passive: true });
    sh.addEventListener('touchmove', function (e) { if (e.touches.length !== 1) return; move(e.touches[0].clientY, e.touches[0].clientX, e); }, { passive: false });
    sh.addEventListener('touchend', end, { passive: true }); sh.addEventListener('touchcancel', end, { passive: true });
    var mouse = false;
    sh.addEventListener('mousedown', function (e) { if (e.button !== 0 || e.target.closest('button,a,input')) return; mouse = true; start(e.clientY, e.clientX, e.target, e); });
    W.addEventListener('mousemove', function (e) { if (mouse && g) move(e.clientY, e.clientX, e); });
    W.addEventListener('mouseup', function () { if (mouse) { mouse = false; end(); } });
  }

  // ——— 选天 / 选站 ———
  function paintAll(inst) { paintSheet(inst); }
  function selectDay(inst, i, anim) {
    if (i >= inst.days.length) i = -1;
    inst.sel = i; inst.cur = 0; inst.curG = 0; inst.curH = false; inst.gray = []; closeAt(inst); markOn(inst); inst.mode = 'list';
    paintAll(inst); draw(inst);
    var d = dets(inst); var k = clamp(inst.lastList != null ? inst.lastList : defaultSnap(inst), 0, d.length - 1); snapTo(inst, k, anim !== false);
    fitView(inst, anim !== false); loadGray(inst);
  }
  function markOn(inst) {
    qsa('section.day.rm-on').forEach(function (s) { s.className = s.className.replace(/\s*rm-(on|c\d|s\d)\b/g, ''); });
  }
  function selectStop(inst, n, opt) {
    var d = curDay(inst); if (!d || !d.pts[n - 1]) return; opt = opt || {};
    inst.cur = n; inst.curG = 0; inst.curH = false; closeAt(inst); inst.lastSel = d.pts[n - 1];
    var was = inst.mode; inst.mode = 'card';
    if (opt.keepCards && was === 'card' && inst.cards) paintSum(inst); else paintSheet(inst);
    paintTagsAndMarks(inst);
    if (was !== 'card') { inst.lastList = inst.snap; snapTo(inst, 1, true); }
    else if (inst.snap === 0) snapTo(inst, 1, true);
    if (opt.fly !== false) flyToPt(inst, d.pts[n - 1].ll);
    if (inst.cards && !opt.keepCards && inst.cards.className.indexOf('one') < 0) { inst.progScroll = true; inst.cards.scrollLeft = (n - 1) * inst.cards.clientWidth; setTimeout(function () { inst.progScroll = false; }, 160); }      // 用户自己滑卡片时不要再去动卡片
  }
  function paintTagsAndMarks(inst) {
    qsa('.rm-mk', inst.pts).forEach(function (b) {
      var on = (b.hasAttribute('data-n') && +b.getAttribute('data-n') === inst.cur) || (b.hasAttribute('data-g') && inst.curG === +b.getAttribute('data-g') + 1) || (b.hasAttribute('data-hm') && inst.curH);
      b.classList.toggle('rm-cur', !!on);
    });
    paintTag(inst);
  }
  function selectGray(inst, gi) {
    var g = inst.gray[gi]; if (!g) return; inst.cur = 0; inst.curH = false; inst.curG = gi + 1; closeAt(inst);
    var was = inst.mode; inst.mode = 'card'; paintSheet(inst); paintTagsAndMarks(inst);
    if (was !== 'card') inst.lastList = inst.snap; snapTo(inst, 1, true); flyToPt(inst, g.ll);
  }
  function selectHome(inst) {
    var d = curDay(inst); if (!d || !d.ep) return; inst.cur = 0; inst.curG = 0; inst.curH = true; closeAt(inst);
    var was = inst.mode; inst.mode = 'card'; paintSheet(inst); paintTagsAndMarks(inst);
    if (was !== 'card') inst.lastList = inst.snap; snapTo(inst, 1, true); flyToPt(inst, d.ep);
  }
  function deselect(inst) {      // 点空白 / “全部站点”：回到列表，回到进卡片前的那一档
    if (inst.mode !== 'card' && !inst.cur && !inst.curG && !inst.curH) return;
    inst.cur = 0; inst.curG = 0; inst.curH = false; inst.mode = 'list'; closeAt(inst);
    paintSheet(inst); paintTagsAndMarks(inst);
    var d = dets(inst); snapTo(inst, clamp(inst.lastList != null ? inst.lastList : 1, 0, d.length - 1), true);
  }

  // ——— 顺路可去（灰点）：复用顺路加一站的候选、试算、加站和撤销（site.js 里 window.zNpMap）———
  function anchorsOf(d) {
    return d.pts.map(function (p) { return p.row; }).filter(function (r) {
      return (r.classList.contains('see') || r.classList.contains('fun')) && r.getAttribute('data-np') !== 'v' && !r.getAttribute('data-at') && !r.getAttribute('data-rain') && !r.getAttribute('data-fo') && !r.getAttribute('data-on') && !/沿途慢慢走/.test(nameOf(r));
    });
  }
  function loadGray(inst) {
    var d = curDay(inst), N = W.zNpMap; inst.gray = [];
    if (!d || !N || d.sec.dataset.oi == null || !navigator.onLine) return;
    var tok = inst.gtok = (inst.gtok || 0) + 1, sec = d.sec;
    N.load(sec, function (cells) {
      if (tok !== inst.gtok || !inst.alive) return;
      var pool = N.pool(cells), best = {}, ans = anchorsOf(d);
      ans.forEach(function (S) {
        var res; try { res = N.cands(sec, S, 'ins', pool); } catch (e) { return; }
        res.list.forEach(function (it) { var c0 = best[it.id]; if (!c0 || it.delta < c0.it.delta) best[it.id] = { it: it, S: S }; });
      });
      var arr = []; for (var k in best) if (best.hasOwnProperty(k)) arr.push(best[k]);
      arr.sort(function (a, b) { return a.it.delta - b.it.delta; });
      inst.gray = arr.slice(0, 40).map(function (x) { return { c: x.it.c, it: x.it, S: x.S, ll: [x.it.c.a, x.it.c.o], label: N.label('ins', x.it) }; });
      draw(inst);
    }, function () {});
  }
  function addGray(inst) {
    var d = curDay(inst), N = W.zNpMap, g = inst.curG ? inst.gray[inst.curG - 1] : null; if (!d || !N || !g) return;
    var t; try { t = N.tryIns(d.sec, g.S, g.c); } catch (e) { t = { ok: false }; }
    if (!t || !t.ok) { toast('这天已经排满了，加不进去'); return; }
    inst.curG = 0; deselect(inst); N.commit(d.sec, g.S, g.c);
  }

  // ——— 整屏图层：锁背景滚动、占一条历史（站里 body.pk-open 的机制：返回键 / Esc / “×”都能退）、退出后回到原来的滚动位置（选过站就滚到那一行）———
  function lockBody(inst) { if (B.classList.contains('rm-lock')) return; B.style.top = (-inst.y) + 'px'; B.classList.add('rm-lock'); }
  function unlockBody(inst) {
    B.classList.remove('rm-lock'); B.style.top = '';
    function back() { try { W.scrollTo({ top: inst.y, behavior: 'instant' }); } catch (e) { W.scrollTo(0, inst.y); } }
    back();
    function pop() { back(); setTimeout(back, 40); W.removeEventListener('popstate', pop); }
    W.addEventListener('popstate', pop); setTimeout(function () { W.removeEventListener('popstate', pop); try { if (inst.sr) history.scrollRestoration = inst.sr; } catch (e) {} }, 1500);      // 返回键触发的历史回退完成后浏览器可能再恢复一次滚动位置：popstate 之后再校正；整屏期间 scrollRestoration 设成 manual，浏览器自己不乱滚
    [60, 200, 500].forEach(function (t) { setTimeout(function () { if (!B.classList.contains('rm-lock') && Math.abs((W.pageYOffset || 0) - inst.y) > 1 && !CUR) back(); }, t); });      // 返回键会让浏览器按“上一条历史的位置”再滚一次：稍后校正
  }
  function toRowAfterClose(inst) {      // 关闭后：页面滚到刚才选中的那一站对应行，高亮一下
    var p = inst.lastSel; if (!p || !p.row || !p.row.getBoundingClientRect) return;
    var r = p.row.getBoundingClientRect(); if (!r.height) return;
    inst.y = Math.max(0, r.top + inst.y - Math.round((W.innerHeight || 600) / 3));
    p.row.classList.add('flash'); setTimeout(function () { p.row.classList.remove('flash'); }, 1600);
  }
  function closeInst(inst) {
    if (!inst || !inst.alive) return;
    inst.alive = false; clearTimeout(inst.timer); clearTimeout(inst.tchk); clearTimeout(inst.hard); if (inst.mo) inst.mo.disconnect();
    if (inst.mq && inst.mq.removeListener) inst.mq.removeListener(inst.onScheme);
    W.removeEventListener('resize', inst.onResize); W.removeEventListener('orientationchange', inst.onResize);
    toRowAfterClose(inst);
    if (inst.view) inst.view.destroy(); if (inst.sch) inst.sch.destroy();
    if (inst.root && inst.root.parentNode) inst.root.parentNode.removeChild(inst.root);
    if (CUR === inst) CUR = null;
    B.classList.remove('rmap-on'); unlockBody(inst); if (inst.addedPk) B.classList.remove('pk-open');
    qsa('.rm-sheet.rm-dyn').forEach(function (s) { s.remove(); });
  }

  // 浮层（导航分段层、存图层）开在地图之上时，返回键只关浮层、地图还在：站里的 popstate 处理已经吃掉了地图占的那条历史，这里补回一条，否则再按一次返回会直接离开页面
  function repush(inst) { setTimeout(function () { if (inst && inst.alive && !(history.state && history.state.zov)) { try { history.pushState({ zov: 1 }, ''); } catch (e) {} } }, 0); }
  // ——— 导航这一天 ———
  function gcj(ll) { var f = W.zGcj; return f ? f(ll[0], ll[1]) : ll; }
  function navPts(d) {
    var a = [];
    function push(n, ll) { if (!ll) return; var l = a[a.length - 1]; if (l && kmd(l.ll, ll) < 0.03) return; a.push({ n: n, ll: ll }); }
    push(d.spName || '昨晚住处', d.sp); d.pts.forEach(function (p) { push(p.name, p.ll); }); push(d.stay ? '住处（' + d.stay + '）' : '住处', d.ep);
    return a;
  }
  function mobileUA() { return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent); }
  function viaMax() { return APP === 'google' ? (mobileUA() ? 3 : 9) : 1; }
  function segUrl(seg) {
    var f = seg[0], t = seg[seg.length - 1], mid = seg.slice(1, -1), g;
    if (APP === 'google') {
      var u = 'https://www.google.com/maps/dir/?api=1&origin=' + f.ll[0] + ',' + f.ll[1] + '&destination=' + t.ll[0] + ',' + t.ll[1];
      if (mid.length) u += '&waypoints=' + mid.map(function (m) { return m.ll[0] + ',' + m.ll[1]; }).join('%7C');
      return u + '&travelmode=driving';
    }
    function pt(p) { g = gcj(p.ll); return g[1] + ',' + g[0] + ',' + encodeURIComponent(p.n); }
    var s = 'https://uri.amap.com/navigation?from=' + pt(f) + '&to=' + pt(t);
    if (mid.length) s += '&via=' + pt(mid[0]);
    return s + '&mode=car&src=zouni&callnative=1';
  }
  function navSegs(d) {
    var a = navPts(d); if (a.length < 2) return [];
    var step = viaMax() + 1, out = [], i, j;
    for (i = 0; i < a.length - 1; i += step) { j = Math.min(i + step, a.length - 1); out.push(a.slice(i, j + 1)); }
    return out.map(function (seg) { return { pts: seg, url: segUrl(seg) }; });
  }
  function navHint(d) {
    var a = navPts(d), segs = navSegs(d).length;
    var lim = APP === 'google' ? '谷歌地图一次最多带 ' + viaMax() + ' 个中途点' : '高德一次只带 1 个中途点';
    return segs > 1 ? '这天 ' + a.length + ' 个点，分 ' + segs + ' 段导航（' + lim + '），按顺序点。' : '';
  }
  function goUrl(u) {
    if (navigator.onLine === false) { toast('没网，暂时不能导航'); return; }
    if (APP !== 'google' && mobileUA() && HOST.open) { HOST.open(u, '高德地图'); return; }      // 手机：callnative=1 唤起高德 App（没装 1.6 秒后提示）
    var w = null; try { w = W.open(u, '_blank'); if (w) { try { w.opener = null; } catch (x) {} } } catch (e) {}      // 不带 'noopener' 特性：带了以后 window.open 一律返回 null，分不清“打开了”和“被拦了”，结果新标签开了、本页也跳走
    if (!w) location.href = u;
  }
  function navHere(inst, p) {      // 导航到这一站：沿用这一行上原有的导航图标（站里已经处理了唤起 App / 断网提示）；没有就按坐标直接去
    if (p.nav) { p.nav.click(); return; }
    if (navigator.onLine === false) { toast('没网，暂时不能导航'); return; }
    var u;
    if (APP === 'google') u = 'https://www.google.com/maps/dir/?api=1&destination=' + p.ll[0] + ',' + p.ll[1] + '&travelmode=driving';
    else { var g = gcj(p.ll); u = 'https://uri.amap.com/navigation?to=' + g[1] + ',' + g[0] + ',' + encodeURIComponent(p.name) + '&mode=car&src=zouni&callnative=1'; }
    goUrl(u);
  }
  function navDay(d, inst) {
    if (navigator.onLine === false) { toast('没网，暂时不能导航'); return; }
    var segs = navSegs(d); if (!segs.length) { toast('这天没有可导航的位置'); return; }
    if (HOST.track) HOST.track('路线地图·导航这一天');
    if (segs.length === 1) { goUrl(segs[0].url); return; }
    var who = APP === 'google' ? '用谷歌地图打开 ›' : '用高德打开 ›';
    var mask = el('div', 'pk-mask'), sh = el('div', 'pk rm-sheet rm-dyn'); sh.setAttribute('role', 'dialog');
    var h = '<div class="pk-h"><b>导航这一天</b><button type="button" class="pk-x">关上</button></div><p class="xnote">' + esc(navHint(d)) + '</p><div class="xd">';
    segs.forEach(function (s, i) { h += '<a class="rm-seg" href="' + esc(s.url) + '" data-i="' + i + '"><span class="rm-sg1"><b>第 ' + (i + 1) + ' 段：</b><small>' + s.pts.map(function (p) { return esc(p.n); }).join(' → ') + '</small></span><em>' + who + '</em></a>'; });
    sh.innerHTML = h + '</div>';
    var xb = inst && inst.root ? qs('.rm-x', inst.root) : null;
    function cl() { mask.remove(); sh.remove(); if (xb) xb.classList.add('pk-x'); if (!inst) B.classList.remove('pk-open'); else repush(inst); }
    sh.addEventListener('click', function (e) { var x = e.target.closest('.pk-x'); if (x) return cl(); var a = e.target.closest('a.rm-seg'); if (a) { e.preventDefault(); goUrl(a.getAttribute('href')); } });
    mask.addEventListener('click', cl); B.appendChild(mask); B.appendChild(sh); B.classList.add('pk-open');
    if (xb) xb.classList.remove('pk-x');      // 分段层在地图之上：返回键 / Esc 先关分段层（站里找第一个 .pk-x：地图的“×”暂时不叫它）
  }

  // ——— 存成图片：底图 + 线 + 标记 + 标题 + 二维码（只放线路网址）；底图取不到就存示意图版并说明。只存面板上方露出来的那一块 ———
  function saveImg(inst) {
    function run() {
      var vis = Math.max(260, inst.sh2 - (inst.sheetH || 0)), CW = 1080, sw = inst.sw || 390, k = CW / sw, mh = Math.round(vis * k), HD = 190, FT = 190, CH = HD + mh + FT;
      var cv = D.createElement('canvas'); cv.width = CW; cv.height = CH; var x = cv.getContext('2d');
      var cs = getComputedStyle(D.documentElement), g = function (n, f) { return (cs.getPropertyValue(n) || '').trim() || f; };
      var BG = g('--bg', '#f4f2ec'), INK = g('--ink', '#1c1d1a'), SUB = g('--sub', '#5d5f59'), RED = g('--red', '#a63d27'), AMB = g('--amb', '#8a5a00'), SERIF = '"Noto Serif SC",serif', SANS = '"Noto Sans SC",sans-serif';
      var PAL = [RED, INK, AMB];
      x.fillStyle = BG; x.fillRect(0, 0, CW, CH);
      x.fillStyle = g('--card', '#ebe8df'); x.fillRect(0, HD, CW, mh);
      var real = false;
      if (inst.view && inst.view.kind === 'ml' && inst.mapShown) {
        try { var mc = inst.view.map.getCanvas(), sc = mc.width / sw; x.save(); x.beginPath(); x.rect(0, HD, CW, mh); x.clip(); x.filter = 'saturate(.5) sepia(.16)'; x.drawImage(mc, 0, 0, mc.width, Math.round(vis * sc), 0, HD, CW, mh); x.restore(); x.getImageData(0, HD, 1, 1); real = true; }
        catch (e) { real = false; x.filter = 'none'; x.fillStyle = g('--card', '#ebe8df'); x.fillRect(0, HD, CW, mh); }
      }
      x.filter = 'none';
      function P(ll) { var p = inst.view.project(ll); return [p.x * k, HD + p.y * k]; }
      x.save(); x.beginPath(); x.rect(0, HD, CW, mh); x.clip();
      inst.days.forEach(function (d, i) {
        var show = inst.sel < 0 || inst.sel === i, col = PAL[i % 3]; if (!show || d.pts.length < 2) return;
        x.beginPath(); d.pts.forEach(function (p, j) { var q = P(p.ll); if (j) x.lineTo(q[0], q[1]); else x.moveTo(q[0], q[1]); });
        x.setLineDash([]); x.strokeStyle = BG; x.lineWidth = 12; x.globalAlpha = .85; x.stroke(); x.globalAlpha = 1; x.setLineDash([20, 14]); x.strokeStyle = col; x.lineWidth = 7; x.stroke(); x.setLineDash([]);
      });
      function sqr(q, txt, col, hollow, mu) {
        var s = 62; x.fillStyle = hollow ? BG : col; x.fillRect(q[0] - s / 2, q[1] - s / 2, s, s); x.lineWidth = 5; x.strokeStyle = hollow ? col : BG; x.strokeRect(q[0] - s / 2 + 2, q[1] - s / 2 + 2, s - 4, s - 4);
        if (mu) { x.lineWidth = 4; x.strokeStyle = hollow ? col : BG; x.strokeRect(q[0] - s / 2 + 12, q[1] - s / 2 + 12, s - 24, s - 24); }
        x.fillStyle = hollow ? col : BG; x.font = '900 32px ' + SERIF; x.textAlign = 'center'; x.textBaseline = 'middle'; x.fillText(txt, q[0], q[1] + 2);
      }
      inst.days.forEach(function (d, i) {
        var col = PAL[i % 3];
        if (inst.sel === i) { d.pts.forEach(function (p) { sqr(P(p.ll), String(p.n), col, p.kind === 'eat', p.kind === 'mu'); }); if (d.ep) sqr(P(d.ep), '住', col, true, false); }
        else if (inst.sel < 0 && d.pts.length) sqr(P(d.pts[0].ll), String(i + 1), col, false, false);
      });
      x.restore(); x.textAlign = 'left'; x.textBaseline = 'alphabetic';
      var title = (ART && (ART.getAttribute('data-title') || ART.getAttribute('data-label'))) || document.title, d0 = curDay(inst);
      x.fillStyle = RED; x.font = '700 30px ' + SANS; x.fillText(inst.sel < 0 ? '路线图 · 全程 ' + inst.days.length + ' 天' : '路线图 · 第 ' + (inst.sel + 1) + ' 天', 64, 76);
      x.fillStyle = INK; x.font = '900 52px ' + SERIF; var tt = d0 ? d0.title : title; if (tt.length > 16) tt = tt.slice(0, 16) + '…'; x.fillText(tt, 64, 146);
      var fy = HD + mh;
      x.fillStyle = INK; x.fillRect(64, fy + 30, CW - 128, 2); x.font = '700 28px ' + SANS; x.fillText('走你 · ' + location.host + location.pathname, 64, fy + 90);
      x.fillStyle = SUB; x.font = '24px ' + SANS; x.fillText(real ? '底图 OpenFreeMap © OpenMapTiles Data from OpenStreetMap' : '示意图，位置是相对的', 64, fy + 140);
      if (W.qrcode) {
        try {
          var q = W.qrcode(0, 'M'); q.addData(location.origin + location.pathname); q.make(); var nM = q.getModuleCount(), c1 = Math.max(4, Math.floor(130 / nM)), z = c1 * nM, qx = CW - 64 - z, qy = fy + 50;
          x.fillStyle = '#fff'; x.fillRect(qx - 8, qy - 8, z + 16, z + 16); x.fillStyle = '#1c1d1a'; for (var r = 0; r < nM; r++) for (var c = 0; c < nM; c++) if (q.isDark(r, c)) x.fillRect(qx + c * c1, qy + r * c1, c1, c1);
        } catch (e) {}
      }
      var url; try { url = cv.toDataURL('image/png'); } catch (e) { toast('保存图片失败'); return; }
      var m = el('div', 'hmap-zoom shotv rm-shot'), had = B.classList.contains('pk-open'), xb = qs('.rm-x', inst.root);
      m.innerHTML = '<button type="button" class="hz-x pk-x">关上</button><div class="hz-b"><img alt="路线图" src="' + url + '"></div><p class="shotp">' + (real ? '' : '街道底图没取到，存的是示意图版。') + '手机上长按图片保存；电脑上 <a download="走你-路线图.png" href="' + url + '">点这里下载</a></p>';
      B.appendChild(m); B.classList.add('pk-open'); if (xb) xb.classList.remove('pk-x');
      function cl() { m.remove(); if (xb) xb.classList.add('pk-x'); if (!had) B.classList.remove('pk-open'); else repush(inst); }
      qs('.hz-x', m).addEventListener('click', cl);
    }
    if (W.qrcode) run(); else { var s = el('script'); s.src = '/assets/qr.js'; s.onload = run; s.onerror = run; D.head.appendChild(s); }
  }

  // ——— 事件 ———
  function wire(inst) {
    var root = inst.root;
    wireSch(inst); wireSheet(inst);
    root.addEventListener('gesturestart', function (e) { e.preventDefault(); });
    root.addEventListener('click', function (e) {
      var t = e.target, b;
      if (t.closest('.rm-x')) { closeInst(inst); return; }
      if (t.closest('.rm-rs')) { var wasCard = inst.mode === 'card'; fitView(inst, true); return; }
      if (t.closest('.rm-zi')) { inst.view.zoomBy(1); if (inst.view.kind === 'sch') place(inst); return; }
      if (t.closest('.rm-zo')) { inst.view.zoomBy(-1); if (inst.view.kind === 'sch') place(inst); return; }
      if (t.closest('.rm-cp')) { try { inst.view.map.resetNorth({ duration: 250 }); } catch (x) {} return; }
      if (t.closest('.rm-sv')) { saveImg(inst); return; }
      if (t.closest('.rm-rt')) { retry(inst); return; }
      if (t.closest('.rm-ai')) { var x = qs('.rm-atx', root), open = x.hidden; x.hidden = !open; qs('.rm-ai', root).setAttribute('aria-expanded', open ? 'true' : 'false'); return; }
      if (t.closest('.rm-ax')) { qs('.rm-atx', root).hidden = true; qs('.rm-ai', root).setAttribute('aria-expanded', 'false'); return; }
      if ((b = t.closest('.rm-tb'))) { selectDay(inst, +b.getAttribute('data-i')); return; }
      if ((b = t.closest('.rm-dr'))) { selectDay(inst, +b.getAttribute('data-i')); return; }
      if ((b = t.closest('.rm-navd'))) { var d = curDay(inst); if (!d) return; e.preventDefault(); navDay(d, inst); return; }
      if ((b = t.closest('.rm-pi'))) { var pm = inst.pick && inst.pick[+b.getAttribute('data-pi')]; closeAt(inst); if (pm) pickMark(inst, pm); return; }
      if ((b = t.closest('.rm-row'))) {
        if (b.hasAttribute('data-n')) selectStop(inst, +b.getAttribute('data-n'), { fly: true });
        if (b.hasAttribute('data-hm')) selectHome(inst);
        return;
      }
      if ((b = t.closest('[data-act]')) && t.closest('.rm-card')) {
        var act = b.getAttribute('data-act'), p = curPt(inst);
        if (act === 'list') { deselect(inst); return; }
        if (act === 'go' && p) { navHere(inst, p); return; }
        if (act === 'adj' && p) { adjustRow(inst, p); return; }
        if (act === 'addg') { addGray(inst); return; }
      }
    });
  }
  function adjustRow(inst, p) {      // 调整这一站：打开页面里原有的“调整”半屏（多待 / 少待 / 去掉 / 换成 / 在这之后加一个）；改完图自己重画
    var a = p.row && qs('.adj', p.row); if (!a) { toast('这一站没有可调整的项'); return; } a.click();
  }

  // ——— 加载 / 兜底 ———
  function setProg(inst, v) { if (inst.prog) inst.prog.style.width = Math.round(clamp(v, 0, 1) * 100) + '%'; inst.pv = v; }
  function showLoad(inst) { inst.load.textContent = NOTE_LOAD; inst.load.hidden = false; inst.root.classList.add('rm-loading'); }
  function hideLoad(inst) { inst.load.hidden = true; inst.root.classList.remove('rm-loading'); setProg(inst, 1); setTimeout(function () { if (inst.alive) setProg(inst, 0); }, 400); }
  function fallback(inst, why) {
    if (!inst.alive || inst.failed) return; inst.failed = true; inst.why = why; clearTimeout(inst.timer); clearTimeout(inst.tchk); clearTimeout(inst.hard); hideLoad(inst);
    if (inst.view && inst.view.kind === 'ml') { var c = inst.view.cam(); inst.view.destroy(); inst.sch.go(c, false); }
    inst.map = null; inst.mapEl.innerHTML = ''; inst.mapEl.className = 'rm-map'; inst.mapShown = false; inst.root.classList.add('rm-sch');
    inst.view = inst.sch; inst.sch.onMove(function () { place(inst); });
    var nt = qs('span', inst.note); nt.textContent = why === 'offline' ? NOTE_NET : NOTE_OFF; inst.note.hidden = false; inst.note.classList.toggle('rm-nr', why === 'offline');
    var at = qs('.rm-at', inst.root); if (at) at.hidden = true;
    draw(inst); place(inst); settle(inst);
  }
  function retry(inst) {
    if (!inst.alive || !inst.failed) return; inst.failed = false; inst.why = ''; inst.note.hidden = true; inst.root.classList.remove('rm-sch'); var at = qs('.rm-at', inst.root); if (at) at.hidden = false;
    startMap(inst);
  }
  function startMap(inst) {
    if (!navigator.onLine) return fallback(inst, 'offline');
    if (!glOk()) return fallback(inst, 'nogl');
    function arm() { clearTimeout(inst.hard); inst.hard = setTimeout(function () { if (!inst.tiles) fallback(inst, 'slow'); }, HARD_MS); }
    showLoad(inst); setProg(inst, .1); arm();      // 脚本 / 样式一直不回：每一步 20 秒，取到一步就重新计时
    loadML(function (ok) {
      if (!inst.alive || inst.failed) return;
      if (!ok) return fallback(inst, 'ml');
      arm(); setProg(inst, .3);
      getStyle(function (st) {
        if (!inst.alive || inst.failed) return;
        if (!st) return fallback(inst, 'style');
        arm(); setProg(inst, .5);
        var map, cam = inst.sch.cam(), weak = weakDevice(), rot = false;
        try { rot = localStorage.getItem('zouni_map_rot') === '1'; } catch (e) {}
        try {
          map = new W.maplibregl.Map({
            container: inst.mapEl, style: JSON.parse(JSON.stringify(st)), center: [cam.lng, cam.lat], zoom: cam.z, minZoom: MINZ, maxZoom: MAXZ,
            attributionControl: false, dragRotate: rot, pitchWithRotate: false, touchPitch: false, fadeDuration: 0, preserveDrawingBuffer: true, renderWorldCopies: false,
            cooperativeGestures: false, localIdeographFontFamily: CJK_FONT, maxTileCacheSize: weak ? 40 : 80, refreshExpiredTiles: false,
            pixelRatio: weak ? 1 : undefined,
            transformRequest: function (url, type) {      // 自托管的西文字形只带常用范围；别的范围（很少用到）回到 OpenFreeMap 取；弱设备 / 慢网取 1x 的 sprite（maplibre 按设备像素比自己加 @2x，改不了，只能在请求里改回来）
              if (weak && (type === 'SpriteImage' || type === 'SpriteJSON')) return { url: url.replace('@2x', '') };
              if (type === 'Glyphs') { var m = /\/assets\/map\/fonts\/([^/]+)\/(\d+-\d+)\.pbf/.exec(url); if (m && ['0-255', '256-511', '8192-8447'].indexOf(m[2]) < 0) return { url: OFM + '/fonts/' + m[1] + '/' + m[2] + '.pbf' }; }
              return { url: url };
            }
          });
          if (!rot) map.touchZoomRotate.disableRotation();
        } catch (e) { return fallback(inst, 'gl'); }
        inst.map = map; inst.view = mlView(inst, map); inst.tiles = 0; inst.terr = 0; inst.pend = 0; inst.mapShown = false;
        map.on('move', function () { if (inst.map === map) place(inst); });
        map.on('rotate', function () { compass(inst); });
        map.on('dataloading', function (e) { if (e.tile) inst.pend++; });
        map.on('data', function (e) {
          if (e.tile) {
            inst.tiles++; inst.pend = Math.max(0, inst.pend - 1); clearTimeout(inst.hard);
            setProg(inst, .6 + .38 * inst.tiles / Math.max(1, inst.tiles + inst.pend));
            if (!inst.mapShown && inst.tiles > 0) { inst.mapShown = true; inst.mapEl.classList.add('rm-in'); paintGr(inst); try { localStorage.setItem('zouni_map_t', String(Date.now())); } catch (x) {} }      // 记一笔“刚开过地图”：site.js 的 warm() 10 分钟内不再预热
          }
        });
        map.on('idle', function () { if (inst.map === map && inst.tiles > 0) hideLoad(inst); });
        map.on('error', function (e) {
          var er = e && e.error, msg = (er && er.message) || '';
          if (e && (e.tile || /Failed to fetch|NetworkError|Load failed|AJAXError|failed|404|403|5\d\d/i.test(msg))) {
            inst.terr++; if (e.tile) inst.pend = Math.max(0, inst.pend - 1);      // 瓦片请求失败：1.5 秒后一块成功的都没有、也没有别的瓦片还在路上 → 退回示意图（还有在路上的，等它们，最迟 12 秒）
            if (!inst.tchk) inst.tchk = setTimeout(function () { inst.tchk = 0; if (inst.alive && !inst.tiles && inst.terr > 0 && !(inst.pend > 0)) fallback(inst, 'tiles'); }, 1500);
          }
        });
        map.getCanvas().addEventListener('webglcontextlost', function () { fallback(inst, 'lost'); });
        map.on('click', function (e) { onTap(inst, e.point.x, e.point.y); });
        inst.slowN = 0;
        (function slowCheck() { inst.timer = setTimeout(function () { if (inst.tiles || !inst.alive || inst.failed) return; if (inst.pend > 0 && ++inst.slowN <= 3) return slowCheck(); fallback(inst, 'slow'); }, SLOW_MS); })();      // 还有瓦片在路上就再等（最多再等 3 轮 12 秒）：慢网下“慢”不等于“坏”
        place(inst);
      });
    });
  }
  function watch(inst) {
    var timer = null;
    inst.mo = new MutationObserver(function (recs) {
      var rel = recs.some(function (r) { var t = r.target.nodeType === 1 ? r.target : r.target.parentNode; return !(t && t.closest && t.closest('.rm,.pk,.pk-mask,.toast')); });
      if (!rel) return; clearTimeout(timer); timer = setTimeout(function () { refresh(inst); }, 160);
    });
    inst.mo.observe(ART, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'data-ll'] });
  }
  function refresh(inst) {
    if (!inst.alive) return; var days = readDays(), s0 = sig(inst.days), s1 = sig(days);
    var sec0 = inst.sel >= 0 && inst.days[inst.sel] ? inst.days[inst.sel].sec : null;
    if (s0 === s1) return;
    var p0 = curPt(inst), row0 = p0 ? p0.row : null;
    inst.days = days;
    if (sec0) { var k2 = days.map(function (d) { return d.sec; }).indexOf(sec0); inst.sel = k2; }
    if (inst.sel >= days.length) inst.sel = days.length - 1;
    var d = curDay(inst);
    if (!d) { inst.cur = 0; inst.curG = 0; inst.curH = false; if (inst.mode === 'card') inst.mode = 'list'; }
    else if (inst.cur) { var k = -1; d.pts.forEach(function (q) { if (q.row === row0) k = q.n; }); inst.cur = k > 0 ? k : 0; if (!inst.cur && inst.mode === 'card' && !inst.curG && !inst.curH) inst.mode = 'list'; }
    paintAll(inst); draw(inst); loadGray(inst);
    var dd = dets(inst); snapTo(inst, clamp(inst.snap, 0, dd.length - 1), false);
  }

  function open(type, sec, boot) {
    if (CUR) closeInst(CUR);
    var days = readDays(); if (!days.length) return null;
    var inst = { type: type, sec: sec || null, days: days, sel: -1, cur: 0, curG: 0, curH: false, gray: [], alive: true, mode: 'list', snap: 1, tiles: 0, sheetH: 0, marks: [] };
    var k = sec ? days.map(function (d) { return d.sec; }).indexOf(sec) : -1;
    if (type === 'day') { if (k < 0) return null; inst.sel = k; inst.home = k; }
    build(inst); CUR = inst; inst.y = boot && boot.y != null ? boot.y : (W.pageYOffset || 0);
    try { inst.sr = boot && boot.sr ? boot.sr : history.scrollRestoration; history.scrollRestoration = 'manual'; } catch (e) {}
    inst.addedPk = boot ? !!boot.addedPk : !B.classList.contains('pk-open'); B.classList.add('pk-open', 'rmap-on');
    B.appendChild(inst.root); lockBody(inst);
    if (boot && boot.root && boot.root.parentNode) boot.root.parentNode.removeChild(boot.root);
    measure(inst); readPal(inst);
    inst.sch = schView(inst); inst.view = inst.sch; inst.sch.onMove(function () { place(inst); });
    inst.mq = W.matchMedia ? W.matchMedia('(prefers-color-scheme: dark)') : null; inst.onScheme = function () { readPal(inst); place(inst); }; if (inst.mq && inst.mq.addListener) inst.mq.addListener(inst.onScheme);
    inst.onResize = function () { if (!inst.alive) return; measure(inst); if (inst.view) inst.view.resize(); var d = dets(inst); snapTo(inst, clamp(inst.snap, 0, d.length - 1), false); place(inst); };
    W.addEventListener('resize', inst.onResize); W.addEventListener('orientationchange', function () { setTimeout(inst.onResize, 300); });
    wire(inst); paintAll(inst);
    snapTo(inst, defaultSnap(inst), false); inst.lastList = inst.snap;
    inst.mb = inst.sheetH; inst.mh = inst.sh2 - inst.mb; inst.mapEl.style.bottom = inst.mb + 'px';
    fitView(inst, false); draw(inst);
    watch(inst); startMap(inst); loadGray(inst);
    if (HOST.track) HOST.track('路线地图·' + (type === 'ov' ? '总览' : '每天'));
    return inst;
  }
  var api = W.ZRM = {
    ov: function (boot) { return open('ov', null, boot); },
    day: function (sec, boot) { return open('day', sec, boot); },
    close: function () { if (CUR) closeInst(CUR); },
    nav: function (sec) { var days = readDays(), k = days.map(function (d) { return d.sec; }).indexOf(sec); if (k >= 0) navDay(days[k], null); },
    cur: function () { return CUR; },
    focus: function () { return false; },      // 旧的“点页面里的行聚焦地图”：整屏图层打开时页面本身不动，用不上
    segs: function (sec) { var days = readDays(), k = days.map(function (d) { return d.sec; }).indexOf(sec); return k >= 0 ? navSegs(days[k]).map(function (s) { return s.url; }) : []; },
    model: readDays,
    select: function (n) { if (CUR) selectStop(CUR, n, { fly: true }); },
    selectDay: function (i) { if (CUR) selectDay(CUR, i); }
  };
})();
