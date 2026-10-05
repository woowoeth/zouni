// 走你：离线也能看看过的行程
// v2：样式和脚本改成“先走网络、没网才用缓存”（v1 是先用缓存，网站更新后手机上一直是旧样式旧脚本，按钮点不了）
const V = 'zouni-v2';
self.addEventListener('install', e => { self.skipWaiting(); e.waitUntil(caches.open(V).then(c => c.addAll(['/', '/where/', '/img/favicon.svg']).catch(() => {}))); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k))))
    .then(() => self.clients.claim())
    .then(() => self.clients.matchAll({ type: 'window' }))
    .then(cs => cs.forEach(c => { try { c.navigate(c.url); } catch (err) {} })));   // 旧页面用的是旧脚本，换版时刷新一次
});
const fresh = (r) => fetch(r).then(res => { if (res.ok) { const cp = res.clone(); caches.open(V).then(c => c.put(r, cp)); } return res; });
self.addEventListener('fetch', e => {
  const r = e.request; if (r.method !== 'GET') return; const u = new URL(r.url); if (u.origin !== location.origin) return;
  const html = r.mode === 'navigate' || (r.headers.get('accept') || '').includes('text/html');
  if (html || /\.(css|js|webmanifest)$/.test(u.pathname)) {          // 网页、样式、脚本：先走网络
    e.respondWith(fresh(r).catch(() => caches.match(r).then(m => m || (html ? caches.match('/') : undefined))));
    return;
  }
  e.respondWith(caches.match(r).then(m => m || fresh(r)));          // 图片、字体：先用缓存
});
