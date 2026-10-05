# 目的地总表 + 坐标气温 → 画布 atlas.js
import json, sys
OUT=sys.argv[1] if len(sys.argv)>1 else 'build/atlas.js'
D=json.load(open('data/destinations.json')); G=json.load(open('data/geo/destinations.json'))
REG={'domestic':['华北','东北','华东','华中','华南','西南','西北','港澳台'],'asia':['东亚','东南亚','南亚','西亚','中亚']}
import re
MAINR=[]
src=open('/mnt/user-data/outputs/artifacts/ae0eaca9-396f-4c49-8bc9-27accd93eca5/project/Main.dc.html',encoding='utf-8').read()
blk=src[src.index('var R = ['):src.index('];',src.index('var R = ['))]
for m in re.finditer(r"\{ id: '([^']+)', reg: '([^']+)', name: '([^']+)', days: (\d+)(.*?)\}(?=,\n|\n)", blk, re.S):
    rid,reg,name,days,rest=m.groups(); g=lambda k: (re.search(k+r": '([^']+)'",rest) or [None,''])[1]
    MAINR.append({'id':rid,'name':name,'days':int(days),'price':g('price'),'feel':g('feel'),'href':g('href'),'blocked':'blocked: true' in rest})
MAP={'xz7':'xizang','njg8':'xinjiang','nm4':'neimenggu','jz4':'sichuan','bj4':'beijing','sc5':'sichuan','xj10':'xinjiang','cd3':'sichuan','sh3':'shanghai','hz3':'zhejiang','sz3':'jiangsu','zjj4':'hunan','hk2':'hongkong','kansai4':'japan','hs2':'anhui','tj2':'tianjin','cb4':'hebei','sx4':'shanxi','aes4':'neimenggu','dl3':'liaoning','cbs3':'jilin','hrb3':'heilongjiang','nj3':'jiangsu','xm4':'fujian','wy3':'jiangxi','qd3':'shandong','ly3':'henan','es4':'hubei','gz3':'guangdong','gl4':'guangxi','sy4':'hainan','cq3':'chongqing','qdn5':'guizhou','dali5':'yunnan','tc4':'yunnan','xa3':'shaanxi','dh4':'gansu','qh5':'qinghai','nx3':'ningxia','mo2':'macau','tw5':'taiwan','hkd5':'japan','tk4':'japan','kr4':'korea','mn5':'mongolia','cm5':'thailand','vn5':'vietnam','sg3':'singapore','pg4':'malaysia','bali5':'indonesia','sr4':'cambodia','lpb4':'laos','plw5':'philippines','np8':'nepal','bt6':'bhutan','in7':'india','mv5':'maldives','uz6':'uzbekistan','tr6':'turkey','ae4':'uae'}
PAGES={'xz7':'Plan.dc.html','cd3':'Route.dc.html#cd3','xj10':'Route.dc.html#xj10','nm4':'Route.dc.html#nm4','jz4':'Route.dc.html#jz4','sh3':'Route.dc.html#sh3','hz3':'Route.dc.html#hz3','sz3':'Route.dc.html#sz3','zjj4':'Route.dc.html#zjj4','hk2':'Route.dc.html#hk2','kansai4':'Route.dc.html#kansai4'}
def trips_of(did):
    return [{'name':t['name'],'days':t['days'],'price':t['price'],'feel':t['feel'],'href':PAGES.get(t['id'],''),'blocked':t['blocked']} for t in MAINR if MAP.get(t['id'])==did]
def item(x):
    g=G.get(x['id'],{})
    return {'id':x['id'],'name':x['name'],'region':x['region'],'base':x['base'],'best':x['best'],'days':x['days'],'see':x['see'],'eat':x['eat'],
            'entry':x.get('visa') or x.get('entry') or '','tip':x.get('tip',''),'routes':len(x.get('routes',[])),'page':x.get('page',''),'noTrip':bool(x.get('noTrip')),
            'elev':g.get('elev'),'clim':g.get('clim',{}),'trips':trips_of(x['id']),'lat':round(g.get('lat',0),2),'lng':round(g.get('lng',0),2),'entryHK':x.get('visaHK') or x.get('entryHK') or ''}
A={'regions':REG,'domestic':[item(x) for x in D['domestic']],'asia':[item(x) for x in D['asia']]}
js='window.ZOUNI_ATLAS='+json.dumps(A,ensure_ascii=False,separators=(',',':'))+';\n'
open(OUT,'w',encoding='utf-8').write(js)
print('本期线路',len(MAINR),'对上目的地',sum(1 for t in MAINR if MAP.get(t['id']))); print('atlas.js',len(js)//1024,'KB','国内',len(A['domestic']),'亚洲',len(A['asia']),'有完整行程',sum(1 for x in A['domestic']+A['asia'] if x['page']),'有路线',sum(1 for x in A['domestic']+A['asia'] if x['routes']))
