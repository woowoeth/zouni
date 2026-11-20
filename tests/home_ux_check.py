#!/usr/bin/env python3
"""首页体验断言（2026-10-16）：把“像用户一样走一遍”的场景做成会红的判据。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/home_ux_check.py build/site            # 全部通过退出码 0，否则 1 并列出每条
    python3 tests/home_ux_check.py build/site --shots /tmp/home_shots   # 同时存截图（给人看，不参与判定）
    python3 tests/home_ux_check.py build/site --inject chan_flat|chan_missing   # 反向自检（2026-10-17，2×2 频道）：只改送到浏览器的页面，必须有判据变红

自己起一个本地静态服务（不占固定端口），用 playwright chromium：
  场景 A  手机第一次打开：390×844 首屏必须同时看到 搜索框 + 频道四格（2×2：走哪儿 / 跟片走 / 跟谁走 / 长线自驾）；封面不吃掉整屏；封面有图
  场景 B  我有 N 天：天数 chip 在“现在去正好”里；点“周末”只剩周末的卡；列表首屏只露 8 张，有“再看”，点一下再多露一批，不丢功能
  场景 C  我知道去哪：搜索框在“替我挑三条”之前；输入后提交到 /where/?q=
  场景 D  逛逛：卡片没有“翻开 ›”按钮、没有重复的“正当季/今天最后一天/xx 月白天…夜里…”多行；整张卡可点
  场景 E  老用户：“我的行程”在首屏，带数量，点开能看到收进的行程
  通用    不再有 .longbar 和跳 /long/ 的天数 chip，首页内容区只有频道一格进 /long/；
          “替我挑三条”默认折叠成一行，点开能选、选满出结果；
          亮色和暗色（prefers-color-scheme）都没有横向溢出，主要文字对比度 >= 4.5；桌面 1280 也看得到搜索和频道
  控制台不许有报错。
"""
import functools, http.server, json, os, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

site = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else os.path.abspath('build/site')
shots = sys.argv[sys.argv.index('--shots') + 1] if '--shots' in sys.argv else None
if shots: os.makedirs(shots, exist_ok=True)
INJECT = sys.argv[sys.argv.index('--inject') + 1] if '--inject' in sys.argv else None
INJ_CSS = {'chan_flat': '.chan2{flex-wrap:nowrap!important}', 'chan_missing': '.chan2 a[href="/follow/"]{display:none!important}'}
if INJECT and INJECT not in INJ_CSS: sys.exit('--inject 只认 ' + ' / '.join(INJ_CSS))

class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site))
threading.Thread(target=srv.serve_forever, daemon=True).start()
B = f'http://127.0.0.1:{srv.server_address[1]}'

fails, oks = [], []
def check(name, cond, detail=''):
    (oks if cond else fails).append(f'{name}' + (f'  → {detail}' if detail and not cond else ''))

LUM = """(c)=>{const m=c.match(/[\\d.]+/g).map(Number);const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return [0.2126*f(m[0])+0.7152*f(m[1])+0.0722*f(m[2]), m.length>3?m[3]:1]}"""
def contrast(pg, sel_fg, sel_bg_chain=None):
    return pg.evaluate("""([sel])=>{const el=document.querySelector(sel);if(!el)return null;
      const L=%s;const fg=getComputedStyle(el).color;let n=el,bg=null;
      while(n){const c=getComputedStyle(n).backgroundColor;const [l,a]=L(c);if(a>0.5){bg=c;break}n=n.parentElement}
      if(!bg)bg=getComputedStyle(document.body).backgroundColor;
      const a=L(fg)[0],b=L(bg)[0];return +((Math.max(a,b)+0.05)/(Math.min(a,b)+0.05)).toFixed(2)}""" % LUM, [sel_fg])

errs = []
with sync_playwright() as p:
    br = p.chromium.launch()
    def ctx(w, h, dark=False, mobile=True, storage=None):
        c = br.new_context(viewport={'width': w, 'height': h}, color_scheme='dark' if dark else 'light', is_mobile=mobile, has_touch=mobile, device_scale_factor=2 if mobile else 1)
        if storage: c.add_init_script('try{' + ''.join(f'localStorage.setItem({json.dumps(k)},{json.dumps(v)});' for k, v in storage.items()) + '}catch(e){}')
        pg = c.new_page()
        pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'open-meteo' not in m.text and 'Failed to load resource' not in m.text else None)
        pg.on('pageerror', lambda e: errs.append('pageerror: ' + str(e)))
        pg.route(re.compile(r'.*(open-meteo|amap|baidu|googletagmanager|hm\.baidu).*'), lambda r: r.abort())
        return c, pg
    def load(pg):
        pg.goto(B + '/', wait_until='networkidle'); pg.wait_for_timeout(600)
        if INJECT: pg.add_style_tag(content=INJ_CSS[INJECT]); pg.wait_for_timeout(100)
    R = lambda pg, sel: pg.evaluate("(s)=>{const e=document.querySelector(s);if(!e)return null;const r=e.getBoundingClientRect();return {t:r.top+scrollY,b:r.bottom+scrollY,l:r.left,r:r.right,h:r.height,w:r.width,vis:!e.hidden&&r.height>0}}", sel)

    # ———— 手机 · 亮色 ————
    c, pg = ctx(390, 844); load(pg)
    # 通用：重复入口
    check('通用 无 .longbar', pg.locator('.longbar').count() == 0)
    check('通用 天数 chip 里无链接', pg.locator('.dchips a').count() == 0)
    n_long = pg.evaluate("document.querySelectorAll('article.home a[href=\"/long/\"]').length")
    check('通用 首页内容区只有 1 处指向 /long/（频道那一格）', n_long == 1, f'{n_long} 处')
    n_w = pg.evaluate("document.querySelectorAll('article.home a[href=\"/where/\"]').length")
    check('通用 首页内容区只有 1 处指向 /where/（频道那一格；列表后面的“全部目的地”长条是重复入口，已去掉）', n_w == 1, f'{n_w} 处')
    chan = pg.evaluate("[...document.querySelectorAll('.chan2 a')].map(a=>a.getAttribute('href'))")
    check('通用 频道四格 = /where/ /pian/ /follow/ /long/（走哪儿 / 跟片走 / 跟谁走 / 长线自驾）', chan == ['/where/', '/pian/', '/follow/', '/long/'], str(chan))
    # A：首屏
    s, ch = R(pg, '.hsearch'), [R(pg, f'.chan2 a:nth-child({i})') for i in (1, 2, 3, 4)]
    check('A 390×844 首屏看得到搜索框', bool(s) and s['b'] <= 844, str(s))
    check('A 频道是 2×2（第 1、2 格同一行，第 3、4 格在下一行，两列各自左对齐）', all(ch) and abs(ch[0]['t'] - ch[1]['t']) <= 1 and abs(ch[2]['t'] - ch[3]['t']) <= 1 and ch[2]['t'] >= ch[0]['b'] - 1 and abs(ch[0]['l'] - ch[2]['l']) <= 1 and abs(ch[1]['l'] - ch[3]['l']) <= 1, str([x and (round(x['l']), round(x['t'])) for x in ch]))
    check('A 390×844 首屏看得到频道四格', all(x and x['b'] <= 844 for x in ch), str([x and x['b'] for x in ch]))
    cov = R(pg, '.cover')
    check('A 封面不吃掉整屏（高 <= 380）', cov and cov['h'] <= 380, str(cov and cov['h']))
    img = pg.evaluate("(()=>{const i=document.querySelector('.cover img');return i?{ok:i.complete&&i.naturalWidth>0,src:i.getAttribute('src')}:null})()")
    check('A 封面有图且加载成功', bool(img and img['ok']), str(img))
    check('A 首屏有“翻开”封面入口', (R(pg, '.cv .go') or {'b': 9999})['b'] <= 844)
    pk = R(pg, '.pick')
    check('A 首屏看到“替我挑三条”那一行', bool(pk) and pk['t'] < 844 - 20, str(pk))
    # C：顺序
    check('C 搜索框在“替我挑三条”之前', s and pk and s['t'] < pk['t'])
    check('C 搜索框在“现在去正好”之前', s['t'] < R(pg, '#now')['t'])
    # 替我挑三条：折叠
    check('通用 替我挑默认折叠（.pkb 隐藏）', pg.evaluate("document.querySelector('.pick .pkb').hidden===true"))
    check('通用 替我挑折叠时只占一行（<= 80）', pk and pk['h'] <= 80, str(pk and pk['h']))
    pg.click('.pick .pkh'); pg.wait_for_timeout(200)
    pk2 = R(pg, '.pick')
    check('通用 替我挑展开后 4 个问题 <= 340 高（原来 > 560）', pk2['h'] <= 340, str(pk2['h']))
    pg.click('.pkr[data-k="o"] button[data-v="北京"]'); pg.click('.pkr[data-k="d"] button[data-v="w"]'); pg.click('.pkr[data-k="w"] button[data-v="f"]'); pg.wait_for_timeout(300)
    nres = pg.locator('.pkres li').count()
    check('通用 替我挑选满三项后出结果（功能保留）', nres >= 1, f'{nres} 条')
    hs = pg.evaluate("document.querySelector('.pick .pkh small').innerText")
    check('通用 替我挑折叠头显示已选项', '北京' in hs, hs)
    pg.click('.pick .pkh'); pg.wait_for_timeout(150)
    check('通用 再点一下收起', pg.evaluate("document.querySelector('.pick .pkb').hidden===true"))
    # D/B：列表
    vis = lambda: pg.evaluate("[...document.querySelectorAll('.now .items li')].filter(l=>!l.hidden).length")
    n0 = vis()
    check('D 列表首屏之后只露 8 张', n0 == 8, str(n0))
    mb = pg.locator('.now .moreb')
    check('D 有“再看”按钮', mb.count() == 1 and mb.is_visible())
    mb_txt = mb.inner_text()
    mb.click(); pg.wait_for_timeout(200)
    n1 = vis()
    check('D 点“再看”再露一批（不是一次全展开）', 8 < n1 < 40, f'{n0}→{n1}')
    check('D “再看”文字带还剩多少', re.search(r'再看 \d+ 条', mb_txt) is not None, mb_txt)
    tot = pg.evaluate("document.querySelectorAll('.now .items li').length")
    check('D 全部条目都还在（不丢功能：>=100 条，逐批翻）', tot >= 100, str(tot))
    card = pg.evaluate("""(()=>{const l=[...document.querySelectorAll('.now .items li')].filter(x=>!x.hidden);return {open:document.querySelectorAll('.items .open').length,
        fan:[...document.querySelectorAll('.items')].some(o=>/翻开 ›/.test(o.innerText)),
        avg:Math.round(l.reduce((a,x)=>a+x.getBoundingClientRect().height,0)/l.length),
        monthTxt:l.some(x=>/月白天/.test(x.innerText)),
        links:l.every(x=>x.querySelector('h3 a'))}})()""")
    check('D 卡片没有“翻开 ›”按钮', card['open'] == 0 and not card['fan'], str(card))
    check('D 卡片平均高度 <= 150（原来约 217）', card['avg'] <= 150, str(card['avg']))
    check('D 卡片不再写“10 月白天 xx℃，夜里 xx℃”整句', not card['monthTxt'])
    check('D 每张卡标题是链接，整张卡可点', card['links'])
    stretch = pg.evaluate("(()=>{const a=document.querySelector('.now .items li:not([hidden]) h3 a');const r=getComputedStyle(a,'::after');const li=a.closest('li');return r.position==='absolute'&&getComputedStyle(li).position==='relative'})()")
    check('D 标题链接的 ::after 铺满整张卡', stretch)
    # B：天数
    dts = R(pg, '.now .datebar')
    check('B 出发日期条在“现在去正好”里（不再压在封面上）', dts is not None and R(pg, '#now')['t'] <= dts['t'] <= R(pg, '.now .items')['t'])
    if pg.evaluate("document.querySelector('.dchips button[data-b=\"d1\"]').classList.contains('on')"): pg.click('.dchips button[data-b="d1"]'); pg.wait_for_timeout(150)      # 2026-10-19：向导里选了“周末”已经点亮了这个键（同一个状态）：先取消再点，让“再看”展开的条数复位
    pg.click('.dchips button[data-b="d1"]')
    pg.wait_for_timeout(200)
    onlyd1 = pg.evaluate("[...document.querySelectorAll('.now .items li')].filter(l=>!l.hidden).every(l=>l.dataset.band==='d1')")
    check('B 点“周末 2–3 天”只剩周末的卡', onlyd1 and vis() == 8, str(vis()))
    pg.click('.dchips button[data-b="d1"]')      # 2026-10-19：没有“全部”键了，再点一次选中的就取消
    # C：搜索提交
    pg.fill('.hsearch input', '敦煌'); pg.press('.hsearch input', 'Enter'); pg.wait_for_url(re.compile(r'/where/\?q='), timeout=8000)
    check('C 搜“敦煌”跳到 /where/?q=', 'q=' in pg.url, pg.url)
    c.close()

    # 横向溢出 + 截图 + 对比度（亮/暗）
    for dark in (False, True):
        c, pg = ctx(390, 844, dark=dark); load(pg)
        tag = '暗色' if dark else '亮色'
        ov = pg.evaluate("document.documentElement.scrollWidth-innerWidth")
        check(f'通用 {tag} 无横向溢出', ov <= 0, str(ov))
        for sel in ('.hsearch input', '.chan2 b', '.chan2 small', '.pick .pkh b', '.now h2 .nt', '.now .ns', '.now .datebar b', '.items li:not([hidden]) h3 a', '.items li:not([hidden]) p', '.items li:not([hidden]) small', '.items li:not([hidden]) .left'):
            if sel == '.hsearch input': continue
            ct = contrast(pg, sel)
            check(f'通用 {tag} 对比度 {sel} >= 4.5', ct is not None and ct >= 4.5, str(ct))
        pkbg = pg.evaluate("[getComputedStyle(document.querySelector('.pick .pkh')).backgroundColor,getComputedStyle(document.body).backgroundColor]")
        check(f'通用 {tag} 替我挑那一行和页面底色有区别', pkbg[0] != pkbg[1], str(pkbg))
        if shots:
            pg.screenshot(path=f'{shots}/home_390_{"dark" if dark else "light"}_fold.png')
            if not dark:
                pg.click('.pick .pkh'); pg.wait_for_timeout(200); pg.locator('.pick').screenshot(path=f'{shots}/home_390_pick_open.png')
                pg.reload(wait_until='networkidle'); pg.wait_for_timeout(500); pg.screenshot(path=f'{shots}/home_390_full.png', full_page=True)
        c.close()

    # E：老用户
    fav = [{'id': 'sx4', 'label': '测试线路', 'title': '测试线路 · 4 天'}]
    c, pg = ctx(390, 844, storage={'zouni_fav': json.dumps(fav)}); load(pg)
    mine = pg.evaluate("(()=>{const b=document.querySelector('.minebtn');const r=b.getBoundingClientRect();return {t:b.innerText.replace(/\\s+/g,' ').trim(),bottom:r.bottom,top:r.top}})()")
    check('E “我的行程”在首屏且带数量', '我的行程 · 1' in mine['t'] and mine['bottom'] <= 844, str(mine))
    pg.click('.minebtn'); pg.wait_for_timeout(300)
    check('E 点开后看得到收进的行程', pg.evaluate("/测试线路/.test(document.querySelector('.pk')?.innerText||'')"))
    c.close()

    # 桌面 1280
    c, pg = ctx(1280, 800, mobile=False); load(pg)
    s, ch = R(pg, '.hsearch'), [R(pg, f'.chan2 a:nth-child({i})') for i in (1, 2, 3, 4)]
    check('通用 桌面 1280×800 首屏看得到搜索和频道四格', s['b'] <= 800 and all(x['b'] <= 800 for x in ch))
    check('通用 桌面无横向溢出', pg.evaluate("document.documentElement.scrollWidth-innerWidth") <= 0)
    if shots: pg.screenshot(path=f'{shots}/home_1280_fold.png')
    c.close()
    br.close()

check('通用 控制台没有报错', not errs, '; '.join(errs[:5]))
for x in oks: print('✓', x)
for x in fails: print('✗', x)
print(f'\n{len(oks)} 过 · {len(fails)} 红')
if INJECT:
    hit = [f for f in fails if '频道' in f or '2×2' in f]
    print(('红（正确）' if hit else '没红（判据有洞）'), '·', INJECT, '→', hit[:1]); sys.exit(0 if hit else 2)
sys.exit(1 if fails else 0)
