import logging
import os
import select
import socket
import sys
import threading
import time
import traceback

import client.ssh_client
from session import Session

import paramiko

class SSHSession(Session):
    def __init__(self, cfg, terminal):
        super(SSHSession, self).__init__(cfg, terminal)

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

        data = []

        data.append(self.channel.recv(block_size))
        time.sleep(.001)
        while self.channel and self.channel.recv_ready():
            data.append(self.channel.recv(block_size))
            time.sleep(.001)

        return ''.join(data)

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

        logging.getLogger('ssh_session').debug('get_pty, term={}, cols={}, rows={}'.format(self.cfg.term_name, cols, rows))
        chan.get_pty(term=self.cfg.term_name, width=cols, height = rows)
        chan.invoke_shell()
        self._start_reader()

    def start(self):
        super(SSHSession, self).start()

        client.ssh_client.start_client(self, self.cfg)

    def send(self, data):
        if self.channel and not self.stopped:
            self.channel.sendall(data)

    def resize_pty(self, col = None, row = None, w = 0, h = 0):
        if not col:
            col = self.terminal.get_cols()
        if not row:
            row = self.terminal.get_rows()

        if self.channel and not self.stopped:
            self.channel.resize_pty(col, row, w, h)

    def prompt_login(self, t, username):
        self.terminal.prompt_login(t, username)

    def try_login(self, t, key_file, key_type, username, password):
        client.ssh_client.try_login(self, t, key_file, key_type, username, password)

        return t.is_authenticated()

    def prompt_password(self, action):
        self.terminal.prompt_password(action)

    def transfer_file(self, l_f, r_f, is_upload = True, callback = None):
        sftp = paramiko.SFTPClient.from_transport(self.transport)

        if is_upload:
            sftp.put(l_f, r_f, callback)
        else:
            sftp.get(r_f, l_f, callback)
