from __future__ import absolute_import

try: # py3
    import socketserver
    from http import client
    from http import server
except ImportError: # py2
    import httplib as client
    import BaseHTTPServer as server
    import SocketServer as socketserver

from .. import logs
from .. import utils
from .. import param
from .. import __version__

from . import Connection, Transport

SERVER_NAME = 'snekrpc'

log = logs.get(__name__)

# BaseRequestHandler is remarkably not an object in Py2
class HTTPHandler(server.BaseHTTPRequestHandler, object):
    protocol_version = 'HTTP/1.1'

    def do_POST(self):
        # handle command
        ifc = self.server._interface
        con = HTTPServerConnection(
            ifc, utils.url.format_addr(self.client_address), self)
        with con:
            while not con.should_close:
                ifc.handle(con)

    def start_response(self):
        # start response
        self.send_response(200)
        self.send_header('Connection', 'keep-alive')
        # TODO: set the content-type based on the codec used
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Transfer-Encoding', 'chunked')

        # user headers
        for k, v in self.server._headers.items():
            self.send_header(k, v)
        self.end_headers()

    def version_string(self):
        return self.server._version or '{}/{} {}'.format(SERVER_NAME,
            __version__, self.server._interface.version or '').strip()

    def log_request(self, code='-', size='-'):
        url = utils.url.format_addr(self.client_address)
        log.debug('%r %s <- %s', self.requestline, code, url)

class HTTPTransport(Transport):
    _name_ = 'http'
    Handler = HTTPHandler

    @param('headers', dict)
    def __init__(self, url, headers=None, version=None):
        super(HTTPTransport, self).__init__(url)
        url = self._url
        self._addr = (url.host, url.port)

        self.headers = headers
        self.version = version

    def connect(self, client):
        return HTTPClientConnection(client, utils.url.format_addr(self._addr))

    def serve(self, server):
        self._server = ThreadingHTTPServer(self._addr, self.Handler)
        self._server._headers = self.headers or {}
        self._server._version = self.version
        self._server._interface = server

        log.info('listening: %s', self.url)
        # XXX: expose poll_interval for config?
        self._server.serve_forever()

    def stop(self):
        # close the server's socket
        self._server.server_close()
        # stop the serve loop
        self._server.shutdown()

    def join(self, timeout=None):
        # ideally we could pass the timeout to the __is_shut_down Event here
        pass

class ThreadingHTTPServer(socketserver.ThreadingMixIn, server.HTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        log.exception('request error (%s)', utils.url.format_addr(client_address))

class HTTPClientConnection(Connection):
    def __init__(self, client_ifc, url):
        super(HTTPClientConnection, self).__init__(client_ifc, url)

        self._res = None

        self._con = con = client.HTTPConnection(url)
        con.auto_open = False
        self.connect()

    def connect(self):
        con = self._con
        con.connect()
        log.debug('connected: %s', self.url)

        con.putrequest('POST', '')
        con.putheader('Connection', 'keep-alive')
        con.putheader('Content-Type', 'application/octet-stream')
        con.putheader('Transfer-Encoding', 'chunked')
        con.endheaders()

    def recv(self):
        if not self._res:
            self._res = self._con.getresponse()
        rfile = self._res.fp

        line = rfile.readline()
        chunk_len = int(line[:-2], 16)

        # +2 for the trailing newline (not included in chunk_len)
        return rfile.read(chunk_len + 2)[:-2]

    def send(self, data):
        con = self._con

        con.send('{:X}\r\n'.format(len(data)).encode('ascii'))
        con.send(data + b'\r\n')

    def close(self):
        log.debug('disconnected: %s', self.url)

class HTTPServerConnection(Connection):
    def __init__(self, server, url, handler):
        super(HTTPServerConnection, self).__init__(server, url)

        self.handler = handler
        self.response_started = False
        self.should_close = False

        log.debug('connected: %s', self.url)

    def recv(self):
        rfile = self.handler.rfile

        line = rfile.readline()
        if not line:
            self.should_close = True
            return None
        chunk_len = int(line[:-2], 16)

        # +2 for the trailing newline (not included in chunk_len)
        return rfile.read(chunk_len + 2)[:-2]

    def send(self, data):
        if not self.response_started:
            self.handler.start_response()
            self.response_started = True

        wfile = self.handler.wfile

        # send chunked
        wfile.write('{:X}\r\n'.format(len(data)).encode('ascii'))
        wfile.write(data + b'\r\n')

    def close(self):
        self.handler.wfile.flush()
        log.debug('disconnected: %s', self.url)
