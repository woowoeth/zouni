import json, re, math, time, urllib.parse, urllib.request, statistics
geo=json.load(open('data/geo/places.json')); pr=json.load(open('data/geo/place_routes.json'))
src=open('tools/export_v2.js',encoding='utf-8').read()
LL={m.group(1):(float(m.group(2)),float(m.group(3))) for m in re.finditer(r"'([^']+)':\s*\[([\d.]+),\s*([\d.]+)\]",src)}
UA={'User-Agent':'zouni-travel-data/1.0 (zouni.app)'}
def q(text, cc='cn,hk,mo'):
    u='https://nominatim.openstreetmap.org/search?'+urllib.parse.urlencode({'q':text,'format':'json','limit':1,'countrycodes':cc,'accept-language':'zh'})
    r=json.loads(urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=20).read()); time.sleep(1.1)
    return (float(r[0]['lat']),float(r[0]['lon']),r[0]['display_name'][:60]) if r else None
REQ={'三亚湾':('三亚湾 三亚市','cn'),'黄龙':('黄龙风景名胜区 松潘县','cn'),'室韦':('室韦俄罗斯族民族乡','cn'),'黑山头':('黑山头镇 额尔古纳','cn'),
     '大峡谷':('派镇 米林','cn'),'大阪':('大阪市','jp'),'关西机场':('関西国際空港','jp')}
out={}; log=[]
for n,(text,cc) in REQ.items():
    r=q(text,cc); log.append((n,text,r))
    if r: out[n]={'lat':r[0],'lng':r[1],'src':'nominatim:'+text,'name':r[2]}
for n in pr:
    if n in out: continue
    if n in LL: out[n]={'lat':LL[n][0],'lng':LL[n][1],'src':'curated'}; continue
for n in pr:
    if n in out: continue
    cands=geo.get(n) or []
    # 同线路其他地点的中位位置，用来挑最近的候选
    pts=[(out[m]['lat'],out[m]['lng']) for r in pr[n] for m,v in pr.items() if r in v and m in out]
    if pts and cands:
        clat=statistics.median(p[0] for p in pts); clng=statistics.median(p[1] for p in pts)
        best=min(cands,key=lambda c:(c['lat']-clat)**2+(c['lng']-clng)**2)
    else: best=cands[0] if cands else None
    if best: out[n]={'lat':best['lat'],'lng':best['lng'],'src':'nominatim','name':best['name']}
json.dump(out,open('data/geo/places.resolved.json','w'),ensure_ascii=False,indent=1)
for x in log: print('重查', x)
print('坐标', len(out), '/', len(pr))
