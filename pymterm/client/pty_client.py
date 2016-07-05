import base64
from binascii import hexlify
import getpass
import logging
import os
import pty
import select
import socket
import sys
import time
import traceback


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
        master_fd = master_fd
        
        if pid == pty.CHILD:
            os.execlp(shell[0], *shell)

        session.interactive_shell(master_fd)
    except Exception as e:
        logging.getLogger('pty_client').exception('pty client caught exception:')
        try:
            if master_fd:
                os.close(master_fd)
        except:
            pass
