#__init__
import ssh_session

__all__ = ['create_session']

def create_session(cfg, terminal):
    if cfg.session_type == 'ssh':
        return ssh_session.SSHSession(cfg, terminal)
