#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string
import threading

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, View, TabView
from GUI import application
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font
from GUI.Colors import rgb
from GUI.Files import FileType, DirRef, FileRef
from GUI import FileDialogs

from GUI import Task

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term_menu import basic_menus

from functools32 import lru_cache

SINGLE_WIDE_CHARACTERS =	\
					" !\"#$%&'()*+,-./" \
					"0123456789" \
					":;<=>?@" \
					"ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
					"[\\]^_`" \
					"abcdefghijklmnopqrstuvwxyz" \
					"{|}~" \
					""

def boundary(value, minvalue, maxvalue):
    '''Limit a value between a minvalue and maxvalue.'''
    return min(max(value, minvalue), maxvalue)

_color_map = {}

class TerminalPyGUIViewBase(TerminalWidget):

    def __init__(self, **kwargs):
        self.font_size = 17.5
        self.padding_x = 5
        self.padding_y = 5
        self.session = None
        self.selection_color = [0.1843, 0.6549, 0.8313, .5]
        self._width_cache = {}
        self._lock = threading.Lock()
        self._refresh_task = Task(self.__refresh, .02, False, False)

        TerminalWidget.__init__(self, **kwargs)

    def _get_color(self, color_spec):
        key = repr(color_spec)
        if key in _color_map:
            return _color_map[key]

        c = map(lambda x: x / 255, map(float, color_spec))

        _color_map[key] = r = rgb(*c)

        return r

    def __refresh(self):
        logging.getLogger('term_pygui').debug('refresh called')
        self.invalidate()
        self.update()

    def refresh(self):
        self._refresh_task.start()

    def key_down(self, e):
        key = term_pygui_key_translate.translate_key(e)

        keycode = (e.char, key)
        text = key if len(key) == 1 and key[0] in string.printable else e.char if len(e.char) > 0 else None
        modifiers = []

        if e.option:
            modifiers.append('alt')
        if e.control:
            modifiers.append('ctrl')
        if e.shift:
            modifiers.append('shift')

        logging.getLogger('term_pygui').debug('view key_down:{}'.format(e))
        logging.getLogger('term_pygui').debug('view key_down:{}, {}, {}'.format(keycode, text, modifiers))
        if self.session.terminal.process_key(keycode,
                                             text,
                                             modifiers):
            return

        v, handled = term.term_keyboard.translate_key(self.session.terminal,
                                                 keycode,
                                                 text,
                                                 modifiers)

        if len(v) > 0:
            self.session.send(v)
        elif len(e.char) > 0:
            self.session.send(e.char)
        elif text:
            self.session.send(text)

        logging.getLogger('term_pygui').debug(' - translated %r, %d' % (v, handled))

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return

    def destroy(self):
        self.session.stop()
        super(TerminalPyGUIViewBase, self).destroy()

    def resized(self, delta):
        w, h = self.size

        if w <= 0 or h <=0:
            return

        w -= self.padding_x * 2
        h -= self.padding_y * 2
        h -= (self._get_line_height() / 3)

        self._calculate_visible_rows(h)
        self._calculate_visible_cols(w)

        logging.getLogger('term_pygui').debug('on size: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))
        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()
            logging.getLogger('term_pygui').debug('on size done: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))

    def _calculate_visible_rows(self, h):
        f = self._get_font()
        self.visible_rows = int(h / self._get_line_height())
        if self.visible_rows <= 0:
            self.visible_rows = 1

    def _calculate_visible_cols(self, w):
        f = self._get_font()
        self.visible_cols = int(w / self._get_col_width())

        if self.visible_cols <= 0:
            self.visible_cols = 1

    def copy_to_clipboard(self, data):
        application().set_clipboard(data.encode('utf-8'))

    def paste_from_clipboard(self):
        return application().get_clipboard().decode('utf-8')

    def mouse_down(self, event):
        self.become_target()

        self.cancel_selection()

        self._selection_from = self._selection_to = self._get_cursor_from_xy(*event.position)

        mouse_tracker = self.track_mouse()
        while True:
            event = mouse_tracker.next()
            self._selection_to = self._get_cursor_from_xy(*event.position)

            self.refresh()

            if event.kind == 'mouse_up':
                try:
                    mouse_tracker.next()
                except StopIteration:
                    pass
                break

    def _get_cursor_from_xy(self, x, y):
        '''Return the (row, col) of the cursor from an (x, y) position.
        '''
        padding_left = self.padding_x
        padding_top = self.padding_y
        l = self.lines
        f = self._get_font()
        dy = self._get_line_height()
        cx = x
        cy = y - padding_top
        cy = int(boundary(round(cy / dy - 0.5), 0, len(l) - 1))

        if cy >= len(l) or cy < 0:
            return 0, 0

        text = self.norm_text(''.join(l[cy]))
        for i in range(0, len(text)):
            if self._get_col_width() * i + self._get_col_width() * 0.6 + padding_left > cx:
                for ii in range(len(l[cy])):
                    if l[cy][ii] == '\000':
                        continue
                    i -= 1
                    if i < 0:
                        while ii < len(l[cy]) and l[cy][ii] == '\000':
                            ii += 1
                        return ii, cy

        return len(l[cy]), cy

    def _merge_color(self, c1, c2):
        return [c1[i] * c2[i] for i in range(len(c1))]

    def setup_menus(self, m):
        if self.session and self.session.terminal:
            m.copy_cmd.enabled = self.session.terminal.has_selection()
            m.paste_cmd.enabled = self.session.terminal.has_selection() or application().query_clipboard()
            m.clear_cmd.enabled = self.session.terminal.has_selection()
            m.transfer_file_cmd.enabled = hasattr(self.session, "transfer_file")
        else:
            m.transfer_file_cmd.enabled = False
            m.copy_cmd.enabled = False
            m.paste_cmd.enabled = False
            m.clear_cmd.enabled = False

    def next_handler(self):
        return application().target_window

    def copy_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.copy_data()

    def paste_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.paste_data()

    @lru_cache(1)
    def _get_col_width(self):
        f = self._get_font()

        col_width = max(map(lambda x:self._get_width(f, x), SINGLE_WIDE_CHARACTERS))

        logging.getLogger('term_pygui').info('col_width:{}'.format(col_width))

        return col_width
