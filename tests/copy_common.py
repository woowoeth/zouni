"""copy_audit.py / copy_check.py 共用：在 390×844 里把每个弹层、选择器、提示条、地图卡片的文字逐个取出来（2026-10-21「文字预算」）。

walk(env, p) → 记录列表，每条 {where, kind, main, sub, note}：
  kind = 'opt'   弹层里的一个选项（按钮 / 链接）：main = 主标题，sub = 副标题（small）
  kind = 'note'  弹层里的说明段（.xnote / .xg / .pk-tip）
  kind = 'head'  弹层标题
  kind = 'toast' 提示条
  kind = 'ctl'   页面上的控件（按钮 / 标签 / 小标题）
"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

LAUNCH = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
FXD = os.path.join(ROOT, 'tests', 'fixtures')
PNG = open(os.path.join(FXD, 'ofm_blank.png'), 'rb').read()
CORS = {'access-control-allow-origin': '*'}


class Stub:
    def __init__(self, c):
        def planet(r): r.fulfill(status=200, content_type='application/json', headers=CORS, body=json.dumps({'tilejson': '2.2.0', 'tiles': ['https://tiles.openfreemap.org/planet/t/{z}/{x}/{y}.pbf'], 'minzoom': 0, 'maxzoom': 14}))
        def pbf(r): r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
        def other(r):
            if r.request.url.split('?')[0].endswith('.json'): r.fulfill(status=200, content_type='application/json', headers=CORS, body='{}')
            elif '/fonts/' in r.request.url: r.fulfill(status=200, content_type='application/x-protobuf', headers=CORS, body=b'')
            else: r.fulfill(status=200, content_type='image/png', headers=CORS, body=PNG)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet$'), planet)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/planet/.+'), pbf)
        c.route(re.compile(r'https://tiles\.openfreemap\.org/(natural_earth|sprites|fonts)/.+'), other)


# 取一个层里所有可见的选项 / 说明 / 标题。root 选择器列表；只取可见的。
HARVEST = r"""(roots)=>{
 const vis=e=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'};
 const tx=e=>(e.textContent||'').replace(/\s+/g,' ').trim();
 const out=[];const seen=new Set();
 document.querySelectorAll(roots).forEach(root=>{if(!vis(root))return;
  root.querySelectorAll('.pk-h b, .tvh b, .tv-h b, h2, h3, h4').forEach(h=>{if(vis(h)&&!seen.has(h)){seen.add(h);out.push({kind:'head',main:tx(h),sub:'',cls:h.className||h.tagName})}});
  root.querySelectorAll('button, a').forEach(b=>{if(!vis(b)||seen.has(b))return;seen.add(b);
    if(b.classList.contains('pk-x')||b.classList.contains('pk-bk')||b.classList.contains('tvx')||b.classList.contains('hz-x'))return;
    const sm=b.querySelector('small'),bb=b.querySelector(':scope > b');
    let sub=sm?tx(sm):'';let main=bb?tx(bb):tx(b);if(!bb&&sm)main=tx(b).replace(sub,'').trim();
    // 主标题里的小徽章（已加）不算副标题但算字数
    const dyn=b.matches('[data-rid],.npc,.mr,.mrx,.mrc,.rm-seg,.rm-tb,.rm-pi,.cmpb,.tvtabs button');
    // 备注类小字（已排过）不算副标题长度，单独带出
    out.push({kind:'opt',main:main,sub:sub,cls:b.className||'',disabled:!!b.disabled,dyn:dyn})});
  root.querySelectorAll('.xnote, .xg, .pk-tip, p.xnote, .allck, .pk-jump').forEach(n=>{if(vis(n)&&!seen.has(n)){seen.add(n);let t=tx(n);const an=n.querySelector('.adjn');if(an)t=t.replace(tx(an),'').trim();if(t||!an)out.push({kind:'note',main:t,sub:'',cls:n.className||''})}});
 });return out}"""


NOISE = re.compile(r'^[\d:‹›+−i×\s]*$')


def harvest(pg, roots='.pk, .tv, .rm-sheet'):
    return [r for r in pg.evaluate(HARVEST, roots) if not (r['kind'] == 'opt' and (NOISE.match(r['main']) and not r['sub']))]


def dismiss(pg):
    pg.evaluate("while(window.ZL&&ZL.depth()>0)history.back()") if False else None
    pg.keyboard.press('Escape'); pg.wait_for_timeout(250)
    for _ in range(3):
        if pg.evaluate("window.ZL?ZL.depth():0") > 0:
            pg.evaluate("history.back()"); pg.wait_for_timeout(300)


def add(rows, where, items):
    for it in items:
        it = dict(it); it['where'] = where; rows.append(it)


def scroll_click(pg, sel, nth=0):
    pg.evaluate("(a)=>{var e=document.querySelectorAll(a[0])[a[1]];if(e)e.scrollIntoView({block:'center',behavior:'instant'})}", [sel, nth])
    pg.locator(sel).nth(nth).click()


def ctl_scan(pg, where, rows):
    """页面本身：按钮 / 链接 / 标签 / 小标题的文字（只取短的，去重）"""
    items = pg.evaluate(r"""()=>{const vis=e=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'};
      const tx=e=>(e.textContent||'').replace(/\s+/g,' ').trim();const out=[],seen={};
      document.querySelectorAll('button, [role=button], summary, label, .kick, .sec-h, section > h2, article > h2, h3, .chip, .tab, .xnote, .note, small, .hint, .sub, .cap').forEach(e=>{
        if(!vis(e))return;if(e.closest('.pk,.tv,.rm,.toast'))return;const t=tx(e);if(!t||t.length>60)return;const k=e.tagName+'|'+t;if(seen[k])return;seen[k]=1;
        out.push({kind:'ctl',main:t,sub:'',cls:(e.className&&e.className.baseVal===undefined?e.className:'')||e.tagName.toLowerCase()})});return out.slice(0,120)}""")
    add(rows, where, items)


def walk(env, p, log=print):
    rows = []
    br = p.chromium.launch()
    bm = p.chromium.launch(args=LAUNCH)

    def page(path, w=390, h=844, storage=None, browser=None, stub=False, wait=700):
        c = new_ctx(browser or br, p, w, h, storage=storage)
        if stub: Stub(c)
        pg = new_page(env, c); goto(env, pg, path, wait); return c, pg

    def step(name, fn):
        try: fn()
        except Exception as e: env.fails.append('walk %s：中途出错（%s）' % (name, str(e).strip().splitlines()[0][:160])); log('  ! %s: %s' % (name, str(e)[:120]))

    # —— 静态页：首页、走哪儿、长线、跟片走、目的地页、行程页 —— #
    for nm, path in [('首页', '/'), ('/where/', '/where/'), ('/long/', '/long/'), ('/follow/', '/follow/'), ('/pian/', '/pian/'), ('目的地页', '/d/xian/' if os.path.isdir(os.path.join(env.site, 'd', 'xian')) else '/d/'), ('行程页', '/trip/xa3/')]:
        def f(nm=nm, path=path):
            c, pg = page(path); ctl_scan(pg, nm, rows); c.close()
        step('页面 ' + nm, f)

    # —— 行程页里的各个弹层 —— #
    c, pg = page('/trip/xa3/')
    step('分享', lambda: (pg.click('.share'), pg.wait_for_selector('.pk'), pg.wait_for_timeout(250), add(rows, '行程页 › 分享', harvest(pg)), env.shots and pg.screenshot(path=os.path.join(env.shots, 'share.png')), dismiss(pg)))
    step('选日期', lambda: (pg.click('.glance .dt'), pg.wait_for_selector('.pk'), pg.wait_for_timeout(250), add(rows, '行程页 › 选日期', harvest(pg)), env.shots and pg.screenshot(path=os.path.join(env.shots, 'date.png')), dismiss(pg)))
    step('几点出发', lambda: (scroll_click(pg, '#d1 .st'), pg.wait_for_selector('.pk'), pg.wait_for_timeout(250), add(rows, '行程页 › 几点出发', harvest(pg)), dismiss(pg)))
    step('加一天', lambda: (scroll_click(pg, '.addday .add'), pg.wait_for_selector('.pk'), pg.wait_for_timeout(500), add(rows, '行程页 › 加一天', harvest(pg)), env.shots and pg.screenshot(path=os.path.join(env.shots, 'addday.png')), dismiss(pg)))
    step('改这一天', lambda: (scroll_click(pg, '#d2 .dayadj'), pg.wait_for_selector('.pk .xd'), pg.wait_for_timeout(250), add(rows, '行程页 › 改这一天', harvest(pg)), env.shots and pg.screenshot(path=os.path.join(env.shots, 'dayadj.png')), dismiss(pg)))

    def adj():
        n = pg.evaluate("document.querySelectorAll('#d1 .tl .adj, #d2 .tl .adj').length")
        got = {'dis': False, 'ok': False}
        for i in range(n):
            if got['dis'] and got['ok']: break
            pg.evaluate("(i)=>{var e=document.querySelectorAll('#d1 .tl .adj, #d2 .tl .adj')[i];e.scrollIntoView({block:'center',behavior:'instant'});e.click()}", i)
            pg.wait_for_selector('.pk .xd'); pg.wait_for_timeout(900)
            ins = pg.locator('.pk [data-np="ins"]')
            if ins.count() and ins.first.is_disabled() and not got['dis']:
                got['dis'] = True; add(rows, '行程页 › 改这一站', harvest(pg))
                if env.shots: pg.screenshot(path=os.path.join(env.shots, 'adj_gray.png'))
            elif ins.count() and not ins.first.is_disabled() and not got['ok']:
                got['ok'] = True; add(rows, '行程页 › 改这一站', harvest(pg))
                if env.shots: pg.screenshot(path=os.path.join(env.shots, 'adj.png'))
                for kind, lab in (('ins', '在这之后加一个'), ('rep', '换成')):
                    b = pg.locator('.pk [data-np="%s"]' % kind)
                    if b.count() and not b.first.is_disabled():
                        b.first.click(); pg.wait_for_selector('.pk .npc, .pk .npe', timeout=20000); pg.wait_for_timeout(300)
                        add(rows, '行程页 › 改这一站 › ' + lab, harvest(pg))
                        if env.shots and kind == 'ins': pg.screenshot(path=os.path.join(env.shots, 'adj_ins.png'))
                        pg.click('.pk .pk-bk'); pg.wait_for_timeout(300)
            dismiss(pg)
    step('改这一站', adj)

    def todo():
        scroll_click(pg, '.todoall'); pg.wait_for_selector('.tv.todo'); pg.wait_for_timeout(300)
        add(rows, '行程页 › 出发前要办的事', harvest(pg, '.tv.todo'))
        dismiss(pg)
    step('出发前', todo)

    def tv():
        pg.click('.tvbtn'); pg.wait_for_selector('.tv'); pg.wait_for_timeout(300)
        add(rows, '行程页 › 按天看', harvest(pg, '.tv'))
        dismiss(pg)
    step('按天看', tv)

    def copybox():
        pg.evaluate("navigator.clipboard.writeText=function(){return Promise.reject(new Error('x'))};0")
        pg.click('.share'); pg.wait_for_selector('.pk'); pg.click('.pk [data-a="copy"]'); pg.wait_for_selector('.pk textarea'); pg.wait_for_timeout(300)
        add(rows, '行程页 › 复制框', harvest(pg)); dismiss(pg)
    step('复制框', copybox)

    def toasts():
        pg.evaluate("document.querySelector('.fav').scrollIntoView({block:'center',behavior:'instant'})")
        pg.click('.fav'); pg.wait_for_timeout(500)
        add(rows, '提示条 › 收进行程', pg.evaluate("[...document.querySelectorAll('.toast')].map(t=>({kind:'toast',main:t.textContent.trim(),sub:'',cls:'t'}))"))
        pg.click('.fav'); pg.wait_for_timeout(500)
        add(rows, '提示条 › 拿掉行程', pg.evaluate("[...document.querySelectorAll('.toast')].map(t=>({kind:'toast',main:t.textContent.trim(),sub:'',cls:'t'}))"))
    step('toast', toasts)
    c.close()

    # 去掉一站的 toast
    def rmstop():
        c, pg = page('/trip/xa3/')
        scroll_click(pg, '#d1 .tl > .r.see .adj'); pg.wait_for_selector('.pk .xd'); pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(600)
        add(rows, '提示条 › 去掉一站', pg.evaluate("[...document.querySelectorAll('.toast')].map(t=>({kind:'toast',main:t.textContent.trim(),sub:'',cls:'t'}))"))
        c.close()
    step('去掉一站', rmstop)

    # 去掉一天：整页重载后的 toast + 提示条
    def rmday():
        c, pg = page('/trip/xa3/')
        scroll_click(pg, '#d2 .dayadj'); pg.wait_for_selector('.pk .xd'); pg.click('.pk .rmgo'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(1500)
        add(rows, '提示条 › 去掉一天', pg.evaluate("[...document.querySelectorAll('.toast')].map(t=>({kind:'toast',main:t.textContent.trim(),sub:'',cls:'t'}))"))
        add(rows, '行程页 › 去掉一天后的提示条', pg.evaluate("[...document.querySelectorAll('.rmnote')].map(t=>({kind:'ctl',main:t.textContent.trim(),sub:'',cls:'rmnote'}))"))
        c.close()
    step('去掉一天', rmday)

    # 我的行程 / 对比
    def mine():
        fav = json.dumps([{'id': i, 'label': l, 'title': t, 'n': 3, 'sd': '2027-10-15'} for i, l, t in (('xa3', '西安 3 天', '三天，在西安看一千年'), ('tk4', '东京 4 天', '东京四天'))], ensure_ascii=False)
        c, pg = page('/', storage={'zouni_fav': fav})
        pg.click('.minebtn'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(500)
        add(rows, '首页 › 我的行程', harvest(pg))
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'mine.png'))
        add(rows, '首页 › 我的行程', pg.evaluate("[...document.querySelectorAll('.pk .mw')].map(t=>({kind:'when',main:t.textContent.trim(),sub:'',cls:'mw'})).concat([...document.querySelectorAll('.pk .mo')].map(t=>({kind:'when',main:t.textContent.trim(),sub:'',cls:'mo'})))"))
        cmp_ = pg.locator('.pk button:has-text("对比"), .pk .cmp')
        if cmp_.count():
            try:
                cmp_.first.click(); pg.wait_for_timeout(600); add(rows, '首页 › 我的行程 › 对比', harvest(pg))
            except Exception: pass
        c.close()
    step('我的行程', mine)

    def mine_empty():
        c, pg = page('/')
        pg.click('.minebtn'); pg.wait_for_selector('.pk'); pg.wait_for_timeout(400)
        add(rows, '首页 › 我的行程（空）', harvest(pg))
        add(rows, '首页 › 我的行程（空）', pg.evaluate("[...document.querySelectorAll('.pk .mempty')].map(t=>({kind:'note',main:t.textContent.trim(),sub:'',cls:'mempty'}))"))
        c.close()
    step('我的行程（空）', mine_empty)

    # —— 地图 —— #
    def mp():
        c, pg = page('/trip/xa3/', browser=bm, stub=True)
        scroll_click(pg, '#d1 .rm-open'); pg.wait_for_function("window.ZRM&&ZRM.cur()&&ZRM.cur().view&&ZRM.cur().marks", timeout=15000); pg.wait_for_timeout(1000)
        add(rows, '地图 › 底部条', harvest(pg, '.rm'))
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'map_bar.png'))
        mk = pg.locator('.rm-mk, .rm-m').first
        try:
            n = pg.evaluate("(function(){var m=document.querySelectorAll('.rm-card');return m.length})()")
            if n: add(rows, '地图 › 站点卡', harvest(pg, '.rm-card'))
        except Exception: pass
        try:
            pg.evaluate("(function(){var c=ZRM.cur();if(c&&c.select){c.select(c.marks[1]||c.marks[0])}})()"); pg.wait_for_timeout(800)
        except Exception: pass
        add(rows, '地图 › 站点卡（选中）', harvest(pg, '.rm-card, .rm-bar, .rm-dock'))
        if env.shots: pg.screenshot(path=os.path.join(env.shots, 'map_card.png'))
        pg.wait_for_selector('.rm-navd:not([hidden])'); pg.click('.rm-navd'); pg.wait_for_selector('.rm-sheet.rm-dyn'); pg.wait_for_timeout(300)
        add(rows, '地图 › 导航分段', harvest(pg, '.rm-sheet'))
        c.close()
    step('地图', mp)

    br.close(); bm.close()
    return rows


FIXED_WHERE = ('行程页 › 分享', '行程页 › 选日期', '行程页 › 几点出发', '行程页 › 加一天', '行程页 › 改这一天', '行程页 › 改这一站', '行程页 › 复制框', '首页 › 我的行程', '首页 › 我的行程（空）', '地图 › 导航分段')
DYN_CLS = ('npc', 'mr', 'mrx', 'mrc', 'rm-seg', 'rm-tb', 'rm-pi', 'cmpb')


def fixed_total(rows):
    """弹层里“固定文案”的总字数：选项主标题 + 副标题 + 说明 + 标题；不含站名 / 行程名 / 日期格 / 候选列表 / 复制框 / 我的行程 / 导航分段（这些内容是数据）"""
    tot = 0; seen = set()
    for r in rows:
        k_ = (r['where'], r['kind'], r['main'], r['sub'])
        if k_ in seen: continue
        seen.add(k_)
        if r['where'] not in FIXED_WHERE or r['kind'] not in ('opt', 'note', 'head'): continue
        if r['where'] in ('行程页 › 复制框', '首页 › 我的行程', '地图 › 导航分段'): continue
        if r['kind'] == 'opt' and (r.get('dyn') or any(c in (r.get('cls') or '').split() for c in DYN_CLS)): continue
        if r['kind'] == 'opt' and NOISE.match(r['main']) and not r['sub']: continue
        if r['where'] == '行程页 › 加一天' and r['kind'] == 'opt' and r.get('cls', '') == '' and not re.match(r'^(在.*)?多留一天$', r['main']): continue
        if r['where'] == '行程页 › 改这一站' and r['kind'] == 'note': continue      # 站名那一行：数据
        tot += len(r['main']) + len(r['sub'])
    return tot
