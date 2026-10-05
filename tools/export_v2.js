// 用法：node tools/export_v2.js <引擎 html> <输出目录>
const p = require('/tmp/node_modules/puppeteer');
const fs = require('fs');
const path = require('path');
const SRC = process.argv[2] || '/mnt/user-data/outputs/zouni-xj-10d.html';
const OUT = process.argv[3] || '/home/claude/zouni-project/data/routes';

// 城市级坐标（约数，够算日出日落到分钟级）
const LL = {
  '拉萨': [29.65, 91.13], '日喀则': [29.27, 88.88], '纳木错': [30.77, 90.85], '羊卓雍错': [28.95, 90.6], '林芝': [29.65, 94.36],
  '喀什': [39.47, 75.99], '塔县': [37.77, 75.23], '塔什库尔干': [37.77, 75.23], '乌鲁木齐': [43.83, 87.62], '喀纳斯': [48.7, 87.0], '禾木': [48.57, 87.43],
  '伊宁': [43.92, 81.32], '赛里木湖': [44.6, 81.2], '北京': [39.9, 116.4], '上海': [31.23, 121.47], '杭州': [30.27, 120.15], '苏州': [31.3, 120.6],
  '南京': [32.06, 118.79], '西安': [34.34, 108.94], '成都': [30.66, 104.06], '重庆': [29.56, 106.55], '武汉': [30.59, 114.3], '长沙': [28.23, 112.94],
  '厦门': [24.48, 118.09], '青岛': [36.07, 120.38], '桂林': [25.27, 110.29], '阳朔': [24.78, 110.49], '黄山': [30.13, 118.17], '九寨沟': [33.26, 103.92],
  '稻城': [29.04, 100.3], '亚丁': [28.4, 100.35], '额济纳': [41.95, 101.07], '香港': [22.3, 114.17], '泰安': [36.2, 117.09], '曲阜': [35.6, 116.99],
  '都江堰': [31.0, 103.62], '元阳': [23.22, 102.83], '张家界': [29.12, 110.48], '大理': [25.6, 100.27], '丽江': [26.87, 100.23], '西宁': [36.62, 101.78],
  '敦煌': [40.14, 94.66], '张掖': [38.93, 100.45], '海拉尔': [49.21, 119.74], '哈尔滨': [45.8, 126.53], '三亚': [18.25, 109.51], '昆明': [25.04, 102.71]
};
const GEO = JSON.parse(fs.readFileSync(path.join(__dirname, '../data/geo/places.resolved.json'), 'utf8'));
const hm = (m) => (m == null ? null : String(Math.floor(m / 60) % 24).padStart(2, '0') + ':' + String(Math.round(m % 60)).padStart(2, '0'));

(async () => {
  const b = await p.launch({ args: ['--no-sandbox', '--disable-dev-shm-usage'] });
  const pg = await b.newPage();
  await pg.goto('file://' + SRC, { waitUntil: 'networkidle0' });
  await new Promise((r) => setTimeout(r, 500));
  const ids = await pg.evaluate(() => Object.keys(ROUTES));
  fs.mkdirSync(OUT, { recursive: true });
  const cov = { routes: 0, days: 0, dep: 0, see: 0, eatTodo: 0, stayCityNights: 0, storyDraft: 0, altKnown: 0, llKnown: 0, unknownPlaces: new Set() };
  for (const id of ids) {
    const raw = await pg.evaluate((id) => {
      setLang('zh');
      const R = ROUTES[id];
      curDays = R.days.length; uiLoadRoute(id); tastes.clear(); applyDraw();
      const map = R.map || {}, nodes = (map.nodes || []).map((n) => n.n), tonight = map.tonight || [];
      return {
        id, fam: R.fam, title: R.title || R.name, dest: R.dest || '', why: R.why || '', weather: R.weather || '',
        seasons: (R.seasons || []).map((s) => ({ name: s.name, why: s.why || '' })),
        transport: R.transport || null, todos: (R.todos ? R.todos() : []).map((t) => t.text),
        days: DAYS.map((d, i) => {
          const rs = resolved[i] || {};
          return {
            tab: d.tab, name: d.name, sub: d.sub || '', start: d.start, drive: d.drive || '',
            pre: d.pre || null, post: d.post || null,
            sched: (rs.sched || []).map((x) => ({ name: x.s.name, arr: x.arr, dur: x.dur, cost: x.s.cost || 0, cat: x.s.cat || '', indoor: !!x.s.indoor, era: x.s.era || '', vibe: x.s.vibe || '', must: x.s.must || [] })),
            conns: (rs.conns || []).map((c) => (c ? { mode: c.mode, min: c.min, km: c.km, conn: c.conn } : null)),
            lodge: LODGES[i] ? (LODGES[i].opts ? LODGES[i].opts.map((o) => ({ city: o.city, price: o.price, why: o.why })) : [{ city: LODGES[i].city, price: LODGES[i].price, why: LODGES[i].why }]) : null,
            place: tonight[i] != null && tonight[i] >= 0 ? nodes[tonight[i]] : (nodes[0] || '')
          };
        })
      };
    }, id);

    const days = raw.days.map((d, i) => {
      const isLast = i === raw.days.length - 1;
      const tl = [];
      let t = d.start;
      if (d.pre && d.pre.min) tl.push({ t: hm(t), type: 'dep', to: d.sched[0] ? d.sched[0].name : '', mode: d.pre.mode, min: d.pre.min, km: d.pre.km || null, via: d.pre.via || null });
      d.sched.forEach((s, k) => {
        if (k > 0 && d.conns[k - 1]) { const c = d.conns[k - 1]; tl.push({ t: hm(s.arr - (c.min || 0)), type: 'dep', to: s.name, mode: c.mode, min: c.min, km: c.km || null }); }
        tl.push({ t: hm(s.arr), type: 'see', name: s.name, dur: s.dur, cost: s.cost, ticket: s.cat, indoor: s.indoor, lock: null });
      });
      const last = d.sched.length ? d.sched[d.sched.length - 1] : null;
      if (d.post && d.post.min && last) tl.push({ t: hm(last.arr + last.dur), type: 'dep', to: isLast ? '回程' : '住处', mode: d.post.mode, min: d.post.min, km: d.post.km || null });
      // 午饭、晚饭槽位：放在空档里，菜和店待补
      const busy = d.sched.map((s) => [s.arr, s.arr + s.dur]);
      const free = (a, z) => !busy.some(([x, y]) => x < z && y > a);
      const lunch = [690, 720, 750, 780].find((m) => free(m, m + 45));
      tl.push({ t: hm(lunch != null ? lunch : 750), type: 'eat', slot: '午饭', dish: '待补', place: '待补', price: null });
      const endDay = last ? last.arr + last.dur + (d.post && d.post.min ? d.post.min : 0) : 1110;
      if (!(isLast && endDay < 17 * 60)) tl.push({ t: hm(Math.max(1110, Math.ceil(endDay / 15) * 15)), type: 'eat', slot: '晚饭', dish: '待补', place: '待补', price: null });
      tl.sort((a, b) => (a.t < b.t ? -1 : a.t > b.t ? 1 : 0));
      if (!isLast) tl.push({ t: '晚上', type: 'stay', city: d.lodge ? d.lodge[0].city : null, name: d.lodge ? d.lodge[0].city : null, engine_price: d.lodge ? d.lodge[0].price : null });
      const altM = (d.sched.map((s) => (s.era.match(/海拔\s*([\d,]+)\s*m/) || [])[1]).find(Boolean) || '').replace(/,/g, '');
      const pk = (d.place || '').split(/\s*·\s*/)[0].replace(/(住这|连住|返回)$/, '').trim();
      const g = GEO[pk] || null;
      const ll = g ? [g.lat, g.lng] : (LL[pk] || null);
      if (!ll && d.place) cov.unknownPlaces.add(d.place);
      cov.days++; cov.dep += tl.filter((x) => x.type === 'dep').length; cov.see += tl.filter((x) => x.type === 'see').length;
      cov.eatTodo += 2; if (d.lodge) cov.stayCityNights++; if (altM || (g && g.elev != null)) cov.altKnown++; if (g && g.clim) cov.tempKnown = (cov.tempKnown || 0) + 1; if (((altM ? +altM : (g ? g.elev : 0)) || 0) >= 3000) cov.highDays = (cov.highDays || 0) + 1; if (ll) cov.llKnown++;
      const draft = d.sched.map((s) => s.vibe).filter(Boolean);
      if (draft.length) cov.storyDraft++;
      return {
        n: i + 1, title: d.name, sub: d.sub, place: d.place || null, lat: ll ? ll[0] : null, lng: ll ? ll[1] : null,
        facts: { depart: tl.find((x) => x.type === 'dep') ? tl.find((x) => x.type === 'dep').t : hm(d.start), drive: d.drive || null, altitude_m: altM ? +altM : (g && g.elev != null ? g.elev : null), high_altitude: (altM ? +altM : (g ? g.elev : 0)) >= 3000, temp_by_month: g && g.clim ? g.clim : null },
        timeline: tl,
        stay: { city: d.lodge ? d.lodge[0].city : null, engine: d.lodge, tiers: { luxury: null, upscale: null, budget: null }, default: 'luxury' },
        story: { text: draft.join(' '), manners: d.sched.flatMap((s) => (s.must || []).slice(1)).filter(Boolean), verified: false },
        experiences: [], notes: d.pre && d.pre.via ? [d.pre.via] : []
      };
    });
    const rec = {
      schema: 'zouni.route.v2', id: raw.id, fam: raw.fam, title: raw.title, dest: raw.dest, days_count: days.length,
      seasons: raw.seasons, transport: raw.transport, prep: raw.todos, weather_note: raw.weather, days,
      status: { timeline: 'engine', departures: 'engine', meals: 'todo', stay_tiers: 'todo', story: 'draft', experiences: 'todo', temp: days.every((d) => d.facts.temp_by_month) ? 'computed' : 'partial', light: days.every((d) => d.lat != null) ? 'computable' : 'partial' }
    };
    fs.writeFileSync(path.join(OUT, id + '.json'), JSON.stringify(rec, null, 1));
    cov.routes++;
  }
  cov.unknownPlaces = [...cov.unknownPlaces];
  fs.writeFileSync(path.join(OUT, '_coverage.json'), JSON.stringify(cov, null, 1));
  console.log(JSON.stringify({ tempKnown: cov.tempKnown, highDays: cov.highDays, routes: cov.routes, days: cov.days, dep: cov.dep, see: cov.see, eatTodo: cov.eatTodo, stayCityNights: cov.stayCityNights, storyDraft: cov.storyDraft, altKnown: cov.altKnown, llKnown: cov.llKnown, unknownPlaces: cov.unknownPlaces.length }));
  await b.close();
})().catch((e) => { console.error('ERR', e.message); process.exit(1); });
