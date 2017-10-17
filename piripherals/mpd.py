class MPD(object):
    """Wrapper for MPDClient that adds

    - automatic reconnect on connection loss
      see https://github.com/Mic92/python-mpd2/issues/64
    - custom methods
    - volume limit
    - supports all methods of ``MPDClient``

    Args:
        maxvol (int): volume limit
        *: args for ``MPDClient``
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
                return a(*args, **kwargs)
            except (mpd.ConnectionError, ConnectionError) as e:
                cargs = self.__dict__['_connect_args']
                if not cargs:
                    raise
                cargs, ckwargs = cargs
                self.connect(*cargs, **ckwargs)
                return a(*args, **kwargs)

        return b

    def __setattr__(self, name, value):
        self._mpd.__setattr__(name, value)

    def connect(self, *args, **kwargs):
        """establish connection

        disconnects if already connected, host and port are stored,
        will reconnect automatically if connection is lost

        Args:
                host (str): hostname/ip/socket
                port (int): port, usually 6600
        """
        self.disconnect()
        self.__dict__['_connect_args'] = args, kwargs
        self._mpd.connect(*args, **kwargs)

    def disconnect(self):
        """disconnect, disables auto reconnect"""
        import mpd
        try:
            self.__dict__['_connect_args'] = None
            self._mpd.close()
            self._mpd.disconnect()
        except (mpd.ConnectionError, ConnectionError) as e:
            pass
        finally:
            self._mpd._reset()

    def volume(self, v=None):
        """adjust volume

        Args:
            v: int = absolute volume 0-100,
                str = absolute volume or relative volume change if prefixed
                with ``+`` or ``-``

        Return:
            int: volume if v was omitted
        """
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
        """current playback state

        Return:
            str: ``stop``, ``play``, ``pause``
        """
        return self.status()['state']

    def toggle_play(self):
        """play or pause

        - start playing if stopped or paused
        - pause if playing
        """
        if self.state() == 'stop':
            self.play()
        else:
            self.pause()

    def save_playlist(self, name):
        """save current playlist

        if playlist exists, it will be overwritten

        Args:
            name (str): name of the playlist
        """
        self.del_playlist(name)
        self.save(name)

    def del_playlist(self, name):
        """delete playlist

        if playlist exists, this does nothing

        Args:
            name (str): name of the playlist to delete
        """
        import mpd
        try:
            self.rm(name)
        except mpd.CommandError:
            pass

    def has_playlist(self, name):
        """check for playlist

        Args:
            name (str): name of the playlist to look for

        Return:
            bool: true if playlist exists
        """
        for i in self.listplaylists():
            if name == i['playlist']:
                return True
        return False

    def load_playlist(self, name):
        """load a playlist

        - replaces current playlist with the named playlist
        - if the given playlist does not exists, this does nothing

        Args:
            name (str): name of the playlist to load
        """
        if self.has_playlist(name):
            self.clear()
            self.load(name)
