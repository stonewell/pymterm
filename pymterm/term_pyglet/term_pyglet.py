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
        self._event_loop = TermPygletEventLoop()
        pyglet.app.event_loop = self._event_loop

    def connect_to(self, conn_str=None, port=None, session_name=None, win=None):
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

        self._event_loop.run()

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

        self._windows.append(window)

    def new_window_cmd(self):
        self.connect_to()


class TermPygletEventLoop(pyglet.app.EventLoop):
    def __init__(self, *args, **kwargs):
        super(TermPygletEventLoop, self).__init__(*args, **kwargs)

    def idle(self):
        dt = self.clock.update_time()
        self.clock.call_scheduled_functions(dt)

        # Redraw all windows only when windows is invalid
        for window in pyglet.app.windows:
            if (window._legacy_invalid and window.invalid):
                window.switch_to()
                window.dispatch_event('on_draw')
                window.flip()
                window._legacy_invalid = False

        # Update timout
        timeout = self.clock.get_sleep_time(True)

        return timeout


class TerminalPyglet(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyglet, self).__init__(cfg)

    def prompt_login(self, transport, username):
        pass

    def prompt_password(self, action):
        pass

    def report_error(self, msg):
        pass

    def ask_user(self, msg):
        pass

    def process_status_line(self, mode, status_line):
        TerminalGUI.process_status_line(self, mode, status_line)
