import logging
import msvcrt

import client.pipe_client
import pywintypes
from session import Session
import win32event
import win32file


class PipeSession(Session):
    def __init__(self, cfg, terminal):
        super(PipeSession, self).__init__(cfg, terminal)
        
        self.p = None
        self.in_pipe = None
        self.out_pipe = None
        self.control_pipe = None
        self.out_pipe_h = None

        self._overlap_read = pywintypes.OVERLAPPED()
        self._overlap_read.hEvent = win32event.CreateEvent(None, 0, 0, None)
        
    def _read_data(self, block_size = 4096):
        if not self.p:
            return None

        try:
            r, d = win32file.ReadFile(self.out_pipe_h, block_size, self._overlap_read)

            while True:
                rc = win32event.WaitForSingleObject(self._overlap_read.hEvent, 10)
                if rc == win32event.WAIT_OBJECT_0:
                    n = win32file.GetOverlappedResult(self.out_pipe_h, self._overlap_read, True)
                    return d[:n]
                else:
                    #time out continue
                    pass
        except:
            logging.getLogger('session').exception('read data fail')
            return None

    def _stop_reader(self):
        if self.p:
            self.in_pipe.close()
            #will block, let system do it when subprocess quit
            #self.out_pipe.close
            self.p.terminate()
            self.p.wait()
            self.p = None

    def interactive_shell(self, p):
        self.p = p
        self.in_pipe = p.stdin
        self.out_pipe = p.stdout
        self.out_pipe_h = msvcrt.get_osfhandle(self.out_pipe.fileno())

        try:
            self.control_pipe = self._open_control_pipe(p)
            logging.getLogger('session').debug('get control pipe:{}'.format(self.control_pipe))
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

        if not self.control_pipe:
            logging.getLogger('session').error("resize_ptry, invalid control pipe")
            return

        win32file.WriteFile(self.control_pipe, d)
        d = win32file.ReadFile(self.control_pipe, 4)

    def _open_control_pipe(self, p):
        import time

        count = 0

        while count < 10:
            try:
                p = win32file.CreateFile(self._get_control_pipe_name(p),
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

    def _get_control_pipe_name(self, p):
        name = ''.join(['\\\\.\\pipe\\winpty-', str(p.pid)])
        return name
