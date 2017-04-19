import hotshot, hotshot.stats
import pymterm.pymterm
import os
import sys

sys.path.append('pymterm')
log_file = 'pymterm.prof'
prof = hotshot.Profile(log_file)
prof.runcall(pymterm.pymterm.pymterm_main)
prof.close()
stats = hotshot.stats.load(log_file)
stats.strip_dirs()
stats.sort_stats('time', 'calls')
stats.print_stats(20)
os._exit(0)
