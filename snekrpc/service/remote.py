from . import Service, ServiceProxy
from .. import Client, param
from .. import logs

log = logs.get(__name__)

class RemoteService(Service, ServiceProxy):
    """Provides access to a remote service"""
    _name_ = 'remote'

    @param('transport')
    @param('codec')
    @param('version')
    @param('retry_count', int)
    @param('retry_interval', float)
    @param('kwargs', hide=True)
    def __init__(self, name, **kwargs):
        Service.__init__(self)
        ServiceProxy.__init__(self, name, Client(**kwargs))

        log.info('forwarding (%s): %s', name, self._client.url)
