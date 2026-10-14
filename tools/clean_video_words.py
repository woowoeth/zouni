# 路线文字里不要出现“视频/博主”这类来源措辞：先按固定改写，剩下的只报告，手工处理
import json, re, sys
RW = [('，视频里车辆已不让开到湖边', '，车辆已不让开到湖边'),
      ('视频里赶上阴雨，山完全被云盖住，没看到雪山，天气好再来。', '阴雨天山会被云盖住，看不到雪山，天气好再来。'),
      ('视频里在湖边露营看星空', '可以在湖边露营看星空'),
      ('视频里走上去要几个小时，建议坐索道', '走上去要几个小时，建议坐索道'),
      ('视频里全程走上去要几个小时，建议坐索道', '全程走上去要几个小时，建议坐索道'),
      ('视频里就遇到暴雨塌方', '就曾遇到暴雨塌方'),
      ('视频里的路段有人爆胎', '这些路段常有人爆胎'),
      ('视频后半段是另一条线路，这里只写到莲宝叶则', '后面是另一条线路，这里只写到莲宝叶则'),
      ('视频里阴雨，山被云遮住', '阴雨天山会被云遮住')]
RW += [('视频过了德格就进西藏', '过了德格就进西藏'),
       ('，视频拍在春节后几天（正月初三前后），所以出发写 2 月 8 日', '，出发日写在正月初三前后（2 月 8 日）'),
       ('，视频里也是找代驾', '，找代驾')]
DROP_START = re.compile(r'^视频(的)?(后半段|后面|是|只|拍|里是)')
def clean(s):
    for a, b in RW: s = s.replace(a, b)
    if '视频' in s:
        parts = s.split('；')
        keep = [x for x in parts if not DROP_START.match(x.strip()) and not re.search(r'视频(只讲|拍|后半段|后面)', x)]
        if keep != parts: s = '；'.join(keep) if keep else ''
        s = s.replace('视频里的', '').replace('视频里', '')
    return s
def walk(o):
    if isinstance(o, str): return clean(o)
    if isinstance(o, list): return [y for y in (walk(x) for x in o) if y != '']
    if isinstance(o, dict): return {k: walk(v) for k, v in o.items()}
    return o
if __name__ == '__main__':
    PAT = re.compile(r'视频|博主(?!峰)|Roc|UP主|up主|字幕')
    f = 'data/itineraries.json'; J = json.load(open(f, encoding='utf-8'))
    for rid, r in J['itineraries'].items():
        if rid.startswith('xv') or rid == 'hx7v': J['itineraries'][rid] = walk(r)
    json.dump(J, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for g in sys.argv[1:]:
        a = json.load(open(g, encoding='utf-8')); json.dump(walk(a), open(g, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    bad = 0
    for rid, r in J['itineraries'].items():
        if rid.startswith('xv') or rid == 'hx7v':
            h = sorted(set(PAT.findall(json.dumps(r, ensure_ascii=False))))
            if h: bad += 1; print('仍有', rid, r['label'], h)
    print('剩余有措辞的路线', bad)
