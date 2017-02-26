from binascii import hexlify
import getpass
import logging
import os

import paramiko

def agent_auth(transport, username):
    """
    Attempt to authenticate to the given transport using any of the private
    keys available from an SSH agent.
    """

    agent = paramiko.Agent()
    agent_keys = agent.get_keys()
    if len(agent_keys) == 0:
        logging.getLogger('ssh_client').debug('no agent keys found!')
        return

    for key in agent_keys:
        logging.getLogger('ssh_client').debug('Trying ssh-agent key %s' % hexlify(key.get_fingerprint()))
        try:
            transport.auth_publickey(username, key)
            logging.getLogger('ssh_client').debug('... authentication success!')
            return
        except paramiko.SSHException:
            logging.getLogger('ssh_client').debug('authentication fail.')

class KeyAuthAction(object):
    def __init__(self, session, transport, key_file, key_type, username, next_action = None, password = None):
        self.session = session
        self.transport = transport
        self.key_file = key_file
        self.key_type = key_type
        self.username = username
        self.next_action = next_action
        self.password = password

    def execute(self):
        key = None

        try:
            if self.password:
                if self.key_type == 'RSA':
                    key = paramiko.RSAKey.from_private_key_file(self.key_file, self.password)
                else:
                    key = paramiko.DSSKey.from_private_key_file(self.key_file, self.password)
            else:
                if self.key_type == 'RSA':
                    key = paramiko.RSAKey.from_private_key_file(self.key_file)
                else:
                    key = paramiko.DSSKey.from_private_key_file(self.key_file)
        except:
            self.session.prompt_password(self)
            return

        if key:
            try:
                self.transport.auth_publickey(self.username, key)
            except paramiko.SSHException:
                pass

        self._post_execute()

    def _post_execute(self):
        if self.transport.is_authenticated():
            self.session.interactive_shell(self.transport)
        elif self.next_action:
            self.next_action.execute()
        else:
            self.session.report_error('Authentication failed.')

    def get_pass_desc(self):
        return "key file " + self.key_file + " 's password:"

class PromptLoginAction(object):
    def __init__(self, session, transport, username):
        self.session = session
        self.transport = transport
        self.username = username

    def execute(self):
        self.session.prompt_login(self.transport, self.username)

def get_user_ssh_dir():
    ssh_dir = os.path.expanduser('~/.ssh')

    if os.path.isdir(ssh_dir):
        return ssh_dir

    ssh_dir = os.path.expanduser('~/ssh')
    
    return ssh_dir if os.path.isdir(ssh_dir) else None

def build_auth_actions(session, t, username):
    key_files = {'id_rsa':'RSA', 'id_dsa':'DSS'}
    root_action = None
    cur_action = None

    ssh_dir = get_user_ssh_dir()
    
    for key_file in key_files:
        if not ssh_dir:
            break
        
        path = os.path.join(ssh_dir, key_file)

        if not os.path.exists(path):
            continue

        action = KeyAuthAction(session, t, path, key_files[key_file], username)

        if cur_action:
            cur_action.next_action = action
        else:
            root_action = cur_action = action

        cur_action = action

    action = PromptLoginAction(session, t, username)
    if cur_action:
        cur_action.next_action = action
    else:
        root_action = action

    return root_action

def start_client(session, cfg):
    username = cfg.username
    hostname = cfg.hostname

    try:
        sock = session._connect()

        if not sock:
            return

        t = paramiko.Transport(sock)
        try:
            t.start_client()
        except paramiko.SSHException:
            session.report_error('*** SSH negotiation failed.')
            return

        ssh_dir = get_user_ssh_dir()
        if ssh_dir:
            try:
                keys_file = os.path.join(ssh_dir, 'known_hosts')
                keys = paramiko.util.load_host_keys(keys_file) if os.path.isfile(keys_file) else {}
            except IOError:
                logging.getLogger('ssh_client').exception('unable to open host keys file:{}'.format(os.path.join(ssh_dir, 'known_hosts')))
                session.report_error('*** Unable to open host keys file')
                keys = {}
        else:
            keys = {}

        # check server's host key -- this is important.
        key = t.get_remote_server_key()
        if hostname not in keys:
            logging.getLogger('ssh_client').warn('*** WARNING: Unknown host key, hostname is not in the list!')
        elif key.get_name() not in keys[hostname]:
            logging.getLogger('ssh_client').warn('*** WARNING: Unknown host key, key is not found in host keys!')
        elif keys[hostname][key.get_name()] != key:
            logging.getLogger('ssh_client').warn('*** WARNING: Host key has changed!!!')

        # get username
        if username == '':
            username = getpass.getuser()

        agent_auth(t, username)
        if not t.is_authenticated():
            if cfg.password:
                try:
                    t.auth_password(username, cfg.password)
                except paramiko.SSHException:
                    pass

            if not t.is_authenticated():
                action = build_auth_actions(session, t, username)
                action.execute()
                return

        if not t.is_authenticated():
            session.report_error('Authentication failed.')
            t.close()
            return

        session.interactive_shell(t)
    except Exception as e:
        logging.getLogger('ssh_client').exception('ssh client caught exception:')

        session.report_error(str(e))

        try:
            t.close()
        except:
            pass

class PassAuthAction(KeyAuthAction):
    def __init__(self, session, transport, username, password):
        super(PassAuthAction, self).__init__(session, transport, None, None, username, None, password)
        self.prompt_pass = True

    def execute(self):
        try:
            self.transport.auth_password(self.username, self.password)
        except paramiko.SSHException:
            pass

        if not self.transport.is_authenticated() and self.prompt_pass:
            self.session.prompt_password(self)
            return

        self._post_execute()

    def get_pass_desc(self):
        return self.username + " 's password:"

def try_login(session, t, key_file, key_type, username, password):
    root_action = None

    if os.path.exists(key_file):
        root_action = KeyAuthAction(session, t, key_file, key_type, username)

    action = PassAuthAction(session, t, username, password)
    action.prompt_pass = False

    if root_action:
        root_action.next_action = action
    else:
        root_action = action

    root_action.execute()
