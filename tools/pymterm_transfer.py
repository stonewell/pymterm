#!/usr/bin/env python
import os
import sys
import json
import argparse

def do_transfer(action, target):
    if action.upper() == 'DOWNLOAD' and not os.path.isfile(target):
        parse_args().print_help()
        sys.exit(0)

    cmd = {}
    cmd['ACTION'] = action.upper()
    cmd['HOME'] = os.path.expanduser('~')
    cmd['PWD'] = os.path.abspath('.')
    cmd['R_F'] = target if target else ''

    print '\033]0;PYMTERM_STATUS_CMD={}\007'.format(json.dumps(cmd))

def parse_args():
    parser = argparse.ArgumentParser(description='helper scripts for upload/download files using sftp in command line')
    sub_parsers = parser.add_subparsers(help='transfer action help', dest='action')

    upload_parser = sub_parsers.add_parser('upload', help='upload file from local system to remote')
    upload_parser.add_argument('target', type=str, nargs='?', help='upload target file remote path')

    download_parser = sub_parsers.add_parser('download', help='download file from remote system to local')
    download_parser.add_argument('target', type=str, help='download file remote path')

    return parser

if __name__ == '__main__':
    args = parse_args().parse_args()

    do_transfer(args.action, args.target)
