import pytest
from unittest.mock import Mock
from time import sleep, monotonic

from piripherals.button import *

T = 0.01  # base time unit
D = 3 * T
H = 10 * T
R = 5 * T


@pytest.fixture
def btn():
    # slow things down for testing
    global clicked, held, button
    clicked, held = Mock(), Mock()
    button = ClickButton(click_time=T, double_click_time=D,
                         hold_time=H, hold_repeat=R,
                         when_clicked=clicked, when_held=held)
    yield button
    print(clicked.mock_calls)
    print(held.mock_calls)


def test_debounce(btn):
    "test debouncing, up/down needs stable input, no clicks are fired"
    # debouncing spurious DOWN
    btn.press()
    assert btn.is_down()
    sleep(T / 2)
    btn.release()  # release quickly
    assert btn.is_down()
    sleep(T)
    btn.release()
    assert btn.is_up()
    sleep(T)

    # debouncing spurious UP
    btn.press()
    assert btn.is_down()
    sleep(T / 2)
    btn.release()  # release, but only short ...
    assert btn.is_down()
    sleep(T / 2)
    btn.press()  # down again
    assert btn.is_down()
    sleep(T)
    btn.release()
    assert btn.is_up()

    # quick UPs and DOWNs
    for i in range(10):
        btn(1)
        assert btn.is_up()
        sleep(T / 2)
        btn(0)
        assert btn.is_up()
        sleep(T / 2)

    # no clicks ro hold detected
    clicked.assert_not_called()
    held.assert_not_called()


def test_single_click(btn):
    btn.press()
    assert btn.is_down()
    sleep(T)
    btn.release()
    assert btn.is_up()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(T)
    btn.release()
    assert btn.is_up()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(T)
    btn.release()
    assert btn.is_up()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(T)
    btn.release()
    assert btn.is_up()
    clicked.assert_called_once_with(1)
    held.assert_not_called()


def test_double_click(btn):
    btn.press()
    assert btn.is_down()
    sleep(T)
    btn.release()
    assert btn.is_up()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(T)
    btn.press()  # again
    assert btn.is_down()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(T)
    btn.release()  # again
    assert btn.is_up()
    clicked.assert_not_called()  # should be counted but not yet fired
    sleep(D)
    btn.release()
    assert btn.is_up()
    clicked.assert_called_once_with(2)
    held.assert_not_called()


def test_hold(btn):
    btn.press()
    assert btn.is_down()
    held.assert_not_called()
    sleep(H)
    btn.press()
    assert btn.is_down()
    sleep(T)
    btn.release()
    assert btn.is_up()
    sleep(D)
    btn.release()
    assert btn.is_up()
    held.assert_called_once_with(0)
    clicked.assert_not_called()


def test_hold_repeat(btn):
    btn.press()
    assert btn.is_down()
    held.assert_not_called()
    sleep(H)
    btn.press()
    assert btn.is_down()
    held.assert_called_once_with(0)
    sleep(T)
    btn.press()
    assert btn.is_down()
    held.assert_called_with(0)
    sleep(R - T)
    btn.press()
    assert btn.is_down()
    held.assert_called_with(0)
    sleep(R)
    btn.press()
    assert btn.is_down()
    held.assert_called_with(0)
    assert held.call_count == 3
    clicked.assert_not_called()


def test_click_hold(btn):
    btn.press()
    assert btn.is_down()
    held.assert_not_called()
    sleep(T)
    btn.release()
    assert btn.is_up()
    sleep(D)
    btn.press()
    assert btn.is_down()
    sleep(H)
    btn.press()
    assert btn.is_down()
    held.assert_called_once_with(1)
    clicked.assert_not_called()
