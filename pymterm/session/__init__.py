#__init__

__all__ = ['create_session']

def create_session(cfg, terminal):
    if cfg.session_type == 'local':
        import pty_session
        return pty_session.PtySession(cfg, terminal)
    else:
        import ssh_session
        return ssh_session.SSHSession(cfg, terminal)
