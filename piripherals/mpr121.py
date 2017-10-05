"""a sane and complete interface to the MPR121 touch sensor

Since Pythagoras, we know that :math:`a^2 + b^2 = c^2`.


.. math::

   (a + b)^2 = a^2 + 2ab + b^2

   (a - b)^2 = a^2 - 2ab + b^2


This is thought to be a replacement of the incomplete and undocumented
Adafruit.MPR121_ library.

To fully understand this device, please read the datasheet_.

Wiring the MPR121 to the RaspberriPi
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Connect the pins of MPR121 to the RaspberriPi according to the following table.
In this doc and in the code, all Pi pin numbers are BCM_ pin numbers, physical
pin numbers are set in round braces (x).

========= ============
MPR121    RaspberriPi
========= ============
3.3V      3.3V (1)
GND       GND (6)
SDA       BCM 2 (3)
SCL       BCM 3 (5)
IRQ*      BCM 4 (7)
========= ============

Connecting the IRQ line is optional but recommended to avoid unneccessary bus
traffic and CPU load due to polling. To able to use the IRQ, you need to have
RPi.GPIO_ installed (``apt-get install python-rpi.gpio`` or ``pip install RPi.GPIO``).

If you want to connect multiple MPR121s to the same bus, you can change their
address with the address pin. Refer to the datasheet_ on how to do this.

Enable I2C access
~~~~~~~~~~~~~~~~~

The MPR121 uses I2C for communication. On the RaspberriPi running
Raspbian_ Stretch, you need to enable the I2C bus. To ``/boot/config.txt``
add the lines::

    dtparam=i2c_arm=on
    dtparam=i2c1=on

and to ``/etc/modules`` add::

    i2c-dev

This should enable the ``/dev/i2c-1`` (bus=1) device on boot. Install i2c-tools with::

    apt-get install i2c-tools

and list the addresses of connected devices::

    i2cdetect -y 1


For MPR121 being able to access the I2C bus, you need to have a Python smbus
implementation installed. Use ``python-smbus`` from the distro or smbus2_
(``apt-get install python-smbus`` or ``pip install smbus2``).

Using MPR121
~~~~~~~~~~~~

Attach the MPR121 to the Pi and use it like::

    from piripherals import MPR121

    mpr = MPR121(irq=4) # MPR121 should be up and running with 12 channels
    for i in range(12):
        mpr.on_touch(i, lambda *x: print(x)) # print status on touch and release

Use the ``mpr121-dump`` script to examine the MPR121's response and to tune
the settings.

.. _datasheet: https://www.sparkfun.com/datasheets/Components/MPR121.pdf
.. _BCM: https://pinout.xyz/
.. _Raspbian: https://www.raspberrypi.org/downloads/raspbian/
.. _RPi.GPIO: https://pypi.python.org/pypi/RPi.GPIO
.. _smbus2: https://pypi.python.org/pypi/smbus2
.. _Adafruit.MPR121: https://github.com/adafruit/Adafruit_Python_MPR121
"""

# http://python-future.org/compatible_idioms.html
from __future__ import print_function
from __future__ import division

__all__ = ['MPR121']

from functools import partial
from time import sleep
from threading import Thread, Event

NCH = 13  # number of channels
# REGISTERS
ETS = 0x00  # touch status
OOR = 0x02  # out of range status
EFD = 0x04  # electrode filtered data
EBL = 0x1e  # baseline value
MHD = 0x2b  # MHD rising
MHDX = 0x36  # MHD rising proximity
TTH = 0x41  # touch threshold 0
RTH = 0x42  # release threshold 0
DEB = 0x5b  # debounce
AFE1 = 0x5c  # parameters 1
AFE2 = 0x5d  # parameters 2
ECR = 0x5e  # electrode control register
CDC = 0x5f  # electrode current
CDT = 0x6c  # charge time
GPIO_CTL0 = 0x73  # GPIO control 0
GPIO_CTL1 = 0x74  # GPIO control 1
GPIO_DAT = 0x75  # GPIO data
GPIO_DIR = 0x76  # GPIO direction
GPIO_EN = 0x77  # GPIO enable
GPIO_SET = 0x78  # GPIO set data
GPIO_CLR = 0x79  # GPIO clear data
GPIO_TOG = 0x7a  # GPIO toggle data
ACNF_C0 = 0x7b  # auto config control 0
ACNF_C1 = 0x7c  # auto config control 1
ACNF_USL = 0x7d  # auto config
ACNF_LSL = 0x7e  # auto config
ACNF_TL = 0x7f  # auto config target level
SRESET = 0x80  # soft reset


def h(v):
    return '0x{:02x}'.format(v)


def b(v):
    return '{:08b}'.format(v)


def w(v):
    return '{:016b}'.format(v)


def not_raising(func):
    """Wraps a function and swallows exceptions.

    Args:
        func: function to wrap

    Returns:
        wrapped function, that does not raise Exceptions,
        Exceptions are printed to console_scripts
    """
    import traceback

    def logging_func(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            traceback.print_exc()

    return logging_func


class IRQHandler:
    """Abstraction of IRQ handler.

    An edge on the pin sets a flag.  The callback is invoked on a separate
    thread when the flag was set.  The flag is reset when the pin is high again.
    The callback may be invoked repeatedly if the pin does not reset.

    Args:
        pin (int): BCM# of pin attached to IRQ line.
        callback: function invoked on IRQ.
        edge (int): fire interrupt on falling=0 or rising=1 edge.
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
        callback = not_raising(callback)
        reset = GPIO.LOW if edge else GPIO.HIGH
        edge = GPIO.RISING if edge else GPIO.FALLING

        GPIO.setup(pin, GPIO.IN, pull_up_down=pud)
        GPIO.add_event_detect(pin, edge, lambda *x: self._irq.set())

        def loop():
            while True:
                self._irq.wait()
                callback()
                if GPIO.input(pin) == reset:
                    self._irq.clear()

        Thread(target=loop, daemon=True).start()


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

        Thread(target=loop, daemon=True).start()


noop = lambda *x: None


class MPR121:
    """MPR121 capacitive touch sensor and GPIO/LED controller.

    It will be configured with sane defaults and started immediately.

    Args:
        addr (int): I2C address of the device
        bus (int): I2C bus, 1 = /dev/i2c-1
        irq (int): GPIO BCM pin # that is connect to interrupt line,
            0=disbale IRQ, use polling
    """

    def __init__(self, addr=0x5a, bus=1, irq=0):
        from .bus import Bus
        self.addr = addr
        self.overcurrent = False
        self._bus = Bus(bus).device(addr)
        self._handlers = [noop] * NCH
        self._touched = 0

        def handle_touch():
            t0 = self._touched
            t1 = self._touched = self.touched()
            ch = t0 ^ t1
            if ch: self._handle_touch(t1, ch)

        if irq:
            IRQHandler(irq, handle_touch)
        else:
            Poller(handle_touch)

        self.setup()

    def _handle_touch(self, touched, changed):
        """Invokes touch handlers if touch status changed.

        Args:
            touched (int): byte containing touch status bits
                bit is 1 if channel is touched
            changed (int): byte containing status change bits
                bit is 1 if touch status has changed
        """

        for i in range(NCH):
            m = 1 << i
            if changed & m:
                try:
                    self._handlers[i]((touched & m) > 0, i)
                except TypeError:
                    self._handlers[i]((touched & m) > 0)

    def is_touched(self, channel):
        """Get touch status.

        Args:
            channel (int): channel to get status for, 0-12

        Returns:
            bool: True if touched
        """
        return (self._touched & (1 << channel)) > 0

    def on_touch(self, channel, handler):
        """Register touch handler, invoked on state change.

        Args:
            channel (int): channel to attach the handler to (0-12, 12=proximity)
            handler (callable(boolean, [channel])): handler,
                it gets passed a channel number [optional] and a boolean (True=touched),
                Pass None to remove any assigned handler.
        """
        self._handlers[channel] = not_raising(handler) or noop

    def reset(self):
        """Perform soft reset."""
        self._bus.write_byte(SRESET, 0x63)

    def configure(self, cl=3, prox=0, touch=0):
        """activate/deactivate measurement.

        Deactivate measurement with prox=0 and touch=0.

        Args:
            cl (int): calibration lock:
                0 = baseline tracking enabled,
                1 = baseline tracking disbled,
                2 = baseline tracking enabled, init 5MSBs with initial measurement,
                3 = baseline tracking enabled, init with initial measurement.
            prox (int): proximity detection:
                0 = disabled,
                1 = enabled on electrodes 0-1,
                2 = enabled on electrodes 0-3,
                3 = enabled on electrodes 0-11.
            touch (int): enable electrodes:
                0 = disabled,
                1 = enable electrode 0,
                2 = enable electrodes 0-1,
                3 = enable electrodes 0-2,
                ...,
                12 = enable electrodes 0-11.
        """
        self._bus.write_byte(ECR, (cl << 6) | (prox << 4) | touch)

    def touched(self):
        """Get touch status bits to the device.

        Returns:
            int: first 12 bits contain touch status, 1=touched

        Raises:
            Exception: on overcurrent
        """
        word = self._bus.read_word(ETS)
        overcurrent = (word & (1 << 15)) > 0
        if overcurrent:
            raise Exception('overcurrent')
        self.out_of_range()
        return word & 0x0fff

    def electrode_data(self):
        """Get raw eletrode measurement data.

        Returns:
            list of int: raw 10 bit eletrode measurement per eletrode
        """
        bytes = self._bus.read_block(EFD, 2 * NCH)
        data = []
        for i in range(NCH):
            data.append((bytes[2 * i + 1] << 8) + bytes[2 * i])
        return data

    def baseline(self, rft=-1, mhd=0, nhd=0, ncl=0, fdl=0, prox=0):
        """Get raw baslines or configure baseline tracking.

        Args:
            rft (int): scenario to set the values for:
                0 = rising, raw eletrode data > current baseline,
                1 = falling, raw eletrode data < current baseline,
                2 = touched, eletrode in touch status.
            mhd (int): max. half delta 0-63 (for rft=0 or 1 only),
                largest magnitude of variation to pass through the baseline filter.
            nhd (int): noise half delta 0-63,
                incremental change when non-noise drift is detected.
            ncl (int): noise count limit 0-255,
                number of samples consecutively greater than mhd necessary
                before if can be determined that it is non-noise.
            fdl (int): filter delay count limit 0-255,
                rate of operation of the filer, greater values makes it operate slower.
            prox (bool): if True set values for proximity mode.

        Returns:
            list of ints: raw 10 bit baseline values per eletrode, if invoked with no args.
        """
        if rft < 0:
            return [b << 2 for b in self._bus.read_block(EBL, NCH)]
        else:
            reg = (MHDX if prox else MHD) + 4 * rft
            if rft > 1: self._bus.write_block(reg, [nhd, ncl, fdl])
            else: self._bus.write_block(reg, [mhd, nhd, ncl, fdl])

    def threshold(self, touch, release=-1, channel=-1):
        """Set touch and release thresholds.

        Usually touch > release for hysteresis.

        Args:
            touch (int): touch threshold 0-255
            release (int): release threshold 0-255
                if ommited release=0.6*touch
            channel (int): channel to set thresholds for 0-12 (12=proximity)
                if ommited apply thresholds to all channels
        """
        if release < 0:
            release = int(0.6 * touch)
        if channel < 0:
            for i in range(NCH):
                self.threshold(touch, release, i)
        else:
            self._bus.write_byte(TTH + 2 * channel, touch)
            self._bus.write_byte(RTH + 2 * channel, release)

    def debounce(self, touch=0, release=-1):
        """Configure debouncing.

        # of consecutiv measurements with same result needed to trigger state change.

        Args:
            touch (int): for touch 0-7
            release (int): for release 0-7, if ommited release=touch
        """
        if release < 0: release = touch
        self._bus.write_byte(DEB, (release << 4) | touch)

    def filter(self, cdc=16, cdt=1, ffi=0, sfi=0, esi=4):
        """Settings for global eletrode charging, sampling and filtering.

        Effective measurement cycle period is sfi*esi.

        Args:
            cdc (int): charge-discharge-current 0-63 (uA)
            cdt (int): charge-discharge-time 0-7 (0.5*2**(cdt-1) us)
            ffi (int): first filter iterations 0-3 (6,10,18,34)
            sfi (int): second filter iterations 0-3 (4,6,10,18)
            esi (int): eletrode sample interval 0-7 (2**esi ms)
        """
        lb = (ffi << 6) | cdc
        hb = (cdt << 5) | (sfi << 3) | esi
        self._bus.write_word(AFE1, (hb << 8) | lb)

    def charge(self, channel, current=0, time=0):
        """Configure change current and time per channel.

        These values are determined automatically when auto_config is activated.

        Args:
            channel (int): channel to configure 0-11
            current (int): charge current
        """
        self._bus.write_byte(CDC + channel, current)
        reg = CDT + channel // 2
        s = 4 * (channel % 2)
        self._bus.write_byte(
            reg, (self._bus.read_byte(reg) & ~(0xf << s)) | (time << s))

    def auto_config(self,
                    ace=1,
                    are=1,
                    bva=3,
                    retry=2,
                    afes=1,
                    scts=0,
                    acfie=1,
                    arfie=1,
                    oorie=1,
                    usl=200,
                    lsl=130,
                    tl=180):
        """Configure automatic adjustment eletrode change current and time.

        Args:
            ace (bool): enable auto configuration
            are (bool): enable auto reconfiguration
            bva (int): baseline adjustment after current and time have been set:
                0 = no change,
                1 = set to zero,
                2 = set 5MSBs to measured value,
                3 = set to measured value.
            retry (int): # of retries for auto configuration: 0-3 (0,2,4,8)
            afes (int): # of AFE sample during search process, set to values
                as filter(ffi): 0-3 (6,10,18,34)
            scts (bool): skip charge time search
            acfie (bool): enable IRQ on auto config failure
            arfie (bool): enable IRQ on auto reconfig failure
            oorie (bool): enable IRQ on out of range event
        """
        lb = (afes & 0b11 << 6) | (retry & 0b11 << 4) | (bva & 0b11 << 2) | (
            are & 0b1 << 1) | ace & 0b1
        hb = (scts & 0b1 << 7) | (oorie & 0b1 << 2) | (
            arfie & 0b1 << 1) | acfie & 0b1
        self._bus.write_word(ACNF_C0, (hb << 8) + lb)
        self._bus.write_byte(ACNF_USL, usl)
        self._bus.write_byte(ACNF_LSL, lsl)
        self._bus.write_byte(ACNF_TL, tl)

    def out_of_range(self):
        """get out of range status.

        Returns:
            int: first 12 bits contain oor status.

        Raises:
            Exception: if auto (re)config has failed
        """
        word = self._bus.read_word(OOR)
        auto_config_failed = (word & (1 << 15)) > 0
        if auto_config_failed:
            raise Exception('auto config failed')
        auto_reconfig_failed = (word & (1 << 14)) > 0
        if auto_reconfig_failed:
            raise Exception('auto reconfig failed')
        return word & 0x0fff

    def gpio_setup(self, channel, output, mode=0, enable=1):
        """Setup GPIO configuration.

        Args:
            channel (int): channel to configure (4-11)
            output (bool): configure as 1=output or 0=input
            mode (int): pin mode, when output:
                0 = CMOS output,
                2 = open drain output, low side MOS only,
                3 = open drain output, high side MOS only,
                when input:
                0 = input,
                2 = input with pull-down,
                3 = input with pull-up.
            enable (bool): enable/disbale GPIO functionality
        """
        assert 4 <= channel <= 11
        if mode == 1: mode = 0
        channel -= 4

        def set_bit(addr, bit, value):
            print('0x{:02x}={:08b}'.format(addr, (
                self._bus.read_byte(addr) & ~(1 << bit)) |
                                           ((1 if value else 0) << bit)))
            self._bus.write_byte(addr,
                                 (self._bus.read_byte(addr) & ~(1 << bit)) |
                                 ((1 if value else 0) << bit))

        set_bit(GPIO_CTL0, channel, mode & 0b10)
        set_bit(GPIO_CTL1, channel, mode & 0b01)
        set_bit(GPIO_DIR, channel, output & 0b1)
        set_bit(GPIO_EN, channel, enable & 0b1)

    def gpio_status(self):
        """Get GPIO status bits.

        Returns:
            GPIO status byte for channels 4-11
        """
        return self._bus.read_byte(GPIO_DAT)

    def gpio_set(self, channel, value):
        """Set GPIO channel.

        Args:
            channel (int): channel to set 4-11
            value (bool): set 1=HIGH or 0=LOW
        """
        assert 4 <= channel <= 11
        self._bus.write_byte(GPIO_SET
                             if value else GPIO_CLR, 1 << (channel - 4))

    def dump(self, regs=1, up=1, loop=1):
        """Dump raw values, baseline and touch status to console.

        Uses this repeatedly to adjust the configuration.

        Args:
            regs (bool): dump register values
            up (bool): move cursor up after dump
            loop (int): run in loop for given # of rounds
        """
        import sys

        tth, rth = [], []
        for i in range(NCH):
            tth.append(self._bus.read_byte(TTH + 2 * i))
            rth.append(self._bus.read_byte(RTH + 2 * i))

        for q in range(loop):
            cols = 4
            fs = '{}0x{:02x} = 0x{:02x} b{:08b} {:3d}\033[0m    ' * cols
            if regs:
                data = []
                for i in range(cols):
                    data += self._bus.read_block(32 * i, 32)
                for j in range(32):
                    x = []
                    for i in range(cols):
                        k = j + 32 * i
                        c = '\033[33m' if data[k] else ''
                        x += (c, k, data[k], data[k], data[k])
                    print(fs.format(*x))

            print(' E:  raw base diff (touched) [GPIO]' + ' ' * 73 +
                  '  cdc     cdt oor')
            n = 80
            ts = self.touched()
            gp = self.gpio_status()
            ed = self.electrode_data()
            bl = self.baseline()
            oo = self.out_of_range()
            for i in range(NCH):
                e = int(n * ed[i] / 0x3ff)
                b = int(n * bl[i] / 0x3ff)
                bar = ['='] * e + ['-'] * (n - e)
                bar[b] = '\033[0m|\033[34m'
                nt = max(0, b - int(n * tth[i] / 255))
                nr = max(0, b - int(n * rth[i] / 255))
                bar[nt] = '\033[33m' + bar[nt]
                bar[nr] = '\033[32m' + bar[nr]
                t = '1' if (ts & (1 << i)) else '0'
                g = '-' if i < 4 or i > 11 else '1' if (gp &
                                                        (1 <<
                                                         (i - 4))) > 0 else '0'
                cdc = self._bus.read_byte(CDC + i)
                s = 4 * (i % 2)
                cdt = (self._bus.read_byte(CDT + i // 2) >> s) & 0x0f
                o = '1' if (oo & (1 << i)) else '0'
                print(
                    '{:2d}: {:4d} {:4d} {:4d} ({}) [{}] \033[31m{}\033[0m {:3d}uA {:5.1f}us  {}   '.
                    format(i, ed[i], bl[i], ed[i] - bl[i], t, g, ''.join(bar),
                           cdc, (0.5 * 2**(cdt - 1)), o))
            if up:  # move cursor up
                sys.stdout.write('\033[F' * ((regs * 32) + NCH + 1))

    def setup(self, reset=1, channels=12, prox=0, threshold=50, debounce=2):
        """Configure the device with sane defaults.

        Args:
            reset (bool): perform soft reset
            channels (int): number of channels to activate 0-12
            threshold (int): touch threshold 0-255
            debounce (int): debounce count 0-7
        """
        if reset:
            self.reset()
        self.configure()
        self.filter(cdc=16, cdt=1, ffi=1, sfi=1, esi=0)
        self.auto_config()
        self.threshold(touch=threshold)
        self.threshold(channel=12, touch=10)
        self.debounce(debounce)
        for i in range(2):
            self.baseline(rft=i, mhd=5, nhd=1, ncl=3, fdl=10)
            self.baseline(rft=i, mhd=1, nhd=1, ncl=3, fdl=10, prox=1)
        self.configure(touch=channels, prox=prox)


if __name__ == '__main__': main()


def main():
    m = MPR121()
    m.dump(0, 1, 1000000)