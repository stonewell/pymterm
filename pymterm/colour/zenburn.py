
COLOR_PALLETE = [
    '3f3f3f',
    '705050',
    '60b48a',
    'dfaf8f',
    '506070',
    'dc8cc3',
    '8cd0d3',
    'DCDCCC',

    '709080',
    'cc9393',
    '7f9f7f',
    'f0dfaf',
    '94bff3',
    'ec93d3',
    '93e0e3',
    'ffffff',
]

def parse_color(c):
    r = int(c[:2], 16)
    g = int(c[2:4], 16)
    b = int(c[4:6], 16)

    return [r, g, b, 0xFF]

def apply_color(cfg, color_table):
    cfg.default_cursor_color = parse_color(COLOR_PALLETE[-2])
    
    for i in range(len(COLOR_PALLETE)):
        if i < len(color_table):
            color_table[i] = parse_color(COLOR_PALLETE[i])
