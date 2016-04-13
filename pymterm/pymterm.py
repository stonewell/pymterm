import os
import sys
import argparse

import ssh.client
import session
import session_config

def args_parser():
    parser = argparse.ArgumentParser(prog='pymterm',
                                     description='a multiple tab terminal emulator in python')
    parser.add_argument('-c', '--console', action="store_true", help='start the terminal emulator in console mode', required = False)
    parser.add_argument('-s', '--session', type=str, help='name of session to use', required = False)
    parser.add_argument('-p', '--port', type=int, help='port of host to connect to', required = False)
    parser.add_argument('-l', '--log', type=str, help='logging file path', required = False)
    parser.add_argument('-t', '--term_name', type=str, help='the terminal type name', default='xterm-256color', required = False)
    parser.add_argument(metavar='user@host', type=str, help='', nargs='?', dest='conn_str')

    return parser

if __name__ == '__main__':
    args = args_parser().parse_args()

    try:
        cfg = session_config.SessionConfig(args)
    except(ValueError) as e:
        args_parser().print_help()
        sys.exit(1)
    
    session = session.Session(cfg)

    ssh.client.start_client(session, cfg)
