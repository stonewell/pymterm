#__init__.py
from collections import namedtuple

TextAttribute = namedtuple('TextAttributes', ['f_color', 'b_color', 'mode'])

class TextMode:
    STDOUT = 0
    REVERSE = 1 << 0
    SELECTION = 1 << 1
    CURSOR = 1 << 2


def set_attr_mode(attr, mode):
    if attr.mode is not None:
        mode |= attr.mode

    return attr._replace(mode=mode)

def reserve(l, size, default = None):
    if l is None:
        l = [default] * size

    if size > len(l):
        l += [default] * (size - len(l))

