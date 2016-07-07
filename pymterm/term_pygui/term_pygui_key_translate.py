
__key_mapping = {
    'return' : 'enter',
    'up_arrow' : 'up',
    'down_arrow' : 'down',
    'left_arrow' : 'left',
    'right_arrow' : 'right',
    'page_up' : 'pageup',
    'page_down' : 'pagedown',
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
