import threading

from .. import logs

# imports for convenience
from . import url
from . import path
from . import retry
from . import compat
from . import format
from . import encoding
from . import function

DEFAULT_URL = 'tcp://127.0.0.1:12321'

log = logs.get(__name__)

##
## threading
##

def start_thread(func, *args, **kwargs):
    def safe(func, *args, **kwargs):
        tid = threading.current_thread().ident
        log.debug('thread started [%s]: %s', tid, func.__name__)
        try:
            return func(*args, **kwargs)
        except Exception:
            log.exception('thread error')
        finally:
            log.debug('thread stopped [%s]: %s', tid, func.__name__)

    t = threading.Thread(target=safe, args=(func,) + args, kwargs=kwargs)
    t.daemon = True
    t.start()
    return t
