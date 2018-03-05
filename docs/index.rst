piripherals' documentation
==========================

Version |release|

This library is intended to be used on the RaspberryPi primarily, but it also works on other
platforms. The things, that are related to the hardware of the Pi, will not work on other
devices, of course.

.. attention::

  This is still in the beginning and work in progress! Many things will change!

.. note::

  This is a **Python 3 only** library! - https://pythonclock.org/

Installation
------------

Install piripherals from `PyPI`_ with pip::

  pip install piripherals

Dependencies
------------

This package has some `soft` dependencies. If you need them, depends on which
partes of this library you actually want to use.

- ``rpi_ws281x`` https://pypi.python.org/pypi/rpi_ws281x
- ``RPi.GPIO`` https://pypi.python.org/pypi/RPi.GPIO
- ``smbus2`` https://pypi.python.org/pypi/smbus2, but other smbus implementations like Raspbians ``python-smbus`` may work, too
- ``python-mpd2`` https://pypi.python.org/pypi/python-mpd2

.. _GitHub: https://github.com/quantenschaum/piripherals/
.. _PyPI: https://pypi.python.org/pypi/piripherals

Modules
=======

.. toctree::
   :maxdepth: 1

   piripherals.bus
   piripherals.button
   piripherals.event
   piripherals.led
   piripherals.mpd
   piripherals.mpr121
   piripherals.util


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
