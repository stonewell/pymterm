import base64
from binascii import hexlify
import getpass
import os
import select
import socket
import sys
import time
import traceback
import logging

import array
import fcntl
import pty
import select
import signal
import termios
import tty
    
def start_client(session, cfg):
    master_fd = None
    
    try:
        shell = os.environ['SHELL']

        if not shell:
            shell = ['/bin/bash', '-i', '-l']
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
