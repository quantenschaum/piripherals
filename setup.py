from setuptools import setup, find_packages

# http://setuptools.readthedocs.io/en/latest/setuptools.html
setup(
    name="piripherals",
    version="0.1",
    packages=find_packages(),
    #install_requires=['rpi_ws281x'],
    #dependency_links=['foo' ],
    python_requires='>=3',
    extras_require={
        'LED': ["rpi_ws281x"],
        'GPIO': ['RPi.GPIO'],
        'I2C': ['smbus2'],
    },
    author="quantenschaum",
    author_email="software@louisenhof2.de",
    description=
    "a collection of classes to interact with peripherals for the RaspberryPi",
    license="GPL-3.0",
    url="https://github.com/quantenschaum/piripherals",
    entry_points={
        'console_scripts': ['mpr121-dump = piripherals.mpr121:main']
    })
