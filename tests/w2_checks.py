#!/usr/bin/env python3
"""第 2 波（2026-10-29）体验与逻辑：分享链接 / 去掉一站重排 / 推荐与线路一致 / 对比页 / 首页选择。会红。

用法（项目根目录；先建好站）：
    python3 tests/w2_checks.py build/site_w2
    python3 tests/w2_checks.py build/site_w2 --inject friend_write|qr_base|drop_old|rep_nocheck|cover_nofilter|num02|no_scroll|warn_walkonly|go_old   # 反向自检，每个必须变红

  F1  朋友打开带 #m= 的链接：页头下有“朋友发来的版本”一行，显示链接里的日期 / 人数，本机 localStorage 一个键都不变；刷新仍是朋友的版本；“用我的”回到本机版本
  F2  “收进行程”：才写进本机（日期、人数落盘）并收进行程
  F3  分享图二维码（cv2 解码）= 分享链接；用解码出的链接开新环境，天数 / 日期 / 人数 / 价格和原页面一致
  D1  去掉一站：没有可见的“出发 → X”指向已被去掉的站；被并掉的那一段车程换成模型重算（data-np-s0 在）；每一行时间不晚于去掉前
  D2  “换成…”：没有候选的站（xw45a）置灰且写原因；有候选的（xa3）可点
  R1  “带老人孩子”各出发地的前三条：线路页里没有“对老人孩子偏累”的天；理由里不再写“没有长爬坡和台阶”
  R2  结果卡写的去程时间和线路页“怎么去”是同一句（zGoWay）
  R3  对比页有“去程”“降雨”两行
  H1  “现在去正好”编号从 01 开始
  H2  选了周末 2–3 天，封面是 ≤3 天的线；取消后封面回到建站时的那一条
  H3  三项选满后结果列表滚进视野
"""
import json, os, re, sys, base64
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'friend_write': ('assets/site.js', "if(diff_){fOn(ov_);fSave()}", "if(diff_){fOn(ov_);fSave();Object.keys(ov_).forEach(function(k){if(ov_[k]!=null)_si2.call(localStorage,k,ov_[k])})}"),
    'qr_base': ('assets/site.js', "q.addData(qu);", "q.addData(location.origin+location.pathname);"),
    'drop_old': ('assets/site.js', "if(!isDrop(S)||!S.dataset.ll||S.dataset.np==='v')return;var sc=npScan", "return;var sc=npScan"),
    'rep_nocheck': ('assets/site.js', "['ins','rep'].forEach(function(kd){", "['ins'].forEach(function(kd){"),
    'cover_nofilter': ('assets/site.js', "inB=function(li){return!band||li.dataset.band===band}", "inB=function(li){return true}"),
    'num02': ('assets/site.js', "('0'+k).slice(-2);", "('0'+(k+1)).slice(-2);"),
    'no_scroll': ('assets/site.js', "function showRes(){if(!(st.o&&st.d&&st.w))return;", "function showRes(){return;"),
    'warn_walkonly': ('assets/site.js', "if(phys.length||hasT('偏累'))return;", "if(phys.length)return;"),
    'go_old': ('assets/site.js', "if(gg_){gd_=km(", "if(false){gd_=km("),
}
env = Env(INJ)
check, guard = env.check, env.guard
B = env.B


def newctx(br, W=390, H=844):
    ctx = br.new_context(viewport={'width': W, 'height': H}, locale='zh-CN', timezone_id='Asia/Shanghai')
    pg = ctx.new_page(); pg.on('pageerror', lambda e: env.errs.append(str(e)))
    return ctx, pg


FACTS = "({date:(document.querySelector('.glance .dt')||{}).innerText||'',pp:(document.querySelector('.glance .pp')||{}).innerText||'',price:(document.querySelector('.price')||{}).innerText||'',days:document.querySelectorAll('.day').length,big:(document.querySelector('.big')||{}).innerText||''})"
LS = "(function(){var o={};for(var i=0;i<localStorage.length;i++){var k=localStorage.key(i);if(!/^zouni_(seen|map_t|v)/.test(k))o[k]=localStorage.getItem(k)}return JSON.stringify(o)})()"

with sync_playwright() as p:
    br = p.chromium.launch()

    # ———— F1 / F2 ————
    with guard('F1'):
        ctx, pg = newctx(br)
        pg.goto(B + '/trip/xa3/'); pg.wait_for_timeout(900)
        pg.evaluate("localStorage.setItem('zouni_n','4');localStorage.setItem('zouni_date','2027-03-10')")
        pg.reload(); pg.wait_for_timeout(900)
        mine = pg.evaluate(FACTS)
        link = pg.evaluate("zLink.enc({zouni_start_:'2027-04-21',zouni_n_:'3',zouni_rmday_:[1]})")
        before = pg.evaluate(LS)
        pf = ctx.new_page(); pf.goto(B + '/trip/xa3/' + link); pf.wait_for_timeout(1400)
        fr = pf.evaluate(FACTS); bar = pf.evaluate("(document.querySelector('.fbar')||{}).innerText||''")
        check('F1a 朋友的链接：页头下有“朋友发来的版本 / 用我的 / 收进行程”', all(x in bar for x in ('朋友发来的版本', '用我的', '收进行程')), bar)
        check('F1b 显示的是链接里的版本（日期 4/21、3 人、去掉一天 → 2 天），不是本机的', '4/21' in fr['date'] and fr['pp'].startswith('3 人') and fr['days'] == 2 and fr != mine, (fr, mine))
        check('F1c 本机 localStorage 一个键都没变（从没打开朋友页的那一页读，朋友页里读到的是覆盖层）', pg.evaluate(LS) == before, (before, pg.evaluate(LS)))
        pf.reload(); pf.wait_for_timeout(900)
        check('F1d 刷新后仍是朋友的版本、本机仍没变', pf.evaluate(FACTS) == fr and pg.evaluate(LS) == before and pf.evaluate("!!document.querySelector('.fbar')"))
        pf.click('.fb-me'); pf.wait_for_timeout(1200)
        check('F1e “用我的”：回到本机版本、横条消失', pf.evaluate(FACTS) == mine and not pf.evaluate("!!document.querySelector('.fbar')"), pf.evaluate(FACTS))
        pf.goto(B + '/trip/xa3/' + link); pf.wait_for_timeout(1400)
        pf.click('.fb-keep'); pf.wait_for_timeout(1200)
        ls = json.loads(pg.evaluate(LS))
        check('F2 “收进行程”：日期 / 人数写进本机，并收进行程', ls.get('zouni_date') == '2027-04-21' and ls.get('zouni_n') == '3' and any(x.get('id') == 'xa3' for x in json.loads(ls.get('zouni_fav', '[]'))), ls)
        ctx.close()

    # ———— F3 ————
    with guard('F3'):
        import cv2, numpy as np
        ctx, pg = newctx(br)
        pg.goto(B + '/trip/xa3/'); pg.evaluate("localStorage.setItem('zouni_n','4');localStorage.setItem('zouni_date','2027-03-10');localStorage.setItem('zouni_rmday_xa3','[1]')")
        pg.reload(); pg.wait_for_timeout(1000); a = pg.evaluate(FACTS)
        pg.click('.share'); pg.wait_for_timeout(300); pg.click('button[data-a=shot]'); pg.wait_for_timeout(1800)
        src = pg.evaluate("document.querySelector('.shotv img').src"); im = cv2.imdecode(np.frombuffer(base64.b64decode(src.split(',')[1]), np.uint8), 1)
        txt = cv2.QRCodeDetector().detectAndDecode(im)[0]
        want = pg.evaluate("zLink.enc({zouni_start_:localStorage.zouni_date,zouni_n_:localStorage.zouni_n,zouni_rmday_:JSON.parse(localStorage.zouni_rmday_xa3)})")
        check('F3a 分享图二维码里是带改动的链接（解出 %s）' % txt[-30:], '#m=' in txt and '/trip/xa3/' in txt, txt)
        c2, p2 = newctx(br); p2.goto(txt.replace('http://localhost:8800', B) if 'localhost:8800' in txt else txt); p2.wait_for_timeout(1400)
        check('F3b 扫出来的页面和图上一致（天数 / 日期 / 人数 / 价格）', p2.evaluate(FACTS) == a, (p2.evaluate(FACTS), a))
        ctx.close(); c2.close()

    # ———— D1 / D2 ————
    DUMP = """(function(di){var s=document.querySelectorAll('.day')[di],rows=[].slice.call(s.querySelectorAll('.tl > .r'));return rows.map(function(r){return{k:r.dataset.k,h:r.hidden,cl:r.className,t:(r.querySelector('time')||{}).textContent,m:((r.querySelector('.m')||{}).textContent||'').replace(/\\s+/g,' ').trim(),s0:r.getAttribute('data-np-s0')}})})"""

    def hm(t):
        m = re.match(r'^(\d+):(\d\d)$', t or ''); return int(m[1]) * 60 + int(m[2]) if m else None
    with guard('D1'):
        ctx, pg = newctx(br)
        for rid, di, ix in (('xa3', 0, 1), ('xa3', 0, 0), ('hjmls1', 1, 0)):
            pg.goto(B + '/trip/%s/' % rid); pg.wait_for_timeout(700)
            base = pg.evaluate(DUMP + '(%d)' % di)
            k = int(pg.evaluate("[].slice.call(document.querySelectorAll('.day')[%d].querySelectorAll('.tl > .r.see, .tl > .r.fun')).filter(function(r){return r.querySelector('.adj')})[%d].dataset.k" % (di, ix)))
            row = [r for r in base if r['k'] == str(k)][0]
            pg.evaluate("document.querySelectorAll('.day')[%d].querySelector('.tl > .r[data-k=\"%d\"] .adj').click()" % (di, k)); pg.wait_for_timeout(500)
            pg.click('.pk button:has-text("去掉这一站")'); pg.wait_for_timeout(1800)
            aft = pg.evaluate(DUMP + '(%d)' % di)
            gone = [r for r in aft if r['h'] and re.search(r'\b(see|fun)\b', r['cl'])]
            nm = re.split(r'\s+', row['m'])[0].split('·')[0].strip()
            dang = [r['m'] for r in aft if not r['h'] and 'dep' in r['cl'] and re.match(r'^出发 → ' + re.escape(nm), r['m'])]
            check('D1a %s 第%d天去掉「%s」：没有“出发 → 它”留着（%s）' % (rid, di + 1, nm[:8], dang), not dang, dang)
            bt = {r['k']: hm(r['t']) for r in base if not r['h']}
            later = [(r['k'], bt[r['k']], hm(r['t'])) for r in aft if not r['h'] and r['k'] in bt and bt[r['k']] is not None and hm(r['t']) is not None and hm(r['t']) > bt[r['k']]]
            check('D1b %s 第%d天去掉一站后没有任何一行时间变晚（%s）' % (rid, di + 1, later), not later, later)
            check('D1c %s 第%d天：本站已隐藏' % (rid, di + 1), any(r['k'] == str(k) and r['h'] for r in aft))
            if rid == 'xa3' and di == 0:
                check('D1d xa3 第 1 天去掉碑林后：并掉的那段车程由模型重算（data-np-s0 记着原文）', any(r['s0'] for r in aft), [r['m'] for r in aft])
            pg.evaluate("localStorage.clear()")
        ctx.close()
    with guard('D2'):
        ctx, pg = newctx(br)
        res = {}
        for rid in ('xw45a', 'xa3'):
            pg.goto(B + '/trip/%s/' % rid); pg.wait_for_timeout(800)
            pg.click('.tl > .r.see .adj >> nth=0'); pg.wait_for_timeout(2800)
            res[rid] = pg.evaluate("(function(){var b=document.querySelector('.pk [data-np=rep]');return b?[b.disabled,b.innerText.replace(/\\n/g,'/')]:null})()")
        check('D2a xw45a “换成…”置灰并写原因', res['xw45a'] and res['xw45a'][0] and '/' in res['xw45a'][1], res)
        check('D2b xa3 “换成…”可点（有候选）', res['xa3'] and not res['xa3'][0], res)
        ctx.close()

    # ———— R1 / R2 / H* ————
    with guard('R1'):
        bad = []; whys = []; n_chk = 0; mism = []; n_cmp = 0
        for org in ('上海', '北京', '成都', '广州'):
            ctx, pg = newctx(br)
            pg.goto(B + '/'); pg.evaluate("localStorage.setItem('zouni_org','%s');localStorage.setItem('zouni_pick','{\"w\":\"o\"}')" % org)
            pg.reload(); pg.wait_for_timeout(1500)
            for band in ('d1', 'd2', 'd3'):
                try:
                    pg.click('.dchips [data-b=%s]' % band); pg.wait_for_timeout(300)
                    if not pg.evaluate("document.querySelector('.pick').classList.contains('open')"): pg.click('.pkh'); pg.wait_for_timeout(200)
                    pg.click('.pkr[data-k=d] [data-v=%s]' % {'d1': 'w', 'd2': 'm', 'd3': 'l'}[band]) if not pg.evaluate("!!document.querySelector('.pkr[data-k=d] .on')") else None
                    pg.click('.pkr[data-k=w] [data-v=o]') if not pg.evaluate("!!document.querySelector('.pkr[data-k=w] .on')") else None
                    pg.wait_for_timeout(400)
                except Exception: pass
                items = pg.evaluate("[].slice.call(document.querySelectorAll('.pkres li')).map(function(l){return[l.querySelector('a').getAttribute('href'),l.querySelector('small').innerText]})")
                for href, why in items:
                    whys.append(why)
                    if '没有长爬坡' in why: bad.append(('文案', href, why))
                    pg2 = ctx.new_page(); pg2.goto(B + href); pg2.wait_for_timeout(900)
                    w = pg2.evaluate("[].slice.call(document.querySelectorAll('.dload.warn')).length")
                    if w: bad.append(('偏累天', org, href, w))
                    gw = pg2.evaluate("(document.querySelector('section.go .gw span')||{}).innerText||''")
                    n_chk += 1
                    first = re.split(r'[；。]', why.split(' · ')[1] if ' · ' in why else why)[0]
                    m = re.search(r'(从\S+?(?:坐|开|飞)[^，；。]*?约 \d+ 小时)', why); g = re.search(r'(从\S+?(?:坐|开)[^，；。]*?约 \d+ 小时)', gw)
                    if m and g: n_cmp += 1
                    if m and g and m.group(1) != g.group(1): mism.append((org, href, m.group(1), g.group(1)))
                    pg2.close()
            ctx.close()
        check('R1 “带老人孩子”前三条（4 个出发地 × 3 档天数，共查 %d 个页面）：没有偏累的天、不写“没有长爬坡”（%s）' % (n_chk, bad[:3]), n_chk >= 6 and not bad, bad[:5])
        check('R2 结果卡的去程时间和线路页“怎么去”同一句（比了 %d 条，%d 条不一致：%s）' % (n_cmp, len(mism), mism[:3]), n_cmp >= 3 and not mism, (n_cmp, mism[:5]))
    with guard('R3'):
        ctx, pg = newctx(br)
        pg.goto(B + '/'); pg.evaluate("localStorage.setItem('zouni_fav',JSON.stringify([{id:'xa3',label:'西安 3 天',title:'三天，在西安看一千年',n:3},{id:'bj4',label:'北京 4 天',title:'四天',n:4}]))")
        pg.reload(); pg.wait_for_timeout(1200); pg.click('.minebtn'); pg.wait_for_timeout(500)
        pg.evaluate("[].slice.call(document.querySelectorAll('.mrc')).slice(0,2).forEach(function(c){c.click()})"); pg.wait_for_timeout(200)
        pg.click('.mcmp'); pg.wait_for_timeout(1500)
        rows = pg.evaluate("[].slice.call(document.querySelectorAll('.cmpt tbody tr')).map(function(r){return r.innerText.replace(/\\s+/g,' ')})")
        check('R3 对比页有“去程”“降雨”两行（%s）' % [r[:16] for r in rows], any(r.startswith('去程 ') and len(r) > 4 for r in rows) and any(r.startswith('降雨') for r in rows), rows)
        ctx.close()
    with guard('H1'):
        ctx, pg = newctx(br)
        pg.goto(B + '/'); pg.wait_for_timeout(1200)
        n0 = pg.evaluate("(document.querySelector('.items li:not([hidden]) .num')||{}).textContent")
        check('H1 “现在去正好”第一条编号是 01（%s）' % n0, n0 == '01', n0)
        base_h = pg.evaluate("document.querySelector('.cv .go').getAttribute('href')")
        pg.click('.dchips [data-b=d1]'); pg.wait_for_timeout(500)
        h = pg.evaluate("document.querySelector('.cv .go').getAttribute('href')")
        n = pg.evaluate("(function(h){var l=[].slice.call(document.querySelectorAll('.items li')).filter(function(x){return x.dataset.h===h})[0];return l?+l.dataset.n:null})('%s')" % h)
        n_static = pg.evaluate("(function(h){var l=[].slice.call(document.querySelectorAll('.items li')).filter(function(x){return x.dataset.h===h})[0];return l?+l.dataset.n:-1})('%s')" % base_h)
        # 封面那一条被摘出了列表：用 ZHA / li 找不到时按 /trip/<id>/ 页面里的天数查
        if n is None:
            pg3 = ctx.new_page(); pg3.goto(B + h); pg3.wait_for_timeout(600); n = pg3.evaluate("+document.querySelector('article.trip').dataset.n0"); pg3.close()
        check('H2a 选了周末 2–3 天：封面是 ≤3 天的线（%s，%s 天）' % (h, n), h != base_h and n is not None and n <= 3, (h, n))
        pg.click('.dchips [data-b=d1]'); pg.wait_for_timeout(500)
        check('H2b 取消后封面回到建站时的那一条', pg.evaluate("document.querySelector('.cv .go').getAttribute('href')") == base_h, pg.evaluate("document.querySelector('.cv .go').getAttribute('href')"))
        ctx.close()
    with guard('H3'):
        ctx, pg = newctx(br, 390, 700)
        pg.goto(B + '/'); pg.evaluate("localStorage.setItem('zouni_org','上海')"); pg.reload(); pg.wait_for_timeout(1400)
        pg.click('.pkh'); pg.wait_for_timeout(300)
        pg.click('.pkr[data-k=d] [data-v=w]'); pg.click('.pkr[data-k=w] [data-v=c]'); pg.wait_for_timeout(1200)
        vis = pg.evaluate("(function(){var r=document.querySelector('.pkres')||document.querySelector('.pick .pkhint');if(!r)return null;var b=r.getBoundingClientRect();return[Math.round(b.top),Math.round(b.bottom),innerHeight]})()")
        check('H3 选满三项后结果在视野里（%s）' % vis, vis and vis[0] >= 0 and vis[0] < vis[2] - 40, vis)
        ctx.close()
    br.close()
env.finish('w2_checks')
sys.exit(1 if (env.fails or [e for e in env.errs if e.startswith('INJECT-NOT-APPLIED') or not env.inject]) else 0)
