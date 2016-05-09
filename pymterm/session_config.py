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
        self.color_table = []

        if args.conn_str:
            self.set_conn_str(args.conn_str)
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

        #init color table
        self.init_color_table()

    COLOR_SET_0_RATIO = 0x44
    COLOR_SET_1_RATIO = 0xaa

    #ansi color
    COLOR_TABLE = [
        [0, 0, 0, 0xFF], #BLACK
        [COLOR_SET_0_RATIO, 0, 0, 0xFF], #RED
        [0, COLOR_SET_0_RATIO, 0, 0xFF], #GREEN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0, 0xFF], #BROWN
        [0, 0, COLOR_SET_0_RATIO, 0xFF], #BLUE
        [COLOR_SET_0_RATIO, 0, COLOR_SET_0_RATIO, 0xFF], #MAGENTA
        [0, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0xFF], #CYAN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0xFF], #LIGHT GRAY
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF], #DARK_GREY
        [0xFF, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF], #RED
        [COLOR_SET_1_RATIO, 0xFF, COLOR_SET_1_RATIO, 0xFF], #GREEN
        [0xFF, 0xFF, COLOR_SET_1_RATIO, 0xFF], #YELLOW
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF, 0xFF], #BLUE
        [0xFF, COLOR_SET_1_RATIO, 0xFF, 0xFF], #MAGENTA
        [COLOR_SET_1_RATIO, 0xFF, 0xFF, 0xFF], #CYAN
        [0xFF, 0xFF, 0xFF, 0xFF], #WHITE
        ]

    def init_color_table(self):
        #copy default table
        self.color_table = [c[:] for c in SessionConfig.COLOR_TABLE]
        
        for i in range(240):
            if i < 216:
                r = i / 36
                g = (i / 6) % 6
                b = i % 6
                self.color_table.append([r * 40 + 55 if r > 0 else 0,
                                                 g * 40 + 55 if g > 0 else 0,
                                                 b * 40 + 55 if b > 0 else 0,
                                                 0xFF])
            else:
                shade = (i - 216) * 10 + 8
                self.color_table.append([shade,
                                                 shade,
                                                 shade,
                                                 0xFF])
        #load config
        if self.color_theme:
            from colour.color_manager import get_color_theme
            color_theme = get_color_theme(self.color_theme)
            if color_theme:
                color_theme.apply_color(self, self.color_table)
                
    def get_color(self, idx):
        return self.color_table[idx]

    def clone(self):
        import copy

        c = copy.deepcopy(self)
        
        c.init_color_table()

        return c

    def set_conn_str(self, conn_str):
        parts = conn_str.split('@')

        if parts >= 2:
            self.hostname = '@'.join(parts[1:])
            self.username = parts[0]
        else:
            self.hostname = conn_str
            self.username = get_default_user()
            
