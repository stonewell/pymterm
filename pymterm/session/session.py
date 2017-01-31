import logging
import os
import select
import socket
import sys
import threading
import time
import traceback
import struct

class Session(object):
    def __init__(self, cfg, terminal):
        self.cfg = cfg
        self.terminal = terminal
        self.terminal.session = self
        self.reader_thread = None
        self.stopped = True

    def report_error(self, msg):
        logging.getLogger('session').error(msg)

        if hasattr(self.terminal, 'report_error'):
            self.terminal.report_error(msg)

    def _start_reader(self):
        def read_term_data():
            if self.cfg.load_data:
                with open(self.cfg.load_data, 'rb') as f:
                    count = 0
                    while True:
                        print '1', count
                        data = f.read(4)
                        print '2', count, ord(data[0]), ord(data[1]), ord(data[2]), ord(data[3])
                        if not data or len(data) != 4:
                            logging.getLogger('session').info("end of dump data, quit")
                            self.stop()
                            break
                        data_len = struct.unpack('!i', data)[0]
                        print '4', count, data_len
                        data = f.read(data_len)
                        if not data or data_len != len(data):
                            logging.getLogger('session').info("end of dump data, quit")
                            self.stop()
                            break
                        print '5', count
                        self.terminal.on_data(data)
                        print '3', count
                        count += 1
                    return
                
            while True:
                data = self._read_data(4096)
                if not data:
                    logging.getLogger('session').info("end of socket, quit")
                    self.stop()
                    break

                if self.cfg.dump_data:
                    with open(self.cfg.dump_data, 'w') as f:
                        print len(data), [ord(x) for x in struct.pack('!i', len(data))]
                        f.write(struct.pack('!i', len(data)))
                        f.write(data)
                        f.flush()
                self.terminal.on_data(data)

        self.reader_thread = reader_thread = threading.Thread(target=read_term_data)
        reader_thread.start()

    def _wait_for_quit(self):
        if self.reader_thread and threading.current_thread() != self.reader_thread:
            self.reader_thread.join()

    def get_tab_width(self):
        return self.terminal.get_tab_width()

    def stop(self):
        if self.stopped:
            return

        self.stopped = True

        if not self.cfg.load_data:
            self._stop_reader()

        self._wait_for_quit()

    def _stop_reader(self):
        pass

    def start(self):
        if not self.stopped:
            return

        self.stopped = False

    def send(self, data):
        pass

    def resize_pty(self, col, row, w, h):
        pass
