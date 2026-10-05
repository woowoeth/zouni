# 自动加内容（在 GitHub Actions 里跑，用 GitHub Models 免费额度，不用外部 key）
# 用法：GITHUB_TOKEN=... python3 tools/auto_grow.py [每次条数，默认 3]
# 规矩：只写真实地名；不写史实故事；每个站点必须查得到坐标且在目标附近；查不到超过四分之一整条丢弃
import json, os, re, sys, time, math, urllib.request, urllib.parse, calendar

N_MAX = int(sys.argv[1]) if len(sys.argv) > 1 else 3
TOKEN = os.environ.get('GITHUB_TOKEN', '')
MODELS = ['openai/gpt-4.1-mini', 'openai/gpt-4o-mini', 'deepseek/DeepSeek-V3-0324']
UA = {'User-Agent': 'zouni-autogrow/1.0 (zouni.app)'}
IT_P, TR_P, NI_P, GEO_P, Q_P = 'data/itineraries.json', 'data/catalog/trips.json', 'data/catalog/niche.json', 'data/geo/pois.json', 'data/auto_queue.json'
D = json.load(open(IT_P)); I = D['itineraries']
T = json.load(open(TR_P)); NI = json.load(open(NI_P)); G = json.load(open(GEO_P))
CAT = {d['id']: d for d in json.load(open('data/catalog/destinations.json'))['destinations']}
CC = {x['id']: x['cc'] for x in json.load(open('data/destinations.json'))['asia']}
Q = json.load(open(Q_P)) if os.path.exists(Q_P) else {'cities': [], 'done': [], 'failed': []}
LOG = []


def km(a, b):
    r = math.pi / 180; dl = (b[1] - a[1]) * r; p1, p2 = a[0] * r, b[0] * r
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def nominatim(q, cc):
    u = 'https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': q, 'format': 'json', 'limit': 3, 'countrycodes': cc, 'accept-language': 'zh'})
    try: r = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    except Exception: r = []
    time.sleep(1.1)
    return r


def targets():
    """待办：开放的小众景点里还没有行程的 → 亚洲没有行程的国家 → 队列里的城市"""
    out = []
    for x in NI['items']:
        if x['status'] == 'open' and not x.get('trip') and x['id'] not in Q['done'] + Q['failed']:
            out.append({'key': x['id'], 'kind': 'niche', 'dest': x['dest'], 'name': x['name'], 'note': x['note'], 'lat': x['lat'], 'lng': x['lng']})
    have_dest = {t['dest'] for t in T['trips'] if t.get('page')}
    for d in CAT.values():
        if d['scope'] == 'asia' and d['id'] not in have_dest and d['id'] not in Q['done'] + Q['failed']:
            out.append({'key': d['id'], 'kind': 'asia', 'dest': d['id'], 'name': d['name'] + '（' + d['base']['name'] + '）', 'note': '看：' + '、'.join(d['see']), 'lat': d['base']['lat'], 'lng': d['base']['lng']})
    for c in Q['cities']:
        if c['key'] not in Q['done'] + Q['failed']: out.append(dict(c, kind='city'))
    return out


PROMPT = '''你是“走你”旅行网站的行程编辑。为下面这个目的地写一条 {days} 天的行程，只输出 JSON，不要任何别的字。
目的地：{name}（{prov}）。补充：{note}
要求：
1. 只用真实存在、能在地图上搜到的地名；不确定的地方不要写。
2. 不写历史典故、年份、数字类的“知识”；text 只写这天怎么走（一两句大白话）。
3. 每天 1–4 个站点，按顺序；type 只能是 sight / museum / street / park / food / night；dur 是停留分钟数（30–300）。
4. q 是地图搜索用的名字：国内写中文全称（带县市名更好），国外写英文。
5. 换城市的日子写 city（当天所在城市）；远的段落在站点里写 via，比如 "包车约 2 小时"、"高铁约 1 小时"。
6. prep 写 1–2 条出发前要办的事（预约、证件、季节），没有就空数组。
JSON 格式：{{"label":"X N 天","title":"N 天，……","prep":["…"],"days":[{{"title":"…","text":"…","stay":"住哪一片","stops":[{{"name":"…","q":"…","type":"sight","dur":120}}]}}]}}'''


ENDPOINTS = [('https://models.github.ai/inference/chat/completions', ['openai/gpt-4.1-mini', 'openai/gpt-4o-mini', 'deepseek/DeepSeek-V3-0324']),
             ('https://models.inference.ai.azure.com/chat/completions', ['gpt-4o-mini', 'DeepSeek-V3-0324'])]


def ask(prompt):
    for url, models in ENDPOINTS:
        for m in models:
            body = json.dumps({'model': m, 'messages': [{'role': 'user', 'content': prompt}], 'temperature': 0.3, 'max_tokens': 2200}).encode()
            req = urllib.request.Request(url, data=body, method='POST', headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json',
                                         'Accept': 'application/json', 'User-Agent': 'zouni-autogrow/1.0', 'X-GitHub-Api-Version': '2022-11-28'})
            raw = b''
            try:
                with urllib.request.urlopen(req, timeout=120) as x:
                    raw = x.read(); ct = x.headers.get('content-type'); code = x.status
                j = json.loads(raw)
                txt = j['choices'][0]['message']['content']
                txt = re.sub(r'^```(json)?|```$', '', txt.strip(), flags=re.M).strip()
                return json.loads(txt[txt.find('{'): txt.rfind('}') + 1]), m
            except urllib.error.HTTPError as e:
                LOG.append(f'模型 {m} @{url.split("/")[2]}：HTTP {e.code} {e.read()[:160]!r}')
            except Exception as e:
                LOG.append(f'模型 {m} @{url.split("/")[2]}：{str(e)[:60]}；返回 {raw[:160]!r}')
                try:
                    import subprocess
                    out = subprocess.run(['curl', '-sL', '--http2', '-X', 'POST', url, '-H', 'Authorization: Bearer ' + TOKEN, '-H', 'Content-Type: application/json',
                                          '-H', 'Accept: application/vnd.github+json', '-H', 'X-GitHub-Api-Version: 2022-11-28', '-d', body.decode()], capture_output=True, timeout=150).stdout
                    j = json.loads(out); txt = j['choices'][0]['message']['content']
                    txt = re.sub(r'^```(json)?|```$', '', txt.strip(), flags=re.M).strip()
                    return json.loads(txt[txt.find('{'): txt.rfind('}') + 1]), m + '（curl）'
                except Exception as e2:
                    LOG.append(f'  curl 也不行：{str(e2)[:60]}；返回 {out[:160] if "out" in dir() else b""!r}')
    return None, None


def validate(it, tg):
    """每个站点查坐标（离目标 300 公里内）；查不到的去掉，超过四分之一就整条不要"""
    cc = CC.get(tg['dest'], 'mo' if tg['dest'] == 'macau' else 'cn')
    base = (tg['lat'], tg['lng']); total = ok = 0
    if not isinstance(it.get('days'), list) or not (2 <= len(it['days']) <= 5): return False, '天数不对'
    for d in it['days']:
        keep = []
        for s in d.get('stops') or []:
            if s.get('type') not in ('sight', 'museum', 'street', 'park', 'food', 'night'): s['type'] = 'sight'
            s['dur'] = max(30, min(300, int(s.get('dur') or 90)))
            city = d.get('city') or tg['city']; key = city + '|' + (s.get('q') or s.get('name', ''))
            total += 1
            if not G.get(key):
                hit = None
                for q in (s.get('q'), s.get('name'), city + ' ' + (s.get('name') or '')):
                    if not q: continue
                    for r in nominatim(q, cc):
                        pt = (float(r['lat']), float(r['lon']))
                        if km(base, pt) <= 300: hit = {'lat': pt[0], 'lng': pt[1], 'hit': r['display_name'][:50], 'q': q, 'src': 'autogrow'}; break
                    if hit: break
                if hit: G[key] = hit
            if G.get(key): ok += 1; keep.append(s)
        d['stops'] = keep
        if not keep: return False, f'第“{d.get("title")}”天一个站点都查不到'
    if total == 0 or ok / total < 0.75: return False, f'站点只查到 {ok}/{total}'
    return True, f'站点查到 {ok}/{total}'


def main():
    if not TOKEN: print('没有 GITHUB_TOKEN，跳过'); return
    added = []
    for tg in targets()[:N_MAX]:
        d0 = CAT[tg['dest']]; tg['city'] = tg.get('city') or d0['base']['name']
        days = 3 if tg['kind'] != 'asia' else 4
        it, model = ask(PROMPT.format(days=days, name=tg['name'], prov=d0['name'], note=tg.get('note', '')))
        if not it: LOG.append(f'{tg["name"]}：模型这次没给出可用结果，下次再试'); continue
        good, why = validate(it, tg)
        if not good: Q['failed'].append(tg['key']); LOG.append(f'{tg["name"]}：不合格（{why}）'); continue
        rid = 'a' + re.sub(r'[^a-z0-9]', '', tg['key'].lower())[:10] + str(len(it['days']))
        I[rid] = {'dest': tg['dest'], 'city': tg['city'], 'label': it.get('label') or f'{tg["name"]} {len(it["days"])} 天', 'title': it.get('title') or tg['name'],
                  'kicker': ('小众 · ' if tg['kind'] == 'niche' else '') + f'{len(it["days"])} 天', 'start': [2026, max(0, (d0['months']['best'] or [10])[0] - 1), 10],
                  'prep': [p for p in (it.get('prep') or []) if isinstance(p, str)][:2], 'auto': model,
                  'days': [{'title': x.get('title', ''), 'text': x.get('text', ''), 'stops': x['stops'], **({'city': x['city']} if x.get('city') else {}), **({'stay': x['stay']} if x.get('stay') else {})} for x in it['days']]}
        ms = sorted(d0['months']['best']) or [10]
        a, b = ms[0], ms[-1]
        T['trips'].append({'id': rid, 'dest': tg['dest'], 'name': I[rid]['label'].rsplit(' ', 2)[0], 'region': d0['region'], 'days': len(it['days']), 'title': I[rid]['label'], 'headline': I[rid]['title'],
                           'dek': ' '.join(x['text'] for x in I[rid]['days'][:2])[:60], 'why': None, 'price': {'lo': None, 'hi': None, 'currency': 'CNY', 'basis': '待算'},
                           'tags': ['小众'] if tg['kind'] == 'niche' else [], 'season': {'ok': ['%02d-01' % a, '%02d-%02d' % (b, calendar.monthrange(2026, b)[1])], 'best': ['%02d-01' % a, '%02d-%02d' % (b, calendar.monthrange(2026, b)[1])]},
                           'anytime': False, 'status': 'ok', 'page': 'Route.dc.html#' + rid, 'engineRoute': None, 'poster': None, 'auto': True})
        for x in NI['items']:
            if x['id'] == tg['key']: x['trip'] = rid
        Q['done'].append(tg['key']); added.append(rid); LOG.append(f'{tg["name"]}：加了 {rid}（{why}，{model}）')
    json.dump(D, open(IT_P, 'w'), ensure_ascii=False, indent=1); json.dump(T, open(TR_P, 'w'), ensure_ascii=False, indent=1)
    json.dump(NI, open(NI_P, 'w'), ensure_ascii=False, indent=1); json.dump(G, open(GEO_P, 'w'), ensure_ascii=False, indent=1)
    json.dump(Q, open(Q_P, 'w'), ensure_ascii=False, indent=1)
    print('\n'.join(LOG)); print('本次新增', len(added), added)
    open(os.environ.get('GITHUB_STEP_SUMMARY', '/dev/null'), 'a').write('\n'.join(['## 本次自动新增'] + LOG) + '\n')


if __name__ == '__main__':
    main()
