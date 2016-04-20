import os
import sys

def handle(term, context, cap_turple):
    light = False
    color_idx = 0

    cap_name, increase = cap_turple

    if increase:
        for idx in range(len(context.params)):
            context.params[idx] -= 1

    if len(context.params) > 1:
        light = context.params[0] == 1
        color_idx = context.params[1] - 30
    else:
        color_idx = context.params[0] - 30

    print light, color_idx, context.params
    term.set_foreground(light, color_idx)
