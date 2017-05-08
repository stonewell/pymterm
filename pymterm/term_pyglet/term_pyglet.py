#coding=utf-8
import json
import logging
import os

import pyglet

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget

from window import TermPygletWindow

LOGGER = logging.getLogger('term_pyglet')

class TerminalPygletApp():
    def __init__(self, cfg):
        self.cfg = cfg
        self.conn_history = []
        self._windows = []

    def connect_to(self, conn_str = None, port = None, session_name = None, win = None):
        cfg = self.cfg.clone()
        if conn_str:
            cfg.set_conn_str(conn_str)
        elif session_name:
            cfg.session_name = session_name
            cfg.config_session()

        if port:
            cfg.port = port

        self._create_window(cfg)

    def create_terminal(self, cfg):
        return TerminalPyglet(cfg)

    def start(self):
        self.open_app()
        pyglet.app.run()

    def open_app(self):
        self.connect_to()

    def open_window_cmd(self):
        self.connect_to()

    def _on_session_stop(self, session):
        if not session.window or not session.term_widget:
            LOGGER.warn('invalid session, window:{}, term_widget:{}'.format(session.window, session.term_widget))
            return

    def _create_window(self, cfg):
        window = TermPygletWindow()
        session = create_session(cfg, self.create_terminal(cfg))
        session.on_session_stop = self._on_session_stop
        session.term_widget = window
        session.window = window
        session.terminal.term_widget = window
        window.session = session
        window.tab_width = session.get_tab_width()

        #session.start()

        self._windows.append(window)

    def new_window_cmd(self):
        self.connect_to()

class TerminalPyglet(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyglet, self).__init__(cfg)
