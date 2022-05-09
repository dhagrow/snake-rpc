from __future__ import absolute_import

import socket

from .. import logs
from .. import utils
from .. import param

from . import tcp

ACCEPT_TIMEOUT = 0.1

log = logs.get(__name__)

class UnixConnection(tcp.TcpConnection):
    log = log

class UnixTransport(tcp.TcpTransport):
    _name_ = 'unix'
    log = log
    Connection = UnixConnection

    @param('backlog', int, default=tcp.BACKLOG)
    @param('chunk_size', int, default=tcp.CHUNK_SIZE)
    def __init__(self, url, timeout=None, backlog=None, chunk_size=None):
        super(UnixTransport, self).__init__(url, timeout, backlog, chunk_size)
        self._path = self._url.path

    def connect(self, client):
        self._sock = s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(self.timeout)
        s.connect(self._path)
        return self.Connection(client, s, self._path, self.chunk_size)

    def bind(self):
        # remove existing socket
        utils.path.discard_file(self._path)

        self._sock = s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(ACCEPT_TIMEOUT)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(self._path)
        s.listen(self.backlog)

    def serve(self, server):
        try:
            super(UnixTransport, self).serve(server)
        finally:
            utils.path.discard_file(self._path)

    def handle(self, server, sock, addr):
        with self.Connection(server, sock, self._path, self.chunk_size) as con:
            server.handle(con)
