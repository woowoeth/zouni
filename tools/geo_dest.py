# 目的地落脚城市：坐标（Nominatim）、海拔、十年月平均气温（Open-Meteo），缓存可续跑
import json, time, urllib.parse, urllib.request, statistics, os, sys
D=json.load(open('data/destinations.json')); P='data/geo/destinations.json'
geo=json.load(open(P)) if os.path.exists(P) else {}
UA={'User-Agent':'zouni-travel-data/1.0 (zouni.app)'}
get=lambda u: json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=60).read())
items=[(x,'cn') for x in D['domestic']]+[(x,x['cc']) for x in D['asia']]
t0=time.time()
for x,cc in items:
    g=geo.get(x['id'],{})
    if 'lat' not in g:
        ccode={'cn':'cn,hk,mo','tw':'tw'}.get(cc,cc)
        if x['id']=='taiwan': ccode='tw'
        r=get('https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':x['q'],'format':'json','limit':1,'countrycodes':ccode,'accept-language':'zh'})); time.sleep(1.1)
        if r: g.update(lat=float(r[0]['lat']),lng=float(r[0]['lon']),name=r[0]['display_name'][:50])
    if 'lat' in g and 'clim' not in g and time.time()-t0<230:
        try:
            g['elev']=round(get('https://api.open-meteo.com/v1/elevation?latitude=%s&longitude=%s'%(round(g['lat'],3),round(g['lng'],3)))['elevation'][0])
            d=get('https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode({'latitude':round(g['lat'],3),'longitude':round(g['lng'],3),'start_date':'2016-01-01','end_date':'2025-12-31','daily':'temperature_2m_max,temperature_2m_min','timezone':'auto'}))['daily']
            acc={}
            for t,a,b in zip(d['time'],d['temperature_2m_max'],d['temperature_2m_min']):
                if a is None or b is None: continue
                acc.setdefault(int(t[5:7]),([],[])); acc[int(t[5:7])][0].append(a); acc[int(t[5:7])][1].append(b)
            g['clim']={str(m):[round(statistics.mean(a)),round(statistics.mean(b))] for m,(a,b) in acc.items()}
        except Exception as e: print('  失败', x['id'], e)
    geo[x['id']]=g
    json.dump(geo,open(P,'w'),ensure_ascii=False,indent=1)
done=sum(1 for v in geo.values() if 'clim' in v)
print('坐标', sum(1 for v in geo.values() if 'lat' in v), '气温', done, '/', len(items))
for k in ['tianjin','harbin' if 'harbin' in geo else 'heilongjiang','taiwan','japan','uae','nepal','mongolia']:
    v=geo.get(k,{}); print(k, v.get('name','')[:30], v.get('elev'), (v.get('clim') or {}).get('1'), (v.get('clim') or {}).get('7'))
