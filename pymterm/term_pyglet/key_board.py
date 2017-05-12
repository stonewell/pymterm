import string

from pyglet.window import key


class KeyState(object):
    def __init__(self, symbol, modifiers):
        _key = key.symbol_string(symbol).lower()

        _text = _key if len(_key) == 1 and _key[0] in string.printable \
            else chr(symbol) if symbol < 256 \
            and chr(symbol) in string.printable \
            else None

        _modifiers = []

        if modifiers & key.MOD_ALT or modifiers & key.MOD_OPTION:
            _modifiers.append('alt')
        if modifiers & key.MOD_CTRL:
            _modifiers.append('ctrl')
        if modifiers & key.MOD_SHIFT:
            _modifiers.append('shift')

        if _modifiers == ['shift'] and _text and _text in string.printable:
            _text = _text.upper()

        self._key = _key
        self._text = _text
        self._modifiers = _modifiers
        self._symbol = symbol

    def has_alt(self):
        return 'alt' in self._modifiers

    def has_ctrl(self):
        return 'ctrl' in self._modifiers

    def has_shift(self):
        return 'shift' in self._modifiers

    def has_modifier(self):
        return len(self._modifiers) > 0

    def has_text(self):
        return self._text is not None

    def get_text(self):
        return self._text

    def is_shift_key(self):
        return self._key == 'shift' or \
            self._key == 'lshift' or \
            self._key == 'rshift'

    def is_cursor_key(self):
        return self._key in ['up', 'left', 'right', 'down']

    def is_home_key(self):
        return self._key in ['home']

    def is_end_key(self):
        return self._key in ['end']

    def is_pageup_key(self):
        return self._key == 'pageup'

    def is_pagedown_key(self):
        return self._key == 'pagedow'

    def is_insert_key(self):
        return self._key == 'insert'

    def is_delete_key(self):
        return self._key == 'delete'

    def is_enter_key(self):
        return self._key == 'enter'

    def is_backspace_key(self):
        return self._key == 'backspace'

    def is_tab_key(self):
        return self._key == 'tab'

    def get_key_name(self):
        return self._key

    def get_key_code(self):
        return self._symbol
