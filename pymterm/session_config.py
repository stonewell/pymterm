import os
import sys
import getpass

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
