/* 路线地图（2026-10-17）。点开“看路线图 / 本日地图 / 导航这一天”才加载；街道底图 maplibre 再按需加载。
 * 规则和坑：docs/handoff/02-UI规范.md「路线地图」、05-注意事项.md「路线地图」。ES5 only（禁 ?. ?? flatMap .at() 箭头函数 let/const），data_checks 会扫。
 *
 * 结构：一份“模型”（从页面 DOM 读：每天的站、标题、出发/住的大概位置、车程）→ 一个 Inst（一个地图实例，同一时间只有一个，省 WebGL 上下文）
 *  地图底：maplibre（街道）；失败（断网 / 瓦片全挂 / 没 WebGL / 样式取不到）退回自画示意图（总览用页面里已有的静态 SVG，每天的图用本文件画的纸色底示意图），并写一行“街道地图需要联网”。
 *  线、站点标记、顺路灰点都画在底图之上的叠层（SVG + 按钮），不是 maplibre 的图层：深色滤镜只作用在底图 canvas 上，标记不会被反色；示意图兜底也能共用同一套画法。 */
(function () {
  if (window.ZRM) return;
  var D = document, W = window, B = D.body;
  var HOST = W.ZRM_HOST || {};
  var ART = D.querySelector('article.trip');
  var APP = ART ? ART.getAttribute('data-app') : 'amap';
  var VER = ''; try { var _m = /[?&]v=(\w+)/.exec(D.currentScript.src); VER = _m ? _m[1] : ''; } catch (e) {}
  var STYLE_URL = 'https://tiles.openfreemap.org/styles/liberty';
  var ML_JS = '/assets/maplibre/maplibre-gl.js', ML_CSS = '/assets/maplibre/maplibre-gl.css';
  var MINZ = 2, MAXZ = 17;
  // 合规：边界线图层（含争议边界）和国家 / 省级标注一律隐藏（data_checks 扫这一行）
  var HIDE_RE = /boundary|country|state|disputed/;
  var ATTR_HTML = '<a href="https://openfreemap.org" target="_blank" rel="noopener">OpenFreeMap</a> <a href="https://www.openmaptiles.org/" target="_blank" rel="noopener">© OpenMapTiles</a> Data from <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>';
  var NOTE_OFF = '街道地图加载失败，已改用示意图';      // 有网也会失败（瓦片服务器连不上、被拦），所以不写“需要联网”
  var NOTE_LOAD = '地图加载中，网慢时可能要十几秒';
  var SLOW_MS = 12000, HARD_MS = 20000;      // 一块瓦片都没来：12 秒退示意图；连脚本 / 样式都没取到：20 秒
  var ICON_FS = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>';
  var ICON_XF = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg>';
  var ICON_RS = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="square" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>';
  var IOS = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

  // ——— 小工具 ———
  function qs(s, r) { return (r || D).querySelector(s); }
  function qsa(s, r) { return [].slice.call((r || D).querySelectorAll(s)); }
  function el(t, c, h) { var e = D.createElement(t); if (c) e.className = c; if (h != null) e.innerHTML = h; return e; }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pll(s) { if (!s) return null; var p = String(s).split(','); var a = parseFloat(p[0]), o = parseFloat(p[1]); return (isNaN(a) || isNaN(o)) ? null : [a, o]; }
  function rad(x) { return x * Math.PI / 180; }
  function kmd(a, b) { var dl = rad(b[1] - a[1]), p1 = rad(a[0]), p2 = rad(b[0]); return 2 * 6371 * Math.asin(Math.sqrt(Math.pow(Math.sin((p2 - p1) / 2), 2) + Math.cos(p1) * Math.cos(p2) * Math.pow(Math.sin(dl / 2), 2))); }
  function merc(lat) { return Math.log(Math.tan(Math.PI / 4 + rad(Math.max(-85, Math.min(85, lat))) / 2)) * 180 / Math.PI; }
  function toast(t, l, f) { if (HOST.toast) HOST.toast(t, l, f); }
  function jump(y) { if (HOST.jump) HOST.jump(y); else { try { W.scrollTo({ top: y, behavior: 'instant' }); } catch (e) { W.scrollTo(0, y); } } }
  function fmt(m) { m = Math.round(m); if (m < 60) return m + ' 分钟'; var h = Math.floor(m / 60), r = m % 60; return h + ' 小时' + (r ? ' ' + r + ' 分' : ''); }
  function dayLabel(i, n) { return n <= 7 ? '第 ' + (i + 1) + ' 天' : String(i + 1); }
  function noStr(n) { return n < 100 ? ('0' + n).slice(-2) : String(n); }

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
  function readDay(sec, i) {
    var pts = [];
    qsa('.tl > .r[data-ll]', sec).forEach(function (r) {
      if (r.hidden) return; var p = pll(r.getAttribute('data-ll')); if (!p) return;
      var eat = r.classList.contains('eat'), ty = r.getAttribute('data-ty') || '';
      pts.push({ n: pts.length + 1, row: r, ll: p, name: nameOf(r), kind: eat ? 'eat' : (ty === 'ms' ? 'mu' : 'sg'), dm: +r.getAttribute('data-dm') || 0, book: !!qs('.bkn,.bkl', r) });
    });
    var nopos = qsa('.tl > .r.see, .tl > .r.fun', sec).filter(function (r) { return !r.hidden && !r.getAttribute('data-ll') && !/沿途/.test(nameOf(r)); }).length;
    var pv = sec.previousElementSibling; while (pv && !(pv.matches && pv.matches('section.day'))) pv = pv.previousElementSibling;
    var ps = pv ? stayOf(pv) : '', cy = sec.getAttribute('data-city') || '';
    var spName = pv ? (ps ? '昨晚住处（' + ps + '）' : '昨晚住处') : (cy ? '起点（' + cy + '）' : '起点');      // 导航起点：不叫“出发地”，写昨晚住处或具体名
    return { i: i, sec: sec, title: titleOf(sec), pts: pts, sp: pll(sec.getAttribute('data-sp')), ep: pll(sec.getAttribute('data-ep')), stay: stayOf(sec), load: loadOf(sec), nopos: nopos, spName: spName };
  }
  function readDays() { return qsa('section.day').filter(function (s) { return !s.hidden && !s.closest('[hidden]'); }).map(readDay); }
  function sig(days) { return days.map(function (d) { return d.title + '#' + d.pts.map(function (p) { return p.ll.join(',') + p.name; }).join('|'); }).join('~'); }

  // ——— 样式：取 OpenFreeMap 的 liberty，隐藏边界和国家 / 省级标注，标注改中文（在交给 maplibre 之前改好，不会闪一下）———
  var STY = null;
  function tuneStyle(st) {
    st.layers.forEach(function (l) {
      if (HIDE_RE.test(l.id)) { l.layout = l.layout || {}; l.layout.visibility = 'none'; }
      else if (l.type === 'symbol' && l.layout && l.layout['text-field'] && !/shield/.test(l.id)) l.layout['text-field'] = ['coalesce', ['get', 'name:zh-Hans'], ['get', 'name:zh'], ['get', 'name']];
    });
    return st;
  }
  function getStyle(cb) {
    if (STY) return cb(STY);
    var x = new XMLHttpRequest(), done = false;
    function fin(v) { if (done) return; done = true; if (v) STY = v; cb(v); }
    x.open('GET', STYLE_URL); x.timeout = 10000;
    x.onload = function () { var j = null; try { j = JSON.parse(x.responseText); } catch (e) {} if (x.status === 200 && j && j.layers) { try { fin(tuneStyle(j)); } catch (e) { fin(null); } } else fin(null); };
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
    var l = el('link'); l.rel = 'stylesheet'; l.href = ML_CSS + v; D.head.appendChild(l);
    var s = el('script'); s.src = ML_JS + v; s.onload = function () { end(!!W.maplibregl); }; s.onerror = function () { end(false); }; D.head.appendChild(s);
  }
  function glOk() { try { var c = D.createElement('canvas'); return !!(c.getContext('webgl') || c.getContext('experimental-webgl')); } catch (e) { return false; } }

  // ——— 视图：同一套接口，两种实现（maplibre 街道底图 / 自画示意图）———
  function bbox(ll) { var s = 90, w = 180, n = -90, e = -180; ll.forEach(function (p) { if (p[0] < s) s = p[0]; if (p[0] > n) n = p[0]; if (p[1] < w) w = p[1]; if (p[1] > e) e = p[1]; }); return { s: s, w: w, n: n, e: e }; }
  function padFor(inst) {      // 四周留出按钮和“街道地图需要联网”那条（示意图版）的位置，标记别被盖住
    var h = inst.stage.clientHeight, w = inst.stage.clientWidth, t = inst.failed ? 74 : 54, b = 54;
    if (t + b > h - 40) { t = Math.round((h - 40) * 0.55); b = Math.round((h - 40) * 0.45); }
    return { top: t, bottom: b, left: Math.min(56, w * 0.14), right: Math.min(60, w * 0.16) };
  }
  function mlView(inst, map) {
    return {
      kind: 'ml', map: map,
      project: function (ll) { var p = map.project([ll[1], ll[0]]); return { x: p.x, y: p.y }; },
      fit: function (b, anim) {
        if (b.s === b.n && b.w === b.e) { map.jumpTo({ center: [b.w, b.s], zoom: 14 }); return; }
        map.fitBounds([[b.w, b.s], [b.e, b.n]], { padding: padFor(inst), maxZoom: 16, duration: anim ? 400 : 0 });
      },
      zoom: function () { return map.getZoom(); },
      zoomBy: function (d) { map.zoomTo(Math.max(MINZ, Math.min(MAXZ, map.getZoom() + d)), { duration: 200 }); },
      panTo: function (ll) { map.easeTo({ center: [ll[1], ll[0]], duration: 300 }); },
      resize: function () { map.resize(); },
      atMax: function () { return map.getZoom() >= MAXZ - 0.01; }, atMin: function () { return map.getZoom() <= MINZ + 0.01; },
      onMove: function (cb) { map.on('move', cb); },
      destroy: function () { try { map.remove(); } catch (e) {} }
    };
  }
  function schView(inst) {
    var st = { cx: 0, cy: 0, sc: 1, z: 0, b: null, cx0: 0, cy0: 0 }, cb = null;
    function lim() { var b = st.b; if (!b) return; st.cx = Math.max(b.w, Math.min(b.e, st.cx)); st.cy = Math.max(merc(b.s), Math.min(merc(b.n), st.cy)); }      // 取景中心不许离开站点范围
    return {
      kind: 'sch', st: st,
      project: function (ll) { var w = inst.stage.clientWidth, h = inst.stage.clientHeight; return { x: w / 2 + (ll[1] - st.cx) * st.sc, y: h / 2 - (merc(ll[0]) - st.cy) * st.sc }; },
      fit: function (b) {      // 自动取景到这一天的站点（站点范围占满可视区）
        var w = inst.stage.clientWidth || 390, h = inst.stage.clientHeight || 200, pd = padFor(inst);
        var sx = Math.max(b.e - b.w, 0.004), sy = Math.max(merc(b.n) - merc(b.s), 0.004);
        st.b = b; st.sc = Math.min((w - pd.left - pd.right) / sx, (h - pd.top - pd.bottom) / sy); st.cx = st.cx0 = (b.w + b.e) / 2; st.cy = st.cy0 = (merc(b.n) + merc(b.s)) / 2; st.z = 0; st.sc0 = st.sc;
        if (cb) cb();
      },
      zoom: function () { return st.z; },
      zoomBy: function (d, ll) {      // 只在站点范围里缩放：0–2 级；放大时以选中的站（没有就以当前中心）为中心，缩回最小时回到全景
        var o = st.z; st.z = Math.max(0, Math.min(2, st.z + d)); st.sc = (st.sc0 || st.sc) * Math.pow(2, st.z);
        if (st.z === 0) { st.cx = st.cx0; st.cy = st.cy0; } else if (d > 0 && ll) { st.cx = ll[1]; st.cy = merc(ll[0]); }
        lim(); if (cb) cb();
      },
      panBy: function (dx, dy) { st.cx -= dx / st.sc; st.cy += dy / st.sc; lim(); if (cb) cb(); },
      panTo: function (ll) { if (st.z > 0) { st.cx = ll[1]; st.cy = merc(ll[0]); lim(); if (cb) cb(); } }, resize: function () { if (cb) cb(); },
      atMax: function () { return st.z >= 2; }, atMin: function () { return st.z <= 0; },
      onMove: function (f) { cb = f; }, destroy: function () {}
    };
  }

  // ——— 颜色：每天一种（红 / 墨 / 琥珀轮换，更多天同色系深浅），类名在 CSS 里 ———
  function dayCls(i) { return 'rm-c' + (i % 3) + ' rm-s' + (Math.floor(i / 3) % 3); }

  // ——— 实例 ———
  var CUR = null;
  function build(inst) {
    var root = el('div', 'rm rm-' + inst.type);
    root.setAttribute('role', 'region'); root.setAttribute('aria-label', '路线地图');
    root.innerHTML =
      '<div class="rm-stage"><div class="rm-map"></div>' +
      '<div class="rm-ovl"><svg class="rm-svg" aria-hidden="true"></svg><div class="rm-pts"></div></div>' +
      '<button type="button" class="rm-b rm-rs" aria-label="回到全程视野" title="回到全程视野">' + ICON_RS + '</button>' +
      '<button type="button" class="rm-b rm-fsb" aria-label="全屏" title="全屏">' + ICON_FS + '</button>' +
      '<div class="rm-zm"><button type="button" class="rm-b rm-zi" aria-label="放大">+</button><button type="button" class="rm-b rm-zo" aria-label="缩小">−</button></div>' +
      '<button type="button" class="rm-b rm-sv" aria-label="把这张图存成图片" title="存成图片">存图</button>' +
      '<div class="rm-at"><p class="rm-atx" hidden>' + ATTR_HTML + '<button type="button" class="rm-b rm-ax" aria-label="关闭署名">×</button></p><button type="button" class="rm-b rm-ai" aria-label="地图数据署名" aria-expanded="false">i</button></div>' +
      '<p class="rm-note" role="status" hidden></p><p class="rm-load" role="status" hidden></p></div>' +
      '<div class="rm-drw"><div class="rm-pop" hidden></div><p class="rm-leg"></p><div class="rm-trow"><div class="rm-tabs"></div><button type="button" class="rm-tl" aria-expanded="false">站点 ˄</button></div><div class="rm-panel"></div>' +
      '<a class="btn rm-navd" href="#" role="button">导航这一天 ›</a><p class="rm-hint"></p></div>';
    inst.root = root; inst.stage = qs('.rm-stage', root); inst.mapEl = qs('.rm-map', root); inst.svg = qs('.rm-svg', root); inst.pts = qs('.rm-pts', root);
    inst.pop = qs('.rm-pop', root); inst.note = qs('.rm-note', root); inst.load = qs('.rm-load', root); inst.dr = qs('.rm-drw', root); inst.leg = qs('.rm-leg', root); inst.tabs = qs('.rm-tabs', root); inst.panel = qs('.rm-panel', root); inst.navd = qs('.rm-navd', root); inst.hint = qs('.rm-hint', root);
    return root;
  }
  function curDay(inst) { return inst.sel >= 0 ? inst.days[inst.sel] : null; }
  function dayPts(inst) {
    var d = curDay(inst), a = [];
    if (d) { d.pts.forEach(function (p) { a.push(p.ll); }); if (d.ep) a.push(d.ep); }
    else inst.days.forEach(function (x) { x.pts.forEach(function (p) { a.push(p.ll); }); });
    return a;
  }
  function fitView(inst, anim) {
    if (!inst.view) return; var a = dayPts(inst); if (!a.length) return;
    inst.view.fit(bbox(a), anim);
  }

  // 叠层：线 + 标记。每次状态变（选天 / 选点 / 重读模型）重建，地图移动只重新定位。
  // 标记本身不接收鼠标 / 手指（pointer-events:none）：手指落在标记上时双指缩放、拖动照样交给地图（原来会变成整页缩放）；
  // 点按由舞台上的一个监听按“离点击位置最近”挑标记（tapHit），挤在一起时弹列表让人选。
  function draw(inst) {
    inst.svg.innerHTML = ''; inst.pts.innerHTML = ''; inst.marks = []; inst.lines = [];
    var n = inst.days.length, sel = inst.sel, NS = 'http://www.w3.org/2000/svg';
    function line(d, cls) {
      var ll = d.pts.map(function (p) { return p.ll; }); if (ll.length < 2) return;
      var c = D.createElementNS(NS, 'polyline'); c.setAttribute('class', 'rm-lc ' + cls);
      var l = D.createElementNS(NS, 'polyline'); l.setAttribute('class', 'rm-ln ' + cls);
      inst.svg.appendChild(c); inst.svg.appendChild(l); inst.lines.push({ ll: ll, els: [c, l] });
    }
    function add(e, ll, meta) { inst.pts.appendChild(e); var m = { el: e, ll: ll, badge: e.className.indexOf('rm-db') >= 0 }, k; if (meta) for (k in meta) if (meta.hasOwnProperty(k)) m[k] = meta[k]; inst.marks.push(m); return m; }
    inst.days.forEach(function (d, i) {
      var cls = dayCls(i) + (sel >= 0 && sel !== i ? ' rm-dim' : '');
      line(d, cls);
      if (sel === i) return;
      // 其他天 / 全程：小方点 + 每天第一站的天数章
      d.pts.forEach(function (p) { var e = el('i', 'rm-dt ' + dayCls(i) + (sel >= 0 ? ' rm-dim' : '')); add(e, p.ll, { dot: true }); });
      if (sel < 0 && d.pts.length) {
        var b = el('button', 'rm-mk rm-db ' + dayCls(i), '<i>' + (i + 1) + '</i>'); b.type = 'button'; b.setAttribute('data-day', i); b.tabIndex = -1; b.setAttribute('aria-label', '第 ' + (i + 1) + ' 天：' + d.title); add(b, d.pts[0].ll, { kind: 'day', day: i, label: '第 ' + (i + 1) + ' 天：' + (d.title || '') });
      }
    });
    var d = curDay(inst);
    if (d) {
      (inst.gray || []).forEach(function (g, gi) { var e = el('button', 'rm-mk rm-gy', '<i></i>'); e.type = 'button'; e.setAttribute('data-g', gi); e.tabIndex = -1; e.setAttribute('aria-label', '顺路可去：' + g.c.n); add(e, g.ll, { kind: 'g', label: '顺路可去：' + g.c.n, small: true }); });
      if (d.ep) { var h = el('button', 'rm-mk rm-hm ' + dayCls(inst.sel), '<i>住</i>'); h.type = 'button'; h.setAttribute('data-hm', '1'); h.setAttribute('aria-label', '住 · 约' + (d.stay ? '（' + d.stay + '，大概位置）' : '')); add(h, d.ep, { kind: 'hm', label: '住 · 约' + (d.stay ? ' ' + d.stay : '') }); }   // 先画住：和某一站重叠时站在上面
      d.pts.forEach(function (p) {
        var cls = 'rm-mk ' + dayCls(inst.sel) + (p.kind === 'mu' ? ' rm-mu' : '') + (p.kind === 'eat' ? ' rm-eat' : '') + (inst.cur === p.n ? ' rm-cur' : '');
        var b = el('button', cls, '<i>' + p.n + '</i>'); b.type = 'button'; b.setAttribute('data-n', p.n); b.setAttribute('aria-label', p.n + ' ' + p.name); add(b, p.ll, { kind: 'n', n: p.n, label: p.n + ' ' + p.name });
      });
    }
    paintTag(inst, true);
    place(inst);
  }
  // 选中一站：在标记旁边显示名字小标签（方形纸色 + 细线）
  function paintTag(inst, quiet) {
    inst.marks = (inst.marks || []).filter(function (m) { if (m.tag) { if (m.el.parentNode) m.el.parentNode.removeChild(m.el); return false; } return true; });
    var d = curDay(inst), p = d && inst.cur ? d.pts[inst.cur - 1] : null; if (!p) { if (!quiet) place(inst); return; }
    var e = el('i', 'rm-tg', '<span>' + esc(p.name) + '</span>'); e.setAttribute('aria-hidden', 'true'); inst.pts.appendChild(e); inst.marks.push({ el: e, ll: p.ll, tag: true });
    if (!quiet) place(inst);
  }
  function place(inst) {
    var v = inst.view; if (!v) return;
    var sch = v.kind === 'sch', W_ = inst.stage.clientWidth, H_ = inst.stage.clientHeight, topM = (inst.failed || inst.fs) ? 50 : 26, botM = inst.fs ? 70 : 26;
    inst.marks.forEach(function (m) {
      var q = v.project(m.ll), x = q.x, y = q.y;
      if (sch && !m.dot) { x = Math.max(24, Math.min(W_ - 24, x)); y = Math.max(topM, Math.min(H_ - botM, y)); }      // 示意图：编号章不许跑出可视区（贴着边放，半透明）
      m.px = x; m.py = y; m.el.style.transform = 'translate(' + Math.round(x) + 'px,' + Math.round(y) + 'px)';
      m.edge = sch && !m.dot && !m.tag && (Math.abs(x - q.x) > 1 || Math.abs(y - q.y) > 1); if (!m.tag) m.el.classList.toggle('rm-edge', !!m.edge);
      if (m.tag) m.el.classList.toggle('rm-tgl', x > W_ - 150);
    });
    inst.lines.forEach(function (l) {
      var s = ''; l.ll.forEach(function (ll) { var q = v.project(ll); s += (Math.round(q.x * 10) / 10) + ',' + (Math.round(q.y * 10) / 10) + ' '; });
      l.els[0].setAttribute('points', s); l.els[1].setAttribute('points', s);
    });
    if (inst.sel < 0) cullBadges(inst); else denseMarks(inst);
    if (sch) schExtras(inst);
    zoomBtns(inst);
  }
  // 标记挤在一起（相距 <30px）：缩成 22px，选中时有名字标签
  function denseMarks(inst) {
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
  // 总览：挤在一起的天数章只留一个，写成“2–5”（原来是剔除，看不出被合并了）；被合并的天仍能点到（点击挑选）
  function cullBadges(inst) {
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
  // 示意图版：站名小标签（贪心，不重叠）+ 比例尺 + 北向
  function schExtras(inst) {
    var v = inst.view, d = curDay(inst), host = inst.pts, old = qsa('.rm-lb,.rm-sc', host), i;
    old.forEach(function (e) { e.parentNode.removeChild(e); });
    if (!v || v.kind !== 'sch') return;
    if (d) {
      var boxes = [];
      d.pts.forEach(function (p) {
        var m = inst.marks.filter(function (k) { return k.kind === 'n' && k.n === p.n; })[0]; if (!m) return;
        var nm = p.name.length > 9 ? p.name.slice(0, 9) + '…' : p.name, w = nm.length * 12 + 12, x = m.px + 16, y = m.py - 9;
        if (x + w > inst.stage.clientWidth - 4) x = m.px - 16 - w;
        var hit = boxes.some(function (b) { return x < b.x + b.w && x + w > b.x && y < b.y + 18 && y + 18 > b.y; }); if (hit) return;
        boxes.push({ x: x, y: y, w: w }); var e = el('span', 'rm-lb', esc(nm)); e.style.cssText = 'left:' + Math.round(x) + 'px;top:' + Math.round(y) + 'px'; host.appendChild(e);
      });
    }
    // 比例尺：站点范围的纬度中心处，每像素多少公里
    var b = v.st.b; if (b) {
      var lat = (b.s + b.n) / 2, kmpp = 111.32 * Math.cos(rad(lat)) / v.st.sc, nice = [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000], km = nice[0];
      for (i = 0; i < nice.length; i++) if (nice[i] / kmpp <= 110) km = nice[i];
      var wpx = Math.max(24, Math.round(km / kmpp)), sc = el('p', 'rm-sc', '<i style="width:' + wpx + 'px"></i><span>' + (km < 1 ? Math.round(km * 1000) + ' 米' : km + ' 公里') + '</span><b>北 ↑</b>'); host.appendChild(sc);
    }
  }
  function zoomBtns(inst) {
    var v = inst.view; if (!v) return; var zi = qs('.rm-zi', inst.root), zo = qs('.rm-zo', inst.root);
    zi.disabled = v.atMax(); zo.disabled = v.atMin();
  }
  // 点按：挑离点击位置最近的标记；一处只有一个 → 当作点了它；挤在一起有几个 → 弹列表选
  function tapHit(inst, e) {
    var r = inst.stage.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, c = [];
    inst.marks.forEach(function (m) {
      if (m.dot || m.tag || !m.kind) return; var dx = m.px - x, dy = m.py - y, d = Math.sqrt(dx * dx + dy * dy);
      if (d <= (m.small ? 20 : 26)) c.push({ m: m, d: d });
    });
    if (!c.length) return false;
    c.sort(function (a, b) { return a.d - b.d; });
    if (c.length === 1 || c[1].d - c[0].d > 12) { c[0].m.el.click(); return true; }
    showPick(inst, c); return true;
  }
  function showPick(inst, c) {
    inst.pick = c.map(function (x) { return x.m; });
    showPop(inst, '<div class="rm-pk"><span class="rm-pt">这里有 ' + c.length + ' 处，点选一个</span>' + c.slice(0, 6).map(function (x, i) { return '<button type="button" class="rm-pi" data-pi="' + i + '">' + esc(x.m.label) + '</button>'; }).join('') + '</div>');
    inst.popOf = { pick: true };
  }

  // 图例、标签条、信息头、站点列表
  function paintLeg(inst) {
    var n = inst.days.length, d = curDay(inst), h = '';
    function sq(i, t) { return '<span class="rm-lg ' + dayCls(i) + '"><i></i>' + t + '</span>'; }
    if (d) h = sq(inst.sel, '第 ' + (inst.sel + 1) + ' 天');
    else if (n <= 7) h = inst.days.map(function (x, i) { return sq(i, '第 ' + (i + 1) + ' 天'); }).join('');
    else h = '<span class="rm-lg2">共 ' + n + ' 天，每天一种颜色，点下面的数字看那一天</span>';
    if (d && inst.gray && inst.gray.length) h += '<span class="rm-lg rm-lgg"><i></i>顺路可去</span>';
    if (d && d.nopos) h += '<span class="rm-lg2">有 ' + d.nopos + ' 个地方没有位置，没画</span>';
    h += '<span class="rm-lg2 rm-st">站点之间是直线示意，不是行车路线</span>';
    inst.leg.innerHTML = h;
  }
  function paintTabs(inst) {
    var n = inst.days.length, h = '<button type="button" class="rm-tb' + (inst.sel < 0 ? ' on' : '') + '" data-i="-1">全程</button>';
    inst.days.forEach(function (d, i) { h += '<button type="button" class="rm-tb' + (inst.sel === i ? ' on' : '') + '" data-i="' + i + '">' + dayLabel(i, n) + '</button>'; });
    inst.tabs.innerHTML = h; inst.tabs.className = 'rm-tabs' + (n > 6 ? ' long' : '');
    var on = qs('.rm-tb.on', inst.tabs); if (on && inst.tabs.scrollWidth > inst.tabs.clientWidth) inst.tabs.scrollLeft = Math.max(0, on.offsetLeft - inst.tabs.clientWidth / 2 + on.offsetWidth / 2);
  }
  function paintPanel(inst) {
    var d = curDay(inst), h = '', n = inst.days.length;
    if (!d) {
      h = '<button type="button" class="rm-hd" aria-expanded="' + (inst.shut ? 'false' : 'true') + '"><span class="rm-no">' + (n < 100 ? noStr(n) : n) + '</span><span class="rm-hdt"><small>全程</small><b>共 ' + n + ' 天</b></span><em>' + (inst.shut ? '展开 ›' : '收起 ‹') + '</em></button><div class="rm-rows">';
      inst.days.forEach(function (x, i) { h += '<button type="button" class="rm-row rm-dr" data-i="' + i + '"><b>' + noStr(i + 1) + '</b><span class="rm-t"><strong>' + esc(x.title || '第 ' + (i + 1) + ' 天') + '</strong><small>' + x.pts.length + ' 个有位置的地方' + (x.stay ? ' · 住 ' + esc(x.stay) : '') + '</small></span></button>'; });
      h += '</div>';
    } else {
      var info = d.load.slice(); if (d.stay) info.push('住 ' + d.stay);
      h = '<button type="button" class="rm-hd" aria-expanded="' + (inst.shut ? 'false' : 'true') + '"><span class="rm-no">' + noStr(d.i + 1) + '</span><span class="rm-hdt"><small>第 ' + (d.i + 1) + ' 天</small><b>' + esc(d.title) + '</b></span><em>' + (inst.shut ? '展开 ›' : '收起 ‹') + '</em></button>' +
        (info.length ? '<p class="rm-ld">今天：' + esc(info.join(' · ')) + '</p>' : '') + '<div class="rm-rows">';
      d.pts.forEach(function (p) {
        h += '<button type="button" class="rm-row' + (inst.cur === p.n ? ' on' : '') + '" data-n="' + p.n + '"><b>' + p.n + '</b><span class="rm-t"><strong>' + esc(p.name) + '</strong>' + (p.kind === 'mu' ? '<small>博物馆</small>' : (p.kind === 'eat' ? '<small>吃饭</small>' : '')) + '</span>' + (p.book ? '<em>要预约</em>' : '') + '</button>';
      });
      if (d.ep) h += '<button type="button" class="rm-row rm-hrow" data-hm="1"><b>住</b><span class="rm-t"><strong>住 · 约' + (d.stay ? ' ' + esc(d.stay) : '') + '</strong><small>大概位置，不是酒店</small></span></button>';
      h += '</div>';
    }
    inst.panel.innerHTML = h; inst.panel.className = 'rm-panel' + (inst.shut ? ' shut' : '');
    var nv = !!d && navSegs(d).length > 0; inst.navd.hidden = !nv; inst.hint.hidden = !nv;
    if (nv) { var sg = navSegs(d), ht = navHint(d); inst.hint.textContent = ht; inst.hint.hidden = !ht; inst.navd.setAttribute('href', sg.length === 1 ? sg[0].url : '#'); navState(inst); }
  }
  // 断网：“导航这一天”置灰写明原因，点它不弹分段层
  function navState(inst) {
    if (!inst || !inst.navd) return; var off = navigator.onLine === false;
    inst.navd.classList.toggle('off', off); inst.navd.setAttribute('aria-disabled', off ? 'true' : 'false'); inst.navd.textContent = off ? '没网，暂时不能导航' : '导航这一天 ›';
  }
  W.addEventListener('offline', function () { navState(CUR); });
  W.addEventListener('online', function () { navState(CUR); });
  function paintAll(inst) { paintLeg(inst); paintTabs(inst); paintPanel(inst); }

  // ——— 选天 / 选点 ———
  function selectDay(inst, i, anim) {
    if (i >= inst.days.length) i = -1;
    inst.sel = i; inst.cur = 0; inst.gray = []; hidePop(inst); markOn(inst);
    paintAll(inst); draw(inst); fitView(inst, anim !== false); loadGray(inst);
  }
  function markOn(inst) {
    qsa('section.day.rm-on').forEach(function (s) { s.className = s.className.replace(/\s*rm-(on|c\d|s\d)\b/g, ''); });
    if (inst.type === 'day' && inst.sec && !inst.sec.hidden) inst.sec.className += ' rm-on ' + dayCls(inst.home);   // 页面行里的编号章（CSS 计数器）用同一个颜色
  }
  function setCur(inst, n, how) {
    var d = curDay(inst); if (!d) return; inst.cur = n; paintTag(inst);
    qsa('.rm-mk', inst.pts).forEach(function (b) { if (b.hasAttribute('data-n')) b.classList.toggle('rm-cur', +b.getAttribute('data-n') === n); });
    qsa('.rm-row[data-n]', inst.panel).forEach(function (b) { var on = +b.getAttribute('data-n') === n; b.classList.toggle('on', on); if (on && how && how.list && inst.panel.scrollHeight > inst.panel.clientHeight) { var top = b.offsetTop - inst.panel.clientHeight / 2 + b.offsetHeight / 2; inst.panel.scrollTop = Math.max(0, top); } });
    var p = d.pts[n - 1];
    if (p && how && how.pan && inst.view) {
      var q = inst.view.project(p.ll), w = inst.stage.clientWidth, h = inst.stage.clientHeight;
      if (q.x < 50 || q.x > w - 50 || q.y < 50 || q.y > h - 50) inst.view.panTo(p.ll);
    }
  }
  function rowTop(inst) { var r = inst.root.getBoundingClientRect(); return r.bottom; }
  function toRow(inst, p) {
    var d = curDay(inst); if (!d || !p.row) return;
    inst.lock = Date.now() + 900;
    var top = p.row.getBoundingClientRect().top + (W.pageYOffset || 0) - rowTop0(inst) - 12;
    jump(Math.max(0, top)); p.row.classList.add('flash'); setTimeout(function () { p.row.classList.remove('flash'); }, 1600);
  }
  function rowTop0(inst) { var nv = qs('.daynav'), a = 0; if (nv) { var cs = getComputedStyle(nv); if (cs.position === 'sticky') a = nv.offsetHeight; } return a + (inst.root.offsetHeight || 0); }
  function showPop(inst, h) { inst.pop.innerHTML = h; inst.pop.hidden = false; }
  function hidePop(inst) { inst.pop.hidden = true; inst.pop.innerHTML = ''; inst.popOf = null; }
  function popMark(inst, p) {
    var h = '<span class="rm-pn"><b>' + p.n + '</b>' + esc(p.name) + '</span>';
    if (inst.type === 'ov' || inst.fs) h += '<button type="button" class="rm-pb" data-act="row">在行程里看 ›</button>';
    inst.popOf = { mark: p.n }; showPop(inst, h);
  }

  // ——— 顺路可去（灰点）：复用顺路加一站的候选、试算、加站和撤销（site.js 里 window.zNpMap）———
  function anchorsOf(d) {
    return d.pts.map(function (p) { return p.row; }).filter(function (r) {
      return (r.classList.contains('see') || r.classList.contains('fun')) && r.getAttribute('data-np') !== 'v' && !r.getAttribute('data-at') && !r.getAttribute('data-rain') && !r.getAttribute('data-fo') && !r.getAttribute('data-on') && !/沿途慢慢走/.test(nameOf(r));
    });
  }
  function loadGray(inst) {
    var d = curDay(inst), N = W.zNpMap; inst.gray = [];
    if (!d || !N || d.sec.dataset.oi == null || !navigator.onLine) { paintLeg(inst); return; }
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
      paintLeg(inst); draw(inst);
    }, function () { paintLeg(inst); });
  }
  function popGray(inst, g) {
    showPop(inst, '<span class="rm-pn"><i class="rm-gq"></i>' + esc(g.c.n) + '<small>' + esc(g.label) + '</small></span><button type="button" class="rm-pb" data-act="add">加到这天</button>');
    inst.popOf = { gray: g };
  }
  function addGray(inst, g) {
    var d = curDay(inst), N = W.zNpMap; if (!d || !N) return;
    var t; try { t = N.tryIns(d.sec, g.S, g.c); } catch (e) { t = { ok: false }; }
    if (!t || !t.ok) { toast('这天已经排满了，加不进去'); return; }
    hidePop(inst); N.commit(d.sec, g.S, g.c);
  }

  // ——— 全屏：优先 Fullscreen API；iOS Safari 没有（非视频元素不能全屏）→ 铺满视口的“伪全屏”，锁背景滚动，返回键 / 关闭 / Esc 退出，退出后回到原来的滚动位置 ———
  function lockBody(inst) {
    B.style.top = (-inst.y) + 'px'; B.classList.add('rm-lock');
  }
  function unlockBody(inst) {
    B.classList.remove('rm-lock'); B.style.top = '';
    function back() { try { W.scrollTo({ top: inst.y, behavior: 'instant' }); } catch (e) { W.scrollTo(0, inst.y); } }
    back();
    // 返回键 / 站里的 history.back() 会让浏览器按“上一条历史记的位置”再滚一次：稍后再校正（只在没人再锁、没人再进全屏时）
    [60, 200, 500].forEach(function (t) { setTimeout(function () { if (!B.classList.contains('rm-lock') && Math.abs((W.pageYOffset || 0) - inst.y) > 1 && !(CUR && CUR.fs)) back(); }, t); });
  }
  function fsHeight(inst) { if (inst.fs && !inst.native) inst.root.style.height = (W.innerHeight || D.documentElement.clientHeight) + 'px'; }
  function enterFS(inst) {
    if (inst.fs) return; var root = inst.root;
    inst.y = W.pageYOffset || 0;      // 先记滚动位置，再占历史、搬节点、锁背景（搬走节点页面会变矮，滚动位置被夹小；锁了背景 scrollY 就是 0）
    inst.addedPk = !B.classList.contains('pk-open'); B.classList.add('pk-open');   // 站里的 MutationObserver 在这之后的微任务里 pushState：那一刻页面还没锁，历史条目记的是真实位置
    inst.ph = D.createComment('rm'); root.parentNode.insertBefore(inst.ph, root); B.appendChild(root);
    root.classList.add('rm-fs'); inst.fs = true;
    Promise.resolve().then(function () { if (inst.fs) lockBody(inst); });
    var b = qs('.rm-fsb', root); b.innerHTML = '<span class="rm-xx" aria-hidden="true">×</span><span class="rm-xt">关上</span>'; b.setAttribute('aria-label', '退出全屏'); b.title = '退出全屏'; b.classList.add('pk-x');
    inst.dr.classList.remove('open'); var tl0 = qs('.rm-tl', root); if (tl0) { tl0.textContent = '站点 ˄'; tl0.setAttribute('aria-expanded', 'false'); }
    var api = !IOS && (root.requestFullscreen || root.webkitRequestFullscreen) && (D.fullscreenEnabled || D.webkitFullscreenEnabled);
    inst.native = false;
    if (api) { try { var pr = (root.requestFullscreen || root.webkitRequestFullscreen).call(root); inst.native = true; if (pr && pr.catch) pr.catch(function () { inst.native = false; fsHeight(inst); }); } catch (e) { inst.native = false; } }
    fsHeight(inst); if (inst.coopOff) inst.coopOff();
    if (!qs('.rm-tb', inst.tabs)) paintTabs(inst);
    paintAll(inst); settle(inst);
  }
  function exitFS(inst) {
    if (!inst.fs) return; var root = inst.root;
    inst.fs = false; root.classList.remove('rm-fs'); root.style.height = '';
    if (D.fullscreenElement === root || D.webkitFullscreenElement === root) { try { (D.exitFullscreen || D.webkitExitFullscreen).call(D); } catch (e) {} }
    if (inst.ph && inst.ph.parentNode) { inst.ph.parentNode.insertBefore(root, inst.ph); inst.ph.parentNode.removeChild(inst.ph); }
    var b = qs('.rm-fsb', root); b.innerHTML = ICON_FS; b.setAttribute('aria-label', '全屏'); b.title = '全屏'; b.classList.remove('pk-x');
    inst.dr.classList.remove('open'); root.style.removeProperty('--dh');
    unlockBody(inst); if (inst.addedPk) B.classList.remove('pk-open'); if (inst.coopOff) inst.coopOff();
    if (inst.type === 'day' && inst.sel !== inst.home) { inst.sel = inst.home; inst.cur = 0; inst.gray = []; markOn(inst); paintAll(inst); draw(inst); loadGray(inst); }
    settle(inst); fitView(inst, false);
  }
  function settle(inst) { [0, 120, 400].forEach(function (t) { setTimeout(function () { if (!inst.alive) return; syncDrawer(inst); if (inst.view) inst.view.resize(); place(inst); }, t); }); }
  // 全屏：站点列表是底部的抽屉，默认只露一条标签条；抽屉的高度写成 --dh，让“存图”“i”站在它上面
  function syncDrawer(inst) { if (inst.fs && inst.dr) inst.root.style.setProperty('--dh', inst.dr.offsetHeight + 'px'); }
  function toggleDrawer(inst) {
    var on = !inst.dr.classList.contains('open'); inst.dr.classList.toggle('open', on);
    var tl = qs('.rm-tl', inst.root); if (tl) { tl.textContent = on ? '收起 ˅' : '站点 ˄'; tl.setAttribute('aria-expanded', on ? 'true' : 'false'); }
    syncDrawer(inst); settle(inst);
  }
  D.addEventListener('fullscreenchange', function () { if (CUR && CUR.fs && CUR.native && !D.fullscreenElement) exitFS(CUR); });
  D.addEventListener('webkitfullscreenchange', function () { if (CUR && CUR.fs && CUR.native && !D.webkitFullscreenElement) exitFS(CUR); });
  W.addEventListener('resize', function () { if (CUR) { fsHeight(CUR); if (CUR.view) { CUR.view.resize(); place(CUR); } } });
  W.addEventListener('orientationchange', function () { setTimeout(function () { if (CUR) { fsHeight(CUR); if (CUR.view) CUR.view.resize(); } }, 300); });

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
    return segs > 1 ? '这天一共 ' + a.length + ' 个点，手机导航要分 ' + segs + ' 段（' + lim + '），按顺序一段一段点。' : '';
  }
  function goUrl(u) {
    if (navigator.onLine === false) { toast('没网，暂时不能导航'); return; }
    if (APP !== 'google' && mobileUA() && HOST.open) { HOST.open(u, '高德地图'); return; }      // 手机：callnative=1 唤起高德 App（没装 1.6 秒后提示）
    var w = null; try { w = W.open(u, '_blank', 'noopener'); } catch (e) {}
    if (!w) location.href = u;
  }
  function navDay(d) {
    if (navigator.onLine === false) { toast('没网，暂时不能导航'); return; }
    var segs = navSegs(d); if (!segs.length) { toast('这天没有可导航的位置'); return; }
    if (HOST.track) HOST.track('路线地图·导航这一天');
    if (segs.length === 1) { goUrl(segs[0].url); return; }
    var who = APP === 'google' ? '用谷歌地图打开 ›' : '用高德打开 ›';
    var mask = el('div', 'pk-mask'), sh = el('div', 'pk rm-sheet'); sh.setAttribute('role', 'dialog');
    var h = '<div class="pk-h"><b>导航这一天</b><button type="button" class="pk-x">关上</button></div><p class="xnote">' + esc(navHint(d)) + '路线按驾车排好，到了地图里可以改成步行或公交。</p><div class="xd">';
    segs.forEach(function (s, i) { h += '<a class="rm-seg" href="' + esc(s.url) + '" data-i="' + i + '"><span class="rm-sg1"><b>第 ' + (i + 1) + ' 段：</b><small>' + s.pts.map(function (p) { return esc(p.n); }).join(' → ') + '</small></span><em>' + who + '</em></a>'; });
    sh.innerHTML = h + '</div>';
    var had = B.classList.contains('pk-open');
    function cl() { mask.remove(); sh.remove(); if (!had) B.classList.remove('pk-open'); }
    sh.addEventListener('click', function (e) { var x = e.target.closest('.pk-x'); if (x) return cl(); var a = e.target.closest('a.rm-seg'); if (a) { e.preventDefault(); goUrl(a.getAttribute('href')); } });
    mask.addEventListener('click', cl); B.appendChild(mask); B.appendChild(sh); B.classList.add('pk-open');
  }

  // ——— 存成图片：底图 + 线 + 标记 + 标题 + 二维码（只放线路网址）；底图取不到就存示意图版并说明 ———
  function saveImg(inst) {
    function run() {
      var CW = 1080, sw = inst.stage.clientWidth || 390, sh = inst.stage.clientHeight || 300, k = CW / sw, mh = Math.round(sh * k), HD = 190, FT = 190, CH = HD + mh + FT;
      var cv = D.createElement('canvas'); cv.width = CW; cv.height = CH; var x = cv.getContext('2d');
      var cs = getComputedStyle(D.documentElement), g = function (n, f) { return (cs.getPropertyValue(n) || '').trim() || f; };
      var BG = g('--bg', '#f4f2ec'), INK = g('--ink', '#1c1d1a'), SUB = g('--sub', '#5d5f59'), RED = g('--red', '#a63d27'), AMB = g('--amb', '#8a5a00'), SERIF = '"Noto Serif SC",serif', SANS = '"Noto Sans SC",sans-serif';
      var PAL = [RED, INK, AMB];
      x.fillStyle = BG; x.fillRect(0, 0, CW, CH);
      x.fillStyle = g('--card', '#ebe8df'); x.fillRect(0, HD, CW, mh);
      var real = false;
      if (inst.view && inst.view.kind === 'ml') {
        try { var mc = inst.view.map.getCanvas(); x.save(); x.beginPath(); x.rect(0, HD, CW, mh); x.clip(); x.filter = 'saturate(.5) sepia(.16)'; x.drawImage(mc, 0, HD, CW, mh); x.restore(); x.getImageData(0, HD, 1, 1); real = true; }
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
      var m = el('div', 'hmap-zoom shotv rm-shot'), had = B.classList.contains('pk-open');
      m.innerHTML = '<button type="button" class="hz-x">关上</button><div class="hz-b"><img alt="路线图" src="' + url + '"></div><p class="shotp">' + (real ? '' : '街道底图没取到，存的是示意图版。') + '手机上长按图片保存；电脑上 <a download="走你-路线图.png" href="' + url + '">点这里下载</a></p>';
      B.appendChild(m); B.classList.add('pk-open');
      function cl() { m.remove(); if (!had) B.classList.remove('pk-open'); }
      qs('.hz-x', m).addEventListener('click', cl);
    }
    if (W.qrcode) run(); else { var s = el('script'); s.src = '/assets/qr.js'; s.onload = run; s.onerror = run; D.head.appendChild(s); }
  }

  // ——— 事件 ———
  function selLL(inst) { var d = curDay(inst), p = d && inst.cur ? d.pts[inst.cur - 1] : null; return p ? p.ll : null; }
  function zoomStep(inst, dz) { if (!inst.view) return; inst.view.zoomBy(dz, selLL(inst)); if (inst.view.kind === 'sch') place(inst); }
  function wire(inst) {
    var root = inst.root;
    // 标记不接收手指：点按在这里按“最近的标记”挑（挤在一起弹列表）；拖动（示意图）也在这里
    inst.stage.addEventListener('click', function (e) {
      if (inst.dragged) { inst.dragged = false; e.__rmHit = true; return; }
      if (e.target.closest('.rm-b,.rm-at,.rm-note,.rm-mk,.rm-zm')) return;
      if (tapHit(inst, e)) e.__rmHit = true;
    });
    wireDrag(inst);
    root.addEventListener('click', function (e) {
      var t = e.target, b;
      if ((b = t.closest('.rm-fsb'))) { if (inst.fs) exitFS(inst); else enterFS(inst); return; }
      if (t.closest('.rm-rs')) { fitView(inst, true); return; }
      if (t.closest('.rm-tl')) { toggleDrawer(inst); return; }
      if (t.closest('.rm-zi')) { zoomStep(inst, 1); return; }
      if (t.closest('.rm-zo')) { zoomStep(inst, -1); return; }
      if (t.closest('.rm-sv')) { saveImg(inst); return; }
      if (t.closest('.rm-ai')) { var x = qs('.rm-atx', root), open = x.hidden; x.hidden = !open; qs('.rm-ai', root).setAttribute('aria-expanded', open ? 'true' : 'false'); return; }
      if (t.closest('.rm-ax')) { qs('.rm-atx', root).hidden = true; qs('.rm-ai', root).setAttribute('aria-expanded', 'false'); return; }
      if ((b = t.closest('.rm-tb'))) { selectDay(inst, +b.getAttribute('data-i')); return; }
      if (t.closest('.rm-hd')) { inst.shut = !inst.shut; paintPanel(inst); settle(inst); return; }
      if ((b = t.closest('.rm-dr'))) { selectDay(inst, +b.getAttribute('data-i')); return; }
      if ((b = t.closest('.rm-navd'))) {
        var d = curDay(inst); if (!d) return;
        e.preventDefault(); navDay(d);      // 一段：直接去；多段：弹选择层
        return;
      }
      if ((b = t.closest('.rm-pi'))) { var pm = inst.pick && inst.pick[+b.getAttribute('data-pi')]; hidePop(inst); if (pm) pm.el.click(); return; }
      if ((b = t.closest('.rm-pb'))) {
        var act = b.getAttribute('data-act');
        if (act === 'add' && inst.popOf && inst.popOf.gray) addGray(inst, inst.popOf.gray);
        if (act === 'row' && inst.popOf && inst.popOf.mark) { var dd = curDay(inst), pp = dd && dd.pts[inst.popOf.mark - 1]; if (pp) { if (inst.fs) exitFS(inst); toRowAny(inst, dd, pp); } }
        return;
      }
      if ((b = t.closest('.rm-mk'))) {
        if (b.hasAttribute('data-day')) { selectDay(inst, +b.getAttribute('data-day')); return; }
        if (b.hasAttribute('data-n')) {
          var n = +b.getAttribute('data-n'), dd2 = curDay(inst), p2 = dd2 && dd2.pts[n - 1]; if (!p2) return;
          setCur(inst, n, { list: true }); hidePop(inst);
          if (inst.type === 'day' && !inst.fs) toRow(inst, p2); else popMark(inst, p2);
          return;
        }
        if (b.hasAttribute('data-g')) { var g = inst.gray[+b.getAttribute('data-g')]; if (g) { popGray(inst, g); } return; }
        if (b.hasAttribute('data-hm')) { var dh = curDay(inst); if (dh && dh.ep) { inst.view.panTo(dh.ep); showPop(inst, '<span class="rm-pn"><b>住</b>住 · 约' + (dh.stay ? esc(dh.stay) : '') + '<small>大概位置，不是酒店</small></span>'); } return; }
        return;
      }
      if ((b = t.closest('.rm-row'))) {
        if (b.hasAttribute('data-n')) { var nn = +b.getAttribute('data-n'), d3 = curDay(inst), p3 = d3 && d3.pts[nn - 1]; setCur(inst, nn, { pan: true }); if (p3 && inst.view) { inst.view.panTo(p3.ll); popMark(inst, p3); } }
        if (b.hasAttribute('data-hm')) { var d4 = curDay(inst); if (d4 && d4.ep) inst.view.panTo(d4.ep); }
        return;
      }
      if (!t.closest('.rm-pop') && !e.__rmHit) hidePop(inst);
    });
  }
  // 示意图版也能拖：指针按下后移动 >6px 算拖动（拖动后那一下 click 不当点按）；全屏时手指拖动归地图，非全屏时竖向仍滚页面
  function wireDrag(inst) {
    var st = null;
    inst.stage.addEventListener('pointerdown', function (e) { if (!inst.view || inst.view.kind !== 'sch' || e.target.closest('.rm-b,.rm-at')) return; st = { x: e.clientX, y: e.clientY, id: e.pointerId, moved: false }; });
    inst.stage.addEventListener('pointermove', function (e) {
      if (!st || e.pointerId !== st.id || !inst.view || inst.view.kind !== 'sch') return;
      var dx = e.clientX - st.x, dy = e.clientY - st.y;
      if (!st.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      st.moved = true; inst.dragged = true; st.x = e.clientX; st.y = e.clientY; inst.view.panBy(dx, dy);
    });
    function end(e) { if (st && st.moved) setTimeout(function () { inst.dragged = false; }, 60); st = null; }
    inst.stage.addEventListener('pointerup', end); inst.stage.addEventListener('pointercancel', end);
  }
  function toRowAny(inst, d, p) {
    // 在行程里看：回到页面里那一行并高亮（全屏要先退出；总览里点的那一天可能不是第一天，行在页面里）
    var y = p.row.getBoundingClientRect().top + (W.pageYOffset || 0) - Math.round((W.innerHeight || 600) / 3);
    y = Math.max(0, y); jump(y); inst.y = y;      // 退全屏后的“位置校正”也跟着去这一行，别又拽回原来的位置
    p.row.classList.add('flash'); setTimeout(function () { p.row.classList.remove('flash'); }, 1600);
  }

  // ——— 打开 / 关闭 ———
  function closeInst(inst) {
    if (!inst) return;
    if (inst.fs) exitFS(inst);
    inst.alive = false; clearTimeout(inst.timer); clearTimeout(inst.tchk); clearTimeout(inst.hard); if (inst.mo) inst.mo.disconnect();
    if (inst.onScroll) W.removeEventListener('scroll', inst.onScroll);
    if (inst.onRowClick) D.removeEventListener('click', inst.onRowClick, true);
    if (inst.view) inst.view.destroy();
    if (inst.root && inst.root.parentNode) inst.root.parentNode.removeChild(inst.root);
    markOff(inst); if (CUR === inst) { CUR = null; B.classList.remove('rmap-on'); }
  }
  function markOff(inst) {
    qsa('section.day.rm-on').forEach(function (s) { s.className = s.className.replace(/\s*rm-(on|c\d|s\d)\b/g, ''); });
    if (inst.type === 'ov') { var ov = qs('.overview'); if (ov) { ov.classList.remove('rm-live', 'mapopen'); var f = qs('.mapfold', ov); if (f) f.textContent = '看路线图'; } }
    if (inst.btn) { inst.btn.setAttribute('aria-expanded', 'false'); inst.btn.textContent = inst.btnText || inst.btn.textContent; }
    if (inst.onClose) inst.onClose();
  }
  // 兜底：街道底图不可用 → 纸色底的示意图（总览和每天都一样：自动取景到这一天的站点、站名小标签、比例尺、能拖、不能缩到站点范围之外），提示写在地图里面
  function showLoad(inst) { if (inst.load) { inst.load.textContent = NOTE_LOAD; inst.load.hidden = false; } }
  function hideLoad(inst) { if (inst.load) inst.load.hidden = true; }
  function fallback(inst, why) {
    if (!inst.alive || inst.failed) return; inst.failed = true; inst.why = why; clearTimeout(inst.timer); clearTimeout(inst.tchk); clearTimeout(inst.hard); hideLoad(inst);
    if (inst.view && inst.view.kind === 'ml') { inst.view.destroy(); }
    inst.mapEl.innerHTML = ''; inst.root.classList.add('rm-sch'); inst.view = schView(inst); inst.view.onMove(function () { place(inst); });
    inst.note.textContent = NOTE_OFF; inst.note.hidden = false;
    var at = qs('.rm-at', inst.root); if (at) at.hidden = true;
    draw(inst); fitView(inst, false); settle(inst);
  }
  function startMap(inst) {
    if (!navigator.onLine) return fallback(inst, 'offline');
    if (!glOk()) return fallback(inst, 'nogl');
    showLoad(inst); inst.hard = setTimeout(function () { if (!inst.tiles) fallback(inst, 'slow'); }, HARD_MS);      // 脚本 / 样式一直不回：20 秒也退
    loadML(function (ok) {
      if (!inst.alive || inst.failed) return;
      if (!ok) return fallback(inst, 'ml');
      getStyle(function (st) {
        if (!inst.alive || inst.failed) return;
        if (!st) return fallback(inst, 'style');
        var map;
        try {
          var coop = !inst.fs;
          map = new W.maplibregl.Map({
            container: inst.mapEl, style: JSON.parse(JSON.stringify(st)), center: [105, 34], zoom: 4, minZoom: MINZ, maxZoom: MAXZ,
            attributionControl: false, dragRotate: false, pitchWithRotate: false, touchPitch: false, fadeDuration: 0, preserveDrawingBuffer: true, renderWorldCopies: false,
            cooperativeGestures: coop,
            locale: { 'CooperativeGesturesHandler.MobileHelpText': '用两根手指移动地图', 'CooperativeGesturesHandler.WindowsHelpText': '按住 Ctrl 再滚动来缩放地图', 'CooperativeGesturesHandler.MacHelpText': '按住 ⌘ 再滚动来缩放地图' }
          });
          map.touchZoomRotate.disableRotation();
        } catch (e) { return fallback(inst, 'gl'); }
        inst.map = map; inst.view = mlView(inst, map); inst.tiles = 0; inst.terr = 0;
        map.on('move', function () { place(inst); });
        map.on('data', function (e) { if (e.tile) { inst.tiles++; hideLoad(inst); clearTimeout(inst.hard); } });
        map.on('error', function (e) {
          var er = e && e.error, msg = (er && er.message) || '';
          if (e && (e.tile || /Failed to fetch|NetworkError|Load failed|AJAXError|failed|404|403|5\d\d/i.test(msg))) {
            inst.terr++;      // 瓦片请求失败：1.5 秒内一块成功的都没有 → 退回示意图（视口里只有两三块瓦片时数“几次错”不可靠）
            if (!inst.tchk) inst.tchk = setTimeout(function () { inst.tchk = 0; if (inst.alive && !inst.tiles && inst.terr > 0) fallback(inst, 'tiles'); }, 1500);
          }
        });
        map.on('click', function () { hidePop(inst); });
        map.getCanvas().addEventListener('webglcontextlost', function () { fallback(inst, 'lost'); });
        inst.timer = setTimeout(function () { if (!inst.tiles) fallback(inst, 'slow'); }, SLOW_MS);
        fitView(inst, false); place(inst);
        if (inst.fs) map.cooperativeGestures.disable();
        inst.coopOff = function () { try { map.cooperativeGestures[inst.fs ? 'disable' : 'enable'](); } catch (e) {} };
      });
    });
  }
  function watch(inst) {
    var timer = null;
    inst.mo = new MutationObserver(function (recs) {
      var rel = recs.some(function (r) { var t = r.target.nodeType === 1 ? r.target : r.target.parentNode; return !(t && t.closest && t.closest('.rm')); });
      if (!rel) return; clearTimeout(timer); timer = setTimeout(function () { refresh(inst); }, 160);
    });
    inst.mo.observe(ART, { childList: true, subtree: true, attributes: true, attributeFilter: ['hidden', 'data-ll'] });
  }
  function refresh(inst) {
    if (!inst.alive) return; var days = readDays(), s0 = sig(inst.days), s1 = sig(days);
    var sec0 = inst.sel >= 0 && inst.days[inst.sel] ? inst.days[inst.sel].sec : null;
    if (s0 === s1) return;
    inst.days = days;
    if (inst.type === 'day') { var k = days.map(function (d) { return d.sec; }).indexOf(inst.sec); if (k < 0) { closeInst(inst); return; } if (inst.sel >= 0 && !inst.fs) inst.sel = k; inst.home = k; }
    else if (sec0) { var k2 = days.map(function (d) { return d.sec; }).indexOf(sec0); inst.sel = k2; }
    if (inst.sel >= days.length) inst.sel = days.length - 1;
    var d = curDay(inst); if (d && inst.cur > d.pts.length) inst.cur = 0;
    paintAll(inst); draw(inst); loadGray(inst);
  }
  function scrollSync(inst) {
    var raf = 0;
    inst.onScroll = function () {
      if (raf || inst.fs || Date.now() < (inst.lock || 0)) return;
      raf = W.requestAnimationFrame(function () {
        raf = 0; var d = curDay(inst); if (!d) return; var line = inst.root.getBoundingClientRect().bottom + 24, best = 0, i;
        for (i = 0; i < d.pts.length; i++) { var r = d.pts[i].row.getBoundingClientRect(); if (r.bottom >= line) { best = d.pts[i].n; break; } }
        if (!best && d.pts.length) best = d.pts[d.pts.length - 1].n;
        if (best && best !== inst.cur) setCur(inst, best, { pan: true });
      });
    };
    W.addEventListener('scroll', inst.onScroll, { passive: true });
    inst.onRowClick = function (e) {
      if (inst.fs) return; var li = e.target.closest && e.target.closest('li.r[data-ll]'); if (!li || e.target.closest('a,button,[role=button]')) return;
      var d = curDay(inst); if (!d || !d.sec.contains(li)) return;
      var p = d.pts.filter(function (q) { return q.row === li; })[0]; if (p) setCur(inst, p.n, { pan: true });
    };
    D.addEventListener('click', inst.onRowClick, true);
  }
  function open(type, sec, host) {
    if (CUR) closeInst(CUR);
    var days = readDays(); if (!days.length) return null;
    var inst = { type: type, sec: sec || null, days: days, sel: -1, cur: 0, gray: [], alive: true, fs: false, host: host };
    var k = sec ? days.map(function (d) { return d.sec; }).indexOf(sec) : -1;
    if (type === 'day') { if (k < 0) return null; inst.sel = k; inst.home = k; }
    build(inst); CUR = inst; B.classList.add('rmap-on');      // 地图打开期间底部固定栏（收进行程 / 按天看）让出位置
    host.appendChild(inst.root);
    if (type === 'day') { var nv = qs('.daynav'); host.style.top = (nv && getComputedStyle(nv).position === 'sticky' ? nv.offsetHeight : 0) + 'px'; }
    wire(inst); markOn(inst); paintAll(inst); draw(inst);
    if (type === 'ov') { var ov = qs('.overview'); if (ov) ov.classList.add('rm-live'); }
    if (type === 'day') scrollSync(inst);
    watch(inst);
    startMap(inst);
    if (!inst.view) { inst.view = null; }
    // 没有底图之前先用示意图的位置占位？不画：等 maplibre 就绪（或兜底）再定位，避免先闪一下
    loadGray(inst);
    if (HOST.track) HOST.track('路线地图·' + (type === 'ov' ? '总览' : '每天'));
    return inst;
  }

  // 点开“看路线图”后把地图（到标签条为止）带进第一屏：入口在页面上方，地图在“怎么排”那一块，原来点完看不到变化
  function reveal(inst) {
    setTimeout(function () {
      if (!inst.alive || inst.fs) return;
      var nv = qs('.daynav'), top = nv && getComputedStyle(nv).position === 'sticky' ? nv.offsetHeight : 0, H = W.innerHeight || 700;
      var r = inst.root.getBoundingClientRect(), tb = inst.tabs.getBoundingClientRect().bottom;
      if (r.top < top + 4 || tb > H - 8) jump(Math.max(0, r.top + (W.pageYOffset || 0) - top - 8));
    }, 80);
  }
  W.ZRM = {
    ov: function (on) {
      var ov = qs('.overview'); if (!ov) return;
      if (!on) { if (CUR && CUR.type === 'ov') closeInst(CUR); return; }
      var host = qs('.rm-ovh', ov); if (!host) { host = el('div', 'rm-ovh'); var f = qs('.mapfold', ov); f.parentNode.insertBefore(host, f.nextSibling); }
      var inst = open('ov', null, host); if (inst) { inst.btn = qs('.mapfold', ov); inst.btnText = '看路线图'; inst.onClose = function () { if (inst.btn && !ov.classList.contains('mapopen')) {} }; reveal(inst); }
    },
    toggleDay: function (sec, btn) {
      if (CUR && CUR.type === 'day' && CUR.sec === sec) { var b0 = CUR.btn; closeInst(CUR); return false; }
      var host = qs('.rm-dayh', sec); if (!host) { host = el('div', 'rm-dayh'); var row = qs('.rm-row2', sec); row.parentNode.insertBefore(host, row.nextSibling); }
      var inst = open('day', sec, host); if (!inst) return false;
      inst.btn = btn; inst.btnText = '本日地图 ›'; if (btn) { btn.setAttribute('aria-expanded', 'true'); btn.textContent = '收起本日地图 ‹'; }
      return true;
    },
    nav: function (sec) { var days = readDays(), k = days.map(function (d) { return d.sec; }).indexOf(sec); if (k >= 0) navDay(days[k]); },
    cur: function () { return CUR; },
    segs: function (sec) { var days = readDays(), k = days.map(function (d) { return d.sec; }).indexOf(sec); return k >= 0 ? navSegs(days[k]).map(function (s) { return s.url; }) : []; },
    model: readDays
  };
})();
