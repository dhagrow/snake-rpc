try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from .compat import str, viewitems

def to_bytes(s, encoding='utf8'):
    if isinstance(s, bytes):
        pass
    elif isinstance(s, str):
        s = s.encode(encoding)
    elif isinstance(s, dict):
        s = {to_bytes(k, encoding): to_bytes(v, encoding)
            for k, v in viewitems(s)}
    elif isinstance(s, Iterable):
        s = [to_bytes(x, encoding) for x in s]
    return s

def to_unicode(s, encoding='utf8', dict_keys_only=False):
    """Attempts to decode all encountered bytes to unicode.

    *s* can be any standard data structure.

    If *dict_keys_only* is `True`, only the keys of a dict will be decoded.
    Values will remain untouched.
    """
    if isinstance(s, bytes):
        s = s.decode(encoding)
    elif isinstance(s, str):
        pass
    elif isinstance(s, dict):
        s = {to_unicode(k, encoding):
            v if dict_keys_only else to_unicode(v, encoding)
            for k, v in viewitems(s)}
    elif isinstance(s, Iterable):
        s = tuple(to_unicode(x, encoding) for x in s)
    return s
