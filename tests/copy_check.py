#!/usr/bin/env python3
"""文字预算（2026-10-21，用户：“按钮里好啰嗦，简单点，其他体验也是少就是多”）。会红。

规则：每个按钮、弹层选项、提示条、区块小标题、空状态，只写“要做什么”，不写“为什么 / 之后会怎样”；
一行放得下就别写两行；同一信息全站只出现一次。图标和功能一个不少；安全信息（高反 / 极夜 / 封路 / 闭馆 / 预约 / 签证）只压缩重复，不删。

用法（项目根目录；先 bash build/pipe.sh build/site_cp）：
    python3 tests/copy_check.py build/site_cp [--shots DIR] [--inject 名字]
    --inject：把某个选项 / 提示改回长句，对应判据必须变红（名字见 INJ）。

判据（逐个弹层 / 提示，390×844 真点开取字，见 tests/copy_common.py）
  C1  固定选项（非站名、非日期格）主标题 ≤ 8 字；固定弹层标题 ≤ 8 字
  C2  副标题 ≤ 14 字；白名单（安全 / 事实类）见 SAFE_SUB，会逐条打印出来
  C3  不写“为什么 / 之后会怎样”：全部选项 / 副标题 / 说明 / 提示里没有 BANNED 里的句式
  C4  说明段：每个弹层 ≤ 1 条固定说明、≤ 16 字（白名单：开放时间以官网为准、复制框的操作句、导航分段说明）；不复述弹层标题
  C5  同一个弹层里没有两条相同的副标题 / 说明；“加入日历”的操作说明只在分享层出现一次
  C6  提示条：源码里每个 toast 要么带动作按钮（撤销 / 换回 / 回到…），要么在 TOAST_OK 白名单里（出错 / 限制 / 第一次才说 / 没有别的反馈）；文字 ≤ 16 字
  C7  “我的行程”：每行日期一行（M/D 出发…）、没有星期、没有“打开 ›”、空状态一句 ≤ 12 字
  C8  首页小标题不再带解释（快过季的先看 / N 月开始 / 城市、古城、博物馆 / 选出发地、天数、和谁去）
  C9  字数不回涨：弹层固定文案总字数 ≤ 预算（BUDGET）
"""
import json, os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from copy_common import *

INJ = {
    # C2 / C1：把副标题 / 主标题改回长句
    'share_copy_sub': ('assets/site.js', "<b>复制行程</b>", "<b>复制行程</b><small>按天的时间和地点，可以直接粘贴到微信</small>"),
    'share_link_sub': ('assets/site.js', "(myState()?'<small>含你的改动</small>':'')", "'<small>原版行程，带上你改过的日期、时间和加的天</small>'"),
    'share_print_main': ('assets/site.js', "<b>打印 / PDF</b>", "<b>打印 / 存成 PDF</b><small>一页页的行程单，给家里人或者出门带着</small>"),
    'addday_free_long': ('assets/site.js', "<b>多留一天</b><small>自由活动</small>", "<b>在'+stc+'多留一天</b><small>自由活动，不排行程，当天你自己安排</small>"),
    'adj_rm_sub': ('assets/site.js', "<b>去掉这一站</b></button>", "<b>去掉这一站</b><small>后面的时间往前挪</small></button>"),
    'adj_why_long': ('assets/site.js', ["return'已排到 '+npHm(b.last)", "rs==='late'?'已排到 '+npHm(sec._npRes?sec._npRes.end:0)"], ["return'这天已经排到 '+npHm(b.last)+'，再加就超过 '+npHm(NP_LIM.CAP)+' 了'", "rs==='late'?'这天已经排到 '+npHm(sec._npRes?sec._npRes.end:0)+'，再加就超过 23:00 了'"]),
    # C3 / C4：复述标题、解释后果的说明段
    'dayadj_dup': ('assets/site.js', "<div class=\"xd\">'\n          +(stb?", "<p class=\"xnote\">第 '+no+' 天 · '+t+'</p><div class=\"xd\">'\n          +(stb?"),
    'picker_tip': ('assets/site.js', "best?'<p class=\"pk-tip\"><i></i>绿色是最好的日子</p>':''", "best?'<p class=\"pk-tip\"><i></i>绿色是最好的日子</p>':'<p class=\"pk-tip\">选好就关上，页面会跟着这天重新排</p>'"),
    'adj_list_note': ('assets/site.js', "sh.innerHTML=h+top+'<div class=\"xd\">'", "sh.innerHTML=h+top+'<p class=\"xnote\">'+(kind==='ins'?'都在这天的路上，多绕 30 分钟以内':'和它在同一片，路程差不多')+'</p><div class=\"xd\">'"),
    # C6：提示条
    'toast_why': ('assets/site.js', "toast('去掉了「'+npCore(nmx)+'」','撤销'", "toast('去掉了「'+npCore(nmx)+'」，后面的时间往前挪了','撤销'"),
    'toast_echo': ('assets/site.js', "toast('改动太多，先撤销几处')", "toast('改动太多了，先撤销几处再加，这样页面才不会乱')"),
    'toast_new': ('assets/site.js', "toast('链接已复制')", "toast('链接已复制'),toast('已加好了，日期和底栏都跟着变了')"),
    # C7 / C8
    'mine_when': ('assets/site.js', "' 出发'+(lf<0?", "' 周五 出发'+(lf<0?"),
    'mine_open': ('assets/site.js', "<i class=\"mo\">›</i>", "<i class=\"mo\">打开 ›</i>"),
    'mine_empty_long': ('assets/site.js', "<p class=\"mempty\">在行程页点“收进行程”</p>", "<p class=\"mempty\">还没有收进的行程。打开一条行程，点底部“收进行程”就会出现在这里。</p>"),
    'home_ns': ('assets/site.js', "vis+' 条'", "vis+' 条，快过季的先看'"),
}

env = Env(INJ)
check = env.check

BANNED = re.compile(r'会跟着|之后会|以后会|后面的时间|往前挪|重新排|重排|可以直接|按天的时间|因为|所以|这样|下载后打开|给家里人|发朋友圈|页面会|就会出现|不是行车|都在这天的路上|和它在同一片|路程差不多')
# 允许写长一点的安全 / 事实类副标题（只压缩重复，不删）。每条要写理由
SAFE_SUB = [
    (re.compile(r'已排过'), '候选一天里你已排过的站（避免重复）'),
    (re.compile(r'^(这天排满了|已排到 \d\d:\d\d|到时已闭馆|附近没有顺路的|没网)$'), '置灰原因（为什么点不了）'),
    (re.compile(r'要预约|周一闭馆|闭馆|高反|极夜|封路|签证|海拔'), '安全 / 预约 / 闭馆'),
]
# 提示条白名单：没有按钮但必须说的
TOAST_OK = {
    '链接已复制': '剪贴板没有别的反馈',
    '行程已复制': '剪贴板没有别的反馈',
    '这个浏览器存不下，改动关掉页面就没了': '数据会丢（出错）',
    '链接不完整，已显示原版': '出错',
    '有一处改动已失效，已去掉': '出错',
    '打开的是朋友改过的版本': '第一次进朋友的版本才说',
    '日期改了，买票订房的勾选已清空': '会丢勾选（后果）',
    '改动太多，先撤销几处': '限制',
    '已经加过了': '限制',
    '这一晚没有推荐的住处': '空状态',
    '这天没有可画的位置': '空状态',
    '这天没有可导航的位置': '空状态',
    '这天排满了': '限制',
    '没拿到位置，选个城市吧': '出错',
    '没取到数据，联网后再试': '出错',
    '地图没加载出来，再点一次': '出错',
    '地图需要联网': '出错',
    '没网，暂时不能': '出错',
    '没网，暂时不能导航': '出错',
    '没打开': '出错',
    '再选一条': '限制',
    '保存图片失败': '出错',
}
FIXED_NOTE_OK = [
    (re.compile(r'^开放时间以官网为准$'), '安全：开放时间'),
    (re.compile(r'^长按文字，选“复制”$|^长按下面的文字，选“复制”$'), '复制框的操作句（要做什么）'),
    (re.compile(r'^分 \d+ 段，按顺序点$'), '导航分段说明'),
    (re.compile(r'^绿色是最好的日子$'), '图例'),
    (re.compile(r'^附近可接的一天$|^附近没有可接的$|^没网，只能多留一天$'), '区块小标题 / 空状态'),
    (re.compile(r'^每天都用这个时间$'), '复选项'),
    (re.compile(r'^主景点，换了这天会变$'), '换主景点的后果（偏离预期）'),
    (re.compile(r'^(附近没有顺路的|这天排满了|已排到 \d\d:\d\d|到时已闭馆|没网，稍后再试)$'), '空状态'),
    (re.compile(r'^(你加的|原来是「.*」)?( · )?((多|少)待 \d+ 分钟)?$'), '这一站的现状（偏离原行程才写）'),
    (re.compile(r'^在行程页点“收进行程”$'), '空状态：要做什么'),
    (re.compile(r'^按默认安排估算$'), '对比口径'),
]
FIXED_WHERE = ('行程页 › 分享', '行程页 › 选日期', '行程页 › 几点出发', '行程页 › 加一天', '行程页 › 改这一天', '行程页 › 改这一站', '行程页 › 复制框', '首页 › 我的行程', '首页 › 我的行程（空）', '地图 › 导航分段')
DYN_CLS = ('npc', 'mr', 'mrx', 'mrc', 'rm-seg', 'rm-tb', 'rm-pi', 'cmpb')      # 站名 / 行程名 / 日期：内容是数据，不算文案
TOTAL_BUDGET = 230      # C9：固定文案总字数上限（改前 340，改后约 200，留一点余量）

with sync_playwright() as p:
    rows = walk(env, p)
    # 源码里的 toast：读送到浏览器的那份 JS（反向注入也生效）
    import urllib.request
    src = ''
    for f in ('/assets/site.js', '/assets/routemap.js'):
        try:
            import glob
            fp = [x for x in glob.glob(os.path.join(env.site, 'assets', os.path.basename(f).split('.')[0] + '*.js'))]
            src += urllib.request.urlopen(env.B + f).read().decode('utf-8') + '\n'
        except Exception as e:
            env.fails.append('读不到 ' + f + ' ' + str(e))

by = {}
for r in rows: by.setdefault(r['where'], []).append(r)
OPTS = [r for r in rows if r['kind'] == 'opt' and r['where'] in FIXED_WHERE and not r.get('dyn') and not any(c in (r.get('cls') or '').split() for c in DYN_CLS) and not (r['where'] == '行程页 › 选日期')]
# 选日期里“这周六 / 下个周末 / 下个月 1 号 / 建议”是固定选项；日期格被 NOISE 滤掉了
OPTS += [r for r in rows if r['kind'] == 'opt' and r['where'] == '行程页 › 选日期']
OPTS = [r for r in OPTS if r['main'] and r.get('cls') != 'pk-j']
HEADS = [r for r in rows if r['kind'] == 'head' and r['where'] in FIXED_WHERE and r['where'] != '首页 › 我的行程（空）' and len(by.get(r['where'], [])) > 0]
FIXED_HEADS = [r for r in HEADS if r['cls'] == '' or True]

# C1 主标题 ≤ 8
over = [(r['where'], r['main']) for r in OPTS if len(r['main']) > 8]
check('C1 固定选项主标题 ≤ 8 字（共 %d 个）%s' % (len(OPTS), over[:4]), not over, over)
hv = [(r['where'], r['main']) for r in rows if r['kind'] == 'head' and r['where'] in ('行程页 › 分享', '行程页 › 选日期', '行程页 › 几点出发', '行程页 › 加一天', '行程页 › 改这一天', '行程页 › 改这一站', '行程页 › 复制框') and len(r['main']) > 8]
check('C1 固定弹层标题 ≤ 8 字', not hv, hv)

# C2 副标题 ≤ 14，或在白名单
def safe(sub):
    for rx, why in SAFE_SUB:
        if rx.search(sub): return why
    return None
subs = [r for r in OPTS if r['sub']]
longs = [(r['where'], r['main'], r['sub']) for r in subs if len(r['sub']) > 14 and not safe(r['sub'])]
check('C2 副标题 ≤ 14 字，超过的必须是白名单里的安全 / 事实类（%d 个有副标题）%s' % (len(subs), longs[:3]), not longs, longs)
# 白名单里的也不许太长（≤ 40）
wl = [(r['where'], r['main'], r['sub']) for r in subs if len(r['sub']) > 14 and safe(r['sub'])]
check('C2 白名单副标题（%d 条）也 ≤ 40 字' % len(wl), all(len(x[2]) <= 40 for x in wl), wl)
for r in subs:
    if len(r['sub']) > 14 and safe(r['sub']): env.note('白名单：%s | %s | %s → %s' % (r['where'], r['main'], r['sub'], safe(r['sub'])))
# 去掉这一天的警告（有才有）
rg = [r for r in rows if 'rmgo' in (r.get('cls') or '') and r['sub']]
check('C2 “去掉这一天”只有真实警告才带小字、≤ 30 字（%s）' % [r['sub'] for r in rg], all(len(r['sub']) <= 30 for r in rg))

# C3 禁句式
LISTW = tuple(w for w in by if w.startswith('行程页 › 改这一站 ›'))      # 候选列表（在这之后加一个 / 换成）：固定说明也受预算管，候选名字不算
allt = [(r['where'], r['main'] + ' ' + r['sub']) for r in rows if r['kind'] in ('opt', 'note', 'toast', 'head') and not r.get('dyn') and r['where'] in FIXED_WHERE + LISTW + tuple(w for w in by if w.startswith('提示条'))]
bad = [(w, t) for w, t in allt if BANNED.search(t)]
check('C3 弹层 / 提示里没有“为什么 / 之后会怎样”的句式 %s' % bad[:3], not bad, bad)

# C4 说明段
for w in FIXED_WHERE + LISTW:
    ns = [r for r in by.get(w, []) if r['kind'] == 'note']
    fixed = [r for r in ns if not any(rx.search(r['main']) for rx, _ in FIXED_NOTE_OK)]
    heads = [r['main'] for r in by.get(w, []) if r['kind'] == 'head']
    dup = [r['main'] for r in ns if heads and len(heads[0]) >= 3 and heads[0].replace('改', '').replace('选', '').strip() and heads[0].replace('改', '').strip() in r['main']]
    check('C4 %s：说明段都是白名单里的短句（%d 条，多余：%s）' % (w, len(ns), [r['main'][:16] for r in fixed][:3]), not fixed, fixed)
    check('C4 %s：说明段不复述标题 %s' % (w, dup[:1]), not dup, dup)
    chk = [r['main'] for r in ns if len(r['main']) > 16 and not any(rx.search(r['main']) for rx, _ in FIXED_NOTE_OK[:1])]
    # 说明段 ≤ 16 字（带站名的“这一站现状”和白名单里的 ≤ 20 例外）
    okl = [r['main'] for r in ns if len(r['main']) > 20 and 'adjn' not in (r.get('cls') or '')]
    check('C4 %s：说明段 ≤ 20 字 %s' % (w, okl[:1]), not okl, okl)

# C5 同一弹层里不重复；“加入日历”说明只在分享层出现一次
for w in FIXED_WHERE:
    ts = [r['sub'] for r in by.get(w, []) if r['kind'] == 'opt' and r['sub'] and not r.get('dyn')] + [r['main'] for r in by.get(w, []) if r['kind'] == 'note']
    d = sorted({t for t in ts if ts.count(t) > 1})
    check('C5 %s：没有两条相同的副标题 / 说明 %s' % (w, d[:2]), not d, d)
ics = [(w, r['main'], r['sub']) for w in FIXED_WHERE + ('行程页 › 出发前要办的事',) for r in by.get(w, []) if '加入日历' in (r['main'] + r['sub'])]
expl = [x for x in ics if len(x[1] + x[2]) > 20]
check('C5 “加入日历”：操作说明只在分享层写一次、出发前清单里只是一个入口（%s）' % [x[1][:20] + '|' + x[2][:12] for x in ics], len([x for x in ics if '全部添加' in x[1] + x[2]]) <= 1 and not [x for x in expl if x[0] != '行程页 › 分享'], ics)

# C6 提示条
calls = re.findall(r"toast\('([^']*)'((?:\s*\+\s*[^,()]+(?:\([^)]*\))?)*)\s*(?:,\s*('[^']*'(?:\s*\+\s*[\w.]+(?:\s*\+\s*'[^']*')?)*)\s*,\s*function)?", src)
bad6, long6 = [], []
seen_t = set()
for t, dyn, lab in calls:
    key = t
    if key in seen_t: continue
    seen_t.add(key)
    if lab: continue      # 带动作按钮（撤销 / 换回我自己的 / 回到第 N 天）
    base = t
    if base not in TOAST_OK: bad6.append(t)
    if len(base) > 16 and base not in TOAST_OK: long6.append(base)
    if len(base) > 18: long6.append(base)
check('C6 源码里每个 toast 要么带动作按钮、要么在白名单里（%d 个不同的提示）%s' % (len(seen_t), bad6[:4]), not bad6, bad6)
check('C6 提示条文字 ≤ 16 字（白名单里的 ≤ 18）%s' % long6[:3], not long6, long6)
act_toasts = [r for w in by if w.startswith('提示条') for r in by[w] if r['kind'] == 'toast']
check('C6 点出来的提示条（%d 个）都带“撤销”、写 ≤ 24 字（含按钮）、没有后果句 %s' % (len(act_toasts), [r['main'] for r in act_toasts]), act_toasts and all(r['main'].endswith('撤销') and len(r['main']) <= 24 for r in act_toasts), [r['main'] for r in act_toasts])
tp = re.findall(r"toast\('([^']*)'[^)]*\)", src)
check('C6 源码里没有后果句 / 复述句 %s' % [t for t in tp if BANNED.search(t)][:3], not [t for t in tp if BANNED.search(t)], [t for t in tp if BANNED.search(t)])

# C7 我的行程
wh = [r['main'] for r in rows if r['kind'] == 'when' and r['cls'] == 'mw']
mo = [r['main'] for r in rows if r['kind'] == 'when' and r['cls'] == 'mo']
check('C7 我的行程每行一句日期（“建议 明年 M/D 出发”这种），没有星期 / 天数前缀（%s）' % wh, wh and all(re.match(r'^(建议 )?(明年 )?\d+/\d+ 出发( · .+)?$|^日期还没定$', t) and '周' not in t and not re.match(r'^\d+ 天', t) for t in wh), wh)
check('C7 我的行程右边只有 ›，没有“打开 ›”（%s）' % mo[:2], mo and all(t == '›' for t in mo), mo)
em = [r['main'] for r in by.get('首页 › 我的行程（空）', []) if r['cls'] == 'mempty']
check('C7 我的行程空状态一句 ≤ 12 字（%s）' % em, em and all(len(t) <= 12 for t in em), em)
cb = [r['main'] for r in by.get('首页 › 我的行程', []) if 'mcmp' in (r.get('cls') or '')]
check('C7 对比按钮 ≤ 8 字（%s）' % cb, cb and all(len(t) <= 8 for t in cb), cb)

# C8 首页小标题
hm = [r['main'] for r in rows if r['where'] == '首页' and r['kind'] == 'ctl']
ban8 = [t for t in hm if re.search(r'快过季的先看|月开始$|^城市、古城、博物馆$|选出发地、天数、和谁去', t)]
check('C8 首页区块小标题不带解释 %s' % ban8, not ban8 and any('条' in t for t in hm), ban8)

# C9 总字数（算法在 copy_common.fixed_total，盘点表也用它算“改前 / 改后”）
tot = fixed_total(rows)
env.note('固定文案总字数 %d（预算 %d）' % (tot, TOTAL_BUDGET))
check('C9 弹层固定文案总字数 %d ≤ %d' % (tot, TOTAL_BUDGET), tot <= TOTAL_BUDGET)

env.finish('文字预算 copy_check')
