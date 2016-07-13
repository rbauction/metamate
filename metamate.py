#!/usr/bin/env python

import argparse
import sys

from deploy import cmd_deploy
from sfdclib import SfdcLogger


# Declare command line arguments and switches
parser = argparse.ArgumentParser(description='Manipulates Salesforce metadata')
parser.add_argument('command', type=str,
                    help='command')
parser.add_argument('-u', '--username', type=str,
                    help='Salesforce user name')
parser.add_argument('-p', '--password', type=str,
                    help='password')
parser.add_argument('-t', '--token', type=str,
                    help='security token')
parser.add_argument('-d', '--deploy-zip', type=str,
                    help='path to deploy.zip')
parser.add_argument('-s', '--source-dir', type=str,
                    help='path to directory containing metadata')
parser.add_argument('--sandbox', dest='sandbox', action='store_true',
                    help='use this switch when working with sandbox')
parser.add_argument('-v', '--version', type=str,
                    help='API version (i.e. 32.0, 33.0, etc)')
args = parser.parse_args()

log = SfdcLogger()

# Execute method corresponding to the command specified
if args.command.lower() == 'deploy':
    ret = cmd_deploy(args, log)
else:
    log.err("Unknown command [%s]" % args.command)
    sys.exit(1)

if not ret:
    log.err("Command failed")
    sys.exit(2)

sys.exit(0)
