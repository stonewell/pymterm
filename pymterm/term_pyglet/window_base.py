# coding=utf-8
import logging
import string
import threading

import pyglet
from pyglet.window import key

import term.term_keyboard

import pymterm

from key_board import KeyState

SINGLE_WIDE_CHARACTERS =    \
                    " !\"#$%&'()*+,-./" \
                    "0123456789" \
                    ":;<=>?@" \
                    "ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
                    "[\\]^_`" \
                    "abcdefghijklmnopqrstuvwxyz" \
                    "{|}~" \
                    ""
LOGGER = logging.getLogger('term_pyglet')

PADDING = 5
FONT_NAME = 'WenQuanYi Micro Hei Mono'


class TermPygletWindowBase(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super(TermPygletWindowBase, self).__init__(width=1280,
                                                   height=800, *args, **kwargs)
        self.visible_cols = 132
        self.visible_rows = 24
        self._keys_handler = key.KeyStateHandler()
        self.push_handlers(self._keys_handler)
        self._key_first_down = False

    def on_resize(self, w, h):
        self.visible_cols = (w - 2 * PADDING) / 14
        self.visible_rows = (h - 2 * PADDING) / 17

        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()
        super(TermPygletWindowBase, self).on_resize(w, h)

    def on_draw(self):
        def locked_draw():
            self.clear()
            y = self.height - PADDING

            batch = pyglet.graphics.Batch()

            for text in map(lambda x:x.get_text().strip(), self.lines):
                pyglet.text.Label(text,
                    font_name=FONT_NAME,
                    font_size=14,
                    multiline=False,
                    width=self.width,
                    x=PADDING, y=y,
                    anchor_x='left', anchor_y='top',
                    batch=batch)
                y -= 17

            batch.draw()

        if (self.session):
            self.session.terminal.lock_display_data_exec(locked_draw)

    def on_show(self):
        if self.session:
            self.session.start()

    def refresh(self):
        def update(dt):
            pass

        pyglet.clock.schedule_once(update, 0)

    def on_key_press(self, symbol, modifiers):
        if pymterm.debug_log:
            LOGGER.debug('on_key_press:{}, {}'.format(
                key.symbol_string(symbol),
                key.modifiers_string(modifiers)))

        key_state = KeyState(symbol, modifiers)

        if self.session.terminal.process_key(key_state):
            if pymterm.debug_log:
                logging.getLogger('term_pygui').debug(' processed by pyterm')
            return

        v, handled = term.term_keyboard.translate_key(self.session.terminal,
                                                      key_state)

        if len(v) > 0:
            self.session.send(v)

        self._key_first_down = True

    def on_text(self, text):
        if pymterm.debug_log:
            LOGGER.debug(u'on_text:{}'.format(text))

        self.session.send(text.encode('utf_8'))

    def on_text_motion(self, motion):
        if motion == key.MOTION_BACKSPACE:
            if self._key_first_down:
                self._key_first_down = False
            else:
                self.on_key_press(key.BACKSPACE, 0)
