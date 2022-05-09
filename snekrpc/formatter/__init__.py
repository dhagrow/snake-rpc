from __future__ import print_function

import inspect
import importlib

from .. import utils
from .. import registry

FormatterMeta = registry.create_metaclass(__name__)

def get(name, **kwargs):
    """Returns an instance of the Formatter matching *name*."""
    if isinstance(name, Formatter):
        return name
    cls = load(name) if '.' in name else FormatterMeta.get(name)
    return cls(**kwargs)

def load(name):
    """Imports and returns the Formatter class matching *name*."""
    mod_name, cls_name = name.rsplit('.', 1)
    mod = importlib.import_module(mod_name)
    return getattr(mod, cls_name)

class Formatter(utils.compat.with_metaclass(FormatterMeta, object)):
    def process(self, res):
        if inspect.isgenerator(res):
            for r in res:
                self.print(r)
        else:
            self.print(res)

    def print(self, res):
        print(self.format(res))

    def format(self, res):
        return res
