import pytest
from piripherals import MPD


@pytest.fixture()
def mpd():
    try:
        m = MPD()
        m.connect('localhost', 6600)
        return m
    except:
        pytest.skip('no MPD connection')


def disconnect(mpd):
    'disconnect internal instance, simulates connection failure'
    mpd._mpd.disconnect()


def test_mpd_connect(mpd):
    mpd.status()
    disconnect(mpd)
    mpd.status()  # fails if it does not reconnect automatically
    assert mpd.timeout < 10


@pytest.mark.xfail(strict=1)
def test_mpd_disconnect(mpd):
    mpd.disconnect()
    mpd.status()


def test_volume(mpd):
    v = mpd.volume()
    assert 0 <= v <= 100
    mpd.volume(42)
    assert mpd.volume() == 42
    mpd.volume('+3')
    assert mpd.volume() == 42 + 3
    mpd.volume('-7')
    assert mpd.volume() == 42 + 3 - 7


def test_state(mpd):
    assert mpd.state() in ['stop', 'play', 'pause']


def test_toggle_play(mpd):
    mpd.stop()
    mpd.add('http://foo')
    assert mpd.state() == 'stop'
    mpd.toggle_play()
    assert mpd.state() == 'play'
    mpd.toggle_play()
    assert mpd.state() == 'pause'
    mpd.toggle_play()
    assert mpd.state() == 'play'
    mpd.stop()
    assert mpd.state() == 'stop'


def test_save_playlist(mpd):
    pl = '#foo#'
    mpd.save_playlist(pl)
    mpd.save_playlist(pl)
    assert mpd.has_playlist(pl)
    mpd.del_playlist(pl)
    assert not mpd.has_playlist(pl)


def test_load_playlist(mpd):
    pl = '#bar#'
    mpd.clear()
    mpd.add('http://foo')
    mpd.add('http://bar')
    mpd.save_playlist(pl)
    mpd.clear()
    assert not mpd.playlist()
    mpd.load_playlist(pl)
    p = mpd.playlist()
    assert len(p) == 2
    mpd.del_playlist(pl)
