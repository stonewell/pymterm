import os
import select
import socket
import sys
import time
import traceback
import logging

import cap.cap_manager

import term.read_termdata
import term.parse_termdata

import term_keyboard

import session
import ssh.client

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import ObjectProperty, ListProperty
from kivy.clock import Clock
from kivy.core.window import Window

from kivy.lang import Builder
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.uix.actionbar import ActionItem
from kivy.uix.spinner import Spinner, SpinnerOption

from term.terminal import Terminal
from uix.terminal_widget_kivy import TerminalWidgetKivy, TextAttribute, TextMode

Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy.kv'))

class RootWidget(FloatLayout):
    term_panel = ObjectProperty(None)
    txt_host = ObjectProperty(None)
    txt_port = ObjectProperty(None)
    btn_connect = ObjectProperty(None)
    spnr_conn_history = ObjectProperty(None)
    
class ActionTextInput(TextInput, ActionItem):
    def __init__(self, *args, **kwargs):
        super(ActionTextInput, self).__init__(*args, **kwargs)
        self.hint_text='user@host'
        self.multiline=False
        
class ActionLabel(Label, ActionItem):
    def __init__(self, *args, **kwargs):
        super(ActionLabel, self).__init__(*args, **kwargs)

class TermTabbedPanel(TabbedPanel):
    def on_do_default_tab(self, instance, value):
        super(TermTabbedPanel, self).on_do_default_tab(instance, value)

from kivy.uix.boxlayout import BoxLayout
class TermBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(TermBoxLayout, self).__init__(**kwargs)
        self.term_widget = None
        self.started = False

    def do_layout(self, *largs):
        super(TermBoxLayout, self).do_layout(*largs)
        if not self.started:
            Clock.schedule_once(lambda ut:self.term_widget.session.start(), .5)
            self.started = True
            self.term_widget.focus = True

class TermTextInput(TerminalWidgetKivy):
    def __init__(self, **kwargs):
        super(TermTextInput, self).__init__(**kwargs)
        
        self.visible_rows = 1
        self.visible_cols = 1
        self.scroll_region = None
        
        self.session = None

    def keyboard_on_textinput(self, window, text):
        self.session.send(text)
        
    def keyboard_on_key_down(self, keyboard, keycode, text, modifiers):
        logging.getLogger('term_kivy').debug('The key {} {}'.format(keycode, 'have been pressed'))
        logging.getLogger('term_kivy').debug(' - text is %r' % text)
        logging.getLogger('term_kivy').debug(' - modifiers are %r' % modifiers)

        v, handled = term_keyboard.translate_key(self.session.terminal, keycode, text, modifiers)

        if len(v) > 0:
            self.session.send(v)

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return handled

    def cal_visible_rows(self):
        lh = self.line_height
        dy = lh + self.line_spacing
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom

        self.visible_rows = int(float(vh) / float(dy))

        if self.visible_rows == 0:
            self.visible_rows = 1

    def cal_visible_cols(self):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vw = self.width - padding_left - padding_right
        text = ''.join([chr(c) for c in range(ord('A'), ord('Z') + 1)])
        
        tw = self._get_text_width(text)

        self.visible_cols = int(float(vw) / float(tw) * 26)

        if self.visible_cols == 0:
            self.visible_cols = 1

    def on_size(self, instance, value):
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom
        vw = self.width - padding_left - padding_right
        
        self.cal_visible_rows()
        self.cal_visible_cols()

        logging.getLogger('term_kivy').debug('on size: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, vw, vh, self.size, self.pos))
        
        self.session.terminal.set_scroll_region(0, self.visible_rows - 1)

        self.session.resize_pty(self.visible_cols, self.visible_rows, vw, vh)
        self.session.terminal.refresh_display()

class TerminalKivyApp(App):
    conn_history = ListProperty([])
    
    def __init__(self, cfg):
        App.__init__(self)

        self.cfg = cfg

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & Kivy'

    def build(self):
        self.root_widget = RootWidget()

        self.root_widget.term_panel.do_default_tab = False
        self.root_widget.term_panel.bind(current_tab=self.on_current_tab)

        self.root_widget.btn_connect.bind(on_press=self.on_connect)

        self.root_widget.spnr_conn_history.bind(text=self.on_conn_history)
        return self.root_widget

    def connect_to(self, conn_str, port):
        cfg = self.cfg.clone()
        cfg.set_conn_str(conn_str)
        cfg.port = port

        for current_tab in self.root_widget.term_panel.tab_list:
            if current_tab.session.stopped:
                current_tab.session.cfg = cfg
                current_tab.session.start()
                Clock.schedule_once(lambda ut:self.root_widget.term_panel.switch_to(current_tab))
                return
            
        self.add_term_widget(cfg)
                
    def on_conn_history(self, instance, value):
        if not isinstance(value, basestring):
            return
        parts = value.split(':')

        self.connect_to(parts[0], int(parts[1]))
        
    def on_connect(self, instance):
        self.connect_to(self.root_widget.txt_host.text, int(self.root_widget.txt_port.text))
    
    def create_terminal(self, cfg):
        return TerminalKivy(cfg)

    def start(self):
        self.run()
        
    def on_start(self):
        self.add_term_widget(self.cfg.clone())

    def on_current_tab(self, instance, value):
        term_widget = self.root_widget.term_panel.current_tab.term_widget

        if term_widget:
            def update(ut):
                term_widget.focus = True
            Clock.schedule_once(update)

    def add_term_widget(self, cfg):
        layout = TermBoxLayout()

        ti = TabbedPanelHeader()
        ti.text = ' '.join([str(len(self.root_widget.term_panel.tab_list) + 1), 'Terminal'])
        ti.content = layout
        ti.size_hint = (1,1)

        self.root_widget.term_panel.add_widget(ti)
        
        term_widget = TermTextInput()
        term_widget.size_hint = (1, 1)
        term_widget.pos_hint = {'center_y':.5, 'center_x':.5}

        layout.add_widget(term_widget)
        layout.term_widget = term_widget
        
        ti.term_widget = term_widget
        ti.session = session.Session(cfg, self.create_terminal(cfg))
        
        term_widget.session = ti.session
        term_widget.tab_width = ti.session.get_tab_width()
        ti.session.term_widget = term_widget
        ti.session.terminal.term_widget = term_widget

        def start_term(dt):
            self.root_widget.term_panel.switch_to(ti)
            
        Clock.unschedule(start_term)
        Clock.unschedule(self.root_widget.term_panel._load_default_tab_content)
        Clock.schedule_once(start_term)

        conn_str = cfg.get_conn_str()

        if conn_str in self.conn_history:
            self.conn_history.remove(conn_str)

        self.conn_history.insert(0, conn_str)

    def on_stop(self):
        for current_tab in self.root_widget.term_panel.tab_list:
            current_tab.session.stop()

    def close_settings(self, *largs):
        App.close_settings(self, *largs)

class TerminalKivy(Terminal):
    def __init__(self, cfg):
        Terminal.__init__(self, cfg)
        
        self.term_widget = None
        self.session = None

        self.lines = []
        self.line_options = []
        self.col = 0
        self.row = 0

        self.last_line_option_row = -1
        self.last_line_option_col = -1
        self.cur_line_option = None
        self.saved_lines, self.saved_line_options, self.saved_cursor = [], [], (0, 0)
        self.bold_mode = False
        self.scroll_region = None
                
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
            self.save_line_option(self.cur_line_option, True)

        logging.getLogger('term_kivy').debug('save buffer:{},{},{},{}'.format(self.col, self.row, c, ord(c)))
        if insert:
            line.insert(self.col, c)
        else:
            if self.col == self.get_cols():
                self.col = 0
                self.cursor_down(None)
                self.save_buffer(c, insert)
                return
            line[self.col] = c
            self.col += 1

    def get_rows(self):
        return self.term_widget.visible_rows

    def get_cols(self):
        cols = self.term_widget.visible_cols

        return cols
    
    def get_text(self):
        if len(self.lines) <= self.get_rows():
            return self.lines + [[]] * (self.get_rows() - len(self.lines)), self.line_options + [[]] * (self.get_rows() - len(self.lines))
        else:
            lines = self.lines[len(self.lines) - self.get_rows():]
            line_options = self.line_options[len(self.lines) - self.get_rows():]
            return lines, line_options
        
    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            logging.getLogger('term_kivy').error('normal data has escape char')
            sys.exit(1)
                        
        self.save_buffer(c, insert)

    def output_status_line_data(self, c):
        if c == '\x1b':
            logging.getLogger('term_kivy').error('status line data has escape char')
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

        logging.getLogger('term_kivy').debug('termianl cursor:{}, {}'.format(self.col, self.row));
        
    def cursor_right(self, context):
        if self.col < self.get_cols() - 1:
            self.col += 1

    def cursor_left(self, context):
        if self.col > 0:
            self.col -= 1

    def cursor_down(self, context):
        self.parm_down_cursor(context)

    def cursor_up(self, context):
        begin, end = self.get_scroll_region()

        self.get_cur_line()
        self.get_cur_line_option()
        
        if self.row == begin:
            self.lines = self.lines[:begin] + [[]] + self.lines[begin:end] + self.lines[end + 1:]
            self.line_options = self.line_options[:begin] + [[]] + self.line_options[begin:end] + self.lines[end + 1:]
        else:
            self.row -= 1
            
        self.get_cur_line()
        self.get_cur_line_option()

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
        
        self.term_widget.lines = lines
        self.term_widget.line_options = line_options
        self.term_widget.cursor = self.get_cursor()
        self.term_widget.refresh()
        
    def on_data(self, data):
        Terminal.on_data(self, data)

        self.refresh_display()

    def meta_on(self, context):
        logging.getLogger('term_kivy').debug('meta_on')
                
    def get_color(self, mode, idx):
        if mode < 0:
            color_set = 0
        else:
            color_set = mode & 1

        if self.bold_mode:
            color_set = 1

        if idx < 8:
            return self.cfg.get_color(color_set * 8 + idx)
        elif idx < 16:
            return self.cfg.get_color(idx)
        elif idx < 256:
            return self.cfg.get_color(idx)
        else:
            logging.getLogger('term_kivy').error('not implemented color:{} mode={}'.format(idx, mode))
            sys.exit(1)
            
    def set_attributes(self, mode, f_color_idx, b_color_idx):
        fore_color = None
        back_color = None
        
        if f_color_idx >= 0:
            logging.getLogger('term_kivy').debug('set fore color:{} {} {}'.format(f_color_idx, ' at ', self.get_cursor()))
            fore_color = self.get_color(mode, f_color_idx)
        elif f_color_idx == -1:
            #reset fore color
            logging.getLogger('term_kivy').debug('reset fore color:{} {} {}'.format(f_color_idx, ' at ', self.get_cursor()))
            fore_color = None
        else:
            #continue
            fore_color = []

        if b_color_idx >= 0:
            logging.getLogger('term_kivy').debug('set back color:{} {} {}'.format(b_color_idx, ' at ', self.get_cursor()))
            back_color = self.get_color(mode, b_color_idx)
        elif b_color_idx == -1:
            #reset back color
            logging.getLogger('term_kivy').debug('reset back color:{} {} {}'.format(b_color_idx, ' at ', self.get_cursor()))
            back_color = None
        else:
            back_color = []

        self.save_line_option(TextAttribute(fore_color, back_color, None))
        
    def get_line_option(self, row):
        if row >= len(self.line_options):
            for i in range(len(self.line_options), row + 1):
                self.line_options.append([])

        return self.line_options[row]
                
    def get_cur_line_option(self):
        return self.get_line_option(self.row)

    def get_option_at(self, row, col):
        line_option = self.get_line_option(row)
        if len(line_option) <= col:
            while len(line_option) <= col:
                line_option.append(None)

        return line_option[col]

    def get_cur_option(self):
        return self.get_option_at(self.row, self.col)
    
    def save_line_option(self, option, clear = False):
        cur_option = self.get_cur_option()
        line_option = self.get_cur_line_option()
        
        if clear or cur_option is None:
            line_option[self.col] = option
        else:
            f_color = option.f_color if option.f_color != [] else cur_option.f_color
            b_color = option.b_color if option.b_color != [] else cur_option.b_color
            if option.mode is None:
                mode = cur_option.mode
            elif option.mode == 0 or cur_option.mode is None:
                mode = option.mode
            else:
                mode = cur_option.mode | option.mode

            line_option[self.col] = TextAttribute(f_color, b_color, mode)

        if not clear:
            self.last_line_option_row = self.row
            self.last_line_option_col = self.col
            self.cur_line_option = line_option[self.col]

    def cursor_address(self, context):
        logging.getLogger('term_kivy').debug('cursor address:{}'.format(context.params))
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
        self.session.send('\033[>0;136;0c')

    def user7(self, context):
        if (context.params[0] == 6):
            col, row = self.get_cursor()
            self.session.send(''.join(['\x1B[', str(row + 1), ';', str(col + 1), 'R']))
        elif context.params[0] == 5:
            self.session.send('\033[0n')

    def tab(self, context):
        col = self.col / self.session.get_tab_width()
        col = (col + 1) * self.session.get_tab_width();
            
        if col >= self.get_cols():
            col = self.get_cols() - 1

        self.col = col

    def row_address(self, context):
        self.set_cursor(self.col, context.params[0])

    def delete_line(self, context):
        self.parm_delete_line(context)
        
    def parm_delete_line(self, context):
        begin, end = self.get_scroll_region()
        logging.getLogger('term_kivy').debug('delete line:{} begin={} end={}'.format(context.params, begin, end))

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
        logging.getLogger('term_kivy').debug('change scroll region:{} rows={}'.format(context.params, self.get_rows()))
        self.set_scroll_region(context.params[0], context.params[1])
        
        
    def insert_line(self, context):
        self.parm_insert_line(context)
        
    def parm_insert_line(self, context):
        begin, end = self.get_scroll_region()
        logging.getLogger('term_kivy').debug('insert line:{} begin={} end={}'.format(context.params, begin, end))

        c_to_insert = context.params[0] if len(context.params) > 0 else 1
        
        for i in range(c_to_insert):
            if self.row <= end:
                self.lines = self.lines[:self.row] + [[]] + self.lines[self.row: end] +self.lines[end + 1:]

            if self.row <= end:
                self.line_options = self.line_options[:self.row] + [[]] + self.line_options[self.row: end] + self.line_options[end + 1:]

    def request_background_color(self, context):
        rbg_response = '\033]11;rgb:%04x/%04x/%04x/%04x\007' % (self.cfg.default_background_color[0], self.cfg.default_background_color[1], self.cfg.default_background_color[2], self.cfg.default_background_color[3])

        logging.getLogger('term_kivy').debug("response background color request:{}".format(rbg_response.replace('\033', '\\E')))
        self.session.send(rbg_response)

    def user9(self, context):
        logging.getLogger('term_kivy').debug('response terminal type:{} {}'.format(context.params, self.cap.cmds['user8'].cap_value))
        self.session.send(self.cap.cmds['user8'].cap_value)

    def enter_reverse_mode(self, context):
        self.set_mode(TextMode.REVERSE)

    def exit_standout_mode(self, context):
        self.set_mode(TextMode.STDOUT)

    def set_mode(self, mode):
        self.save_line_option(TextAttribute([], [], mode))
        
    def enter_ca_mode(self, context):
        self.saved_lines, self.saved_line_options, self.saved_col, self.saved_row, self.saved_bold_mode = self.lines, self.line_options, self.col, self.row, self.bold_mode
        self.lines, self.line_options, self.col, self.row, self.bold_mode = [], [], 0, 0, False

    def exit_ca_mode(self, context):
        self.lines, self.line_options, self.col, self.row, self.bold_mode = \
            self.saved_lines, self.saved_line_options, self.saved_col, self.saved_row, self.saved_bold_mode

    def key_shome(self, context):
        self.set_cursor(1, 0)

    def enter_bold_mode(self, context):
        self.bold_mode = True

    def keypad_xmit(self, context):
        logging.getLogger('term_kivy').debug('keypad transmit mode')
        self.keypad_transmit_mode = True

    def keypad_local(self, context):
        logging.getLogger('term_kivy').debug('keypad local mode')
        self.keypad_transmit_mode = False

    def cursor_invisible(self, context):
        self.term_widget.cursor_visible = False

    def cursor_normal(self, context):
        self.term_widget.cursor_visible = True

    def cursor_visible(self, context):
        self.cursor_normal(context)

    def parm_down_cursor(self, context):
        begin, end = self.get_scroll_region()

        count = context.params[0] if context and context.params and len(context.params) > 0 else 1

        for i in range(count):
            self.get_cur_line()
            self.get_cur_line_option()
        
            if self.row == end:
                self.lines = self.lines[:begin] + self.lines[begin + 1: end + 1] + [[]] + self.lines[end + 1:]
                self.line_options = self.line_options[:begin] + self.line_options[begin + 1: end + 1] + [[]] + self.line_options[end + 1:]
            else:        
                self.row += 1

            self.get_cur_line()
            self.get_cur_line_option()

    def exit_alt_charset_mode(self, context):
        self.exit_standout_mode(context)
