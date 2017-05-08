import getpass
import json
import logging
import logging.config
import os
import sys

import pymterm

GUI_RENDERS = ["cairo", "pygame", "native"]
PYGLET_RENDERS = ["pyglet"]
RENDERS = GUI_RENDERS + ["kivy", "console"] + PYGLET_RENDERS

def get_default_user():
	return getpass.getuser()

class SessionConfig:
    def __init__(self, args):
        self.term_name = args.term_name
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
        self.password = None
        self.render = None
        self.gui_renders = GUI_RENDERS
        self.renders = 	RENDERS
        self.font_file = args.font_file
        self.font_name = args.font_name
        self.font_size = args.font_size
        self.dump_data = args.dump_data
        self.load_data = args.load_data
        self.send_envs = args.send_envs
        self.use_ssh_config = args.use_ssh_config

        self.load_config()

        if self.dump_data:
            try:
                f = open(self.dump_data, "w")
                f.close()
            except:
                logging.exception("unable to create dump file")
                raise ValueError('Unable to write dump data to file:{}'.format(self.dump_data))

        if self.load_data and not os.access(self.load_data, os.R_OK):
            raise ValueError('Unable to read dump data from file:{}'.format(self.load_data))

        if args.render:
            self.render = args.render
        elif 'render' in self.config:
            render = self.config['render']

            if 'default' in render:
                self.render = render['default'] if render['default'] in self.renders else None

        if self.debug_more:
            self.debug = True

        self.color_table = []

        if args.conn_str:
            self.set_conn_str(args.conn_str)
        elif not self.session_name:
            if self.render and self.render == 'console':
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

        #update global debug mode
        pymterm.debug_log = self.debug
        pymterm.debug_more_log = self.debug_more

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
        self.default_foreground_color = [0x00,0x00,0x00,0x88]
        self.default_background_color = [0xdd,0xdd,0xdd,0xFF]
        self.default_cursor_color = self.default_foreground_color

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
                if not color_theme.apply_color(self, self.color_table):
                    self.default_foreground_color = self.color_table[7]
                    self.default_background_color = self.color_table[0]

        #init render color table
        self.render_color_table = self.color_table[:]

    def get_color(self, idx):
        return self.render_color_table[idx]

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

        with open(config_path) as f:
            self.config = json.load(f)

    def find_config(self, p):
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
        if self.session_name:
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

            self.session_type = 'ssh'

    def get_session_names(self):
        if not 'sessions' in self.config:
            return []

        return [name for name in self.config['sessions']]

    def get_font_info(self):
        font_size = 17
        font_file = None
        font_name = 'Monospace'
        font_dir = None

        def norm_font_file(f, f_dir = None):
            if f is None:
                return None

            f = os.path.expandvars(os.path.expanduser(f))
            f_dir = os.path.expandvars(os.path.expanduser(f_dir)) if f_dir else None

            if os.path.isfile(f):
                return f

            if not os.path.isabs(f):
                f = os.path.join(f_dir if f_dir else '.', f)

            return f if os.path.isfile(f) else None

        config = self.config

        if config and 'font' in config:
            font_config = config['font']

            if 'name' in font_config:
                font_name = font_config['name']

            if 'font_file' in font_config:
                font_file = font_config['font_file']

            if 'size' in font_config:
                font_size = font_config['size']

            if 'font_dir' in font_config:
                font_dir = font_config['font_dir']

        if self.font_size:
            font_size = self.font_size

        if self.font_name:
            font_name = self.font_name

        if self.font_file:
            font_file = self.font_file

        font_file = norm_font_file(font_file, font_dir)
        logging.info('font info:file=[{}], name=[{}], size={}'.format(font_file, font_name, font_size))
        return (font_file, font_name, font_size)

    def load_send_envs(self, send_envs):
        keys, _vars = [], {}

        if not send_envs:
            return (keys, _vars)

        for env in send_envs:
            if '=' in env:
                parts=env.split('=')
                _vars[parts[0]] = '='.join(parts[1:])
            else:
                keys.append(env)

        return (keys, _vars)

    def read_ssh_config_file(self, config_file, hostname):
        files = []

        if config_file == '__pymterm_use_sys_default_config_file__':
            files.extend(['~/.ssh/ssh_config', '/etc/ssh/ssh_config'])
        else:
            files.append(config_file)

        for file_path in files:
            fp = os.path.expandvars(os.path.expanduser(file_path))

            if os.access(fp, os.R_OK):
                import paramiko
                try:
                    ssh_config = paramiko.SSHConfig()
                    with open(fp) as f:
                        ssh_config.parse(f)

                    return ssh_config.lookup(hostname)
                except:
                    logging.exception('read ssh_config file failed:{}'.format(fp))

        return None

    def get_ssh_config(self, session, hostname):
        ssh_config = None

        if self.use_ssh_config:
            ssh_config = self.read_ssh_config_file(self.use_ssh_config, hostname)

        if not ssh_config and session:
            if 'use_ssh_config' in session:
                ssh_config = self.read_ssh_config_file(session['use_ssh_config'], hostname)

            if not ssh_config and 'use_system_ssh_config' in session and session['use_system_ssh_config']:
                ssh_config = self.read_ssh_config_file('__pymterm_use_sys_default_config_file__', hostname)

        if not ssh_config:
            if 'use_ssh_config' in self.config:
                ssh_config = self.read_ssh_config_file(self.config['use_ssh_config'], hostname)

            if not ssh_config and 'use_system_ssh_config' in self.config and self.config['use_system_ssh_config']:
                ssh_config = self.read_ssh_config_file('__pymterm_use_sys_default_config_file__', hostname)

        return ssh_config

    def get_envs(self, keys):
        import fnmatch

        envs = {}

        for key in os.environ:
            for key2 in keys:
                if fnmatch.fnmatch(key, key2):
                    envs[key] = os.environ[key]

        return envs

    def get_conn_info(self):
        if not self.hostname or len(self.hostname) == 0:
            return ({}, None) #envs, proxy command

        envs = {}
        proxy_command = None

        session = None

        if (self.session_name
                and self.config
                and 'sessions' in self.config
                and self.session_name in self.config['sessions']):
            session = self.config['sessions'][self.session_name]

        ssh_config = self.get_ssh_config(session, self.hostname)

        if ssh_config:
            if  'proxycommand' in ssh_config:
                proxy_command = ssh_config['proxycommand']

            if 'sendenv' in ssh_config:
                keys, _vars = self.load_send_envs(ssh_config['sendenv'].split(' '))
                envs.update(self.get_envs(keys))
                envs.update(_vars)

        #global envs
        if 'send_envs' in self.config:
            keys, _vars = self.load_send_envs(self.config['send_envs'])
            envs.update(self.get_envs(keys))
            envs.update(_vars)

        #session envs
        if session and 'send_envs' in session:
            keys, _vars = self.load_send_envs(session['send_envs'])
            envs.update(self.get_envs(keys))
            envs.update(_vars)

        #cmd envs
        if self.send_envs:
            keys, _vars = self.load_send_envs(self.send_envs)
            envs.update(self.get_envs(keys))
            envs.update(_vars)

        return (envs, proxy_command)

    def update_color_for_render(self, gen_color_func):
        for i in range(len(self.render_color_table)):
            self.render_color_table[i] = gen_color_func(self.render_color_table[i])

        self.default_foreground_color = gen_color_func(self.default_foreground_color)
        self.default_background_color = gen_color_func(self.default_background_color)
        self.default_cursor_color = gen_color_func(self.default_cursor_color)
