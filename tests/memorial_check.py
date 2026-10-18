#!/usr/bin/env python3
"""红色 / 抗战 / 革命类纪念性主题线的版面与语气（2026-10-18，用户反馈 P1）。会红。纯静态（读建好的站和 data/history），不用浏览器。

用法（项目根目录；先 bash build/pipe.sh build/site）：
    python3 tests/memorial_check.py build/site
    python3 tests/memorial_check.py build/site --inject hotel_back|rain_memo|rain_dup|etq_late|etq_box|xiang_exh|memo_off   # 反向自检：改的是测试读到的 HTML 文本（磁盘上的站不动），必须变红

K1  纪念类主题线（kind=event 且名字属于长征 / 延安 / 井冈山 / 西柏坡 / 辛亥 / 重庆陪都 / 台儿庄 / 卢沟桥 / 南京）的线路页：没有酒店星级档（奢华 / 高级 / 中低）、携程订房、点评评分入口（站点行的点评图标）、境外视频入口、美食影视标签；住处只有名称和“住处自行预订”
K2  对照：同一批页面里不属于纪念类的主题线（郑和、苏轼）仍有这些（防止判据空转）
K3  “下雨了去哪”和页面里的雨天备选（#indoor）排除纪念馆 / 陵园 / 遗址类，同一座馆不重复列
K4  参观礼仪是“出发前”的第一条：一句平实的话，没有复选框、没有粗体，整页只出现一次
K5  站点注释：馆内展陈介绍不加“某某：”前缀、不写“相传”；conf=medium 的传说类说法仍写“相传”
K6  整页最多一句通用的“多数博物馆、纪念馆周一休馆…”，且每个馆行里没有重复的通用句
"""
import glob, html, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
A = sys.argv[1:]
SITE = os.path.abspath(A[0]) if A and not A[0].startswith('--') else os.path.join(ROOT, 'build', 'site')
INJ = A[A.index('--inject') + 1] if '--inject' in A else None
ALL = ('hotel_back', 'rain_memo', 'rain_dup', 'etq_late', 'etq_box', 'xiang_exh', 'memo_off')
if INJ and INJ not in ALL: sys.exit('--inject 只认 ' + ' / '.join(ALL))
oks, fails = [], []
def check(name, cond, detail=''): (oks if cond else fails).append(name + ('  → ' + str(detail)[:300] if not cond and detail != '' else ''))

RED = re.compile(r'长征|红军|延安|井冈山|中央苏区|西柏坡|辛亥|陪都|重庆|台儿庄|卢沟桥|南京|抗战|抗日|革命|解放战争')
H = {}
for f in glob.glob(os.path.join(ROOT, 'data', 'history', '*.json')):
    if os.path.basename(f).startswith('_'): continue
    h = json.load(open(f, encoding='utf-8')); H[h['id']] = h
memo_t = {t: h for t, h in H.items() if h.get('kind') == 'event' and RED.search(h.get('name') or '')}
other_t = {t: h for t, h in H.items() if t not in memo_t and h.get('kind') in ('person',)}
rid_of = lambda ts: sorted(r for t in ts for r in (H[t].get('routes') or []))
MR, OR = rid_of(memo_t), rid_of(other_t)


def page(rid):
    p = os.path.join(SITE, 'trip', rid, 'index.html')
    if not os.path.exists(p): return None
    h = open(p, encoding='utf-8').read()
    if INJ == 'hotel_back' and rid == 'hya1': h = h.replace('<div class="stays memo">', '<div class="stays"><span class="tier">高级</span><a class="tl2" href="#">携程订这家 ›</a><small>4.7 分 · 2870 点评</small></div><div class="stays memo">', 1)
    if INJ == 'rain_memo' and rid == 'hzh1': h = h.replace('<script type="application/json" id="indoor">[', '<script type="application/json" id="indoor">[{"n": "南京大屠杀遇难同胞纪念馆", "q": "x", "c": "南京", "lat": 32.03, "lng": 118.73, "km": 3},', 1)
    if INJ == 'rain_dup' and rid == 'hzh1': h = h.replace('<script type="application/json" id="indoor">[', '<script type="application/json" id="indoor">[{"n": "南京云锦博物馆", "q": "x", "c": "南京", "lat": 32.0, "lng": 118.7, "km": 2},{"n": "南京云锦博物馆", "q": "x", "c": "南京", "lat": 32.0, "lng": 118.7, "km": 2},', 1)
    if INJ == 'etq_late' and rid == 'hya1': h = re.sub(r'(<li class="tip etq">.*?</li>)', '', h, 1, flags=re.S).replace('</ul></section><script type="application/json" id="cands">', '<li class="tip etq"><span>参观礼仪：着装得体</span></li></ul></section><script type="application/json" id="cands">', 1)
    if INJ == 'etq_box' and rid == 'hya1': h = h.replace('<li class="tip etq"><span>', '<li class="tip etq"><label><input type="checkbox"><b>', 1).replace('</span></li><li class="tip"><span>这条线跟着', '</b></label></li><li class="tip"><span>这条线跟着', 1)
    if INJ == 'xiang_exh': h = re.sub(r'<p class="fnote">(?![^<]{0,12}：)', '<p class="fnote">某某：相传', h)      # 展陈介绍又带上前缀和“相传”
    if INJ == 'memo_off' and rid == 'hya1': h = h.replace('class="stays memo"', 'class="stays"', 1).replace('住处自行预订', '', 1)
    return h


def text(h): return html.unescape(re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>', '', h, flags=re.S)))


# K1 / K2
bad = {}; seen = 0
for rid in MR:
    h = page(rid)
    if h is None: continue
    seen += 1; t = text(h); errs = []
    if re.search(r'携程', t): errs.append('携程')
    if 'class="tl2"' in h: errs.append('订房链接')
    if re.search(r'奢华|class="tier"', h): errs.append('星级档')
    if re.search(r'\d(\.\d)? ?分 · ?\d+ ?点评|\d+点评|[1-5] 钻', t): errs.append('点评评分')
    sites = re.findall(r'<li class="r (?:see|fun)[^>]*>.*?</li>', h, flags=re.S)
    if any('class="ic dp"' in x for x in sites): errs.append('景点行点评图标')
    if 'class="ic yt"' in h: errs.append('境外视频入口')
    if 'class="sjn"' in h: errs.append('美食影视标签')
    if 'stays memo' not in h or '住处自行预订' not in h: errs.append('缺“住处自行预订”')
    if errs: bad[rid] = errs
check('K1 纪念类主题线 %d 条：没有星级档、携程订房、点评评分入口、境外视频入口、美食影视标签，住处只写名称和“住处自行预订”' % seen, seen >= 10 and not bad, list(bad.items())[:4])
ctrl = [r for r in OR if page(r) and 'class="tl2"' in page(r)]
yt = [r for r in OR if page(r) and 'class="ic yt"' in page(r)]
check('K2 对照：不属于纪念类的主题线（%d 条）里仍有携程订房（%d 条）和视频入口（%d 条）——防止判据空转' % (len(OR), len(ctrl), len(yt)), len(ctrl) >= 3 and len(yt) >= 3, (len(ctrl), len(yt)))

# K3 雨天备选
MEMO_SITE = re.compile(r'纪念馆|纪念园|纪念碑|纪念地|烈士|陵园|遗址|遇难|大屠杀|战役|旧址|革命博物馆')
bad3, dup3, n3 = [], [], 0
for p in glob.glob(os.path.join(SITE, 'trip', '*', 'index.html')):
    rid = os.path.basename(os.path.dirname(p)); h = page(rid)
    m = re.search(r'<script type="application/json" id="indoor">(.*?)</script>', h, re.S)
    if not m: continue
    n3 += 1
    names = [x['n'] for x in json.loads(m.group(1).replace('<\\/', '</'))]
    if any(MEMO_SITE.search(n) for n in names): bad3.append((rid, [n for n in names if MEMO_SITE.search(n)][:2]))
    if len(names) != len(set(names)) or any(a != b and (a in b or b in a) for a in names for b in names): dup3.append((rid, names[:4]))
    f = re.search(r'<dt>下雨了去哪？</dt><dd>(.*?)</dd>', h, re.S)
    if f and MEMO_SITE.search(text(f.group(1))): bad3.append((rid, 'FAQ'))
for rid in ('hzh1',):
    h = page(rid); f = re.search(r'<dt>下雨了去哪？</dt><dd>(.*?)</dd>', h, re.S)
    check('K3a hzh1 的“下雨了去哪”有备选，且没有纪念馆 / 陵园 / 遗址（%s）' % (text(f.group(1))[:60] if f else None), bool(f) and not MEMO_SITE.search(text(f.group(1))), f and text(f.group(1)))
check('K3b 全站 %d 个线路页的雨天备选里没有纪念馆 / 陵园 / 遗址类' % n3, n3 > 100 and not bad3, bad3[:3])
check('K3c 雨天备选里同一座馆不重复列（名字相同或互相包含）', not dup3, dup3[:3])

# K4 参观礼仪
bad4 = []; n4 = 0
for rid in MR + OR:
    h = page(rid)
    if h is None: continue
    m = re.search(r'<section class="pre"><h2>出发前</h2><ul>(.*?)</ul>(?:<ul class="prehid" hidden>.*?</ul>)?</section>', h, re.S)      # 2026-10-18：“出发前”页内只露 ≤2 条纯文字提示，其余（待办和别的提示）在 ul.prehid[hidden] 里、只在“出发前要办的事”弹层里出现（礼仪永远是第一条，在外面）
    if not m or '参观礼仪' not in html.unescape(re.sub(r'<[^>]+>', '', m.group(1))): continue
    n4 += 1; first = re.match(r'\s*<li([^>]*)>(.*?)</li>', m.group(1), re.S)
    ok = bool(first) and 'etq' in first.group(1) and '参观礼仪' in re.sub(r'<[^>]+>', '', first.group(2)) and not re.search(r'<input|<b>|<strong>|<label', first.group(2)) and len(re.findall('参观礼仪', m.group(1))) == 1
    if not ok: bad4.append(rid)
check('K4 %d 条有参观礼仪的线：礼仪是“出发前”第一条、没有复选框和粗体、只出现一次' % n4, n4 >= 10 and not bad4, bad4[:4])

# K5 站点注释
EXH = re.compile(r'陈列|展陈|展出|展示|展览|馆藏|收藏|馆里|馆内|设有|辟有|专题博物馆|综合博物馆'); VEN = re.compile(r'博物馆|博物院|纪念馆|陈列馆|纪念园|展览馆|美术馆|科技馆')
nm_ = lambda h: re.sub(r'[（(].*?[）)]', '', h.get('name') or h['id']).strip()
bad5, n_ex, n_leg = [], 0, 0
for t, h in H.items():
    pages = [(r, page(r)) for r in (h.get('routes') or []) if page(r)]
    if not pages: continue
    blob = '\n'.join(text(x) for _, x in pages)
    for k, v in (h.get('notes') or {}).items():
        line = (v.get('line') or '').strip().rstrip('。')
        if not line: continue
        exh = bool(VEN.search(k) and EXH.search(line))
        if exh:
            body = re.sub(r'^(相传|传说)[，,]?', '', line)
            if body not in blob.replace(' ', '').replace('\xa0', '') and body.replace(' ', '') not in blob.replace(' ', '').replace('\xa0', ''): continue    # 这条没落在页面上（站点没排进线路）
            n_ex += 1
            if (nm_(h) + '：' + body).replace(' ', '') in blob.replace(' ', '').replace('\xa0', '') or ('相传' + body).replace(' ', '') in blob.replace(' ', '').replace('\xa0', ''): bad5.append((t, k, '展陈带了前缀或相传'))
        elif v.get('conf') == 'medium':
            want = (nm_(h) + '：' + (line if '相传' in line else '相传' + line)).replace(' ', '')
            if line.replace(' ', '') in blob.replace(' ', '').replace('\xa0', ''):
                n_leg += 1
                if want not in blob.replace(' ', '').replace('\xa0', ''): bad5.append((t, k, '传说类说法没写“相传”'))
check('K5 站点注释：展陈介绍（%d 条落在页面上）不带“某某：”前缀、不写“相传”；传说类（%d 条）仍写“相传”' % (n_ex, n_leg), n_ex >= 8 and n_leg >= 20 and not bad5, bad5[:4])

# K6 通用句只写一次
bad6 = []
for rid in MR + OR:
    h = page(rid)
    if h is None: continue
    if len(re.findall(r'多数博物馆、纪念馆周一休馆，热门馆要提前订票', h)) > 1 or '多数馆周一休馆，热门馆要提前订票' in h: bad6.append(rid)
check('K6 通用的“周一休馆、热门馆要提前订票”整页最多一句，馆行里没有重复', not bad6, bad6[:4])

for x in oks: print('✓', x)
for x in fails: print('✗', x)
print('\n纪念类主题线：%d 过 · %d 红%s' % (len(oks), len(fails), '（--inject %s）' % INJ if INJ else ''))
sys.exit(1 if fails else 0)
