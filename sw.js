// 走你：离线也能看看过的行程
// v2：样式和脚本改成“先走网络、没网才用缓存”（v1 是先用缓存，网站更新后手机上一直是旧样式旧脚本，按钮点不了）
// v3（2026-10-17）：①没存过的页面断网打开，不再悄悄变首页，改成明确的离线页 /offline.html；②第一次安装不再刷新页面（只有“从旧版升级”才刷新一次，
//   因为旧页面跑的是旧脚本）；③manifest 和图标进预存清单；④/where/?q=… 断网时落到缓存的 /where/（查询词还在网址里，页面自己提示“没网，搜不了线路”）
const V = 'zouni-v3';
const PRE = ['/', '/where/', '/offline.html', '/manifest.webmanifest', '/img/favicon.svg', '/img/favicon-32.png', '/img/apple-touch-icon.png', '/img/icon-192.png', '/img/icon-512.png'];
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => Promise.all(PRE.map(u => c.add(u).catch(() => {})))).catch(() => {})); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => {
    const upgrade = ks.some(k => k !== V);            // 之前装过旧版：旧页面用的是旧脚本，换版时刷新一次；第一次安装没有旧版，不刷新
    return Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))
      .then(() => self.clients.claim())
      .then(() => upgrade ? self.clients.matchAll({ type: 'window' }).then(cs => cs.forEach(c => { try { c.navigate(c.url); } catch (err) {} })) : null);
  }));
});
const fresh = (r) => fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(V).then(c => c.put(r, cp)); } return res; });
self.addEventListener('fetch', e => {
  const r = e.request; if (r.method !== 'GET') return; const u = new URL(r.url); if (u.origin !== location.origin) return;
  const nav = r.mode === 'navigate';
  const html = nav || (r.headers.get('accept') || '').includes('text/html');
  if (html || /\.(css|js|webmanifest)$/.test(u.pathname)) {          // 网页、样式、脚本：先走网络
    e.respondWith(fresh(r).catch(() => caches.match(r).then(m => m
      || (nav && u.pathname === '/where/' ? caches.match('/where/') : null)         // 带 ?q= 的搜索页：用缓存的搜索页
      || (nav ? caches.match('/offline.html') : undefined))));                      // 没存过的页面：明确的离线页，不静默跳首页
    return;
  }
  e.respondWith(caches.match(r).then(m => m || fresh(r)));          // 图片、字体：先用缓存
});
