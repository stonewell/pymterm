#coding=utf-8
import json
import logging
import os

from pylibui.core import App
from pylibui.controls import Window, Tab, OpenGLArea

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
from term_menu import basic_menus
from file_transfer import FileTransferDialog, FileTransferProgressDialog

padding = 10

class TermWindow(Window):
    def __init__(self, *args, **kwargs):
        Window.__init__(self, *args, **kwargs)

class TerminalApp(App):
    def __init__(self, cfg):
        Application.__init__(self)

        self.cfg = cfg
        self.current_tab = None
        self.conn_history = []
        self.menus = basic_menus(self.cfg.get_session_names())
        self._cls_view = self._select_view_render()

    def _try_import_render(self, render):
        if render == 'cairo':
            try:
                from glview_pycairo import TerminalPyGUIGLView as TerminalPyGUIView
                logging.getLogger('term_pylibui').info('using opengl cairo/pango render')
                return TerminalPyGUIView
            except:
                logging.getLogger('term_pylibui').exception('failed load opengl cairo render')
                return None

        if render == 'pygame':
            try:
                from glview_pygame import TerminalPyGUIGLView as TerminalPyGUIView
                logging.getLogger('term_pylibui').info('using opengl pygame render')
                return TerminalPyGUIView
            except:
                logging.getLogger('term_pylibui').exception('failed load opengl pygame render')
                return None

        if render == 'native':
            try:
                from view import TerminalPyGUIView as TerminalPyGUIView
                logging.getLogger('term_pylibui').info('using native pygui render')
                return TerminalPyGUIView
            except:
                return None

        logging.getLogger('term_pylibui').info('unsupported render:{}'.format(render))
        return None

    def _select_view_render(self):
        render = self.cfg.render
        _cls_view = None

        if render and render in self.cfg.gui_renders:
            _cls_view = self._try_import_render(render)

        if _cls_view:
            return _cls_view

        for render in self.cfg.gui_renders:
            _cls_view = self._try_import_render(render)
            if _cls_view:
                return _cls_view

        logging.getLogger('term_pylibui').error("unable to find a valid render")

        stop_alert("unable to find a valid render, supported render:{}".format(self.cfg.renders))

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & pyGUI'

    def _create_view(self):
        return self._cls_view()

    def connect_to(self, conn_str = None, port = None, session_name = None, win = None):
        cfg = self.cfg.clone()
        if conn_str:
            cfg.set_conn_str(conn_str)
        elif session_name:
            cfg.session_name = session_name
            cfg.config_session()

        if port:
            cfg.port = port

        doc = self.make_new_document()
        doc.new_contents()
        doc.cfg = cfg

        if win:
            view = self._create_view(doc)
            self._create_new_tab(win, view)
        else:
            self.make_window(doc)

    def create_terminal(self, cfg):
        return TerminalPyGUI(cfg)

    def start(self):
        self.run()

    def open_app(self):
        self.connect_to()

    def open_window_cmd(self):
        self.connect_to()

    def make_window(self, document):
        view = self._create_view(document)
        w, h = view.get_prefered_size()

        win = TermWindow(bounds = (0, 0, w + 10, h + 50), document = document)
        win.tabview = tabview = TermTabView()
        win.auto_position = False

        self._create_new_tab(win, view)

        win.place(tabview, left = 0, top = 0, right = 0, bottom = 0, sticky = 'nsew')

        win.center()
        win.show()
        view.become_target()

    def _remove_session_tab(self, win, view):
        selected_index = win.tabview.selected_index
        count = len(win.tabview.items)

        if selected_index < 0 or selected_index >= count:
            return

        win.tabview.remove_item(view)

        count = len(win.tabview.items)

        win.tabview.selected_index = -1

        if count == 0:
            win.close_cmd()
            application()._check_for_no_windows()
        elif selected_index < count and selected_index >= 0:
            win.tabview.selected_index = selected_index
        else:
            win.tabview.selected_index = count - 1


    def _on_session_stop(self, session):
        if not session.window or not session.term_widget:
            logging.getLogger('term_pylibui').warn('invalid session, window:{}, term_widget:{}'.format(session.window, session.term_widget))
            return

        win = session.window
        view = session.term_widget

        self._remove_session_tab(win, view)

    def _create_new_tab(self, win, view):
        win.tabview.add_item(view)

        cfg = view.model.cfg
        session = create_session(cfg, self.create_terminal(cfg))
        session.on_session_stop = self._on_session_stop
        session.term_widget = view
        session.window = win
        session.terminal.term_widget = view
        view.session = session
        view.tab_width = session.get_tab_width()

        self._session_task = Task(session.start, .1)
        #session.start()

        win.tabview.selected_index = len(win.tabview.items) - 1

    def make_document(self, fileref):
        doc = TerminalPyGUIDoc()
        doc.cfg = self.cfg.clone()
        doc.title = 'Multi-Tab Terminal Emulator in Python & pyGUI'

        return doc

    def new_window_cmd(self):
        self.connect_to()

    def next_tab_cmd(self):
        self._change_cur_tab(1)

    def prev_tab_cmd(self):
        self._change_cur_tab(-1)

    def _change_cur_tab(self, step):
        win = self.get_target_window()
        tab_view = win.tabview
        count = len(tab_view.items)

        if count == 0:
            return

        selected_index = 0 if tab_view.selected_index < 0 else tab_view.selected_index

        new_index = selected_index + step

        if new_index < 0:
            new_index = count - 1
        elif new_index >= count:
            new_index = 0

        if new_index != selected_index:
            tab_view.selected_index = new_index

    def close_tab_cmd(self):
        win = self.get_target_window()
        tab_view = win.tabview

        if tab_view.selected_index < 0:
            return

        view = tab_view.items[tab_view.selected_index]

        if view.session.stopped:
            self._remove_session_tab(win, view)
        else:
            view.session.stop()

    def new_cmd(self):
        self.connect_to(win = self.get_target_window())

    def open_session_cmd(self, *args):
        index, = args
        self.connect_to(session_name=self.cfg.get_session_names()[index], win=self.get_target_window())

    def transfer_file_cmd(self):
        win = self.get_target_window()
        tab_view = win.tabview

        if tab_view.selected_index < 0:
            return
        view = tab_view.items[tab_view.selected_index]
        dlog = FileTransferDialog(view.session)
        dlog.present()


class TerminalPyGUIDoc(Document):
    def new_contents(self):
        pass

    def read_contents(self, file):
        pass

    def write_contents(self, file):
        pass


class TermTabView(TabView):
    def __init__(self, *args, **kwargs):
        TabView.__init__(self, *args, **kwargs)
        self._generic_tabbing = False
        
    def tab_changed(self, tab_index):
        if tab_index >= 0 and tab_index < len(self.items):
            v = self.items[tab_index]
            self.__focus_task = Task(lambda:v.become_target(), .01)

class TerminalPyGUI(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyGUI, self).__init__(cfg)

    def prompt_login(self, transport, username):
        dlog = LoginDialog(self.session, transport, username = username)
        dlog.present()

    def prompt_password(self, action):
        dlog = PasswordDialog(action)
        dlog.present()

    def report_error(self, msg):
        self.__alert_task = Task(lambda : stop_alert(msg), .001)

    def ask_user(self, msg):
        return ask(msg)

    def process_status_line(self, mode, status_line):
        TerminalGUI.process_status_line(self, mode, status_line)

        if status_line.startswith('PYMTERM_STATUS_CMD='):
            try:
                context = json.loads(status_line[len('PYMTERM_STATUS_CMD='):])
                self.__status_cmd_task = Task(lambda:self.process_status_cmd(context), .01)
            except:
                logging.getLogger('term_pylibui').exception('invalid status cmd found')

    def process_status_cmd(self, context):
        if not 'ACTION' in context:
            logging.getLogger('term_pylibui').warn('action not found in status cmd')
            return

        action = context['ACTION'].upper()
        home = context['HOME']
        pwd = context['PWD']
        r_f = context['R_F']

        global last_dir
        l_f = None
        result = None

        base_name = os.path.basename(r_f)

        if action == 'UPLOAD':
            result = FileDialogs.request_old_file("Choose file to upload:",
                default_dir = last_dir, file_types = file_types)
        elif action == 'DOWNLOAD':
            result = FileDialogs.request_new_file("Choose location to save download file:",
                default_dir = last_dir, default_name = base_name)
        else:
            logging.getLogger('term_pylibui').warn('action not valid:{} in status cmd'.format(action))
            return

        if not isinstance(result, FileRef):
            return
        last_dir = result.dir
        l_f = result.path

        dlg = FileTransferProgressDialog(self.session,
                                        l_f,
                                        r_f,
                                        home,
                                        pwd,
                                        action == 'UPLOAD')
        dlg.present()
