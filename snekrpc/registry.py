import threading

from . import logs
from . import errors
from .utils.path import import_package

log = logs.get(__name__)

_metaclasses = {}
_init_lock = threading.Lock()
_initialized = threading.Event()

def init():
    """Import and register modules for all known metaclass registries.

    Safe to call multiple times from multiple threads.
    """
    with _init_lock:
        if _initialized.is_set():
            return

        for meta_name, Meta in _metaclasses.items():
            Meta.init(meta_name)

        _initialized.set()

def create_metaclass(meta_name):
    class RegistryMeta(type):
        registry = {}

        def __init__(cls, name, bases, dct):
            if bases[0] is not object:
                cls._name_ = reg_name = dct.get('_name_', name)
                if reg_name in RegistryMeta.registry:
                    raise errors.RegistryError(
                        'already registered: {}'.format(reg_name))
                else:
                    RegistryMeta.registry[reg_name] = cls
                    log.debug('registered %s: %s',
                        meta_name.split('.', 1)[1], reg_name)
            super(RegistryMeta, cls).__init__(name, bases, dct)

        @classmethod
        def get(cls, name):
            _initialized.wait()
            return cls.registry[name]

        @classmethod
        def names(cls):
            _initialized.wait()
            return tuple(cls.registry.keys())

        @classmethod
        def init(cls, name):
            exceptions = import_package(name)
            for modname, exc in exceptions.items():
                RegistryMeta.registry[modname] = exc

    _metaclasses[meta_name] = RegistryMeta
    return RegistryMeta
