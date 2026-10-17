"""页面里“周几”的说法必须来自所选出发日期（2026-10-18，用户反馈 P0）。

内容里（data/、build/history 入库后的线路）有大量把“这条线的日期落在周几”写死的句子：
  “本线三天是周二到周四，没有排在周一” “这天是周二” “第一天是周日” “三天分别是周五、周六、周日，避开了周一闭馆”
用户改了出发日期，这些句子就和页面上的日期打架。线路页是按出发日期动态算星期的（site.js monday() / 顶部闭馆提醒），
所以静态文案里**不许**再带“这条线具体哪天是周几”的说法；场馆自己的闭馆日（“某馆周一闭馆”）是场馆的事实，保留。

scrub(text) 逐分句判断：含周几 + 日程锚词（这天 / 第N天 / 本线 / 行程 / 避开 / 排在 / 落在 …）→ 删掉；
紧跟其后的“正常开放 / 不受影响”这类结论一起删（它们依赖那个被删的周几）；删到只剩标签（“星期核对：”）就整句删。
build_site.py 在载入线路时对 prep / fit / 每天的 text、story、notes、行的说明各跑一遍；tests/weekday_check.py 对全站再扫一遍。
"""
import re

WD = r'周[一二三四五六日]'
NUM = r'[一二三四五六七八九十\d]+'
# 日程锚词：出现在同一分句里，说明这句是在讲“这条线的日期”而不是“某馆的闭馆日”
ANCHOR = re.compile(r'这天|这一天|这日|这一日|当天|当日|今天|本天|本线|这条线|这趟|本趟|行程(?:里|已|把|按|从|定|排|日期)|线路(?:的|里|把|已|从|排|日期|定)|出发日|日期|三天|两天|四天|五天|六天|七天|八天|九天|十天'
                    r'|第\s*' + NUM + r'\s*(?:[、,]\s*' + NUM + r'\s*)*天|避开|没有排在|排在|落在|定在|安排在|不落在|不排|依次|分别|所以排|特意|赶路日|错开|从周|走到周')
FORMS = [re.compile(p) for p in (
    r'\d+\s*月\s*\d+\s*日\s*(?:是|为)?\s*[（(]?' + WD,            # 出发日是 2027 年 10 月 12 日周二
    WD + r'[（(]\d+\s*月\s*\d+\s*日[）)]',                        # 周四（10 月 14 日）是赶路日
    r'[天日][（(]' + WD,                                         # 第 2、4、6 天（周二、周四、周六）
    r'[（(]' + WD + r'(?:[、，,]\s*' + WD + r')*[）)]',          # 天一阁博物院（周三）
)]
# 前一句是日期说法时，紧跟的这种结论也依赖它
RESULT = re.compile(r'^(?:没有排|不排|不在|不落在|也不在|不撞|行程里那天|那天)|^[^，；。]{0,14}?(?:正常开放|照常开放|正常开|开着|开门|不受影响|不用调|不用改|不受闭馆影响|都开|也开放|开放)[^，；。]{0,8}$|^工作日[^，；。]{0,12}$')
LABEL_ONLY = re.compile(r'^[^，；。]{0,12}[：:]\s*$')
SEP = '，；;,'
PH = {'，': '\u0001', '；': '\u0002', ';': '\u0003', ',': '\u0004'}
RPH = {v: k for k, v in PH.items()}


DANGLE = re.compile(r'^\s*(?:本线路?|这条线路?|这趟)(?:的)?日期里?\s*$')
COND = re.compile(r'^\s*(?:如果|要是|若|假如|改期|改日期|改了|别|不要|勿|避免|请|建议)')   # 对用户自己改日期的建议，不是对“这条线哪天”的断言


def is_claim(cl):
    if not re.search(WD, cl): return False
    if COND.match(cl): return False
    c2 = cl.replace('出发前', '').replace('出发后', '')
    if ANCHOR.search(c2): return True
    return any(f.search(cl) for f in FORMS)


def _protect(s):
    # （…）里面的逗号不当分句符号
    return re.sub(r'（[^（）]*）', lambda m: ''.join(PH.get(ch, ch) for ch in m.group(0)), s)


def _restore(s):
    return ''.join(RPH.get(ch, ch) for ch in s)


def _sentence(s):
    """一个句子（不含 。）→ 删掉日期说法后的句子（可能为空）"""
    s0 = s
    # 先处理括号里的内容（递归一层就够）
    def inner(m):
        t = _sentence(_restore(m.group(1)))
        return ('（' + t + '）') if t else ''
    s = re.sub(r'（([^（）]*)）', inner, s)
    parts = re.split(r'([' + re.escape(SEP) + r'])', _protect(s))
    cl = [(parts[i], parts[i + 1] if i + 1 < len(parts) else '') for i in range(0, len(parts), 2)]
    keep = []; prev_drop = False
    for c, sp in cl:
        c_ = _restore(c)
        if is_claim(c_) or DANGLE.match(c_): prev_drop = True; continue
        if prev_drop and (RESULT.match(c_.strip()) or (re.search(WD, c_) and not re.search(r'闭|休|开放|营业|开门', c_))): continue   # “正常开放”依赖被删掉的周几；接着一串“周五的甘肃省博物馆”也是同一个断言
        prev_drop = False; keep.append((c_, sp))
    if not keep: return ''
    out = ''.join(c + sp for c, sp in keep[:-1]) + keep[-1][0]
    out = out.strip(' ，；;,')
    if LABEL_ONLY.match(out) or len(re.sub(r'[\s，；、：:（）()]', '', out)) < 4 and out != s0: return ''
    return out if out != s0 else s0


def scrub(text):
    if not text or not re.search(WD, text): return text
    # 按 。！？换行切句，保留终止符
    pieces = re.split(r'([。！？\n])', text)
    out = []
    for i in range(0, len(pieces), 2):
        s = pieces[i]; t = pieces[i + 1] if i + 1 < len(pieces) else ''
        if not re.search(WD, s): out.append(s + t); continue
        n = _sentence(s)
        if n: out.append(n + t)
    r = ''.join(out)
    r = re.sub(r'\s{2,}', ' ', r).strip()
    return r


def scrub_route(r):
    """就地清洗一条线路里会渲染到页面上的文字；返回改了几处"""
    n = [0]
    def fix(d, k):
        v = d.get(k)
        if isinstance(v, str):
            w = scrub(v)
            if w != v: d[k] = w; n[0] += 1
        elif isinstance(v, list):
            nv = []
            for x in v:
                w = scrub(x) if isinstance(x, str) else x
                if w != x: n[0] += 1
                if w or not isinstance(x, str): nv.append(w)
            if nv != v: d[k] = nv
    for k in ('prep', 'fit', 'note', 'notes', 'intro', 'driveSub'): fix(r, k)
    for d in r.get('days') or []:
        for k in ('text', 'story', 'notes', 'stayNote'): fix(d, k)
        for w in d.get('rows') or []:
            for k in ('d', 'kb', 'text'): fix(w, k)
    return n[0]
