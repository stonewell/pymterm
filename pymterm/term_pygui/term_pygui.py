#coding=utf-8
import json
import logging
import os

from GUI import Application, Document, Window, TabView
from GUI import FileDialogs
from GUI import ModalDialog, Label, Button
from GUI import RadioGroup, RadioButton
from GUI import Task
from GUI import TextField
from GUI import application
from GUI.Alerts import stop_alert, ask
from GUI.Files import DirRef, FileRef

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, set_attr_mode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
from term_menu import basic_menus
from term_pygui_file_transfer import FileTransferDialog, FileTransferProgressDialog

padding = 10
file_types = None
last_dir = DirRef(path = os.path.abspath(os.path.expanduser("~/.ssh")))

class PasswordDialog(ModalDialog):
    def __init__(self, action, **kwargs):
        title = 'Password'

        self._action = action

        lbl_text = action.get_pass_desc()

        ModalDialog.__init__(self, title=title)

        label = Label(lbl_text)
        self.txt_passwd = TextField(multiline = False, password = True)

        self.ok_button = Button("Connect", action = "ok", enabled = True, style = 'default')
        self.cancel_button = Button("Cancel", enabled = True, style = 'cancel', action='cancel')

        self.place(label, left = padding, top = padding)
        self.place(self.txt_passwd, left = padding, top = label + padding,
                   right= label.right if label.right > 260 else 260)

        self.place(self.cancel_button, top = self.txt_passwd + padding, right = self.txt_passwd.right)
        self.place(self.ok_button, top = self.txt_passwd + padding, right = self.cancel_button - padding)
        self.shrink_wrap(padding = (padding, padding))

    def ok(self):
        if len(self.txt_passwd.text) == 0:
            return
        self._action.password = self.txt_passwd.text
        self.dismiss(True)
        self._action.execute()

    def cancel(self):
        self.dismiss(False)

        if self._action.next_action:
            self._action.next_action.execute()

class LoginDialog(ModalDialog):

    def __init__(self, session, transport,  **kwargs):
        title = 'Login'

        self._session = session
        self._transport = transport

        if 'title' in kwargs:
            title = kwargs['title']

        ModalDialog.__init__(self, title=title)

        label = Label('Key File:')
        btn_rsa = RadioButton(title='RSA', value = 'RSA')
        btn_dss = RadioButton(title='DSS', value = 'DSS')
        self.key_file_group = key_file_group = RadioGroup(items = [btn_rsa, btn_dss])
        key_file_group.value = 'RSA'
        self.txt_key_file = txt_key_file = TextField(multiline = False, password = False)
        btn_browse_file = Button('Browse', action='choose_key_file', enabled = True)

        lbl_login = Label('Login')
        self.txt_login = TextField(multiline = False, password = False)

        if 'username' in kwargs:
            self.txt_login.text = kwargs['username']

        lbl_passwd = Label('Password')
        self.txt_passwd = TextField(multiline = False, password = True)

        self.ok_button = Button("Connect", action = "ok", enabled = True, style = 'default')
        self.cancel_button = Button("Cancel", enabled = True, style = 'cancel', action='cancel')

        self.place(label, left = padding, top = padding)
        self.place(btn_rsa, left = label + padding, top = padding)
        self.place(btn_dss, left = btn_rsa + padding, top = padding)
        self.place(txt_key_file, left = padding, top = btn_rsa + padding, right = 240)
        self.place(btn_browse_file, left = txt_key_file, top = txt_key_file.top)

        self.place(lbl_login, left = padding, top = txt_key_file + padding)
        self.place(self.txt_login, left = padding, top = lbl_login + padding, right = btn_browse_file.right)

        self.place(lbl_passwd, left = padding, top = self.txt_login + padding)
        self.place(self.txt_passwd, left = padding, top = lbl_passwd + padding, right = btn_browse_file.right)

        self.place(self.cancel_button, top = self.txt_passwd + padding, right = btn_browse_file.right)
        self.place(self.ok_button, top = self.txt_passwd + padding, right = self.cancel_button - padding)
        self.shrink_wrap(padding = (padding, padding))

    def ok(self):
        if self._session.try_login(self._transport,
                                self.txt_key_file.text,
                                self.key_file_group.value,
                                self.txt_login.text,
                                self.txt_passwd.text):
            self.dismiss(True)

    def cancel(self):
        self.dismiss(False)

    def choose_key_file(self):
        global last_dir
        result = FileDialogs.request_old_file("Open SSH key File:",
            default_dir = last_dir, file_types = file_types)

        if isinstance(result, FileRef):
            last_dir = result.dir
            self.txt_key_file.text = result.path

class TermWindow(Window):
    def key_down(self, event):
        Window.key_down(self, event)

        logging.error('window key down:{}'.format(event))

class TerminalPyGUIApp(Application):
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
                from term_pygui_glview_pycairo import TerminalPyGUIGLView as TerminalPyGUIView
                logging.getLogger('term_pygui').info('using opengl cairo/pango render')
                return TerminalPyGUIView
            except:
                return None

        if render == 'pygame':
            try:
                from term_pygui_glview_pygame import TerminalPyGUIGLView as TerminalPyGUIView
                logging.getLogger('term_pygui').info('using opengl pygame render')
                return TerminalPyGUIView
            except:
                logging.getLogger('term_pygui').exception('failed load opengl pygame render')
                return None

        if render == 'native':
            try:
                from term_pygui_view import TerminalPyGUIView as TerminalPyGUIView
                logging.getLogger('term_pygui').info('using native pygui render')
                return TerminalPyGUIView
            except:
                return None

        logging.getLogger('term_pygui').info('unsupported render:{}'.format(render))
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

        logging.getLogger('term_pygui').error("unable to find a valid render")

        stop_alert("unable to find a valid render, supported render:{}".format(self.cfg.renders))

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & pyGUI'

    def setup_menus(self, m):
        Application.setup_menus(self, m)
        m.paste_cmd.enabled = application().query_clipboard()
        m.new_window_cmd.enabled = 1
        m.open_session_cmd.enabled = 1

        win = self.get_target_window()
        close_tab_enabled = False

        if win and win.tabview:
            tab_view = win.tabview
            close_tab_enabled = tab_view.selected_index >= 0

        m.close_tab_cmd.enabled = 1 if close_tab_enabled else 0
        m.next_tab_cmd.enabled = True
        m.prev_tab_cmd.enabled = True

    def _create_view(self, doc):
        return self._cls_view(model=doc)

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
            logging.getLogger('term_pygui').warn('invalid session, window:{}, term_widget:{}'.format(session.window, session.term_widget))
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
    def tab_changed(self, tab_index):

        if tab_index >= 0 and tab_index < len(self.items):
            v = self.items[tab_index]
            v.become_target()

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
                logging.getLogger('term_pygui').exception('invalid status cmd found')

    def process_status_cmd(self, context):
        if not 'ACTION' in context:
            logging.getLogger('term_pygui').warn('action not found in status cmd')
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
            logging.getLogger('term_pygui').warn('action not valid:{} in status cmd'.format(action))
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
