import inspect
import datetime

import temporenc

from .. import errors
from .. import utils
from .. import registry

CodecMeta = registry.create_metaclass(__name__)

def get(name, codec_args=None):
    """Returns an instance of the Codec matching *name*."""
    if isinstance(name, Codec):
        return name
    cls = CodecMeta.get(name)
    return cls(**(codec_args or {}))

class Codec(utils.compat.with_metaclass(CodecMeta, object)):
    _name_ = None

    def encode(self, msg):
        raise NotImplementedError('abstract')

    def decode(self, data):
        raise NotImplementedError('abstract')

    def _encode(self, msg):
        """Wrapper that provides encoding error context. Used internally."""
        try:
            return self.encode(msg)
        except Exception as e:
            raise errors.EncodeError('{}: msg={}'.format(e,
                utils.format.elide(repr(msg))))

    def _decode(self, data):
        """Wrapper that provides decoding error context. Used internally."""
        try:
            return self.decode(data)
        except Exception as e:
            raise errors.DecodeError('{}: data={!r}'.format(e,
                utils.format.elide(repr(data))))

## combined codecs

def encode(obj):
    if isinstance(obj, datetime.datetime):
        return encode_datetime(obj)
    elif inspect.isgenerator(obj):
        return encode_generator(obj)
    return obj

def decode(obj):
    if u'__datetime__' in obj:
        return decode_datetime(obj)
    elif u'__generator__' in obj:
        return decode_generator(obj)
    return obj

## datetime support

def encode_datetime(obj):
    return {u'__datetime__': temporenc.packb(obj)}

def decode_datetime(obj):
    return temporenc.unpackb(obj[u'__datetime__']).datetime()

## generator support
## Note that this is only intended to mark that *obj* is a generator. It
## does not encode/decode the contents.
## This is important for the argument handling in `protocol.py:recv_cmd()`

def encode_generator(obj):
    return {u'__generator__': None}

def decode_generator(obj):
    # any generator is fine
    return (x for x in ())
