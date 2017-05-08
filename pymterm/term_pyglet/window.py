#coding=utf-8
import logging
import sys

from functools32 import lru_cache

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import window_base


class TermPygletWindow(window_base.TermPygletWindowBase):
    def __init__(self, *args, **kwargs):
        super(TermPygletWindow, self).__init__(*args, **kwargs)
