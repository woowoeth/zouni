# 用法：python3 tools/add_video_routes.py 6 7 8 ...   把 build/video/route_<n>.json 入库（路线本身，不写来源）
# 流程：check_new_routes（id 重复以外的错必须为零）→ clean_video_words（“视频/博主”措辞改写，清不掉的拦下）→ data/auto_routes/video_<n>.json → add_routes_json
import json, sys, os, subprocess, re
sys.path.insert(0, 'tools')
from clean_video_words import walk
IT = json.load(open('data/itineraries.json', encoding='utf-8'))['itineraries']
PAT = re.compile(r'视频|博主(?!峰)|Roc|UP主|up主|字幕')
ok_n = []; bad = []
for n in [int(x) for x in sys.argv[1:]]:
    rp = f'build/video/route_{n}.json'
    if not os.path.exists(rp): bad.append((n, '文件不全')); continue
    o = subprocess.run(['python3', 'tools/check_new_routes.py', rp], capture_output=True, text=True).stdout
    errs = [l for l in o.splitlines() if l.startswith('    ') and 'id 重复' not in l]
    if errs: bad.append((n, '; '.join(e.strip() for e in errs[:6]))); continue
    rs = [walk(x) for x in json.load(open(rp, encoding='utf-8'))]
    h = sorted({m for r in rs for m in PAT.findall(json.dumps(r, ensure_ascii=False))})
    if h: bad.append((n, f'仍有来源措辞 {h}')); continue
    rs = [r for r in rs if r['id'] not in IT]
    if not rs: bad.append((n, 'id 已存在')); continue
    for r in rs: r.pop('video', None)
    json.dump(rs, open(f'data/auto_routes/video_{n}.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1); ok_n.append((n, rs))
if ok_n:
    out = subprocess.run(['python3', 'tools/add_routes_json.py'] + [f'data/auto_routes/video_{n}.json' for n, _ in ok_n], capture_output=True, text=True)
    print(out.stdout.strip().splitlines()[-1] if out.stdout.strip() else out.stderr[-300:])
    for n, rs in ok_n: print('第', n, '个：', ' / '.join(r['label'] for r in rs))
for n, why in bad: print('✗ 第', n, '个没入库：', why)
