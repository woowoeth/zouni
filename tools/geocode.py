# 给每条线路每天住的地方补坐标：OpenStreetMap Nominatim，1 次/秒，结果缓存
import json, glob, time, re, urllib.parse, urllib.request, os, sys
CACHE='data/geo/places.json'
cache=json.load(open(CACHE)) if os.path.exists(CACHE) else {}
def clean(n):
    n=re.split(r'\s*·\s*', n or '')[0].strip()
    return re.sub(r'(住这|连住|返回)$','',n).strip()
names={}
for f in sorted(glob.glob('data/routes/*.json')):
    if f.endswith('_coverage.json') or f.endswith('.gold.json'): continue
    r=json.load(open(f))
    for d in r['days']:
        c=clean(d.get('place'))
        if c: names.setdefault(c,set()).add(r['id'])
print('地名', len(names))
UA={'User-Agent':'zouni-travel-data/1.0 (zouni.app)'}
for n in sorted(names):
    if n in cache: continue
    q=urllib.parse.urlencode({'q':n,'format':'json','limit':3,'countrycodes':'cn,hk,mo','accept-language':'zh'})
    try:
        res=json.loads(urllib.request.urlopen(urllib.request.Request('https://nominatim.openstreetmap.org/search?'+q,headers=UA),timeout=20).read())
    except Exception as e:
        res=[]; print('  失败',n,e)
    cache[n]=[{'lat':float(x['lat']),'lng':float(x['lon']),'name':x.get('display_name','')[:80],'type':x.get('type')} for x in res]
    json.dump(cache,open(CACHE,'w'),ensure_ascii=False,indent=1)
    time.sleep(1.1)
miss=[n for n in names if not cache.get(n)]
print('有坐标', len(names)-len(miss), '没找到', miss)
json.dump({n:sorted(v) for n,v in names.items()},open('data/geo/place_routes.json','w'),ensure_ascii=False,indent=1)
