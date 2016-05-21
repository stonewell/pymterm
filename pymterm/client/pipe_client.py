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
import subprocess

def start_client(session, cfg):
    p = None
    
    try:
        #cmd = [r'pythonw.exe', r'c:\local\winpty\run.py']
        #cmd = [r'C:\local\winpty\bin\console.exe', r'C:\local\mingw64\msys\1.0\bin\bash.exe']
        cmd = [r'C:\Users\stone\GitHub\winpty\build\winpty.exe', r'C:\local\mingw64\msys\1.0\bin\bash.exe' , '--login']
        p = Popen(cmd,
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
