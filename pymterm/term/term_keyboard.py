import logging


def translate_key(term, key_state):
    result = []
    handled = False

    if key_state.has_alt() and key_state.has_text():
        # alt + key, send \E and let system do the text stuff
        result.append('\x1B')
        result.append(key_state.get_text())
        handled = True

    if key_state.has_ctrl() and key_state.has_text():
        # take care of the control sequence
        c = key_state.get_text()[0]
        handled = True
        if (c >= 'a' and c <= 'z'):
            result.append(chr(ord(c) - ord('a') + 1))
        elif c >= '[' and c <= ']':
            result.append(chr(ord(c) - ord('[') + 27))
        elif c == '6':
            result.append(chr(ord('^') - ord('[') + 27))
        elif c == '-':
            result.append(chr(ord('_') - ord('[') + 27))
        else:
            handled = False

        if handled:
            return (''.join(result), True)

    # arrow
    if key_state.is_cursor_key() \
       or key_state.is_home_key() or key_state.is_end_key():
        cap_prefix = 'key_'
        if term.keypad_transmit_mode:
            cap_prefix = 'key_'
        cap_name = cap_prefix + key_state.get_key_name()

        result.append(term.cap.cmds[cap_name].cap_value)
        handled = True
    elif key_state.is_pageup_key() or key_state.is_pagedown_key() \
            or key_state.is_insert_key() or key_state.is_delete_key():
        # pageup,page down, ins, del
        m = {'pageup': 'ppage',
             'pagedown': 'npage', 'insert': 'ic', 'delete': 'dc'}
        cap_name = 'key_' + m[key_state.get_key_name()]
        result.append(term.cap.cmds[cap_name].cap_value)
        handled = True
    elif key_state.is_enter_key():
        if 'carriage_return' in term.cap.cmds:
            result.append(term.cap.cmds['carriage_return'].cap_value)
            handled = True
    elif key_state.is_backspace_key():
            result.append('\x7f')
            handled = True
    elif key_state.is_tab_key():
        if 'tab' in term.cap.cmds:
            result.append(term.cap.cmds['tab'].cap_value)
            handled = True
    else:
        # numpad
        # function keys
        cap_name = 'key_' + key_state.get_key_name()
        if cap_name in term.cap.cmds:
            result.append(term.cap.cmds[cap_name].cap_value)
            handled = True

    # do not translate single Alt
    if len(result) == 1 and result[0] == '\x1b':
        logging.getLogger('term_keyboard').debug(
            'reset single alt key handled to False')
        handled = False

    return (''.join(result), handled)
