# 画板标签配对检查：删改模板后跑一遍，防止留下半截标签把后面的内容挤乱
import re, sys, glob
bad=0
for f in sorted(glob.glob((sys.argv[1] if len(sys.argv)>1 else '.')+'/*.dc.html')):
    s=open(f,encoding='utf-8').read()
    for t in ('div','sc-if','sc-for','a','button','span'):
        o=len(re.findall(r'<'+t+r'[\s>]',s)); c=len(re.findall(r'</'+t+r'>',s))
        if o!=c: print('✗', f.split('/')[-1], t, o, c); bad+=1
print('标签配对', '全部成对' if not bad else f'{bad} 处不成对'); sys.exit(1 if bad else 0)
