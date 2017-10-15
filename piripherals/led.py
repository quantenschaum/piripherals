"""an interface to NeoPixel LEDs based on rpi_ws281x"""

__all__ = ['NeoPixels']

from time import sleep
from .util import *
from threading import Thread, Condition, RLock


def wheel(p):
    a = 3 * (p % (1 / 3))
    c1, c2, c3 = [int(255 * x) for x in (1 - a, a, 0)]
    b = int(3 * p)
    if b == 0:
        return c1, c2, c3
    elif b == 1:
        return c3, c1, c2
    else:
        return c2, c3, c1


class NeoPixels(object):
    """NeoPixels with asynchronous animation support."""

    def __init__(self, num=1, pin=12, type='GRB'):
        from rpi_ws281x import PixelStrip
        self.strip = PixelStrip(num, pin)
        self.strip.begin()
        self.strip.show()
        self._start_loop()

    def brightness(self, b=1):
        self._running = False
        self._cond.acquire()
        self.strip.setBrightness(int(255 * b))
        self.strip.show()
        self._cond.release()

    def color(self, led=None, r=0, g=-1, b=-1, v=-1):
        self._running = False
        self._cond.acquire()
        if led and led < 0:
            led += self.strip.numPixels()
        if g < 0:
            g = r
        if b < 0:
            b = g
        if v >= 0:
            self.strip.setBrightness(int(255 * v))
        rgb = [int(255 * v) for v in (r, g, b)]
        if led is None:
            for i in range(self.strip.numPixels()):
                self.strip.setPixelColorRGB(i, *rgb)
        else:
            self.strip.setPixelColorRGB(led, *rgb)
        self.strip.show()
        self._cond.release()

    def _start_loop(self):
        self._cond = Condition(RLock())
        self._cond.acquire()

        def start_stop_loop():
            self._cond.acquire()
            while True:
                self._cond.notify()
                self._cond.wait()
                try:
                    self._animation_loop()
                except:
                    self._cond.notify()
                    self._cond.release()
                    raise
                if self._atexit:
                    self._atexit()

        fork(start_stop_loop)

        self._cond.wait()
        self._cond.release()

    def _animation_loop(self):
        from time import monotonic
        t0 = monotonic()
        try:
            self._running = True
            while self._running:
                t = monotonic() - t0
                if self._timeout and t > self._timeout:
                    break
                tau = (t * self._freq) % 1
                self._func(t, tau)
                if self._fade:
                    self.strip.setBrightness(int(255 * (1 - t / self._fade)))
                self.strip.show()
                sleep(self._delay)
        finally:
            self._running = False

    def animate(self,
                func,
                atexit=None,
                freq=1,
                period=0,
                timeout=0,
                cycles=0,
                fade=0,
                delay=0.01,
                wait=False):

        self._running = False
        self._cond.acquire()
        self._func = func
        self._atexit = atexit or (lambda: self.color(v=1))
        self._freq = 1 / period if period else freq
        self._timeout = fade or ((cycles / self._freq) if cycles else timeout)
        self._fade = fade
        self._delay = delay
        if wait and not self._timeout:
            raise Exception('dead lock: wait=1 and timeout=0')

        self._cond.notify()
        if wait:
            self._cond.wait()
        self._cond.release()

    def breathe(self, n=1, fade=0, color=None, **kwargs):
        from math import exp, cos, pi
        a, b = exp(-n), 1 / (exp(n) - exp(-n))
        if fade:
            def h(t): return 1 - t / fade
            kwargs['timeout'] = fade
        else:
            def h(t): return 1

        def g(t, s): return b * (exp(-n * cos(2 * pi * s)) - a) * h(t)

        def f(t, s): return self.strip.setBrightness(int(255 * g(t, s)))
        if color:
            self.color()
        self.animate(f, **kwargs)

    def rainbow(self, **kwargs):
        def f(t, s):
            n = self.strip.numPixels()
            for i in range(n):
                self.strip.setPixelColorRGB(i, *wheel((i / n - s) % 1))

        self.animate(f, **kwargs)

    def blink(self, pattern='10', **kwargs):
        if ' ' in pattern:
            pattern = pattern.split()
        pattern = [max(0, min(1, float(s))) for s in pattern]
        l = len(pattern)

        def g(s): return pattern[int(s * l)]

        def f(t, s): return self.strip.setBrightness(int(255 * g(s)))
        self.animate(f, **kwargs)

    def sequence(self,
                 colors=[(1, 0, 0), (0.5, 0.5, 0), (0, 1, 0), (0, 0.5, 0.5),
                         (0, 0, 1), (0.5, 0, 0.5)],
                 **kwargs):
        colors = [tuple(map(lambda x: int(255 * float(x)), c)) for c in colors]
        l = len(colors)

        def f(t, s): return self.strip.setPixelColorRGB(0, *colors[int(s * l)])
        self.animate(f, **kwargs)

    def spin(self, **kwargs):
        pass

    def clock(self, flash=0, secs=1, fade=0, **kwargs):
        from datetime import datetime
        from math import floor, ceil

        n = self.strip.numPixels()

        def color(r, g, b): return (r << 16) | (g << 8) | b

        def f(t, s):
            now = datetime.now()
            h, m, s, us = now.hour, now.minute, now.second, now.microsecond

            def pos(v, single=0):
                v *= n
                if single:
                    return [(round(v) % n, 1)]
                else:
                    return [
                        (floor(v), (1 - v % 1)),  #
                        (ceil(v) % n, (v % 1))
                    ]

            def get(i):
                return self.strip.getPixelColor(i)

            def set(i, c):
                return self.strip.setPixelColor(i, c)

            def add(i, c):
                set(i, get(i) | c)

            g = 2.5

            for i in range(n):
                set(i, 0)

            for i, v in pos(h / 12, 1):
                add(i, color(int(255 * v), 0, 0))

            for i, v in pos((m + s / 60) / 60, 0):
                add(i, color(0, int(255 * v**g), 0))

            if secs:
                for i, v in pos((s + us * 1e-6) / 60, 0):
                    add(i, color(0, 0, int(255 * v**g)))

            if flash > 1:
                for i, v in pos((us * 1e-6), 0):
                    v = int(20 * v**g)
                    add(i, color(v, v, v))

            if flash and us < 0.1e6:
                add(0, color(255, 255, 255))

        self.animate(f, **kwargs)


if __name__ == '__main__':
    main()


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

    parser = ArgumentParser(
        description=__doc__, formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('num', type=int, help='number of pixels')
    parser.add_argument('pin', type=int, help='BCM# of data pin')
    args = parser.parse_args()

    print('led-test')

    p = NeoPixels(args.num, args.pin)
    p.rainbow(wait=1, fade=10)
    p.color(r=0.3, v=0)
    p.breathe(period=3, n=3, cycles=3, wait=1)
    p.clock(fade=600)
    on_change(__file__, exit, forking=0)
