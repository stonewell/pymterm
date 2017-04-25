import logging
import pymterm

def handle(term, context, cap_turple):
    cap_name, increase = cap_turple

    if increase:
        for idx in range(len(context.params)):
            context.params[idx] -= 1 if context.params[idx] != 0 else 0

    mode = -1
    f_color_idx = -2
    b_color_idx = -2

    for v in context.params:
        if v == 0:
            #reset
            term.origin_pair()
        elif v >= 1 and v <= 29:
            #mode
            if mode < 0:
                mode = 0

            mode |= (1 << v)
        elif v == 39:
            #reset foreground
            f_color_idx = -1
        elif v == 49:
            #reset background
            b_color_idx = -1
        elif (v >= 30 and v <= 37) or (v >= 90 and v <= 97):
            #foreground
            f_color_idx = v % 10 + (8 if v >= 90 else 0)
        elif (v >= 40 and v <= 47) or (v >= 100 and v <= 107):
            #background
            b_color_idx = v % 10 + (8 if v >= 100 else 0)

    if pymterm.debug_log:
        logging.getLogger('set_attributes').debug('params={} mode={} f_color={} b_color={}'.format(context.params, mode, f_color_idx, b_color_idx))

    if not (mode == -1 and f_color_idx == -2 and b_color_idx == -2):
        term.set_attributes(mode, f_color_idx, b_color_idx)
