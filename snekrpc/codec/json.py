from __future__ import absolute_import

import json
from . import Codec, encode, decode

class JsonCodec(Codec):
    _name_ = 'json'

    def __init__(self, encoding=None):
        self._encoding = encoding or 'utf8'

    def encode(self, msg):
        return json.dumps(msg, default=encode).encode(self._encoding)

    def decode(self, data):
        return json.loads(data, object_hook=decode)
