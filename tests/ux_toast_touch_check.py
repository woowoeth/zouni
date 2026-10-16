#!/usr/bin/env python3
"""撤销提示条 + 触控目标与误触（2026-10-17，任务单第 3、4 组）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/ux_toast_touch_check.py build/site [--shots DIR]
    python3 tests/ux_toast_touch_check.py build/site --inject toast_long|toast_stack|no_undo|small_x    # 反向自检

第 3 组 撤销
  T1 “去掉这一站”后提示条带“撤销”按钮（≥44 高），点了这一站回来、存的键和去掉前逐字一致
  T2 提示条停留约 5 秒（4 秒时还在、6.5 秒时已没）
  T3 点别处立刻收起；打开弹层时收起；连着做两件事只有一条提示条（不叠）
  T4 老入口“恢复”还在，点击区 ≥44×44，点了恢复整天
  T5 去掉一天：确认弹层 → 去掉 → 马上有“撤销”提示条，点了天数回来
第 4 组 触控与误触
  T6 点击区（elementFromPoint 实测，含伪元素）≥44×44：调整、日期格、出发时间“改”、恢复、去掉这一天、这天后面加一天、收进行程、按天看、返回/首页/分享、
     提示条上的撤销、各弹层的“关上”（右上和底部）、日历格和翻月键；首页的日期条（点“改”那个字也行）、我的行程、再看、替我挑、天数 chip
  T7 去掉这一天 与 这天后面加一天：间距 ≥16px、高 ≥44、破坏性的在右边；去掉一天要确认弹层
  T8 弹层里按钮文字上下居中（文字块中心和按钮中心差 ≤3px）
  T9 弹层底部“关上”真的能关；ESC/遮罩原来的关法不坏
"""
import json, os, re, sys, time
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'toast_long': ('assets/site.js', "ms||(label?5000:1700)", "ms||(label?10000:1700)"),          # 提示条又停 10 秒
    'toast_stack': ('assets/site.js', ["function toast(t,label,fn,ms){toastOff();", "var ts=document.querySelectorAll('.toast');for(var i=0;i<ts.length;i++){if(!ts[i].contains(e.target)){clearTimeout(ts[i]._tm);ts[i].remove()}}"], ["function toast(t,label,fn,ms){", ""]),   # 新提示不顶掉旧的、点别处也不收 → 叠起来（两条机制都拿掉才算）
    'no_undo': ('assets/site.js', "ztrack('去掉一站');toast('去掉了「'+npCore(nmx)+'」，后面的时间往前挪了','撤销',function(){undo0();replan(sec);toast('撤销了，「'+npCore(nmx)+'」回来了')})", "ztrack('去掉一站');toast('去掉了「'+npCore(nmx)+'」，后面的时间往前挪了')"),   # 去掉这一站不给撤销
    'small_x': ('assets/site.js', "x.className='pk-xb';", "x.className='pk-xb';x.style.display='none';"),                                                                 # 底部“关上”藏起来（点击区的判据要红）
}
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
env = Env(INJ)
check, guard = env.check, env.guard

with sync_playwright() as p:
    br = p.chromium.launch()

    def shot(pg, name):
        if env.shots: pg.screenshot(path=os.path.join(env.shots, name))

    # ———— 第 3 组 ————
    with guard('T1-T4'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        k0 = {k: ls(pg, k) for k in ('zouni_drop_xa3', 'zouni_np_xa3', 'zouni_adj_xa3')}
        row = pg.locator('#d2 .tl > .r.see').nth(1)         # 华清宫
        name = row.evaluate("r=>r.querySelector('.m').childNodes[0].textContent.trim()")
        row.locator('.adj').click(); pg.wait_for_selector('.pk')
        pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(300)
        check('T1 去掉后这一站被藏起来', row.evaluate("r=>r.hidden"))
        t = pg.locator('.toast'); act = pg.locator('.toast .toast-act')
        check('T1 提示条出现，只有 1 条', t.count() == 1, t.count())
        check('T1 提示条上有“撤销”按钮', act.count() == 1 and act.inner_text().strip() == '撤销', act.count())
        bb = act.bounding_box() if act.count() else None
        check('T1 “撤销”按钮高 ≥44px、宽 ≥44px', bb and bb['height'] >= 44 and bb['width'] >= 44, bb)
        h = pg.evaluate(HIT, act.element_handle()) if act.count() else None
        check('T1 “撤销”实际点击区 ≥44×44（elementFromPoint 实测）', h and h['w'] >= 44 and h['h'] >= 44, h)
        shot(pg, 'T1_toast_undo.png')
        t_start = time.time()
        # T2 时长
        pg.wait_for_timeout(3600)
        check('T2 4 秒左右提示条还在', pg.locator('.toast').count() == 1, pg.locator('.toast').count())
        pg.wait_for_function("document.querySelectorAll('.toast').length===0", timeout=6000)
        el = time.time() - t_start
        check('T2 提示条停留约 5 秒（实测 %.1f 秒，要求 4–6.5）' % el, 4.0 <= el <= 6.5, '%.1f' % el)
        # 提示条没了，用旧入口“恢复”还原这一天
        rs = pg.locator('#d2 .latewarn .reset')
        check('T4 老入口“恢复”还在', rs.count() == 1, rs.count())
        hh = pg.evaluate(HIT, rs.element_handle()) if rs.count() else None
        check('T4 “恢复”实际点击区 ≥44×44', hh and hh['w'] >= 44 and hh['h'] >= 44, hh)
        shot(pg, 'T4_reset.png')
        rs.click(); pg.wait_for_timeout(400)
        check('T4 点“恢复”后这一站回来', not row.evaluate("r=>r.hidden"))
        # 再去掉一次，用提示条上的撤销
        row.locator('.adj').click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(300)
        pg.locator('.toast .toast-act').click(); pg.wait_for_timeout(400)
        k1 = {k: ls(pg, k) for k in ('zouni_drop_xa3', 'zouni_np_xa3', 'zouni_adj_xa3')}
        k1n = {k: (None if v in ('{}', '[]') else v) for k, v in k1.items()}
        check('T1 点“撤销”后这一站回来（「%s」）' % name, not row.evaluate("r=>r.hidden"))
        check('T1 撤销后存的键和去掉前一致', all((k1n[k] or None) in ((k0[k] or None), None) and (k0[k] is None or k1n[k] == k0[k]) for k in k0) or all(k1n[k] == k0[k] or (k0[k] is None and k1n[k] in (None, '{}', '[]')) for k in k0), (k0, k1))
        check('T1 撤销后提示条已收起、或换成“撤销了”那一条（仍只有 1 条）', pg.locator('.toast').count() <= 1)
        c.close()

    with guard('T3'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        row = pg.locator('#d2 .tl > .r.see').nth(1)
        row.locator('.adj').click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(300)
        check('T3 去掉后有提示条', pg.locator('.toast').count() == 1)
        pg.tap('.hero h1') if False else pg.mouse.click(200, 60); pg.wait_for_timeout(150)
        check('T3 点别处，提示条立刻收起', pg.locator('.toast').count() == 0, pg.locator('.toast').count())
        # 连做两件事：多待 30 → 少待 30，只有一条
        pg.locator('#d1 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-d="30"]'); pg.wait_for_timeout(200)
        n1 = pg.locator('.toast').count()
        pg.locator('#d1 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-d="-30"]'); pg.wait_for_timeout(200)
        n2 = pg.locator('.toast').count()
        check('T3 连着两次操作，提示条同一时刻只有 1 条（%d、%d）' % (n1, n2), n1 == 1 and n2 == 1, (n1, n2))
        # 打开弹层时提示条消失，不叠在弹层上
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]'); pg.wait_for_timeout(100)
        check('T3 打开日期弹层时提示条已收起（不叠在弹层上）', pg.locator('.toast').count() == 0, pg.locator('.toast').count())
        pg.click('.pk-x'); pg.wait_for_timeout(150)
        c.close()

    with guard('T5'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        n0 = pg.evaluate("document.querySelectorAll('.day').length")
        pg.locator('#d2 .rmorig').click(); pg.wait_for_selector('.pk .rmgo')
        check('T7 去掉一天要先过确认弹层', pg.locator('.pk .rmgo').count() == 1)
        shot(pg, 'T5_confirm.png')
        pg.click('.pk .rmgo'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
        check('T5 去掉后少一天', pg.evaluate("document.querySelectorAll('.day').length") == n0 - 1)
        act = pg.locator('.toast .toast-act')
        check('T5 去掉一天后马上有带“撤销”的提示条', act.count() == 1 and act.inner_text().strip() == '撤销', act.count())
        if act.count():
            bb = act.bounding_box(); check('T5 “撤销”高 ≥44', bb['height'] >= 44, bb)
            act.click(); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(800)
            check('T5 点“撤销”后天数回来', pg.evaluate("document.querySelectorAll('.day').length") == n0)
        c.close()

    # ———— 第 4 组 ————
    with guard('T6'):
        c = new_ctx(br, p, user_agent=IPHONE); pg = new_page(env, c)      # 手机 UA：高德/点评/小红书图标才会显示
        goto(env, pg, '/trip/xa3/')
        # 先做一处改动，让“恢复”出现
        pg.locator('#d2 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-d="30"]'); pg.wait_for_timeout(2200)
        targets = [('调整', '#d1 .adj'), ('页头日期“改”', '.glance .dt'), ('出发时间“改”', '#d1 .fx .st'), ('恢复', '#d2 .latewarn .reset'), ('去掉这一天', '#d1 .rmorig'),
                   ('这天后面加一天', '#d1 .addafter'), ('收进行程', '.dock .fav'), ('按天看', '.dock .tvbtn'), ('返回', '.hero .back'), ('首页', '.hero .home'), ('分享', '.hero .share'),
                   ('天数条', '.daynav a'), ('每人（人数）', '.glance .pp'), ('出发前要办的事', '.todoall'), ('地图图标', '.r .ic.map'), ('预约入口', '.r a.bkl'), ('住宿“再看两家”', '.stays .tog')]
        bad = []
        for nm, sel in targets:
            el = pg.locator(sel).first
            if el.count() == 0: bad.append('%s：页面上没有 %s' % (nm, sel)); continue
            h = pg.evaluate(HIT, el.element_handle())
            if not h or h['w'] < 44 or h['h'] < 44: bad.append('%s %s' % (nm, h))
        check('T6 行程页可点元素实际点击区都 ≥44×44', not bad, bad)
        # 弹层的“关上”
        def dialog_close(nm, opener, expect_sel='.pk'):
            opener()
            pg.wait_for_selector(expect_sel); pg.wait_for_timeout(250)
            hx = pg.evaluate(HIT, pg.locator('.pk .pk-x').first.element_handle())
            hb = pg.evaluate(HIT, pg.locator('.pk .pk-xb').first.element_handle()) if pg.locator('.pk .pk-xb').count() else None
            w = pg.evaluate("document.querySelector('.pk').getBoundingClientRect().width")
            check('T6 弹层“%s”右上“关上”点击区 ≥44×44' % nm, hx and hx['w'] >= 44 and hx['h'] >= 44, hx)
            check('T6 弹层“%s”底部“关上”≥44 高、几乎整行宽（单手好点）' % nm, hb and hb['h'] >= 44 and hb['bw'] >= w * 0.8 - 40, (hb, w))
            if nm == '调整': shot(pg, 'T6_dialog_adjust.png')
            return hb
        def close_by_bottom():
            pg.locator('.pk .pk-xb').first.click(); pg.wait_for_timeout(300)
            check('T9 点底部“关上”后弹层真的关了、页面能滚动', pg.locator('.pk').count() == 0 and not pg.evaluate("document.body.classList.contains('pk-open')"))
        dialog_close('调整', lambda: pg.locator('#d1 .adj').first.click()); close_by_bottom()
        dialog_close('日期', lambda: pg.click('.glance .dt'))
        # 日历格和翻月键
        cells = pg.evaluate("[...document.querySelectorAll('.pk-g button:not([disabled])')].slice(0,3).map(b=>Math.round(b.getBoundingClientRect().height))")
        nav = pg.evaluate("[...document.querySelectorAll('.pk-m button')].map(b=>[Math.round(b.getBoundingClientRect().width),Math.round(b.getBoundingClientRect().height)])")
        check('T6 日历日期格高 ≥44', all(x >= 44 for x in cells), cells)
        check('T6 翻月键 ≥44×44', all(w >= 44 and h >= 44 for w, h in nav), nav)
        close_by_bottom()
        dialog_close('分享', lambda: pg.click('.hero .share')); close_by_bottom()
        dialog_close('去掉这一天', lambda: pg.locator('#d1 .rmorig').click()); close_by_bottom()
        dialog_close('加一天', lambda: pg.locator('#d1 .addafter').click(), '.pk [data-free]'); close_by_bottom()
        dialog_close('出发时间', lambda: pg.locator('#d1 .fx .st').click(), '.pk .stg'); close_by_bottom()
        # T8 弹层按钮文字上下居中：在“调整”弹层里量
        pg.locator('#d1 .adj').first.click(); pg.wait_for_selector('.pk')
        off = pg.evaluate("""[...document.querySelectorAll('.pk .xd button')].map(b=>{const r=b.getBoundingClientRect();const rg=document.createRange();rg.selectNodeContents(b);const q=rg.getBoundingClientRect();return {t:b.innerText.replace(/\\n/g,'|').slice(0,14),d:Math.abs((q.top+q.bottom)/2-(r.top+r.bottom)/2)}})""")
        check('T8 “调整”弹层里每个按钮文字上下居中（差 ≤3px）', all(o['d'] <= 3 for o in off), off)
        shot(pg, 'T8_adjust_sheet.png')
        close_by_bottom()
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]')
        off2 = pg.evaluate("""[...document.querySelectorAll('.pk .pk-q button')].map(b=>{const r=b.getBoundingClientRect();const rg=document.createRange();rg.selectNodeContents(b);const q=rg.getBoundingClientRect();return {t:b.innerText.replace(/\\n/g,'|'),d:Math.abs((q.top+q.bottom)/2-(r.top+r.bottom)/2)}})""")
        check('T8 日历里“这周六 / 下周六 …”按钮文字居中', all(o['d'] <= 3 for o in off2), off2)
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
        check('T9 ESC 照旧能关弹层', pg.locator('.pk').count() == 0, pg.locator('.pk').count())
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]'); pg.mouse.click(195, 60); pg.wait_for_timeout(300)
        check('T9 点遮罩照旧能关弹层', pg.locator('.pk').count() == 0, pg.locator('.pk').count())
        c.close()

    with guard('T7'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xa3/')
        g = pg.evaluate("""(()=>{const d=document.querySelector('#d1 .dayact'),a=d.querySelector('.rmorig').getBoundingClientRect(),b=d.querySelector('.addafter').getBoundingClientRect();return {rm:[a.left,a.right,a.height],add:[b.left,b.right,b.height],gap:Math.max(a.left-b.right,b.left-a.right)}})()""")
        check('T7 “去掉这一天”和“这天后面加一天”间距 ≥16px', g['gap'] >= 16, g)
        check('T7 两个按钮高都 ≥44', g['rm'][2] >= 44 and g['add'][2] >= 44, g)
        check('T7 破坏性的“去掉这一天”在右边（不在最顺手的左边）', g['rm'][0] > g['add'][0], g)
        shot(pg, 'T7_dayact.png')
        c.close()

    # ———— 首页触控 ————
    with guard('T6h'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/')
        bad = []
        for nm, sel in [('日期条', '.hdt'), ('我的行程', '.minebtn'), ('再看', '.moreb'), ('替我挑', '.pkh'), ('天数 chip', '.dchips button'), ('搜', '.hsearch button'), ('频道', '.chan2 a'), ('翻开', '.cv .go')]:
            el = pg.locator(sel).first
            h = pg.evaluate(HIT, el.element_handle()) if el.count() else None
            if not h or h['w'] < 44 or h['h'] < 44: bad.append('%s %s' % (nm, h))
        check('T6 首页可点元素实际点击区都 ≥44×44', not bad, bad)
        # 点日期条上“改”那个字也能打开日历
        i_box = pg.locator('.hdt i').bounding_box()
        pg.mouse.click(i_box['x'] + i_box['width'] / 2, i_box['y'] + i_box['height'] / 2); pg.wait_for_timeout(300)
        check('T6 点日期条上的“改”字能打开日历', pg.locator('.pk[role=dialog]').count() == 1)
        pg.locator('.pk .pk-xb').first.click()
        c.close()
    br.close()
env.finish('撤销提示条 / 触控目标')
