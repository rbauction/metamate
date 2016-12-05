#!/usr/bin/env python
""" Metamate tool main entry point """

import argparse
import sys

from metamatelib.deploy import DeployCommand
from metamatelib.metamatecache import MetamateCache
from sfdclib import SfdcLogger


def parse_command_line_args(argv):
    """ Parses command line arguments """
    # Declare command line arguments and switches
    parser = argparse.ArgumentParser(description='Manipulates Salesforce metadata')
    subparsers = parser.add_subparsers(title='commands', help='commands', dest='command')
    subparsers.required = True

    clear_cache_parser = subparsers.add_parser('clear-cache', help='Clear local cache')
    clear_cache_parser.set_defaults(which='clear-cache')
    clear_cache_parser.add_argument('-o', '--org-name', type=str, required=True,
                                    help='Salesforce org name')

    deploy_parser = subparsers.add_parser('deploy', help='Deploy deployment package')
    deploy_parser.set_defaults(which='deploy')
    deploy_parser.add_argument('-o', '--org-name', type=str, required=True,
                               help='Salesforce org name (omit this argument when working with production)')
    deploy_parser.add_argument('-u', '--username', type=str, required=True,
                               help='Salesforce user name')
    deploy_parser.add_argument('-p', '--password', type=str, required=True,
                               help='password')
    deploy_parser.add_argument('-t', '--token', type=str,
                               help='security token')
    deploy_parser.add_argument('-d', '--deploy-zip', type=str, required=True,
                               help='path to deployment package')
    deploy_parser.add_argument('-s', '--source-dir', type=str, required=True,
                               help='path to directory containing metadata')
    deploy_parser.add_argument('-c', '--check-only', action='store_true',
                               help='use this switch to validate deployment package')
    deploy_parser.add_argument('-uc', '--use-cache', action='store_true',
                               help='use local cache to store symbol tables')
    deploy_parser.add_argument('-tl', '--test-level', type=str, default='NoTestRun',
                               choices=['NoTestRun', 'RunSpecifiedTests', 'RunLocalTests'],
                               help='test level: NoTestRun, RunSpecifiedTests, RunLocalTests')
    deploy_parser.add_argument('-v', '--version', type=str,
                               help='API version (i.e. 32.0, 33.0, etc)')

    return parser.parse_args(argv)


def main(argv):
    """ Main function """
    args = parse_command_line_args(argv)
    log = SfdcLogger()

    # Execute method corresponding to the command specified
    if args.command.lower() == 'deploy':
        cmd = DeployCommand(args, log)
        ret = cmd.run()
    elif args.command.lower() == 'clear-cache':
        cache = MetamateCache(args.org_name)
        cache.clear()
        ret = True
    else:
        log.err("Unknown command [%s]" % args.command)
        sys.exit(1)

    if not ret:
        log.err("Command failed")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
