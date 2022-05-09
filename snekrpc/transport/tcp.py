from __future__ import absolute_import

import io
import ssl
import errno
import socket
import struct
import threading

from .. import logs
from .. import utils
from .. import errors
from .. import param

from . import Connection, Transport

BACKLOG = socket.SOMAXCONN
CHUNK_SIZE = io.DEFAULT_BUFFER_SIZE
ACCEPT_TIMEOUT = 0.1

log = logs.get(__name__)

class TcpConnection(Connection):
    log = log

    def __init__(self, interface, sock, url, chunk_size=None):
        super(TcpConnection, self).__init__(interface, url)
        self._sock = sock
        self._chunk_size = chunk_size
        self.log.debug('connected: %s', self.url)

    def recv(self):
        return recv(self._sock, self._chunk_size)

    def send(self, data):
        try:
            return send(self._sock, data)
        except socket.error as e:
            raise errors.TransportError(e)

    def close(self):
        close(self._sock)
        self.log.debug('disconnected: %s', self.url)

class TcpTransport(Transport):
    _name_ = 'tcp'
    log = log
    Connection = TcpConnection

    @param('backlog', int, default=BACKLOG)
    @param('chunk_size', int, default=CHUNK_SIZE)
    @param('ssl_key', doc='server-side only')
    def __init__(self, url, timeout=None, backlog=None, chunk_size=None,
            ssl_cert=None, ssl_key=None):
        super(TcpTransport, self).__init__(url)
        url = self._url

        self._addr = (url.host, url.port)
        self._sock = None

        self.timeout = timeout
        self.backlog = backlog or BACKLOG
        self.chunk_size = chunk_size

        self._ssl_cert = ssl_cert
        self._ssl_key = ssl_key

        self._stop = threading.Event()
        self._stopped = threading.Event()

    def connect(self, client):
        s = socket.create_connection(self._addr, self.timeout)

        if self._ssl_cert:
            ctx = ssl.create_default_context()
            ctx.load_verify_locations(self._ssl_cert)
            hostname = socket.gethostbyaddr(self._addr[0])[0]
            s = ctx.wrap_socket(s, server_hostname=hostname)

        return self.Connection(client, s, self._url.netloc, self.chunk_size)

    def bind(self):
        self._sock = s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(ACCEPT_TIMEOUT)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(self._addr)
        s.listen(self.backlog)

    def serve(self, server):
        self.bind()
        self.log.info('listening: %s', self.url)

        s = self._sock

        ctx = None
        if self._ssl_cert:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            ctx.load_cert_chain(certfile=self._ssl_cert, keyfile=self._ssl_key)

        stop = self._stop
        stopped = self._stopped
        stop.clear()
        stopped.clear()

        try:
            while not stop.is_set():
                try:
                    sock, addr = s.accept()
                except socket.timeout:
                    continue
                sock.settimeout(self.timeout)

                try:
                    if ctx:
                        sock = ctx.wrap_socket(sock, server_side=True)
                except ssl.SSLError:
                    log.exception('ssl error')
                    continue

                utils.start_thread(self.handle, server, sock, addr)
        finally:
            stopped.set()

    def handle(self, server, sock, addr):
        addr = utils.url.format_addr(addr)
        with self.Connection(server, sock, addr, self.chunk_size) as con:
            server.handle(con)

    def stop(self):
        self._stop.set()

    def join(self, timeout=None):
        self._stopped.wait(timeout)

##
## sockio
##

def close(sock):
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except (OSError, socket.error) as e:
        # ignore if not connected
        if e.errno not in (errno.ENOTCONN,):# errno.EBADF):
            raise
    sock.close()

def recv(sock, chunk_size=None):
    """Receives a block of data from the socket."""
    try:
        return b''.join(recviter(sock, chunk_size))
    except errors.ReceiveInterrupted:
        return b''

def recviter(sock, chunk_size=None):
    """Returns an iterator over the data received from the socket.

    Each chunk of data yielded will be equal to or less than
    *chunk_size*.

    Can raise a `ReceiveInterrupted` exception.
    """
    buf = b''.join(recvsize(sock, 4, chunk_size))
    data_len = struct.unpack('>I', buf)[0]
    for chunk in recvsize(sock, data_len, chunk_size):
        yield chunk

def recvsize(sock, size, chunk_size=None):
    """Returns an iterator over the chunks received from the socket.

    If the socket stops receiving data before *size* bytes have been read, a
    `ReceiveInterrupted` exception will be raised.
    """
    pos = 0
    chunk_size = min(size, chunk_size or CHUNK_SIZE)
    while pos < size:
        chunk = sock.recv(min(size-pos, chunk_size))
        if not chunk:
            raise errors.ReceiveInterrupted()
        pos += len(chunk)
        yield chunk

def send(sock, data):
    """Sends *data* over the socket."""
    data_len = len(data)
    size = struct.pack('>I', data_len)
    sock.sendall(size)
    sock.sendall(data)
