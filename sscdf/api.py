import graphblas as gb
from .container import Reader, Writer


def info(fp):
    """
    Returns a dict of attributes associated with the
    primary and secondary tensors.
    """
    with Reader(fp) as r:
        ret = r.info()
        if r.names():
            ret['SECONDARY'] = s = {}
            for name in r.names():
                s[name] = r.info(name)
    return ret


def read(file):
    with Reader(file) as r:
        return r.read()


def write(file, x, comment=None, *, format=None):
    if type(x) != gb.Matrix and type(x) != gb.Vector:
        raise TypeError(f'Object x must be a graphblas Matrix or Vector')
    with Writer(file) as w:
        w.write(x, comment=comment, format=format)


