"Things that have to do with controlling LEDs"

from time import sleep, monotonic
from threading import Thread, Condition, RLock
from math import exp, cos, pi, floor, ceil
from datetime import datetime
from .util import *
try:
    from rpi_ws281x import PixelStrip
except:
    pass

__all__ = ['NeoPixels']


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
    """an interface to NeoPixel LEDs based on rpi_ws281x_.

    This wraps around PixelStrip_ and adds additional functionality,
    especially asynchronous animation support.

    Constructor arguments are passed to PixelStrip_.

    Args:
        num (int): # of LEDs on the strip
        pin (int): BCM_ pin number of data pin. not all pins are allowed,
            see `pin usage`_ information of rpi_ws281x_.

    .. _rpi_ws281x: https://pypi.python.org/pypi/rpi_ws281x
    .. _PixelStrip: https://github.com/pimoroni/rpi_ws281x-python/blob/master/library/rpi_ws281x/rpi_ws281x.py#L51
    .. _pin usage: https://github.com/pimoroni/rpi_ws281x/blob/master/README.md
    .. _BCM: https://pinout.xyz/
    """

    _strip = None

    def __init__(self, *args, **kwargs):
        if 'brightness' not in kwargs:
            kwargs['brightness'] = 255
        self._strip = PixelStrip(*args, **kwargs)
        self.auto_show = True
        self._strip.begin()
        self._strip.show()
        self._start_loop()

    def __getattr__(self, name):
        a = getattr(self._strip, name)

        def b(*args, **kwargs):
            self._running = False
            self._cond.acquire()
            a(*args, **kwargs)
            if self.auto_show:
                self._strip.show()
            self._cond.release()

        return b

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
                    self._running = False
                if self._atexit:
                    self._atexit()

        fork(start_stop_loop)

        self._cond.wait()
        self._cond.release()

    def _animation_loop(self):
        t0 = monotonic()
        try:
            self._running = True
            while self._running:
                t = monotonic() - t0  # time since animation start
                if self._timeout and t > self._timeout:
                    break
                s = (t * self._freq) % 1  # normalized period time
                self._func(self._strip, s, t)
                if self._fade:
                    self._strip.setBrightness(int(255 * (1 - t / self._fade)))
                self._strip.show()
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
        """asynchronous animation

        The animation is executed on a separate thread. The animation is stopped,
        when any function, that changes the state of the LEDs, is called. The
        animation is defined in ``func``. This function gets passed 3 arguments:

        - ``p`` - raw PixelStrip_, call methods of this to manipulate the LEDs,
            which results in the animation
        - ``s`` - normalized time in [0,1] in animation period, use this
            to create cyclic animations
        - ``t`` - time in seconds since startof animation

        ``func`` is called repeatedly with ``delay`` between the calls.

        Args:
            func (callable(p,s,t)): animation function
            atexit (callable()): exit hook, function to call after animation
            freq (float): animation frequency in Hz
            period (float): animation period in seconds (freq=1/period),
                give either freq or period, period has higher priority
            timeout (float): animation duration in seconds
            cycles (float): animation cycle count, (timeout=cycles/freq)
                give either timeout or cycles, cycles has higher priority
            fade (float): fade out animation over this number of seconds
                (sets timeout=fade)
            delay (float): delay in seconds between calls of func
            wait (bool): wait for animation to finish,
                synchronous animation, requires timeout
        """

        self._running = False
        self._cond.acquire()
        self._func = func
        self._atexit = atexit or (lambda: self.color(v=1))
        self._freq = 1 / period if period else freq
        self._timeout = fade or ((cycles / self._freq) if cycles else timeout)
        self._fade = fade
        self._delay = delay
        if wait and not self._timeout:
            raise Exception('deadlock: wait=1 and timeout=0')

        self._cond.notify()
        if wait:
            self._cond.wait()
        self._cond.release()

    def brightness(self, b=1):
        """set brightness, affects all LEDs

        Args:
            b (float): brightness in range [0,1]
        """
        self.setBrightness(int(255 * b))

    def color(self, led=None, r=0, g=-1, b=-1, v=-1):
        """set color

        Args:
            led (int): # of LED on strip to set the color for,
                None = all LEDs
            r (float): red value from range [0,1], if not given r = 0
            g (float): green value from range [0,1], if not given g = r
            b (float): blue value from range [0,1], if not given b = g
            v (float): brightness, see :meth:`brightness`,
                is applied to all LEDs
        """
        self._running = False
        self._cond.acquire()
        if led and led < 0:
            led += self._strip.numPixels()
        if g < 0:
            g = r
        if b < 0:
            b = g
        if v >= 0:
            self._strip.setBrightness(int(255 * v))
        rgb = [int(255 * v) for v in (r, g, b)]
        if led is None:
            for i in range(self._strip.numPixels()):
                self._strip.setPixelColorRGB(i, *rgb)
        else:
            self._strip.setPixelColorRGB(led, *rgb)
        if self.auto_show:
            self._strip.show()
        self._cond.release()

    def rainbow(self, **kwargs):
        "rotating rainbow animation, for args see :meth:`animate`"
        def f(p, s, t):
            n = p.numPixels()
            for i in range(n):
                p.setPixelColorRGB(i, *wheel((i / n - s) % 1))

        self.animate(f, **kwargs)

    def breathe(self, n=1, fade=0, color=None, **kwargs):
        """brightness breathing animation.

        This was inspired by http://sean.voisen.org/blog/2011/10/breathing-led-with-arduino/.

        Args:
            n (float): nonlinearity of brightness function
            color(tuple(r,g,b)): color set on animation start
        for other args see :meth:`animate`
        """
        if fade:
            def h(t): return 1 - t / fade
            kwargs['timeout'] = fade
        else:
            def h(t): return 1

        a, b = exp(-n), 1 / (exp(n) - exp(-n))

        def g(t, s): return b * (exp(-n * cos(2 * pi * s)) - a) * h(t)

        def f(p, s, t): return p.setBrightness(int(255 * g(t, s)))

        self.brightness(0)

        if color:
            self.color(None, *color)

        self.animate(f, **kwargs)

    def blink(self, pattern='10', **kwargs):
        if ' ' in pattern:
            pattern = pattern.split()
        pattern = [max(0, min(1, float(s))) for s in pattern]
        l = len(pattern)

        def g(s): return pattern[int(s * l)]

        def f(p, s, t): return p.setBrightness(int(255 * g(s)))
        self.animate(f, **kwargs)

    def sequence(self,
                 colors=[(1, 0, 0), (0.5, 0.5, 0), (0, 1, 0), (0, 0.5, 0.5),
                         (0, 0, 1), (0.5, 0, 0.5)],
                 **kwargs):
        colors = [tuple(map(lambda x: int(255 * float(x)), c)) for c in colors]
        l = len(colors)

        def f(p, s, t): return p.setPixelColorRGB(0, *colors[int(s * l)])
        self.animate(f, **kwargs)

    def clock(self, flash=0, secs=1, fade=0, **kwargs):

        def color(r, g, b): return (r << 16) | (g << 8) | b

        def f(p, s, t):
            now = datetime.now()
            h, m, s, us = now.hour, now.minute, now.second, now.microsecond
            n = p.numPixels()
            g = 2.5  # brightness gamma correction

            def pos(v, single=0):
                v *= n
                if single:
                    return [(round(v) % n, 1)]
                else:
                    return [(floor(v), (1 - v % 1)), (ceil(v) % n, (v % 1))]

            def get(i): return p.getPixelColor(i)

            def set(i, c): return selprip.setPixelColor(i, c)

            def add(i, c): set(i, get(i) | c)

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


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    from signal import pause

    parser = ArgumentParser()
    parser.add_argument('mode', default='clock', help='animation mode')
    parser.add_argument('num', type=int, help='number of pixels')
    parser.add_argument('pin', type=int, help='BCM# of data pin')
    args = parser.parse_args()

    print('led-test')

    p = NeoPixels(args.num, args.pin)

    #p.rainbow(wait=1, fade=10)
    #p.color(r=0.3, v=0)
    #p.breathe(period=3, n=3, cycles=3, wait=1)
    p.clock()
    #on_change(__file__, exit, forking=0)
    pause()


if __name__ == '__main__':
    main()
