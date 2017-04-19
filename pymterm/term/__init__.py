#__init__.py
from collections import namedtuple


class TextMode:
    STDOUT = 0
    REVERSE = 1
    SELECTION = 2
    CURSOR = 3
    BOLD = 4
    DIM = 5

def reserve(l, size, default=None):
    import copy

    while size > len(l):
        l.append(copy.deepcopy(default) if default is not None else None)

def clone_attr(attr):
    return TextAttribute(attr.f_color, attr.b_color, attr.mode)

def testBit(int_type, offset):
    mask = 1 << offset
    return(int_type & mask)

# setBit() returns an integer with the bit at 'offset' set to 1.
def setBit(int_type, offset):
    mask = 1 << offset

    return(int_type | mask)

# clearBit() returns an integer with the bit at 'offset' cleared.
def clearBit(int_type, offset):
    mask = ~(1 << offset)
    return(int_type & mask)

# toggleBit() returns an integer with the bit at 'offset' inverted, 0 -> 1 and 1 -> 0.
def toggleBit(int_type, offset):
    mask = 1 << offset
    return(int_type ^ mask)

class TextAttribute(object):
    def __init__(self, f_color_idx, b_color_idx, mode = 0):
        super().__init__()

        self.f_color_idx = f_color_idx
        self.b_color_idx = b_color_idx
        self.mode = mode

    def set_mode(self, text_mode):
        setBit(self.mode, text_mode)

    def unset_mode(self, text_mode):
        clearBit(self.mode, text_mode)

    def has_mode(self, text_mode):
        return testBit(self.mode, text_mode)
