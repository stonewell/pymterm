import os
import sys

TANGO_PALLETE = [
    '2e2e34343636',
    'cccc00000000',
    '4e4e9a9a0606',
    'c4c4a0a00000',
    '34346565a4a4',
    '757550507b7b',
    '060698989a9a',
    'd3d3d7d7cfcf',
    '555557575353',
    'efef29292929',
    '8a8ae2e23434',
    'fcfce9e94f4f',
    '72729f9fcfcf',
    'adad7f7fa8a8',
    '3434e2e2e2e2',
    'eeeeeeeeecec',
    '4c4c4c4c4c4c',
    'a8a830303030',
    '202088882020',
    'a8a888880000',
    '555555559898',
    '888830308888',
    '303088888888',
    'd8d8d8d8d8d8',
]

def parse_tango_color(c):
    r = int(c[:4][:2], 16)
    g = int(c[4:8][:2], 16)
    b = int(c[8:][:2], 16)

    return [r, g, b, 0xFF]

def apply_color(cfg, color_table):
    cfg.default_foreground_color = parse_tango_color('eeeeeeeeecec')
    cfg.default_background_color = parse_tango_color('323232323232')
    cfg.default_cursor_color = cfg.default_foreground_color

    for i in range(len(TANGO_PALLETE)):
        if i < len(color_table):
            color_table[i] = parse_tango_color(TANGO_PALLETE[i])

if __name__ == '__main__':
    for i in range(len(TANGO_PALLETE)):
        r, g, b, a = parse_tango_color(TANGO_PALLETE[i])

        if i < 8:
            print '"Colour{}"="{},{},{}"'.format(6 + 2 * i, r, g, b)
        else:
            print '"Colour{}"="{},{},{}"'.format(6 + 2 * (i - 8) + 1, r, g, b)
    
    r, g, b, a = parse_tango_color('323232323232')
    print '"Colour{}"="{},{},{}"'.format(i, r, g, b)
    r, g, b, a = parse_tango_color('eeeeeeeeecec')
    print '"Colour{}"="{},{},{}"'.format(i, r, g, b)
