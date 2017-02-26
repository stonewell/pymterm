import logging
import os
import pty


def start_client(session, cfg):
    master_fd = None
    
    try:
        shell = os.environ['SHELL']

        if not shell:
            shell = ['/bin/bash', '-i', '-l']

            if cfg.config and 'pty-config' in cfg.config and 'default-shell' in cfg.config['pty-config']:
                shell = cfg.config['pty-config']['default-shell']
        else:
            shell = [shell]

        pid, master_fd = pty.fork()
        
        if pid == pty.CHILD:
            os.execlp(shell[0], *shell)

        session.interactive_shell(master_fd)
    except:
        logging.getLogger('pty_client').exception('pty client caught exception:')
        try:
            if master_fd:
                os.close(master_fd)
        except:
            pass
