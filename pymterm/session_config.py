import os
import sys

class SessionConfig:
    def __init__(self):
        self.term_name = 'xterm-256color'
#        self.hostname = 'angelstone-pi.local'
#        self.username = 'pi'
#        self.hostname = 'localhost'
#        self.username = 'stone'
        self.hostname = 'D-235027-B'
        self.username = 'stone'
        self.port = 22
        self.is_logging = False
        self.log_file_path = 'pymterm.log'
