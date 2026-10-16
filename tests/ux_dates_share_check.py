#!/usr/bin/env python3
"""出发日期一致 + 修改后全页一致 + 分享链接（2026-10-17，任务单第 1、2 组）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site 建好站）：
    python3 tests/ux_dates_share_check.py build/site [--shots DIR]
    python3 tests/ux_dates_share_check.py build/site --inject date_home|copy_hidden|title_days|link_nolz|backrow    # 反向自检：故意改坏 site.js，对应判据必须变红

第 1 组 日期
  D1 没选过日期：线路页写“建议 M/D 出发（按最佳季节）”，不写“明年”，跨年写“2027 年 M/D”；首页写“今天 M/D 周X 出发”
  D2 在首页改日期 → 进任何线路页（4 条不同的线）日期都是它；说明行和首页日期条是同一个写法（“M/D 周X 出发”）
  D3 在线路页改日期 → 别的线路页和首页也跟着；谁改得晚听谁的
  D4 旧数据兼容：只有 zouni_start_<id>（无时间戳）和 zouni_home_date（无时间戳）→ 和以前一样“这条线自己存的优先”，不坏
  D5 日历默认打开在“当前选中日期所在的月”；选中日期在很远的月份时有“回到今天所在的月”，点了回到本月、‹ 置灰
  D6 页头月份跟着日期：往年气温写的月份、每天的日期、总览里的日期、底栏
第 2 组 修改后全页一致
  S1 复制整条行程 = 当前页面：去掉的站不在、顺路加的站在、加的天在（并且那天晚上有住处）、每天有住处、预约入口、闭馆提醒；第二行是带全部修改的分享链接
  S2 去掉一天 / 加一天：<title>、页头小标、大标题、“我的行程”名字和副标题、最近看过、分享图标题（canvas 里真画出来的字）一起变天数
  S3 去掉最后一天：新的最后一天有“出发 → 回程”、没有“住”和住宿卡，总览写“回家”；恢复后回到原样
  S4 分享链接：给出新旧编码的长度数字；新编码比旧的短；旧链接（#mine=）仍能打开、还原得一样；朋友（新环境）打开看到的和你一致；
     自己再打开自己的链接不丢改动；打开别的版本时有“换回我自己的”并真能换回
  S5 压缩编码往返 300 个随机串（含中文、emoji）逐字相等
"""
import json, os, random, re, sys, datetime
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'date_home': ('assets/site.js', "if(ef_){isSugg=false;srcTxt=ef_[1];if(ef_[0]!==dk.value)dk.value=ef_[0];applyStart(ef_[0])}", "if(false){}"),            # 线路页不认首页的日期
    'copy_hidden': ("assets/site.js", "var rows=[].slice.call(d.querySelectorAll('.tl .r')).filter(function(r){return!r.hidden&&!r.closest('[hidden]')});", "var rows=[].slice.call(d.querySelectorAll('.tl .r'));"),   # 复制时把去掉的站也写进去
    'title_days': ("assets/site.js", "if(dn===n0)document.title=T0;else document.title=", "if(true)document.title=T0;else document.title="),                            # <title> 的天数不跟着改
    'link_nolz': ("assets/site.js", "return(z&&z.length+2<a.length+5)?'#m='+z:'#mine='+a}", "return'#mine='+a}"),                                                       # 分享链接不压缩
    'backrow': ("assets/site.js", "if(backRow&&left.length&&", "if(false&&backRow&&left.length&&"),                                                                   # 去掉最后一天后不补“回程”
}
env = Env(INJ)
check, guard = env.check, env.guard
WD = '日一二三四五六'


def md(iso):
    d = datetime.date.fromisoformat(iso); return '%d/%d' % (d.month, d.day), '周' + WD[(d.weekday() + 1) % 7]


def add_days(iso, n): return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=n)).isoformat()


def goto_month(pg, iso):
    """日历翻到 iso 所在的月（最多翻 14 次）"""
    ty, tm = int(iso[:4]), int(iso[5:7])
    for _ in range(14):
        m = re.match(r'(\d+) 年 (\d+) 月', pg.inner_text('.pk-m b').strip()); cy, cm = int(m.group(1)), int(m.group(2))
        if (cy, cm) == (ty, tm): return
        pg.click('.pk-n' if (cy, cm) < (ty, tm) else '.pk-p'); pg.wait_for_timeout(60)

with sync_playwright() as p:
    br = p.chromium.launch()
    TRIPS = ['xa3', 'gqhx10', 'tk4', 'par5']

    # ———— D1 没选过日期 ————
    with guard('D1'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/')
        mn = pg.evaluate("document.querySelector('.hdpk').dataset.min")
        today_txt = pg.inner_text('.hdt b').strip()
        a, w = md(mn)
        check('D1 首页没选过日期：日期条写“今天 M/D 周X 出发”', today_txt == '今天 %s %s 出发' % (a, w), today_txt)
        for t in TRIPS:
            goto(env, pg, '/trip/%s/' % t)
            dock = pg.inner_text('.dock b').strip(); note = pg.inner_text('.dnote').strip(); dt = pg.inner_text('.glance .dt').strip()
            val = pg.evaluate("document.querySelector('.dpk').value")
            check('D1 %s 底栏写“建议 M/D 出发”' % t, dock.startswith('建议 ') and '明年' not in dock, dock)
            check('D1 %s 说明行写“建议 … 出发（按最佳季节）”，不写“明年”' % t, note.startswith('建议 ') and '按最佳季节' in note and '明年' not in note, note)
            check('D1 %s 页头日期格是 M/D 起头、没有“明年”' % t, re.match(r'^\d+/\d+', dt) and '明年' not in dt, dt)
            y = int(val[:4]); mn_y = int(mn[:4])
            if y > mn_y: check('D1 %s 跨年写完整“%d 年”' % (t, y), ('%d 年' % y) in note, note)
            m1, w1 = md(val)
            check('D1 %s 说明行里的日期和星期就是 .dpk 里的 %s %s' % (t, m1, w1), (m1 + ' ' + w1) in note, note)
        c.close()

    # ———— D2 首页改日期 → 所有线路 ————
    with guard('D2'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/')
        mn = pg.evaluate("document.querySelector('.hdpk').dataset.min")
        pg.click('.hdt'); pg.wait_for_selector('.pk[role=dialog]')
        head = pg.inner_text('.pk-m b').strip()
        check('D5 首页日历默认打开在今天所在的月（不是别的月）', head == '%d 年 %d 月' % (int(mn[:4]), int(mn[5:7])), head)
        want = add_days(mn, 25)
        goto_month(pg, want)
        pg.click('.pk-g button[data-v="%s"]' % want); pg.wait_for_timeout(500)
        a, w = md(want)
        hb = pg.inner_text('.hdt b').strip()
        check('D2 首页改完日期条写“M/D 周X 出发”（不带“今天”）', hb == '%s %s 出发' % (a, w), hb)
        for t in TRIPS:
            goto(env, pg, '/trip/%s/' % t)
            v = pg.evaluate("document.querySelector('.dpk').value"); dock = pg.inner_text('.dock b'); note = pg.inner_text('.dnote'); h1 = pg.inner_text('.day header small')
            check('D2 %s 日期 = 首页选的 %s' % (t, want), v == want, v)
            check('D2 %s 底栏写 %s 出发（不写“建议”）' % (t, a), dock.startswith(a + ' 出发') and '建议' not in dock, dock)
            check('D2 %s 说明行和首页日期条是同一个写法“%s %s 出发”' % (t, a, w), ('%s %s 出发' % (a, w)) in note and '建议' not in note, note)
            check('D2 %s 第一天标题日期 = %s %s' % (t, a, w), (a + ' ' + w) in h1, h1)
        # 回首页：日期条还是它
        goto(env, pg, '/')
        check('D2 回到首页日期条还是 %s' % a, ('%s %s 出发' % (a, w)) in pg.inner_text('.hdt b'), pg.inner_text('.hdt b'))
        c.close()

    # ———— D3 线路页改日期 → 别的线路页和首页 ————
    with guard('D3'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        mn = pg.evaluate("document.querySelector('.dpk').dataset.min")
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]')
        head = pg.inner_text('.pk-m b').strip(); val0 = pg.evaluate("document.querySelector('.dpk').value")
        check('D5 线路页日历默认打开在“当前选中日期”所在的月', head == '%d 年 %d 月' % (int(val0[:4]), int(val0[5:7])), '%s vs %s' % (head, val0))
        jump = pg.locator('.pk-j')
        if (int(val0[:4]), int(val0[5:7])) != (int(mn[:4]), int(mn[5:7])):
            check('D5 选中日期不在今天所在的月时，有“回到今天所在的月”', jump.count() == 1, '没有')
            jump.click(); pg.wait_for_timeout(200)
            h2 = pg.inner_text('.pk-m b').strip()
            check('D5 点“回到今天所在的月”后日历在 %s' % mn[:7], h2 == '%d 年 %d 月' % (int(mn[:4]), int(mn[5:7])), h2)
            check('D5 回到本月后“‹”置灰（过去的月份点不了）', pg.evaluate("document.querySelector('.pk-p').disabled"))
        want = add_days(mn, 40)
        goto_month(pg, want)
        pg.click('.pk-g button[data-v="%s"]' % want); pg.wait_for_timeout(600)
        a, w = md(want)
        check('D3 线路页自己改完：底栏 %s 出发、说明行“按你选的”' % a, pg.inner_text('.dock b').startswith(a + ' 出发') and '按你选的' in pg.inner_text('.dnote'), pg.inner_text('.dnote'))
        goto(env, pg, '/trip/gqhx10/')
        check('D3 别的线路页（gqhx10）也是 %s' % want, pg.evaluate("document.querySelector('.dpk').value") == want, pg.evaluate("document.querySelector('.dpk').value"))
        goto(env, pg, '/')
        check('D3 首页日期条也跟着改成 %s %s 出发' % (a, w), ('%s %s 出发' % (a, w)) in pg.inner_text('.hdt b'), pg.inner_text('.hdt b'))
        # 谁晚听谁的：再到首页改一次，线路页跟首页
        pg.click('.hdt'); pg.wait_for_selector('.pk[role=dialog]')
        want2 = add_days(mn, 12)
        goto_month(pg, want2)
        pg.click('.pk-g button[data-v="%s"]' % want2); pg.wait_for_timeout(500)
        goto(env, pg, '/trip/xa3/')
        check('D3 首页后改的日期盖过线路页先改的（xa3 = %s）' % want2, pg.evaluate("document.querySelector('.dpk').value") == want2, pg.evaluate("document.querySelector('.dpk').value"))
        c.close()

    # ———— D4 旧数据兼容 ————
    with guard('D4'):
        probe = br.new_context(viewport={'width': 390, 'height': 844}); pp = probe.new_page(); pp.goto(env.B + '/', wait_until='networkidle')
        mn = pp.evaluate("document.querySelector('.hdpk').dataset.min"); probe.close()
        r_old, h_old = add_days(mn, 50), add_days(mn, 20)
        c = new_ctx(br, p, storage={'zouni_start_xa3': r_old, 'zouni_home_date': h_old}); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        check('D4 旧数据：这条线自己存的日期优先（和以前一样）', pg.evaluate("document.querySelector('.dpk').value") == r_old, pg.evaluate("document.querySelector('.dpk').value"))
        goto(env, pg, '/trip/gqhx10/')
        check('D4 旧数据：这条线没存过，用首页那个', pg.evaluate("document.querySelector('.dpk').value") == h_old, pg.evaluate("document.querySelector('.dpk').value"))
        goto(env, pg, '/')
        check('D4 旧数据：首页读到旧的 zouni_home_date', md(h_old)[0] in pg.inner_text('.hdt b'), pg.inner_text('.hdt b'))
        # 过期的旧数据不起作用
        c.close()
        c = new_ctx(br, p, storage={'zouni_start_xa3': add_days(mn, -5), 'zouni_home_date': add_days(mn, -3)}); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        check('D4 已经过去的旧日期不生效，回到建议日期', pg.inner_text('.dock b').startswith('建议 '), pg.inner_text('.dock b'))
        c.close()

    # ———— D5 远处的建议日期：日历里有回到本月 ————（xa3 默认在明年，已在 D3 覆盖；这里单独看跨年文字）
    with guard('D5'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        val = pg.evaluate("document.querySelector('.dpk').value"); mn = pg.evaluate("document.querySelector('.dpk').dataset.min")
        if val[:4] != mn[:4]:
            check('D5 跨年的建议日期：说明行写“%s 年 M/D”' % val[:4], ('%s 年' % val[:4]) in pg.inner_text('.dnote'), pg.inner_text('.dnote'))
            check('D5 跨年时底栏不出现“明年”', '明年' not in pg.inner_text('.dock b'))
        else:
            env.note('xa3 的建议日期没有跨年（%s），跨年文字这次没验到' % val)
        c.close()

    # ———— D6 页头月份跟着日期 ————
    with guard('D6'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        mn = pg.evaluate("document.querySelector('.dpk').dataset.min")
        dec = '%d-12-05' % (int(mn[:4]) + (0 if int(mn[5:7]) < 12 else 1))
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]')
        goto_month(pg, dec)
        pg.click('.pk-g button[data-v="%s"]' % dec); pg.wait_for_timeout(600)
        cl = pg.inner_text('#d1 .cl'); a, w = md(dec)
        check('D6 改到 12 月：往年气温写的是 12 月（页头自动生成的月份跟着变）', '12 月' in cl, cl)
        check('D6 第一天日期 12/5', ('12/5 ' + w) in pg.inner_text('#d1 header small'), pg.inner_text('#d1 header small'))
        check('D6 总览里第一天日期 12/5', pg.inner_text('.overview li i').strip() == '12/5', pg.inner_text('.overview li i'))
        check('D6 页头日期格 12/5 起头', pg.inner_text('.glance .dt').strip().startswith('12/5'), pg.inner_text('.glance .dt'))
        c.close()

    # ———— S1 复制整条行程 = 当前页面；S2 天数 ————
    with guard('S1'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        pg.evaluate("window.__ft=[];var P=CanvasRenderingContext2D.prototype,f=P.fillText;P.fillText=function(t){window.__ft.push(String(t));return f.apply(this,arguments)};0")
        # 去掉第 2 天第一个景点（兵马俑）
        pg.locator('#d2 .adj').first.click(); pg.wait_for_selector('.pk')
        dropped = pg.evaluate("document.querySelector('.pk-h b').innerText.trim()")
        pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(300)
        # 第 3 天陕西历史博物馆之后加一个顺路的（这个站后面排得开）
        pg.locator('#d3 .adj').first.click(); pg.wait_for_selector('.pk')
        pg.click('.pk [data-np="ins"]'); pg.wait_for_selector('.pk .npc', timeout=15000)
        added = pg.evaluate("document.querySelector('.pk .npc b').innerText.trim()")
        pg.click('.pk .npc'); pg.wait_for_timeout(500)
        # 第 1 天后面加一天（自由活动）
        pg.locator('#d1 .addafter').click(); pg.wait_for_selector('.pk [data-free="1"]')
        pg.click('.pk [data-free="1"]'); pg.wait_for_timeout(800)
        txt = pg.evaluate("window.zTripText()")
        lines = txt.split('\n')
        check('S1 复制文本第二行是带全部修改的分享链接（#m= 或 #mine=）', re.match(r'^https?://\S+#(m|mine)=\S+$', lines[1] or '') is not None, lines[1][:80])
        check('S1 去掉的站「%s」不在复制文本里' % dropped, dropped not in txt, dropped)
        check('S1 顺路加的站「%s」在复制文本里' % added, added in txt, '')
        check('S1 加的那一天（自由活动）在复制文本里', '自由活动' in txt, '')
        # 加的自由活动天：晚上有住处
        k = [i for i, l in enumerate(lines) if '自由活动' in l and l.startswith('第')]
        seg = '\n'.join(lines[k[0]:k[0] + 6]) if k else ''
        check('S1 加的自由活动天：导出里那天晚上有“住 ·”', re.search(r'晚上\s+住 · ', seg) is not None, seg)
        days = [l for l in lines if re.match(r'^第.天 · ', l)]
        stays = [l for l in lines if re.match(r'^\s+(晚上|\S+)\s+住 · ', l)]
        check('S1 每天（除最后一天）都有住处行', len(stays) >= len(days) - 1, '%d 天 %d 个住' % (len(days), len(stays)))
        check('S1 带预约入口（兵马俑/历史博物馆要预约）', '预约入口：http' in txt or '入口 http' in txt, '')
        check('S1 带闭馆提醒（周一闭馆）', '周一闭馆' in txt, '')
        check('S1 带出发前要办的事', '出发前要办的事' in txt, '')
        page_times = pg.evaluate("[...document.querySelectorAll('.day .tl .r')].filter(r=>!r.hidden).map(r=>(r.querySelector('time')||{}).textContent)")
        n_txt_rows = len([l for l in lines if re.match(r'^  \d\d:\d\d  |^  晚上  ', l)])
        check('S1 复制文本里的时间行数 = 页面上没被去掉的行数（含加的）', abs(n_txt_rows - len(page_times)) <= 1, '%d vs %d' % (n_txt_rows, len(page_times)))
        # 点分享 → 复制整条行程 = 同一份
        pg.click('.share'); pg.wait_for_selector('.pk [data-a="copy"]'); pg.click('.pk [data-a="copy"]'); pg.wait_for_timeout(300)
        clip = pg.evaluate("window.__clip")
        check('S1 分享里“复制整条行程”复制的就是 zTripText()', clip == txt, (clip or '')[:80])
        # S2 去掉一天 → 天数跟着变（页面上现在是 4 天：3 + 加的 1）
        n_now = pg.evaluate("document.querySelectorAll('.day').length")
        check('S2 加了一天后共 4 天', n_now == 4, n_now)
        h1 = pg.inner_text('.hero h1'); kick = pg.inner_text('.hero .kick'); tt = pg.title().replace('\xa0', ' ')
        check('S2 加一天后大标题写“四天”', h1.startswith('四天'), h1)
        check('S2 加一天后页头小标写“四天”', '四天' in kick, kick)
        check('S2 加一天后 <title> 写“4 天行程”', '4 天行程' in tt, tt)
        pg.click('.fav'); pg.wait_for_timeout(500)
        fav = json.loads(ls(pg, 'zouni_fav') or '[]')
        check('S2 收进行程时名字写 4 天、副标题写“四天，…”', fav and '4 天' in fav[0]['label'].replace('\xa0', ' ') and fav[0]['title'].startswith('四天'), fav)
        # 分享图（canvas 里真画出来的标题）
        pg.click('.share'); pg.wait_for_selector('.pk [data-a="shot"]'); pg.click('.pk [data-a="shot"]'); pg.wait_for_selector('.shotv', timeout=15000)
        ft = pg.evaluate("window.__ft")
        check('S2 分享图标题（canvas 里画的字）是“四天，…”', any(s.startswith('四天') for s in ft) and not any(s.startswith('三天，') for s in ft), ft[:8])
        pg.click('.shotv .hz-x')
        # 去掉第 3 天（原来的最后一天）
        pg.locator('#d4 .rmorig').click(); pg.wait_for_selector('.pk .rmgo'); pg.click('.pk .rmgo'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
        n_now = pg.evaluate("document.querySelectorAll('.day').length")
        h1 = pg.inner_text('.hero h1'); kick = pg.inner_text('.hero .kick'); tt = pg.title().replace('\xa0', ' ')
        check('S2 去掉最后一天后剩 3 天（原 3 + 加 1 - 去 1）', n_now == 3, n_now)
        check('S2 去掉一天后大标题“三天”、页头小标“三天”、<title> “3 天行程”', h1.startswith('三天') and '三天' in kick and '3 天行程' in tt, '%s | %s | %s' % (h1, kick, tt))
        fav = json.loads(ls(pg, 'zouni_fav') or '[]'); seen = json.loads(ls(pg, 'zouni_seen') or '[]')
        check('S2 收藏里的名字跟着改回 3 天', fav and '3 天' in fav[0]['label'].replace('\xa0', ' '), fav)
        check('S2 最近看过里的名字也是 3 天', seen and '3 天' in seen[0]['label'].replace('\xa0', ' '), seen)
        # 复制文本也反映
        txt2 = pg.evaluate("window.zTripText()")
        check('S2 复制文本里不再有被去掉的那天（标题天数一致）', txt2.startswith('三天，'), txt2[:20])
        c.close()

    # ———— S3 去掉最后一天：回程补到新的最后一天 ————
    with guard('S3'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        before = pg.evaluate("(()=>{const d=[...document.querySelectorAll('.day')];const l=d[d.length-1];return {n:d.length,lastRows:[...l.querySelectorAll('.tl > .r')].map(r=>r.innerText.replace(/\\s+/g,' ')),d2stay:!!d[1].querySelector('.r.stay'),ov:[...document.querySelectorAll('.overview li small')].map(s=>s.innerText)}})()")
        check('S3 原样：最后一天有“出发 → 回程”', any('回程' in r for r in before['lastRows']), before['lastRows'])
        check('S3 原样：第 2 天晚上有“住”', before['d2stay'])
        pg.locator('#d3 .rmorig').click(); pg.wait_for_selector('.pk .rmgo'); pg.click('.pk .rmgo'); pg.wait_for_load_state('networkidle'); pg.wait_for_timeout(900)
        after = pg.evaluate("(()=>{const d=[...document.querySelectorAll('.day')];const l=d[d.length-1];return {n:d.length,lastRows:[...l.querySelectorAll('.tl > .r')].map(r=>r.className+'|'+r.innerText.replace(/\\s+/g,' ')),stay:!!l.querySelector('.r.stay'),card:!!l.querySelector('.stays'),ov:[...document.querySelectorAll('.overview li small')].map(s=>s.innerText),times:[...l.querySelectorAll('.tl > .r:not([hidden]) time')].map(t=>t.innerText)}})()")
        check('S3 去掉最后一天后剩 2 天', after['n'] == 2, after['n'])
        check('S3 新的最后一天补上了“出发 → 回程”', any('回程' in r for r in after['lastRows']), after['lastRows'])
        check('S3 新的最后一天不再有“住”和住宿卡', not after['stay'] and not after['card'], after)
        check('S3 总览里新的最后一天写“回家”', after['ov'][-1] == '回家', after['ov'])
        tm = [int(t[:2]) * 60 + int(t[3:]) for t in after['times'] if re.match(r'^\d\d:\d\d$', t)]
        check('S3 新的最后一天时间单调不倒退', all(a <= b for a, b in zip(tm, tm[1:])), after['times'])
        # 恢复
        pg.evaluate("localStorage.removeItem('zouni_rmday_xa3')"); goto(env, pg, '/trip/xa3/')
        again = pg.evaluate("(()=>{const d=[...document.querySelectorAll('.day')];const l=d[d.length-1];return {n:d.length,lastRows:[...l.querySelectorAll('.tl > .r')].map(r=>r.innerText.replace(/\\s+/g,' ')),ov:[...document.querySelectorAll('.overview li small')].map(s=>s.innerText)}})()")
        check('S3 恢复后回到原样（天数、最后一天各行、总览）', again == before | {'d2stay': again.get('d2stay')} or (again['n'] == before['n'] and again['lastRows'] == before['lastRows'] and again['ov'] == before['ov']), again)
        c.close()

    # ———— S4 分享链接 ————
    with guard('S4'):
        c = new_ctx(br, p); pg = new_page(env, c)
        goto(env, pg, '/trip/xa3/')
        mn = pg.evaluate("document.querySelector('.dpk').dataset.min")
        # 造一个“改得很多”的状态：改日期、改出发时间、去掉站、顺路加站、加一天、多待、换人数、去掉第 3 天
        pg.click('.glance .dt'); pg.wait_for_selector('.pk[role=dialog]')
        want = add_days(mn, 30)
        goto_month(pg, want)
        pg.click('.pk-g button[data-v="%s"]' % want); pg.wait_for_timeout(500)
        pg.locator('#d2 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-d="30"]'); pg.wait_for_timeout(200)
        pg.locator('#d3 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-np="ins"]'); pg.wait_for_selector('.pk .npc', timeout=15000); pg.click('.pk .npc'); pg.wait_for_timeout(400)
        pg.locator('#d1 .addafter').click(); pg.wait_for_selector('.pk [data-free="1"]'); pg.click('.pk [data-free="1"]'); pg.wait_for_timeout(600)
        pg.locator('#d1 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-x="1"]'); pg.wait_for_timeout(300)
        pg.evaluate("localStorage.setItem('zouni_n_xa3','4')")
        state_keys = ['zouni_start_', 'zouni_st_', 'zouni_drop_', 'zouni_adj_', 'zouni_extra_', 'zouni_slow_', 'zouni_n_', 'zouni_rain_', 'zouni_fill_', 'zouni_rmday_', 'zouni_np_']
        pg.reload(wait_until='networkidle'); pg.wait_for_timeout(700)
        txt = pg.evaluate("window.zTripText()")
        link_new = txt.split('\n')[1]
        mine = pg.evaluate("(()=>{var o={};['zouni_start_','zouni_st_','zouni_drop_','zouni_adj_','zouni_extra_','zouni_slow_','zouni_n_','zouni_rain_','zouni_fill_','zouni_rmday_','zouni_np_'].forEach(function(k){var v=localStorage.getItem(k+'xa3');if(v!=null&&v!==''&&v!=='{}'&&v!=='[]'){try{o[k]=JSON.parse(v)}catch(e){o[k]=v}}});return o})()")
        used = [k for k in state_keys if k in mine]
        old_link = pg.evaluate("(o)=>{var a=btoa(unescape(encodeURIComponent(JSON.stringify(o)))).replace(/\\+/g,'-').replace(/\\//g,'_').replace(/=+$/,'');return location.origin+location.pathname+'#mine='+a}", mine)
        n_old = len(old_link) - len(env.B) - len('/trip/xa3/'); n_new = len(link_new) - len(env.B) - len('/trip/xa3/')
        env.note('分享链接长度（# 后面的字符数）：旧编码 %d → 新编码 %d（省 %d%%）；状态里用到 %d 个键：%s' % (n_old, n_new, round(100 - 100.0 * n_new / n_old), len(used), ' '.join(k[6:-1] for k in used)))
        check('S4 状态里每一类改动都用到了（日期、多待、顺路、加一天、去掉站、人数）', {'zouni_start_', 'zouni_adj_', 'zouni_np_', 'zouni_extra_', 'zouni_drop_', 'zouni_n_'} <= set(used), used)
        check('S4 新编码（#m=）比旧编码（#mine=）至少短 25%', '#m=' in link_new and n_new <= 0.75 * n_old, '%d vs %d' % (n_new, n_old))
        # 往返：解码 = 原状态
        rt = pg.evaluate("(o)=>{var h=window.zLink.enc(o);return JSON.stringify(window.zLink.dec(h))===JSON.stringify(o)}", mine)
        check('S4 新编码解码回来和原状态逐字相等', rt)
        # 朋友（全新环境）打开新链接 / 旧链接，看到的和你一致
        base_lines = txt.split('\n')[2:]
        for label, lk in (('新链接 #m=', link_new), ('旧链接 #mine=', old_link)):
            c2 = new_ctx(br, p); f = new_page(env, c2)
            f.goto(lk, wait_until='networkidle'); f.wait_for_timeout(1200)
            t2 = f.evaluate("window.zTripText()")
            check('S4 朋友打开%s：复制出来的行程和你的一致' % label, t2.split('\n')[2:] == base_lines, [(a, b) for a, b in zip(t2.split('\n')[2:], base_lines) if a != b][:2])
            check('S4 朋友打开%s：地址栏的 #m=/#mine= 被清掉（不会越刷越乱）' % label, '#m' not in f.url, f.url[-30:])
            c2.close()
        # 自己再打开自己的链接（新开一个标签页，才是真的重新加载）：状态不丢（完全相同时不改任何键值）
        snap = "(()=>{var o={};for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(/_xa3$/.test(k)&&k.indexOf('startt')<0)o[k]=localStorage.getItem(k)}return o})()"
        before = pg.evaluate(snap)
        pg2 = new_page(env, c); pg2.goto(link_new, wait_until='networkidle'); pg2.wait_for_timeout(1000)
        after = pg2.evaluate(snap)
        check('S4 自己打开自己的链接：所有修改原样还在', before == after, [k for k in set(before) | set(after) if before.get(k) != after.get(k)])
        check('S4 自己打开自己的链接后地址栏的 #m= 清掉了', '#m' not in pg2.url, pg2.url[-30:])
        pg2.close()
        # 先再改一处，再打开旧链接（别的版本）：有“换回我自己的”，点了真换回
        pg.locator('#d3 .adj').first.click(); pg.wait_for_selector('.pk'); pg.click('.pk [data-d="-30"]'); pg.wait_for_timeout(300)
        full = "(()=>{var o={};for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(/_xa3$/.test(k)&&k.indexOf('lastday')<0)o[k]=localStorage.getItem(k)}return o})()"
        mine_before = pg.evaluate(full)
        pg3 = new_page(env, c); pg3.goto(link_new, wait_until='networkidle'); pg3.wait_for_timeout(1500)
        act = pg3.locator('.toast .toast-act')
        check('S4 打开另一个版本时有“换回我自己的”（自己的最新改动被盖掉前给了退路）', act.count() == 1 and '换回我自己的' in act.inner_text(), act.count())
        changed = pg3.evaluate(full) != mine_before
        check('S4 另一个版本确实载入了（状态和我的最新状态不同）', changed)
        if act.count():
            act.click(); pg3.wait_for_load_state('networkidle'); pg3.wait_for_timeout(800)
            mine_after = pg3.evaluate(full)
            check('S4 点“换回我自己的”后所有改动回来（含日期和时间戳）', mine_before == mine_after, [(k, mine_before.get(k), mine_after.get(k)) for k in set(mine_before) | set(mine_after) if mine_before.get(k) != mine_after.get(k)])
        pg3.close()
        c.close()

    # ———— S5 压缩往返 ————
    with guard('S5'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xa3/')
        random.seed(7)
        pool = list('abcdefghijklmnopqrstuvwxyz0123456789{}[]":,') + list('西安城墙钟鼓楼回民街兵马俑华清宫大雁塔顺路加站自由活动') + ['😀', '𠮷', '—', '·', ' ']
        samples = [''.join(random.choice(pool) for _ in range(random.randint(1, 400))) for _ in range(300)] + ['a', 'aa', 'aaa' * 200, '西' * 500, json.dumps({'a': [1, 2, {'x': '西安'}] * 50}, ensure_ascii=False)]
        bad = pg.evaluate("(xs)=>xs.filter(function(s){try{return window.zLink.lzD(window.zLink.lzC(s))!==s}catch(e){return true}}).length", samples)
        check('S5 压缩编码往返 %d 个随机串（含中文、emoji）逐字相等' % len(samples), bad == 0, '%d 个不一致' % bad)
        c.close()
    br.close()
env.finish('出发日期 / 全页一致 / 分享链接')
