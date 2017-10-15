# piripherals

a collection of classes to interact with peripherals for the RaspberryPi


## Installation

```
pip install piripherals
```

## Dependencies

This package has some soft dependencies. If you need them, depends on which
classes you actually use.

- [rpi_ws281x](https://pypi.python.org/pypi/rpi_ws281x)
- [RPi.GPIO](https://pypi.python.org/pypi/RPi.GPIO)
- [smbus2](https://pypi.python.org/pypi/smbus2), but other smbus implementations like Raspbians `python-smbus` may work, too
- [python-mpd2](https://pypi.python.org/pypi/python-mpd2)

## Documentation

Generate it with Sphinx (`cd docs && make html`) or [read it online](https://quantenschaum.github.io/piripherals/).
