class MPD(object):
    """Wrapper for MPDClient that adds

    - automatic reconnect on connection loss
      see https://github.com/Mic92/python-mpd2/issues/64
    - custom methods
    - volume limit
    """

    def __init__(self, maxvol=100, *args, **kwargs):
        from mpd import MPDClient
        self.__dict__['maxvol'] = maxvol
        self.__dict__['_mpd'] = MPDClient(*args, **kwargs)
        self.__dict__['_connect_args'] = None
        self.timeout = 5

    def __getattr__(self, name):
        import mpd
        a = self._mpd.__getattribute__(name)
        if not callable(a):
            return a

        def b(*args, **kwargs):
            try:
                if verbosity > 1:
                    debug(['try', name, args, kwargs])
                return a(*args, **kwargs)
            except (mpd.MPDConnectionError, ConnectionError) as e:
                cargs = self.__dict__['_connect_args']
                if not cargs:
                    raise
                if verbosity > 1:
                    exception(e)
                cargs, ckwargs = cargs
                self.connect(*cargs, **ckwargs)
                if verbosity > 1:
                    debug(['retry', name, args, kwargs])
                return a(*args, **kwargs)

        return b

    def __setattr__(self, name, value):
        self._mpd.__setattr__(name, value)

    def connect(self, *args, **kwargs):
        self.disconnect()
        self.__dict__['_connect_args'] = args, kwargs
        self._mpd.connect(*args, **kwargs)

    def disconnect(self):
        import mpd
        try:
            self.__dict__['_connect_args'] = None
            self._mpd.close()
            self._mpd.disconnect()
        except (mpd.MPDConnectionError, ConnectionError) as e:
            pass
        finally:
            self._mpd._reset()

    def volume(self, v=None):
        if v is not None:
            try:
                if v.startswith('+') or v.startswith('-'):
                    v = self.volume() + int(v)
            except:
                pass
            self.setvol(max(0, min(self.maxvol, v)))
        else:
            return int(self.status()['volume'])

    def state(self):
        return self.status()['state']

    def toggle_play(self):
        if self.state() == 'stop':
            self.play()
        else:
            self.pause()

    def save_playlist(self, name):
        self.del_playlist(name)
        self.save(name)

    def del_playlist(self, name):
        import mpd
        try:
            self.rm(name)
        except mpd.CommandError:
            pass

    def has_playlist(self, name):
        for i in self.listplaylists():
            if name == i['playlist']:
                return True
        return False

    def load_playlist(self, name):
        if self.has_playlist(name):
            self.clear()
            self.load(name)
