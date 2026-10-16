/* 「顺路加一站 / 换一站」的车程与绕路模型（ES5，不碰 DOM）。
   和 tools/nearby_model.py 逐位一致：tests/nearby_parity.py 用 node 跑这个文件，随机 500 对坐标 × 3 种出行方式，
   差值必须为 0 分钟。改任何数字，两边一起改。
   浏览器里挂 ZNP_MODEL（全局），node 里 module.exports。
   不要用 ?. ?? flatMap .at() 等高版本语法（微信 X5 老内核）。 */
(function (root) {
  'use strict';

  var C = {
    ROUTE_FACTOR: 1.25,
    WALK_KM: 1.3,
    DETOUR_MAX: 30,
    REPLACE_NEAR_MAX: 30,
    F_MIN: 0.8,
    F_MAX: 2.0,
    SHOW_STEP: 5,
    MAX_NONMEAL: 4,
    END_LIMIT: 22 * 60 + 30,
    SPAN_LIMIT: 10 * 60,
    SAME_SPOT_KM: 0.25,
    BESIDE_KM: 0.6,
    REACH_KM: 35,
    LIST_MAX: 5,
    BBOX_PAD: 0.35,
    GRID: 3,
    W_HAS_SENTENCE: 6,
    W_POP_CAP: 6,
    W_POP_K: 2,
    W_SAME_KIND: 4,
    F_SLOW: 1.4,
    W_SLOW: 3,
    W_APPROX: 8,
    APPROX_DELTA: 20
  };
  var KIND_WORDS = ['寺', '馆', '园', '街', '塔', '山', '湖'];
  var BIG_CITIES = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安', '厦门', '苏州', '青岛', '天津', '长沙', '香港', '澳门', '佐敦', '郑州', '沈阳', '大连', '哈尔滨', '昆明', '南宁', '福州', '济南', '合肥', '南昌', '贵阳', '兰州', '乌鲁木齐', '呼和浩特', '石家庄', '太原', '宁波', '无锡', '扬州', '洛阳', '开封', '泉州', '三亚', '海口', '桂林', '拉萨'];

  /* Python 的 round() 是银行家舍入（x.5 取偶）；Math.round 是 x.5 进位。两边必须一样 */
  function pyRound(x) {
    var f = Math.floor(x);
    var d = x - f;
    if (d < 0.5) { return f; }
    if (d > 0.5) { return f + 1; }
    return (f % 2 === 0) ? f : f + 1;
  }

  function r5(x) { return 5 * pyRound(x / 5.0); }

  function km(a, b) {
    var r = Math.PI / 180;
    var dl = (b[1] - a[1]) * r;
    var p1 = a[0] * r;
    var p2 = b[0] * r;
    var h = Math.pow(Math.sin((p2 - p1) / 2), 2) + Math.cos(p1) * Math.cos(p2) * Math.pow(Math.sin(dl / 2), 2);
    return 2 * 6371 * Math.asin(Math.sqrt(h));
  }

  function inList(list, x) {
    var i;
    for (i = 0; i < list.length; i++) { if (list[i] === x) { return true; } }
    return false;
  }

  function modeOfDay(drive, domestic, city) {
    if (drive) { return 'drive'; }
    if (domestic && !inList(BIG_CITIES, city)) { return 'rural'; }
    return 'city';
  }

  /* 返回 [怎么走, 分钟, 公里(或 null)]，和 Python 的 leg() 同一张表 */
  function leg(a, b, mode) {
    var d;
    if (!a || !b) { return ['打车', 20, null]; }
    d = km(a, b) * C.ROUTE_FACTOR;
    if (d < C.WALK_KM) { return ['步行', Math.max(5, r5(d / 4.5 * 60)), null]; }
    if (mode === 'drive') {
      if (d < 20) { return ['开车', Math.max(10, r5(d / 30 * 60 + 5)), pyRound(d)]; }
      return ['自驾约', r5(d / 70 * 60 + 10), pyRound(d)];
    }
    if (mode === 'rural' && d >= 12) { return ['包车约', r5(d / 50 * 60 + 10), pyRound(d)]; }
    if (d < 20) { return ['打车', Math.max(10, r5(d / 25 * 60 + 8)), pyRound(d)]; }
    if (d < 60) { return ['打车约', r5(d / 55 * 60 + 10), pyRound(d)]; }
    return ['包车约', r5(d / 65 * 60 + 10), pyRound(d)];
  }

  function t(a, b, mode) { return leg(a, b, mode)[1]; }

  function clamp(x, lo, hi) { return x < lo ? lo : (x > hi ? hi : x); }

  function factor(a, b, t0, mode) {
    if (!t0) { return 1.0; }
    return clamp(t0 / t(a, b, mode), C.F_MIN, C.F_MAX);
  }

  function show5(x) { return r5(x); }

  function detourInsert(A, B, X, t0AB, mode) {
    var f, base, v;
    if (B === null || B === undefined) { return t(A, X, mode); }
    f = factor(A, B, t0AB, mode);
    base = t0AB ? t0AB : t(A, B, mode);
    v = f * (t(A, X, mode) + t(X, B, mode)) - base;
    return v > 0 ? v : 0.0;
  }

  function detourReplace(A, S, C2, X, t0AS, t0SC, mode) {
    var d = 0.0;
    var f1, f2;
    if (A !== null && A !== undefined) {
      f1 = factor(A, S, t0AS, mode);
      d += f1 * t(A, X, mode) - (t0AS ? t0AS : t(A, S, mode));
    }
    if (C2 !== null && C2 !== undefined) {
      f2 = factor(S, C2, t0SC, mode);
      d += f2 * t(X, C2, mode) - (t0SC ? t0SC : t(S, C2, mode));
    }
    return d;
  }

  function replaceNear(S, X, mode) { return t(S, X, mode) <= C.REPLACE_NEAR_MAX; }
  function detourOk(delta) { return delta <= C.DETOUR_MAX; }

  /* rows: [{s, e, k}]，k = see | fun | eat | dep | stay */
  function dayBudgetOk(rows, inserting) {
    var n = 0;
    var first = null;
    var last = 0;
    var i, r, e, span, reason;
    for (i = 0; i < rows.length; i++) {
      r = rows[i];
      if (r.k === 'see' || r.k === 'fun') { n += 1; }
      e = (r.e === undefined || r.e === null) ? r.s : r.e;
      if (first === null || r.s < first) { first = r.s; }
      if (e > last) { last = e; }
    }
    if (first === null) { first = 0; }
    span = last - first;
    reason = '';
    if (inserting && n > C.MAX_NONMEAL) { reason = 'full'; }
    else if (last > C.END_LIMIT) { reason = 'late'; }
    else if (span > C.SPAN_LIMIT) { reason = 'long'; }
    return { ok: reason === '', reason: reason, n: n, first: first, last: last, span: span };
  }

  function sameSpot(cand, refs) {
    var best = null;
    var i, d;
    for (i = 0; i < refs.length; i++) {
      if (!refs[i]) { continue; }
      d = km(cand, refs[i]);
      if (best === null || d < best) { best = d; }
    }
    if (best === null) { return ''; }
    if (best < C.SAME_SPOT_KM) { return 'same'; }
    if (best < C.BESIDE_KM) { return 'beside'; }
    return '';
  }

  function inReach(cand, refs) {
    var i;
    for (i = 0; i < refs.length; i++) {
      if (refs[i] && km(cand, refs[i]) <= C.REACH_KM) { return true; }
    }
    return false;
  }

  var HRS = /(\d{1,2}):(\d{2})\s*[–—~\-至]\s*(\d{1,2}):(\d{2})/;

  function parseHours(h) {
    var m = HRS.exec(h || '');
    if (!m) { return null; }
    return [parseInt(m[1], 10) * 60 + parseInt(m[2], 10), parseInt(m[3], 10) * 60 + parseInt(m[4], 10)];
  }

  function hoursOk(arrive, dur, h) {
    var p = parseHours(h);
    if (!p) { return true; }
    return arrive + Math.min(dur, 60) <= p[1];
  }

  function closedOn(cl, weekday) { return cl !== null && cl !== undefined && cl === weekday; }

  function kindWords(s) {
    var out = [];
    var i;
    s = s || '';
    for (i = 0; i < KIND_WORDS.length; i++) {
      if (s.indexOf(KIND_WORDS[i]) >= 0) { out.push(KIND_WORDS[i]); }
    }
    return out;
  }

  function sameKind(candT, candN, refT, refN, dayTitle) {
    var ck, rk, i;
    if (candT && refT && candT === refT) { return true; }
    ck = kindWords(candN);
    if (!ck.length) { return false; }
    rk = kindWords(refN).concat(kindWords(dayTitle));
    for (i = 0; i < ck.length; i++) { if (inList(rk, ck[i])) { return true; } }
    return false;
  }

  function rankScore(c) {
    var dp = c.delta > 0 ? c.delta : 0.0;
    var s = -dp;
    if (c.has_s) { s += C.W_HAS_SENTENCE; }
    s += Math.min(C.W_POP_CAP, C.W_POP_K * Math.log(1 + (c.pop || 0)));
    if (c.same) { s += C.W_SAME_KIND; }
    if ((c.f || 1.0) > C.F_SLOW) { s -= C.W_SLOW; }
    if (c.approx && c.delta >= C.APPROX_DELTA) { s -= C.W_APPROX; }
    return s;
  }

  function copyObj(c) {
    var o = {};
    var k;
    for (k in c) { if (Object.prototype.hasOwnProperty.call(c, k)) { o[k] = c[k]; } }
    return o;
  }

  function rank(cands, limit) {
    var out = [];
    var i, d;
    if (limit === undefined || limit === null) { limit = C.LIST_MAX; }
    for (i = 0; i < cands.length; i++) {
      d = copyObj(cands[i]);
      d.score = rankScore(cands[i]);
      out.push(d);
    }
    out.sort(function (a, b) {
      var ia, ib;
      if (a.score !== b.score) { return b.score - a.score; }
      if (a.delta !== b.delta) { return a.delta - b.delta; }
      ia = String(a.id === undefined ? '' : a.id);
      ib = String(b.id === undefined ? '' : b.id);
      return ia < ib ? -1 : (ia > ib ? 1 : 0);
    });
    return out.slice(0, limit);
  }

  function cell(lat, lng) {
    return [Math.floor((lat + 90) / C.GRID), Math.floor((lng + 180) / C.GRID)];
  }

  function cellKey(lat, lng) {
    var c = cell(lat, lng);
    return c[0] + '_' + c[1];
  }

  /* bbox = [minLat, minLng, maxLat, maxLng] → ['纬格_经格', …]，外扩 ±0.35°。客户端取片函数用它 */
  function shardsFor(bbox) {
    var lo = cell(bbox[0] - C.BBOX_PAD, bbox[1] - C.BBOX_PAD);
    var hi = cell(bbox[2] + C.BBOX_PAD, bbox[3] + C.BBOX_PAD);
    var out = [];
    var a, b;
    for (a = lo[0]; a <= hi[0]; a++) {
      for (b = lo[1]; b <= hi[1]; b++) { out.push(a + '_' + b); }
    }
    return out;
  }

  var API = {
    C: C, KIND_WORDS: KIND_WORDS, BIG_CITIES: BIG_CITIES,
    pyRound: pyRound, r5: r5, km: km, modeOfDay: modeOfDay, leg: leg, t: t, factor: factor, show5: show5,
    detourInsert: detourInsert, detourReplace: detourReplace, replaceNear: replaceNear, detourOk: detourOk,
    dayBudgetOk: dayBudgetOk, sameSpot: sameSpot, inReach: inReach, parseHours: parseHours, hoursOk: hoursOk,
    closedOn: closedOn, kindWords: kindWords, sameKind: sameKind, rankScore: rankScore, rank: rank,
    cell: cell, cellKey: cellKey, shardsFor: shardsFor
  };

  if (typeof module !== 'undefined' && module.exports) { module.exports = API; }
  else { root.ZNP_MODEL = API; }
}(this));
