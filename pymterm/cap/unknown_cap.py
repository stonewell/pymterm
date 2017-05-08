import logging


def handle(term, context, cap_turple):
    cap_name, increase_params = cap_turple
    
    if hasattr(term, cap_name):
        if increase_params:
            for idx in range(len(context.params)):
                context.params[idx] -= 1 if context.params[idx] != 0 else 0
        getattr(term, cap_name)(context)
    else:
        logging.error('No module named:{}, params:{}'.format(cap_name, context.params))
