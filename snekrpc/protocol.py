import inspect
import traceback

from .op import Op
from . import logs
from . import utils
from . import errors

log = logs.get(__name__)

class Protocol(object):
    def __init__(self, interface, con, metadata=None):
        self._ifc = interface
        self._con = con

        self.metadata = metadata or {}

    @property
    def local_url(self):
        return self._ifc.url

    @property
    def remote_url(self):
        return self._con.url

    ## protocol ##

    def handle(self):
        recv = self._con.recv_msg

        while True:
            try:
                msg = recv()

                if msg is None:
                    return
                elif msg.op == Op.command:
                    self.recv_cmd(msg)
                else:
                    raise errors.ProtocolOpError(msg.op)

            except errors.TransportError as e:
                logger = (log.exception
                    if log.isEnabledFor(logs.DEBUG) else log.error)
                logger('transport error (%s): %s',
                    self.remote_url, utils.format.format_exc(e))

            except Exception as e:
                self.send_err(e)

    def recv_cmd(self, msg):
        """Processes commands received from the remote interface."""
        svc_name, cmd_name, args, kwargs = msg.data

        svc = self._ifc.service(svc_name)
        func = getattr(svc, cmd_name)

        # convert any stream to a generator
        recv_args = []
        recv_kwargs = {}

        for arg in args:
            if inspect.isgenerator(arg):
                arg = self.recv_stream()
            recv_args.append(arg)
        for name, arg in kwargs.items():
            if inspect.isgenerator(arg):
                arg = self.recv_stream()
            recv_kwargs[name] = arg

        args = recv_args
        kwargs = recv_kwargs

        if log.isEnabledFor(logs.DEBUG):
            log.debug('cmd: %s <- %s',
                utils.format.format_cmd(svc_name, cmd_name, args, kwargs),
                self.remote_url)

        # call
        res = func(*args, **kwargs)

        if inspect.isgenerator(res):
            self.send_stream(res)
        else:
            self._con.send_msg(Op.data, res)

    def send_cmd(self, svc_name, cmd_name, *args, **kwargs):
        """Sends a command operation to the remote interface."""
        if log.isEnabledFor(logs.DEBUG):
            log.debug('cmd: %s -> %s',
                utils.format.format_cmd(svc_name, cmd_name, args, kwargs),
                self.remote_url)

        # convert any generator arg to a stream
        stream = None
        send_args = []
        send_kwargs = {}

        for arg in args:
            if inspect.isgenerator(arg):
                if stream is not None:
                    err = 'only one stream param is possible'
                    raise errors.ParameterError(err)
                stream = arg
            send_args.append(arg)
        for name, arg in kwargs.items():
            if inspect.isgenerator(arg):
                if stream is not None:
                    err = 'only one stream param is possible'
                    raise errors.ParameterError(err)
                stream = arg
            send_kwargs[name] = arg

        args = send_args
        kwargs = send_kwargs

        # send command
        self._con.send_msg(Op.command, (svc_name, cmd_name, args, kwargs))

        # send stream
        if stream:
            self.send_stream(stream)

        msg = self._con.recv_msg()

        if msg.op == Op.data:
            return msg.data
        elif msg.op == Op.error:
            raise errors.RemoteError(*msg.data)
        elif msg.op == Op.stream_start:
            # have to return a generator (see service/__init__.py:wrap_call)
            return self.recv_stream(started=True)
        else:
            raise errors.ProtocolOpError(msg.op)

    def recv_stream(self, started=False):
        recv = self._con.recv_msg

        if not started:
            msg = recv()
            if not msg:
                raise errors.ReceiveInterrupted()
            if msg.op != Op.stream_start:
                raise errors.ProtocolOpError(msg.op)

        while True:
            msg = recv()
            if not msg:
                raise errors.ReceiveInterrupted()
            elif msg.op == Op.data:
                yield msg.data
            elif msg.op == Op.error:
                raise errors.RemoteError(*msg.data)
            elif msg.op == Op.stream_end:
                return
            else:
                raise errors.ProtocolOpError(msg.op)

    def send_stream(self, it):
        send = self._con.send_msg
        send(Op.stream_start)
        for x in it:
            send(Op.data, x)
        send(Op.stream_end)

    def send_err(self, e):
        name = e.__class__.__name__
        msg = str(e)
        tb = traceback.format_exc().rstrip() if self._ifc.remote_tracebacks else ''

        log.exception('%s: %s', name, msg)
        self._con.send_msg(Op.error, utils.encoding.to_unicode((name, msg, tb)))
