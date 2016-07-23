import getpass
import logging
import logging.config
import os
import sys


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
        self.debug_more = args.debug_more
        self.session_type = args.session_type
        self.config = args.config
        self.kivy = args.kivy
        self.pygui = args.pygui
        self.password = None

        self.load_config()
        
        if self.debug_more:
            self.debug = True
            
        self.color_table = []

        if args.conn_str:
            self.set_conn_str(args.conn_str)
        elif not self.session_name:
            if self.console:
                raise ValueError("no engouth connect information")

        #validate host and user
        if not self.session_name and (len(self.hostname) == 0 or len(self.username) == 0):
            if self.session_type == 'ssh':
                raise ValueError("no engouth connect information")

        if not args.conn_str:
            self.config_session()

        if self.session_type == 'pipe':
            if self.config and 'pipe-config' in self.config and 'default-shell' in self.config['pipe-config']:
                pass
            else:
                raise ValueError('no default shell configured for pipe mode')

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

        if len(parts) >= 2:
            self.hostname = '@'.join(parts[1:])
            self.username = parts[0]
        else:
            self.hostname = conn_str
            self.username = get_default_user()
            
    def get_conn_str(self):
        return ''.join([self.username, '@', self.hostname, ':', str(self.port)])

    def load_config(self):
        config_path, need_find_config = (self.config, False) if self.config else ('pymterm.json', True)

        if need_find_config:
            config_path = self.find_config(config_path)

        if not os.path.exists(config_path):
            raise ValueError('unable to find the config file:{}'.format(config_path))

        import json
        with open(config_path) as f:
            self.config = json.load(f)

    def find_config(f, p):
        if os.path.exists(p):
            return p

        import appdirs

        dirs = [appdirs.user_config_dir('pymterm'),
                os.path.dirname(__file__),
                os.path.join(os.path.dirname(__file__), '..')]

        for d in dirs:
            pp = os.path.join(d, p)

            if os.path.exists(pp):
                return pp
        return p
    
    def config_session(self):
        if self.session_name and self.session_type == 'ssh':
            if not self.config or not 'sessions' in self.config or not self.session_name in self.config['sessions']:
                raise ValueError("unable to find the session:{}".format(self.session_name))

            #set session config
            session = self.config['sessions'][self.session_name]

            if not 'conn_str' in session:
                raise ValueError("unable to find connection string for the session:{}".format(self.session_name))

            self.set_conn_str(session['conn_str'])

            if 'port' in session:
                self.port = session['port']
            else:
                self.port = 22

            if 'password' in session:
                self.password = session['password']
            else:
                self.password = None

    def get_session_names(self):
        if not 'sessions' in self.config:
            return []

        return [name for name in self.config['sessions']]
        
