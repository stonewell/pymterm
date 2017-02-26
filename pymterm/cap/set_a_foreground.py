import logging

def handle(term, context, cap_turple):
    light = False
    color_idx = 0

    cap_name, increase = cap_turple

    if increase:
        for idx in range(len(context.params)):
            context.params[idx] -= 1 if context.params[idx] != 0 else 0

    if len(context.params) == 2:
        light = context.params[0] == 1
        color_idx = context.params[1] - 30
    elif len(context.params) == 3 and context.params[0] == 38 and context.params[1] == 5:
        color_idx = context.params[2]
    else:
        color_idx = context.params[0] - 30

    logging.getLogger('set_a_foreground').debug('light={}, color_index={}, params={}'.format(light, color_idx, context.params))
    term.set_foreground(light, color_idx)
