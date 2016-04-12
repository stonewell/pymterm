import os
import sys

import ssh.client
import session
import session_config

if __name__ == '__main__':
    cfg = session_config.SessionConfig()
    
    session = session.Session(cfg)

    ssh.client.start_client(session, cfg)
