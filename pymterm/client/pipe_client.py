import base64
from binascii import hexlify
import getpass
import logging
import os
import select
import socket
from subprocess import Popen, PIPE, STDOUT
import sys
import time
import traceback


def start_client(session, cfg):
    p = None
    
    try:
        if cfg.config and 'pipe-config' in cfg.config and 'default-shell' in cfg.config['pipe-config']:
            cmd = cfg.config['pipe-config']['default-shell']
        else:
            raise ValueError('no default shell configed for pipe mode')

        p = Popen(cmd,
                  stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=False)
        session.interactive_shell(p)
    except Exception as e:
        logging.getLogger('pipe_client').exception('pipe client caught exception:')
        try:
            if p:
                p.terminate()
                p.wait()
        except:
            pass
