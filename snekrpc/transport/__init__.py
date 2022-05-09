import struct

from ..op import Op
from .. import logs
from .. import utils
from .. import errors
from .. import protocol
from .. import registry

TransportMeta = registry.create_metaclass(__name__)

log = logs.get(__name__)

def get(url, transport_args=None):
    """Returns an instance of the Transport matching the schema of *url*."""
    if isinstance(url, Transport):
        return url

    scheme = utils.url.Url(url).scheme
    cls = TransportMeta.get(scheme)
    if isinstance(cls, Exception):
        raise cls
    return cls(url, **(transport_args or {}))

class Transport(utils.compat.with_metaclass(TransportMeta, object)):
    def __init__(self, url):
        self._url = utils.url.Url(url)

    @property
    def url(self):
        return self._url

    def connect(self, client):
        raise NotImplementedError('abstract')

    def serve(self, server):
        raise NotImplementedError('abstract')

    def stop(self):
        raise NotImplementedError('abstract')

    def join(self, timeout=None):
        raise NotImplementedError('abstract')

class Message(object):
    def __init__(self, op, data=None):
        self.op = op
        self.data = data

    def __repr__(self):
        tpl = '{}(op=<{}:{}>{})'
        class_name = self.__class__.__name__
        data_str = ', data={}'.format(
            utils.format.elide(repr(self.data))) if self.data is not None else ''
        return tpl.format(class_name, self.op, Op.to_str(self.op), data_str)

class Connection(object):
    def __init__(self, interface, addr):
        self._ifc = interface
        self._addr = addr
        self._proto = protocol.Protocol(interface, self)

    @property
    def url(self):
        return self._addr

    def get_protocol(self, metadata=None):
        if metadata:
            self._proto.metadata = metadata
        return self._proto

    ## data protocol ##

    def send(self, data):
        raise NotImplementedError('abstract')

    def recv(self):
        raise NotImplementedError('abstract')

    ## handshake protocol ##

    def req_handshake(self):
        if self._ifc.codec:
            return

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s -> %s', Message(Op.handshake, None), self._addr)

        buf = struct.pack('>B', Op.handshake)
        self.send(buf)

        buf = self.recv()
        op, codec = struct.unpack('>B{}s'.format(len(buf) - 1), buf)
        if op != Op.handshake:
            raise errors.ProtocolOpError(op)

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s <- %s', Message(op, codec), self._addr)

        self._ifc.codec = codec.decode('utf8')

    def res_handshake(self, data):
        if data != b'\x00': # bit of a shortcut. skip conversion to Op.handshake
            return data

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s <- %s', Message(Op.handshake, None), self._addr)

        name = self._ifc.codec._name_.encode('utf8')

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s -> %s', Message(Op.handshake, name), self._addr)

        buf = struct.pack('>B{}s'.format(len(name)), Op.handshake, name)
        self.send(buf)

        # continue with standard protocol
        return self.recv()

    ## message protocol ##

    def recv_msg(self):
        data = self.recv()
        # check for handshake
        data = self.res_handshake(data)

        if not data:
            return None

        msg = Message(*self._ifc.codec._decode(data))

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s <- %s', msg, self._addr)

        return msg

    def send_msg(self, op, data=None):
        # check for handshake
        self.req_handshake()

        if log.isEnabledFor(logs.DEBUG):
            log.debug('msg: %s -> %s', Message(op, data), self._addr)

        msg = self._ifc.codec._encode((op, data))
        return self.send(msg)

    ## management ##

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, etype, evalue, tb):
        self.close()
