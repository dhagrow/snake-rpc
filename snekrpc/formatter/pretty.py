from __future__ import print_function

import pprint

from . import Formatter
from ..utils import compat

str = compat.str

class PrettyFormatter(Formatter):
    _name_ = 'pretty'

    def print(self, res):
        s = self.format(res)
        if s is not None:
            print(s)

    def format(self, res):
        if res is None:
            return
        elif isinstance(res, str):
            return res
        elif isinstance(res, (list, tuple)):
            return '\n'.join(str(r) for r in res)
        else:
            return pprint.pformat(res)
