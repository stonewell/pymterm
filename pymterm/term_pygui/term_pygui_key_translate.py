import logging
import string
import pymterm

__key_mapping = {
    'return': 'enter',
    'up_arrow': 'up',
    'down_arrow': 'down',
    'left_arrow': 'left',
    'right_arrow': 'right',
    'page_up': 'pageup',
    'page_down': 'pagedown',
}


def translate_key(e):
    if len(e.key) > 0:
        return __key_mapping[e.key] if e.key in __key_mapping else e.key
    else:
        if e.char == '\x08':
            return 'backspace'
        elif e.char == '\t':
            return 'tab'
        else:
            return e.key


class KeyState(object):
    def __init__(self, e):
        key = translate_key(e)

        keycode = (e.char, key)
        text = key if len(key) == 1 and key[0] in string.printable \
            else e.char if len(e.char) > 0 else None
        modifiers = []

        if e.option:
            modifiers.append('alt')
        if e.control:
            modifiers.append('ctrl')
        if e.shift:
            modifiers.append('shift')

        if pymterm.debug_log:
            logging.getLogger('term_pygui').debug('view key_down:{}'.format(e))
            logging.getLogger('term_pygui').debug(
                'view key_down:{}, {}, {}'.format(keycode, text, modifiers))

        self._key = key
        self._text = text
        self._modifiers = modifiers
        self._event = e

    def has_alt(self):
        return 'alt' in self._modifiers \
            or 'alt_L' in self._modifiers \
            or 'alt_R' in self._modifiers

    def has_ctrl(self):
        return 'ctrl' in self._modifiers \
            or 'ctrl_L' in self._modifiers \
            or 'ctrl_R' in self._modifiers

    def has_shift(self):
        return 'shift' in self._modifiers \
            or 'shift_L' in self._modifiers \
            or 'shift_R' in self._modifiers

    def has_modifier(self):
        return len(self._modifiers) > 0

    def has_text(self):
        return self._text is not None

    def get_text(self):
        return self._text

    def is_shift_key(self):
        return self._key == 'shift' or \
            self._key == 'shift_L' or \
            self._key == 'shift_R'

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
        return self._event.char
