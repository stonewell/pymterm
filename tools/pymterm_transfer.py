#!/usr/bin/env python
import os
import sys
import json

if len(sys.argv) < 2:
    sys.exit(0)

action = sys.argv[1].lower()
print sys.argv

if action != 'upload' and action != 'download':
    sys.exit(1)

if action == 'download' and len(sys.argv) < 3:
    sys.exit(2)

cmd = {}
cmd['ACTION'] = action.upper()
cmd['HOME'] = os.path.expanduser('~')
cmd['PWD'] = os.path.abspath('.')
cmd['R_F'] = sys.argv[2] if action == 'download' else ''

print r'\033]0;PYMTERM_STATUS_CMD={}\007'.format(json.dumps(cmd))
print '\033]0;PYMTERM_STATUS_CMD={}\007'.format(json.dumps(cmd))
