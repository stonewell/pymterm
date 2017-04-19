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

DEFAULT_FG_COLOR_IDX = 256
DEFAULT_BG_COLOR_IDX = 257

class TextAttribute(object):
    def __init__(self, f_color_idx, b_color_idx, mode = 0):
        super.__init__()

        self._f_color_idx = f_color_idx
        self._b_color_idx = b_color_idx
        self._mode = mode

    def set_mode(self, text_mode):
        setBit(self._mode, text_mode)

    def reset_mode(self):
        self._mode = 0
        
    def unset_mode(self, text_mode):
        clearBit(self._mode, text_mode)

    def has_mode(self, text_mode):
        return testBit(self._mode, text_mode)

    def set_fg_idx(self, fg_idx):
        self._f_color_idx = fg_idx

    def reset_fg_idx(self):
        self._f_color_idx = DEFAULT_FG_COLOR_IDX
        
    def set_bg_idx(self, bg_idx):
        self._b_color_idx = bg_idx

    def reset_bg_idx(self):
        self._b_color_idx = DEBAULT_BG_COLOR_IDX

    def get_fg_idx(self):
        return self._f_color_idx

    def get_bg_idx(self):
        return self._b_color_idx
    
    def equals(self, attr):
        return (self._f_color_idx == attr._f_color_idx and
                    self._b_color_idx == attr._b_color_idx and
                    self._mode == attr._mode)

def get_default_text_attribute():
    return TextAttribute(DEFAULT_FG_COLOR_IDX,
                             DEFAULT_BG_COLOR_IDX,
                             0)
def clone_attr(attr):
    return TextAttribute(attr.f_color, attr.b_color, attr.mode)

