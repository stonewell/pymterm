#__init__.py
from collections import namedtuple

TextAttribute = namedtuple('TextAttributes', ['f_color', 'b_color', 'mode'])

class TextMode:
    STDOUT = 0
    REVERSE = 1 << 0


