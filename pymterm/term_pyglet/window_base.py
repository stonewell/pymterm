#coding=utf-8
import logging
import string
import threading

import pyglet

from functools32 import lru_cache

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, reserve, get_default_text_attribute
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget

import pymterm

SINGLE_WIDE_CHARACTERS =	\
					" !\"#$%&'()*+,-./" \
					"0123456789" \
					":;<=>?@" \
					"ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
					"[\\]^_`" \
					"abcdefghijklmnopqrstuvwxyz" \
					"{|}~" \
					""

class TermPygletWindowBase(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super(TermPygletWindowBase, self).__init__(width=1440, height=1024, *args, **kwargs)
        self.visible_cols = 80
        self.visible_rows = 24

    def on_resize(self, w, h):
        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()
        super(TermPygletWindowBase, self).on_resize(w, h)

    def on_draw(self):
        def locked_draw():
            self.clear()
            y = self.height

            text = '\n'.join(map(lambda x:x.get_text().strip(), self.lines))

            label = pyglet.text.Label(text,
                            font_name='Monospace',
                            font_size=14,
                            multiline=True,
                            width=self.width,
                            x=0, y=y,
                            anchor_x='left', anchor_y='top')
            label.draw()

        if (self.session):
            self.session.terminal.lock_display_data_exec(locked_draw)

    def on_show(self):
        if self.session:
            self.session.start()
            
    def refresh(self):
        def update(dt):
            pass 

        pyglet.clock.schedule_once(update, .1)

    ## def on_key_press(self, symbol, modifiers):
    ##     self.session.send(chr(symbol))

    ##     if pymterm.debug_log:
    ##         logging.getLogger('term_pygui').debug(' - translated %r, %d' % (v, handled))

    ##     # Return True to accept the key. Otherwise, it will be used by
    ##     # the system.
    ##     return

    def on_text(self, text):
        self.session.send(text)
