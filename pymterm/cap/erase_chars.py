import logging

def handle(term, context, cap_turple):
    cap_name, increase = cap_turple

    if increase:
        for idx in range(len(context.params)):
            context.params[idx] -= 1 if context.params[idx] != 0 else 0

    term.delete_chars(context.params[0], True) #overwirte only
    logging.error('erase chars:{}, {}'.format(term.get_cursor(), context.params[0]))

