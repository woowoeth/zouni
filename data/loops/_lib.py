# 环线 / 长途线路的简写工具
import json
def S(n, q=None, t='sight', dur=None, **k):
    x = {'name': n, 'q': q or n, 'type': t}
    if dur: x['dur'] = dur
    x.update(k); return x
def D(title, text, stops, **k):
    x = {'title': title, 'text': text, 'stops': stops}; x.update(k); return x
def LOOP(dest, city, label, title, days, start, prep, kicker=None, loop=True, drive=True, season=('05-01', '10-31'), tags=None):
    n = len(days)
    return {'dest': dest, 'city': city, 'label': label, 'title': title, 'kicker': kicker or (('自驾环线' if loop else '自驾长线') + f' · {n} 天'),
            'start': start, 'prep': prep, 'days': days, 'drive': drive, 'loop': loop, '_season': season, '_tags': tags or (['自驾', '环线'] if loop else ['自驾', '长途'])}
