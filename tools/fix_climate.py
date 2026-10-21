#!/usr/bin/env python3
"""各线实际城市的月均气温（Open-Meteo ERA5 再分析，2015–2024 逐日最高 / 最低温的月平均），写进 data/climate_era5.json。

为什么：目的地级气候表是一整个国家一张（日本全国用东京、挪威用奥斯陆），页面“往年 N 月平均：白天 X℃”
对特罗姆瑟 12 月差 7℃、网走 2 月差 13℃（2026-10-20 国外线测试 abroad.md #3）。现在每条线每一天按“当天所在城市”取这张表。

用法（项目根目录，额度：免费版每天 10000 点、10 年一个格点约 52 点，所以一天取不完，分几天跑）；可反复跑，已有的格子不重取，被限流会自动退避）：
    python3 tools/fix_climate.py            # 补齐所有行程用到的城市
    python3 tools/fix_climate.py --check    # 只统计缺多少，不联网
数据结构：{"source", "years", "cells": {"纬度,经度(0.25° 格点)": {"1": [最高, 最低], ...}}, "cities": {城市: "格点键"}}
用 curl 取（本机 Python urllib 访问 HTTPS 会证书报错）。城市坐标取 data/geo/pois.json 里的“城市|城市”。
"""
import json, os, subprocess, sys, time, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'climate_era5.json')
Y0, Y1 = 2022, 2024     # 免费额度按“天数×地点”计费：10 年一个格点约 52 次、每分钟 600、每天 10000；改成 3 年（月均误差 ≈±1.5℃，闸的容差是 6℃），先取国外和北方
# 已有的格点保留原来的年份（data['cell_years']）
BATCH = 10


FIRST = {'xv612a', 'xv611a', 'xv611b', 'xv610a', 'xv613a', 'xv614a', 'bkk3', 'tk4', 'xl2a', 'xl1a', 'xv14a', 'xl8a'}      # 用户测试报告点名的线先取


def cell(lat, lng): return '%.2f,%.2f' % (round(lat * 4) / 4, round(lng * 4) / 4)


def wanted():
    IT = json.load(open(os.path.join(ROOT, 'data/itineraries.json'), encoding='utf-8'))['itineraries']
    GEO = json.load(open(os.path.join(ROOT, 'data/geo/pois.json'), encoding='utf-8'))
    DM = {d['id'] for d in json.load(open(os.path.join(ROOT, 'data/destinations.json'), encoding='utf-8'))['domestic']}
    cities = {}; prio = {}
    for rid, it in IT.items():
        ab = it['dest'] not in DM
        for c in [it['city']] + [d.get('city') for d in it['days'] if d.get('city')]:
            g = GEO.get(c + '|' + c)
            if g and g.get('lat') is not None:
                cities[c] = cell(g['lat'], g['lng'])
                # 优先级：国外 0；国内北方（北纬 ≥38）或高处（长线）1；其余 2
                pr = -1 if rid in FIRST else (0 if ab else (1 if (g['lat'] >= 38 or len(it['days']) >= 15) else 2))
                prio[cities[c]] = min(prio.get(cities[c], 9), pr)
    wanted.prio = prio
    return cities


def fetch(keys):
    lats = ','.join(k.split(',')[0] for k in keys); lngs = ','.join(k.split(',')[1] for k in keys)
    u = f'https://archive-api.open-meteo.com/v1/archive?latitude={lats}&longitude={lngs}&start_date={Y0}-01-01&end_date={Y1}-12-31&daily=temperature_2m_max,temperature_2m_min&timezone=GMT'
    for wait in (0, 65, 65, 130, 300, 600):
        time.sleep(wait)
        out = subprocess.run(['curl', '-s', '-m', '120', u], capture_output=True, text=True).stdout
        try: j = json.loads(out)
        except Exception: continue
        if isinstance(j, dict) and j.get('error'):
            print('  限流/错误：', j.get('reason'), flush=True)
            if 'aily' in (j.get('reason') or ''): return None
            continue
        return j if isinstance(j, list) else [j]
    return None


def monthly(j):
    acc = collections.defaultdict(lambda: [[], []])
    t = j['daily']['time']
    for i, day in enumerate(t):
        m = int(day[5:7]); a, b = j['daily']['temperature_2m_max'][i], j['daily']['temperature_2m_min'][i]
        if a is not None: acc[m][0].append(a)
        if b is not None: acc[m][1].append(b)
    return {str(m): [int(round(sum(v[0]) / len(v[0]))), int(round(sum(v[1]) / len(v[1])))] for m, v in sorted(acc.items())}


def main():
    cities = wanted()
    data = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {'cells': {}, 'cities': {}}
    global Y0
    if '--ten' in sys.argv:      # 把 3 年的格点（优先级 ≤0：用户报告点名的线和国外）重取成 10 年（高纬度 12 月的年际差可达 ±3℃，3 年不够）；额度恢复后跑
        Y0 = 2015
        need = sorted({k for k in cities.values() if k in data.get('cell_years', {}) and wanted.prio.get(k, 9) <= 0}, key=lambda k: (wanted.prio.get(k, 9), k))
    else:
        need = sorted({k for k in cities.values() if k not in data['cells']}, key=lambda k: (wanted.prio.get(k, 9), k))
    print(f'城市 {len(cities)} 个，格点 {len(set(cities.values()))} 个，缺 {len(need)} 个格点')
    if '--check' in sys.argv: return
    for i in range(0, len(need), BATCH):
        keys = need[i:i + BATCH]; js = fetch(keys)
        if js is None or len(js) != len(keys):
            print('  这一批没取到（多半是当日额度用完），已存的保留；再跑一次会接着取'); break
        for k, j in zip(keys, js): data['cells'][k] = monthly(j)
        data['cities'].update({c: k for c, k in cities.items() if k in data['cells']})
        data['cell_years'] = {**data.get('cell_years', {}), **{k: [Y0, Y1] for k in keys}}
        for k in keys:
            if Y0 == 2015: data['cell_years'].pop(k, None)
        data.update({'source': 'Open-Meteo Historical Weather API（ERA5 再分析），逐日最高/最低温的月平均', 'generated_by': 'tools/fix_climate.py'})
        json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
        print(f'  {min(i + BATCH, len(need))}/{len(need)}', flush=True)
        time.sleep(3)
    data['cities'].update({c: k for c, k in cities.items() if k in data['cells']})
    json.dump(data, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('完成' if all(k in data['cells'] for k in cities.values()) else '还有缺，再跑一次')


if __name__ == '__main__': main()
