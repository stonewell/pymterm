import os
import sys
import argparse
import logging

import session_config

def args_parser():
    parser = argparse.ArgumentParser(prog='pymterm',
                                     description='a multiple tab terminal emulator in python')
    parser.add_argument('-c', '--console', action="store_true", help='start the terminal emulator in console mode', required = False)
    parser.add_argument('-s', '--session', type=str, help='name of session to use', required = False)
    parser.add_argument('-p', '--port', type=int, help='port of host to connect to', required = False)
    parser.add_argument('-l', '--log', type=str, help='logging file path', required = False)
    parser.add_argument('-t', '--term_name', type=str, help='the terminal type name', default='xterm-256color', required = False)
    parser.add_argument('--color_theme', type=str, help='the terminal color theme', default='tango', required = False)
    parser.add_argument('-d', '--debug', action="store_true", help='show debug information in log file and console', required = False)
    parser.add_argument('-dd', '--debug_more', action="store_true", help='show more debug information in log file and console', required = False)
    parser.add_argument(metavar='user@host', type=str, help='', nargs='?', dest='conn_str')

    return parser

if __name__ == '__main__':
    args = args_parser().parse_args()

    try:
        sys.argv = sys.argv[:1]
        cfg = session_config.SessionConfig(args)
    except(ValueError) as e:
        logging.exception('load configuration failed')
        args_parser().print_help()
        sys.exit(1)

    if cfg.console:
        from term.terminal_console import TerminalConsoleApp
        TerminalConsoleApp(cfg).start()
    else:
        os.environ['KIVY_NO_FILELOG'] = ''
        os.environ['KIVY_NO_CONSOLELOG'] = ''
        from kivy.core.text import LabelBase

        FONTS = {'WenQuanYi':'wqy-microhei-mono.ttf',
                 'YaHei Consolas':'YaHei Consolas Hybrid 1.12.ttf',
                 'NotoSans':'NotoSansMonoCJKsc-Regular.otf'}
        for f_name in FONTS:
            font_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'fonts', FONTS[f_name]) 
            logging.getLogger('term_kivy_app').debug(font_path)
        
            LabelBase.register(f_name, font_path)
        
        from term_kivy.term_kivy import TerminalKivyApp
        from kivy.logger import Logger
        #Logger.setLevel(logging.ERROR)
        
        TerminalKivyApp(cfg).start()
