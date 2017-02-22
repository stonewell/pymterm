import argparse
import logging
import os
import sys

import cross_platform as platform
import session_config

def unhandled_exception(exctype, value, tb):
    logging.error('unknown error happening', exc_info=(exctype, value, tb))

sys.excepthook = unhandled_exception

def args_parser():
    parser = argparse.ArgumentParser(prog='pymterm',
                                     description='a multiple tab terminal emulator in python')
    parser.add_argument('-s', '--session', type=str, help='name of session to use', required = False)
    parser.add_argument('-p', '--port', type=int, help='port of host to connect to', required = False)
    parser.add_argument('-l', '--log', type=str, help='logging file path', required = False)
    parser.add_argument('-t', '--term_name', choices=['xterm-256color'], help='the terminal type name', default='xterm-256color', required = False)
    parser.add_argument('--color_theme', choices=['tango', 'solarized_dark', 'solarized_light', 'terminal'], help='the terminal color theme, default is tango', default='tango', required = False)
    parser.add_argument('-d', '--debug', action="store_true", help='show debug information in log file and console', required = False)
    parser.add_argument('-dd', '--debug_more', action="store_true", help='show more debug information in log file and console', required = False)
    parser.add_argument('--config', type=str, help='use the give file as config file, otherwise will find pymterm.json in save directory with pymterm.py or pymterm directory in user config directroy or parent directory of pymterm.py as config file', required = False)
    parser.add_argument('--render', type=str, choices=session_config.RENDERS, help='choose a render system', required = False)
    parser.add_argument('--font_file', type=str, default = None, help='provide a font file', required = False)
    parser.add_argument('--font_name', type=str, default = None, help='provide a font name', required = False)
    parser.add_argument('--font_size', type=int, default = None, help='given a font size', required = False)
    parser.add_argument('--dump_data', type=str, default = None, help='dump all received data to given file path', required = False)
    parser.add_argument('--load_data', type=str, default = None, help='load dumped data from give file path and use the data to fake terminal data', required = False)
    parser.add_argument('--send_env', metavar='[key=value|key]', type=str, action='append', dest='send_envs', help='send the evnviroment variables to the remote system, value should be key=value or key format', required = False)
    parser.add_argument('--use_ssh_config', metavar='[ssh config path]', type=str, nargs='?', help='use open ssh config file to do ssh connection, if no file given system default configuration file will be used', const='__pymterm_use_sys_default_config_file__', required = False)

    if not platform.is_windows():
        parser.add_argument('--session_type', choices=['ssh', 'pty'], default='ssh')
    else:
        parser.add_argument('--session_type', choices=['ssh', 'pipe'], default='ssh')

    parser.add_argument(metavar='user@host', type=str, help='', nargs='?', dest='conn_str')

    return parser

def pymterm_main():
    args = args_parser().parse_args()
    try:
        sys.argv = sys.argv[:1]
        cfg = session_config.SessionConfig(args)
    except(ValueError) as e:
        logging.exception('load configuration failed')
        args_parser().print_help()
        sys.exit(1)

    if cfg.render and cfg.render == 'console':
        from term.terminal_console import TerminalConsoleApp
        TerminalConsoleApp(cfg).start()
    elif cfg.render and cfg.render == 'kivy':
        from kivy.config import Config
        Config.set('kivy', 'exit_on_escape', 0)
        Config.set('graphics', 'height', '660')
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
    else:
        from term_pygui.term_pygui import TerminalPyGUIApp
        TerminalPyGUIApp(cfg).start()

if __name__ == '__main__':
    import locale
    locale.setlocale(locale.LC_ALL, '')
    pymterm_main()
    os._exit(0)
