_color0         = '000d18'
_color8         = '000d18'

_color1         = 'e89393'
_color9         = 'e89393'

_color2         = '9ece9e'
_color10        = '9ece9e'

_color3         = 'f0dfaf'
_color11        = 'f0dfaf'

_color4         = '8cd0d3'
_color12        = '8cd0d3'

_color5         = 'c0bed1'
_color13        = 'c0bed1'

_color6         = 'dfaf8f'
_color14        = 'dfaf8f'

_color7         = 'efefef'
_color15        = 'efefef'

_colorBD        = 'ffcfaf'
_colorUL        = 'ccdc90'
_colorIT        = '80d4aa'

_foreground     = 'dcdccc'
_background     = '1f1f1f'
_cursorColor    = '8faf9f'


COLOR_PALLETE = [
    _color0,
    _color1,
    _color2,
    _color3,
    _color4,
    _color5,
    _color6,
    _color7,
    _color8,
    _color9,
    _color10,
    _color11,
    _color12,
    _color13,
    _color14,
    _color15,
]

def parse_color(c):
    r = int(c[:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)

    return [r, g, b, 0xFF]

def apply_color(cfg, color_table):
    cfg.default_foreground_color = parse_color(_foreground)
    cfg.default_background_color = parse_color(_background)
    cfg.default_cursor_color = parse_color(_cursorColor)
    
    for i in range(len(COLOR_PALLETE)):
        if i < len(color_table):
            color_table[i] = parse_color(COLOR_PALLETE[i])

    return True
