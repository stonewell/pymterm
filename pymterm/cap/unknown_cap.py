import os
import sys

def handle(term, context, cap_turple):
    cap_name, increase_params = cap_turple
    
    if hasattr(term, cap_name):
        if increase_params:
            for idx in range(len(context.params)):
                context.params[idx] -= 1
        getattr(term, cap_name)(context)
    else:
        print 'No module named', cap_name
