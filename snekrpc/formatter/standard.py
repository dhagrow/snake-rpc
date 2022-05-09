from __future__ import print_function

import json
import pprint
import datetime

from . import Formatter

class RawFormatter(Formatter):
    _name_ = 'raw'

    def print(self, res):
        print(self.format(res), end='')

class PprintFormatter(Formatter):
    _name_ = 'pprint'

    def print(self, res):
        pprint.pprint(res)

class JsonFormatter(Formatter):
    _name_ = 'json'

    def format(self, res):
        return json.dumps(res, default=self.encode)

    def encode(self, obj):
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf8')
            except UnicodeDecodeError:
                return '<binary data>'
        elif isinstance(obj, datetime.datetime):
            return obj.isoformat()
        raise TypeError('unsupported type: %s' % type(obj))
