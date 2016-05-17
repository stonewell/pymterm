import base64
from binascii import hexlify
import getpass
import os
import select
import socket
import sys
import time
import traceback
from paramiko.py3compat import input
import logging

import paramiko

def start_client(session, cfg):
    username = cfg.username
    hostname = cfg.hostname
    port = cfg.port

    try:
        sock = session.connect()

        if not sock:
            return
    
        t = paramiko.Transport(sock)
        try:
            t.start_client()
        except paramiko.SSHException:
            session.report_error('*** SSH negotiation failed.')
            return

        try:
            keys = paramiko.util.load_host_keys(os.path.expanduser('~/.ssh/known_hosts'))
        except IOError:
            try:
                keys = paramiko.util.load_host_keys(os.path.expanduser('~/ssh/known_hosts'))
            except IOError:
                session.report_error('*** Unable to open host keys file')
                keys = {}

        # check server's host key -- this is important.
        key = t.get_remote_server_key()
        if hostname not in keys:
            session.report_error('*** WARNING: Unknown host key!')
        elif key.get_name() not in keys[hostname]:
            session.report_error('*** WARNING: Unknown host key!')
        elif keys[hostname][key.get_name()] != key:
            session.report_error('*** WARNING: Host key has changed!!!')
        else:
            session.report_error('*** Host key OK.')

        # get username
        if username == '':
            default_username = getpass.getuser()
            username = input('Username [%s]: ' % default_username)
            if len(username) == 0:
                username = default_username

        agent_auth(t, username)
        if not t.is_authenticated():
            manual_auth(t, username, hostname)
        if not t.is_authenticated():
            logging.getLogger('ssh_client').debug('*** Authentication failed. :(')
            t.close()
            sys.exit(1)

        session.interactive_shell(t)
    except Exception as e:
        logging.getLogger('ssh_client').exception('ssh client caught exception:')
        try:
            t.close()
        except:
            pass
        sys.exit(1)

