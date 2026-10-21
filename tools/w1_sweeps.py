#!/usr/bin/env python3
"""第 1 波的“同类全站扫”：每修一类错，就把同一类在全站扫一遍，数字写进报告、拿不准的列清单（不改数据，只读）。
用法：python3 tools/w1_sweeps.py [站目录]    输出 build/w1/sweeps.json 和摘要"""
import glob, json, math, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, 'tools')); sys.path.insert(0, os.path.join(ROOT, 'tests'))
import w1_checks as W, geo_prov
site = sys.argv[1] if len(sys.argv) > 1 else 'build/site_w1'
X = W.load_all(site); IT, geo = X['IT'], X['geo']; out = {}


def vm(s):
    h = re.search(r'(\d+) 小时', s or ''); m = re.search(r'(\d+) 分', s or '')
    return (int(h.group(1)) * 60 if h else 0) + (int(m.group(1)) if m else 0)


# 1 徒步段（步行 ≥60 分钟的一段）：导航按钮 / “导航这一天”改走步行模式；这里数有多少天、多少线涉及
walk = [(rid, di + 1, s['name'], s['via']) for rid, it in IT.items() for di, d in enumerate(it['days']) for s in d['stops'] if (s.get('via') or '').startswith(('步行', '徒步')) and vm(s['via']) >= 60]
out['walk_legs_ge60'] = dict(n=len(walk), routes=len({x[0] for x in walk}), sample=walk[:12])
# 2 餐食只出自别的省（旧 routes.js 与新的对比）
cf = json.load(open('data/catalog/city_food.json', encoding='utf-8')); dp = geo_prov.dish_provs()
def meals(path):
    R = json.loads(re.search(r'window.ZOUNI_ROUTES=(.*);\n', open(path, encoding='utf-8').read()).group(1))
    return W.check_meals(R, IT, X['DM'], geo_prov.prov_of, dp, cf)
out['meals_before'] = len(meals('build/bak_w1/routes.js')); mb = meals('build/routes.js'); out['meals_after'] = len(mb); out['meals_after_list'] = [str(x) for x in mb[:30]]
# 3 站点坐标离当天城市中心过远（非长线、国内、≥150 公里；只列单，不改）
far = []
DM = X['DM']
for rid, it in IT.items():
    if len(it['days']) >= 15 or it['dest'] not in DM: continue
    for di, d in enumerate(it['days']):
        c = d.get('city', it['city']); cc = geo.get(c + '|' + c)
        if not cc or cc.get('lat') is None: continue
        for s in d['stops']:
            g = geo.get(c + '|' + (s.get('q') or s['name']))
            if g and g.get('lat') is not None:
                k = W.km((g['lat'], g['lng']), (cc['lat'], cc['lng']))
                if k >= 150 and not re.search(r'(自驾|包车|高铁|火车|飞机|动车)', s.get('via') or ''): far.append((rid, di + 1, c, s['name'], round(k)))
out['far_stop_nonlong'] = dict(n=len(far), sample=far[:25])
rj = [l for l in open('build/w1/coord_rejects.txt', encoding='utf-8').read().splitlines() if l.strip()] if os.path.exists('build/w1/coord_rejects.txt') else []
out['coord_fallback_rejected'] = dict(n=len(rj), sample=rj[:20])
# 4 酒店：携程“关键词搜”出的 top 推荐没有按片区核对过的条数（只有 top、没有三档）
H = json.load(open('data/hotels/ctrip_hotels.json', encoding='utf-8')); topo = [k for k, v in H.items() if v.get('top') and not (v.get('lux') or v.get('mid') or v.get('eco'))]
out['hotel_top_only_unverified_area'] = dict(n=len(topo), total=len(H), sample=topo[:20])
# 5 “相传”：medium 且已有出处词的（规则改后不再加“相传”）
n5 = 0
for f in glob.glob('data/history/*.json'):
    try: h = json.load(open(f, encoding='utf-8'))
    except Exception: continue
    for k, v in (h.get('notes') or {}).items():
        if v.get('conf') == 'medium' and '相传' not in v.get('line', '') and re.search(r'传记|史载|据载|据年谱|据[^，。；]{0,8}(简介|介绍)|学界|一般认为|传统上', v.get('line', '')): n5 += 1
out['xiangchuan_dropped_notes'] = n5
# 6 季节句子包装数
pages = X['pages']; mw = sum(h.count('class="mw') for h in pages.values()); sw = sum(h.count('class="sw"') + h.count(' sw"') for h in pages.values())
out['season_spans'] = dict(mw_sentences=mw, sw_sentences=sw, pages_with_swarn=sum('class="swarn"' in h for h in pages.values()), pages_with_mw=sum('class="mw' in h for h in pages.values()), pages_with_sw=sum('class="sw"' in h or 'mw sw' in h for h in pages.values()))
# 7 机场模板
b, tpl = W.check_air(IT, X['ASIA']); out['air_template'] = dict(days=len(tpl), routes=len({x[0] for x in tpl}))
# 8 自驾线最后一天正文里写“开车约 N 小时”但没算进当天路上（home_via 之后）
pd = {rid: W.page_days(h) for rid, h in pages.items()}; out['drive_text_mismatch'] = [str(x) for x in W.check_drive(pd)]
json.dump(out, open('build/w1/sweeps.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
for k, v in out.items(): print(k, '→', json.dumps(v, ensure_ascii=False)[:300])
