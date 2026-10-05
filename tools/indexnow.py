# 把站点地图里的网址提交给 IndexNow（必应等）
import json, re, sys, urllib.request
out = sys.argv[1] if len(sys.argv) > 1 else 'out'
key = '9d9f5f79ba69da27e840e85bca1c3556'
urls = re.findall(r'<loc>(.*?)</loc>', open(out + '/sitemap.xml', encoding='utf-8').read())
req = urllib.request.Request('https://api.indexnow.org/indexnow', data=json.dumps({'host': 'zouni.app', 'key': key, 'keyLocation': f'https://zouni.app/{key}.txt', 'urlList': urls}).encode(), headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
try: print('IndexNow', len(urls), urllib.request.urlopen(req, timeout=30).status)
except Exception as e: print('IndexNow', e)
