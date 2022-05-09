import io
import sys

PY3 = sys.version_info.major >= 3
# use str for unicode data and bytes for binary data
str = str if PY3 else unicode

def is_fileobject(o):
    return isinstance(o, io.IOBase if PY3 else file)

##
## Python 2/3 compatibility
## Pulled from the "future" library.
##

def with_metaclass(meta, *bases):
    """
    Function from jinja2/_compat.py. License: BSD.

    Use it like this::

        class BaseForm(object):
            pass

        class FormType(type):
            pass

        class Form(with_metaclass(FormType, BaseForm)):
            pass

    This requires a bit of explanation: the basic idea is to make a
    dummy metaclass for one level of class instantiation that replaces
    itself with the actual metaclass.  Because of internal type checks
    we also need to make sure that we downgrade the custom metaclass
    for one level to something closer to type (that's why __call__ and
    __init__ comes back from type etc.).

    This has the advantage over six.with_metaclass of not introducing
    dummy classes into the final MRO.
    """
    class metaclass(meta):
        __call__ = type.__call__
        __init__ = type.__init__
        def __new__(cls, name, this_bases, d):
            if this_bases is None:
                return type.__new__(cls, name, (), d)
            return meta(name, bases, d)
    return metaclass('temporary_class', None, {})

def viewitems(obj):
    return getattr(obj, "viewitems", obj.items)()

def viewkeys(obj):
    return getattr(obj, "viewkeys", obj.keys)()

def viewvalues(obj):
    return getattr(obj, "viewvalues", obj.values)()
