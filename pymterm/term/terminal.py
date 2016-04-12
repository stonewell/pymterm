import os
import select
import socket
import sys
import time
import traceback
import read_termdata
import parse_termdata

class Terminal:
    def __init__(self, cfg):
        self.cfg = cfg

        self.cap_str = self.__load_cap_str__(self.cfg.term_name) + self.__load_cap_str__('generic-color')
        self.cap = parse_termdata.parse_cap(self.cap_str)
        self.context = parse_termdata.ControlDataParserContext()
        self.state = self.cap.control_data_start_state
        self.control_data = []

    def __load_cap_str__(self, term_name):
        term_path = os.path.dirname(os.path.realpath(__file__))
        term_path = os.path.join(term_path, '..', '..', 'data', term_name+'.dat')
        return read_termdata.get_entry(term_path, term_name)

    def on_data(self, data):
        self.__try_parse__(data)

    def on_control_data(self, cap_turple):
        cap_name, increase_params = cap_turple
        print 'matched:', cap_turple, self.context.params
        if cap_name == 'carriage_return':
            sys.stdout.write('\r\n')

    def output_data(self, c):
        sys.stdout.write(c)

    def __try_parse__(self, data):	
        next_state = None

        for c in data:
            next_state = self.state.handle(self.context, c)

            if not next_state or self.state.get_cap(self.context.params):
                cap_turple = self.state.get_cap(self.context.params)

                if cap_turple:
                    self.on_control_data(cap_turple)
                    d = ''.join(self.control_data)
                    self.output_data(d.replace('\\E', '\x1B'))
                elif len(self.control_data) > 0:
                    print 'current state:', self.state.cap_name, self.context.params
                    print "unknown control data:" + ''.join(self.control_data)

                    d = ''.join(self.control_data)
                    self.output_data(d.replace('\\E', '\x1B'))
                    pass

                self.state = self.cap.control_data_start_state
                self.context.params = []
                self.output_data(c)
                self.control_data = []
                
                continue

            self.state = next_state
            self.control_data.append(c if not c == '\x1B' else '\\E')
        
