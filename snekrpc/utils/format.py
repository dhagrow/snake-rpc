import traceback

def format_cmd(svc_name, cmd_name, args, kwargs):
    argstr = []
    if args:
        argstr.append(', '.join([repr(v) for v in args]))
    if kwargs:
        argstr.append(', '.join('{}={}'.format(k, repr(v))
            for k, v in kwargs.items()))
    return '{}.{}({})'.format(svc_name, cmd_name, elide(', '.join(argstr)))

def format_exc(exc):
    return traceback.format_exception_only(exc.__class__, exc)[0].strip()

# XXX: term.elide ?
def elide(s, width=100):
    return s if len(s) <= width else s[:width-3] + '...'
