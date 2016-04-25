import os
import select
import socket
import sys
import time
import traceback

import cap.cap_manager

import term.read_termdata
import term.parse_termdata

import term_keyboard

import session
import ssh.client

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window

from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label

from term.terminal import Terminal

Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy.kv'))

class RootWidget(FloatLayout):
    txtBuffer = ObjectProperty(None)
    
    pass

class TermTextInput(TextInput):
    def __init__(self, **kwargs):
        super(TermTextInput, self).__init__(**kwargs)
        self.channel = None

    def keyboard_on_textinput(self, window, text):
        self.channel.send(text)
        
    def keyboard_on_key_down(self, keyboard, keycode, text, modifiers):
        print('The key', keycode, 'have been pressed')
        print(' - text is %r' % text)
        print(' - modifiers are %r' % modifiers)

        v, handled = term_keyboard.translate_key(self.session.terminal, keycode, text, modifiers)

        if len(v) > 0:
            self.channel.send(v)

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return handled

    def insert_text(self, substring, from_undo=False):
        return

    def real_insert_text(self, substring, from_undo=False):
        TextInput.insert_text(self, substring, from_undo)

    def get_visible_rows(self):
        lh = self.line_height
        dy = lh + self.line_spacing
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom

        return int(float(vh) / float(dy))

    def get_visible_cols(self):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vw = self.width - padding_left - padding_right
        text = ''.join([chr(c) for c in range(ord('A'), ord('Z') + 1)])
        
        tw = self._get_text_width(text, self.tab_width, None)

        return int(float(vw) / float(tw) * 26)

    def on_size(self, instance, value):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom
        vw = self.width - padding_left - padding_right

        print 'cols=', self.get_visible_cols(), 'rows=', self.get_visible_rows()
        self.channel.resize_pty(self.get_visible_cols(), self.get_visible_rows(), vw, vh)

class TerminalKivyApp(App):
    def __init__(self, cfg):
        App.__init__(self)

        self.cfg = cfg
        self.session = None
        self.transport = None
        self.channel = None
        
    def build(self):
        a = TermTextInput()
        
        self.root_widget = RootWidget()
        self.root_widget.txtBuffer.focus = True
        return self.root_widget

    def terminal(self, cfg):
        return TerminalKivy(cfg, self.root_widget.txtBuffer)

    def start(self):
        self.run()
        
    def on_start(self):
        self.session = session.Session(self.cfg, self.terminal(self.cfg))
        self.root_widget.txtBuffer.session = self.session
        self.root_widget.txtBuffer.tab_width = self.session.get_tab_width()
        
        self.transport, self.channel = ssh.client.start_client(self.session, self.cfg)
        self.root_widget.txtBuffer.channel = self.channel

    def on_stop(self):
        self.channel.close()
        self.transport.close()
        self.session.wait_for_quit()

    def close_settings(self, *largs):
        App.close_settings(self, *largs)
        self.root_widget.txtBuffer.focus = True

class TerminalKivy(Terminal):
    def __init__(self, cfg, txtBuffer):
        Terminal.__init__(self, cfg)
        self.txt_buffer = txtBuffer
        self.lines = []
        self.col = 0
        self.row = 0

    def get_line(self, row):
        if row >= len(self.lines):
            for i in range(len(self.lines), row + 1):
                self.lines.append([])
                
        return self.lines[row]
                
    def get_cur_line(self):
        return self.get_line(self.row)
    
    def save_buffer(self, c, insert = False):
        line = self.get_cur_line()
        if len(line) <= self.col:
            line.append(c)
            self.col += 1
        elif insert:
            line.insert(self.col, c)
        else:
            line[self.col] = c
            self.col += 1

    def get_rows(self):
        return self.txt_buffer.get_visible_rows()

    def get_cols(self):
        cols =  self.txt_buffer.get_visible_cols()

        return cols
    
    def get_text(self):
        if len(self.lines) <= self.get_rows():
            return '\r\n'.join([''.join(line) for line in self.lines])
        else:
            return '\r\n'.join([''.join(line) for line in self.lines[len(self.lines) - self.get_rows():]])
        
    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            print 'normal data has escape char'
            sys.exit(1)
                        
        self.save_buffer(c, insert)

    def output_status_line_data(self, c):
        if c == '\x1b':
            print 'status line data has escape char'
            sys.exit(1)
        pass
        
    def cursor_right(self, context):
        self.col += 1

    def cursor_left(self, context):
        if self.col > 0:
            self.col -= 1

    def cursor_down(self, context):
        self.row += 1

    def cursor_up(self, context):
        if self.row > 0:
            self.row -= 1

    def carriage_return(self, context):
        self.col = 0
        
    def set_foreground(self, light, color_idx):
        pass
    
    def origin_pair(self):
        pass

    def clr_eol(self, context):
        line = self.get_cur_line()
        for i in range(self.col, len(line)):
            line[i] = ' '

    def delete_chars(self, count):
        line = self.get_cur_line()
        for i in range(self.col, len(line)):
            if i + count < len(line):
                line[i] = line[i + count]
            else:
                line[i] = ' '

    def refresh_display(self):
        def update_cursor(dt):
            self.txt_buffer.cursor = [self.col, self.row]
        
        def update(dt):
            self.txt_buffer.text = self.get_text()
            Clock.schedule_once(update_cursor)

        Clock.schedule_once(update)

    def on_data(self, data):
        Terminal.on_data(self, data)

        self.refresh_display()

    def meta_on(self, context):
        print 'meta_on'
