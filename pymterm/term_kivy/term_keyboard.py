import os
import sys

def translate_key(term, keycode, text, modifiers):
    result = []
    handled = False
    code, key = keycode

    if 'alt' in modifiers and text:
        #alt + key, send \E and let system do the text stuff
        result.append('\x1B')

    if ('ctrl' in modifiers) and text:
        #take care of the control sequence
        c = text[0]
        handled = True
        if (c >= 'a' and c <= 'z'):
            result.append(chr(ord(c) - ord('a') + 1))
        elif c>= '[' and c <= ']':
            result.append(chr(ord(c) - ord('[') + 27))
        elif c == '6':
            result.append(chr(ord('^') - ord('[') + 27))
        elif c == '-':
            result.append(chr(ord('_') - ord('[') + 27))
        else:
            handled = False

        if handled:
            return (''.join(result), True)

    #arrow
    if key in ['up', 'left', 'right', 'down', 'home', 'end']:
        cap_prefix = 'key_'
        if term.keypad_transmit_mode:
            cap_prefix = 'key_'
        cap_name = cap_prefix + key

        result.append(term.cap.cmds[cap_name].cap_value)
        handled = True
    elif key in ['pageup', 'pagedown', 'insert', 'delete']:
        #pageup,page down, ins, del
        m = {'pageup':'ppage', 'pagedown':'npage', 'insert':'ic', 'delete':'dc'}
        cap_name = 'key_' + m[key]
        result.append(term.cap.cmds[cap_name].cap_value)
        handled = True
    elif key == 'enter':
        if 'carriage_return' in term.cap.cmds:
            result.append(term.cap.cmds['carriage_return'].cap_value)
            handled = True
    elif key == 'backspace':
            result.append('\x7f')
            handled = True
    else:
        #numpad
        #function keys
        if 'key_' + key in term.cap.cmds:
            cap_name = 'key_' + key
            result.append(term.cap.cmds[cap_name].cap_value)
            handled = True

    #not handled and no text
    if not handled and not text:
        #todo convert keycode to bytes
        if code < 256:
            result.append(chr(code))
            handled = True

    return (''.join(result), handled)
            
        
