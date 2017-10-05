"""an interface to NeoPixel LEDs based on https://github.com/jgarff/rpi_ws281x
"""

# http://python-future.org/compatible_idioms.html
from __future__ import print_function, division

__all__ = ['ColorLED']

from time import sleep
from threading import Thread, Condition, RLock


def wheel(p):
    a = 3 * (p % (1 / 3))
    c1, c2, c3 = [int(255 * x) for x in (1 - a, a, 0)]
    b = int(3 * p)
    if b == 0: return c1, c2, c3
    elif b == 1: return c3, c1, c2
    else: return c2, c3, c1


class ColorLED:
    """a single neopixel with asynchronous animation support
    """

    black = (0, 0, 0)
    red = (1, 0, 0)
    green = (0, 1, 0)
    blue = (0, 0, 1)
    yellow = (1, 1, 0)
    cyan = (0, 1, 1)
    magenta = (1, 0, 1)
    white = (1, 1, 1)

    def __init__(self, pin=12, type='GRB'):
        import neopixel as px
        self._px = px.Adafruit_NeoPixel(
            1, pin, strip_type=getattr(px.ws, 'WS2811_STRIP_' + type))
        self._px.begin()
        self._px.show()
        self._start_loop()

    def _loop(self):
        from time import monotonic
        t0 = monotonic()
        self._running = True
        while self._running:
            t = monotonic() - t0
            if self._timeout and t > self._timeout: break
            tau = (t * self._freq) % 1
            self._func(t, tau)
            self._px.show()
            sleep(self._delay)
        self._running = False

    def _start_loop(self):
        self._cond = Condition(RLock())
        self._cond.acquire()

        def loop():
            self._cond.acquire()
            while True:
                self._cond.notify()
                self._cond.wait()
                try:
                    self._loop()
                except:
                    self._cond.notify()
                    self._cond.release()
                    raise
                if self._atexit: self._atexit()

        Thread(target=loop, daemon=True).start()

        self._cond.wait()
        self._cond.release()

    def animate(self,
                func,
                atexit=None,
                freq=1,
                period=0,
                timeout=0,
                cycles=0,
                delay=0.01,
                wait=False):

        self._running = False
        self._cond.acquire()

        self._func = func
        self._atexit = atexit
        self._freq = 1 / period if period else freq
        self._timeout = (cycles / self._freq) if cycles else timeout
        self._delay = delay

        self._cond.notify()
        if wait: self._cond.wait()
        self._cond.release()

    def color(self, red, green=-1, blue=-1, bri=-1):
        self._running = False
        self._cond.acquire()
        if green < 0: green = red
        if blue < 0: blue = red
        self._px.setPixelColorRGB(0,
                                  int(255 * red),
                                  int(255 * green), int(255 * blue))
        if bri >= 0:
            self._px.setBrightness(int(255 * bri))
        self._px.show()
        self._cond.release()

    def breathe(self, n=1, fade=0, color=None, **kwargs):
        from math import exp, cos, pi
        a, b = exp(-n), 1 / (exp(n) - exp(-n))
        if fade:
            h = lambda t: 1 - t / fade
            kwargs['timeout'] = fade
        else:
            h = lambda t: 1
        g = lambda t, s: b * (exp(-n * cos(2 * pi * s)) - a) * h(t)
        f = lambda t, s: self._px.setBrightness(int(255 * g(t, s)))
        if color: self.color(*color, bri=0)
        kwargs['atexit'] = lambda: self.color(0, 0, 0, 1)
        self.animate(f, **kwargs)

    def rainbow(self, **kwargs):
        f = lambda t, s: self._px.setPixelColorRGB(0, *wheel(s))
        kwargs['atexit'] = lambda: self.color(0, 0, 0, 1)
        self.animate(f, **kwargs)

    def blink(self, pattern='10', color=None, **kwargs):
        if ' ' in pattern: pattern = pattern.split()
        pattern = [max(0, min(1, float(s))) for s in pattern]
        l = len(pattern)
        g = lambda s: pattern[int(s * l)]
        f = lambda t, s: self._px.setBrightness(int(255 * g(s)))
        if color: self.color(*color, bri=0)
        kwargs['atexit'] = lambda: self.color(0, 0, 0, 1)
        self.animate(f, **kwargs)

    def sequence(self, colors=[(1, 0, 0), (0, 1, 0), (0, 0, 1)], **kwargs):
        colors = [
            tuple(map(lambda x: int(255 * max(0, min(1, float(x)))), c))
            for c in colors
        ]
        l = len(colors)
        f = lambda t, s: self._px.setPixelColorRGB(0, *colors[int(s * l)])
        kwargs['atexit'] = lambda: self.color(0, 0, 0, 1)
        self.animate(f, **kwargs)


if __name__ == '__main__': main()


def main():
    l = ColorLED()
    l.color(*green)
    sleep(1)

    l.blink('100', color=red, period=1, cycles=3, wait=1)
    sleep(1)

    l.sequence(
        colors=[white, red, yellow, green, cyan, blue, magenta],
        period=2,
        cycles=1,
        wait=1)
    sleep(1)

    l.breathe(color=(1, 1, 1, 0), period=5, n=3, fade=30, wait=1)

    sleep(5)
