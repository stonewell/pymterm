#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string
import json

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, View, TabView
from GUI import application
from GUI import FileDialogs
from GUI import ModalDialog, Label, Button
from GUI import RadioGroup, RadioButton
from GUI import TextField
from GUI.Files import FileType, DirRef, FileRef
from GUI.Alerts import stop_alert, ask
from GUI import Task

import cap.cap_manager
import term.term_keyboard
import term_pygui_key_translate

from session import create_session
from term.terminal_gui import TerminalGUI
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term.terminal_widget import TerminalWidget
from term_menu import basic_menus

padding = 10
file_types = None
last_dir = DirRef(path = os.path.abspath(os.path.expanduser("~/")))

class FileTransfer(object):
    def __init__(self, session):
        self._transfer_task = None
        self._session = session

    def _upload(self, l_f, r_f, r_home = None, r_pwd = None):
        if not os.path.isfile(l_f):
            self._session.report_error("local file:{} is not existing, upload failed".format(l_f))
            return

        if len(r_f) == 0:
            r_f = os.path.join(".", os.path.basename(l_f))
        elif len(os.path.basename(r_f)) == 0:
            r_f = os.path.join(r_f, os.path.basename(l_f))

        self._transfer_task = Task(lambda: self._session.transfer_file(l_f,
                                    r_f,
                                    r_home,
                                    r_pwd,
                                    True,
                                    self.on_progress), .01)

    def on_progress(self, transfered, total):
        pass

    def _download(self, l_f, r_f, r_home = None, r_pwd = None):
        if len(r_f) == 0:
            self._session.report_error("remote file is not existing, download failed")
            return

        if len(l_f) == 0:
            l_f = os.path.join('.', os.path.basename(r_f))

        l_f = os.path.expandvars(os.path.expanduser(l_f))

        if os.path.isdir(l_f):
            l_f = os.path.join(l_f, os.path.basename(r_f))

        if os.path.isfile(l_f):
            if ask('file:{} exists, overwrite?'.format(l_f)) != 1:
                return

        self._transfer_task = Task(lambda: self._session.transfer_file(l_f,
                                    r_f,
                                    r_home,
                                    r_pwd,
                                    False,
                                    self.on_progress), .01)
        
class FileTransferDialog(ModalDialog, FileTransfer):
    def __init__(self, session,  **kwargs):
        title = 'File Transfer'

        self._session = session

        if 'title' in kwargs:
            title = kwargs['title']

        ModalDialog.__init__(self, title=title)
        FileTransfer.__init__(self, session)

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
        self.label_progress.text = 'Progress: {}%'.format(progress)

    def upload(self):
        l_f = os.path.expandvars(os.path.expanduser(self.txt_local_file.text))
        r_f = self.txt_remote_file.text

        self._upload(l_f, r_f)

    def download(self):
        r_f = self.txt_remote_file.text
        l_f = self.txt_local_file.text

        self._download(l_f, r_f)

    def cancel(self):
        self.dismiss(False)

    def choose_local_file(self):
        global last_dir
        try:
            result = FileDialogs.request_old_file("Open Local File:",
                default_dir = last_dir, file_types = file_types)

            if isinstance(result, FileRef):
                last_dir = result.dir
                self.txt_local_file.text = result.path
        except:
            logging.getLogger('term_pygui').exception('unable to choose file')

class FileTransferProgressDialog(ModalDialog, FileTransfer):
    def __init__(self, session, l_f, r_f, r_home, r_pwd, is_upload, **kwargs):
        title = 'File Transfer'

        self._session = session
        self._l_f = l_f
        self._r_f = r_f
        self._r_home = r_home
        self._r_pwd = r_pwd

        if 'title' in kwargs:
            title = kwargs['title']

        ModalDialog.__init__(self, title=title)
        FileTransfer.__init__(self, session)

        label_local = Label('Local File:')
        label_local_name = Label(l_f)

        label_remote = Label('Remote File:')
        label_remote_name = Label(r_f)

        self.cancel_button = Button("Close", enabled = True, style = 'cancel', action='cancel')

        self.label_progress = label_progress = Label('Progress: 0%')

        self.place(label_local, left = padding, top = padding)
        self.place(label_local_name, left = padding, top = label_local + padding, right = 240)

        self.place(label_remote, left = padding, top = label_local_name + padding)
        self.place(label_remote_name, left = padding, top = label_remote + padding, right = 240)

        self.place(label_progress, left = padding, top = label_remote_name + padding, right = label_remote_name.right)

        self.place(self.cancel_button, top = self.label_progress + padding, right = label_remote_name.right)
        self.shrink_wrap(padding = (padding, padding))

        if is_upload:
            self.task = Task(self.upload, .01)
        else:
            self.task = Task(self.download, .01)

    def on_progress(self, transfered, total):
        if total <= 0:
            return

        progress = int(float(transfered) / float(total) * 100)
        self.label_progress.text = 'Progress: {}%'.format(progress)

    def upload(self):
        self._upload(self._l_f, self._r_f, self._r_home, self._r_pwd)

    def download(self):
        self._download(self._l_f, self._r_f, self._r_home, self._r_pwd)

    def cancel(self):
        self.dismiss(False)
