#!/usr/bin/env python3
"""详情页“少就是多”的前后数字表（只打印，不判定；写 docs/handoff/02 的“详情页元素清单”用）。

用法：python3 tests/detail_simplify_table.py <改动前的站目录> <改动后的站目录> [--shots DIR]
每条线路（xa3 / xl9a / hss1a / tk4 / xv29a / hcz1）在两个站里各量一遍（390×844，亮色，默认状态）：
  页高 px / 屏、第 1 天标题离页顶 px / 屏、页头区（页顶到第 1 天标题）可见可点元素数 / 文字块数 / 字数、第一屏（不滚动）可点元素数 / 字数、
  第 1 天标题到第一行时间线的 px、第 1 天“非站点”按钮数、全页“关上 / ×”入口数（弹层里数，见 detail_simplify_check S1）。
"""
import functools, http.server, json, os, socketserver, sys, threading
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ux_common import new_ctx, new_page, NO_NET

class Env2:
    errs = []

def serve(d):
    class Q(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    socketserver.TCPServer.allow_reuse_address = True
    s = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=d))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return 'http://127.0.0.1:%d' % s.server_address[1]

M = """(()=>{const H=innerHeight;const vis=(e)=>{const r=e.getBoundingClientRect(),cs=getComputedStyle(e);return r.width>0&&r.height>0&&cs.visibility!=='hidden'&&cs.display!=='none'&&!e.closest('[hidden]')&&!(e.closest('details:not([open])')&&!e.closest('summary'))};
 const d1=document.getElementById('d1'),L=d1.getBoundingClientRect().top+scrollY;
 const clk=(lim)=>[...document.querySelectorAll('a[href],button,input:not([type=hidden]),select,summary,[role=button]')].filter(e=>vis(e)&&(e.getBoundingClientRect().top+scrollY)<lim&&(e.getBoundingClientRect().top+scrollY)>=0).length;
 const chars=(lim,top)=>{let n=0;const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let t;while(t=w.nextNode()){const s=t.nodeValue.replace(/\\s+/g,'');if(!s)continue;const p=t.parentElement;if(!p||p.closest('script,style,svg,noscript,[hidden]')||!vis(p))continue;const rg=document.createRange();rg.selectNodeContents(t);const r=rg.getBoundingClientRect();if(r.height<1)continue;const y=r.top+scrollY;if(y<lim&&y>=top)n+=s.length}return n};
 const tl=d1.querySelector('.tl > .r'),btn=[...d1.querySelectorAll('button,[role=button]')].filter(b=>vis(b)&&!b.closest('.tl')&&!b.closest('.stays')&&!b.closest('.latewarn')).length;
 return {h:document.documentElement.scrollHeight,y:Math.round(L),headClk:clk(L),headChars:chars(L,0),fsClk:clk(H),fsChars:chars(H,0),gap:Math.round(tl.getBoundingClientRect().top+scrollY-L),dayBtn:btn}})()"""

def measure(br, base, rid):
    c = new_ctx(br, None); pg = new_page(Env2, c, hits_errors=False)
    pg.goto(base + '/trip/%s/' % rid, wait_until='networkidle'); pg.wait_for_timeout(900)
    r = pg.evaluate(M); c.close(); return r

if __name__ == '__main__':
    old, new = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
    bo, bn = serve(old), serve(new)
    with sync_playwright() as p:
        br = p.chromium.launch()
        print('线路   | 页高 px（屏）          | 第1天标题 px（屏）     | 页头区 可点/字数        | 第一屏 可点/字数      | 标题→第一行 px | 第1天非站点按钮')
        for rid in ['xa3', 'xl9a', 'hss1a', 'tk4', 'xv29a', 'hcz1']:
            a, b = measure(br, bo, rid), measure(br, bn, rid)
            f = lambda k, d=844.0: '%d→%d' % (a[k], b[k])
            print('%-6s | %s（%.1f→%.1f 屏）| %s（%.2f→%.2f 屏）| %s / %s | %s / %s | %s | %s' % (rid, f('h'), a['h'] / 844, b['h'] / 844, f('y'), a['y'] / 844, b['y'] / 844, f('headClk'), f('headChars'), f('fsClk'), f('fsChars'), f('gap'), f('dayBtn')))
        br.close()
