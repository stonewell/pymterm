import os
import select
import socket
import sys
import time
import traceback
import logging
import threading

import client.pipe_client

from session import Session

class PipeSession(Session):
    def __init__(self, cfg, terminal):
        super(PipeSession, self).__init__(cfg, terminal)
        
        self.p = None
        self.in_pipe = None
        self.out_pipe = None
        self.control_pipe_r = None
        self.control_pipe_w = None
        self._control_pipe_reader_thread = None
        
    def _read_data(self, block_size = 4096):
        if not self.p:
            return None

        d = self.out_pipe.read(1)
        return d

    def _stop_reader(self):
        if self.p:
            self.in_pipe.close()
            self.out_pipe.close()
            self.p.terminate()
            self.p.wait()
            self.p = None

            if self._control_pipe_reader_thread and threading.current_thread() != self._control_pipe_reader_thread:
                self._control_pipe_reader_thread.join()

    def interactive_shell(self, p):
        self.p = p
        self.in_pipe = p.stdin
        self.out_pipe = p.stdout

        try:
            self.control_pipe_r = self._open_control_pipe(p, True)
            self.control_pipe_w = self._open_control_pipe(p, False)
            logging.getLogger('session').error('get control pipe:{}, {}'.format(self.control_pipe_r, self.control_pipe_w))
            self._start_control_pipe_reader()
        except:
            logging.getLogger('session').exception('unable to open control pipe')

        self._start_reader()
        
        self.resize_pty()
        
    def start(self):
        super(PipeSession, self).start()
        
        client.pipe_client.start_client(self, self.cfg)

    def send(self, data):
        if self.p and not self.stopped:
            in_pipe = self.in_pipe

            in_pipe.write(data)

    def resize_pty(self, col = None, row = None, w = 0, h = 0):
        from struct import pack
        f = '=QBiBiBi'

        if not col:
            col = self.terminal.get_cols()
        if not row:
            row = self.terminal.get_rows()
            
        size = 8 + 3 * 4 + 3 * 1
        d = pack(f,
                 size, #Size
                 0,#Int32
                 2, #SetSize Message
                 0,#Int32
                 col,#Int32
                 0,#Int32
                 row)

        if not self.control_pipe_r:
            logging.getLogger('session').error("resize_ptry, invalid control pipe")
            return

        logging.getLogger('session').error('{}'.format(map(ord, d)))
        import win32pipe, win32file
        import win32file

        logging.getLogger('session').error('write file:{}, {}'.format(len(d), self.control_pipe_r))
        win32file.WriteFile(self.control_pipe_r, d)
        logging.getLogger('session').error('write file:{} done'.format(d))

    def _open_control_pipe(self, p, read):
        import win32pipe, win32file
        import win32file
        import time

        count = 0

        while count < 10:
            try:
                p = win32file.CreateFile(self._get_control_pipe_name(p, read),
                                        win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                                        0, None,
                                        win32file.OPEN_EXISTING,
                                        0, None)

                return p
            except:
                count += 1
                time.sleep(1)
                pass

        logging.getLogger('session').exception('unable to get control pipe')
        return None

    def _get_control_pipe_name(self, p, read):
        name = ''.join(['\\\\.\\pipe\\winpty-', 'read' if read else 'write', '-', str(p.pid)])
        print name
        return name

    def _start_control_pipe_reader(self):
        if not self.control_pipe_w:
            logging.getLogger('session').error("start control reader invalid control pipe")
            return
        
        import win32pipe, win32file
        import win32file

        def read_term_data():
            while True:
                data = win32file.ReadFile(self.control_pipe_w, 1)
                if not data or len(data) == 0:
                    logging.getLogger('session').info("end of socket, quit")
                    self.stop()
                    break

        self._control_pipe_reader_thread = reader_thread = threading.Thread(target=read_term_data)
        reader_thread.start()
    
