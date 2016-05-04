#!/usr/bin/env python

# Copyright (C) 2003-2007  Robey Pointer <robeypointer@gmail.com>
#
# This file is part of paramiko.
#
# Paramiko is free software; you can redistribute it and/or modify it under the
# terms of the GNU Lesser General Public License as published by the Free
# Software Foundation; either version 2.1 of the License, or (at your option)
# any later version.
#
# Paramiko is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Paramiko; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA.


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

def agent_auth(transport, username):
    """
    Attempt to authenticate to the given transport using any of the private
    keys available from an SSH agent.
    """
    
    agent = paramiko.Agent()
    agent_keys = agent.get_keys()
    if len(agent_keys) == 0:
        return
        
    for key in agent_keys:
        logging.getLogger('ssh_client').debug('Trying ssh-agent key %s' % hexlify(key.get_fingerprint()))
        try:
            transport.auth_publickey(username, key)
            logging.getLogger('ssh_client').debug('... authentication success!')
            return
        except paramiko.SSHException:
            logging.getLogger('ssh_client').debug('authentication fail.')


def manual_auth(t, username, hostname):
    default_auth = 'p'
    auth = input('Auth by (p)assword, (r)sa key, or (d)ss key? [%s] ' % default_auth)
    if len(auth) == 0:
        auth = default_auth

    if auth == 'r':
        default_path = os.path.join(os.environ['HOME'], '.ssh', 'id_rsa')
        path = input('RSA key [%s]: ' % default_path)
        if len(path) == 0:
            path = default_path
        try:
            key = paramiko.RSAKey.from_private_key_file(path)
        except paramiko.PasswordRequiredException:
            password = getpass.getpass('RSA key password: ')
            key = paramiko.RSAKey.from_private_key_file(path, password)
        t.auth_publickey(username, key)
    elif auth == 'd':
        default_path = os.path.join(os.environ['HOME'], '.ssh', 'id_dsa')
        path = input('DSS key [%s]: ' % default_path)
        if len(path) == 0:
            path = default_path
        try:
            key = paramiko.DSSKey.from_private_key_file(path)
        except paramiko.PasswordRequiredException:
            password = getpass.getpass('DSS key password: ')
            key = paramiko.DSSKey.from_private_key_file(path, password)
        t.auth_publickey(username, key)
    else:
        pw = getpass.getpass('Password for %s@%s: ' % (username, hostname))
        t.auth_password(username, pw)


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

        chan = t.open_session()
        session.interactive_shell(chan)

        return (t, chan)
    except Exception as e:
        logging.getLogger('ssh_client').exception('ssh client caught exception:')
        try:
            t.close()
        except:
            pass
        sys.exit(1)

