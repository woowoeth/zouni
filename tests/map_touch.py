"""CDP 合成触摸（单指拖 / 双指缩放 / 轻点 / 双击 / 双指轻点 / 快速划）：map_app_check.py 和 map_perf 的 fps 采样共用。
走浏览器真实的输入管线（Input.dispatchTouchEvent），所以 touch-action、pointer 事件、maplibre 的手势识别、页面滚动 / 缩放都会真的发生——不是在页面里伪造事件。"""
import time


class Touch:
    def __init__(self, ctx, page):
        self.pg = page; self.cdp = ctx.new_cdp_session(page)

    def _send(self, typ, pts):
        self.cdp.send('Input.dispatchTouchEvent', {'type': typ, 'timestamp': time.time(), 'touchPoints': [{'x': x, 'y': y, 'id': i, 'radiusX': 8, 'radiusY': 8, 'force': 1} for i, (x, y) in enumerate(pts)]})

    def tap(self, x, y, hold=0.04):
        self._send('touchStart', [(x, y)]); time.sleep(hold); self._send('touchEnd', [])

    def double_tap(self, x, y, gap=0.09):
        self.tap(x, y); time.sleep(gap); self.tap(x, y)

    def two_finger_tap(self, x, y, dx=40, hold=0.05):
        self._send('touchStart', [(x - dx, y), (x + dx, y)]); time.sleep(hold); self._send('touchEnd', [])

    def drag(self, x0, y0, x1, y1, steps=14, dt=0.016, release_wait=0.0, hold=0.0):
        """单指从 (x0,y0) 拖到 (x1,y1)。dt 小 = 快（有速度，松手会惯性 / 判定为甩）；dt 大 = 慢拖（松手没速度）"""
        self._send('touchStart', [(x0, y0)])
        if hold: time.sleep(hold)
        for i in range(1, steps + 1):
            t = i / steps; self._send('touchMove', [(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t)]); time.sleep(dt)
        if release_wait: time.sleep(release_wait)
        self._send('touchEnd', [])

    def pinch(self, cx, cy, d0, d1, steps=14, dt=0.016, angle=0.0):
        """双指以 (cx,cy) 为中心，两指间距从 d0 到 d1（水平方向）"""
        def pts(d): return [(cx - d / 2, cy), (cx + d / 2, cy)]
        self._send('touchStart', pts(d0))
        for i in range(1, steps + 1):
            self._send('touchMove', pts(d0 + (d1 - d0) * i / steps)); time.sleep(dt)
        self._send('touchEnd', [])

    def two_drag(self, cx, cy, dx, dy, d=120, steps=12, dt=0.016):
        def pts(k): return [(cx - d / 2 + dx * k, cy + dy * k), (cx + d / 2 + dx * k, cy + dy * k)]
        self._send('touchStart', pts(0))
        for i in range(1, steps + 1):
            self._send('touchMove', pts(i / steps)); time.sleep(dt)
        self._send('touchEnd', [])
