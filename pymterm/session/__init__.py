#__init__

__all__ = ['create_session']

def create_session(cfg, terminal):
    if cfg.session_type == 'pty':
        import pty_session
        return pty_session.PtySession(cfg, terminal)
    elif cfg.session_type == 'pipe':
        import pipe_session
        return pipe_session.PipeSession(cfg, terminal)
    else:
        import ssh_session
        return ssh_session.SSHSession(cfg, terminal)
