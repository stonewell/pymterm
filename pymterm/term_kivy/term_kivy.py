import logging
import os
import select
import socket
import sys
import time
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.properties import ObjectProperty, ListProperty
from kivy.uix.actionbar import ActionItem
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelHeader
from kivy.uix.textinput import TextInput

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
import term.term_keyboard

from uix.term_kivy_login import prompt_login as pl
from uix.term_kivy_password import prompt_password as pp
from uix.terminal_widget_kivy import TerminalWidgetKivy

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

class TermBoxLayout(BoxLayout):
    def __init__(self, **kwargs):
        super(TermBoxLayout, self).__init__(**kwargs)
        self.term_widget = None
        self.started = False
        self.trigger_start_session = Clock.create_trigger(self.start_session, .5)

    def start_session(self, *largs):
        self.term_widget.session.start()

    def do_layout(self, *largs):
        super(TermBoxLayout, self).do_layout(*largs)
        if not self.started:
            self.started = True
            self.term_widget.focus = True
            self.trigger_start_session()

class TermTextInput(TerminalWidgetKivy):
    def __init__(self, session, **kwargs):
        super(TermTextInput, self).__init__(session, **kwargs)

        self.visible_rows = 1
        self.visible_cols = 1
        self.scroll_region = None

        self.keyboard_handled = False

    def keyboard_on_textinput(self, window, text):
        if self.keyboard_handled:
            return True

        logging.getLogger('term_kivy').debug('key board send text {}'.format(text))
        self.session.send(text)
        return True

    def keyboard_on_key_down(self, keyboard, keycode, text, modifiers):
        logging.getLogger('term_kivy').debug('The key {} {}'.format(keycode, 'have been pressed'))
        logging.getLogger('term_kivy').debug(' - text is %r' % text)
        logging.getLogger('term_kivy').debug(' - modifiers are %r' % modifiers)

        if self.session.terminal.process_key(keycode, text, modifiers):
            self.keyboard_handled = True
            return True

        v, handled = term.term_keyboard.translate_key(self.session.terminal, keycode, text, modifiers)

        if len(v) > 0:
            self.session.send(v)

        logging.getLogger('term_kivy').debug(' - translated %r, %d' % (v, handled))

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        self.keyboard_handled = handled
        return handled

    def cal_visible_rows(self):
        lh = self.line_height
        dy = lh + self.line_spacing
        padding_left, padding_top, padding_right, padding_bottom = self.padding
        vh = self.height - padding_top - padding_bottom

        self.visible_rows = int(float(vh) / float(dy) + 0.1)

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

        self.session.resize_pty(self.visible_cols, self.visible_rows, vw, vh)
        self.session.terminal.resize_terminal()
        self.session.terminal.refresh_display()

class TerminalKivyApp(App):
    conn_history = ListProperty([])

    def __init__(self, cfg):
        App.__init__(self)

        self.cfg = cfg
        self.current_tab = None

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & Kivy'

    def build(self):
        self.root_widget = RootWidget()

        self.root_widget.term_panel.do_default_tab = False
        self.root_widget.term_panel.bind(current_tab=self.on_current_tab)

        self.root_widget.btn_connect.bind(on_press=self.on_connect)

        self.root_widget.spnr_conn_history.bind(text=self.on_conn_history)

        self.trigger_switch_to_tab = Clock.create_trigger(self._switch_to_tab)

        return self.root_widget

    def _switch_to_tab(self, *largs):
        if not self.current_tab:
            return
        self.root_widget.term_panel.switch_to(self.current_tab)

    def switch_to_tab(self, current_tab):
        self.current_tab = current_tab
        self.trigger_switch_to_tab()

    def connect_to(self, conn_str, port):
        cfg = self.cfg.clone()
        cfg.set_conn_str(conn_str)
        cfg.port = port
        cfg.session_type = 'ssh'

        for current_tab in self.root_widget.term_panel.tab_list:
            if current_tab.session.stopped:
                current_tab.session.cfg = cfg
                current_tab.session.start()
                self.switch_to_tab(current_tab)
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
            Clock.unschedule(update)
            Clock.schedule_once(update)

    def add_term_widget(self, cfg):
        layout = TermBoxLayout()

        ti = TabbedPanelHeader()
        ti.text = ' '.join([str(len(self.root_widget.term_panel.tab_list) + 1), 'Terminal'])
        ti.content = layout
        ti.size_hint = (1,1)

        self.root_widget.term_panel.add_widget(ti)

        session = create_session(cfg, self.create_terminal(cfg))

        term_widget = TermTextInput(session)
        term_widget.size_hint = (1, 1)
        term_widget.pos_hint = {'center_y':.5, 'center_x':.5}

        layout.add_widget(term_widget)
        layout.term_widget = term_widget

        ti.term_widget = term_widget
        ti.session = session

        ti.session.term_widget = term_widget
        ti.session.terminal.term_widget = term_widget

        Clock.unschedule(self.root_widget.term_panel._load_default_tab_content)
        self.switch_to_tab(ti)

        conn_str = cfg.get_conn_str()

        if conn_str in self.conn_history:
            self.conn_history.remove(conn_str)

        self.conn_history.insert(0, conn_str)

    def on_stop(self):
        for current_tab in self.root_widget.term_panel.tab_list:
            current_tab.session.stop()

    def close_settings(self, *largs):
        App.close_settings(self, *largs)

class TerminalKivy(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalKivy, self).__init__(cfg)

    def prompt_login(self, t, username):
        pl(self, t, username)

    def prompt_password(self, action):
        pp(action)
