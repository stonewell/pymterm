import logging
import os
import select
import socket
import sys
import threading
import time
import traceback
import stat

import client.ssh_client
from session import Session

import paramiko

class SSHSession(Session):
    def __init__(self, cfg, terminal):
        super(SSHSession, self).__init__(cfg, terminal)

        self.sock = None
        self.channel = None
        self.transport = None
        self.status_cmd_event = threading.Event()
        self.status_cmd_event.set()
        self.status_lines = {}

    def _connect(self):
        username = self.cfg.username
        hostname = self.cfg.hostname
        port = self.cfg.port

        # now connect
        try:
            envs, proxy_command = self.cfg.get_conn_info()

            if proxy_command:
                self.sock = paramiko.ProxyCommand(proxy_command)
            else:
                self.sock = sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((hostname, port))

            return self.sock
        except Exception as e:
            logging.getLogger('session').exception("connect to %s@%s:%d failed." % (username, hostname, port))
            self.report_error("connect to %s@%s:%d failed." % (username, hostname, port))

        return None

    def _read_data(self, block_size = 4096):
        if not self.channel:
            return None

        data = []

        def wait():
            if not (self.channel and self.channel.recv_ready()):
                time.sleep(.001)

        data.append(self.channel.recv(block_size))
        #wait()
        while self.channel and self.channel.recv_ready():
            data.append(self.channel.recv(block_size))
            #wait()

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

        envs, proxy_command = self.cfg.get_conn_info()

        logging.getLogger('ssh_session').error('using proxy_command:{}, env:{}'.format(proxy_command, envs))

        for key in envs:
            chan.set_environment_variable(key, envs[key])

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

    def on_status_line(self, mode, status_line):
        if status_line.startswith('PYMTERM_STATUS_HOME_PWD='):
            self.status_lines['PYMTERM_STATUS_HOME_PWD'] = status_line[len('PYMTERM_STATUS_HOME_PWD='):]

        self.status_cmd_event.set()

    def get_home_and_pwd(self):
        if not self.channel:
            return (None, None)

        self.status_cmd_event.clear()
        self.channel.sendall(r'echo -ne "\033]0;PYMTERM_STATUS_HOME_PWD=${HOME};${PWD}\007"' + '\r')

        self.status_cmd_event.wait(5)

        if self.status_cmd_event.is_set() and 'PYMTERM_STATUS_HOME_PWD' in self.status_lines:
            return self.status_lines['PYMTERM_STATUS_HOME_PWD'].split(';')

        return (None, None)

    def normalize_remote_file_path(self, p, r_home = None, r_pwd = None):
        if os.path.isabs(p):
            return p

        home, pwd = r_home, r_pwd

        if not home or not pwd:
            home, pwd = self.get_home_and_pwd()
            home = home.decode('utf-8') if home else None
            pwd = pwd.decode('utf-8') if pwd else None

        logging.getLogger('session').debug(u'sftp get home:{} and cwd:{}'.format(home, pwd))

        if home and p.startswith('~/'):
            p = '/'.join([home, p[2:]])

        if pwd and not os.path.isabs(p):
            p = '/'.join([pwd, p])

        return p

    def transfer_file(self, l_f, r_f, r_home = None, r_pwd = None, is_upload = True, callback = None):
        try:
            r_f = self.normalize_remote_file_path(r_f, r_home, r_pwd)

            with paramiko.SFTPClient.from_transport(self.transport) as sftp:
                try:
                    r_stat = sftp.stat(r_f)

                    if not is_upload:
                        while True:
                            if stat.S_ISDIR(r_stat.st_mode):
                                self.report_error(u'unable to download dir:{}'.format(r_f))
                                return
                            elif stat.S_ISLNK(r_stat.st_mode):
                                r_f = sftp.normalize(r_f)
                                r_stat = sftp.state(r_f)
                            else:
                                break
                    else:
                        while True:
                            if stat.S_ISDIR(r_stat.st_mode):
                                r_f = '/'.join([r_f, os.path.basename(l_f)])
                                r_stat = sftp.state(r_f)
                            elif stat.S_ISLNK(r_stat.st_mode):
                                r_f = sftp.normalize(r_f)
                                r_stat = sftp.state(r_f)
                            elif self.terminal.ask_user(u'overwirte remote file:{}?'.format(r_f)) != 1:
                                return
                            else:
                                break
                except:
                    logging.getLogger('session').exception(u'stat remote file failed:local={}, remote={}, upload={}'.format(l_f, r_f, is_upload));
                    if not is_upload:
                        self.report_error('transfer file failed:{}'.format(sys.exc_info()[0]))
                        return

                if is_upload:
                    sftp.put(l_f, r_f, callback)
                else:
                    sftp.get(r_f, l_f, callback)
        except:
            logging.getLogger('session').exception(u'transfer file failed:local={}, remote={}, upload={}'.format(l_f, r_f, is_upload));
            self.report_error('transfer file failed:{}'.format(sys.exc_info()[0]))
