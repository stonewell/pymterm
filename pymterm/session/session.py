import logging
import os
import select
import socket
import sys
import threading
import time
import traceback

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
            while True:
                data = self._read_data(4096)
                if not data:
                    logging.getLogger('session').info("end of socket, quit")
                    self.stop()
                    break
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
