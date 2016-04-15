import os
import select
import socket
import sys
import time
import traceback
import term.read_termdata
import term.parse_termdata
import cap.cap_manager

from kivy.uix.floatlayout import FloatLayout
from kivy.app import App
from kivy.properties import ObjectProperty

from term.terminal import Terminal

class RootWidget(FloatLayout):
    txtBuffer = ObjectProperty(None)
    pass


class TerminalKivyApp(App):
    def build(self):
	self.root_widget = RootWidget()
	self.root_widget.txtBuffer.focus = True
        return self.root_widget

    def terminal(self, cfg):
        return TerminalKivy(cfg, self.root_widget.txtBuffer)

class TerminalKivy(Terminal):
    def __init__(self, cfg, txtBuffer):
        Terminal.__init__(self, cfg)
        self.txt_buffer = txtBuffer

    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            sys.exit(1)

        self.txt_buffer.insert_text(c, False)

    def output_status_line_data(self, c):
        if c == '\x1b':
            sys.exit(1)
        pass
        
    def cursor_right(self, context):
        sys.stdout.write('\x1B[C')

    def cursor_left(self, context):
        sys.stdout.write(chr(ord('H') - ord('A') + 1))
        
    def cursor_down(self, context):
        sys.stdout.write(chr(ord('J') - ord('A') + 1))

    def carriage_return(self, context):
        sys.stdout.write(chr(ord('M') - ord('A') + 1))
        
    def set_foreground(self, light, color_idx):
	if light:
	    sys.stdout.write('\x1B[%d;3%dm' % (light, color_idx))
        else:
            sys.stdout.write('\x1B[3%dm' % (light, color_idx))
	    
    def origin_pair(self):
	sys.stdout.write('\x1B[0m')


if __name__ == '__main__':
    TerminalKivyApp().run()
