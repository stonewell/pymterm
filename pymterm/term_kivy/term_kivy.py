import os
import select
import socket
import sys
import time
import traceback
import term.read_termdata
import term.parse_termdata
import cap.cap_manager

import session
import ssh.client

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import ObjectProperty
from kivy.clock import Clock
from kivy.core.window import Window

from term.terminal import Terminal

from kivy.lang import Builder
from kivy.uix.textinput import TextInput

Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy.kv'))

class RootWidget(FloatLayout):
    txtBuffer = ObjectProperty(None)
    
    pass

class TermTextInput(TextInput):
	def __init__(self, **kwargs):
		super(TermTextInput, self).__init__(**kwargs)
		self._keyboard = Window.request_keyboard(
			self._keyboard_closed, self, 'text')
		if self._keyboard.widget:
			# If it exists, this widget is a VKeyboard object which you can use
			# to change the keyboard layout.
			pass
		self._keyboard.bind(on_key_down=self._on_keyboard_down)
		self.channel = None

	def _keyboard_closed(self):
		print('My keyboard have been closed!')
		self._keyboard.unbind(on_key_down=self._on_keyboard_down)
		self._keyboard = None

	def _on_keyboard_down(self, keyboard, keycode, text, modifiers):
		print('The key', keycode, 'have been pressed')
		print(' - text is %r' % text)
		print(' - modifiers are %r' % modifiers)

		# Keycode is composed of an integer + a string
		# If we hit escape, release the keyboard
		if keycode[1] == 'escape':
			keyboard.release()

		code, key = keycode

		if code < 256:
			self.channel.send(chr(code))

		# Return True to accept the key. Otherwise, it will be used by
		# the system.
		return True

	def insert_text(self, substring, from_undo=False):
		return

	def real_insert_text(self, substring, from_undo=False):
		TextInput.insert_text(self, substring, from_undo)
		                    
class TerminalKivyApp(App):
	def __init__(self, cfg):
		App.__init__(self)
		
		self.cfg = cfg
		self.session = None
		self.transport = None
		self.channel = None
		
	def build(self):
		self.root_widget = RootWidget()
		#self.root_widget.txtBuffer.focus = True
		return self.root_widget

	def terminal(self, cfg):
		return TerminalKivy(cfg, self.root_widget.txtBuffer)

	def start(self):
		self.run()
		
	def on_start(self):
		self.session = session.Session(self.cfg, self.terminal(self.cfg))
		
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

    def get_text(self):
		return '\r\n'.join([''.join(line) for line in self.lines])
	    
    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            sys.exit(1)

        self.save_buffer(c, insert)
        
        def update(dt):
            self.txt_buffer.text = self.get_text()

        Clock.schedule_once(update)

    def output_status_line_data(self, c):
        if c == '\x1b':
            sys.exit(1)
        pass
        
    def cursor_right(self, context):
        def update(dt):
	        self.txt_buffer.do_cursor_movement('cursor_right')

        Clock.schedule_once(update)

        self.col += 1

    def cursor_left(self, context):
        def update(dt):
	        self.txt_buffer.do_cursor_movement('cursor_left')

        Clock.schedule_once(update)

        if self.col > 0:
	        self.col -= 1
        
    def cursor_down(self, context):
        def update(dt):
	        self.txt_buffer.do_cursor_movement('cursor_down')

        Clock.schedule_once(update)

        self.row += 1

    def carriage_return(self, context):
        self.col = 0
        
    def set_foreground(self, light, color_idx):
	    pass
    
    def origin_pair(self):
	    pass

