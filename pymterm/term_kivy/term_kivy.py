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
from uix.TerminalWidgetKivy import TerminalWidgetKivy

Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy.kv'))

class RootWidget(FloatLayout):
    txtBuffer = ObjectProperty(None)
    
    pass

class TermTextInput(TerminalWidgetKivy):
    def __init__(self, **kwargs):
        super(TermTextInput, self).__init__(**kwargs)
        self.channel = None
        self.visible_rows = 0
        self.visible_cols = 0

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

    def cal_visible_rows(self):
        lh = self.line_height
        dy = lh + self.line_spacing
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom

        self.visible_rows = int(float(vh) / float(dy))

    def cal_visible_cols(self):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vw = self.width - padding_left - padding_right
        text = ''.join([chr(c) for c in range(ord('A'), ord('Z') + 1)])
        
        tw = self._get_text_width(text)

        self.visible_cols = int(float(vw) / float(tw) * 26)

    def on_size(self, instance, value):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom
        vw = self.width - padding_left - padding_right
        
        self.cal_visible_rows()
        self.cal_visible_cols()

        print 'on size:', self.visible_cols, self.visible_rows, vw, vh, self.size
        
        self.channel.resize_pty(self.visible_cols, self.visible_rows, vw, vh)

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
        self.session.terminal.channel = self.channel

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
        self.line_options = []
        self.col = 0
        self.row = 0
        self.channel = None

    def get_line(self, row):
        if row >= len(self.lines):
            for i in range(len(self.lines), row + 1):
                self.lines.append([])
                
        return self.lines[row]
                
    def get_cur_line(self):
        return self.get_line(self.row)
    
    def save_buffer(self, c, insert = False):
        line = self.get_cur_line()
        self.get_cur_line_option()
        
        if len(line) <= self.col:
            while len(line) <= self.col:
                line.append(' ')

        if insert:
            line.insert(self.col, c)
        else:
            line[self.col] = c
            self.col += 1

    def get_rows(self):
        return self.txt_buffer.visible_rows

    def get_cols(self):
        cols =  self.txt_buffer.visible_cols

        return cols
    
    def get_text(self):
        if len(self.lines) <= self.get_rows():
            return self.lines, self.line_options
        else:
            lines = self.lines[len(self.lines) - self.get_rows():]
            line_options = self.line_options[len(self.lines) - self.get_rows():]
            return lines, line_options
        
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

    def get_cursor(self):
        if len(self.lines) <= self.get_rows():
            return (self.col, self.row)
        else:
            return (self.col, self.row - len(self.lines) + self.get_rows())

    def set_cursor(self, col, row):
        self.col = col
        if len(self.lines) <= self.get_rows():
            self.row = row
        else:
            self.row = row + len(self.lines) - self.get_rows()
        
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
        self.set_attributes(1 if light else 0, color_idx, -1)
    
    def origin_pair(self):
        self.set_attributes(-1, -1, -1)

    def clr_eol(self, context):
        line = self.get_cur_line()
        line_option = self.get_cur_line_option()
        
        for i in range(self.col, len(line)):
            line[i] = ' '

            if i < len(line_option):
                line_option[i] = None

    def delete_chars(self, count):
        line = self.get_cur_line()
        for i in range(self.col, len(line)):
            if i + count < len(line):
                line[i] = line[i + count]
            else:
                line[i] = ' '

    def refresh_display(self):
        lines, line_options = self.get_text()
        
        self.txt_buffer.lines = lines
        self.txt_buffer.line_options = line_options
        self.txt_buffer.refresh()
        
    def on_data(self, data):
        Terminal.on_data(self, data)

        self.refresh_display()

    def meta_on(self, context):
        print 'meta_on'

    COLOR_SET_0_RATIO = float(0x44) / 0xff
    COLOR_SET_1_RATIO = float(0xaa) / 0xff

    #ansi color
    COLOR_TABLE = [
        [0, 0, 0, 1], #BLACK
        [COLOR_SET_0_RATIO, 0, 0, 1], #RED
        [0, COLOR_SET_0_RATIO, 0, 1], #GREEN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0, 1], #BROWN
        [0, 0, COLOR_SET_0_RATIO, 1], #BLUE
        [COLOR_SET_0_RATIO, 0, COLOR_SET_0_RATIO, 1], #MAGENTA
        [0, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 1], #CYAN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 1], #LIGHT GRAY
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 1], #DARK_GREY
        [1, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 1], #RED
        [COLOR_SET_1_RATIO, 1, COLOR_SET_1_RATIO, 1], #GREEN
        [1, 1, COLOR_SET_1_RATIO, 1], #YELLOW
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 1, 1], #BLUE
        [1, COLOR_SET_1_RATIO, 1, 1], #MAGENTA
        [COLOR_SET_1_RATIO, 1, 1, 1], #CYAN
        [1, 1, 1, 1], #WHITE
        ]

    def get_color(self, mode, idx):
        if mode < 0:
            color_set = 0
        else:
            color_set = mode & 1

        if idx < 8:
            return TerminalKivy.COLOR_TABLE[color_set * 8 + idx]
        elif idx < 16:
            return TerminalKivy.COLOR_TABLE[idx]
        else:
            print 'not implemented 256 color'
            sys.exit(1)
            
    def set_attributes(self, mode, f_color_idx, b_color_idx):
        fore_color = None
        back_color = None
        
        if f_color_idx >= 0:
            print 'set fore color:', f_color_idx, ' at ', self.col, self.row
            fore_color = self.get_color(mode, f_color_idx)
        else:
            #reset fore color
            print 'reset fore color:', f_color_idx, ' at ', self.col, self.row
            fore_color = self.get_color(mode, 7)

        if b_color_idx >= 0:
            print 'set back color:', b_color_idx, ' at ', self.col, self.row
            back_color = self.get_color(mode, b_color_idx)
        else:
            #reset back color
            print 'reset back color:', b_color_idx, ' at ', self.col, self.row
            back_color = self.get_color(mode, 0)

        self.save_line_option((fore_color, back_color))
        
    def get_line_option(self, row):
        if row >= len(self.line_options):
            for i in range(len(self.line_options), row + 1):
                self.line_options.append([])
                
        return self.line_options[row]
                
    def get_cur_line_option(self):
        return self.get_line_option(self.row)
    
    def save_line_option(self, option):
        line_option = self.get_cur_line_option()
        if len(line_option) <= self.col:
            while len(line_option) <= self.col:
                line_option.append(None)
                
        line_option[self.col] = option

    def cursor_address(self, context):
        self.set_cursor(context.params[1], context.params[0])
        
    def cursor_home(self, context):
        if len(self.lines) <= self.get_rows():
            self.col = 0
            self.row = 0
        else:
            self.col = 0
            self.row = len(self.lines) - self.get_rows()

    def clr_eos(self, context):
        self.get_cur_line()
        self.get_cur_line_option()

        self.clr_eol(context)

        for row in range(self.row + 1, len(self.lines)):
            line = self.get_line(row)
            line_option = self.get_line_option(row)
            
            for i in range(len(line)):
                line[i] = ' '
                if i < len(line_option):
                    line_option[i] = None

    def parm_right_cursor(self, context):
        self.col += context.params[0]

    def client_report_version(self, context):
        self.channel.send('\033[>0;136;0c')

    def user7(self, context):
        if (context.params[0] == 6):
            col, row = self.get_cursor()
            self.channel.send(''.join(['\x1B[', str(row + 1), ';', str(col + 1), 'R']))
        elif context.params[0] == 5:
            self.channel.send('\033[0n')

