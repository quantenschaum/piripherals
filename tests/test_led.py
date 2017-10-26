import pytest
from unittest.mock import Mock, patch, call
from time import sleep
from piripherals import NeoPixels
from piripherals.util import noop

T = 1


@pytest.fixture
def np():
    with patch('piripherals.led.PixelStrip', create=1) as strip:
        s = strip()
        s.numPixels.side_effect = lambda: strip.call_args[0][0]

        def brightness():
            try:
                return s.setBrightness.call_args[0][0]
            except:
                return 128

        s.getBrightness.side_effect = brightness
        color_data = [0] * 3

        def set_color(i, r, g, b):
            color_data[i] = (r << 16) | (g << 8) | b

        strip().setPixelColorRGB.side_effect = set_color
        strip().color_data = color_data
        return NeoPixels(3, 12)


def test_neopixels_color_and_brightness(np):
    strip = np._strip
    np.brightness(1)
    np.color(None, 0.1, 0.2, 0.3)
    assert strip.mock_calls == [call.begin(),
                                call.show(),
                                call.setBrightness(255),
                                call.show(),
                                call.numPixels(),
                                call.setPixelColorRGB(0, 25, 51, 76),
                                call.setPixelColorRGB(1, 25, 51, 76),
                                call.setPixelColorRGB(2, 25, 51, 76),
                                call.show()]


def test_neopixels_color_and_brightness_no_auto(np):
    strip = np._strip
    np.auto_show = 0
    np.brightness(1)
    np.color(None, 0.1, 0.2, 0.3)
    assert strip.mock_calls == [call.begin(),
                                call.show(),
                                call.setBrightness(255),
                                call.numPixels(),
                                call.setPixelColorRGB(0, 25, 51, 76),
                                call.setPixelColorRGB(1, 25, 51, 76),
                                call.setPixelColorRGB(2, 25, 51, 76)]


def test_neopixels_color(np):
    strip = np._strip
    np.auto_show = 0

    np.color(0, 0)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(0, 0, 0, 0)

    np.color(1, 0.2)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(1, 51, 51, 51)

    np.color(2, 0.1, 0.2)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(2, 25, 51, 51)

    np.color(0, 0.1, 0.2, 0.3)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(0, 25, 51, 76)

    np.color(1, 0.4, 0.5, 0.6, 0.7)
    assert strip.mock_calls[-2] == call.setBrightness(178)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(1, 102, 127, 153)

    np.color(-1, 1)
    assert strip.mock_calls[-1] == call.setPixelColorRGB(2, 255, 255, 255)


@pytest.mark.xfail(strict=1)
def test_neopixels_deadlock(np):
    np.animate(noop, timeout=0, wait=1)


def test_animation_error(np):
    strip = np._strip
    f = Mock(side_effect=Exception, unsafe=1)
    np.animate(f, period=T, timeout=T, wait=1, atexit=noop)
    f.assert_called_once()
    assert strip.show.call_count == 1

    # see if animation thread survived the exception
    f = Mock(unsafe=1)
    np.animate(f, period=T, timeout=T, wait=1)
    f.assert_called()
    assert strip.show.call_count > 5


def assert_colors(act, exp, tol=0):
    assert len(act) == len(exp)
    for i in range(len(exp)):
        a = act[i][0]
        e = exp[i]
        assert a[0] == e[0]
        assert abs(a[1] - e[1]) <= tol
        assert abs(a[2] - e[2]) <= tol
        assert abs(a[3] - e[3]) <= tol


def assert_brightness(act, exp, tol=0):
    assert len(act) == len(exp)
    for i in range(len(exp)):
        assert abs(act[i][0][0] - exp[i]) <= tol


def test_neopixels_raibow(np):
    strip = np._strip
    np.rainbow(period=T, timeout=T, delay=T / 6, wait=1)
    assert strip.color_data == [0] * 3
    assert strip.setPixelColorRGB.call_count == 7 * 3
    assert strip.show.call_count == 8
    strip.setBrightness.assert_called_once_with(255)
    assert_colors(strip.setPixelColorRGB.call_args_list,
                  [(0, 254, 0, 0), (1, 0, 254, 0), (2, 0, 0, 254),
                   (0, 126, 0, 128), (1, 128, 126, 0), (2, 0, 128, 126),
                   (0, 0, 1, 253), (1, 253, 0, 1), (2, 1, 253, 0),
                   (0, 0, 128, 126), (1, 126, 0, 128), (2, 128, 126, 0),
                   (0, 2, 252, 0), (1, 0, 2, 252), (2, 252, 0, 2),
                   (0, 130, 124, 0), (1, 0, 130, 124), (2, 124, 0, 130),
                   (0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)],
                  tol=10)


def test_neopixels_raibow_fade(np):
    strip = np._strip
    np.rainbow(period=T, fade=T, delay=T / 6, wait=1)
    assert strip.color_data == [0] * 3
    assert strip.setPixelColorRGB.call_count == 7 * 3
    assert strip.show.call_count == 8
    assert strip.setBrightness.call_count == 7
    strip.setBrightness.assert_called_with(255)
    assert_colors(strip.setPixelColorRGB.call_args_list,
                  [(0, 254, 0, 0), (1, 0, 254, 0), (2, 0, 0, 254),
                   (0, 126, 0, 128), (1, 128, 126, 0), (2, 0, 128, 126),
                   (0, 0, 1, 253), (1, 253, 0, 1), (2, 1, 253, 0),
                   (0, 0, 128, 126), (1, 126, 0, 128), (2, 128, 126, 0),
                   (0, 2, 252, 0), (1, 0, 2, 252), (2, 252, 0, 2),
                   (0, 130, 124, 0), (1, 0, 130, 124), (2, 124, 0, 130),
                   (0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)],
                  tol=10)


def test_breathe(np):
    strip = np._strip
    np.breathe(color=[1], fade=3 * T, period=T, wait=1, delay=T / 6)
    assert_colors(strip.setPixelColorRGB.call_args_list,
                  [(0, 255, 255, 255), (1, 255, 255, 255), (2, 255, 255, 255),
                   (0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)])
    assert_brightness(strip.setBrightness.call_args_list, [
                      0, 0, 12, 62, 106, 53, 8, 0, 8, 39, 63, 29, 9,
                      0, 7, 31, 41, 14, 1, 255], tol=10)


def test_blink(np):
    strip = np._strip
    np.blink('1 0.3 1 0', cycles=2, period=T, wait=1, delay=T / 4)
    assert_colors(strip.setPixelColorRGB.call_args_list,
                  [(0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)])
    assert_brightness(strip.setBrightness.call_args_list, [
        0, 255, 76, 255, 0, 255, 76, 255, 0, 255])


def test_sequence(np):
    strip = np._strip
    np.sequence(period=T, cycles=1, wait=1, delay=T / 6)
    assert_colors(strip.setPixelColorRGB.call_args_list,
                  [(0, 255, 0, 0), (0, 127, 127, 0), (0, 0, 255, 0),
                   (0, 0, 127, 127), (0, 0, 0, 255), (0, 127, 0, 127),
                   (0, 0, 0, 0), (1, 0, 0, 0), (2, 0, 0, 0)])
    assert_brightness(strip.setBrightness.call_args_list, [255])
