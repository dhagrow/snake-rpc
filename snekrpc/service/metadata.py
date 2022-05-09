from .. import Service, command, param
from ..utils.encoding import to_unicode
from . import service_to_dict as s2d

class MetadataService(Service):
    """Provides commands that return server and service metadata.

    Note that this service is handled as a special case in several places.
    """
    _name_ = 'meta'

    @param('server', hide=True)
    def __init__(self, server):
        self._server = server

    @command()
    def status(self):
        ifc = self._server
        res = {
            'codec': ifc.codec._name_,
            'transport': ifc.transport._name_,
            'version': ifc.version,
            }
        return to_unicode(res)

    @command()
    def service_names(self):
        return self._server.service_names()

    @command()
    def services(self):
        return to_unicode([s2d(svc) for svc in self._server.services()])

    @command()
    def service(self, name):
        return to_unicode(s2d(self._server.service(name)))
