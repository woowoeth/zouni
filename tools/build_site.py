# 走你 · 静态网站生成器
# 用法：python3 tools/build_site.py <输出目录>
# 输入：build/routes.js、build/catalog.js、data/catalog/cn_quality.json、海报 SVG
# 输出：首页、去哪儿、56 个目的地页、全部行程页、sitemap.xml、robots.txt、llms.txt、404.html、CNAME
import json, re, os, sys, shutil, html, datetime, glob, urllib.parse

OUT = sys.argv[1] if len(sys.argv) > 1 else 'site'
BASE = 'https://zouni.app'
TODAY = datetime.date.today()
SITE = '走你'
POSTER_SRC = os.environ.get('POSTER_SRC') or ('assets/blob' if os.path.isdir('assets/blob') else '/tmp/dc-test/_blob')
E = lambda s: html.escape(str(s if s is not None else ''), quote=True)


def jsvar(path, name):
    s = open(path, encoding='utf-8').read()
    m = re.search(r'window\.' + name + r'=(.*?);\n', s, re.S)
    return json.loads(m.group(1))


ROUTES = jsvar('build/routes.js', 'ZOUNI_ROUTES'); ORDER = jsvar('build/routes.js', 'ZOUNI_ORDER')
CAT = jsvar('build/catalog.js', 'ZOUNI_CATALOG'); ATLAS = jsvar('build/catalog.js', 'ZOUNI_ATLAS')
DEST = {d['id']: d for d in CAT['destinations']}
TRIPS = CAT['trips']
QUAL = json.load(open('data/catalog/cn_quality.json'))['items']
NICHE = json.load(open('data/catalog/niche.json'))['items']
NICHE_BY_DEST = {}
for _n in NICHE: NICHE_BY_DEST.setdefault(_n['dest'], []).append(_n)
STATUS = {'open': '可以去', 'restricted': '有条件', 'paused': '暂停开放', 'check': '出发前查'}
TRIP_OF_ROUTE = {}
for t in TRIPS:
    m = re.match(r'Route\.dc\.html#(\w+)', t.get('page') or '')
    if m: TRIP_OF_ROUTE[m.group(1)] = t
ROUTE_IDS = [r for r in ORDER if r in ROUTES]
DEST_ROUTES = {}
for rid in ROUTE_IDS:
    t = TRIP_OF_ROUTE.get(rid)
    if t: DEST_ROUTES.setdefault(t['dest'], []).append(rid)
QUAL_BY_PROV = {}
for q in QUAL: QUAL_BY_PROV.setdefault(q['prov'], []).append(q)
REGION_ORDER = ATLAS['regions']['domestic'] + ATLAS['regions']['asia']
ORIGINS = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '重庆', '武汉', '西安', '香港']

ICON_PIN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0119 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>'
ICON_DP = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linejoin="round" aria-hidden="true"><path d="M4 4.5h16v11.5H10l-5 4v-4H4z"/><path d="M12 7.4l1.1 2.3 2.5.36-1.8 1.76.42 2.48L12 13.1l-2.22 1.2.42-2.48-1.8-1.76 2.5-.36z" fill="currentColor" stroke="none"/></svg>'


def mapurl(kw, city, app):
    if app == 'google': return 'https://www.google.com/maps/search/?api=1&query=' + urllib.parse.quote(kw)
    return 'https://uri.amap.com/search?keyword=' + urllib.parse.quote(kw) + ('&city=' + urllib.parse.quote(city) if city else '')


def dpurl(kw, city=''):
    return 'https://www.dianping.com/ai-search?keyword=' + urllib.parse.quote((city + ' ' if city else '') + kw)


def icons(kw, city, app, dp=None):
    if not kw: return ''
    return (f'<a class="ic" href="{E(mapurl(kw, city, app))}" rel="nofollow noopener" target="_blank" aria-label="地图上看 {E(kw)}">{ICON_PIN}</a>'
            f'<a class="ic" href="{E(dp or dpurl(kw, city))}" rel="nofollow noopener" target="_blank" aria-label="大众点评上看 {E(kw)}">{ICON_DP}</a>')


def md(s):  # "10-25" → "10 月 25 日"
    m, d = s.split('-'); return f'{int(m)} 月 {int(d)} 日'


def season_text(t):
    if not t: return ''
    if t.get('anytime'): return '一年四季都能去'
    s = t.get('season') or {}
    b = s.get('best')
    return f'最好在 {md(b[0])}到{md(b[1])}' if b else ''


def page(path, title, desc, body, jsonld=(), image=None, crumbs=()):
    url = BASE + path
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    if crumbs:
        ld += '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': BASE + p} for i, (n, p) in enumerate(crumbs)]}, ensure_ascii=False) + '</script>'
    nav = ''.join(f'<a href="{E(p)}">{E(n)}</a><span>›</span>' for n, p in crumbs[:-1]) + (f'<b>{E(crumbs[-1][0])}</b>' if crumbs else '')
    og = image or '/img/og.png'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{E(url)}">
<meta property="og:type" content="website"><meta property="og:site_name" content="{SITE}"><meta property="og:locale" content="zh_CN">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(url)}"><meta property="og:image" content="{E(BASE + og)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#f4f2ec">
<link rel="icon" href="/img/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/site.css">
{ld}
</head>
<body>
<header class="top"><a class="brand" href="/">走你</a><nav><a href="/where/">去哪儿</a></nav></header>
{('<nav class="crumbs" aria-label="位置">' + nav + '</nav>') if crumbs else ''}
<main>
{body}
</main>
<footer class="foot"><p>走你：按季节挑地方，按天排好每一站。</p><p><a href="/where/">全部目的地</a><a href="/sitemap.xml">网站地图</a></p></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
'''


def write(path, s):
    p = os.path.join(OUT, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.strip('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)


def hero(r):
    img = (r.get('img') or '').replace('/_blob/', '')
    if img and os.path.exists(os.path.join(POSTER_SRC, img + '.svg')):
        return f'<div class="hero"><img src="/img/{E(img)}.svg" alt="{E(r.get("alt") or r["title"])}" width="390" height="380"><div class="hero-t"><span class="kick">{E((r.get("kicker") or "").replace(" · ", "，"))}</span><h1>{E(r["title"])}</h1></div></div>'
    mark = re.sub(r'\s*\d+\s*天$', '', r.get('label') or '')
    bg = ['#3a302a', '#2e3a3f', '#3b3527', '#2f3830'][len(r.get('id') or '') % 4]
    return f'<div class="hero text" style="background:{bg}"><span class="mark" aria-hidden="true">{E(mark)}</span><div class="hero-t"><span class="kick">{E((r.get("kicker") or "").replace(" · ", "，"))}</span><h1>{E(r["title"])}</h1></div></div>'


def hrs(m):
    if not m: return ''
    v = round(m / 30) / 2
    return (f'{v:.1f}' if v % 1 else f'{int(v)}') + ' 小时'


def row_html(w, city, app):
    t = w['type']
    if t == 'dep':
        to = w.get('to') or ''; how = (w.get('how') or '').replace(' · ', '，')
        txt = ('回住处' + ('，' + how if how and how not in ('打车或步行', '回去歇一下') else ('歇一下' if how == '回去歇一下' else ''))) if to == '住处' else \
              ('去吃饭' if to == '吃晚饭' else (how or '前往') + ('，到' + to if to and to != '回程' else '')) if to != '回程' else '去车站或机场'
        return f'<li class="r dep"><span class="cn">{E(w["t"])} 出发 · {E(txt)}</span></li>' if to == '回程' else f'<li class="r dep"><span class="cn">{E(txt)}</span></li>'
    if t == 'eat':
        main = f'{E(w.get("slot"))}：{E(w.get("dish"))}'
        place = w.get('place') if w.get('place') not in ('随意', '住的地方附近', '附近', '车站或机场里吃', '沿途', '路上') else ''
        sub = '，'.join(x for x in [E(place), E(w.get('d')), E(w.get('kb'))] if x)
        kw = w.get('poi') or place
    elif t == 'stay':
        main = E(w.get('name')); sub = E(w.get('d')); kw = w.get('poi')
    else:
        main = E(w.get('name')); sub = '，'.join(x for x in [E(w.get('d')), E(w.get('kb'))] if x); kw = w.get('poi')
    ic = icons(kw, city, app, w.get('dp')) if kw else ''
    return f'<li class="r {t}"><time>{E(w["t"])}</time><span class="dot"></span><div class="rb"><p class="m">{main}</p>{f"<p class=s>{sub}</p>" if sub else ""}</div><span class="ics">{ic}</span></li>'


def trip_page(rid):
    r = ROUTES[rid]; t = TRIP_OF_ROUTE.get(rid) or {}; d0 = DEST.get(t.get('dest'), {})
    app = r.get('navApp') or 'amap'; n = len(r['days'])
    price = r.get('price') or ''
    cost = r.get('cost')
    glance = (f'<div class="glance"><div><b>{n}<small> 天</small></b><small>{E(season_text(t))}</small></div><div><b>{E(r.get("driveTop"))}</b><small>{E(r.get("driveSub"))}</small></div>'
              f'<div><b class="price" data-cost=\'{E(json.dumps(cost)) if cost and cost.get("trans") else ""}\'>{E(price)}</b><small>{("每人，含往返，参考价" if price.startswith("约") else "每人，含往返") if "¥" in price else "价格另算"}</small></div></div>')
    if cost and cost.get('trans'):
        glance += '<div class="ppl" hidden><span>几个人去</span><button type="button" data-d="-1" aria-label="少一个人">−</button><b>2 人</b><button type="button" data-d="1" aria-label="多一个人">+</button></div>'
    prep = ''.join(f'<li><label><input type="checkbox" data-k="{i}"><span>{E(x)}</span></label></li>' for i, x in enumerate(r.get('prep') or [])) + ''.join(f'<li class="fit">{E(x)}</li>' for x in r.get('fit') or [])
    over = ''.join(f'<li><a href="#d{i + 1}"><b>{i + 1}</b><span>{E(d["title"])}</span><small>{"返程" if i == n - 1 else "住" + E(d.get("navCity") or d.get("city"))}</small></a></li>' for i, d in enumerate(r['days']))
    days = []
    sights = []
    for i, d in enumerate(r['days']):
        rows = list(d['rows'])
        if i < n - 1 and (d.get('stayName') or d.get('stay')):
            nm = d['stay'][0]['name'] if d.get('stay') else d.get('stayName')
            rows.append({'t': '晚上', 'type': 'stay', 'name': '住' + nm if nm.startswith(('山', '海')) else '住在' + nm, 'd': d['stay'][0].get('sell', '') if d.get('stay') else d.get('stayNote', ''), 'poi': nm})
        first = next((w for w in d['rows'] if w['type'] == 'dep'), None)
        facts = [('出发', first['t'] if first else '—')]
        if d.get('driveMin'): facts.append(('开车', hrs(d['driveMin'])))
        if (d.get('elev') or 0) >= 1500: facts.append(('海拔', f'{d["elev"]:,} 米'))
        fx = ''.join(f'<span class="fx"><small>{k}</small><b>{E(v)}</b></span>' for k, v in facts)
        fx += f'<span class="fx"><small>日出</small><b class="sun" data-lat="{d["lat"]}" data-lng="{d["lng"]}" data-k="rise">—</b></span><span class="fx"><small>日落</small><b class="sun" data-lat="{d["lat"]}" data-lng="{d["lng"]}" data-k="set">—</b></span>'
        stays = ''
        if d.get('stay') and i < n - 1 and not (i > 0 and r['days'][i - 1].get('city') == d.get('city') and r['days'][i - 1].get('stay')):
            stays = '<div class="stays"><h3>今晚住</h3><ul>' + ''.join(
                f'<li><span class="tier">{E(o["tier"])}</span><div><b>{E(o["name"])}</b><small>{E(o.get("sell"))}{(" · " + E(o.get("price"))) if o.get("price") else ""}</small></div><span class="ics">{icons(o["name"], d.get("navCity") or d.get("city"), app, o.get("dp"))}</span></li>' for o in d['stay']) + \
                f'</ul><a class="btn" rel="nofollow noopener" target="_blank" href="https://hotels.ctrip.com/hotels/list?keyword={urllib.parse.quote(d["stay"][0]["name"])}">去携程订</a></div>'
        story = f'<aside class="story"><p>{E(d["story"])}</p></aside>' if d.get('story') else ''
        notes = ''.join(f'<p class="note">{E(x)}</p>' for x in d.get('notes') or [])
        clim = d.get('clim') or {}
        days.append(f'''<section class="day" id="d{i + 1}"><header><small>第 {i + 1} 天</small><h2>{E(d["title"])}</h2></header>
<div class="facts">{fx}</div>{notes}<p class="lead">{E(d.get("text"))}</p>
<ol class="tl">{"".join(row_html(w, d.get("navCity") or d.get("city"), app) for w in rows)}</ol>{stays}{story}</section>''')
        sights += [w['name'] for w in d['rows'] if w['type'] == 'see' and w.get('poi')]
    desc = f'{r["title"]}：{n} 天按天排好，' + '、'.join(dict.fromkeys(re.split(r'\s*·\s*', ' · '.join(x['title'] for x in r['days']))))[:70] + '。' + season_text(t)
    ld = {'@context': 'https://schema.org', '@type': 'TouristTrip', 'name': r['title'], 'description': desc, 'url': BASE + f'/trip/{rid}/', 'inLanguage': 'zh-CN',
          'touristType': [x for x in (t.get('tags') or [])][:3] or None,
          'itinerary': {'@type': 'ItemList', 'numberOfItems': len(dict.fromkeys(sights)), 'itemListElement': [
              {'@type': 'ListItem', 'position': i + 1, 'item': {'@type': 'TouristAttraction', 'name': s}} for i, s in enumerate(dict.fromkeys(sights))]},
          'provider': {'@type': 'Organization', 'name': SITE, 'url': BASE}}
    lo, hi = (t.get('price') or {}).get('lo'), (t.get('price') or {}).get('hi')
    if lo and hi: ld['offers'] = {'@type': 'AggregateOffer', 'priceCurrency': 'CNY', 'lowPrice': lo, 'highPrice': hi, 'description': '每人，2 人同行，含往返大交通'}
    ld = {k: v for k, v in ld.items() if v}
    dest_link = f'<p class="back"><a href="/d/{E(t["dest"])}/">{E(d0.get("name", ""))}还有哪些去处</a></p>' if t.get('dest') in DEST else ''
    daynav = ('<nav class="daynav" aria-label="跳到第几天">' + ''.join(f'<a href="#d{i + 1}">{i + 1}</a>' for i in range(n)) + '</nav>') if n >= 4 else ''
    acts = f'<div class="acts"><button type="button" class="fav" data-id="{rid}" data-label="{E(r.get("label"))}" data-title="{E(r["title"])}">收藏</button><button type="button" class="share">分享</button><button type="button" class="copy">复制行程</button></div>'
    body = f'''<article class="trip" data-app="{app}" data-id="{rid}" data-label="{E(r.get("label"))}" data-title="{E(r["title"])}">{hero(r)}
{acts}{glance}
<section class="pre"><h2>出发前</h2><ul>{prep or "<li>没有特别要提前办的</li>"}</ul></section>
<section class="overview"><h2>{n} 天怎么走</h2><ol>{over}</ol></section>{daynav}
{"".join(days)}
{dest_link}</article>'''
    crumbs = [('首页', '/'), ('去哪儿', '/where/')] + ([(d0['name'], f'/d/{t["dest"]}/')] if d0 else []) + [(r.get('label') or r['title'], f'/trip/{rid}/')]
    img = '/img/' + (r.get('img') or '').replace('/_blob/', '') + '.svg' if r.get('img') else None
    write(f'/trip/{rid}/', page(f'/trip/{rid}/', f'{r.get("label") or r["title"]}行程：{r["title"]} | 走你', desc, body, [ld], img, crumbs))
    return desc


def dest_page(d):
    did = d['id']; cl = d.get('climate') or {}
    best = set(d['months']['best'])
    SEASON = {12: 'w', 1: 'w', 2: 'w', 3: 'sp', 4: 'sp', 5: 'sp', 6: 'su', 7: 'su', 8: 'su', 9: 'au', 10: 'au', 11: 'au'}
    months = ''.join(f'<li class="{("on " + SEASON[m]) if m in best else ""}"><b>{m}月</b><small>{cl.get(str(m), ["", ""])[0]}°</small><small>{cl.get(str(m), ["", ""])[1]}°</small></li>' for m in range(1, 13))
    trips = ''.join(f'<li><a href="/trip/{rid}/"><b>{E(ROUTES[rid].get("label"))}</b><span>{E(ROUTES[rid]["title"])}</span><small>{E(ROUTES[rid].get("price"))}</small></a></li>' for rid in DEST_ROUTES.get(did, []))
    other = [t for t in TRIPS if t['dest'] == did and not any(TRIP_OF_ROUTE.get(r) is t for r in DEST_ROUTES.get(did, []))]
    trips += ''.join(f'<li><span><b>{E(t["title"])}</b><small>{"暂不排" if t["status"] == "blocked" else "整理中"}</small></span></li>' for t in other)
    city = d['base']['name']; app = 'google' if d['scope'] == 'asia' else 'amap'
    ql = sorted(QUAL_BY_PROV.get(d['name'], []) if d['scope'] == 'domestic' else [], key=lambda q: (0 if '世界遗产' in q['tags'] else 1, q['short']))
    qhtml = ''.join(f'<li><span>{E(q["short"])}</span><small>{"世界遗产" if "世界遗产" in q["tags"] else "5A"}</small>{icons(q["short"], d["name"], app)}</li>' for q in ql)
    see = '、'.join(d['see']); eat = '、'.join(d['eat'])
    nhtml = ''.join(f'<li><div class="nh"><b>{E(x["name"])}</b><span class="st {x["status"]}">{STATUS[x["status"]]}</span>{icons(x["name"].split("（")[0].replace(" · ", " "), d["name"], app)}</div><p>{E(x["note"])}</p>' + (f'<a href="/trip/{x["trip"]}/">看行程</a>' if x.get('trip') and x['trip'] in ROUTES else '') + '</li>' for x in NICHE_BY_DEST.get(did, []))
    desc = f'{d["name"]}旅行：最好的月份是 {"、".join(str(m) for m in sorted(best))} 月，建议 {d["days"]["min"] if d.get("days") else ""}–{d["days"]["max"] if d.get("days") else ""} 天；看{see}，吃{eat}。' + (f'共 {len(ql)} 处 5A 和世界遗产。' if ql else '')
    entry = f'<p class="entry"><b>入境</b>{E(d["entry"])}</p>' if d.get('entry') else ''
    tip = f'<p class="tip">{E(d["tip"])}</p>' if d.get('tip') else ''
    body = f'''<article class="dest"><header class="dh"><small>{E(d["region"])} · 落脚 {E(city)}</small><h1>{E(d["name"])}</h1>
<p class="lead">最好的月份：{"、".join(str(m) + " 月" for m in sorted(best))}。建议 {E(d["days"]["min"]) if d.get("days") else "—"}{("–" + str(d["days"]["max"])) if d.get("days") and d["days"]["max"] != d["days"]["min"] else ""} 天。</p>{entry}{tip}</header>
<section><h2>什么时候去</h2><p class="hint">深色是最好的月份；数字是白天、夜里的平均气温</p><ol class="months">{months}</ol>{f"<p class=elev>落脚城市海拔 {d['base']['elev']:,} 米</p>" if (d['base'].get('elev') or 0) >= 1500 else ""}</section>
<section class="se"><div><h2>看</h2><p>{E(see)}</p></div><div><h2>吃</h2><p>{E(eat)}</p></div></section>
{f'<section><h2>排好的行程</h2><ul class="trips">{trips}</ul></section>' if trips else ''}
{f'<section><h2>5A 景区和世界遗产<span class="ct">{len(ql)}</span></h2><ul class="qual">{qhtml}</ul></section>' if ql else ''}
{f'<section><h2>去的人少<span class="ct">{len(NICHE_BY_DEST.get(did, []))}</span></h2><ul class="niche">{nhtml}</ul></section>' if nhtml else ''}
</article>'''
    attractions = [{'@type': 'TouristAttraction', 'name': q['short']} for q in ql] or [{'@type': 'TouristAttraction', 'name': x} for x in d['see']]
    ld = {'@context': 'https://schema.org', '@type': 'TouristDestination', 'name': d['name'], 'description': desc, 'url': BASE + f'/d/{did}/',
          'geo': {'@type': 'GeoCoordinates', 'latitude': d['base']['lat'], 'longitude': d['base']['lng']}, 'includesAttraction': attractions[:60]}
    write(f'/d/{did}/', page(f'/d/{did}/', f'{d["name"]}旅行攻略：什么时候去、玩几天、看什么吃什么 | 走你', desc, body, [ld], None, [('首页', '/'), ('去哪儿', '/where/'), (d['name'], f'/d/{did}/')]))
    return desc


def fit_label(best, m):
    if m in best: return '正好'
    if any(abs((b - m) % 12) in (1, 11) for b in best): return '也行'
    return '不建议'


def where_page():
    m = TODAY.month
    groups = []
    for scope, title in (('domestic', '国内'), ('asia', '亚洲')):
        regs = []
        for reg in ATLAS['regions'][scope]:
            cards = []
            for x in [x for x in ATLAS[scope] if x['region'] == reg]:
                f = '暂不排' if x['noTrip'] else fit_label(x['best'], m)
                cl = x['clim'].get(str(m)) or ['', '']
                n_tr = len(DEST_ROUTES.get(x['id'], []))
                days = sorted({len(ROUTES[r]['days']) for r in DEST_ROUTES.get(x['id'], [])}) or ([int(z) for z in re.findall(r'\d+', x['days'])[:1]] or [0])
                qn = ' '.join([x['name'], x['base']] + x['see'] + x['eat'] + [q['short'] for q in QUAL_BY_PROV.get(x['name'], [])] + [ROUTES[r].get('label', '') for r in DEST_ROUTES.get(x['id'], [])] + [z['name'] for z in NICHE_BY_DEST.get(x['id'], [])])
                high = 1 if (x.get('elev') or 0) >= 2200 else 0
                nn = len(NICHE_BY_DEST.get(x['id'], []))
                los = [t['price']['lo'] for t in TRIPS if t['dest'] == x['id'] and (t.get('price') or {}).get('lo') and t.get('status') != 'blocked']
                plo = min(los) if los else ''
                hits = '|'.join([q['short'] for q in QUAL_BY_PROV.get(x['name'], [])] + [z['name'] for z in NICHE_BY_DEST.get(x['id'], [])] + x['see'] + x['eat'])
                cards.append(f'<li class="card {("f0" if f == "正好" else "f1" if f == "也行" else "f2")}" data-best="{",".join(map(str, x["best"]))}" data-clim=\'{E(json.dumps(x["clim"]))}\' data-no="{1 if x["noTrip"] else 0}" data-days="{",".join(map(str, days))}" data-high="{high}" data-lat="{x['lat']}" data-lng="{x['lng']}" data-niche="{nn}" data-plo="{plo}" data-hits="{E(hits)}" data-q="{E(qn)}"><a href="/d/{x["id"]}/">'
                             f'<div class="ch"><h3>{E(x["name"])}</h3><span class="fit">{f}</span></div><p class="cl">{m} 月白天 {cl[0]}°，夜里 {cl[1]}°</p>'
                             f'<p class="hit" hidden></p><p class="dist" hidden></p><p>看 {E("、".join(x["see"]))}</p><p class="n">{f"{n_tr} 条排好的行程" if n_tr else ""}{f" · {nn} 处小众" if nn else ""}</p></a></li>')
            regs.append(f'<section class="reg"><h3 class="rh">{E(reg)}</h3><ul class="cards">{"".join(cards)}</ul></section>')
        groups.append(f'<section class="scope" id="{scope}"><h2>{title}</h2>{"".join(regs)}</section>')
    body = f'''<article class="where"><h1>去哪儿</h1><p class="lead">国内 34 个省级行政区和亚洲 22 国，按月份看哪儿正好去。</p>
<div class="flt"><input type="search" placeholder="搜地名或景点，比如 婺源、兵马俑" aria-label="搜地名或景点">
<div class="sel"><select aria-label="从哪出发"><option value="">出发地</option>{"".join(f'<option value="{o}">从{o}出发</option>' for o in ORIGINS)}</select><select aria-label="每人预算" class="bud"><option value="">预算</option><option value="2000">每人 2,000 以内</option><option value="5000">每人 5,000 以内</option><option value="10000">每人 1 万以内</option></select></div>
<div class="chips"><button type="button" data-f="near" hidden>500 公里内</button><button type="button" data-f="fit" class="on">只看合适的</button><button type="button" data-f="d1">2–3 天</button><button type="button" data-f="d2">4–5 天</button><button type="button" data-f="d3">6 天以上</button><button type="button" data-f="low">避开高原</button><button type="button" data-f="niche">有小众</button></div><p class="cnt" aria-live="polite"></p></div>
<div class="mon" role="group" aria-label="选月份">{"".join(f'<button type="button" data-m="{k}" class="{"on" if k == m else ""}">{k}月</button>' for k in range(1, 13))}</div>
{"".join(groups)}</article>'''
    write('/where/', page('/where/', '去哪儿：国内 34 个省级行政区和亚洲 22 国，按月份挑目的地 | 走你', '每个目的地按月份标出正好去、也行、不建议，附每月平均气温、看什么吃什么和排好的行程。', body, [], None, [('首页', '/'), ('去哪儿', '/where/')]))


def home_page():
    m = TODAY.month; md0 = TODAY.strftime('%m-%d')
    def in_season(t):
        if t.get('anytime'): return 1
        b = (t.get('season') or {}).get('best')
        return 2 if b and b[0] <= md0 <= b[1] else 0
    picks = sorted([rid for rid in ROUTE_IDS if TRIP_OF_ROUTE.get(rid)], key=lambda rid: (-in_season(TRIP_OF_ROUTE[rid]), 0 if ROUTES[rid].get('img') else 1))
    cover = picks[0]; r = ROUTES[cover]
    items = ''.join(f'<li><a href="/trip/{rid}/"><b>{E(ROUTES[rid].get("label"))}</b><span>{E(ROUTES[rid]["title"])}</span><small>{E(ROUTES[rid].get("price"))}</small></a></li>' for rid in picks[1:9])
    good = [x for x in ATLAS['domestic'] + ATLAS['asia'] if not x['noTrip'] and m in x['best']]
    nrids = [rid for rid in ROUTE_IDS if '小众' in ((TRIP_OF_ROUTE.get(rid) or {}).get('tags') or [])]
    niche_items = ''.join(f'<li><a href="/trip/{rid}/"><b>{E(ROUTES[rid].get("label"))}</b><span>{E(ROUTES[rid]["title"])}</span><small>{E(ROUTES[rid].get("price"))}</small></a></li>' for rid in sorted(nrids, key=lambda r: -in_season(TRIP_OF_ROUTE[r]))[:6])
    body = f'''<article class="home"><a class="cover" href="/trip/{cover}/">{hero(r)}</a>
<section class="mine" hidden><h2 class="lbl">我收藏的</h2><ul class="list" data-k="fav"></ul></section>
<section class="mine" hidden><h2 class="lbl">最近看过</h2><ul class="list" data-k="seen"></ul></section>
<section><h2>{m} 月的行程</h2><ul class="list">{items}</ul></section>
<section><h2>{m} 月正好去的地方</h2><ul class="tiles">{"".join(f'<li><a href="/d/{x["id"]}/"><b>{E(x["name"])}</b><small>白天 {(x["clim"].get(str(m)) or ["", ""])[0]}°</small></a></li>' for x in good[:12])}</ul><p class="more"><a href="/where/">看全部 56 个目的地</a></p></section>
<section><h2>去的人少</h2><ul class="list">{niche_items}</ul></section></article>
<script>(function(){{var m=location.hash.match(/#trip=(\\w+)/);if(m){{location.replace("/trip/"+m[1]+"/");}}}})();</script>'''
    ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE, 'url': BASE + '/', 'inLanguage': 'zh-CN',
          'description': '按季节挑目的地，按天排好每一站：几点出发、怎么去、吃什么、住哪。'}
    write('/', page('/', '走你：按季节挑目的地，按天排好每一站', f'{len(ROUTE_IDS)} 条按天排好的行程，国内 34 个省级行政区和亚洲 22 国的目的地，按月份看哪儿正好去。', body, [ld], '/img/' + (r.get('img') or '').replace('/_blob/', '') + '.svg' if r.get('img') else None))


def extras(trip_desc, dest_desc):
    urls = ['/', '/where/'] + [f'/d/{d["id"]}/' for d in CAT['destinations']] + [f'/trip/{rid}/' for rid in ROUTE_IDS]
    lm = TODAY.isoformat()
    open(os.path.join(OUT, 'sitemap.xml'), 'w', encoding='utf-8').write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        ''.join(f'<url><loc>{BASE}{u}</loc><lastmod>{lm}</lastmod></url>\n' for u in urls) + '</urlset>\n')
    open(os.path.join(OUT, 'robots.txt'), 'w', encoding='utf-8').write(f'User-agent: *\nAllow: /\n\nSitemap: {BASE}/sitemap.xml\n')
    lines = ['# 走你（zouni.app）', '', '> 中文旅行行程网站：按季节挑目的地，按天排好每一站——几点出发、怎么去、吃什么、住哪；覆盖国内 34 个省级行政区和亚洲 22 国。', '',
             '每条行程都是按天、按时间排的：出发时间、交通方式和时长、饭点、住宿片区或三档酒店；每个地点带地图和大众点评链接。目的地页给出最好的月份、12 个月平均气温、看什么吃什么，以及该省全部国家 5A 级旅游景区和世界遗产。', '',
             '## 主要页面', f'- [去哪儿]({BASE}/where/)：按月份看国内和亚洲目的地哪儿正好去', '', '## 目的地']
    lines += [f'- [{d["name"]}]({BASE}/d/{d["id"]}/)：{dest_desc[d["id"]]}' for d in CAT['destinations']]
    lines += ['', '## 行程'] + [f'- [{ROUTES[rid].get("label")}]({BASE}/trip/{rid}/)：{trip_desc[rid]}' for rid in ROUTE_IDS]
    open(os.path.join(OUT, 'llms.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    open(os.path.join(OUT, 'CNAME'), 'w').write('zouni.app\n')
    for f in glob.glob('site_src/*.txt'):   # indexnow 密钥文件（公开的，按协议要放在站点根目录）
        if re.fullmatch(r'[0-9a-f]{32}\.txt', os.path.basename(f)): shutil.copy(f, os.path.join(OUT, os.path.basename(f)))
    open(os.path.join(OUT, '.nojekyll'), 'w').write('')
    nf = page('/404.html', '没找到这个页面 | 走你', '这个页面不存在，可以从去哪儿重新找。',
              '<article class="nf"><h1>没找到这个页面</h1><p><a class="btn" href="/where/">去“去哪儿”找找 ›</a></p></article><script>(function(){var m=location.hash.match(/#trip=(\\w+)/);if(m){location.replace("/trip/"+m[1]+"/");}})();</script>')
    open(os.path.join(OUT, '404.html'), 'w', encoding='utf-8').write(nf.replace('<link rel="canonical" href="https://zouni.app/404.html">', '<meta name="robots" content="noindex">'))


if __name__ == '__main__':
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'img')); os.makedirs(os.path.join(OUT, 'assets'))
    for f in glob.glob(os.path.join(POSTER_SRC, '*.svg')): shutil.copy(f, os.path.join(OUT, 'img'))
    for f in ('site.css', 'site.js', 'favicon.svg', 'og.png'):
        src = os.path.join('site_src', f)
        if os.path.exists(src): shutil.copy(src, os.path.join(OUT, 'img' if f in ('favicon.svg', 'og.png') else 'assets', f))
    trip_desc = {rid: trip_page(rid) for rid in ROUTE_IDS}
    dest_desc = {d['id']: dest_page(d) for d in CAT['destinations']}
    where_page(); home_page(); extras(trip_desc, dest_desc)
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print('网站', OUT, '· 行程页', len(ROUTE_IDS), '· 目的地页', len(CAT['destinations']), '· 文件', n)
