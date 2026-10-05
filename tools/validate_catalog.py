# 目录体检：字段、类型、引用、日期、价格、坐标、气温，一条条查
import json, re, sys
D=json.load(open('data/catalog/destinations.json'))['destinations']; T=json.load(open('data/catalog/trips.json'))['trips']
ROUTES=re.search(r'window.ZOUNI_ORDER=(\[.*?\])',open(sys.argv[1] if len(sys.argv)>1 else 'build/routes.js',encoding='utf-8').read()).group(1)
pages=set(json.loads(ROUTES))
E=[]; W=[]
ids=[d['id'] for d in D]; tids=[t['id'] for t in T]
if len(set(ids))!=len(ids): E.append('目的地 id 重复')
if len(set(tids))!=len(tids): E.append('线路 id 重复')
dom=[d for d in D if d['scope']=='domestic']
if len(dom)!=34: E.append(f'国内应为 34 个省级行政区，现在 {len(dom)}')
mmdd=re.compile(r'^(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
for d in D:
    for k in ('id','name','scope','kind','region','base','months','see','eat','status','climate','trips'):
        if k not in d or d[k] in (None,''): E.append(f"{d.get('id')}: 缺 {k}")
    b=d['base']
    if not (-90<=b['lat']<=90 and -180<=b['lng']<=180) or (b['lat']==0 and b['lng']==0): E.append(f"{d['id']}: 坐标不对 {b['lat']},{b['lng']}")
    if b['elev'] is None or not (-100<=b['elev']<=6000): E.append(f"{d['id']}: 海拔不对 {b['elev']}")
    if sorted(d['climate'],key=int)!=[str(i) for i in range(1,13)]: E.append(f"{d['id']}: 气温不是 12 个月")
    for m,(hi,lo) in d['climate'].items():
        if hi<lo: E.append(f"{d['id']}: {m} 月最高低于最低")
    if not all(1<=m<=12 for m in d['months']['best']): E.append(f"{d['id']}: 月份越界")
    if d['scope']=='asia' and not d['entry']: E.append(f"{d['id']}: 亚洲目的地缺入境要求")
    if not d['trips'] and d['status']=='ok': W.append(f"{d['id']}: 还没有线路")
    for t in d['trips']:
        if t not in tids: E.append(f"{d['id']}: 引用了不存在的线路 {t}")
    # 最好的月份里，白天最高 ≥35℃ 或 ≤-15℃ 的提醒
    for m in d['months']['best']:
        hi,lo=d['climate'][str(m)]
        if hi>=35: W.append(f"{d['id']}: {m} 月标“正好”，但白天平均 {hi}℃")
        if hi<=-15: W.append(f"{d['id']}: {m} 月标“正好”，白天平均 {hi}℃（冰雪主题可以）")
for t in T:
    if t['dest'] not in ids: E.append(f"{t['id']}: 目的地 {t['dest']} 不存在")
    p=t['price']
    if (p['lo'] is None) != (p['hi'] is None) or (p['lo'] is not None and p['lo']>=p['hi']): E.append(f"{t['id']}: 价格不对 {p}")
    if p['lo'] is None: W.append(f"{t['id']}: 价格还没算")
    if not t['anytime']:
        s=t['season']
        if not s: E.append(f"{t['id']}: 不是随时能去，却没写季节")
        else:
            for k in ('ok','best'):
                for x in s[k]:
                    if not mmdd.match(x): E.append(f"{t['id']}: 日期格式不对 {x}")
            if not (s['ok'][0]<=s['best'][0]<=s['best'][1]<=s['ok'][1]): W.append(f"{t['id']}: 最好的日子 {s['best']} 不在能去的范围 {s['ok']} 里")
    if t['page'] and t['page'].startswith('Route.dc.html#') and t['page'].split('#')[1] not in pages: E.append(f"{t['id']}: 页面 {t['page']} 不存在")
    d=next((x for x in D if x['id']==t['dest']),None)
    if d and d['status']=='blocked' and t['status']!='blocked': E.append(f"{t['id']}: 目的地暂不排，线路却没标")
    if d and d['days'] and not (d['days']['min']-1<=t['days']<=d['days']['max']+3): W.append(f"{t['id']}: {t['days']} 天，和目的地建议的 {d['days']['min']}–{d['days']['max']} 天差得多")
print('错误', len(E)); [print('  ✗', e) for e in E]
print('提醒', len(W)); [print('  ·', w) for w in W]
# 编号撞车：目录里线路的标题和同编号行程的标题对不上（新行程误用了旧编号，会把旧行程覆盖掉）
try:
    _IT = json.load(open('data/itineraries.json'))['itineraries']
    _T = json.load(open('data/catalog/trips.json'))['trips']
    def _clash(t, it):
        nm = (t.get('name') or '').split(' · ')[-1]
        same_place = bool(nm) and (nm[:2] in it['label'] or it['label'][:2] in t['title'])
        return t['dest'] != it['dest'] or not same_place
    _bad = [f"{t['id']}: 目录“{t['title']}”（{t['dest']}） / 行程“{_IT[t['id']]['label']}”（{_IT[t['id']]['dest']}）" for t in _T if t['id'] in _IT and _clash(t, _IT[t['id']])]
    if _bad: print('编号撞车', len(_bad)); [print('  · ' + b) for b in _bad]
    else: print('编号撞车 0')
except Exception as _e: print('编号检查没跑成', _e)
# 住处矛盾：第二天一早要坐长途才到第一站，前一晚却写住在第二天那座城
try:
    import re as _re
    _lv = _re.compile(r'(JR|高铁|火车|动车|飞机|轮渡|包车约\s*[1-9]\s*小时|大巴约\s*[1-9]|自驾约\s*[1-9])')
    _bad = []
    for _rid, _it in json.load(open('data/itineraries.json'))['itineraries'].items():
        _ds = _it['days']
        for _i in range(len(_ds) - 1):
            _d, _nx = _ds[_i], _ds[_i + 1]; _st = _d.get('stay') or _d.get('city') or _it['city']; _dc = _d.get('city') or _it['city']
            _fv = (_nx['stops'][0].get('via') or '') if _nx['stops'] else ''; _nc = _nx.get('city') or _it['city']
            if _fv and _lv.search(_fv) and _st and (_st == _nc or _nc in _st) and _dc != _nc: _bad.append(f'{_rid} 第{_i + 1}天在{_dc}，住处写{_st}，第二天要{_fv}才到{_nc}')
    print('住处矛盾', len(_bad)); [print('  · ' + b) for b in _bad]
except Exception as _e: print('住处检查没跑成', _e)
sys.exit(1 if E else 0)

