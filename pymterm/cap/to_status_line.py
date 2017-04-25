import logging
import pymterm

def handle(term, context, cap_turple):
    if pymterm.debug_log:
        logging.getLogger('cap').debug('status line:{}'.format(context.params))
        
    mode = context.params[0] if len(context.params) > 0 else 0
    term.enter_status_line(mode, True)
