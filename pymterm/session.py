import os
import select
import socket
import sys
import time
import traceback

from term.terminal_console import TerminalConsole

class Session:
    def __init__(self, cfg):
        self.cfg = cfg
        self.terminal = TerminalConsole(cfg)

    def connect(self):
        username = self.cfg.username
        hostname = self.cfg.hostname
        port = self.cfg.port

        # now connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((hostname, port))

            return sock
        except Exception as e:
            print('*** Connect failed: ' + str(e))
            traceback.print_exc()
            self.report_error("connect to %s@%s:%d failed." % (username, hostname, port))

        return None

    def report_error(self, msg):
        print('^^^^ ' + msg);

    def interactive_shell(self, chan):
        chan.get_pty(term=self.cfg.term_name, width=160)
        chan.invoke_shell()
        self.windows_shell(chan)

    def windows_shell(self, chan):
        import threading

        def writeall(sock):
            while True:
                data = sock.recv(256)
                if not data:
                    sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
                    sys.stdout.flush()

                    sock.send('ls\n');
                    
                    r, w, e = select.select([sock.fileno()], [], [])

                    if sys.stdin.fileno() in r:
                        x = sys.stdin.read(1)
                        if len(x) > 0:
                            sock.send(x)
                        if x == 'q':
	                        break
                    continue
                self.terminal.on_data(data)

        chan.send('echo $TERM\x01abc\r\n')
        chan.send('ls\r\n')
        chan.send('exit\r\n')
        writer = threading.Thread(target=writeall, args=(chan,))
        writer.start()
        writer.join()
