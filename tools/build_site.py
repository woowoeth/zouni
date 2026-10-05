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
CULT = json.load(open('data/catalog/culture.json')) if os.path.exists('data/catalog/culture.json') else {'museums': [], 'experiences': []}
MUS = CULT['museums']


def museum_of(text):
    t = text or ''
    return next((x for x in sorted(MUS, key=lambda x: -len(x['name'])) if x['name'] in t or x['name'].replace('博物馆', '博') in t or (len(x['name']) > 4 and t and t in x['name'] and len(t) >= 4) or any(a and a in t for a in x.get('alias', []))), None)


FAMOUS = {  # 只写有把握的老字号 / 名店
    '北京': {'烤鸭': ['四季民福', '全聚德'], '涮羊肉': ['东来顺']}, '西安': {'羊肉泡馍': ['老孙家', '同盛祥'], '肉夹馍': ['樊记肉夹馍']},
    '兰州': {'牛肉面': ['马子禄']}, '武汉': {'热干面': ['蔡林记'], '豆皮': ['老通城']}, '长沙': {'臭豆腐': ['火宫殿']},
    '杭州': {'西湖醋鱼': ['楼外楼'], '片儿川': ['奎元馆']}, '苏州': {'苏式汤面': ['同得兴'], '松鼠鳜鱼': ['松鹤楼']},
    '上海': {'生煎': ['小杨生煎']}, '天津': {'狗不理包子': ['狗不理'], '耳朵眼炸糕': ['耳朵眼']}, '广州': {'早茶': ['陶陶居', '广州酒家']},
    '桂林': {'桂林米粉': ['崇善米粉']}, '开封': {'灌汤包': ['第一楼']}, '洛阳': {'水席': ['真不同']}, '扬州': {'早茶': ['富春茶社']},
    '无锡': {'小笼包': ['王兴记']}, '哈尔滨': {'锅包肉': ['老厨家'], '马迭尔冰棍': ['马迭尔']}, '沈阳': {'老边饺子': ['老边饺子馆']},
    '澳门': {'葡挞': ['安德鲁饼店'], '猪扒包': ['大利来记']}, '香港': {'云吞面': ['麦奀记'], '烧腊': ['甘牌烧鹅']}}
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

ICON_PIN = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21s-6.5-5.8-6.5-11a6.5 6.5 0 0 1 13 0c0 5.2-6.5 11-6.5 11z"/><circle cx="12" cy="10" r="2.3"/></svg>'
ICON_DP = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4.5 5h15v10.5H11l-4.5 3.5v-3.5h-2z"/><path d="M12 7.7l1 2 2.2.3-1.6 1.55.38 2.2-1.98-1.05-1.98 1.05.38-2.2-1.6-1.55 2.2-.3z"/></svg>'


GEO = json.load(open('data/geo/pois.json')) if os.path.exists('data/geo/pois.json') else {}


PLACES = json.load(open('data/geo/places.resolved.json')) if os.path.exists('data/geo/places.resolved.json') else {}
GEO_BY_NAME = {}
for _k, _v in GEO.items():
    if _v and '|' in _k and not _k.endswith('#tried'): GEO_BY_NAME.setdefault(_k.split('|', 1)[1], _v)
QUAL_GEO = {q['short']: q for q in json.load(open('data/catalog/cn_quality.json'))['items'] if 'lat' in q}
NICHE_GEO = {n['name'].split('（')[0].replace(' · ', ' '): n for n in json.load(open('data/catalog/niche.json'))['items']}


def coord(kw, city):
    kw = kw or ''
    for g in (GEO.get((city or '') + '|' + kw), PLACES.get(kw), GEO_BY_NAME.get(kw), QUAL_GEO.get(kw), NICHE_GEO.get(kw)):
        if g and g.get('lat') is not None: return (g['lat'], g['lng'])
    return None



import math as _m
def wgs2gcj(lat, lng):
    """WGS-84 → GCJ-02（高德用的坐标），国外不转"""
    if not (73.5 < lng < 135.1 and 3.8 < lat < 53.6): return lat, lng
    a = 6378245.0; ee = 0.00669342162296594323
    def tl(x, y): return -100.0 + 2.0*x + 3.0*y + 0.2*y*y + 0.1*x*y + 0.2*_m.sqrt(abs(x)) + (20.0*_m.sin(6.0*x*_m.pi) + 20.0*_m.sin(2.0*x*_m.pi)) * 2.0/3.0 + (20.0*_m.sin(y*_m.pi) + 40.0*_m.sin(y/3.0*_m.pi)) * 2.0/3.0 + (160.0*_m.sin(y/12.0*_m.pi) + 320*_m.sin(y*_m.pi/30.0)) * 2.0/3.0
    def tg(x, y): return 300.0 + x + 2.0*y + 0.1*x*x + 0.1*x*y + 0.1*_m.sqrt(abs(x)) + (20.0*_m.sin(6.0*x*_m.pi) + 20.0*_m.sin(2.0*x*_m.pi)) * 2.0/3.0 + (20.0*_m.sin(x*_m.pi) + 40.0*_m.sin(x/3.0*_m.pi)) * 2.0/3.0 + (150.0*_m.sin(x/12.0*_m.pi) + 300.0*_m.sin(x/30.0*_m.pi)) * 2.0/3.0
    dlat = tl(lng - 105.0, lat - 35.0); dlng = tg(lng - 105.0, lat - 35.0)
    rl = lat / 180.0 * _m.pi; mg = 1 - ee * _m.sin(rl) ** 2; sm = _m.sqrt(mg)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (mg * sm) * _m.pi); dlng = (dlng * 180.0) / (a / sm * _m.cos(rl) * _m.pi)
    return round(lat + dlat, 6), round(lng + dlng, 6)

def mapurl(kw, city, app):
    ll = coord(kw, city)
    if app == 'google':
        return 'https://www.google.com/maps/search/?api=1&query=' + (f'{ll[0]},{ll[1]}' if ll else urllib.parse.quote(kw))
    if ll:
        g = wgs2gcj(ll[0], ll[1])
        return f'https://uri.amap.com/marker?position={g[1]},{g[0]}&name={urllib.parse.quote(kw)}&src=zouni&callnative=1'
    return 'https://uri.amap.com/search?keyword=' + urllib.parse.quote(kw) + ('&city=' + urllib.parse.quote(city) if city else '') + '&src=zouni&callnative=1'


def dpurl(kw, city=''):
    return 'https://www.dianping.com/ai-search?keyword=' + urllib.parse.quote((city + ' ' if city else '') + kw)


def icons(kw, city, app, dp=None, nav=None):
    if not kw: return ''
    q = ((city + ' ') if city else '') + kw
    return (f'<a class="ic" href="{E(nav or mapurl(kw, city, app))}" rel="nofollow noopener" target="_blank" aria-label="{"导航去 " if nav else "地图上看 "}{E(kw)}">{ICON_PIN}</a>'
            f'<a class="ic dp" href="{E(dp or dpurl(kw, city))}" data-app="{E("dianping://searchshoplist?keyword=" + urllib.parse.quote(q))}" rel="nofollow noopener" target="_blank" aria-label="大众点评上看 {E(kw)}">{ICON_DP}</a>')


def md(s):  # "10-25" → "10 月 25 日"
    m, d = s.split('-'); return f'{int(m)} 月 {int(d)} 日'


def season_text(t):
    if not t: return ''
    if t.get('anytime'): return '一年四季都能去'
    s = t.get('season') or {}
    b = s.get('best')
    return f'最好在 {md(b[0])}到{md(b[1])}' if b else ''




def write(path, s):
    p = os.path.join(OUT, path.strip('/'), 'index.html') if path.endswith('/') else os.path.join(OUT, path.strip('/'))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write(s)




def hrs(m):
    if not m: return ''
    v = round(m / 30) / 2
    return (f'{v:.1f}' if v % 1 else f'{int(v)}') + ' 小时'




WEEK = '一二三四五六日'






def fit_label(best, m):
    if m in best: return '正好'
    if any(abs((b - m) % 12) in (1, 11) for b in best): return '也行'
    return '不建议'






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


# ======== 按画布设计稿重写的页面（覆盖上面的同名函数） ========
CN_NUM = '一二三四五六七八九十'
def cn_day(i): return '第' + (CN_NUM[i] if i < 10 else str(i + 1)) + '天'
SHARE_ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 14.5V3.5"/><path d="M7.5 8L12 3.5 16.5 8"/><path d="M5 12.5v7h14v-7"/></svg>'
BACK_ICON = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M14.5 5.5L8 12l6.5 6.5"/></svg>'


def page(path, title, desc, body, jsonld=(), image=None, crumbs=()):
    url = BASE + path
    ld = ''.join(f'<script type="application/ld+json">{json.dumps(j, ensure_ascii=False)}</script>' for j in jsonld)
    if crumbs:
        ld += '<script type="application/ld+json">' + json.dumps({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
            {'@type': 'ListItem', 'position': i + 1, 'name': n, 'item': BASE + p} for i, (n, p) in enumerate(crumbs)]}, ensure_ascii=False) + '</script>'
    og = image or '/img/og.png'
    return f"""<!doctype html>
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
<link rel="manifest" href="/manifest.webmanifest"><link rel="apple-touch-icon" href="/img/icon-192.png">
<link rel="stylesheet" href="/assets/fonts/sans.css"><link rel="stylesheet" href="/assets/fonts/serif.css">
<link rel="stylesheet" href="/assets/site.css">
{ld}
</head>
<body>
<main>
{body}
</main>
<footer class="foot"><p>走你：按季节挑地方，按天排好每一站。</p><p><a href="/">本期</a><a href="/where/">去哪儿</a><a href="/sitemap.xml">网站地图</a></p></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


def hero(r, back=None, share=False):
    sq = (f'<a class="sq l back" href="/" aria-label="返回上一页">{BACK_ICON}</a><a class="sq l2 home" href="/" aria-label="回首页"><b>走</b></a>' if back else '') + (f'<button type="button" class="sq rt share" aria-label="分享">{SHARE_ICON}</button>' if share else '')
    kick = E(r.get('kicker'))
    img = (r.get('img') or '').replace('/_blob/', '')
    gen = os.path.join('site_src', 'posters', (r.get('id') or '') + '.svg')
    if not (img and os.path.exists(os.path.join(POSTER_SRC, img + '.svg'))) and os.path.exists(gen):
        return f'<div class="hero"><img src="/img/p/{E(r.get("id"))}.svg" alt="{E(r.get("alt") or r["title"])}" width="430" height="380">{sq}<div class="hero-t"><span class="kick">{kick}</span><h1>{E(r["title"])}</h1></div></div>'
    if img and os.path.exists(os.path.join(POSTER_SRC, img + '.svg')):
        return f'<div class="hero"><img src="/img/{E(img)}.svg" alt="{E(r.get("alt") or r["title"])}" width="430" height="380">{sq}<div class="hero-t"><span class="kick">{kick}</span><h1>{E(r["title"])}</h1></div></div>'
    mark = re.sub(r'\s*\d+\s*天$', '', r.get('label') or '')
    bg = ['#3a302a', '#2e3a3f', '#3b3527', '#2f3830'][len(r.get('id') or '') % 4]
    return f'<div class="hero text" style="background:{bg}"><span class="mark" aria-hidden="true">{E(mark)}</span>{sq}<div class="hero-t"><span class="kick">{kick}</span><h1>{E(r["title"])}</h1></div></div>'


def navurl(a, b, how, app, name):
    if not a or not b: return None
    h = how or ''
    if any(k in h for k in ('高铁', '飞机', '轮渡', '火车', 'JR', '坐船', '徒步约')): return None
    mode = 'walk' if '步行' in h else 'bus' if ('地铁' in h or '公交' in h) else 'car'
    if app == 'google':
        gm = {'walk': 'walking', 'bus': 'transit', 'car': 'driving'}[mode]
        return f'https://www.google.com/maps/dir/?api=1&origin={a[0]},{a[1]}&destination={b[0]},{b[1]}&travelmode={gm}'
    ga, gb = wgs2gcj(*a), wgs2gcj(*b)
    return f'https://uri.amap.com/navigation?from={ga[1]},{ga[0]},{urllib.parse.quote("上一站")}&to={gb[1]},{gb[0]},{urllib.parse.quote(name or "下一站")}&mode={mode}&src=zouni&callnative=1'


def row_html(w, city, app):
    t = w['type']
    if t == 'dep':
        sub = E(w.get('how')) if w.get('how') else ''
        return f'<li class="r dep"><time>{E(w["t"])}</time><span class="dot"></span><div class="rb"><p class="m">出发 → {E(w.get("to"))}</p>{f"<p class=s>{sub}</p>" if sub else ""}</div></li>'
    if t == 'eat':
        place = w.get('place') if w.get('place') not in ('随意', '住的地方附近', '附近', '车站或机场里吃', '沿途', '路上') else ''
        main = f'{E(w.get("slot"))} · {E(w.get("dish"))}'
        rec = [x for d_ in re.split(r'[、，]', w.get('dish') or '') for x in FAMOUS.get(city or '', {}).get(d_.strip(), [])]
        tip = ('老店：' + '、'.join(rec)) if rec else ('点评上找附近评分高的店' if w.get('dish') not in ('简单吃一点', '随意') else '')
        sub = ' · '.join(x for x in [E(place), E(w.get('d')), E(w.get('kb')), E(tip)] if x)
        kw = w.get('poi') or place
    elif t == 'stay':
        main = '住 · ' + E(w.get('name')); sub = E(w.get('d')); kw = w.get('poi')
        if not w.get('dp'):
            ic = f'<a class="ic" href="{E(mapurl(kw, city, app))}" rel="nofollow noopener" target="_blank" aria-label="地图上看 {E(kw)}">{ICON_PIN}</a>' if kw else ''
            return f'<li class="r stay"><time>{E(w["t"])}</time><span class="dot"></span><div class="rb"><p class="m">{main}{ic}</p>{f"<p class=s>{sub}</p>" if sub else ""}</div></li>'
    else:
        main = E(w.get('name')); sub = ' · '.join(x for x in [E(w.get('d')), E(w.get('kb'))] if x); kw = w.get('poi')
        mu = museum_of(w.get('name')) or museum_of(w.get('poi'))
        if mu and mu['treasures']:
            main += '<span class="gb">国宝</span>'
            sub = (sub + '</p><p class="s tre">' if sub else '') + '<b>镇馆之宝</b>' + E('、'.join(mu['treasures'])) + (('，' + E(mu['note'])) if mu.get('note') else '')
    ic = icons(kw, city, app, w.get('dp'), w.get('nav')) if kw else ''
    if t == 'eat' and not kw:   # 没有具体地方的饭：只放点评，按“城市 + 菜名”找
        ic = f'<a class="ic dp" href="{E(dpurl(w.get("dish") or "", city))}" data-app="{E("dianping://searchshoplist?keyword=" + urllib.parse.quote((city or "") + " " + (w.get("dish") or "")))}" rel="nofollow noopener" target="_blank" aria-label="大众点评上找 {E(w.get("dish"))}">{ICON_DP}</a>'
    return f'<li class="r {t}"><time>{E(w["t"])}</time><span class="dot"></span><div class="rb"><p class="m">{main}{ic}</p>{f"<p class=s>{sub}</p>" if sub else ""}</div></li>'


WEEK = '一二三四五六日'
def start_date(r):
    st = r.get('start') or [TODAY.year, TODAY.month - 1, TODAY.day]
    d = datetime.date(st[0], st[1] + 1, min(st[2], 28))
    while d < TODAY: d = d.replace(year=d.year + 1)
    return d


def trip_page(rid):
    r = ROUTES[rid]; t = TRIP_OF_ROUTE.get(rid) or {}; d0 = DEST.get(t.get('dest'), {})
    sd = start_date(r); dates = [sd + datetime.timedelta(days=i) for i in range(len(r['days']))]
    md = lambda x: f'{x.month}/{x.day}'
    app = r.get('navApp') or 'amap'; n = len(r['days']); price = r.get('price') or ''; cost = r.get('cost')
    back = f'/d/{t["dest"]}/' if t.get('dest') in DEST else '/where/'
    s0 = (t.get('season') or {}).get('best')
    when = '一年四季都能去' if t.get('anytime') else (f'{int(s0[0][:2])}/{int(s0[0][3:])}–{int(s0[1][:2])}/{int(s0[1][3:])} 最好' if s0 else '')
    has_cost = bool(cost and cost.get('trans'))
    sub3 = ('<button type="button" class="pp">2 人 · 每人 ›</button>' if has_cost else f'<small>{"每人 · 含往返" + (" · 参考价" if price.startswith("约") else "") if "¥" in price else "价格另算"}</small>')
    glance = (f'<div class="glance"><div class="g1"><b class="big">{n}<small> 天</small></b><button type="button" class="dtw dt" data-best="{",".join(s0) if s0 else ""}" aria-label="改出发日期">{md(dates[0])}–{md(dates[-1])} <i>改</i></button><input type="hidden" class="dpk" data-min="{TODAY.isoformat()}" value="{dates[0].isoformat()}"></div>'
              f'<div><b>{E(r.get("driveTop"))}</b><small>{E(r.get("driveSub"))}</small></div>'
              f'<div><b class="price" data-cost=\'{E(json.dumps(cost)) if has_cost else ""}\'>{E(price)}</b>{sub3}</div></div>')
    if has_cost:
        glance += f'<div class="ppl" hidden><span>{"租车按车分摊，两人一间" if cost.get("perCar") else "两人一间，一个人单独一间"}</span><div><button type="button" data-d="-1" aria-label="少一个人">−</button><b>2 人</b><button type="button" data-d="1" aria-label="多一个人">+</button></div></div>'
    prep = ''.join(f'<li><label><input type="checkbox" data-k="{i}"><span>{E(x)}</span></label></li>' for i, x in enumerate(r.get('prep') or [])) + ''.join(f'<li class="fit">{E(x)}</li>' for x in r.get('fit') or [])
    def firstdep(d):
        w = next((w for w in d['rows'] if w['type'] == 'dep'), None); return w['t'] if w else ''
    over = ''.join(f'<li><a href="#d{i + 1}"><b>{i + 1:02d}</b><i>{md(dates[i])}</i><span class="ot"><strong>{E(d["title"])}</strong><small>{"回家" if i == n - 1 else "住" + E(d.get("navCity") or d.get("city"))}</small></span><em>{E(firstdep(d))} 走</em></a></li>' for i, d in enumerate(r['days']))
    hm_ = hand_map(r)
    daynav = '<nav class="daynav" aria-label="跳到第几天">' + ''.join(f'<a href="#d{i + 1}">{i + 1}</a>' for i in range(n)) + '</nav>'
    days = []; sights = []; navprev = None
    for i, d in enumerate(r['days']):
        city = d.get('navCity') or d.get('city'); rows = list(d['rows'])
        if i < n - 1 and (d.get('stayName') or d.get('stay')):
            nm = d['stay'][0]['name'] if d.get('stay') else d.get('stayName')
            rows.append({'t': '晚上', 'type': 'stay', 'name': nm, 'd': d['stay'][0].get('sell', '') if d.get('stay') else d.get('stayNote', ''), 'poi': nm, 'dp': d['stay'][0].get('dp') if d.get('stay') else None})
        first = firstdep(d)
        facts = [('出发', first or '—')]
        if d.get('driveMin'): facts.append(('开车', hrs(d['driveMin'])))
        if (d.get('elev') or 0) >= 1500: facts.append(('高海拔' if d['elev'] >= 3000 else '海拔', f'{d["elev"]:,}'))
        fx = ''.join(f'<div class="fx"><small>{k}</small><b>{E(v)}</b></div>' for k, v in facts)
        fx += f'<div class="fx"><small>日出</small><b class="sun" data-lat="{d["lat"]}" data-lng="{d["lng"]}" data-date="{dates[i].isoformat()}" data-k="rise">—</b></div><div class="fx"><small>日落</small><b class="sun" data-lat="{d["lat"]}" data-lng="{d["lng"]}" data-date="{dates[i].isoformat()}" data-k="set">—</b></div>'
        stays = ''
        if d.get('stay') and i < n - 1 and not (i > 0 and r['days'][i - 1].get('city') == d.get('city') and r['days'][i - 1].get('stay')):
            run = 1
            while i + run < n - 1 and r['days'][i + run].get('city') == d.get('city'): run += 1
            lis = ''.join(f'<li class="{"" if k == 0 else "more"}"><span class="tier">{E(o["tier"])}</span><div><b>{E(o["name"])}</b><small>{E(o.get("sell"))}{(" · " + E(o.get("price"))) if o.get("price") else ""}</small>{f"<small>{E(o.get(chr(107)+chr(98)))}</small>" if o.get("kb") else ""}</div></li>' for k, o in enumerate(d['stay']))
            dpu = d['stay'][0].get('dp') or dpurl(d['stay'][0]['name'], city)
            stays = (f'<div class="stays"><div class="sh"><span class="lbl">今晚住</span><span>{"连住 " + str(run) + " 晚" if run > 1 else ""}</span></div><ul>{lis}</ul>'
                     + (f'<button type="button" class="tog">看另外两档</button>' if len(d['stay']) > 1 else '')
                     + f'<div class="bk"><a class="btn" rel="nofollow noopener" target="_blank" href="https://m.ctrip.com/webapp/hotels/list?keyword={urllib.parse.quote(d["stay"][0]["name"])}">去携程订</a><a class="btn2" rel="nofollow noopener" target="_blank" href="{E(dpu)}" aria-label="在大众点评看这家酒店">{ICON_DP}</a><button type="button" class="mk" data-k="{rid}-{i}">标记已订</button></div></div>')
        if not stays and not d.get('stay') and i < n - 1 and (d.get('stayName') or d.get('stayNote')) and not (i > 0 and r['days'][i - 1].get('stayName') == d.get('stayName') and r['days'][i - 1].get('city') == d.get('city')):
            area = d.get('stayName') or city; run = 1
            while i + run < n - 1 and r['days'][i + run].get('stayName') == d.get('stayName'): run += 1
            BIG = {'北京', '上海', '广州', '深圳', '杭州', '成都', '西安', '南京', '苏州', '重庆', '武汉', '长沙', '厦门', '三亚', '香港', '澳门', '青岛', '大连', '天津', '东京', '首尔', '新加坡', '迪拜', '伊斯坦布尔', '大阪', '京都'}
            hi = (d.get('elev') or 0) >= 2500
            pr = (('¥600 起', '¥300–500', '¥120–250') if hi else ('¥1,500 起', '¥600–1,000', '¥250–400') if city in BIG else ('¥900 起', '¥400–700', '¥150–300'))
            q_ = lambda w_: 'https://m.ctrip.com/webapp/hotels/list?keyword=' + urllib.parse.quote(f'{city} {area if area != city else ""} {w_}'.replace('  ', ' ').strip())
            tiers = [('奢华', '五星或高端度假酒店' if not hi else '当地最好的酒店', pr[0], q_('五星酒店' if not hi else '酒店')), ('高级', '四星或品牌连锁', pr[1], q_('四星酒店')), ('中低', '经济连锁或干净的客栈', pr[2], q_('经济型酒店'))]
            lis = ''.join(f'<li class="{"" if k == 0 else "more"}"><span class="tier">{tn}</span><div><b>{E(area)} · {desc}</b><small>参考价 {pp}/晚</small><a class="tl2" rel="nofollow noopener" target="_blank" href="{E(u)}">携程上按这档看 ›</a></div></li>' for k, (tn, desc, pp, u) in enumerate(tiers))
            stays = (f'<div class="stays"><div class="sh"><span class="lbl">今晚住</span><span>{"连住 " + str(run) + " 晚" if run > 1 else "按档位挑"}</span></div><ul>{lis}</ul><button type="button" class="tog">看另外两档</button>'
                     f'<div class="bk"><a class="btn" rel="nofollow noopener" target="_blank" href="{E(tiers[0][3])}">去携程订</a><a class="btn2" rel="nofollow noopener" target="_blank" href="{E(dpurl(area + " 酒店", city))}" aria-label="在大众点评看附近酒店">{ICON_DP}</a><button type="button" class="mk" data-k="{rid}-{i}">标记已订</button></div></div>')
        story = f'<aside class="story"><span class="lbl">懂一点</span><p>{E(d["story"])}</p></aside>' if d.get('story') else ''
        mlist = (CULT.get('manners') or {}).get(t.get('dest'), []) if i == 0 else []
        if mlist: story = f'<div class="mn"><span class="lbl">当地讲究</span><ul>' + ''.join(f'<li>{E(x)}</li>' for x in mlist) + '</ul></div>' + story
        notes = ''.join(f'<p class="note"><b>路上</b>{E(x)}</p>' for x in d.get('notes') or [])
        lastpt = navprev
        for k, w in enumerate(rows):
            if w['type'] == 'dep':
                nxt = next((x for x in rows[k + 1:] if x['type'] != 'dep' and x.get('poi')), None)
                b_ = coord(nxt['poi'], city) if nxt else None
                u_ = navurl(lastpt, b_, w.get('how'), app, (nxt.get('name') or nxt.get('place') or nxt.get('dish') or '') if nxt else '') if nxt else None
                if u_:
                    j_ = rows.index(nxt); rows[j_] = dict(nxt, nav=u_)
            elif w.get('poi'):
                c_ = coord(w['poi'], city)
                if c_: lastpt = c_
        navprev = lastpt
        days.append(f'<section class="day" id="d{i + 1}"><header><span class="no">{i + 1:02d}</span><div><small>{cn_day(i)} · {md(dates[i])} 周{WEEK[dates[i].weekday()]}</small><h2>{E(d["title"])}</h2></div></header>'
                    f'<div class="facts">{fx}</div><p class="cl" data-clim=\'{E(json.dumps({**(d0.get("climate") or {}), **(d.get("clim") or {})}))}\'>{("往年 " + str(dates[i].month) + " 月平均：白天 " + str((d.get("clim") or {}).get(str(dates[i].month), ["", ""])[0]) + "℃，夜里 " + str((d.get("clim") or {}).get(str(dates[i].month), ["", ""])[1]) + "℃") if (d.get("clim") or {}).get(str(dates[i].month)) else ""}</p>{notes}<p class="lead">{E(d.get("text"))}</p><ol class="tl">{"".join(row_html(w, city, app) for w in rows)}</ol>{stays}{story}</section>')
        sights += [w['name'] for w in d['rows'] if w['type'] == 'see' and w.get('poi')]
    desc = f'{r["title"]}：{n} 天按天排好，' + '、'.join(dict.fromkeys(re.split(r'\s*·\s*', ' · '.join(x['title'] for x in r['days']))))[:70] + '。' + season_text(t)
    ld = {'@context': 'https://schema.org', '@type': 'TouristTrip', 'name': r['title'], 'description': desc, 'url': BASE + f'/trip/{rid}/', 'inLanguage': 'zh-CN',
          'itinerary': {'@type': 'ItemList', 'numberOfItems': len(dict.fromkeys(sights)), 'itemListElement': [
              {'@type': 'ListItem', 'position': i + 1, 'item': {'@type': 'TouristAttraction', 'name': x}} for i, x in enumerate(dict.fromkeys(sights))]},
          'provider': {'@type': 'Organization', 'name': SITE, 'url': BASE}}
    lo, hi = (t.get('price') or {}).get('lo'), (t.get('price') or {}).get('hi')
    if lo and hi: ld['offers'] = {'@type': 'AggregateOffer', 'priceCurrency': 'CNY', 'lowPrice': lo, 'highPrice': hi, 'description': '每人，2 人同行，含往返大交通'}
    dest_link = f'<p class="back"><a href="/d/{E(t["dest"])}/">{E(d0.get("name", ""))}的其他去处 ›</a></p>' if t.get('dest') in DEST else ''
    dock = f'<div class="dock"><div><b>{md(dates[0])} 出发 · {n} 天</b><small>2 人 · 每人 {E(price.replace("约 ", ""))}</small></div><button type="button" class="fav" data-id="{rid}" data-label="{E(r.get("label"))}" data-title="{E(r["title"])}">收进行程</button></div>'
    body = (f'<article class="trip" data-app="{app}" data-id="{rid}" data-start="{dates[0].isoformat()}" data-label="{E(r.get("label"))}" data-title="{E(r["title"])}">{hero(r, back, True)}{glance}'
            f'<section class="pre"><h2>出发前</h2><ul>{prep or "<li class=fit>没有特别要提前办的</li>"}</ul></section>'
            f'<script type="application/json" id="cands">{json.dumps([{"rid": o, "label": ROUTES[o].get("label"), "i": k, "title": dd["title"]} for o in DEST_ROUTES.get(t.get("dest"), []) if o != rid for k, dd in enumerate(ROUTES[o]["days"])][:40], ensure_ascii=False).replace("</", "<\\/")}</script>'
            f'<section class="overview"><h2>{n} 天，怎么排</h2><ol>{over}</ol>{("<figure class=hmap>" + hm_ + "</figure>") if hm_ else ""}</section>{daynav}{"".join(days)}<div class="addday"><button type="button" class="add">＋ 加一天</button><small>想多玩一天：可以自由活动，也可以从附近线路挑一天接上</small></div><div class="acts"><button type="button" class="copy">复制整条行程，发到微信</button></div>{dest_link}{dock}</article>')
    crumbs = [('首页', '/'), ('去哪儿', '/where/')] + ([(d0['name'], f'/d/{t["dest"]}/')] if d0 else []) + [(r.get('label') or r['title'], f'/trip/{rid}/')]
    img = '/img/' + (r.get('img') or '').replace('/_blob/', '') + '.svg' if r.get('img') else None
    write(f'/trip/{rid}/', page(f'/trip/{rid}/', f'{r.get("label") or r["title"]}行程：{r["title"]} | 走你', desc, body, [ld], img, crumbs))
    return desc


def dest_page(d):
    did = d['id']; cl = d.get('climate') or {}; best = set(d['months']['best'])
    months = ''.join(f'<li class="{"on" if m in best else ""}{" now" if m == TODAY.month else ""}"><b>{m} 月{"·本月" if m == TODAY.month else ""}</b><small>{cl.get(str(m), ["", ""])[0]}° / {cl.get(str(m), ["", ""])[1]}°</small></li>' for m in range(1, 13))
    trips = ''.join(f'<li><a href="/trip/{rid}/"><b>{E(ROUTES[rid].get("label"))} ›</b><span>{E(ROUTES[rid]["title"])}</span><small>{E(ROUTES[rid].get("price"))}</small></a></li>' for rid in DEST_ROUTES.get(did, []))
    other = [t for t in TRIPS if t['dest'] == did and not any(TRIP_OF_ROUTE.get(r) is t for r in DEST_ROUTES.get(did, []))]
    trips += ''.join(f'<li><span><b>{E(t["title"])}</b> · {"暂不排" if t["status"] == "blocked" else "整理中"}</span></li>' for t in other)
    city = d['base']['name']; app = 'google' if d['scope'] == 'asia' else 'amap'
    ql = sorted(QUAL_BY_PROV.get(d['name'], []) if d['scope'] == 'domestic' else [], key=lambda q: (0 if '世界遗产' in q['tags'] else 1, q['short']))
    qhtml = ''.join(f'<li><span>{E(q["short"])}</span><small>{"世界遗产" if "世界遗产" in q["tags"] else "5A"}</small>{icons(q["short"], d["name"], app)}</li>' for q in ql)
    nl = NICHE_BY_DEST.get(did, [])
    nhtml = ''.join(f'<li><div class="nh"><b>{E(x["name"])}</b><span class="st {x["status"]}">{STATUS[x["status"]]}</span>{icons(x["name"].split("（")[0].replace(" · ", " "), d["name"], app)}</div><p>{E(x["note"])}</p>' + (f'<a href="/trip/{x["trip"]}/">看排好的行程 ›</a>' if x.get('trip') and x['trip'] in ROUTES else '') + '</li>' for x in nl)
    see = '、'.join(d['see']); eat = '、'.join(d['eat'])
    dd = d.get('days') or {}
    desc = f'{d["name"]}旅行：最好的月份是 {"、".join(str(m) for m in sorted(best))} 月，建议 {dd.get("min", "")}–{dd.get("max", "")} 天；看{see}，吃{eat}。' + (f'共 {len(ql)} 处 5A 和世界遗产。' if ql else '')
    entry = f'<p class="entry"><b>入境</b>{E(d["entry"])}</p>' if d.get('entry') else ''
    tip = f'<p class="tip"><b>提示</b>{E(d["tip"])}</p>' if d.get('tip') else ''
    days_txt = (str(dd.get('min')) + ('–' + str(dd['max']) if dd.get('max') and dd.get('max') != dd.get('min') else '')) if dd else '—'
    body = (f'<article class="dest"><div class="pagehead"><a class="back" href="/where/">{BACK_ICON}返回</a><a class="home" href="/">本期</a></div><div class="dh"><h1>{E(d["name"])}</h1><small>{E(d["region"])} · 落脚 {E(city)} · 建议 {days_txt} 天</small>'
            f'<p class="lead">最好的月份：{"、".join(str(m) + " 月" for m in sorted(best))}。</p>{entry}{tip}</div>'
            f'<section><h2>每个月白天 / 夜里平均气温（℃）</h2><ol class="months">{months}</ol>{f"<p class=hint style=margin-top:8px>落脚城市海拔 {d[chr(98)+chr(97)+chr(115)+chr(101)][chr(101)+chr(108)+chr(101)+chr(118)]:,} 米</p>" if (d["base"].get("elev") or 0) >= 1500 else ""}</section>'
            f'<section class="se"><div><h2>看</h2><p>{E(see)}</p></div><div><h2>吃</h2><p>{E(eat)}</p></div></section>'
            + (f'<section><h2>排好的行程</h2>' + (f'<figure class="hmap dmap">{dm_}</figure>' if (dm_ := dest_map(did, d)) else '') + f'<ul class="trips">{trips}</ul></section>' if trips else '')
            + (f'<section id="q"><h2>5A 和世界遗产 <span class="ct">{len(ql)} 处</span></h2><ul class="qual">{qhtml}</ul></section>' if ql else '')
            + (f'<section><h2>博物馆 <span class="ct">{len([x for x in MUS if x["dest"] == did])} 家</span></h2><ul class="qual mus">' + ''.join(f'<li><span><b>{E(x["name"])}</b>{("<small class=gt>镇馆之宝：" + E("、".join(x["treasures"])) + "</small>") if x["treasures"] else ""}</span>{"<em class=gb>国宝</em>" if x["treasures"] else ""}{icons(x["name"], x["city"], app)}</li>' for x in MUS if x['dest'] == did) + '</ul></section>' if any(x['dest'] == did for x in MUS) else '')
            + (f'<section><h2>人文体验</h2><ul class="niche">' + ''.join(f'<li><div class="nh"><b>{E(x["name"])}</b><span class="st open">{E(x["kind"])}</span>{icons(x["name"], x["city"], app)}</div><p>{E(x["note"])}</p></li>' for x in CULT['experiences'] if x['dest'] == did) + '</ul></section>' if any(x['dest'] == did for x in CULT['experiences']) else '')
            + (f'<section><h2>小众 <span class="ct">{len(nl)} 处</span></h2><ul class="niche">{nhtml}</ul></section>' if nhtml else '') + '</article>')
    attractions = [{'@type': 'TouristAttraction', 'name': q['short']} for q in ql] or [{'@type': 'TouristAttraction', 'name': x} for x in d['see']]
    ld = {'@context': 'https://schema.org', '@type': 'TouristDestination', 'name': d['name'], 'description': desc, 'url': BASE + f'/d/{did}/',
          'geo': {'@type': 'GeoCoordinates', 'latitude': d['base']['lat'], 'longitude': d['base']['lng']}, 'includesAttraction': attractions[:60]}
    write(f'/d/{did}/', page(f'/d/{did}/', f'{d["name"]}旅行攻略：什么时候去、玩几天、看什么吃什么 | 走你', desc, body, [ld], None, [('首页', '/'), ('去哪儿', '/where/'), (d['name'], f'/d/{did}/')]))
    return desc


def where_page():
    m = TODAY.month; scopes = []
    for scope, title in (('domestic', '国内'), ('asia', '亚洲')):
        regs = []
        for reg in ATLAS['regions'][scope]:
            cards = []
            for x in [x for x in ATLAS[scope] if x['region'] == reg]:
                f = '暂不排' if x['noTrip'] else fit_label(x['best'], m)
                cl = x['clim'].get(str(m)) or ['', '']
                n_tr = len(DEST_ROUTES.get(x['id'], [])); nn = len(NICHE_BY_DEST.get(x['id'], []))
                days = sorted({len(ROUTES[r]['days']) for r in DEST_ROUTES.get(x['id'], [])}) or ([int(z) for z in re.findall(r'\d+', x['days'])[:1]] or [0])
                qn = ' '.join([x['name'], x['base']] + x['see'] + x['eat'] + [q['short'] for q in QUAL_BY_PROV.get(x['name'], [])] + [ROUTES[r].get('label', '') for r in DEST_ROUTES.get(x['id'], [])] + [z['name'] for z in NICHE_BY_DEST.get(x['id'], [])])
                hits = '|'.join([q['short'] for q in QUAL_BY_PROV.get(x['name'], [])] + [z['name'] for z in NICHE_BY_DEST.get(x['id'], [])] + x['see'] + x['eat'])
                los = [t['price']['lo'] for t in TRIPS if t['dest'] == x['id'] and (t.get('price') or {}).get('lo') and t.get('status') != 'blocked']
                base = (x['base'] + ' · ' if x['base'] and x['base'] != x['name'] else '') + x['days']
                cnt = '　'.join(z for z in [f'{n_tr} 条排好的行程' if n_tr else '', f'{nn} 处小众' if nn else ''] if z)
                fcls = 'fit' + ('' if f == '正好' else ' ok' if f == '也行' else ' no')
                rows = []
                for rid in DEST_ROUTES.get(x['id'], [])[:4]:
                    tt = TRIP_OF_ROUTE[rid]; rr = ROUTES[rid]
                    rows.append(f'<a href="/trip/{rid}/"><b>{E(rr.get("label"))} ›</b><span>{E(rr.get("price"))}{(" · " + " · ".join((tt.get("tags") or [])[:2])) if tt.get("tags") else ""}</span></a>')
                more = len(DEST_ROUTES.get(x['id'], [])) - 4
                qn_ = len(QUAL_BY_PROV.get(x['name'], [])) if scope == 'domestic' else 0
                qlink = (f'<a class="q" href="/d/{x["id"]}/#q">{qn_} 处 5A 和世界遗产 ›</a>' if qn_ else '') + (f'<a class="q" href="/d/{x["id"]}/">还有 {more} 条行程 ›</a>' if more > 0 else '')
                entry = f'<p class="kv"><b>入境</b>{E(x.get("entry"))}</p>' if x.get('entry') else ''
                cards.append(f'<li class="card" data-best="{",".join(map(str, x["best"]))}" data-clim=\'{E(json.dumps(x["clim"]))}\' data-no="{1 if x["noTrip"] else 0}" data-days="{",".join(map(str, days))}" '
                             f'data-high="{1 if (x.get("elev") or 0) >= 2200 else 0}" data-lat="{x["lat"]}" data-lng="{x["lng"]}" data-niche="{nn}" data-plo="{min(los) if los else ""}" data-hits="{E(hits)}" data-q="{E(qn)}" data-name="{E(x["name"])}">'
                             f'<a class="ch" href="/d/{x["id"]}/"><div><h3>{E(x["name"])}</h3><span class="base">{E(base)}</span></div><span class="{fcls}">{f}</span></a>'
                             f'<p class="cl">{m} 月：白天 {cl[0]}℃，夜里 {cl[1]}℃</p><p class="hit" hidden></p><p class="dist" hidden></p>'
                             f'<p class="kv"><b>看</b>{E("、".join(x["see"]))}</p><p class="kv"><b>吃</b>{E("、".join(x["eat"]))}</p>{entry}'
                             f'{("<div class=tr>" + "".join(rows) + "</div>") if rows else ""}{qlink}</li>')
            regs.append(f'<section class="reg"><h3 class="rh">{E(reg)}</h3><ul class="cards">{"".join(cards)}</ul></section>')
        scopes.append(f'<section class="scope" id="{scope}"{"" if scope == "domestic" else " hidden"}>{"".join(regs)}</section>')
    nd, na = len(ATLAS['domestic']), len(ATLAS['asia'])
    body = (f'<article class="where"><div class="pagehead"><a class="back" href="/">{BACK_ICON}返回</a><a class="home" href="/">本期</a></div><h1>去哪儿</h1><div class="stick">'
            f'<div class="tabs"><button type="button" data-t="domestic" class="on">国内 · {nd}</button><button type="button" data-t="asia">亚洲 · {na}</button></div>'
            f'<div class="mon" role="group" aria-label="选月份">{"".join(f"<button type=button data-m={k} class={chr(39)}{chr(111)+chr(110) if k == m else chr(32)}{chr(39)}>{k}月</button>" for k in range(1, 13))}</div>'
            f'<div class="gl"><p class="goodline"></p><button type="button" class="ftog" aria-label="筛选">筛选 ▾</button></div>'
            f'<div class="flt" hidden><input type="search" placeholder="搜地名或景点，比如 婺源、兵马俑" aria-label="搜地名或景点">'
            f'<div class="row"><span>出发</span><select class="org" aria-label="从哪出发"><option value="">不限</option>{"".join(f"<option value={o}>{o}</option>" for o in ORIGINS)}</select><button type="button" data-f="near" hidden>500 公里内</button></div>'
            f'<div class="row"><span>天数</span><button type="button" data-f="d1">2–3 天</button><button type="button" data-f="d2">4–5 天</button><button type="button" data-f="d3">6 天以上</button></div>'
            f'<div class="row"><span>预算</span><select class="bud" aria-label="每人预算"><option value="">不限</option><option value="2000">2,000 以内</option><option value="5000">5,000 以内</option><option value="10000">1 万以内</option></select></div>'
            f'<div class="row"><span>其他</span><button type="button" data-f="fit" class="on">只看合适的</button><button type="button" data-f="low">避开高原</button><button type="button" data-f="niche">有小众</button></div><button type="button" class="clr" hidden>清空筛选</button></div>'
            f'<span class="cnt" aria-live="polite"></span></div>{"".join(scopes)}</article>')
    write('/where/', page('/where/', '去哪儿：国内 34 个省级行政区和亚洲 22 国，按月份挑目的地 | 走你', '每个目的地按月份标出正好去、也行、不建议，附每月平均气温、看什么吃什么和排好的行程。', body, [], None, [('首页', '/'), ('去哪儿', '/where/')]))





def home_page():
    """首页：先回答“现在去哪儿正好、还剩几天、我有几天”，再给下个月和小众"""
    m = TODAY.month; md0 = TODAY.strftime('%m-%d')
    def window(t):
        if t.get('anytime'): return None
        b = (t.get('season') or {}).get('best')
        return b
    def days_left(t):
        b = window(t)
        if not b: return None
        wrap = b[0] > b[1]
        inside = (md0 >= b[0] or md0 <= b[1]) if wrap else (b[0] <= md0 <= b[1])
        if not inside: return None
        end = datetime.date(TODAY.year + (1 if wrap and md0 >= b[0] else 0), int(b[1][:2]), int(b[1][3:]))
        return (end - TODAY).days
    inseason = [rid for rid in ROUTE_IDS if TRIP_OF_ROUTE.get(rid) and days_left(TRIP_OF_ROUTE[rid]) is not None]
    anytime = [rid for rid in ROUTE_IDS if TRIP_OF_ROUTE.get(rid) and TRIP_OF_ROUTE[rid].get('anytime')]
    # 封面：当季、有海报、离过季还有一段时间的里面挑最好看的那条
    cov = sorted([r for r in inseason if ROUTES[r].get('img')], key=lambda r: (0 if '小众' not in (TRIP_OF_ROUTE[r].get('tags') or []) else 1, -min(days_left(TRIP_OF_ROUTE[r]), 40)))
    cover = (cov or inseason or ROUTE_IDS)[0]; r = ROUTES[cover]; tc = TRIP_OF_ROUTE[cover]; dc = DEST.get(tc['dest'], {})
    clim = lambda d: (d.get('climate') or {}).get(str(m)) or ['', '']
    cimg = (r.get('img') or '').replace('/_blob/', '')
    mnames = '一二三四五六七八九十'
    mname = (mnames[m - 1] if m <= 10 else '十' + mnames[m - 11]) + '月'
    def wtxt(t):
        b = window(t)
        return f'{int(b[0][:2])}/{int(b[0][3:])}–{int(b[1][:2])}/{int(b[1][3:])}' if b else ''
    def item(i, rid, kicker, hide=False):
        rr = ROUTES[rid]; tt = TRIP_OF_ROUTE[rid]; dd = DEST.get(tt['dest'], {}); c = clim(dd); n = len(rr['days'])
        wb = window(tt) or ['', '']
        _src = ('/img/' + (rr.get('img') or '').replace('/_blob/', '') + '.svg') if rr.get('img') else ('/img/p/' + rid + '.svg')
        extra = (f' data-ws="{wb[0]}" data-we="{wb[1]}" data-img="{1 if rr.get("img") else 0}" data-comp="{1 if rr.get("compiled") else 0}" data-clim=\'{E(json.dumps(dd.get("climate") or {}))}\''
                 f' data-t="{E(rr["title"])}" data-n="{n}" data-pr="{E(rr.get("price"))}" data-src="{E(_src)}" data-h="/trip/{rid}/"')
        img = (rr.get('img') or '').replace('/_blob/', '')
        if not (img and os.path.exists(os.path.join(POSTER_SRC, img + '.svg'))) and os.path.exists(os.path.join('site_src', 'posters', rid + '.svg')): img = 'p/' + rid
        tile = (f'<a class="tile img" href="/trip/{rid}/"><img src="/img/{img}.svg" alt="" loading="lazy"></a>' if img and (img.startswith('p/') or os.path.exists(os.path.join(POSTER_SRC, img + '.svg')))
                else f'<a class="tile" href="/trip/{rid}/" style="background:{["#c8432f", "#2e5b6b", "#4f6233", "#5a4a6b", "#8a5a2b", "#3b5a7a"][i % 6]}">{E(re.sub(r"\s*\d+\s*天$", "", rr.get("label") or ""))}</a>')
        dl = days_left(tt)
        when = (f'<span class="left{" urgent" if dl is not None and dl <= 14 else ""}">{"最后 " + str(dl) + " 天" if dl is not None and dl <= 14 else "最好 " + wtxt(tt) + (" · 还剩 " + str(dl) + " 天" if dl is not None else "")}</span>' if window(tt) else '<span class="left">一年四季都能去</span>')
        band = 'd1' if n <= 3 else 'd2' if n <= 5 else 'd3'
        return (f'<li data-band="{band}"{extra}{" hidden" if hide else ""}><span class="num">{i:02d}</span><div class="tx"><span class="k">{kicker}</span><h3>{E(dd.get("name", ""))} · {E(rr.get("label"))}</h3><p>{E(rr["title"])}</p>'
                f'<small>{n} 天 · 人均 {E(rr.get("price"))}</small>{when}<span class="c">{m} 月白天 {c[0]}℃，夜里 {c[1]}℃</span><a class="open" href="/trip/{rid}/">翻开 ›</a></div>{tile}</li>')
    rest = [x for x in inseason if x != cover]
    urgent = sorted([x for x in rest if days_left(TRIP_OF_ROUTE[x]) <= 14], key=lambda x: (0 if ROUTES[x].get('img') else 1, days_left(TRIP_OF_ROUTE[x])))[:3]
    # 其余：有海报的精编线路先，再按离过季远近
    order = urgent + sorted([x for x in rest if x not in urgent], key=lambda x: (0 if ROUTES[x].get('img') else 1, 0 if not ROUTES[x].get('compiled') else 1, days_left(TRIP_OF_ROUTE[x])))
    counts = {b: sum(1 for x in order if ('d1' if len(ROUTES[x]['days']) <= 3 else 'd2' if len(ROUTES[x]['days']) <= 5 else 'd3') == b) for b in ('d1', 'd2', 'd3')}
    others = [x for x in ROUTE_IDS if TRIP_OF_ROUTE.get(x) and window(TRIP_OF_ROUTE[x]) and x not in order and x != cover]
    toc = ''.join(item(i + 2, rid, '小众' if '小众' in (TRIP_OF_ROUTE[rid].get('tags') or []) else '正当季', hide=i >= 8) for i, rid in enumerate(order)) + \
          ''.join(item(0, rid, '小众' if '小众' in (TRIP_OF_ROUTE[rid].get('tags') or []) else '正当季', hide=True) for rid in others)
    chips = (f'<div class="dchips" role="group" aria-label="我有几天"><button type="button" data-b="" class="on">全部 {len(order)}</button>'
             f'<button type="button" data-b="d1">周末 2–3 天 · {counts["d1"]}</button><button type="button" data-b="d2">4–5 天 · {counts["d2"]}</button><button type="button" data-b="d3">一周以上 · {counts["d3"]}</button></div>')
    nxt = (m % 12) + 1
    nextm = [rid for rid in ROUTE_IDS if TRIP_OF_ROUTE.get(rid) and window(TRIP_OF_ROUTE[rid]) and int(window(TRIP_OF_ROUTE[rid])[0][:2]) == nxt and rid not in inseason]
    nextm.sort(key=lambda x: (0 if ROUTES[x].get('img') else 1, 0 if not ROUTES[x].get('compiled') else 1))
    nitems = ''.join(item(i + 1, rid, f'{nxt} 月开始') for i, rid in enumerate(nextm[:5]))
    anyt = sorted([x for x in ROUTE_IDS if TRIP_OF_ROUTE.get(x) and TRIP_OF_ROUTE[x].get('anytime')], key=lambda x: (0 if ROUTES[x].get('img') else 1, 0 if not ROUTES[x].get('compiled') else 1))
    aitems = ''.join(item(i + 1, rid, '随时') for i, rid in enumerate(anyt[:6]))
    c0 = clim(dc); dl0 = days_left(tc)
    body = (f'<article class="home"><div class="cover">{f"<img src=/img/{cimg}.svg alt=>" if cimg else ""}'
            f'<div class="mast"><div><h1>走你</h1><small>{TODAY.year} · {mname}</small></div><a href="#mine"><span>我的行程</span></a></div>'
            f'<div class="datebar"><button type="button" class="hdt" aria-label="改出发日期"><b>{TODAY.month}/{TODAY.day} 周{"一二三四五六日"[TODAY.weekday()]} 出发</b><i>改</i></button><input type="hidden" class="hdpk" data-min="{TODAY.isoformat()}" value="{TODAY.isoformat()}"></div>'
            f'<div class="cv"><span class="kick">封面故事 · 正当季{(" · 还剩 " + str(dl0) + " 天") if dl0 is not None else ""}</span><h2>{E(r["title"])}</h2><div class="chips"><span>{len(r["days"])} 天 · 人均 {E(r.get("price"))}</span><span>{m} 月 {c0[0]}°C / {c0[1]}°C</span></div><a class="go" href="/trip/{cover}/">翻开 →</a></div></div>'
            f'<section class="mine" id="mine" hidden><h2>我的行程</h2><ul class="list" data-k="fav"></ul></section>'
            f'<section class="mine" hidden><h2>最近看过</h2><ul class="list" data-k="seen"></ul></section>'
            f'<section class="toc now" id="now"><h2><span class="nt">现在去正好</span><small class="ns">{len(order) + 1} 条，快过季的先看</small></h2>{chips}<ol class="items">{toc}</ol>'
            f'{("<button type=button class=moreb>再看 " + str(max(0, len(order) - 8)) + " 条</button>") if len(order) > 8 else ""}</section>'
            f'<a class="allbar" href="/where/"><span>全部目的地 · 按月份挑</span><span>›</span></a>'
            + (f'<section class="toc"><h2>下个月正好<small>{nxt} 月开始</small></h2><ol class="items">{nitems}</ol></section>' if nitems else '')
            + (f'<section class="toc"><h2>什么时候去都行<small>城市、古城、博物馆</small></h2><ol class="items">{aitems}</ol></section>' if aitems else '')
            + '</article>'
            '<script>(function(){var m=location.hash.match(/#trip=(\\w+)/);if(m){location.replace("/trip/"+m[1]+"/");}})();</script>')
    ld = {'@context': 'https://schema.org', '@type': 'WebSite', 'name': SITE, 'url': BASE + '/', 'inLanguage': 'zh-CN', 'description': '按季节挑目的地，按天排好每一站：几点出发、怎么去、吃什么、住哪。'}
    write('/', page('/', '走你：按季节挑目的地，按天排好每一站', f'{len(ROUTE_IDS)} 条按天排好的行程，现在正当季的 {len(inseason)} 条，国内 34 个省级行政区和亚洲 22 国的目的地按月份看。', body, [ld], '/img/' + cimg + '.svg' if cimg else None))



def hand_map(r):
    """手绘路线图：按每天经过的地点画（纸面、手抖的红线、天数圆章、主要地名、指北针）"""
    import random as _r, hashlib as _h, math as _m
    days = []
    for i, d in enumerate(r['days']):
        city = d.get('navCity') or d.get('city'); pts = []
        for w in d['rows']:
            if w['type'] in ('see', 'fun', 'eat', 'stay') and w.get('poi'):
                c = coord(w['poi'], city)
                if c and (not pts or abs(pts[-1][0] - c[0]) + abs(pts[-1][1] - c[1]) > 1e-4):
                    nm = re.sub(r'\s*·.*$', '', w.get('name') or w.get('place') or '')
                    pts.append((c[0], c[1], nm if w['type'] in ('see', 'fun') else '', w['type']))
        if not pts:
            g0 = GEO.get((city or '') + '|' + (city or ''))
            if g0: pts.append((g0['lat'], g0['lng'], city or '', 'see'))
        days.append(pts)
    allp = [p for d in days for p in d]
    if len(allp) < 2: return ''
    lats = [p[0] for p in allp]; lngs = [p[1] for p in allp]
    clat = (max(lats) + min(lats)) / 2; kx = _m.cos(_m.radians(clat))
    spanx = max((max(lngs) - min(lngs)) * kx, .03); spany = max(max(lats) - min(lats), .03)
    Wm, Hm, pad = 390, 260, 34
    sc = min((Wm - 2 * pad) / spanx, (Hm - 2 * pad - 10) / spany)
    cx0 = (max(lngs) + min(lngs)) / 2; cy0 = clat
    P = lambda la, lo: (Wm / 2 + (lo - cx0) * kx * sc, Hm / 2 + 6 - (la - cy0) * sc)
    rnd = _r.Random(int(_h.md5(r['title'].encode()).hexdigest()[:6], 16))
    out = [f'<svg viewBox="0 0 {Wm} {Hm}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{E(r["title"])} 路线手绘图">',
           '<defs><filter id="pp"><feTurbulence type="fractalNoise" baseFrequency=".8" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 .45  0 0 0 0 .38  0 0 0 0 .28  0 0 0 .06 0"/><feComposite in2="SourceGraphic" operator="in"/></filter></defs>',
           f'<rect x="1" y="1" width="{Wm - 2}" height="{Hm - 2}" fill="#efe9dc"/><rect x="1" y="1" width="{Wm - 2}" height="{Hm - 2}" filter="url(#pp)"/>',
           f'<rect x="6" y="6" width="{Wm - 12}" height="{Hm - 12}" fill="none" stroke="#1c1d1a" stroke-width="1.2" opacity=".55"/><rect x="9" y="9" width="{Wm - 18}" height="{Hm - 18}" fill="none" stroke="#1c1d1a" stroke-width=".6" opacity=".35"/>']
    # 手抖的线：每段用略微偏移的二次曲线画两遍
    prev = None; dots = []; labels = []; boxes = []; legend = []
    for di, pts in enumerate(days):
        for k, (la, lo, nm, tp) in enumerate(pts):
            x, y = P(la, lo)
            if prev:
                px, py = prev; mx, my = (px + x) / 2, (py + y) / 2; dx, dy = x - px, y - py; L = max(1, _m.hypot(dx, dy))
                off = rnd.uniform(-.18, .18) * L; qx, qy = mx - dy / L * off, my + dx / L * off
                dash = ' stroke-dasharray="5 4"' if (k == 0 and di > 0 and L > 120) else ''
                out.append(f'<path d="M{px:.1f},{py:.1f} Q{qx:.1f},{qy:.1f} {x:.1f},{y:.1f}" fill="none" stroke="#a63d27" stroke-width="2.2" stroke-linecap="round"{dash}/>')
                out.append(f'<path d="M{px + .8:.1f},{py - .6:.1f} Q{qx + 1.2:.1f},{qy + .8:.1f} {x - .6:.1f},{y + .7:.1f}" fill="none" stroke="#a63d27" stroke-width=".8" opacity=".5"/>')
            prev = (x, y)
            if k == 0: dots.append((x, y, di + 1))
            elif tp in ('see', 'fun'): out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#1c1d1a"/>')
            if nm and tp in ('see', 'fun') and nm not in [l_[1] for l_ in legend]:
                legend.append((len(legend) + 1, nm)); out.append(f'<text x="{x + 4:.1f}" y="{y - 4:.1f}" font-family="Noto Sans SC,sans-serif" font-size="8" font-weight="700" fill="#a63d27">{len(legend)}</text>') if len(pts) > 1 or di > 0 else None
            for (qx_, qy_, _n) in labels:
                if abs(qx_ - x) < 3 and abs(qy_ - y) < 3: x += 5; y -= 4
            if nm and len(labels) < 20: labels.append((x, y, nm[:7]))
    for x, y, n in dots:
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="9" fill="#f4f2ec" stroke="#a63d27" stroke-width="1.8"/><text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-family="Noto Serif SC,serif" font-weight="900" font-size="11" fill="#a63d27">{n}</text>')
        boxes.append((x - 10, y - 10, x + 10, y + 10))
    for x, y, nm in labels:
        w = len(nm) * 11 + 4
        for (lx, ly, anc) in ((x + 12, y + 4, 'start'), (x - 12, y + 4, 'end'), (x + 8, y - 12, 'start'), (x - 8, y + 20, 'end'), (x + 8, y + 20, 'start'), (x - 8, y - 12, 'end')):
            bx0 = lx if anc == 'start' else lx - w; bx1 = bx0 + w; by0, by1 = ly - 11, ly + 3
            if bx0 < 12 or bx1 > Wm - 12 or by0 < 12 or by1 > Hm - 12: continue
            if any(not (bx1 < a or bx0 > c or by1 < b or by0 > d) for a, b, c, d in boxes): continue
            boxes.append((bx0, by0, bx1, by1))
            out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-family="Noto Serif SC,serif" font-size="11" font-weight="700" fill="#1c1d1a" paint-order="stroke" stroke="#efe9dc" stroke-width="3">{E(nm)}</text>')
            break
        else:
            nm2 = nm[:5]; w2 = len(nm2) * 9 + 2
            for (lx, ly, anc) in ((x + 6, y - 5, 'start'), (x - 6, y - 5, 'end'), (x + 6, y + 12, 'start'), (x - 6, y + 12, 'end')):
                bx0 = lx if anc == 'start' else lx - w2; bx1 = bx0 + w2; by0, by1 = ly - 9, ly + 2
                if bx0 < 12 or bx1 > Wm - 12 or by0 < 12 or by1 > Hm - 12: continue
                if any(not (bx1 < a or bx0 > c or by1 < b or by0 > d) for a, b, c, d in boxes): continue
                boxes.append((bx0, by0, bx1, by1))
                out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-family="Noto Serif SC,serif" font-size="9" font-weight="700" fill="#3d3f3a" paint-order="stroke" stroke="#efe9dc" stroke-width="2.5">{E(nm2)}</text>')
                break
    # 景点扎堆的城市：右下角放一块放大图（西安城里那一堆，主图上挤在一起看不清）
    seq = [(la, lo, nm, tp) for d_ in days for (la, lo, nm, tp) in d_]
    kmp = [((lo - cx0) * kx * 111, (la - cy0) * 111) for la, lo, _, _ in seq]
    span_km = max(spanx, spany) * 111
    if span_km > 25 and len(seq) >= 6:
        R_ = max(2.5, span_km * .06); best = None
        for i_, (ax, ay) in enumerate(kmp):
            mem = [j_ for j_, (bx, by) in enumerate(kmp) if _m.hypot(ax - bx, ay - by) <= R_]
            if not best or len(mem) > len(best): best = mem
        if best and len(best) >= 4 and len(best) >= .4 * len(seq):
            cl = [seq[j_] for j_ in best]
            clat = [c[0] for c in cl]; clng = [c[1] for c in cl]
            ix0, iy0, iw, ih = Wm - 152, Hm - 112, 138, 96
            sx_ = max((max(clng) - min(clng)) * kx, .005); sy_ = max(max(clat) - min(clat), .005)
            isc = min((iw - 24) / sx_, (ih - 24) / sy_); icx = (max(clng) + min(clng)) / 2; icy = (max(clat) + min(clat)) / 2
            IP = lambda la, lo: (ix0 + iw / 2 + (lo - icx) * kx * isc, iy0 + ih / 2 - (la - icy) * isc)
            bx0, by1 = P(min(clat), min(clng)); bx1, by0 = P(max(clat), max(clng))
            out.append(f'<rect x="{bx0 - 5:.1f}" y="{by0 - 5:.1f}" width="{bx1 - bx0 + 10:.1f}" height="{by1 - by0 + 10:.1f}" fill="none" stroke="#1c1d1a" stroke-width=".8" stroke-dasharray="3 2" opacity=".6"/>')
            out.append(f'<rect x="{ix0}" y="{iy0}" width="{iw}" height="{ih}" fill="#f6f1e6" stroke="#1c1d1a" stroke-width="1"/><text x="{ix0 + 6}" y="{iy0 + 12}" font-family="Noto Sans SC,sans-serif" font-size="9" fill="#5d5f59">城里放大</text>')
            numof = {nm_: n_ for n_, nm_ in legend}
            pp = None
            for la, lo, nm, tp in cl:
                x_, y_ = IP(la, lo)
                if pp: out.append(f'<path d="M{pp[0]:.1f},{pp[1]:.1f} L{x_:.1f},{y_:.1f}" stroke="#a63d27" stroke-width="1.4" fill="none" opacity=".8"/>')
                pp = (x_, y_)
            for la, lo, nm, tp in cl:
                x_, y_ = IP(la, lo)
                out.append(f'<circle cx="{x_:.1f}" cy="{y_:.1f}" r="2.4" fill="#1c1d1a"/>')
                if nm in numof: out.append(f'<text x="{x_ + 4:.1f}" y="{y_ - 3:.1f}" font-family="Noto Sans SC,sans-serif" font-size="9" font-weight="700" fill="#a63d27">{numof[nm]}</text>')
    out.append(f'<g transform="translate({Wm - 30},34)" opacity=".75"><path d="M0,-14 L5,4 L0,0 L-5,4 Z" fill="#1c1d1a"/><text x="0" y="-17" text-anchor="middle" font-family="Noto Serif SC,serif" font-size="10" font-weight="900" fill="#1c1d1a">北</text></g>')
    km_w = spanx * 111
    out.append(f'<text x="16" y="{Hm - 16}" font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59">东西约 {round(km_w) if km_w >= 10 else round(km_w, 1)} 公里 · 示意，不按比例</text></svg>')
    if legend:
        out.append('<p class="hlegend">' + '　'.join(f'<b>{n_}</b>{E(nm_)}' for n_, nm_ in legend) + '</p>')
    return ''.join(out)



def dest_map(did, d):
    """目的地页的线路分布手绘图：每条线路画在它经过地点的中间，点名字直接进行程；小黑点是 5A 和世界遗产"""
    import math as _m
    pts = []
    for rid in DEST_ROUTES.get(did, []):
        r = ROUTES[rid]; cs = []
        for dd in r['days']:
            city = dd.get('navCity') or dd.get('city')
            for w in dd['rows']:
                if w['type'] in ('see', 'fun') and w.get('poi'):
                    c = coord(w['poi'], city)
                    if c: cs.append(c)
        if cs:
            pts.append((sum(c[0] for c in cs) / len(cs), sum(c[1] for c in cs) / len(cs), re.sub(r'\s*\d+\s*天$', '', r.get('label') or ''), rid))
    dots = [(q['lat'], q['lng']) for q in QUAL_BY_PROV.get(d['name'], []) if q.get('lat')] if d['scope'] == 'domestic' else []
    allp = [(p_[0], p_[1]) for p_ in pts] + dots
    if len(pts) < 2: return ''
    lats = [a for a, _ in allp]; lngs = [b for _, b in allp]
    clat = (max(lats) + min(lats)) / 2; kx = _m.cos(_m.radians(clat))
    spx = max((max(lngs) - min(lngs)) * kx, .2); spy = max(max(lats) - min(lats), .2)
    Wm, Hm, pad = 390, 300, 40
    sc = min((Wm - 2 * pad) / spx, (Hm - 2 * pad) / spy); cx0 = (max(lngs) + min(lngs)) / 2
    P = lambda la, lo: (Wm / 2 + (lo - cx0) * kx * sc, Hm / 2 - (la - clat) * sc)
    o = [f'<svg viewBox="0 0 {Wm} {Hm}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{E(d["name"])}的线路分布">',
         f'<rect x="1" y="1" width="{Wm - 2}" height="{Hm - 2}" fill="#efe9dc"/><rect x="6" y="6" width="{Wm - 12}" height="{Hm - 12}" fill="none" stroke="#1c1d1a" stroke-width="1.2" opacity=".55"/>']
    for la, lo in dots:
        x, y = P(la, lo); o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#1c1d1a" opacity=".35"/>')
    boxes = []
    for la, lo, nm, rid in sorted(pts, key=lambda p_: -len(ROUTES[p_[3]]['days'])):
        x, y = P(la, lo); w = len(nm) * 12 + 10
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#f4f2ec" stroke="#a63d27" stroke-width="2"/>')
        for (lx, ly, anc) in ((x + 9, y + 4, 'start'), (x - 9, y + 4, 'end'), (x, y - 10, 'middle'), (x, y + 18, 'middle')):
            bx0 = lx if anc == 'start' else lx - w if anc == 'end' else lx - w / 2; bx1 = bx0 + w
            if bx0 < 10 or bx1 > Wm - 10 or ly - 12 < 10 or ly + 3 > Hm - 10: continue
            if any(not (bx1 < a or bx0 > c or ly + 3 < b or ly - 12 > d_) for a, b, c, d_ in boxes): continue
            boxes.append((bx0, ly - 12, bx1, ly + 3))
            o.append(f'<a href="/trip/{rid}/" aria-label="{E(nm)}"><rect x="{bx0 - 2:.1f}" y="{ly - 26:.1f}" width="{w + 6:.1f}" height="40" fill="#efe9dc" fill-opacity="0"/><text x="{lx:.1f}" y="{ly:.1f}" text-anchor="{anc}" font-family="Noto Serif SC,serif" font-size="12" font-weight="900" fill="#a63d27" paint-order="stroke" stroke="#efe9dc" stroke-width="3">{E(nm)}</text></a>')
            break
    o.append(f'<g transform="translate({Wm - 28},32)" opacity=".75"><path d="M0,-12 L4,3 L0,0 L-4,3 Z" fill="#1c1d1a"/><text x="0" y="-15" text-anchor="middle" font-family="Noto Serif SC,serif" font-size="10" font-weight="900" fill="#1c1d1a">北</text></g>')
    o.append(f'<text x="14" y="{Hm - 14}" font-family="Noto Sans SC,sans-serif" font-size="10" fill="#5d5f59">红圈是排好的线路（点名字进去），小黑点是 5A 和世界遗产</text></svg>')
    return ''.join(o)

if __name__ == '__main__':
    if os.path.exists(OUT): shutil.rmtree(OUT)
    os.makedirs(os.path.join(OUT, 'img')); os.makedirs(os.path.join(OUT, 'assets'))
    for f in glob.glob(os.path.join(POSTER_SRC, '*.svg')): shutil.copy(f, os.path.join(OUT, 'img'))
    if os.path.isdir('site_src/fonts'): shutil.copytree('site_src/fonts', os.path.join(OUT, 'assets', 'fonts'))
    if os.path.isdir('site_src/posters'): shutil.copytree('site_src/posters', os.path.join(OUT, 'img', 'p'))
    for f in ('sw.js', 'manifest.webmanifest'):
        if os.path.exists('site_src/' + f): shutil.copy('site_src/' + f, os.path.join(OUT, f))
    for f in ('icon-192.png', 'icon-512.png'):
        if os.path.exists('site_src/' + f): shutil.copy('site_src/' + f, os.path.join(OUT, 'img', f))
    for f in ('site.css', 'site.js', 'favicon.svg', 'og.png'):
        src = os.path.join('site_src', f)
        if os.path.exists(src): shutil.copy(src, os.path.join(OUT, 'img' if f in ('favicon.svg', 'og.png') else 'assets', f))
    trip_desc = {rid: trip_page(rid) for rid in ROUTE_IDS}
    dest_desc = {d['id']: dest_page(d) for d in CAT['destinations']}
    where_page(); home_page(); extras(trip_desc, dest_desc)
    n = sum(len(fs) for _, _, fs in os.walk(OUT))
    print('网站', OUT, '· 行程页', len(ROUTE_IDS), '· 目的地页', len(CAT['destinations']), '· 文件', n)
