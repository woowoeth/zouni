#!/usr/bin/env python3
"""静态终检：id 完整性 / 残词 / 假按钮 / 重复绑定 / 老内核语法 / 卡片价格一致性"""
import re, sys
html=open(__import__('os').path.dirname(__file__)+'/../src/index.html',encoding='utf-8').read()
js=re.search(r'<script>(.*?)</script>',html,re.S).group(1)
bad=0
def chk(name,ok,detail=''):
    global bad
    print(('✓' if ok else '✗'),name,('' if ok else '→ '+str(detail)))
    bad += (0 if ok else 1)
# 1. id 完整性
js_ids=set(re.findall(r"\$\('([^']+)'\)",js))
html_ids=set(re.findall(r' id="([^"]+)"',html))
dyn={'btn-reopen','btn-wucai','btn-baihaba','mk-wucai','mk-baihaba','btn-draw'}
miss=js_ids-html_ids-dyn
chk('DOM id 零缺失', not miss, sorted(miss))
# 2. 残词（黑话/占位/死引用）
banned=['《国地》','正在做','即将上线','PERSONS','openCreateView','TODO','FIXME','占位符']
hits=[w for w in banned if w in html]
chk('残词零命中', not hits, hits)
# 3. 假按钮（纯 toast 无动作）
fakes=re.findall(r"addEventListener\('click',\(\)=>toast\(",js)
chk('纯 toast 假按钮为零', not fakes, len(fakes))
# 4. 重复绑定
dups=[w for w in ['tab-bar','trips-list','search-results','sc-days-grid','search-chips','cr-']
      if js.count(f"getElementById('{w}').addEventListener")>1]
chk('监听零重复绑定', not dups, dups)
# 5. 老内核红线：?. ?? replaceAll flat at(
syn=[w for w in ['?.','??','replaceAll','.flatMap','.at('] if w in js]
chk('老内核语法零残留（微信 X5）', not syn, syn)
# 6. rec 卡价格 = 对应路线精打档
ok_price=True; detail=[]
for rid,seg in re.findall(r'data-rec="(\w+)"(.*?)</button>',html,re.S):
    m=re.search(r'¥([\d,]+)\s*起',seg)
    if not m: continue
    shown=int(m.group(1).replace(',',''))
    key={'xj':'xj8','qg':'qg7','cx':'cx4'}.get(rid,rid)
    rm=re.search(key+r":(?:Object\.assign\([^,]+,)?\{.*?budgets:\[\{l:'宽松',v:(\d+)\},\{l:'精打细算',v:(\d+)\}",html,re.S)
    if rm and shown!=int(rm.group(2)):
        ok_price=False; detail.append(f"{rid}卡¥{shown}≠精打{rm.group(2)}")
chk('卡片价格与预算一致', ok_price, detail)
# 7. i18n 对账：en 覆盖 zh 全部键；data-i18n 引用键存在；?. 回归
zh_keys=set(re.findall(r"'([a-z][\w.]+)':'",js[js.index('var I18N'):js.index('I18N.zh.cards')]))
en_block=js[js.index("en:{",js.index('var I18N')):js.index('I18N.zh.cards')]
en_keys=set(re.findall(r"'([a-z][\w.]+)':'",en_block))
missing_en=zh_keys-en_keys
refs=set(re.findall(r'data-i18n(?:-ph)?="([^"]+)"',html))
dead_refs={r for r in refs if f"'{r}':" not in js}
chk('i18n：en 键齐全 / 引用键存在 / 无可选链', not missing_en and not dead_refs and '?.' not in js,
    {'en缺':sorted(missing_en)[:6],'死引用':sorted(dead_refs)[:6]})
# 8. 数据真实性：later 项文案不得承诺"可加/可排"（除非已标注 inDay 或改为 ins）
fake=[]
for m in re.finditer(r"later:\{([^}]+)\}", js):
    blk=m.group(1)
    nm=re.search(r"name:'([^']+)'",blk); why=re.search(r"why:'([^']+)'",blk)
    if not nm or not why: continue
    if re.search(r'可.{0,3}加|可排|能加|顺路|可插', why.group(1)) and 'inDay' not in blk:
        fake.append(nm.group(1))
chk('无"可加入"假承诺（承诺可加须有插入数据）', not fake, fake)
# 9. inserts 数据完整性：ins 引用必须有对应定义，且字段齐全
bad_ins=[]
for m in re.finditer(r"\{ins:'(\w+)'\}", js):
    key=m.group(1)
    d=re.search(r"\b"+key+r":\{day:\d+, *afterK:'[\w-]+', *label:'[^']+', *brief:'[^']+'", js)
    if not d: bad_ins.append(key)
chk('ins 引用均有完整插入定义', not bad_ins, bad_ins)
# 10. i18n 覆盖完整性：sheet/tab/按钮等可见中文文案必须挂 data-i18n
import html as _h
sheet_seg = html[html.index('id="sheet-body"'):html.index('id="view-home"')] if 'id="sheet-body"' in html else ''
untagged=[]
for m in re.finditer(r'<(button|div|span)([^>]*)>([^<>]*[\u4e00-\u9fa5][^<>]*)</\1>', sheet_seg):
    attrs, text = m.group(2), m.group(3).strip()
    if not text or 'data-i18n' in attrs or 'data-cng' in attrs: continue
    if re.search(r'\bid=', attrs): continue   # 带 id = JS 动态填充（已走 t()）
    if re.match(r'^[\d\s·¥$€]+$', text): continue
    untagged.append(text[:16])
chk('抽卡表单中文文案均已挂 data-i18n', not untagged, untagged)
# 11. 首页卡片必须指向真实线路 id（族名如 xj/cx/qg 不是 id，点了没反应）
card_ids=set(re.findall(r'data-rec="([\w-]+)"', html))
route_ids=set(re.findall(r'\n\s*(\w+):(?:normRoute\(|Object\.assign\(|\{name:)', js))
route_ids |= set(re.findall(r'ROUTES\.(\w+)\.dayVariants', js))
route_ids |= set(re.findall(r'\n\s*(\w+):Object\.assign\(\{\},ROUTES', js))
dangling=[c for c in card_ids if c not in route_ids]
chk('首页卡片均指向真实线路（非族名）', not dangling, dangling)
sys.exit(1 if bad else 0)
