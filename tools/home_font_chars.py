#!/usr/bin/env python3
"""首页字体：收集“首页打开时实际渲染的汉字”按（字体族, 字重）分组，写 tools/home_font_chars.json（2026-10-17）。

为什么：首页要 45 个字体切片、2.8MB（Slow 3G 下 50 秒以上）。切片是按字频切的，每片 100–200 字，首页每片只用到几个字；
改成“首页专用的小字体”（只含首页首屏渲染的字，一个字重一个文件，见 tools/make_home_fonts.py），其余字仍走原来的切片、用到才下载。

用法（先建好站，项目根目录）：  python3 tools/home_font_chars.py build/site
收集口径：真打开首页（390 宽，移动端）；遍历文字节点，只收“有渲染框、不 hidden”的（display:none 的卡片不会触发字体下载）；
点开才出现的弹层、提示条、第 9 条起的卡片，用到什么字就走原来的切片（用到才下载）。
"""
import functools, http.server, json, os, re, socketserver, sys, threading
from playwright.sync_api import sync_playwright

site = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.abspath('build/site')
JS = """()=>{const res={};const w=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);let n;
 while(n=w.nextNode()){const t=n.nodeValue;if(!t.trim())continue;const el=n.parentElement;if(!el||['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName))continue;
  if(!el.getClientRects().length)continue;const cs=getComputedStyle(el);if(cs.visibility==='hidden')continue;
  const fam=cs.fontFamily.split(',')[0].replace(/["']/g,'').trim();const key=fam+'|'+cs.fontWeight;(res[key]=res[key]||new Set());for(const ch of t)if(ch.trim()&&ch.charCodeAt(0)>0x20)res[key].add(ch)}
 const o={};for(const k in res)o[k]=[...res[k]].join('');return o}"""


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass


def main():
    socketserver.TCPServer.allow_reuse_address = True
    srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(Q, directory=site)); threading.Thread(target=srv.serve_forever, daemon=True).start()
    B = 'http://127.0.0.1:%d' % srv.server_address[1]
    out = {}
    with sync_playwright() as p:
        br = p.chromium.launch(); c = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, locale='zh-CN', timezone_id='Asia/Shanghai')
        pg = c.new_page(); pg.route(re.compile(r'.*open-meteo.*'), lambda r: r.abort())
        pg.goto(B + '/', wait_until='networkidle'); pg.wait_for_timeout(1500)
        for k, v in pg.evaluate(JS).items(): out.setdefault(k, set()).update(v)
        # 首页上一点就出来的东西：日期面板、“替我挑三条”展开（真点开再收一遍字），不然用户第一次点就多下几个切片
        for sel_ in ('.pkh', '.hdt'):
            try:
                pg.click(sel_, timeout=4000); pg.wait_for_timeout(500)
                for k, v in pg.evaluate(JS).items(): out.setdefault(k, set()).update(v)
                pg.keyboard.press('Escape'); pg.evaluate("document.querySelectorAll('.pk-x').forEach(b=>b.click())"); pg.wait_for_timeout(200)
            except Exception: pass
        # 伪元素里的字（› ‹ ✓ ▴ 之类写在 CSS 的 content 里，遍历文字节点看不到）：全站 css 里的 content 字符串，Sans 400/700 都带上
        css = open(os.path.join(site, 'assets', 'site.css'), encoding='utf-8').read()
        pse = {ch for m in re.findall(r'content:\s*"([^"]*)"', css) for ch in m if ch.strip() and ord(ch) > 0x20 and not ch.startswith('\\')}
        for k_ in ('Noto Sans SC|400', 'Noto Sans SC|700'): out.setdefault(k_, set()).update(pse)
        # 首屏 8 张卡每天不一样（按今天正当季排）：把前 60 张卡 + 全部卡标题里最常用的 600 个字也算进去，换了一批卡也不用再下大切片
        try:
            pg.wait_for_function("document.documentElement.getAttribute('data-hb')", timeout=15000)
            lis = pg.evaluate("[...document.querySelectorAll('.now .items li')].map(li=>({h:(li.querySelector('h3')||{}).textContent||'',t:li.innerText||''}))")
        except Exception:
            lis = []
        import collections
        fq = collections.Counter(ch for x in lis for ch in x['h'] if ch.strip() and ord(ch) > 0x2e7f)
        ft = collections.Counter(ch for x in lis for ch in x['t'] if ch.strip() and ord(ch) > 0x2e7f)
        out.setdefault('Noto Serif SC|900', set()).update({ch for x in lis[:60] for ch in x['h'] if ch.strip()} | {ch for ch, _ in fq.most_common(600)})
        out.setdefault('Noto Sans SC|400', set()).update({ch for x in lis[:60] for ch in x['t'] if ch.strip()} | {ch for ch, _ in ft.most_common(600)})
        br.close()
    # 字重落到现有的面上：Sans 只有 400/500/700（900 用 700，600 用 700），Serif 只有 700/900（400/500 用 700，600 用 700，800 用 900）
    def face(k):
        fam, w = k.split('|'); w = int(w)
        if fam == 'Noto Sans SC': return fam + '|' + ('400' if w <= 400 else '500' if w == 500 else '700')
        if fam == 'Noto Serif SC': return fam + '|' + ('900' if w >= 800 else '700')
        return k
    merged = {}
    for k, v in out.items(): merged.setdefault(face(k), set()).update(v)
    out = merged
    res = {k: ''.join(sorted(v)) for k, v in sorted(out.items())}
    json.dump(res, open('tools/home_font_chars.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for k, v in res.items(): print(k, len(v))


if __name__ == '__main__':
    main()
