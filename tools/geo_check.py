import json, glob, math, re
geo=json.load(open('data/geo/places.json'))
def clean(n):
    n=re.split(r'\s*·\s*', n or '')[0].strip()
    return re.sub(r'(住这|连住|返回)$','',n).strip()
def dist(a,b):
    R=6371; p1,p2=math.radians(a['lat']),math.radians(b['lat']); dl=math.radians(b['lng']-a['lng']); dp=p2-p1
    h=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2; return 2*R*math.asin(math.sqrt(h))
flags=[]
for f in sorted(glob.glob('data/routes/*.json')):
    if f.endswith('_coverage.json') or f.endswith('.gold.json'): continue
    r=json.load(open(f)); prev=None
    for d in r['days']:
        n=clean(d.get('place')); g=(geo.get(n) or [None])[0]
        if prev and g:
            km=dist(prev[1],g)
            if km>700: flags.append((r['id'],prev[0],n,int(km)))
        if g: prev=(n,g)
for x in flags: print('  可疑', x)
print('可疑段数', len(flags))
for n in ['拉萨','纳木错','日喀则','佐敦','日隆','双廊','黑马河','乌尔禾','富蕴']:
    g=(geo.get(n) or [None])[0]; print(n, g and (round(g['lat'],2), round(g['lng'],2), g['name'][:40]))
