
S_yellow        ='b58900'
S_orange        ='cb4b16'
S_red           ='dc322f'
S_magenta       ='d33682'
S_violet        ='6c71c4'
S_blue          ='268bd2'
S_cyan          ='2aa198'
S_green         ='859900'

S_base03        ='002b36'
S_base02        ='073642'
S_base01        ='586e75'
S_base00        ='657b83'
S_base0         ='839496'
S_base1         ='93a1a1'
S_base2         ='eee8d5'
S_base3         ='fdf6e3'

COLOR_PALLETE = [
    S_base02,
    S_red,
    S_green,
    S_yellow,
    S_blue,
    S_magenta,
    S_cyan,
    S_base2,
    S_orange,
    S_base03,
    S_base01,
    S_base00,
    S_base0,
    S_violet,
    S_base1,
    S_base3
    ]

def parse_color(c):
    r = int(c[:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)

    return [r, g, b, 0xFF]

def apply_color(cfg, color_table):
    cfg.default_foreground_color = parse_color(S_base0)
    cfg.default_background_color = parse_color(S_base03)
    cfg.default_cursor_color = parse_color(S_base1)

    for i in range(len(COLOR_PALLETE)):
        if i < len(color_table):
            color_table[i] = parse_color(COLOR_PALLETE[i])
     
