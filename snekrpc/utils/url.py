import posixpath

try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

DEFAULT_SCHEME = 'tcp'
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 12321

def format_addr(addr):
    return '{}:{}'.format(*addr)

class Url(object):
    def __init__(self, url):
        if isinstance(url, Url):
            self.__dict__ = url.__dict__
            return

        if ':/' not in url:
            url = '{}://{}'.format(DEFAULT_SCHEME, url)

        u = urlparse(url)

        self._scheme = u.scheme

        if self._scheme == 'unix':
            self._host = None
            self._port = None
            self._path = posixpath.join(
                u.hostname or posixpath.sep,
                u.path.lstrip(posixpath.sep)).rstrip(posixpath.sep)
            self._address = self._netloc = self._path
        else:
            if u.path.strip(posixpath.sep):
                raise ValueError('invalid URL: {}'.format(url))
            self._host = (u.hostname or DEFAULT_HOST).replace('*', '0.0.0.0')
            self._port = u.port or DEFAULT_PORT
            self._path = None
            self._address = (self._host, self._port)
            self._netloc = format_addr(self._address)

    @property
    def scheme(self):
        return self._scheme

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def path(self):
        return self._path

    @property
    def address(self):
        return self._address

    @property
    def netloc(self):
        return self._netloc

    def __eq__(self, other):
        return str(self) == str(other)

    def __str__(self):
        return '{}://{}'.format(self.scheme, self.netloc)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, str(self))
