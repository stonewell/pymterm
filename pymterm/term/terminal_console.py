import os
import select
import socket
import sys
import time
import traceback
import read_termdata
import parse_termdata
import cap.cap_manager

from terminal import Terminal

class TerminalConsole(Terminal):
    def __init__(self, cfg):
	    Terminal.__init__(self, cfg)

    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            sys.exit(1)
        sys.stdout.write(c)

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

                    
