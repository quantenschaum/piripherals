"""Testing the MPR121

Testing a hardware device is hard. This test aims to test the MPR121 class, not
the actual hardware. It will test, whether the MPR121 class reads and writes
the right bits to the right registers.

A test with the actual hardware MPR121 can only happen interactively on the Pi
with the MPR121 connected.
"""

import pytest
from unittest.mock import Mock
from piripherals import MPR121
from piripherals.bus import Bus

HARDWARE = 0
ADDR = 0x5a

reg = None


@pytest.fixture
def bus():
    if HARDWARE:
        from smbus import SMBus
        b = SMBus(1)
        m = b = Mock(wraps=b)  # wrap in mock to record calls
    else:
        # use a mock i2c bus
        m = b = Mock(spec=['read_byte_data', 'write_byte_data'])
        reg = [0] * 129  # registers of the MPR121
        reg[0x5c] = 0x10  # defauts according to datasheet
        reg[0x5d] = 0x24

    def read(a, r): return reg[r]
    m.read_byte_data.side_effect = read

    def write(a, r, b): reg[r] = b & 0xff
    m.write_byte_data.side_effect = write

    b = Bus(b)
    yield b
    # print(m.mock_calls)
    if not HARDWARE:
        for i in range(len(reg)):
            if reg[i]:
                print('0x{0:02x} = 0x{1:02x} {1:08b}'.format(i, reg[i]))


def assert_reg(dev, non_zero_regs):
    for i in range(129):
        v = non_zero_regs.get(i)
        v = v if v else 0
        assert dev[i] == v, 'register 0x{:02x}'.format(i)


def test_mpr121_init_default(bus):
    # turn all initialization off, but reset --> MPR121 in default state
    mpr = MPR121(bus=bus, handlers=0, setup=0)

    dev = bus.device(0x5a)
    assert_reg(dev, {0x5c: 0x10})

    for i in range(129):
        if i == 0x5c:
            v = 0x10
        elif i == 0x5d:
            v = 0x24
        elif i == 0x80:
            v = 0x63  # reset
        else:
            v = 0
        assert dev.read_byte(i) == v, 'reg=0x{:02x}'.format(i)


def test_mpr121_configure(bus):
    mpr = MPR121(bus=bus, handlers=0, setup=0)
    mpr.configure()

    dev = bus.device(0x5a)
    for i in range(129):
        if i == 0x5c:
            v = 0x10
        elif i == 0x5d:
            v = 0x24
        elif i == 0x5e:
            v = 0x24
        elif i == 0x80:
            v = 0x63
        else:
            v = 0
        assert dev.read_byte(i) == v, 'reg=0x{:02x}'.format(i)
