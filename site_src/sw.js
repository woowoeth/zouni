// 走你：离线也能看看过的行程
// v2：样式和脚本改成“先走网络、没网才用缓存”（v1 是先用缓存，网站更新后手机上一直是旧样式旧脚本，按钮点不了）
// v3（2026-10-17）：①没存过的页面断网打开，不再悄悄变首页，改成明确的离线页 /offline.html；②第一次安装不再刷新页面（只有“从旧版升级”才刷新一次，
//   因为旧页面跑的是旧脚本）；③manifest 和图标进预存清单；④/where/?q=… 断网时落到缓存的 /where/（查询词还在网址里，页面自己提示“没网，搜不了线路”）
// 2026-10-18（地图 App 化；缓存名仍叫 v3——缓存名只管“换版时清旧缓存”，策略变了不需要清，也就不会让老用户被强制刷新一次）：①地图那几个大文件（maplibre、routemap.js、自托管样式）网址带版本指纹（?v=），内容一变网址就变，所以可以“先用缓存”——第二次点开地图不再等网络；
//   ②自托管的 sprite / 西文字形：先用缓存、后台更新；③OpenFreeMap 的瓦片（跨域，CORS 可读）：先用缓存、后台更新，最多留 500 块（超了删最早的）；
//   瓦片缓存单独一个名字，换版本（V）时不删——瓦片网址里自带版本号，换了自然取新的。
const V = 'zouni-v3';
const TILES = 'zouni-tiles-v1';
const TILE_MAX = 500;
const PRE = ['/', '/where/', '/offline.html', '/manifest.webmanifest', '/img/favicon.svg', '/img/favicon-32.png', '/img/apple-touch-icon.png', '/img/icon-192.png', '/img/icon-512.png'];
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => Promise.all(PRE.map(u => c.add(u).catch(() => {})))).catch(() => {})); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => {
    const upgrade = ks.some(k => k !== V && k !== TILES);            // 之前装过旧版：旧页面用的是旧脚本，换版时刷新一次；第一次安装没有旧版，不刷新
    return Promise.all(ks.filter(k => k !== V && k !== TILES).map(k => caches.delete(k)))
      .then(() => self.clients.claim())
      .then(() => upgrade ? self.clients.matchAll({ type: 'window' }).then(cs => cs.forEach(c => { try { c.navigate(c.url); } catch (err) {} })) : null);
  }));
});
// 瓦片索引（/planet，里面是“当前版本”的瓦片地址）：12 小时内的缓存直接用（后台更新），更老的先走网络——旧版本的瓦片网址 OpenFreeMap 过几天会删，不能一直用旧索引
const tilejson = (e, r) => e.respondWith(caches.open(TILES).then(c => c.match(r).then(m => {
  const net = fetch(r).then(res => { if (res.ok && res.type !== 'opaque') { res.clone().blob().then(b => { const h = new Headers(res.headers); h.set('x-sw-t', String(Date.now())); return c.put(r, new Response(b, { status: 200, headers: h })); }); } return res; });
  const t = m ? +m.headers.get('x-sw-t') : 0;
  if (m && t && Date.now() - t < 12 * 3600e3) { e.waitUntil(net.catch(() => {})); return m; }
  return net.catch(() => m || Response.error());
})));
const fresh = (r) => fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(V).then(c => c.put(r, cp)); } return res; });
// 先用缓存、后台更新（stale-while-revalidate）；cache：缓存名；max：最多留多少条（0 = 不限）
const swr = (e, r, cache, max) => e.respondWith(caches.open(cache).then(c => c.match(r).then(m => {
  const net = fetch(r).then(res => {
    if (res.ok && res.type !== 'opaque') { c.put(r, res.clone()).then(() => { if (max) c.keys().then(ks => { if (ks.length > max) ks.slice(0, ks.length - max).forEach(k => c.delete(k)); }); }); }
    return res;
  });
  if (m) { e.waitUntil(net.catch(() => {})); return m; }
  return net.catch(() => Response.error());      // 页面取消了请求（AbortError）/ 没网：回一个网络错误响应，别让 respondWith 的 Promise 带着未处理的拒绝报到控制台
})));
// 先用缓存，没有再走网络并存下来（网址自带版本指纹的文件）
const first = (e, r) => e.respondWith(caches.open(V).then(c => c.match(r).then(m => m || fetch(r).then(res => {
  if (res.ok) { const p = new URL(r.url).pathname; c.put(r, res.clone()).then(() => c.keys().then(ks => ks.forEach(k => { const ku = new URL(k.url); if (ku.pathname === p && k.url !== r.url) c.delete(k); }))); }      // 同一个文件旧版本的指纹条目顺手清掉
  return res; }).catch(() => Response.error()))));
self.addEventListener('fetch', e => {
  const r = e.request; if (r.method !== 'GET') return; const u = new URL(r.url);
  if (u.origin !== location.origin) {                                                    // 地图瓦片、瓦片索引的字形：OpenFreeMap
    if (u.hostname === 'tiles.openfreemap.org' && r.mode === 'cors') {
      if (/\/planet\/[^/]+\/\d+\/\d+\/\d+\.pbf$|\/natural_earth\/|\/fonts\//.test(u.pathname)) swr(e, r, TILES, TILE_MAX);
      else if (u.pathname === '/planet') tilejson(e, r);
    }
    return;
  }
  const nav = r.mode === 'navigate';
  const html = nav || (r.headers.get('accept') || '').includes('text/html');
  if (!html && u.search.indexOf('v=') >= 0 && /\/assets\/(maplibre\/|routemap\.js|map\/style\.json)/.test(u.pathname)) { first(e, r); return; }      // 地图的大文件：带指纹，先用缓存
  if (/\/assets\/map\/(sprite|fonts)\//.test(u.pathname)) { swr(e, r, V, 0); return; }     // 自托管 sprite / 字形：先用缓存、后台更新
  if (html || /\.(css|js|webmanifest)$/.test(u.pathname)) {          // 网页、样式、脚本：先走网络
    e.respondWith(fresh(r).catch(() => caches.match(r).then(m => m
      || (nav && u.pathname === '/where/' ? caches.match('/where/') : null)         // 带 ?q= 的搜索页：用缓存的搜索页
      || (nav ? caches.match('/offline.html') : undefined))));                      // 没存过的页面：明确的离线页，不静默跳首页
    return;
  }
  e.respondWith(caches.match(r).then(m => m || fresh(r)));          // 图片、字体：先用缓存
});
