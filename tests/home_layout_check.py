#!/usr/bin/env python3
"""首页栅格 / 节奏 / 对齐检查（2026-10-16）：把“间距不齐、边距不一致、对不齐、点不到”做成会红的判据。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/home_layout_check.py build/site                  # 全绿退出码 0，否则 1，并列出每条红在哪个视口
    python3 tests/home_layout_check.py build/site --only 390       # 只跑一个宽度（调样式时快）
    python3 tests/home_layout_check.py build/site --inject         # 自检：故意把几处间距/对齐改坏，必须全部变红（改完判据后跑一次）

视口 360×740 / 390×844 / 430×932 / 768×1024 / 1280×800 × 亮色 / 暗色；每个视口量三个状态：
默认、点开“替我挑三条”、点了“再看 12 条”之后。

规则（出处：docs/handoff/02-UI规范.md「首页」一节的“栅格与节奏”）：
  a 栅格   所有区块的左缘（文字量文字、框量框）落在同一条线 L 上（L = 搜索框左缘），右缘落在 R 上，容差 1px
  b 节奏   竖向间距只取 {8, 12, 16, 24, 32}，且同一种关系取同一个值（见 GAPS 表：控件叠放 8、标题到内容 12、区块之间 32 …）
  c 等高   频道三格等高、天数 chip 等高、挑三条每行 chip 等高、搜索框和“搜”等高同顶；卡片里图和字顶对齐，所有卡内边距相同
  d 对齐   框里左右两端的字（“10/16 周五 出发”和“改”、“替我挑三条”和“展开”）中线一致；chip 里文字垂直居中；频道格里两行字同一左缘
  e 溢出   无横向滚动；横向滚动的行（天数 chip、挑三条）必须铺到版心边缘，不能在内容区中间被切；
           文字不被截（频道格副标题不换行落单字、搜索框占位字放得下）；卡片文字和图不重叠
  f 触控   可点元素有效高度 >= 44（用 elementFromPoint 真探，伪元素补出来的点击区也算）
  g 层级   同级标题字号一致（各区块 h2、卡片 h3、右侧小字）
  h 桌面   >= 600 宽时版心不超过 480、左右留白相等（居中）；手机宽度版心 = 视口
"""
import functools, http.server, json, os, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

args = [a for a in sys.argv[1:] if not a.startswith('--')]
site = os.path.abspath(args[0]) if args else os.path.abspath('build/site')
ONLY = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
INJECT = '--inject' in sys.argv
if ONLY and ONLY in args: args.remove(ONLY)

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{srv.server_address[1]}'

VIEWPORTS = [(360, 740), (390, 844), (430, 932), (768, 1024), (1280, 800)]
SET = [8, 12, 16, 24, 32]
TOL = 1.01
# 关系 → 期望值（都取自 SET）
GAPS = {
    '封面→搜索': 16, '搜索→频道': 8, '频道→挑三条': 8, '挑三条→现在去正好': 24,
    '分区线→标题': 12, '标题→日期条': 12, '日期条→天数chip': 8, '天数chip→列表': 8, '列表→再看': 8,
    '标题→列表': 12, '区块→区块': 32, '列表→全部线路条': 8, '再看→全部线路条': 8,
    '挑三条 头→第一行': 8, '挑三条 行→行': 8, '挑三条 末行→提示': 12,
}

JS = r"""(state)=>{
const q=s=>document.querySelector(s), qa=s=>[...document.querySelectorAll(s)];
const vis=e=>{if(!e||e.hidden)return false;const b=e.getBoundingClientRect();return b.width>0&&b.height>0};
const first=s=>qa(s).find(vis)||null;
const R=e=>{if(!e)return null;const b=e.getBoundingClientRect();return {l:b.left,r:b.right,t:b.top+scrollY,b:b.bottom+scrollY,h:b.height,w:b.width}};
const txt=e=>{if(!e)return null;const w=document.createTreeWalker(e,NodeFilter.SHOW_TEXT,{acceptNode:n=>n.textContent.trim()?1:2});const n=w.nextNode();if(!n)return null;const g=document.createRange();g.selectNodeContents(n);const b=g.getBoundingClientRect();return {l:b.left,r:b.right,t:b.top+scrollY,b:b.bottom+scrollY,cy:(b.top+b.bottom)/2+scrollY,h:b.height}};
const cy=e=>{const b=e.getBoundingClientRect();return (b.top+b.bottom)/2+scrollY};
const o={vw:innerWidth,doc:document.documentElement.scrollWidth,bodyw:document.body.scrollWidth};
const art=q('article.home');o.art=R(art);
const L=R(q('.hsearch')); o.L=L.l; o.Rr=L.r;
// a 左缘 / 右缘
const edges=[];
const E=(name,e,mode,side)=>{if(!e)return;const r=mode==='t'?txt(e):R(e);if(!r)return;edges.push({name,l:r.l,r:r.r,side:side||'lr'})};
E('封面 走你',q('.mast h1'),'t','l');E('封面 小字',q('.cv .kick'),'t','l');E('封面 标题',q('.cv h2'),'t','l');
E('封面 chips',q('.cv .chips'),'b','l');E('封面 翻开',q('.cv .go'),'b');E('封面 我的行程(右缘)',q('.minebtn'),'b','r');
E('搜索框',q('.hsearch'),'b');E('频道三格',q('.chan2'),'b');E('挑三条 条',q('.pick .pkh'),'b');
if(state!=='base'){E('挑三条 左标签',q('.pick .pkq'),'t','l');E('挑三条 提示',q('.pick .pkhint'),'t','l')}
E('现在去正好 区块',q('#now'),'b');E('现在去正好 标题',q('#now h2 .nt'),'t','l');E('日期条',q('.datebar .hdt'),'b');
const dc=q('.dchips');E('天数chip 第一个',dc&&dc.querySelector('button'),'b','l');
const li1=first('#now .items li');E('卡片 整张',li1,'b');E('卡片 序号',li1&&li1.querySelector('.num'),'t','l');E('卡片 图(右缘)',li1&&li1.querySelector('.tile'),'b','r');
E('再看',first('.moreb'),'b');
qa('article.home > section.toc').forEach((s,i)=>{const h=s.querySelector('h2');E('区块'+i+' 标题',h,'t','l');E('区块'+i+' 框',s,'b')});
const ab=first('.allbar');E('全部线路条',ab,'b');
qa('article.home ~ footer a, footer.foot a').slice(0,1).forEach(a=>E('页脚 第一个字',a,'t','l'));
const ft=q('footer.foot,.foot');if(ft){const t=txt(ft);if(t)edges.push({name:'页脚 文字',l:t.l,r:t.r,side:'l'})}
o.edges=edges;
// b 竖向间距
const gaps=[];
const G=(name,a,b2,fromBottom=true)=>{if(!a||!b2)return;const ra=R(a),rb=R(b2);gaps.push({name,v:rb.t-(fromBottom?ra.b:ra.t)})};
G('封面→搜索',q('.cover'),q('.hsearch'));G('搜索→频道',q('.hsearch'),q('.chan2'));G('频道→挑三条',q('.chan2'),q('.pick'));
const now=q('#now');G('挑三条→现在去正好',q('.pick'),now);
if(now){const bt=parseFloat(getComputedStyle(now).borderTopWidth)||0;const h=now.querySelector('h2');gaps.push({name:'分区线→标题',v:R(h).t+(parseFloat(getComputedStyle(h).paddingTop)||0)-R(now).t-bt});
 G('标题→日期条',h,now.querySelector('.datebar'));G('日期条→天数chip',now.querySelector('.datebar'),now.querySelector('.dchips'));
 G('天数chip→列表',now.querySelector('.dchips'),now.querySelector('.items'));G('列表→再看',now.querySelector('.items'),now.querySelector('.moreb'))}
const secs=qa('article.home > section.toc');
secs.forEach((s,i)=>{if(s===now)return;const h=s.querySelector('h2'),it=s.querySelector('.items');const bt=parseFloat(getComputedStyle(s).borderTopWidth)||0;
 if(h){gaps.push({name:'分区线→标题',v:R(h).t+(parseFloat(getComputedStyle(h).paddingTop)||0)-R(s).t-bt,who:'区块'+i});if(it)gaps.push({name:'标题→列表',v:R(it).t-R(h).b,who:'区块'+i})}
 const mb=s.querySelector('.moreb'),al=s.querySelector('.allbar');
 if(mb&&vis(mb)&&it)gaps.push({name:'列表→再看',v:R(mb).t-R(it).b,who:'区块'+i});
 if(al&&mb&&vis(mb))gaps.push({name:'再看→全部线路条',v:R(al).t-R(mb).b,who:'区块'+i});
 else if(al&&it)gaps.push({name:'列表→全部线路条',v:R(al).t-R(it).b,who:'区块'+i})});
for(let i=1;i<secs.length;i++)gaps.push({name:'区块→区块',v:R(secs[i]).t-R(secs[i-1]).b,who:'区块'+(i-1)+'→'+i});
if(state==='pick'){const pk=q('.pick'),rows=qa('.pick .pkrow');if(rows.length){gaps.push({name:'挑三条 头→第一行',v:R(rows[0]).t-R(q('.pick .pkh')).b});
 for(let i=1;i<rows.length;i++)gaps.push({name:'挑三条 行→行',v:R(rows[i]).t-R(rows[i-1]).b,who:'行'+i});
 const hint=q('.pick .pkhint');if(hint)gaps.push({name:'挑三条 末行→提示',v:R(hint).t-R(rows[rows.length-1]).b})}}
o.gaps=gaps;
// c 等高 / d 对齐
const eq=[];
const H=(name,els)=>{els=els.filter(vis);if(els.length>1)eq.push({name,hs:els.map(e=>+e.getBoundingClientRect().height.toFixed(1))})};
H('频道四格等高',qa('.chan2 a'));H('天数chip 等高',qa('.dchips button'));
qa('.pick .pkr').forEach((r,i)=>H('挑三条 第'+(i+1)+'行 chip 等高',[...r.querySelectorAll('button')]));
const si=q('.hsearch input'),sb=q('.hsearch button');
eq.push({name:'搜索框和“搜”等高',hs:[si.getBoundingClientRect().height,sb.getBoundingClientRect().height]});
eq.push({name:'搜索框和“搜”同顶',hs:[si.getBoundingClientRect().top,sb.getBoundingClientRect().top]});
o.eq=eq;
const al=[];
const C=(name,a,b2)=>{if(a&&b2)al.push({name,d:Math.abs(a.cy-b2.cy)})};
const db=q('.datebar .hdt');if(db)C('日期条 左字/“改”中线',txt(db.querySelector('b')),txt(db.querySelector('i')));
const ph=q('.pick .pkh');if(ph){C('挑三条 标题/摘要中线',txt(ph.querySelector('b')),txt(ph.querySelector('small')));C('挑三条 标题/“展开”中线',txt(ph.querySelector('b')),txt(ph.querySelector('i')))}
// chip 文字垂直居中
const chipc=[];[...qa('.dchips button'),...qa('.pick .pkr button'),q('.moreb'),q('.minebtn'),first('.allbar'),first('.dchips button.on')].filter(vis).forEach(b=>{const t=txt(b);if(t){const bc=cy(b);chipc.push({d:Math.abs(t.cy-bc),who:(b.className||b.parentElement.className||b.tagName)+':'+b.textContent.trim().slice(0,6)})}});
o.chipc=chipc;o.al=al;
const mb0=q('.minebtn');if(mb0){const sv=mb0.querySelector('svg'),sp=txt(mb0.querySelector('span')),br=mb0.getBoundingClientRect(),sr=sv.getBoundingClientRect();o.mine={gap:sp.l-sr.right,pl:sr.left-br.left,pr:br.right-sp.r}};
// 搜索框文字 / 搜 中线
o.search_txt={d:Math.abs(cy(si)-cy(sb))};
o.grid=qa('.chan2 a').map(R);   // 频道 2×2 的四个格
// 频道格内字左缘
o.chan=qa('.chan2 a').map(a=>{const ar=a.getBoundingClientRect();const b=txt(a.querySelector('b')),s=txt(a.querySelector('small'));return {pl:b.l-ar.left,dl:Math.abs(b.l-s.l),sh:a.querySelector('small').getBoundingClientRect().height,sfs:parseFloat(getComputedStyle(a.querySelector('small')).fontSize),slh:parseFloat(getComputedStyle(a.querySelector('small')).lineHeight)||0}});
// 卡片
const cards=qa('#now .items li').filter(vis).slice(0,8);
o.cards=cards.map((li,i)=>{const lr=R(li),tx=R(li.querySelector('.tx')),tl=R(li.querySelector('.tile')),nm=R(li.querySelector('.num')),h3=li.querySelector('h3'),p=li.querySelector('p'),sm=li.querySelector('.tx>small');
 const cs=e=>e?parseFloat(getComputedStyle(e).lineHeight)||0:0,fs=e=>e?parseFloat(getComputedStyle(e).fontSize):0;
 return {i,top:tx.t-lr.t,tileTop:tl.t-lr.t,numTop:nm.t-lr.t,bot:lr.b-Math.max(tx.b,tl.b),gapTile:tl.l-tx.r,h3:fs(h3),h3lh:cs(h3),pfs:fs(p),plh:cs(p),sfs:fs(sm),slh:cs(sm),h:lr.h}});
// e 溢出
o.rows=[];qa('.dchips,.pick .pkr').filter(vis).forEach(r=>{const b=r.getBoundingClientRect();o.rows.push({name:r.className,over:r.scrollWidth>r.clientWidth+1,l:b.left,r:b.right,al:o.art.l,ar:o.art.r})});
const ph2=q('.hsearch input');const pcs=getComputedStyle(ph2,'::placeholder');const ics=getComputedStyle(ph2);
const cl=ph2.cloneNode();cl.value=ph2.placeholder;cl.removeAttribute('placeholder');cl.style.cssText='position:absolute;visibility:hidden;left:0;top:0;width:'+ph2.getBoundingClientRect().width+'px;font-size:'+pcs.fontSize;ph2.parentNode.appendChild(cl);
o.ph={w:cl.scrollWidth,avail:cl.clientWidth,fs:pcs.fontSize};cl.remove();
o.clip=[];qa('article.home .tx *, article.home .chan2 *, article.home .cv *, article.home .pkh *, article.home .datebar *').filter(e=>vis(e)&&e.clientWidth>0&&getComputedStyle(e).display!=='inline').forEach(e=>{const cs=getComputedStyle(e);if(e.scrollWidth>e.clientWidth+1&&cs.textOverflow!=='ellipsis')o.clip.push(e.className+':'+e.textContent.trim().slice(0,12))});
// f 触控（有效点击高度）
const sels=['.minebtn','.cv .go','.hsearch input','.hsearch button','.chan2 a','.pick .pkh','.pick .pkr button','.datebar .hdt','.dchips button','#now .items li:not([hidden]) h3 a','.moreb','.allbar','footer.foot a,.foot a'];
o.tap=[];
sels.forEach(s=>{qa(s).filter(vis).slice(0,3).forEach(e=>{e.scrollIntoView({block:'center',inline:'nearest',behavior:'instant'});const b=e.getBoundingClientRect();let x=(b.left+b.right)/2;if(x<2||x>innerWidth-2)return;
 let cyy=(b.top+b.bottom)/2;const inEl=y=>{const h=document.elementFromPoint(x,y);return !!h&&(h===e||e.contains(h))};
 if(!inEl(cyy))return;let up=cyy,dn=cyy;while(inEl(up-1)&&cyy-up<80)up--;while(inEl(dn+1)&&dn-cyy<80)dn++;
 o.tap.push({name:s+' '+e.textContent.trim().slice(0,8),h:dn-up+1,w:b.width})})});
scrollTo(0,0);
// g 层级
o.h2=secs.map(s=>{const h=s.querySelector('h2');const sm=h&&h.querySelector('small');return {t:h&&parseFloat(getComputedStyle(h).fontSize),s:sm&&parseFloat(getComputedStyle(sm).fontSize),lh:h&&getComputedStyle(h).lineHeight}});
o.h3=[...new Set(qa('.items h3').filter(vis).map(h=>getComputedStyle(h).fontSize))];
return o}"""

fails, oks = {}, []
def rec(name, ok, ctx, detail=''):
    if ok: oks.append(name)
    else: fails.setdefault(name, []).append(f'{ctx}' + (f' {detail}' if detail else ''))

def judge(o, ctx, w, state):
    vw = o['vw']
    # h 版心
    art = o['art']
    if w >= 600:
        rec('h 桌面：版心不超过 480', art['w'] <= 480, ctx, f"{art['w']:.0f}")
        rec('h 桌面：版心居中（左右留白相等）', abs(art['l'] - (vw - art['r'])) <= TOL, ctx, f"左{art['l']:.0f} 右{vw-art['r']:.0f}")
    else:
        rec('h 手机：版心 = 视口宽', abs(art['w'] - vw) <= TOL, ctx, f"{art['w']:.0f}/{vw}")
    # e 无横向滚动
    rec('e 无横向滚动', o['doc'] <= vw and o['bodyw'] <= vw, ctx, f"doc {o['doc']} body {o['bodyw']} vw {vw}")
    if state != 'base': return
    # a 栅格
    for e in o['edges']:
        if 'l' in e['side']:
            rec('a 左缘落在栅格线上（所有区块同一条线）', abs(e['l'] - o['L']) <= TOL, ctx, f"{e['name']} {e['l']:.1f} ≠ {o['L']:.1f}")
        if 'r' in e['side']:
            rec('a 右缘落在栅格线上', abs(e['r'] - o['Rr']) <= TOL, ctx, f"{e['name']} {e['r']:.1f} ≠ {o['Rr']:.1f}")
    # b 间距
    for g in o['gaps']:
        who = g.get('who', '')
        rec('b 竖向间距取自 {8,12,16,24,32}', any(abs(g['v'] - s) <= TOL for s in SET), ctx, f"{g['name']}{who} = {g['v']:.1f}")
        exp = GAPS.get(g['name'])
        if exp is not None:
            rec('b 同一种关系同一个间距（见 GAPS 表）', abs(g['v'] - exp) <= TOL, ctx, f"{g['name']}{who} = {g['v']:.1f}，应为 {exp}")
    # c 等高
    for e in o['eq']:
        rec('c ' + e['name'].replace('第1行', '第N行').replace('第2行', '第N行').replace('第3行', '第N行').replace('第4行', '第N行'),
            max(e['hs']) - min(e['hs']) <= TOL, ctx, str(e['hs']))
    cs = o['cards']
    if cs:
        for k, lab in (('top', '卡片内边距（上）相同且在 {8,12,16}'), ('bot', '卡片内边距（下）相同且在 {8,12,16}')):
            vals = [c[k] for c in cs[1:]] if k == 'top' else [c[k] for c in cs]
            rec('c ' + lab, vals and max(vals) - min(vals) <= TOL and any(abs(vals[0] - s) <= TOL for s in (8, 12, 16)), ctx, str(sorted(set(round(v, 1) for v in vals))))
        rec('c 卡片里图顶和文字顶对齐', all(abs(c['tileTop'] - c['top']) <= TOL for c in cs[1:]), ctx, str([(round(c['tileTop'], 1), round(c['top'], 1)) for c in cs[1:3]]))
        rec('c 卡片里序号顶和文字顶对齐', all(abs(c['numTop'] - c['top']) <= TOL for c in cs[1:]), ctx, str([(round(c['numTop'], 1), round(c['top'], 1)) for c in cs[1:3]]))
        rec('e 卡片文字和图不重叠（间隔 >= 8）', all(c['gapTile'] >= 8 for c in cs), ctx, str(min(c['gapTile'] for c in cs)))
        for k in ('h3lh', 'plh', 'slh', 'h3', 'pfs', 'sfs'):
            rec('g 卡片内字号/行高每张一致 ' + k, len(set(round(c[k], 1) for c in cs)) == 1, ctx, str(sorted(set(round(c[k], 1) for c in cs))))
    # d 对齐
    for a in o['al']:
        rec('d ' + a['name'] + ' <= 2px', a['d'] <= 2, ctx, f"{a['d']:.1f}")
    for c in o['chipc']:
        rec('d chip/按钮里文字垂直居中 <= 2px', c['d'] <= 2, ctx, f"{c['who']} {c['d']:.1f}")
    if o.get('mine'):
        m = o['mine']
        rec('d “我的行程”按钮：图标和字的间距 <= 8，左右内边距相等', m['gap'] <= 8 and abs(m['pl'] - m['pr']) <= 2, ctx, f"图标到字 {m['gap']:.0f}，左 {m['pl']:.0f} 右 {m['pr']:.0f}")
    rec('d 搜索框和“搜”中线一致', o['search_txt']['d'] <= TOL, ctx)
    ch = o['chan']
    gr = o['grid']
    rec('b 频道是 2×2：四格，第一行两格同顶、第二行两格同顶、两列左缘各自对齐', len(gr) == 4 and abs(gr[0]['t'] - gr[1]['t']) <= TOL and abs(gr[2]['t'] - gr[3]['t']) <= TOL and abs(gr[0]['l'] - gr[2]['l']) <= TOL and abs(gr[1]['l'] - gr[3]['l']) <= TOL and gr[2]['t'] > gr[0]['b'] - TOL, ctx, str([(round(x['l']), round(x['t'])) for x in gr]))
    rec('b 频道 2×2 的行距、列距都是 8，四格等宽', len(gr) == 4 and abs(gr[2]['t'] - gr[0]['b'] - 8) <= TOL and abs(gr[1]['l'] - gr[0]['r'] - 8) <= TOL and max(x['w'] for x in gr) - min(x['w'] for x in gr) <= TOL, ctx, str([(round(x['w']), round(x['h'])) for x in gr]))
    rec('d 频道格里字的左内边距四格相同', len(set(round(c['pl'], 1) for c in ch)) == 1, ctx, str([round(c['pl'], 1) for c in ch]))
    rec('d 频道格里标题和副标题左缘一致', all(c['dl'] <= TOL for c in ch), ctx)
    rec('d 频道格副标题不换行（不出现落单字）', all(c['sh'] <= c['sfs'] * 1.6 for c in ch), ctx, str([round(c['sh'], 1) for c in ch]))
    # e 溢出
    for r in o['rows']:
        if r['over']:
            rec('e 横向滚动的行铺到版心边缘（不在内容区中间被切）', r['r'] >= r['ar'] - TOL and (r['l'] <= r['al'] + TOL or 'pkr' in r['name']), ctx, f"{r['name']} {r['l']:.0f}–{r['r']:.0f}，版心 {r['al']:.0f}–{r['ar']:.0f}")
    rec('e 搜索框占位字放得下', o['ph']['w'] <= o['ph']['avail'], ctx, f"占位字总宽（含内边距） {o['ph']['w']:.0f} > 可用 {o['ph']['avail']:.0f}（{o['ph']['fs']}）")
    rec('e 文字没有被无声截断', not o['clip'], ctx, '; '.join(o['clip'][:3]))
    # f 触控
    for t in o['tap']:
        rec('f 可点元素有效高度 >= 44', t['h'] >= 43.5, ctx, f"{t['name']} = {t['h']:.0f}")
    # g 层级
    rec('g 各区块标题 h2 字号一致', len(set(h['t'] for h in o['h2'] if h['t'])) == 1, ctx, str([h['t'] for h in o['h2']]))
    rec('g 各区块 h2 右侧小字字号一致', len(set(h['s'] for h in o['h2'] if h['s'])) <= 1, ctx, str([h['s'] for h in o['h2']]))
    rec('g 卡片标题 h3 字号一致', len(o['h3']) == 1, ctx, str(o['h3']))

INJECTIONS = {
    # 名称: (css, 应该变红的判据前缀)
    '搜索→频道 间距 8→10': ('.chan2{margin-top:10px!important}', 'b 同一种关系'),
    '频道格左缘 +3': ('.chan2{margin-left:23px!important}', 'a 左缘'),
    '频道变回一行': ('.chan2{flex-wrap:nowrap!important}', 'b 频道是 2×2'),
    '频道行距 8→12': ('.chan2{row-gap:12px!important}', 'b 频道 2×2 的行距'),
    '搜索框高度 44→40': ('.hsearch input{height:40px!important}', 'c 搜索框和“搜”等高'),
    '“改”下沉 6px': ('.datebar .hdt i{position:relative;top:6px}', 'd 日期条'),
    '天数 chip 铺不到边缘': ('.dchips{margin-right:0!important;padding-right:0!important}', 'e 横向滚动的行'),
}

with sync_playwright() as p:
    br = p.chromium.launch()
    for (w, h) in VIEWPORTS:
        if ONLY and str(w) != ONLY: continue
        for scheme in ('light', 'dark'):
            if INJECT and (scheme == 'dark' or w != 390): continue
            c = br.new_context(viewport={'width': w, 'height': h}, color_scheme=scheme, is_mobile=w < 600, has_touch=w < 600, device_scale_factor=1)
            pg = c.new_page()
            pg.route(re.compile(r'.*(open-meteo|amap|baidu|googletagmanager).*'), lambda r: r.abort())
            def run(style=None):
                pg.goto(B + '/', wait_until='networkidle'); pg.wait_for_timeout(500)
                if style: pg.add_style_tag(content=style); pg.wait_for_timeout(100)
                out = {}
                out['base'] = pg.evaluate(JS, 'base')
                pg.evaluate("document.querySelector('.pick .pkh').click()"); pg.wait_for_timeout(200)
                out['pick'] = pg.evaluate(JS, 'pick')
                pg.evaluate("document.querySelector('.pick .pkh').click()")
                pg.evaluate("(()=>{const m=document.querySelector('#now .moreb');m&&m.click()})()"); pg.wait_for_timeout(200)
                out['more'] = pg.evaluate(JS, 'more')
                return out
            if not INJECT:
                out = run()
                for st in ('base', 'pick', 'more'):
                    judge(out[st], f'{w}×{h} {scheme} {st}', w, st)
                # 挑三条展开时也量间距（judge 里 state != base 只做溢出），单独量一遍 pick 的节奏
                o = out['pick']
                for g in o['gaps']:
                    if g['name'].startswith('挑三条'):
                        rec('b 竖向间距取自 {8,12,16,24,32}', any(abs(g['v'] - s) <= TOL for s in SET), f'{w}×{h} {scheme} pick', f"{g['name']} = {g['v']:.1f}")
                        rec('b 同一种关系同一个间距（见 GAPS 表）', abs(g['v'] - GAPS[g['name']]) <= TOL, f'{w}×{h} {scheme} pick', f"{g['name']} = {g['v']:.1f}，应为 {GAPS[g['name']]}")
                for e in o['edges']:
                    if e['name'].startswith('挑三条'):
                        rec('a 左缘落在栅格线上（所有区块同一条线）', abs(e['l'] - o['L']) <= TOL, f'{w}×{h} {scheme} pick', f"{e['name']} {e['l']:.1f}")
                for r in o['rows']:
                    if r['over']:
                        rec('e 横向滚动的行铺到版心边缘（不在内容区中间被切）', r['r'] >= r['ar'] - TOL and (r['l'] <= r['al'] + TOL or 'pkr' in r['name']), f'{w}×{h} {scheme} pick', r['name'])
                for t in o['tap']:
                    rec('f 可点元素有效高度 >= 44', t['h'] >= 43.5, f'{w}×{h} {scheme} pick', f"{t['name']} = {t['h']:.0f}")
                for e in o['eq']:
                    rec('c ' + re.sub(r'第\d行', '第N行', e['name']), max(e['hs']) - min(e['hs']) <= TOL, f'{w}×{h} {scheme} pick', str(e['hs']))
                for a in o['chipc']:
                    rec('d chip/按钮里文字垂直居中 <= 2px', a['d'] <= 2, f'{w}×{h} {scheme} pick', f"{a['who']} {a['d']:.1f}")
            else:
                for name, (css, prefix) in INJECTIONS.items():
                    fails.clear(); oks.clear()
                    out = run(css)
                    judge(out['base'], f'{w}×{h} {scheme} base', w, 'base')
                    hit = [k for k in fails if k.startswith(prefix)]
                    print(('红（正确）' if hit else '没红（判据有洞）'), '·', name, '→', hit[:1])
                    if not hit: sys.exit(2)
            c.close()
    br.close()

if INJECT:
    print('反向注入：每一处改坏都被抓到'); sys.exit(0)
for k in sorted(set(oks) - set(fails)): print('✓', k)
for k, v in sorted(fails.items()):
    print('✗', k, f'（{len(v)} 处）')
    for x in v[:6]: print('     ', x)
    if len(v) > 6: print(f'      … 另 {len(v) - 6} 处')
print(f'\n{len(set(oks) - set(fails))} 条过 · {len(fails)} 条红')
sys.exit(1 if fails else 0)
