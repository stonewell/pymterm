import os
import sys
import argparse

import session_config

from term.terminal_console import TerminalConsoleApp

def args_parser():
    parser = argparse.ArgumentParser(prog='pymterm',
                                     description='a multiple tab terminal emulator in python')
    parser.add_argument('-c', '--console', action="store_true", help='start the terminal emulator in console mode', required = False)
    parser.add_argument('-s', '--session', type=str, help='name of session to use', required = False)
    parser.add_argument('-p', '--port', type=int, help='port of host to connect to', required = False)
    parser.add_argument('-l', '--log', type=str, help='logging file path', required = False)
    parser.add_argument('-t', '--term_name', type=str, help='the terminal type name', default='xterm-256color', required = False)
    parser.add_argument('--color_theme', type=str, help='the terminal color theme', default='tango', required = False)
    parser.add_argument(metavar='user@host', type=str, help='', nargs='?', dest='conn_str')

    return parser

if __name__ == '__main__':
    args = args_parser().parse_args()

    try:
        sys.argv = sys.argv[:1]
        cfg = session_config.SessionConfig(args)
    except(ValueError) as e:
        args_parser().print_help()
        sys.exit(1)

    if cfg.console:
	    TerminalConsoleApp(cfg).start()
    else:
        from term_kivy.term_kivy import TerminalKivyApp
        TerminalKivyApp(cfg).start()
