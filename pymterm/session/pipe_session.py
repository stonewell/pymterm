import os
import select
import socket
import sys
import time
import traceback
import logging
import threading

import client.pipe_client

from session import Session

class PipeSession(Session):
    def __init__(self, cfg, terminal):
        super(PipeSession, self).__init__(cfg, terminal)
        
        self.p = None
        self.in_pipe = None
        self.out_pipe = None

    def _read_data(self, block_size = 4096):
        if not self.p:
            return None

        d = self.out_pipe.read(1)
        return d

    def _stop_reader(self):
        if self.p:
            self.in_pipe.close()
            self.out_pipe.close()
            self.p.terminate()
            self.p.wait()
            self.p = None

    def interactive_shell(self, p):
        self.p = p
        self.in_pipe = p.stdin
        self.out_pipe = p.stdout

        self.resize_pty()
        
        self._start_reader()
        
    def start(self):
        super(PipeSession, self).start()
        
        client.pipe_client.start_client(self, self.cfg)

    def send(self, data):
        if self.p and not self.stopped:
            in_pipe = self.in_pipe

            in_pipe.write(data)

    def resize_pty(self, col = None, row = None, w = 0, h = 0):
        pass
