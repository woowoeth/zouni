# 海拔：Open-Meteo elevation；往年气温：Open-Meteo 历史数据 2016–2025 按月平均（缓存，可断点续跑）
import json, time, urllib.parse, urllib.request, os, statistics
P='data/geo/places.resolved.json'; geo=json.load(open(P))
UA={'User-Agent':'zouni-travel-data/1.0 (zouni.app)'}
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read())
if '室韦' in geo and geo['室韦'].get('src','').startswith('nominatim') and abs(geo['室韦']['lat']-51.3)>2:
    for text in ['室韦 额尔古纳','Shiwei, Ergun']:
        r=get('https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':text,'format':'json','limit':1,'countrycodes':'cn'})); time.sleep(1.1)
        if r: geo['室韦']={'lat':float(r[0]['lat']),'lng':float(r[0]['lon']),'src':'nominatim:'+text,'name':r[0]['display_name'][:60]}; break
    else: geo['室韦']={'lat':51.32,'lng':119.9,'src':'curated-approx'}
names=sorted(geo)
need=[n for n in names if 'elev' not in geo[n]]
for i in range(0,len(need),80):
    chunk=need[i:i+80]
    r=get('https://api.open-meteo.com/v1/elevation?'+urllib.parse.urlencode({'latitude':','.join(str(round(geo[n]['lat'],4)) for n in chunk),'longitude':','.join(str(round(geo[n]['lng'],4)) for n in chunk)}))
    for n,e in zip(chunk,r['elevation']): geo[n]['elev']=round(e)
json.dump(geo,open(P,'w'),ensure_ascii=False,indent=1)
t0=time.time()
for n in names:
    if 'clim' in geo[n]: continue
    if time.time()-t0>230: print('时间到，下次接着跑'); break
    u='https://archive-api.open-meteo.com/v1/archive?'+urllib.parse.urlencode({'latitude':round(geo[n]['lat'],4),'longitude':round(geo[n]['lng'],4),
       'start_date':'2016-01-01','end_date':'2025-12-31','daily':'temperature_2m_max,temperature_2m_min','timezone':'Asia/Shanghai'})
    try: r=get(u)
    except Exception as e: print('  失败',n,e); time.sleep(2); continue
    d=r['daily']; acc={m:([],[]) for m in range(1,13)}
    for day,mx,mn in zip(d['time'],d['temperature_2m_max'],d['temperature_2m_min']):
        if mx is None or mn is None: continue
        m=int(day[5:7]); acc[m][0].append(mx); acc[m][1].append(mn)
    geo[n]['clim']={str(m):[round(statistics.mean(a)),round(statistics.mean(b))] for m,(a,b) in acc.items() if a}
    json.dump(geo,open(P,'w'),ensure_ascii=False,indent=1)
done=sum(1 for n in names if 'clim' in geo[n])
print('海拔', sum(1 for n in names if 'elev' in geo[n]), '气温', done, '/', len(names))
for n in ['拉萨','纳木错','日喀则','羊卓雍错','北京','喀纳斯','室韦']:
    g=geo.get(n); print(n, g and (g.get('elev'), (g.get('clim') or {}).get('10')))
