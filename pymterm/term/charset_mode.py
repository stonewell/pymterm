# DEC Special Character and Line Drawing Set.  VT100 and higher (per XTerm docs).
line_drawing_map = [
    0x25c6,  # ` => diamond
    0x2592,  # a => checkerboard
    0x2409,  # b => HT symbol
    0x240c,  # c => FF symbol
    0x240d,  # d => CR symbol
    0x240a,  # e => LF symbol
    0x00b0,  # f => degree
    0x00b1,  # g => plus/minus
    0x2424,  # h => NL symbol
    0x240b,  # i => VT symbol
    0x2518,  # j => downright corner
    0x2510,  # k => upright corner
    0x250c,  # l => upleft corner
    0x2514,  # m => downleft corner
    0x253c,  # n => cross
    0x23ba,  # o => scan line 1/9
    0x23bb,  # p => scan line 3/9
    0x2500,  # q => horizontal line (also scan line 5/9)
    0x23bc,  # r => scan line 7/9
    0x23bd,  # s => scan line 9/9
    0x251c,  # t => left t
    0x2524,  # u => right t
    0x2534,  # v => bottom t
    0x252c,  # w => top t
    0x2502,  # x => vertical line
    0x2264,  # y => <=
    0x2265,  # z => >=
    0x03c0,  # { => pi
    0x2260,  # | => not equal
    0x00a3,  # } => pound currency sign
    0x00b7,  # ~ => bullet
]

def translate_char(c):
    if ord(c) >= 96 and ord(c) < 126:
        return unichr(line_drawing_map[ord(c) - 96])
    return c

def translate_char_british(c):
    if c == '#':
        return unichr(0x00a3)
