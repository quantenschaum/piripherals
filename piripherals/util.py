"""utility functions and classes"""

__all__ = ['fork', 'not_raising', 'IRQHandler', 'Poller', 'on_change', 'noop']

from time import sleep
from threading import Thread, Event
from functools import partial


def fork(func):
    """run func asynchronously in a DaemonThread"""
    Thread(target=func, daemon=True).start()


noop = lambda *x: None


def not_raising(func):
    """Wraps a function and swallows exceptions.

    Args:
        func: function to wrap

    Returns:
        wrapped function, that does not raise Exceptions,
        Exceptions are printed to console
    """
    import traceback

    def logging_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            traceback.print_exc()

    return logging_func


def on_change(file, callback, delay=1, forking=1):
    from os.path import getmtime
    t = getmtime(file)

    def check():
        while True:
            if getmtime(file) != t:
                callback()
            sleep(delay)

    if forking:
        fork(check)
    else:
        check()


class IRQHandler:
    """Abstraction of an IRQ handler.

    An edge on the IRQ pin sets a flag.  The callback is invoked on a separate
    thread when the flag was set.  The flag is reset when the pin is high again.
    The callback may be invoked repeatedly if the pin does not reset. So you have
    to reset the IRQ inside the callback, such that when the callback returns,
    the IRQ line is high again.

    This uses RPi.GPIO_ internally.

    .. _RPi.GPIO: https://pypi.python.org/pypi/RPi.GPIO
    .. _BCM: https://pinout.xyz/

    Args:
        pin (int): BCM_ pin number attached to IRQ line.
        callback: function invoked on IRQ.
        edge (int): fire interrupt on falling=0 or rising=1 edge. 1 inverts
            the logic, so IRQ is considered reset when low.
        pullup (int): activate internal pullup
            1=pullup, 0=nothing, -1=pulldown.
    """

    def __init__(self, pin, callback, edge=0, pullup=1):
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        import atexit
        atexit.register(partial(GPIO.cleanup, pin))

        self._irq = Event()

        pud = [GPIO.PUD_DOWN, GPIO.PUD_OFF, GPIO.PUD_UP][pullup + 1]
        reset = GPIO.LOW if edge else GPIO.HIGH
        edge = GPIO.RISING if edge else GPIO.FALLING
        callback = not_raising(callback)

        GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
        GPIO.add_event_detect(pin, edge, lambda *x: self._irq.set())

        def loop():
            while True:
                self._irq.wait()
                callback()
                if GPIO.input(pin) == reset:
                    self._irq.clear()

        fork(loop)


class Poller:
    """Polling loop as replacement for IRQHandler.

    Use it if using the IRQ line is not possible or desired.

    Args:
        callcack: function that is called continously. The actuall polling
            happens in this callback.
        delay (float): delay in seconds between invocations of callback
    """

    def __init__(self, callback, delay=0.01):

        callback = not_raising(callback)

        def loop():
            while True:
                callback()
                sleep(delay)

        fork(loop)
