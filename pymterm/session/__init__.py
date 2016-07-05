#__init__
import logging


__all__ = ['create_session']

def create_session(cfg, terminal):
    logging.getLogger('create_session').debug('session_type:{}'.format(cfg.session_type))
    
    if cfg.session_type == 'pty':
        import pty_session
        return pty_session.PtySession(cfg, terminal)
    elif cfg.session_type == 'pipe':
        import pipe_session
        return pipe_session.PipeSession(cfg, terminal)
    else:
        import ssh_session
        return ssh_session.SSHSession(cfg, terminal)
