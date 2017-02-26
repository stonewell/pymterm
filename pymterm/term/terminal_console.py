import sys
import session
import ssh.client
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

class TerminalConsoleApp:
	def __init__(self, cfg):
		self.cfg = cfg
		self.terminal = None
		self.session = None

	def start(self):
		self.terminal = TerminalConsole(self.cfg)
		self.session = session.Session(self.cfg, self.terminal)
		transport, channel = ssh.client.start_client(self.session, self.cfg)

		import threading
		def read_input(sock):
			while True:
				x = sys.stdin.read(1)
				if len(x) > 0:
				    sock.send(x)
				if x == 'q':
					break
		#end read_input
		reader = threading.Thread(target=read_input, args=(channel,))
		reader.start()

		self.session.wait_for_quit()
		reader.join()
		channel.close()
		transport.close()
            
		
