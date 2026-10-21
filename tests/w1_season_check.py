#!/usr/bin/env python3
"""季节措辞跟日期走（2026-10-20 第 1 波 B1/B2；abroad.md #1、driver.md #3）。会红。

用法（项目根目录；先 bash build/pipe.sh build/site_w1）：
    python3 tests/w1_season_check.py build/site_w1
    python3 tests/w1_season_check.py build/site_w1 --inject swarn_never|sw_keep|mw_keep|tail_ignored    # 反向自检：只改送到浏览器的 site.js，对应判据必须变红

Z1 特罗姆瑟极夜线（xv612a）建议日期（12/10）：红字行隐藏；极夜 / 冬季轮胎句子（.sw）全部可见
Z2 同一条线改到 6/20：红字行出现（含“不在这条线能走的季节”和能走季节 11/25–12/31）、字是红色；极夜类句子（.sw）全部隐藏
Z3 道东流冰线（xv610a）改到 8/10：流冰 / 雪胎句子全部隐藏，红字行出现，当天气温栏是 8 月的 ERA5（白天不得 ≥28℃，原来写 33℃）
Z4 滇藏线（xl2a，能走 5/10–10/10）改到 10/31：红字行出现；写“9 月上旬”的句子（.mw）在 10/31 之后的日子里全部隐藏；建议日期（9/5）下前 14 天的可见
Z5 一年四季都能去的线（xa3）：没有红字行
Z6 日期落在能走季节中间（xl1a 改到 6/1）：红字行隐藏
Z7 整趟只有后半段出了季节（xl8a 能走 9/20–11/20，改到 11/10）：红字行写“第 N 天（M/D）起”
"""
import os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import *

INJ = {
    'swarn_never': ('assets/site.js', "if(bad<0){W.hidden=true;W.textContent=''}else{", "if(true){W.hidden=true;W.textContent=''}else{"),        # 红字行永远不出现
    'sw_keep': ('assets/site.js', "if(ok&&el.classList.contains('sw')){", "if(false&&el.classList.contains('sw')){"),                    # 冬季提示不隐藏
    'mw_keep': ('assets/site.js', "if(el.classList.contains('mw')&&!szMW(el,date))ok=false;", ""),                                          # “9 月上旬”句子不隐藏
    'tail_ignored': ('assets/site.js', "for(i=0;i<n;i++){if(!szIn(szMD(new Date(d0.getTime()+i*864e5)),o[0],o[1])){bad=i;break}}", "for(i=0;i<1;i++){if(!szIn(szMD(new Date(d0.getTime()+i*864e5)),o[0],o[1])){bad=i;break}}"),      # 只看第一天
}
env = Env(INJ)
check, guard = env.check, env.guard


def setdate(pg, iso):
    pg.evaluate("(v)=>{var k=document.querySelector('.dpk');k.value=v;k.dispatchEvent(new Event('change'))}", iso); pg.wait_for_timeout(400)


def vis(pg, sel):
    return pg.evaluate("(s)=>{var a=[].slice.call(document.querySelectorAll(s));return {n:a.length,shown:a.filter(function(e){return !e.hidden}).length}}", sel)


with sync_playwright() as p:
    br = p.chromium.launch()
    with guard('Z1/Z2'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xv612a/')
        sw = vis(pg, '.sw[data-sw=polar],.sw[data-sw=winter]'); sa = pg.evaluate("(function(){var w=document.querySelector('.swarn');return w?{hidden:w.hidden,t:w.textContent}:null})()")
        check('Z1 建议日期：.sw 有 ≥6 句且全部可见', sw['n'] >= 6 and sw['shown'] == sw['n'], sw)
        check('Z1 建议日期：红字行存在且隐藏', sa is not None and sa['hidden'], sa)
        setdate(pg, '2027-06-20')
        sw = vis(pg, '.sw[data-sw=polar],.sw[data-sw=winter]'); sa = pg.evaluate("(function(){var w=document.querySelector('.swarn');return {hidden:w.hidden,t:w.textContent,c:getComputedStyle(w).color}})()")
        check('Z2 改到 6/20：极夜 / 冬季句子全部隐藏', sw['n'] >= 6 and sw['shown'] == 0, sw)
        check('Z2 改到 6/20：红字行出现，写明不在能走的季节和 11/25–12/31', (not sa['hidden']) and '不在这条线能走的季节' in sa['t'] and '11/25' in sa['t'] and '12/31' in sa['t'], sa)
        m = re.match(r'rgb\((\d+), (\d+), (\d+)\)', sa['c']); check('Z2 红字行是红色（R 明显大于 G、B）', bool(m) and int(m.group(1)) > 120 and int(m.group(1)) > int(m.group(2)) + 60, sa['c'])
        c.close()
    with guard('Z3'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xv610a/'); setdate(pg, '2027-08-10')
        sw = vis(pg, '.sw'); sa = pg.evaluate("document.querySelector('.swarn').hidden")
        check('Z3 8/10：流冰 / 雪胎句子全部隐藏', sw['n'] >= 6 and sw['shown'] == 0, sw)
        check('Z3 8/10：红字行出现', sa is False)
        t = pg.evaluate("(document.querySelector('.day .cl')||{}).textContent||''"); m = re.search(r'白天 (-?\d+)℃', t)
        cl = pg.evaluate("(function(){var c=document.querySelector('.day .cl');try{return JSON.parse(c.dataset.clim)['8']}catch(e){return null}})()")
        check('Z3 8 月网走白天不得 ≥28℃（原来写 33℃）', cl is not None and cl[0] < 28, cl)
        c.close()
    with guard('Z4'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xl2a/')
        mw0 = pg.evaluate("(function(){var a=[].slice.call(document.querySelectorAll('.mw[data-mw^=\"9:\"]')),days=[].slice.call(document.querySelectorAll('.day'));var early=a.filter(function(e){return days.indexOf(e.closest('.day'))<14});return {n:early.length,shown:early.filter(function(e){return !e.hidden}).length,all:a.length}})()")
        check('Z4 建议日期（9/5 出发）：前 14 天里的“9 月上旬”句子 ≥8 句且全部可见（更后面的天已过 9 月 20 日，按设计隐藏）', mw0['n'] >= 8 and mw0['shown'] == mw0['n'] and mw0['all'] >= 15, mw0)
        setdate(pg, '2026-10-31')
        mw1 = pg.evaluate("(function(){var a=[].slice.call(document.querySelectorAll('.mw[data-mw^=\"9:\"]')),days=[].slice.call(document.querySelectorAll('.day'));var late=a.filter(function(e){var s=e.closest('.day');return days.indexOf(s)>=2});return {n:late.length,shown:late.filter(function(e){return !e.hidden}).length}})()")
        sa = pg.evaluate("(function(){var w=document.querySelector('.swarn');return {hidden:w.hidden,t:w.textContent}})()")
        check('Z4 10/31：第 3 天起的“9 月上旬”句子全部隐藏', mw1['n'] >= 8 and mw1['shown'] == 0, mw1)
        check('Z4 10/31：红字行出现', not sa['hidden'] and '能走的季节' in sa['t'], sa)
        c.close()
    with guard('Z5/Z6/Z7'):
        c = new_ctx(br, p); pg = new_page(env, c); goto(env, pg, '/trip/xa3/')
        check('Z5 一年四季都能去的线（xa3）没有红字行', pg.query_selector('.swarn') is None)
        pg.goto(env.B + '/trip/xl1a/', wait_until='networkidle'); pg.wait_for_timeout(500); setdate(pg, '2027-06-01')
        check('Z6 xl1a 6/1 出发（整趟在 5/10–10/10 里）红字行隐藏', pg.evaluate("document.querySelector('.swarn').hidden") is True)
        pg.goto(env.B + '/trip/xl8a/', wait_until='networkidle'); pg.wait_for_timeout(500); setdate(pg, '2026-11-10')
        t = pg.evaluate("(function(){var w=document.querySelector('.swarn');return w.hidden?'':w.textContent})()")
        check('Z7 xl8a 11/10 出发：红字行写“第 N 天（M/D）起”', re.search(r'第 \d+ 天（\d+/\d+）起', t) is not None, t)
        c.close()
    br.close()
env.finish('季节措辞跟日期走')
