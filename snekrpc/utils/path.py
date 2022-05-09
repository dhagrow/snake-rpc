import io
import os
import errno
import pkgutil
import importlib

from .. import logs

log = logs.get(__name__)

BASE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

def base_path(*names):
    return os.path.join(BASE_PATH, *names)

def ensure_dirs(path, mode=0o755):
    """Creates *path* if it does not exist. Does nothing otherwise."""
    try:
        os.makedirs(path, mode)
    except OSError:
        pass

def discard_file(path):
    """Removes *path* if it exists. Does nothing otherwise."""
    try:
        os.remove(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def iter_file(fp, chunk_size=None):
    """Iterates through a file object in chunks."""
    chunk_size = chunk_size or io.DEFAULT_BUFFER_SIZE
    for chunk in iter(lambda: fp.read(chunk_size), b''):
        yield chunk

def import_package(pkgname):
    """Imports all modules in a package (aka directory).

    Returns a dict of `{<modname>: <exc>}` for modules that raise an exception
    on import.
    """
    exceptions = {}

    path = base_path(pkgname.replace('.', '/'))
    for _, modname, ispkg in pkgutil.iter_modules([path]):
        if ispkg: continue
        exc = import_module(modname, pkgname)
        if exc:
            exceptions[modname] = exc

    return exceptions

def import_module(modname, pkgname=None):
    """Imports a module, optionally from a package.

    Returns any exceptions."""
    name = '.'.join(filter(None, [pkgname, modname]))
    try:
        log.debug('loading: %s', name)
        if pkgname:
            importlib.import_module('.' + modname, pkgname)
        else:
            importlib.import_module(modname)
    except Exception as e:
        return e
