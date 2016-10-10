#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, View, TabView
from GUI import application
from GUI.Files import FileType
from GUI.Files import FileType, DirRef, FileRef
from GUI import FileDialogs

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term_menu import basic_menus

try:
    from term_pygui_glview import TerminalPyGUIGLView as TerminalPyGUIView
except:
    from term_pygui_view import TerminalPyGUIView as TerminalPyGUIView

from GUI import ModalDialog, Label, Button
from GUI import RadioGroup, RadioButton
from GUI import TextField
from GUI import Task

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

class FileTransferDialog(ModalDialog):

    def __init__(self, session,  **kwargs):
        title = 'File Transfer'

        self._session = session

        if 'title' in kwargs:
            title = kwargs['title']

        ModalDialog.__init__(self, title=title)

        label_local = Label('Local File:')
        self.txt_local_file = txt_local_file = TextField(multiline = False, password = False)
        btn_browse_file = Button('Browse', action='choose_local_file', enabled = True)

        label_remote = Label('Remote File:')
        self.txt_remote_file = txt_remote_file = TextField(multiline = False, password = False)

        self.download_button = Button("Download", action = "download", enabled = True)
        self.upload_button = Button("Upload", action = "upload", enabled = True)
        self.cancel_button = Button("Close", enabled = True, style = 'cancel', action='cancel')

        self.label_progress = label_progress = Label('Progress: 0%')

        self.place(label_local, left = padding, top = padding)
        self.place(txt_local_file, left = padding, top = label_local + padding, right = 240)
        self.place(btn_browse_file, left = txt_local_file, top = txt_local_file.top)

        self.place(label_remote, left = padding, top = txt_local_file + padding)
        self.place(txt_remote_file, left = padding, top = label_remote + padding, right = 240)

        self.place(label_progress, left = padding, top = txt_remote_file + padding, right = btn_browse_file.right)

        self.place(self.cancel_button, top = self.label_progress + padding, right = btn_browse_file.right)
        self.place(self.download_button, top = self.cancel_button.top, right = self.cancel_button - padding)
        self.place(self.upload_button, top = self.cancel_button.top, right = self.download_button - padding)
        self.shrink_wrap(padding = (padding, padding))

    def on_progress(self, transfered, total):
        if total <= 0:
            return

        progress = int(float(transfered) / float(total) * 100)
        logging.error('Progress:{}%, {}, {}'.format(progress, transfered, total))
        self.label_progress.text = 'Progress: {}%'.format(progress)

    def upload(self):
        l_f = self.txt_local_file.text

        if not os.path.isfile(l_f):
            return

        r_f = self.txt_remote_file.text

        if len(r_f) == 0:
            r_f = os.path.join(".", os.path.basename(l_f))

        self._session.transfer_file(l_f,
                                        r_f,
                                        True,
                                        self.on_progress)

    def download(self):
        r_f = self.txt_remote_file.text

        if len(r_f) == 0:
            return

        l_f = self.txt_local_file.text

        if len(l_f) == 0:
            l_f = os.path.join('.', os.path.basename(r_f))

        if os.path.isdir(l_f):
            l_f = os.path.join(l_f, os.path.basename(r_f))

        self._session.transfer_file(l_f,
                                    r_f,
                                    False,
                                        self.on_progress)

    def cancel(self):
        self.dismiss(False)

    def choose_key_file(self):
        global last_dir
        result = FileDialogs.request_old_file("Open Local File:",
            default_dir = last_dir, file_types = file_types)

        if isinstance(result, FileRef):
            last_dir = result.dir
            self.txt_local_file.text = result.path

class TerminalPyGUIApp(Application):
    def __init__(self, cfg):
        Application.__init__(self)

        self.cfg = cfg
        self.current_tab = None
        self.conn_history = []
        self.menus = basic_menus(self.cfg.get_session_names())

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & pyGUI'

    def setup_menus(self, m):
        Application.setup_menus(self, m)
        m.paste_cmd.enabled = application().query_clipboard()
        m.new_window_cmd.enabled = 1
        m.open_session_cmd.enabled = 1

    def connect_to(self, conn_str = None, port = None, session_name = None, win = None):
        cfg = self.cfg.clone()
        if conn_str:
            cfg.set_conn_str(conn_str)
        elif session_name:
            cfg.session_name = session_name
            cfg.config_session()

        if port:
            cfg.port = port

        cfg.session_type = 'ssh'

        doc = self.make_new_document()
        doc.new_contents()
        doc.cfg = cfg

        if win:
            view = TerminalPyGUIView(model=doc)
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
        view = TerminalPyGUIView(model=document)
        w, h = view.get_prefered_size()

        win = Window(bounds = (0, 0, w + 10, h + 50), document = document)
        win.tabview = tabview = TermTabView()
        win.auto_position = False

        self._create_new_tab(win, view)

        win.place(tabview, left = 0, top = 0, right = 0, bottom = 0, sticky = 'nsew')

        win.center()
        win.show()
        view.become_target()

    def _create_new_tab(self, win, view):
        win.tabview.add_item(view)

        cfg = view.model.cfg
        session = create_session(cfg, self.create_terminal(cfg))
        session.term_widget = view
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
