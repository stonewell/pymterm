import logging
from subprocess import Popen, PIPE, STDOUT


def start_client(session, cfg):
    p = None
    
    try:
        if cfg.config and 'pipe-config' in cfg.config and 'default-shell' in cfg.config['pipe-config']:
            cmd = cfg.config['pipe-config']['default-shell']
        else:
            raise ValueError('no default shell configed for pipe mode')

        p = Popen(cmd,
                  stdin=PIPE, stdout=PIPE, stderr=STDOUT, shell=False)
        session.interactive_shell(p)
    except:
        logging.getLogger('pipe_client').exception('pipe client caught exception:')
        try:
            if p:
                p.terminate()
                p.wait()
        except:
            pass
