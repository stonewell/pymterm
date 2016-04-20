import os
import sys

def handle(term, context, cap_turple):
    light = False
    color_idx = 0

    cap_name, increase = cap_turple

    if increase:
        for idx in range(len(context.params)):
            context.params[idx] -= 1

    mode = -1
    f_color_idx = -1
    b_color_idx = -1
    
    for v in context.params:
        if v == 0:#reset
            term.origin_pair()
        elif v >= 1 and v <= 8:
            #mode
            if mode < 0:
                mode = 0

            if v == 1:
                mode |= 1
            else:
                mode |= (1 << v)
        elif (v >= 30 and v <= 37) or (v >= 90 and v <= 97):
            #foreground
            f_color_idx = v % 10 + (8 if v >= 90 else 0)
        elif (v >= 40 and v <= 47) or (v >= 100 and v <= 107):
            #background
            b_color_idx = v % 10 + (8 if v >= 100 else 0)
    print context.params, mode, f_color_idx, b_color_idx
