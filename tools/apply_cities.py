# 把城市表合进线路：饭点按附近景点挑当地特色和店；有小吃街的那顿不另排；晚上出门补出发行；住宿填三档
import json, glob, re
cities=[json.load(open(f)) for f in glob.glob('data/cities/*.json')]
def key(n):
    n=re.split(r'\s*·\s*', n or '')[0].strip(); return re.sub(r'(住这|连住|返回)$','',n).strip()
def mins(t): h,m=t.split(':'); return int(h)*60+int(m)
def hm(v): return '%02d:%02d'%(v//60%24, v%60)
FOODY=re.compile(r'小吃|夜市|美食|吃')
GENERIC=re.compile(r'本地|连锁|随便|附近|不排队|简餐|打卡')
filled=dict(meals=0,stays=0,fun=0,days=0,skipped_meals=0)
for f in sorted(glob.glob('data/routes/*.json')):
    if '_coverage' in f or '.gold' in f: continue
    r=json.load(open(f)); touched=False; fun_used=set(); route_used={}
    selfdrive=(r.get('transport') or {}).get('mode')=='drive'; MODE='drive' if selfdrive else 'taxi'
    for di,d in enumerate(r['days']):
        tl0=d['timeline']
        for x in list(tl0):   # 午饭落在长途开车中间 → 路上吃
            if x['type']!='eat' or x.get('slot')!='午饭' or x.get('dish') not in ('待补',None): continue
            t=mins(x['t'])
            for y in tl0:
                if y['type']=='dep' and (y.get('min') or 0)>=120 and mins(y['t'])<t<mins(y['t'])+y['min']:
                    mid=mins(y['t'])+y['min']//2; x.update(t=hm(mid//15*15),dish='随意',place='路上找个镇子吃',price=None,in_drive=True); touched=True; break
        tl0.sort(key=lambda x:(x['t'] if re.match(r'^\d\d:\d\d$',x['t']) else '99'))
        c=next((c for c in cities if key(d.get('place')) in c['match']),None)
        if not c: continue
        filled['days']+=1; touched=True
        tl=d['timeline']
        # 引擎里的吃饭站（cat=food、又不是小吃街夜市）换成城市表里的店  MEALSTOP
        for x in list(tl):
            if x['type']=='see' and x.get('ticket')=='food' and not FOODY.search(x['name']):
                t=mins(x['t']); slot='午饭' if t<16*60 else '晚饭'
                if GENERIC.search(x['name']):
                    tl[tl.index(x)]={'t':x['t'],'type':'eat','slot':slot,'dish':'待补','place':'待补','price':None,'from_engine':x['name']}
                else:
                    parts=re.split(r'\s*·\s*',x['name'])
                    tl[tl.index(x)]={'t':x['t'],'type':'eat','slot':slot,'dish':parts[1] if len(parts)>1 else '本地菜','place':parts[0],'price':x.get('cost') or None,'poi':parts[0],'from_engine':x['name']}
                for y in list(tl):
                    if y['type']=='eat' and y is not x and y.get('slot')==slot and y.get('dish')=='待补' and not y.get('from_engine'): tl.remove(y)
        sees=[x for x in tl if x['type']=='see']
        used=set()
        for x in list(tl):
            if x['type']!='eat' or x.get('dish') not in ('待补',None): continue
            t=mins(x['t'])
            near=[s for s in sees if abs(mins(s['t'])-t)<=150]
            if x['slot']=='午饭' and any(FOODY.search(s['name']) for s in near):
                tl.remove(x); filled['skipped_meals']+=1; continue
            pool=[p for p in c['food'] if p['place'] not in used and (not p.get('close') or mins(p['close'])>=t+30) and (not p.get('slots') or x['slot'] in p['slots'])]
            if not pool:
                x.update(dish='随意',place='住的地方附近',price=None); continue
            pool_pref=[p for p in pool if any(k in s['name'] for s in near for k in p.get('near',[]))]
            pool=(pool_pref or pool or c['food'])
            pool=sorted(pool,key=lambda p:p['price']) if x['slot']=='午饭' else sorted(pool,key=lambda p:-p['price'])
            pool=sorted(pool,key=lambda q:route_used.get(q['place'],0))  # 先用这条线路还没去过的店
            p=pool[0]
            route_used[p['place']]=route_used.get(p['place'],0)+1
            used.add(p['place'])
            x.update(dish=p['dish'],place=p['place'],price=p['price'],poi=p['poi'],src=p['src'],priceText=p.get('priceText')); filled['meals']+=1
            if x['slot']=='晚饭' and any(y['type']=='dep' and y.get('to')=='住处' and mins(y['t'])<t for y in tl):
                for y in list(tl):
                    if y['type']=='dep' and y.get('to')=='住处' and t-60<=mins(y['t'])<=t: tl.remove(y)
                tl.append({'t':hm(t-20),'type':'dep','to':p['place'],'mode':MODE,'min':20})
                pass  # 回住处统一在体验之后补（RETURNFIX）
        dinner=next((x for x in tl if x['type']=='eat' and x['slot']=='晚饭'),None)
        longday=sum((y.get('min') or 0) for y in tl if y['type']=='dep' and y.get('mode')=='drive')>=360   # LONGDAY 长途那天晚上不加活动
        for e in c['fun']:
            if longday or e['name'] in fun_used or (dinner and '文化火锅' in (dinner.get('place') or '')): continue
            if any(x.get('poi')==e['poi'] for x in tl if x['type']=='eat'): continue
            if dinner and mins(e['t'])>=mins(dinner['t'])+75:
                fun_used.add(e['name'])
                tl.append({'t':hm(mins(e['t'])-20),'type':'dep','to':e['name'].split('（')[0],'mode':MODE,'min':20})
                tl.append({'t':e['t'],'type':'fun','name':e['name'],'detail':e['detail'],'poi':e['poi'],'src':e['src']})
                tl.append({'t':hm(mins(e['t'])+100),'type':'dep','to':'住处','mode':MODE,'min':20})
                filled['fun']+=1; break
        if dinner and any(y['type']=='dep' and y.get('to')==dinner.get('place') for y in tl) and not any(y['type']=='fun' for y in tl if y['t']>dinner['t']) and not any(y['type']=='dep' and y.get('to')=='住处' and y['t']>dinner['t'] for y in tl):
            tl.append({'t':hm(mins(dinner['t'])+70),'type':'dep','to':'住处','mode':MODE,'min':20})
        if c.get('stay'):
            d['stay']['tiers']=c['stay']; filled['stays']+=1
            first=next((c['stay'][k] for k in ('luxury','upscale','budget') if c['stay'].get(k)),None)
            for x in tl:
                if x['type']=='stay' and first: x['name']=first['name']
        d['experiences']=c['fun']
        tl.sort(key=lambda x:(x['t'] if re.match(r'^\d\d:\d\d$',x['t']) else '99'))
    if touched:
        r['status']['meals']='partial'; json.dump(r,open(f,'w'),ensure_ascii=False,indent=1)
print(filled)
cov=json.load(open('data/routes/_coverage.json')); cov.update(eatFilled=filled['meals'],stayFilled=filled['stays'],funAdded=filled['fun'],cityTables=[c['city'] for c in cities])
json.dump(cov,open('data/routes/_coverage.json','w'),ensure_ascii=False,indent=1)
