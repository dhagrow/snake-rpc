from . import logs
from . import utils
from . import errors
from . import registry
from .codec import get as get_codec
from .transport import get as get_transport
from .service import ServiceProxy, get as get_service

DEFAULT_CODEC = 'msgpack'

log = logs.get(__name__)

class Interface(object):
    def __init__(self, transport=None, codec=None, version=None):
        """Base class for client or server interfaces.

        *transport* can be a `transport.Transport` instance, or the name of a
        registered `transport.Transport` class.

        *codec* can be a `codec.Codec` instance, or the name of a
        registered `codec.Codec` class.

        *version* is an optional version string for tracking changes.
        """
        # initialize all metaclass registries
        registry.init()

        self.transport = get_transport(transport or utils.DEFAULT_URL)
        self.codec = codec
        self.version = version

    @property
    def url(self):
        return self.transport.url

    @property
    def codec(self):
        return self._codec

    @codec.setter
    def codec(self, codec):
        self._codec = codec and get_codec(codec)
        log.debug('codec: %s', self._codec and self._codec._name_)

class Client(Interface):
    def __init__(self, transport=None, codec=None, version=None,
            retry_count=None, retry_interval=None):
        super(Client, self).__init__(transport, codec, version)

        self._con = None

        self.retry_count = retry_count
        self.retry_interval = retry_interval

    ## connection ##

    def connect(self):
        if not self._con:
            try:
                self._con = self.transport.connect(self)
            except Exception as e:
                raise errors.TransportError(e)
        return self._con

    def close(self):
        if self._con:
            self._con.close()
        self._con = None

    ## remote services ##

    def __getitem__(self, name):
        """Convenience access to `service()`."""
        return self.service(name)
    
    def __getattr__(self, name):
        """Convenience access to `service()`.
        
        Note that this will not work if the service name is that same
        as a `Client` attribute. Use the `service()` method in those cases.
        """
        try:
            return self.service(name)
        except errors.RemoteError as e:
            if e.name != 'KeyError':
                raise
            raise AttributeError(name)

    def service(self, name, metadata=True):
        """Returns a `ServiceProxy` instance providing access to a remote
        service.

        If *metadata* is `True`, retrieves the metadata for the service commands
        from the remote interface. *metadata* can also be set directly as a list
        of command metadata.
        """
        return ServiceProxy(name, self, metadata)

    def service_names(self):
        return self.service('_meta').service_names()

class Server(Interface):
    def __init__(self, transport=None, codec=None, version=None,
            remote_tracebacks=False):
        super(Server, self).__init__(transport, codec or DEFAULT_CODEC, version)

        self._services = {}
        self.add_service('meta', {'server': self}, '_meta')

        self.remote_tracebacks = remote_tracebacks

    ## connection ##

    def serve(self):
        try:
            self.transport.serve(self)
        except Exception as e:
            raise errors.TransportError(e)

    def handle(self, con):
        con.get_protocol().handle()

    def stop(self):
        self.transport.stop()

    def join(self, timeout=None):
        self.transport.join(timeout)

    ## local services ##

    def add_service(self, service, service_args=None, alias=None):
        if service == 'meta': # special case
            service_args = {'server': self}

        svc = get_service(service, service_args, alias)
        self._services[svc._name_] = svc

        log.debug('service added: %s', svc._name_)

        return self

    def remove_service(self, name):
        del self._services[name]
        return self

    def service(self, name):
        return self._services[name]

    def services(self):
        return [self.service(n) for n in self.service_names()]

    def service_names(self):
        return [k for k in self._services if k and not k.startswith('_')]
