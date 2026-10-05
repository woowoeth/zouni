# 目录 → 画布 catalog.js：一份数据，派生出“去哪儿”和“本期”两种视图
import json, re, sys, datetime, subprocess
OUT=sys.argv[1] if len(sys.argv)>1 else 'build/catalog.js'
# 1 先由旧格式重建结构化目的地（保持一处维护：data/destinations.json + data/geo/destinations.json）
D0=json.load(open('data/destinations.json')); G=json.load(open('data/geo/destinations.json')); TR=json.load(open('data/catalog/trips.json'))
KIND={'beijing':'municipality','tianjin':'municipality','shanghai':'municipality','chongqing':'municipality','neimenggu':'autonomous','guangxi':'autonomous','xizang':'autonomous','ningxia':'autonomous','xinjiang':'autonomous','hongkong':'sar','macau':'sar'}
def days(s):
    m=re.findall(r'\d+',s or ''); return {'min':int(m[0]),'max':int(m[-1])} if m else None
T=TR['trips']; DEST=[]
for scope in ('domestic','asia'):
    for x in D0[scope]:
        g=G.get(x['id'],{})
        DEST.append({'id':x['id'],'name':x['name'],'scope':scope,'kind':'country' if scope=='asia' else KIND.get(x['id'],'province'),'region':x['region'],
          'base':{'name':x['base'],'lat':round(g.get('lat',0),3),'lng':round(g.get('lng',0),3),'elev':g.get('elev'),'geoSource':g.get('src','nominatim')},
          'months':{'best':sorted(x['best'])},'days':days(x['days']),'see':x['see'],'eat':x['eat'],
          'entry':x.get('visa') or x.get('entry') or None,
          'tip':x.get('tip') or None,'status':'blocked' if x.get('noTrip') else 'ok',
          'climate':{m:g['clim'][m] for m in sorted(g.get('clim',{}),key=int)},
          'trips':[t['id'] for t in T if t['dest']==x['id']],'engineRoutes':x.get('routes',[]),'page':x.get('page') or None})
json.dump({'version':TR['version'],'climateSource':'Open-Meteo 2016–2025 月平均最高/最低气温','destinations':DEST},open('data/catalog/destinations.json','w'),ensure_ascii=False,indent=1)
# 2 优质景点（5A ∪ 世界遗产）挂到省级目的地
QL={}
try:
    for q in json.load(open('data/catalog/cn_quality.json'))['items']:
        QL.setdefault(q['prov'],[]).append(q)
except FileNotFoundError: pass
def quality_of(d):
    xs=QL.get(d['name'],[]) if d['scope']=='domestic' else []
    xs=sorted(xs,key=lambda q:(0 if '世界遗产' in q['tags'] else 1, 0 if q.get('covered') else 1, q['short']))
    return [{'n':q['short'],'w':'世界遗产' in q['tags'],'a':'5A' in q['tags'],'c':bool(q.get('covered'))} for q in xs]
# 2 派生：去哪儿
REG={'domestic':['华北','东北','华东','华中','华南','西南','西北','港澳台'],'asia':['东亚','东南亚','南亚','西亚','中亚']}
fmt=lambda p: '¥{:,}–{:,}'.format(p['lo'],p['hi']) if p.get('lo') else '另算'
def trip_card(t): return {'name':t['name'],'days':t['days'],'price':fmt(t['price']),'feel':' · '.join(t['tags']),'href':t['page'] or '','blocked':t['status']=='blocked'}
ATLAS={'regions':REG,'domestic':[],'asia':[]}
for d in DEST:
    ATLAS[d['scope']].append({'id':d['id'],'name':d['name'],'region':d['region'],'base':d['base']['name'],'best':d['months']['best'],
      'days':(f"{d['days']['min']} 天" if d['days'] and d['days']['min']==d['days']['max'] else (f"{d['days']['min']}–{d['days']['max']} 天" if d['days'] else '—')),
      'see':d['see'],'eat':d['eat'],'entry':d['entry'] or '','tip':d['tip'] or '',
      'routes':len(d['engineRoutes']),'page':d['page'] or '','noTrip':d['status']=='blocked','elev':d['base']['elev'],'clim':d['climate'],
      'lat':d['base']['lat'],'lng':d['base']['lng'],'trips':[trip_card(t) for t in T if t['dest']==d['id']],'quality':quality_of(d)})
# 3 派生：本期（日期 → 相对本期起点的天数）
base=datetime.date.fromisoformat(TR['issueBase'])
def off(mmdd):
    m,dd=map(int,mmdd.split('-')); dt=datetime.date(2026 if m>=base.month-1 else 2027,m,dd); return (dt-base).days
MAIN=[]
for t in T:
    r={'id':t['id'],'reg':t['region'],'name':t['name'],'days':t['days'],'title':t['title'],'ctitle':t['headline'],'dek':t['dek'],'price':fmt(t['price']),'feel':' · '.join(t['tags'])}
    if t['why']: r['why']=t['why']
    if t['anytime']: r.update(always=True,ws=0,we=75,ps=0,pe=75)
    else: r.update(ws=off(t['season']['ok'][0]),we=off(t['season']['ok'][1]),ps=off(t['season']['best'][0]),pe=off(t['season']['best'][1]))
    if t['page']: r.update(linked=True,href=t['page'])
    if t['status']=='blocked': r['blocked']=True
    MAIN.append(r)
CAT={'version':TR['version'],'destinations':DEST,'trips':T}
js=('window.ZOUNI_CATALOG='+json.dumps(CAT,ensure_ascii=False,separators=(',',':'))+';\n'
    +'window.ZOUNI_ATLAS='+json.dumps(ATLAS,ensure_ascii=False,separators=(',',':'))+';\n'
    +'window.ZOUNI_MAIN_R='+json.dumps(MAIN,ensure_ascii=False,separators=(',',':'))+';\n')
open(OUT,'w',encoding='utf-8').write(js)
print('catalog.js',len(js)//1024,'KB · 目的地',len(DEST),'· 线路',len(T))
