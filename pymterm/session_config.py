import os
import sys
import getpass
import logging
import logging.config

def get_default_user():
	return getpass.getuser()

class SessionConfig:
    def __init__(self, args):
        self.term_name = args.term_name
        self.console = args.console if args.console is not None else False
        self.session_name = args.session
        self.port = args.port if args.port is not None else 22
        self.is_logging = args.log is not None
        self.log_file_path = args.log
        self.hostname = ''
        self.username = ''
        self.default_foreground_color = [0x00,0x00,0x00,0x88]
        self.default_background_color = [0xdd,0xdd,0xdd,0xFF]
        self.default_cursor_color = self.default_foreground_color
        self.color_theme = args.color_theme
        self.debug = args.debug

        if args.conn_str:
            parts = args.conn_str.split('@')

            if parts >= 2:
                self.hostname = '@'.join(parts[1:])
                self.username = parts[0]
            else:
                self.hostname = args.conn_str
                self.username = get_default_user()
        elif not self.session_name:
            if self.console:
                raise ValueError("no engouth connect information")

        #validate host and user
        if not self.session_name and (len(self.hostname) == 0 or len(self.username) == 0):
            raise ValueError("no engouth connect information")

        default_formatter = logging.Formatter(fmt='%(asctime)s %(levelname)-8s %(name)-15s %(message)s',
                                    datefmt='%Y-%m-%d %H:%M:%S')
        root_logger = logging.getLogger('')
        root_logger.setLevel(logging.WARN)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(default_formatter)
        root_logger.addHandler(console_handler)
        
        if self.is_logging or self.debug:
            root_logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

            if self.debug:
                console_handler.setLevel(logging.DEBUG)

            if self.is_logging:
                file_handler = logging.handlers.TimedRotatingFileHandler(self.log_file_path,
                                   when='D',
                                   backupCount=1,
                                   interval=1)
                file_handler.setFormatter(default_formatter)
                file_handler.setLevel(logging.DEBUG if self.debug else logging.INFO)
                root_logger.addHandler(file_handler)
