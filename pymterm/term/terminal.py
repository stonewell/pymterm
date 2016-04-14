import os
import select
import socket
import sys
import time
import traceback
import read_termdata
import parse_termdata
import cap.cap_manager

class Terminal:
    def __init__(self, cfg):
        self.cfg = cfg

        try:
            self.cap_str = self.__load_cap_str__(self.cfg.term_name)
        except:
            self.cap_str = self.__load_cap_str__('xterm-256color')

        self.cap_str += self.__load_cap_str__('generic-color')
        self.cap = parse_termdata.parse_cap(self.cap_str)
        self.context = parse_termdata.ControlDataParserContext()
        self.state = self.cap.control_data_start_state
        self.control_data = []
        self.in_status_line = False

    def __load_cap_str__(self, term_name):
        term_path = os.path.dirname(os.path.realpath(__file__))
        term_path = os.path.join(term_path, '..', '..', 'data', term_name+'.dat')
        return read_termdata.get_entry(term_path, term_name)

    def on_data(self, data):
        self.__try_parse__(data)

    def on_control_data(self, cap_turple):
        cap_name, increase_params = cap_turple
        cap_handler = cap.cap_manager.get_cap_handler(cap_name)

        if not cap_handler:
            print 'matched:', cap_turple, self.context.params
        elif cap_handler:
            cap_handler.handle(self, self.context, cap_turple)

    def output_data(self, c):
        if self.in_status_line:
            self.output_status_line_data(c)
        else:
            self.output_normal_data(c)

    def __try_parse__(self, data):	
        next_state = None

        for c in data:
            next_state = self.state.handle(self.context, c)

            if not next_state or self.state.get_cap(self.context.params):
                cap_turple = self.state.get_cap(self.context.params)

                if cap_turple:
                    self.on_control_data(cap_turple)
                elif len(self.control_data) > 0:
                    print 'current state:', self.state.cap_name, self.context.params
                    print "unknown control data:" + ''.join(self.control_data) + "," + c

                    sys.exit(1)

                self.state = self.cap.control_data_start_state
                self.context.params = []
                self.control_data = []

                if cap_turple:
                    # retry last char
                    next_state = self.state.handle(self.context, c)

                    if next_state:
                        self.state = next_state
                        self.control_data.append(c if not c == '\x1B' else '\\E')
                    else:
                        self.output_data(c)
                else:
                    self.output_data(c)
                
                continue

            self.state = next_state
            self.control_data.append(c if not c == '\x1B' else '\\E')
        
    def enter_status_line(self, enter):
        self.in_status_line = enter
