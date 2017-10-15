"""Wrapper classes to abstract bus access."""

from functools import partial


class Bus:
    """Abstraction for a data bus, i.e. I2C."""

    def __init__(self, bus=1):
        try:
            from smbus import SMBus
        except:
            from smbus2 import SMBus

        bus = SMBus(bus)
        self.read_byte = bus.read_byte_data
        self.read_word = bus.read_word_data
        self.read_block = bus.read_i2c_block_data
        self.write_byte = bus.write_byte_data
        self.write_word = bus.write_word_data
        self.write_block = bus.write_i2c_block_data

    def read_byte(self, addr, reg):
        """read a byte.

        Args:
            addr (int): address of device to read the byte from
            reg (int): register to be read

        Returns:
            int: the byte, that was read
        """
        return 0

    def read_word(self, addr, reg):
        """read a word (2 bytes).

        Args:
            addr (int): address of device to read the word from
            reg (int): base register, low byte of the word is there,
                high byte is at reg+1

        Returns:
            int: the word, that was read
        """
        return 0

    def read_block(self, addr, reg, n):
        """read a block of bytes.

        Args:
            addr (int): address of device to read the block from
            reg (int): base register, first byte of the block
            n (int): # of bytes to read n<=32

        Returns:
            list of int: bytes, that were read
        """
        return [0] * n

    def write_byte(self, addr, reg, byte):
        """write a byte.

        Args:
            addr (int): address of device to write the byte to
            reg (int): register to write to
            byte (int): byte to be written
        """
        return

    def write_word(self, addr, reg, word):
        """write a word (2 bytes).

        Args:
            addr (int): address of device to write the word to
            reg (int): base register, low byte of the word is there,
                high byte is at reg+1
            word (int): word to be written
        """
        return

    def write_block(self, addr, reg, block):
        """write a block of bytes.

        Args:
            addr (int): address of device to write the block to
            reg (int): base register, first byte of the block
            block (list of int): bytes to be written, len(block)<=32
        """
        return

    def device(self, addr):
        """Get a Device.

        Args:
            addr (int): device address

        Returns:
            Device: device at given address
        """
        return Device(self, addr)


class Device:
    """Abstraction of a device on a bus.

    It has the same methods as Bus, but with the ``addr`` already set.

    Args:
        bus (Bus): the bus the Device is attached to
        addr (int): address of the device

    """

    def __init__(self, bus, addr):
        self.read_byte = partial(bus.read_byte, addr)
        self.read_word = partial(bus.read_word, addr)
        self.read_block = partial(bus.read_block, addr)
        self.write_byte = partial(bus.write_byte, addr)
        self.write_word = partial(bus.write_word, addr)
        self.write_block = partial(bus.write_block, addr)
