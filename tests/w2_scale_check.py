#!/usr/bin/env python3
"""大字体 + 点击区（2026-10-29 第 2 波，slow.md #3/#4/#5）。会红。

用法（项目根目录；先建好站）：
    python3 tests/w2_scale_check.py build/site_w2 [--shots DIR]
    python3 tests/w2_scale_check.py build/site_w2 --inject px_font|dt_nobox|adj_small   # 反向自检，必须变红

“系统字体放大 1.5 倍”怎么模拟：Android / 浏览器的“字体大小”改的是浏览器默认字号（16px → 24px），页面里用 rem 的字号跟着变，用 px 的不动，
@media 里的 rem 也按它算。用 CDP 的 Page.setFontSizes（standard=24）改真实的默认字号（不是给 <html> 写样式：那样 @media 里的 rem 不会变）。
第 1 步先断言“site.css 里除地图界面（.rm*）和 SVG 以外没有 px 字号”。
  Z1  site.css：非地图规则里的 font-size / font 简写 / line-height 全部不是 px（rem / em / 无单位）
  Z2  首页 360 / 390 宽、1.5 倍：封面标题 h2 和“走你”h1 不重叠；整页不横向溢出
  Z3  行程页 360 / 390 宽、1.5 倍：“改日期”和“最长一天”（第二格）不重叠；价格不被截断（scrollWidth ≤ clientWidth）；标题不压到“走”“分享”方块；整页不横向溢出
  Z4  行程页 1 倍：“改这站”“改时间”“N 人 · 每人 ›”“改日期”“要预约 ›”的实际点击区（elementFromPoint 扫出来的，含不可见的扩点）宽高都 ≥ 44px；1.5 倍下仍 ≥ 44
  Z5  1 倍下首页和行程页的版面和改字号前一样：关键元素的框（h1 / 价格 / 改日期）宽高在改前的站（--base 目录，可选）上差 ≤ 1px
"""
import os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'px_font': ('assets/site.css', '.glance .big{', '.glance .big{font-size:20px!important;'),
    'dt_nobox': ('assets/site.css', '.glance .dt:after{content:"";position:absolute;left:-8px;right:-8px;top:-12px;bottom:-12px}', ''),
    'adj_small': ('assets/site.css', '.r .s .adj:after,.adj:after{inset:-2px -10px -18px -10px}', '.r .s .adj:after,.adj:after{inset:0}'),
}
env = Env(INJ)
check, guard = env.check, env.guard
def newpage(br, W, sc, H=800):
    ctx = br.new_context(viewport={'width': W, 'height': H}, locale='zh-CN', timezone_id='Asia/Shanghai')
    pg = ctx.new_page(); pg.on('pageerror', lambda e: env.errs.append(str(e)))
    if sc != 16: ctx.new_cdp_session(pg).send('Page.setFontSizes', {'fontSizes': {'standard': sc, 'fixed': round(sc * 13 / 16)}})
    return ctx, pg
OVER = """(function(a,b){var A=document.querySelector(a),B=document.querySelector(b);if(!A||!B)return'无元素 '+(A?'':a)+(B?'':b);var r=A.getBoundingClientRect(),s=B.getBoundingClientRect();var ox=Math.min(r.right,s.right)-Math.max(r.left,s.left),oy=Math.min(r.bottom,s.bottom)-Math.max(r.top,s.top);return(ox>1&&oy>1)?'重叠 '+Math.round(ox)+'x'+Math.round(oy):''})"""
HIT = """(function(sels){var o={};sels.forEach(function(s){var e=document.querySelector(s);if(!e){o[s]=null;return}e.scrollIntoView({block:'center',behavior:'instant'});var r=e.getBoundingClientRect(),x0=1e9,x1=-1e9,y0=1e9,y1=-1e9,n=0;
 for(var y=Math.floor(r.top)-40;y<=r.bottom+40;y+=1)for(var x=Math.floor(r.left)-40;x<=r.right+40;x+=2){var t=document.elementFromPoint(x,y);if(t&&(t===e||e.contains(t))){n++;if(x<x0)x0=x;if(x>x1)x1=x;if(y<y0)y0=y;if(y>y1)y1=y}}
 o[s]=n?[Math.round(x1-x0+2),Math.round(y1-y0+1)]:[0,0]});return o})"""
OVERFLOW = "(document.documentElement.scrollWidth-document.documentElement.clientWidth)"

with sync_playwright() as p:
    br = p.chromium.launch()

    with guard('Z1'):
        css = open(os.path.join(env.site, 'assets', 'site.css'), encoding='utf-8').read()
        bad = []
        for m in re.finditer(r'([^{}]*)\{([^{}]*)\}', css):
            sel, body = m.group(1).strip(), m.group(2)
            if re.search(r'(^|[ ,>.+])\.rm([ .\-,:>[]|$)|\.rm-|svg|\.mp-|\.mk-|wmap|hmap', sel): continue
            for d in re.findall(r'(?:font-size|line-height):\s*[\d.]+px|font:[^;}]*?\s[\d.]+px', body): bad.append((sel[:50], d))
        check('Z1 site.css 非地图规则里没有 px 字号（rem 才跟着系统字号走）%s' % ('' if not bad else '：' + str(bad[:5])), not bad, len(bad))

    for W in (360, 390):
        for sc, nm in ((24, '1.5 倍'), (16, '1 倍')):
            if sc == 16 and W == 360: continue
            with guard('Z2 首页 %d %s' % (W, nm)):
                ctx, pg = newpage(br, W, sc)
                pg.goto(env.B + '/'); pg.wait_for_timeout(900)
                if sc != 16:
                    check('Z2a 首页 %d %s：封面标题和“走你”不重叠' % (W, nm), pg.evaluate(OVER + "('.cv h2','.mast h1')") == '', pg.evaluate(OVER + "('.cv h2','.mast h1')"))
                    check('Z2b 首页 %d %s：封面标题和“最好到…”小字不重叠' % (W, nm), pg.evaluate(OVER + "('.cv h2','.cv .kick')") == '', pg.evaluate(OVER + "('.cv h2','.cv .kick')"))
                    check('Z2c 首页 %d %s：封面标题不压到“我的行程”' % (W, nm), pg.evaluate(OVER + "('.cv h2','.minebtn')") == '', pg.evaluate(OVER + "('.cv h2','.minebtn')"))
                    check('Z2d 首页 %d %s：不横向溢出（%dpx）' % (W, nm, pg.evaluate(OVERFLOW)), pg.evaluate(OVERFLOW) <= 1)
                    if env.shots: pg.screenshot(path=os.path.join(env.shots, 'home_%d_%d.png' % (W, sc)))
                ctx.close()

    for W in (360, 390):
        for rid in ('xa3', 'zl4a'):
            with guard('Z3 行程页 %s %d' % (rid, W)):
                ctx, pg = newpage(br, W, 24)
                pg.goto(env.B + '/trip/%s/' % rid); pg.wait_for_timeout(1500)
                nm = '%s %d 1.5 倍' % (rid, W)
                o = pg.evaluate(OVER + "('.glance .dt','.glance [data-gd]')"); check('Z3a %s：“改日期”和“最长一天”不重叠' % nm, o == '', o)
                o = pg.evaluate(OVER + "('.glance .dt','.glance .big')"); check('Z3b %s：“改日期”和天数大字不重叠' % nm, o == '', o)
                o = pg.evaluate(OVER + "('.glance [data-gd]','.glance .price')"); check('Z3c %s：“最长一天”和价格不重叠' % nm, o == '', o)
                tr = pg.evaluate("(function(){var e=document.querySelector('.glance .price');return e?[e.scrollWidth,e.clientWidth,e.getBoundingClientRect().right]:null})()")
                check('Z3d %s：价格不被截断（%s）' % (nm, tr), tr and tr[0] <= tr[1] + 1 and tr[2] <= W + 0.5, tr)
                o = pg.evaluate(OVER + "('.hero-t h1','.hero .share')"); check('Z3e %s：标题不压到分享按钮' % nm, o == '', o)
                o = pg.evaluate(OVER + "('.hero-t h1','.hero .back')"); check('Z3f %s：标题不压到返回按钮' % nm, o == '', o)
                check('Z3g %s：不横向溢出（%dpx）' % (nm, pg.evaluate(OVERFLOW)), pg.evaluate(OVERFLOW) <= 1)
                pp = pg.evaluate("(function(){var e=document.querySelector('.glance .pp');if(!e)return null;var r=document.createRange();r.selectNodeContents(e);var t=r.getBoundingClientRect(),c=e.parentNode.getBoundingClientRect();return[Math.round(t.right),Math.round(c.right),Math.round(t.left)]})()")
                check('Z3h %s：“N 人 · 每人 ›”文字在自己那一格里、在屏幕里（%s）' % (nm, pp), pp and pp[0] <= pp[1] + 1 and pp[0] <= W and pp[2] >= 0, pp)
                if env.shots: pg.screenshot(path=os.path.join(env.shots, 'trip_%s_%d_15.png' % (rid, W)))
                ctx.close()

    SELS = ['.tl .s .adj', '.fx .st', '.glance .pp', '.glance .dt', 'a.bkn.bkl']
    NAMES = {'.tl .s .adj': '改这站', '.fx .st': '改时间', '.glance .pp': '“N 人 · 每人 ›”', '.glance .dt': '改日期', 'a.bkn.bkl': '要预约 ›'}
    for W in (360, 390):
        for sc, nm in ((16, '1 倍'), (24, '1.5 倍')):
            with guard('Z4 %d %s' % (W, nm)):
                ctx, pg = newpage(br, W, sc)
                pg.goto(env.B + '/trip/xa3/'); pg.wait_for_timeout(1500)
                r = pg.evaluate(HIT + '(%s)' % str(SELS))
                for s in SELS:
                    v = r.get(s)
                    check('Z4 %d %s：%s 点击区 %s ≥ 44×44' % (W, nm, NAMES[s], v), v is not None and v[0] >= 44 and v[1] >= 44, v)
                ctx.close()
    br.close()
env.finish('w2_scale_check')
sys.exit(1 if (env.fails or [e for e in env.errs if e.startswith('INJECT-NOT-APPLIED') or not env.inject]) else 0)
