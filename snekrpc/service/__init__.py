import inspect
import itertools

from .. import logs
from .. import utils
from .. import errors
from .. import registry
from ..utils.encoding import to_unicode

log = logs.get(__name__)

def parse_alias(name):
    try:
        name, alias = name.split(':')
    except ValueError:
        alias = None
    return name, alias

def get_class(name):
    return ServiceMeta.get(name)

def get(name, service_args=None, alias=None):
    """Returns an instance of the Service matching *name*."""
    if isinstance(name, Service):
        obj = name
    elif inspect.isclass(name) and issubclass(name, Service):
        obj = name(**(service_args or {}))
    else:
        cls = get_class(name)
        obj = cls(**(service_args or {}))

    # rename the instance if any alias was set
    if alias:
        obj._name_ = alias

    return obj

def service_to_dict(svc):
    """Returns service metadata as a dict."""
    f2d = utils.function.func_to_dict

    d = {
        'name': svc._name_,
        'doc': svc.__doc__,
        }
    d['commands'] = cmds = []

    # find commands
    for name in dir(svc):
        if name.startswith('_'):
            continue
        attr = getattr(svc, name)
        meta = getattr(attr, '_meta', None)
        if meta is not None:
            cmds.append(f2d(attr))

    return d

ServiceMeta = registry.create_metaclass(__name__)

class Service(utils.compat.with_metaclass(ServiceMeta, object)):
    _name_ = None

    # this is here only to define an __init__ that takes no args
    # otherwise Python will use a `method-wrapper`, which can somehow produce
    # a `Signature` with different arguments than what it actually takes
    def __init__(self):
        pass

class ServiceProxy(object):
    """A proxy class providing access to a remote service.

    If *metadata* is `True`, the metadata service will be used to load metadata
    for the selected remote service. If `False`, no metadata will be loaded.
    It is also possible to use *metadata* to pass a metadata dict directly.
    """
    def __init__(self, name, client, metadata=True):
        self._svc_name = to_unicode(name)
        self._client = client
        self._commands = cmds = {}

        self._retry = utils.retry.Retry(
            client.retry_count, client.retry_interval,
            errors=[errors.TransportError], logger=log)

        # collect metadata. convert commands to functions
        wrap = lambda c: wrap_call(self, c['name'], c)
        if metadata is True:
            meta = ServiceProxy('_meta', client, metadata=False)
            svc = meta.service(self._svc_name)
            cmds.update({c['name']: wrap(c) for c in svc['commands']})
        elif metadata:
            cmds.update({c['name']: wrap(c) for c in metadata})

    def __getattr__(self, cmd_name):
        if self._commands:
            # return a metadata-based wrapper
            try:
                return self._commands[cmd_name]
            except KeyError:
                raise AttributeError(cmd_name)
        # return a raw wrapper
        return wrap_call(self, cmd_name)

    def __dir__(self):
        return list(self._commands.keys()) + super(ServiceProxy, self).__dir__()

def wrap_call(proxy, cmd_name, cmd_def=None):
    # Protocol.send_cmd() is wrapped by two functions here in order to simplify
    # connection cleanup for both regular and generator calls.
    # For that reason call() is a generator, and call_wrap() handles the
    # case where the command is not a generator
    def call(*args, **kwargs):
        # with proxy._client.connect() as con:
        con = proxy._client.connect()
        try:
            proto = con.get_protocol({proxy._svc_name: proxy._commands})

            res = proto.send_cmd(proxy._svc_name, to_unicode(cmd_name),
                *args, **to_unicode(kwargs, dict_keys_only=True))

            # notify call_wrap of type of response
            isgen = inspect.isgenerator(res)
            yield isgen

            if isgen:
                for r in res:
                    yield r
            else:
                yield res
        except errors.TransportError:
            proxy._client.close()
            raise

    def call_wrap(*args, **kwargs):
        gen = call(*args, **kwargs)
        isgen = next(gen) # get type of response
        return iter(StreamInitiator(gen)) if isgen else next(gen)

    if cmd_def and cmd_def.get('isgen'):
        retry_wrap = lambda *a, **k: proxy._retry.call_gen(call_wrap, *a, **k)
    else:
        retry_wrap = lambda *a, **k: proxy._retry.call(call_wrap, *a, **k)

    if not cmd_def:
        return retry_wrap
    return utils.function.dict_to_func(cmd_def, retry_wrap)

class StreamInitiator(object):
    """Captures the first value of a generator to ensure that it begins
    execution."""
    def __init__(self, gen):
        # cache first result
        try:
            gen = itertools.chain([next(gen)], gen)
        except StopIteration:
            # keep the generator to raise StopIteration later
            pass
        self._gen = gen

    def __iter__(self):
        for x in self._gen:
            yield x
