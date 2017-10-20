import pytest
from piripherals import MPD
from unittest.mock import Mock, MagicMock
from piripherals.util import noop
from io import StringIO as sio


_data = []
_rwfile = Mock()


def patch_mock(m):
    global _rwfile
    c = m._mpd
    connect = c._connect_tcp = Mock()
    sock = connect()
    _rwfile = sock.makefile()
    _send('OK MPD 1.2.3\n')


def _send(*x):
    'what shoud send to the client'
    _rwfile.readline.side_effect = x


def _receive(*a, **k):
    'what MPD should recieve from the client'
    _rwfile.write.assert_called_with(*a, **k)


def patch_record(m):
    global _send, _receive, _data
    _send = _receive = noop
    _data = []

    c = m._mpd

    r = c._rfile.readline

    def readline():
        line = r()
        _data.append('< ' + line)
        return line

    c._rfile.readline = readline

    w = c._wfile.write

    def write(x):
        _data.append('> ' + x)
        w(x)

    c._wfile.write = write


@pytest.fixture()
def mpd():
    try:
        m = MPD()
        m.connect('localhost', 6600)
        patch_record(m)
        yield m
        m.disconnect()
    except:  # if connection to a real MPD fails, use mocked protocol replies
        m = MPD()
        patch_mock(m)
        m.connect('localhost', 6600)
        yield m
    finally:
        print(_rwfile.mock_calls)
        for x in _data:
            print(repr(x))


OK = 'OK\n'


def test_mpd_connect(mpd):
    assert mpd.timeout < 10
    _send(OK)
    mpd.status()
    mpd._mpd.disconnect()
    _send('OK MPD foo\n', OK)
    mpd.status()  # fails if it did not reconnect automatically
    _rwfile.write.side_effect = [ConnectionError] + [None] * 10
    _send('OK MPD foo\n',  OK)
    mpd.status()  # fails if it did not reconnect automatically
    _send(ConnectionError, 'OK MPD foo\n', OK)
    mpd.status()  # fails if it did not reconnect automatically


@pytest.mark.xfail(strict=1)
def test_mpd_disconnect(mpd):
    mpd.disconnect()
    mpd.status()  # must fail, because it's disconnected


def test_volume(mpd):
    _send('volume: 10\n', OK)
    v = mpd.volume()
    assert 0 <= v <= 100
    _receive('status\n')

    _send(OK)
    mpd.volume(42)
    _receive('setvol "42"\n')

    _send('volume: 42\n', OK)
    assert mpd.volume() == 42
    _receive('status\n')

    _send('volume: 42\n', OK, OK)
    mpd.volume('+3')
    _receive('setvol "45"\n')

    _send('volume: 45\n', OK)
    assert mpd.volume() == 42 + 3
    _receive('status\n')

    _send('volume: 45\n', OK, OK)
    mpd.volume('-7')
    _receive('setvol "38"\n')

    _send('volume: 38\n', OK)
    assert mpd.volume() == 42 + 3 - 7
    _receive('status\n')


def test_toggle_play(mpd):
    _send(OK)
    mpd.clear()
    _receive('clear\n')

    _send(OK)
    mpd.add('http://89.16.185.174:8003/stream')
    _receive('add "http://89.16.185.174:8003/stream"\n')

    _send('state: stop\n', OK)
    assert mpd.state() == 'stop'
    _receive('status\n')

    _send('state: stop\n', OK, OK)
    mpd.toggle_play()
    _receive('play\n')

    _send('state: play\n', OK)
    assert mpd.state() == 'play'
    _receive('status\n')

    _send('state: play\n', OK, OK)
    mpd.toggle_play()
    _receive('pause\n')

    _send('state: pause\n', OK)
    assert mpd.state() == 'pause'
    _receive('status\n')

    _send('state: pause\n', OK, OK)
    mpd.toggle_play()
    _receive('pause\n')

    _send('state: play\n', OK)
    assert mpd.state() == 'play'
    _receive('status\n')

    _send(OK)
    mpd.stop()
    _receive('stop\n')

    _send('state: stop\n', OK)
    assert mpd.state() == 'stop'
    _receive('status\n')


def test_save_playlist(mpd):
    pl = '#foo#'

    _send('ACK [50@0] {rm} No such playlist\n', OK)
    mpd.save_playlist(pl)
    _receive('save "' + pl + '"\n')

    _send(OK, OK)
    mpd.save_playlist(pl)
    _receive('save "' + pl + '"\n')

    _send('playlist: #foo#\n', OK)
    assert mpd.has_playlist(pl)
    _receive('listplaylists\n')

    _send(OK)
    mpd.del_playlist(pl)
    _receive('rm "' + pl + '"\n')

    _send(OK)
    assert not mpd.has_playlist(pl)
    _receive('listplaylists\n')


def test_load_playlist(mpd):
    pl = '#bar#'

    _send(OK)
    mpd.clear()
    _receive('clear\n')

    _send(OK)
    mpd.add('http://foo')
    _receive('add "http://foo"\n')

    _send(OK)
    mpd.add('http://bar')
    _receive('add "http://bar"\n')

    _send(OK, OK)
    mpd.save_playlist(pl)
    _receive('save "' + pl + '"\n')

    _send(OK)
    mpd.clear()
    _receive('clear\n')

    _send(OK)
    assert not mpd.playlist()
    _receive('playlist\n')

    _send('playlist: #bar#\n', OK, OK, OK)
    mpd.load_playlist(pl)
    _receive('load "' + pl + '"\n')

    _send('0:file: http://foo\n', '1:file: http://bar\n', OK)
    p = mpd.playlist()
    assert len(p) == 2
    _receive('playlist\n')

    _send(OK)
    mpd.del_playlist(pl)
    _receive('rm "' + pl + '"\n')
