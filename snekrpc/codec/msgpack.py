from __future__ import absolute_import

import msgpack
from . import Codec, encode, decode

class MsgpackCodec(Codec):
    _name_ = 'msgpack'

    def encode(self, msg):
        return msgpack.packb(msg, use_bin_type=True, default=encode)

    def decode(self, data):
        return msgpack.unpackb(data, use_list=True, raw=False, object_hook=decode)
