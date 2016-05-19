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

from subprocess import Popen, PIPE, STDOUT

def start_client(session, cfg):
    p = None
    
    try:
        p = Popen(['C:\\local\\MinGW-32\\msys\\1.0\\bin\\bash.exe'],
                  stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=True)
        session.interactive_shell(p)
    except Exception as e:
        logging.getLogger('pipe_client').exception('pipe client caught exception:')
        try:
            if p:
                p.terminate()
                p.wait()
        except:
            pass
