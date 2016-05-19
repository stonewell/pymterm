import os
import select
import socket
import sys
import time
import traceback
import logging
import threading

import ssh.client

from session import Session

class SSHSession(Session):
    def __init__(self, cfg, terminal):
        Session.__init__(self, cfg, terminal)
        
        self.sock = None
        self.channel = None
        self.transport = None

    def _connect(self):
        username = self.cfg.username
        hostname = self.cfg.hostname
        port = self.cfg.port

        # now connect
        try:
            self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((hostname, port))

            return sock
        except Exception as e:
            logging.getLogger('session').exception("connect to %s@%s:%d failed." % (username, hostname, port))
            self.report_error("connect to %s@%s:%d failed." % (username, hostname, port))

        return None

    def _read_data(self, block_size = 4096):
        if not self.channel:
            return None

        return self.channel.recv(block_size)

    def _stop_reader(self):
        if self.channel:
            self.channel.close()
            self.channel = None

        if self.transport:
            self.transport.close()
            self.transport = None

        if self.sock:
            self.sock.close()
            self.sock = None
            
    def interactive_shell(self, transport):
        self.transport = transport
        self.channel = chan = transport.open_session()

        cols = self.terminal.get_cols()
        rows = self.terminal.get_rows()
        
        chan.get_pty(term=self.cfg.term_name, width=cols, height = rows)
        chan.invoke_shell()
        self._start_reader()

    def start(self):
        super(SSHSession, self).start()
        
        ssh.client.start_client(self, self.cfg)

    def send(self, data):
        if self.channel and not self.stopped:
            self.channel.send(data)

    def resize_pty(self, col, row, w, h):
        if self.channel and not self.stopped:
            self.channel.resize_pty(col, row, w, h)
