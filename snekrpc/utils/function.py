import re
import copy
import inspect
import keyword
import tokenize
import collections

try:
    from inspect import signature, Parameter as Param
except ImportError:
    from funcsigs import signature, Parameter as Param

from .. import errors

from . import compat
from .encoding import to_unicode, to_bytes

# tokenize.Name should only be used as a fallback, since Py2 and Py3 define it
# differently
_rx_ident = re.compile(r'^{}$'.format(tokenize.Name))
def is_identifier(s):
    try:
        return s.isidentifier()
    except AttributeError:
        return bool(_rx_ident.match(s)) and not keyword.iskeyword(s)

def command(**hints):
    """Decorator that identifies a function to expose as an RPC command.

    *hints* can be used to set type hints for arguments accepted by the
    command. A type hint can be a type object or a string. If a type object is
    passed, it's `__name__` attribute will be used as the type hint. The type
    hint should indicate to a client developer the type of value that is
    expected. Use of standard Python types is recommended.

    To provide more parameter metadata, use the `@param()` decorator.
    """
    def decorator(func):
        cmd_meta = func.__dict__.setdefault('_meta', {})
        params = cmd_meta.setdefault('params', {})
        for name, hint in hints.items():
            hintstr = _hint_to_str(hint)

            if hintstr == 'stream':
                if 'stream' in cmd_meta:
                    err = 'only one stream param is possible: {}'
                    raise errors.ParameterError(err.format(name))
                cmd_meta['stream'] = name

            params.setdefault(name, {})['hint'] = hintstr
        return func
    return decorator

def param(name, hint=None, doc=None, hide=False, **metadata):
    """Decorator that assigns additional metadata, such as a doc string, to
    individual command parameters.

    The default *hint* is a unicode string: `str`.

    Where supported, *hide* can be used to prevent parameters from being
    displayed. This can be used to hide `**kwargs` when only certain parameters
    are expected.
    """
    def decorator(func):
        cmd_meta = func.__dict__.setdefault('_meta', {})
        params = cmd_meta.setdefault('params', {})
        param = params.setdefault(name, {})

        if hint:
            hintstr = _hint_to_str(hint)

            if hintstr == 'stream':
                if 'stream' in cmd_meta:
                    err = 'only one stream param is possible: {}'
                    raise errors.ParameterError(err.format(name))
                cmd_meta['stream'] = name

            param['hint'] = hintstr

        if doc: param['doc'] = doc
        if hide: param['hide'] = hide
        param.update(metadata)
        return func
    return decorator

def _hint_to_str(hint):
    """Internal. Converts type hints to strings."""
    if not hint:
        name = 'str'
    elif isinstance(hint, (compat.str, bytes)):
        name = hint
    else:
        name = hint.__name__
        if name == 'str':
            name = 'str' if compat.PY3 else 'bytes'
        elif name == 'unicode':
            name = 'str'
    return to_unicode(name)

def func_to_dict(func, remove_self=False):
    """Returns metadata for *func* in a dict.

    If *remove_self* is `True` ...
    """
    d = {
        'name': func.__name__,
        'doc': func.__doc__,
        }

    # we mutate these dicts, so make copies
    cmd_meta = copy.deepcopy(getattr(func, '_meta', {}))
    cmd_params = cmd_meta.pop('params', {})

    sig = signature(func)

    if remove_self:
        # remove 'self' parameter
        sig = sig.replace(parameters=list(sig.parameters.values())[1:])

    # add parameters
    params = d['params'] = []
    for p in sig.parameters.values():
        param = {
            'name': p.name,
            'kind': int(p.kind),
            }

        hint = param.get('hint')
        if p.default is not p.empty:
            param['default'] = p.default
            # if no hint, set an automatic hint based on the default value
            if not hint and p.default is not None:
                param['hint'] = type(p.default).__name__

        param.update(cmd_params.pop(p.name, {}))

        params.append(param)

    # add missing hints as params
    for name, param in cmd_params.items():
        param['name'] = name
        param.setdefault('kind', int(Param.KEYWORD_ONLY))
        params.append(param)

    # stream
    if 'stream' in cmd_meta:
        d['stream'] = cmd_meta.pop('stream')

    if inspect.isgeneratorfunction(func):
        d['isgen'] = True

    if cmd_meta:
        # add any left over metadata
        d['meta'] = cmd_meta

    return d

def dict_to_func(d, callback):
    """Returns a function based on the metadata dict *d*, as created by
    `func_to_dict`.

    *callback* must be a function which will be wrapped and called by the
    returned function.

    Note that `exec` is used to create the wrapping function. This exposes a
    potential security risk, however care is taken to ensure that the only user
    provided input that is executed consists of function parameter names which
    must be valid Python identifiers. It should therefore be safe to use from a
    security perspective.

    `POSITIONAL_ONLY` parameters are silently converted to
    `POSITIONAL_OR_KEYWORD` parameters.
    """
    sig_defn = []
    sig_call = []

    meta = copy.deepcopy(d)
    params = collections.OrderedDict()

    for p in meta.pop('params'):
        if not is_identifier(p['name']):
            raise ValueError('invalid parameter name: {}'.format(p['name']))
        kind = {
            0: Param.POSITIONAL_ONLY,
            1: Param.POSITIONAL_OR_KEYWORD,
            2: Param.VAR_POSITIONAL,
            3: Param.KEYWORD_ONLY,
            4: Param.VAR_KEYWORD,
            }[p['kind']]

        if kind == Param.KEYWORD_ONLY:
            # we assume these are part of kwargs
            continue
        elif kind == Param.VAR_POSITIONAL:
            name = '*' + p['name']
        elif kind == Param.VAR_KEYWORD:
            name = '**' + p['name']
        else:
            name = p['name']

        def_name = name
        if 'default' in p:
            def_name += '=' + repr(p['default'])

        sig_defn.append(def_name)
        sig_call.append(name)

        params[p.pop('name')] = p

    meta['params'] = params

    sig_defn = ', '.join(sig_defn)
    sig_call = ', '.join(sig_call)

    isgen = meta.pop('isgen', False)
    if isgen:
        tpl = 'def {}({}):\n  for x in callback({}): yield x'
    else:
        tpl = 'def {}({}): return callback({})'
    src = tpl.format(d['name'], sig_defn, sig_call)

    # compile
    g = {'callback': callback}
    exec(src, g) # pylint: disable=exec-used

    func = g[meta.pop('name')]
    func.__doc__ = meta.pop('doc', None)
    func.__dict__['_meta'] = meta

    return func

def get_func_name(name):
    # func.__name__ must be bytes in Python2
    return to_unicode(name) if compat.PY3 else to_bytes(name)
