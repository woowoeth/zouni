/* 路线地图（2026-10-17）。点开“看路线图 / 本日地图 / 导航这一天”才加载；街道底图 maplibre 再按需加载。
 * 规则和坑：docs/handoff/02-UI规范.md「路线地图」、05-注意事项.md「路线地图」。ES5 only（禁 ?. ?? flatMap .at() 箭头函数 let/const），data_checks 会扫。
 *
 * 结构：一份“模型”（从页面 DOM 读：每天的站、标题、出发/住的片区、车程）→ 一个 Inst（一个地图实例，同一时间只有一个，省 WebGL 上下文）
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
  var NOTE_OFF = '街道地图需要联网';
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
    return { i: i, sec: sec, title: titleOf(sec), pts: pts, sp: pll(sec.getAttribute('data-sp')), ep: pll(sec.getAttribute('data-ep')), stay: stayOf(sec), load: loadOf(sec), nopos: nopos };
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
    var st = { cx: 0, cy: 0, sc: 1, z: 0 }, cb = null;
    return {
      kind: 'sch', st: st,
      project: function (ll) { var w = inst.stage.clientWidth, h = inst.stage.clientHeight; return { x: w / 2 + (ll[1] - st.cx) * st.sc, y: h / 2 - (merc(ll[0]) - st.cy) * st.sc }; },
      fit: function (b) {
        var w = inst.stage.clientWidth || 390, h = inst.stage.clientHeight || 200, pd = padFor(inst);
        var sx = Math.max(b.e - b.w, 0.004), sy = Math.max(merc(b.n) - merc(b.s), 0.004);
        st.sc = Math.min((w - pd.left - pd.right) / sx, (h - pd.top - pd.bottom) / sy); st.cx = (b.w + b.e) / 2; st.cy = (merc(b.n) + merc(b.s)) / 2; st.z = 0; st.sc0 = st.sc;
        if (cb) cb();
      },
      zoom: function () { return st.z; },
      zoomBy: function (d) { st.z = Math.max(-1, Math.min(3, st.z + d)); st.sc = (st.sc0 || st.sc) * Math.pow(2, st.z); if (cb) cb(); },
      panTo: function () {}, resize: function () { if (cb) cb(); },
      atMax: function () { return st.z >= 3; }, atMin: function () { return st.z <= -1; },
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
      '<p class="rm-note" role="status" hidden></p></div>' +
      '<div class="rm-pop" hidden></div><p class="rm-leg"></p><div class="rm-tabs"></div><div class="rm-panel"></div>' +
      '<a class="btn rm-navd" href="#" role="button">导航这一天 ›</a><p class="rm-hint"></p>';
    inst.root = root; inst.stage = qs('.rm-stage', root); inst.mapEl = qs('.rm-map', root); inst.svg = qs('.rm-svg', root); inst.pts = qs('.rm-pts', root);
    inst.pop = qs('.rm-pop', root); inst.note = qs('.rm-note', root); inst.leg = qs('.rm-leg', root); inst.tabs = qs('.rm-tabs', root); inst.panel = qs('.rm-panel', root); inst.navd = qs('.rm-navd', root); inst.hint = qs('.rm-hint', root);
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

  // 叠层：线 + 标记。每次状态变（选天 / 选点 / 重读模型）重建，地图移动只重新定位
  function draw(inst) {
    inst.svg.innerHTML = ''; inst.pts.innerHTML = ''; inst.marks = []; inst.lines = [];
    var n = inst.days.length, sel = inst.sel, NS = 'http://www.w3.org/2000/svg';
    function line(d, cls) {
      var ll = d.pts.map(function (p) { return p.ll; }); if (ll.length < 2) return;
      var c = D.createElementNS(NS, 'polyline'); c.setAttribute('class', 'rm-lc ' + cls);
      var l = D.createElementNS(NS, 'polyline'); l.setAttribute('class', 'rm-ln ' + cls);
      inst.svg.appendChild(c); inst.svg.appendChild(l); inst.lines.push({ ll: ll, els: [c, l] });
    }
    function add(e, ll) { inst.pts.appendChild(e); inst.marks.push({ el: e, ll: ll, badge: e.className.indexOf('rm-db') >= 0 }); }
    inst.days.forEach(function (d, i) {
      var cls = dayCls(i) + (sel >= 0 && sel !== i ? ' rm-dim' : '');
      line(d, cls);
      if (sel === i) return;
      // 其他天 / 全程：小方点 + 每天第一站的天数章
      d.pts.forEach(function (p) { var e = el('i', 'rm-dt ' + dayCls(i) + (sel >= 0 ? ' rm-dim' : '')); add(e, p.ll); });
      if (sel < 0 && d.pts.length) {
        var b = el('button', 'rm-mk rm-db ' + dayCls(i), '<i>' + (i + 1) + '</i>'); b.type = 'button'; b.setAttribute('data-day', i); b.setAttribute('aria-label', '第 ' + (i + 1) + ' 天：' + d.title); add(b, d.pts[0].ll);
      }
    });
    var d = curDay(inst);
    if (d) {
      (inst.gray || []).forEach(function (g, gi) { var e = el('button', 'rm-mk rm-gy', '<i></i>'); e.type = 'button'; e.setAttribute('data-g', gi); e.setAttribute('aria-label', '顺路可去：' + g.c.n); add(e, g.ll); });
      if (d.ep) { var h = el('button', 'rm-mk rm-hm ' + dayCls(inst.sel), '<i>住</i>'); h.type = 'button'; h.setAttribute('data-hm', '1'); h.setAttribute('aria-label', '住 · 约' + (d.stay ? '（' + d.stay + '，片区位置）' : '')); add(h, d.ep); }   // 先画住：和某一站重叠时站在上面
      d.pts.forEach(function (p) {
        var cls = 'rm-mk ' + dayCls(inst.sel) + (p.kind === 'mu' ? ' rm-mu' : '') + (p.kind === 'eat' ? ' rm-eat' : '') + (inst.cur === p.n ? ' rm-cur' : '');
        var b = el('button', cls, '<i>' + p.n + '</i>'); b.type = 'button'; b.setAttribute('data-n', p.n); b.setAttribute('aria-label', p.n + ' ' + p.name); add(b, p.ll);
      });
    }
    place(inst);
  }
  function place(inst) {
    var v = inst.view; if (!v) return;
    inst.marks.forEach(function (m) { var p = v.project(m.ll); m.el.style.transform = 'translate(' + Math.round(p.x) + 'px,' + Math.round(p.y) + 'px)'; });
    inst.lines.forEach(function (l) {
      var s = ''; l.ll.forEach(function (ll) { var q = v.project(ll); s += (Math.round(q.x * 10) / 10) + ',' + (Math.round(q.y * 10) / 10) + ' '; });
      l.els[0].setAttribute('points', s); l.els[1].setAttribute('points', s);
    });
    if (inst.sel < 0) cullBadges(inst);
    zoomBtns(inst);
  }
  function cullBadges(inst) {
    var kept = [];
    inst.marks.forEach(function (m) {
      if (!m.badge) return; var t = m.el.style.transform, mm = /translate\((-?\d+)px,\s*(-?\d+)px\)/.exec(t); if (!mm) return; var x = +mm[1], y = +mm[2], hide = false, i;
      for (i = 0; i < kept.length; i++) if (Math.abs(kept[i][0] - x) < 30 && Math.abs(kept[i][1] - y) < 30) { hide = true; break; }
      m.el.style.visibility = hide ? 'hidden' : ''; if (!hide) kept.push([x, y]);
    });
  }
  function zoomBtns(inst) {
    var v = inst.view; if (!v) return; var zi = qs('.rm-zi', inst.root), zo = qs('.rm-zo', inst.root);
    zi.disabled = v.atMax(); zo.disabled = v.atMin();
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
      if (d.ep) h += '<button type="button" class="rm-row rm-hrow" data-hm="1"><b>住</b><span class="rm-t"><strong>住 · 约' + (d.stay ? ' ' + esc(d.stay) : '') + '</strong><small>片区位置，不是酒店</small></span></button>';
      h += '</div>';
    }
    inst.panel.innerHTML = h; inst.panel.className = 'rm-panel' + (inst.shut ? ' shut' : '');
    var nv = !!d && navSegs(d).length > 0; inst.navd.hidden = !nv; inst.hint.hidden = !nv;
    if (nv) { inst.hint.textContent = navHint(d); var sg = navSegs(d); inst.navd.setAttribute('href', sg.length === 1 ? sg[0].url : '#'); }
  }
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
    var d = curDay(inst); if (!d) return; inst.cur = n;
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
    var b = qs('.rm-fsb', root); b.innerHTML = ICON_XF; b.setAttribute('aria-label', '退出全屏'); b.title = '退出全屏'; b.classList.add('pk-x');
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
    unlockBody(inst); if (inst.addedPk) B.classList.remove('pk-open'); if (inst.coopOff) inst.coopOff();
    if (inst.type === 'day' && inst.sel !== inst.home) { inst.sel = inst.home; inst.cur = 0; inst.gray = []; markOn(inst); paintAll(inst); draw(inst); loadGray(inst); }
    settle(inst); fitView(inst, false);
  }
  function settle(inst) { [0, 120, 400].forEach(function (t) { setTimeout(function () { if (!inst.alive) return; if (inst.view) inst.view.resize(); place(inst); }, t); }); }
  D.addEventListener('fullscreenchange', function () { if (CUR && CUR.fs && CUR.native && !D.fullscreenElement) exitFS(CUR); });
  D.addEventListener('webkitfullscreenchange', function () { if (CUR && CUR.fs && CUR.native && !D.webkitFullscreenElement) exitFS(CUR); });
  W.addEventListener('resize', function () { if (CUR) { fsHeight(CUR); if (CUR.view) { CUR.view.resize(); place(CUR); } } });
  W.addEventListener('orientationchange', function () { setTimeout(function () { if (CUR) { fsHeight(CUR); if (CUR.view) CUR.view.resize(); } }, 300); });

  // ——— 导航这一天 ———
  function gcj(ll) { var f = W.zGcj; return f ? f(ll[0], ll[1]) : ll; }
  function navPts(d) {
    var a = [];
    function push(n, ll) { if (!ll) return; var l = a[a.length - 1]; if (l && kmd(l.ll, ll) < 0.03) return; a.push({ n: n, ll: ll }); }
    push('出发地', d.sp); d.pts.forEach(function (p) { push(p.name, p.ll); }); push(d.stay ? '住处（' + d.stay + '）' : '住处', d.ep);
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
    var a = navPts(d), per = viaMax(), cap = per + 2, segs = navSegs(d).length;
    var who = APP === 'google' ? '谷歌地图手机上一次最多带 ' + per + ' 个途经点' : '高德一次最多带 1 个途经点';
    return who + '，超过 ' + cap + ' 个点（含出发地和住处）会分几段打开' + (segs > 1 ? '；这天一共 ' + a.length + ' 个点，分 ' + segs + ' 段' : '') + '。';
  }
  function goUrl(u) {
    if (!navigator.onLine) { toast('地图需要联网'); return; }
    if (APP !== 'google' && mobileUA() && HOST.open) { HOST.open(u, '高德地图'); return; }      // 手机：callnative=1 唤起高德 App（没装 1.6 秒后提示）
    var w = null; try { w = W.open(u, '_blank', 'noopener'); } catch (e) {}
    if (!w) location.href = u;
  }
  function navDay(d) {
    var segs = navSegs(d); if (!segs.length) { toast('这天没有可导航的位置'); return; }
    if (HOST.track) HOST.track('路线地图·导航这一天');
    if (segs.length === 1) { goUrl(segs[0].url); return; }
    var mask = el('div', 'pk-mask'), sh = el('div', 'pk rm-sheet'); sh.setAttribute('role', 'dialog');
    var h = '<div class="pk-h"><b>导航这一天</b><button type="button" class="pk-x">关上</button></div><p class="xnote">' + esc(navHint(d)) + '路线按驾车排好，到了地图里可以改成步行或公交。</p><div class="xd">';
    segs.forEach(function (s, i) { h += '<a class="rm-seg" href="' + esc(s.url) + '" data-i="' + i + '"><b>第 ' + (i + 1) + ' 段</b><small>' + s.pts.map(function (p) { return esc(p.n); }).join(' → ') + '</small></a>'; });
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
  function wire(inst) {
    var root = inst.root;
    root.addEventListener('click', function (e) {
      var t = e.target, b;
      if ((b = t.closest('.rm-fsb'))) { if (inst.fs) exitFS(inst); else enterFS(inst); return; }
      if (t.closest('.rm-rs')) { fitView(inst, true); return; }
      if (t.closest('.rm-zi')) { inst.view && inst.view.zoomBy(1); if (inst.view && inst.view.kind === 'sch') place(inst); return; }
      if (t.closest('.rm-zo')) { inst.view && inst.view.zoomBy(-1); if (inst.view && inst.view.kind === 'sch') place(inst); return; }
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
        if (b.hasAttribute('data-hm')) { var dh = curDay(inst); if (dh && dh.ep) { inst.view.panTo(dh.ep); showPop(inst, '<span class="rm-pn"><b>住</b>住 · 约' + (dh.stay ? esc(dh.stay) : '') + '<small>片区位置，不是酒店</small></span>'); } return; }
        return;
      }
      if ((b = t.closest('.rm-row'))) {
        if (b.hasAttribute('data-n')) { var nn = +b.getAttribute('data-n'), d3 = curDay(inst), p3 = d3 && d3.pts[nn - 1]; setCur(inst, nn, { pan: true }); if (p3 && inst.view) { inst.view.panTo(p3.ll); popMark(inst, p3); } }
        if (b.hasAttribute('data-hm')) { var d4 = curDay(inst); if (d4 && d4.ep) inst.view.panTo(d4.ep); }
        return;
      }
      if (!t.closest('.rm-pop')) hidePop(inst);
    });
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
    inst.alive = false; clearTimeout(inst.timer); clearTimeout(inst.tchk); if (inst.mo) inst.mo.disconnect();
    if (inst.onScroll) W.removeEventListener('scroll', inst.onScroll);
    if (inst.onRowClick) D.removeEventListener('click', inst.onRowClick, true);
    if (inst.view) inst.view.destroy();
    if (inst.root && inst.root.parentNode) inst.root.parentNode.removeChild(inst.root);
    markOff(inst); if (CUR === inst) CUR = null;
  }
  function markOff(inst) {
    qsa('section.day.rm-on').forEach(function (s) { s.className = s.className.replace(/\s*rm-(on|c\d|s\d)\b/g, ''); });
    if (inst.type === 'ov') { var ov = qs('.overview'); if (ov) { ov.classList.remove('rm-live', 'mapopen'); var f = qs('.mapfold', ov); if (f) f.textContent = '看路线图'; } }
    if (inst.btn) { inst.btn.setAttribute('aria-expanded', 'false'); inst.btn.textContent = inst.btnText || inst.btn.textContent; }
    if (inst.onClose) inst.onClose();
  }
  // 兜底：街道底图不可用
  function fallback(inst, why) {
    if (!inst.alive || inst.failed) return; inst.failed = true; inst.why = why; clearTimeout(inst.timer); clearTimeout(inst.tchk);
    if (inst.view && inst.view.kind === 'ml') { inst.view.destroy(); }
    var st = qs('.hmap'), ov = qs('.overview');
    if (inst.type === 'ov' && st && ov) {
      // 总览：用页面里已有的静态示意图（tools/mapdraw.py 画的），下面写一行说明
      var host = inst.host; closeInst(inst); ov.classList.add('mapopen');
      var f = qs('.mapfold', ov); if (f) f.textContent = '收起路线图';
      if (!qs('.rm-fbn', st)) { var p = el('p', 'rm-fbn', NOTE_OFF); p.setAttribute('role', 'status'); st.appendChild(p); }
      CUR = null; return;
    }
    // 每天的图 / 没有静态图的总览：纸色底的示意图，同一套线和标记
    inst.mapEl.innerHTML = ''; inst.root.classList.add('rm-sch'); inst.view = schView(inst); inst.view.onMove(function () { place(inst); });
    inst.note.textContent = NOTE_OFF; inst.note.hidden = false;
    var at = qs('.rm-at', inst.root); if (at) at.hidden = true;
    draw(inst); fitView(inst, false); settle(inst);
  }
  function startMap(inst) {
    if (!navigator.onLine) return fallback(inst, 'offline');
    if (!glOk()) return fallback(inst, 'nogl');
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
        map.on('data', function (e) { if (e.tile) inst.tiles++; });
        map.on('error', function (e) {
          var er = e && e.error, msg = (er && er.message) || '';
          if (e && (e.tile || /Failed to fetch|NetworkError|Load failed|AJAXError|failed|404|403|5\d\d/i.test(msg))) {
            inst.terr++;      // 瓦片请求失败：1.5 秒内一块成功的都没有 → 退回示意图（视口里只有两三块瓦片时数“几次错”不可靠）
            if (!inst.tchk) inst.tchk = setTimeout(function () { inst.tchk = 0; if (inst.alive && !inst.tiles && inst.terr > 0) fallback(inst, 'tiles'); }, 1500);
          }
        });
        map.on('click', function () { hidePop(inst); });
        map.getCanvas().addEventListener('webglcontextlost', function () { fallback(inst, 'lost'); });
        inst.timer = setTimeout(function () { if (!inst.tiles) fallback(inst, 'slow'); }, 25000);
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
    build(inst); CUR = inst;
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

  W.ZRM = {
    ov: function (on) {
      var ov = qs('.overview'); if (!ov) return;
      if (!on) { if (CUR && CUR.type === 'ov') closeInst(CUR); return; }
      var host = qs('.rm-ovh', ov); if (!host) { host = el('div', 'rm-ovh'); var f = qs('.mapfold', ov); f.parentNode.insertBefore(host, f.nextSibling); }
      var inst = open('ov', null, host); if (inst) { inst.btn = qs('.mapfold', ov); inst.btnText = '看路线图'; inst.onClose = function () { if (inst.btn && !ov.classList.contains('mapopen')) {} }; }
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
