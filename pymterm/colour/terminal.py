import os
import sys


foreground = 'c5c8c6'
background = '1d1f21'
cursorColor = 'c5c8c6'

color0 = '282a2e'
color8 = '373b41'

# red'
color1 = 'a54242'
color9 = 'cc6666'

# green'
color2 = '8c9440'
color10 = 'b5bd68'

# yellow'
color3 = 'de935f'
color11 = 'f0c674'

# blue'
color4 = '5f819d'
color12 = '81a2be'

# magenta'
color5 = '85678f'
color13 = 'b294bb'

# cyan'
color6 = '5e8d87'
color14 = '8abeb7'

# white'
color7 = '707880'
color15 = 'c5c8c6'

def parse_color(c):
    r = int(c[:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)

    return [r, g, b, 0xFF]

def apply_color(cfg, color_table):
    cfg.default_foreground_color = parse_color(foreground)
    cfg.default_background_color = parse_color(background)
    cfg.default_cursor_color = parse_color(cursorColor)

    for i in range(16):
        if i < len(color_table):
            color_table[i] = parse_color(globals()['color' + str(i)])
     
