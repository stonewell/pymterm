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
from uix.terminal_widget_kivy import TerminalWidgetKivy

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

        self.scroll_region = None

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
        self.init_color_table()
        self.last_line_option_row = -1
        self.last_line_option_col = -1

    def get_line(self, row):
        if row >= len(self.lines):
            for i in range(len(self.lines), row + 1):
                self.lines.append([])

        self.get_line_option(row)
        
        return self.lines[row]
                
    def get_cur_line(self):
        return self.get_line(self.row)
    
    def save_buffer(self, c, insert = False):
        line = self.get_cur_line()
        self.get_cur_line_option()
        
        if len(line) <= self.col:
            while len(line) <= self.col:
                line.append(' ')

        if self.last_line_option_row != self.row or self.last_line_option_col != self.col:
            self.save_line_option(None, True)

        if insert:
            line.insert(self.col, c)
        else:
            line[self.col] = c
            self.col += 1

    def get_rows(self):
        return self.txt_buffer.visible_rows

    def get_cols(self):
        cols = self.txt_buffer.visible_cols

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
        self.set_attributes(1 if light else 0, color_idx, -2)
        
    def set_background(self, light, color_idx):
        self.set_attributes(1 if light else 0, -2, color_idx)
    
    def origin_pair(self):
        self.set_attributes(-1, -1, -1)

    def clr_eol(self, context):
        line = self.get_cur_line()
        line_option = self.get_cur_line_option()

        for i in range(self.col, len(line)):
            line[i] = ' '

        for i in range(self.col, len(line_option)):
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

    COLOR_SET_0_RATIO = 0x44
    COLOR_SET_1_RATIO = 0xaa

    #ansi color
    COLOR_TABLE = [
        [0, 0, 0, 0xFF], #BLACK
        [COLOR_SET_0_RATIO, 0, 0, 0xFF], #RED
        [0, COLOR_SET_0_RATIO, 0, 0xFF], #GREEN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0, 0xFF], #BROWN
        [0, 0, COLOR_SET_0_RATIO, 0xFF], #BLUE
        [COLOR_SET_0_RATIO, 0, COLOR_SET_0_RATIO, 0xFF], #MAGENTA
        [0, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0xFF], #CYAN
        [COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, COLOR_SET_0_RATIO, 0xFF], #LIGHT GRAY
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF], #DARK_GREY
        [0xFF, COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF], #RED
        [COLOR_SET_1_RATIO, 0xFF, COLOR_SET_1_RATIO, 0xFF], #GREEN
        [0xFF, 0xFF, COLOR_SET_1_RATIO, 0xFF], #YELLOW
        [COLOR_SET_1_RATIO, COLOR_SET_1_RATIO, 0xFF, 0xFF], #BLUE
        [0xFF, COLOR_SET_1_RATIO, 0xFF, 0xFF], #MAGENTA
        [COLOR_SET_1_RATIO, 0xFF, 0xFF, 0xFF], #CYAN
        [0xFF, 0xFF, 0xFF, 0xFF], #WHITE
        ]

    def init_color_table(self):
        for i in range(240):
            if i < 216:
                r = i / 36
                g = (i / 6) % 6
                b = i % 6
                TerminalKivy.COLOR_TABLE.append([r * 40 + 55 if r > 0 else 0,
                                                 g * 40 + 55 if g > 0 else 0,
                                                 b * 40 + 55 if b > 0 else 0,
                                                 0xFF])
            else:
                shade = (i - 216) * 10 + 8
                TerminalKivy.COLOR_TABLE.append([shade,
                                                 shade,
                                                 shade,
                                                 0xFF])
                
    def get_color(self, mode, idx):
        if mode < 0:
            color_set = 0
        else:
            color_set = mode & 1

        if idx < 8:
            return TerminalKivy.COLOR_TABLE[color_set * 8 + idx]
        elif idx < 16:
            return TerminalKivy.COLOR_TABLE[idx]
        elif idx < 256:
            return TerminalKivy.COLOR_TABLE[idx]
        else:
            print 'not implemented color', idx, mode
            sys.exit(1)
            
    def set_attributes(self, mode, f_color_idx, b_color_idx):
        fore_color = None
        back_color = None
        
        if f_color_idx >= 0:
            print 'set fore color:', f_color_idx, ' at ', self.col, self.row
            fore_color = self.get_color(mode, f_color_idx)
        elif f_color_idx == -1:
            #reset fore color
            print 'reset fore color:', f_color_idx, ' at ', self.col, self.row
            fore_color = None
        else:
            #continue
            fore_color = []

        if b_color_idx >= 0:
            print 'set back color:', b_color_idx, ' at ', self.col, self.row
            back_color = self.get_color(mode, b_color_idx)
        elif b_color_idx == -1:
            #reset back color
            print 'reset back color:', b_color_idx, ' at ', self.col, self.row
            back_color = None
        else:
            back_color = []

        self.save_line_option((fore_color, back_color))
        
    def get_line_option(self, row):
        if row >= len(self.line_options):
            for i in range(len(self.line_options), row + 1):
                self.line_options.append([])
                
        return self.line_options[row]
                
    def get_cur_line_option(self):
        return self.get_line_option(self.row)
    
    def save_line_option(self, option, clear = False):
        line_option = self.get_cur_line_option()
        if len(line_option) <= self.col:
            while len(line_option) <= self.col:
                line_option.append(None)

        if not clear and line_option[self.col]:
            f, b = option

            if f == []:
                f = line_option[self.col][0]
            if b == []:
                b = line_option[self.col][1]

            option = (f, b)
                
        line_option[self.col] = option

        if not clear:
            self.last_line_option_row = self.row
            self.last_line_option_col = self.col

    def cursor_address(self, context):
        self.set_cursor(context.params[1], context.params[0])
        
    def cursor_home(self, context):
        self.set_cursor(0, 0)

    def clr_eos(self, context):
        self.get_cur_line()
        self.get_cur_line_option()

        self.clr_eol(context)

        for row in range(self.row + 1, len(self.lines)):
            line = self.get_line(row)
            line_option = self.get_line_option(row)
            
            for i in range(len(line)):
                line[i] = ' '

            for i in range(len(line_option)):
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

    def tab(self, context):
        self.save_buffer('\t', False)

    def row_address(self, context):
        self.set_cursor(self.col, context.params[0])

    def delete_line(self, context):
        self.parm_delete_line(context)
        
    def parm_delete_line(self, context):
        begin, end = self.get_scroll_region()
        print 'delete line', context.params, begin, end

        c_to_delete = context.params[0] if len(context.params) > 0 else 1
        
        for i in range(c_to_delete):
            if self.row <= end:
                self.lines = self.lines[:self.row] + self.lines[self.row + 1: end + 1] + [[]] +self.lines[end + 1:]

            if self.row <= end:
                self.line_options = self.line_options[:self.row] + self.line_options[self.row + 1: end + 1] + [[]] + self.line_options[end + 1:]

    def get_scroll_region(self):
        if self.scroll_region:
            return self.scroll_region

        self.set_scroll_region(0, self.get_rows() - 1)

        return self.scroll_region

    def set_scroll_region(self, begin, end):
        if len(self.lines) > self.get_rows():
            begin = begin + len(self.lines) - self.get_rows()
            end = end + len(self.lines) - self.get_rows()

        self.get_line(end)
        self.get_line(begin)
        
        self.scroll_region = (begin, end)
    
    def change_scroll_region(self, context):
        print 'change scroll region', context.params, self.get_rows()
        self.set_scroll_region(context.params[0], context.params[1])
        
        
    def insert_line(self, context):
        self.parm_insert_line(context)
        
    def parm_insert_line(self, context):
        begin, end = self.get_scroll_region()
        print 'insert line', context.params, begin, end

        c_to_insert = context.params[0] if len(context.params) > 0 else 1
        
        for i in range(c_to_insert):
            if self.row <= end:
                self.lines = self.lines[:self.row] + [[]] + self.lines[self.row: end] +self.lines[end + 1:]

            if self.row <= end:
                self.line_options = self.line_options[:self.row] + [[]] + self.line_options[self.row: end] + self.line_options[end + 1:]

    def get_attributes(self, context):
        print 'get_attributes', context.params

    def user9(self, context):
        print 'terminal type', context.params, self.cap.cmds['user8'].cap_value
        self.channel.send(self.cap.cmds['user8'].cap_value)

    def enter_reverse_mode(self, context):
        pass
