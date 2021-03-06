""" Deploy command """
import time
from metamatelib.abstract_command import AbstractCommand
from metamatelib.dependency_finder import find_test_class_dependencies
from metamatelib.metamatecache import MetamateCache
from metamatelib.test_extractor import \
    extract_class_objects, \
    extract_test_objects, \
    extract_class_names, \
    find_test_objects
from sfdclib import \
    SfdcSession, \
    SfdcMetadataApi


class DeployCommand(AbstractCommand):
    """ Deploy command """
    def __init__(self, args, log):
        super().__init__(args, log)
        self._check_only = self._args.check_only
        self._test_level = self._args.test_level
        self._cache = None
        self._session = None
        self._mapi = None
        self._deployment_id = None
        self._deployment_state = None
        self._deployment_detail = None
        self._unit_tests_to_run = None
        self._unit_test_detail = None

    def _compose_sf_connection_settings(self):
        """ Composes Salesforce connection settings """
        sf_kwargs = {
            'username': self._args.username,
            'password': self._args.password,
            'token': self._args.token,
            'is_sandbox': self._args.sandbox
        }

        if self._args.version:
            sf_kwargs['api_version'] = self._args.version

        return sf_kwargs

    def _wait_for_deployment_to_finish(self):
        while self._deployment_state in ['Queued', 'Pending', 'InProgress']:
            time.sleep(5)
            self._deployment_state, state_detail, self._deployment_detail, self._unit_test_detail =\
                self._mapi.check_deploy_status(self._deployment_id)
            if state_detail is None:
                self._log.inf("  State: %s" % self._deployment_state)
            else:
                if int(self._deployment_detail['deployed_count']) + \
                   int(self._deployment_detail['failed_count']) < \
                   int(self._deployment_detail['total_count']):
                    progress = "(%s/%s) " % (
                        self._deployment_detail['deployed_count'] +
                        self._deployment_detail['failed_count'],
                        self._deployment_detail['total_count']
                        )
                else:
                    progress = "(%s/%s) " % (
                        self._unit_test_detail['completed_count'],
                        self._unit_test_detail['total_count']
                        )

                self._log.inf("  State: %s - %s%s" % (
                    self._deployment_state,
                    progress,
                    state_detail))

    def _log_unit_test_errors(self):
        for err in self._unit_test_detail['errors']:
            self._log.err("=====\nClass: %s\nMethod: %s\nError: %s\nStack trace: %s\n" % (
                err['class'],
                err['method'],
                err['message'],
                err['stack_trace']
                ))
        self._log.err("===== %s test(s) failed out of %s" %
                      (len(self._unit_test_detail['errors']), self._unit_test_detail['total_count']))

    def _log_deployment_errors(self):
        for err in self._deployment_detail['errors']:
            self._log.err("=====\nType: %s\nFile: %s\nStatus: %s\nMessage: %s\n" % (
                err['type'],
                err['file'],
                err['status'],
                err['message']
                ))
        self._log.err("===== %s Component(s) failed out of %s" %
                      (len(self._deployment_detail['errors']), self._deployment_detail['total_count']))

    def _connect_to_salesforce(self):
        sf_kwargs = self._compose_sf_connection_settings()
        self._log.inf("Connecting to Salesforce")
        self._session = SfdcSession(**sf_kwargs)
        self._session.login()

    def _find_unit_tests_to_run(self):
        self._log.inf("Extracting names of objects containing classes from deployment ZIP")
        class_objects = extract_class_objects(self._args.deploy_zip)

        self._log.inf("Checking which objects contain test classes")
        test_objects = extract_test_objects(class_objects, self._args.source_dir)
        nontest_objects = class_objects
        for test_object in test_objects:
            nontest_objects.remove(test_object)
            if self._args.use_cache:
                self._cache.delete_class_data(test_object)

        self._log.inf("Extracting names of test classes")
        self._unit_tests_to_run = extract_class_names(test_objects, self._args.source_dir)

        self._log.inf("Extracting names of non-test classes")
        changed_nontest_classes = extract_class_names(nontest_objects, self._args.source_dir)

        self._log.inf("Searching for all objects containing Apex classes")
        all_test_objects = find_test_objects(self._args.source_dir)

        test_class_dependencies, class_dependencies = find_test_class_dependencies(
            self._log, self._session, all_test_objects, self._args.source_dir, self._args.use_cache, self._cache.data)

        # Save class_dependencies to cache
        for class_name, data in test_class_dependencies.items():
            self._cache.add_class_data(class_name, data)

        # Find test classes that need to be executed based on non-test classes dependencies
        for class_name in changed_nontest_classes:
            if class_name in class_dependencies:
                for dependant in class_dependencies[class_name]:
                    self._unit_tests_to_run.append(dependant)

        self._log.inf("Unit tests to be executed")
        for class_name in self._unit_tests_to_run:
            self._log.inf("  %s" % class_name)

    def run(self):
        """ Gets called by Metamate """
        self._cache = MetamateCache(self._args.username)
        if self._args.use_cache:
            self._cache.load()

        self._connect_to_salesforce()

        if self._test_level == 'RunSpecifiedTests':
            self._find_unit_tests_to_run()
            if len(self._unit_tests_to_run) == 0:
                self._log.inf("Could not find any tests to run, downgrading test level to NoTestRun")
                self._test_level = 'NoTestRun'

        self._mapi = SfdcMetadataApi(self._session)

        self._log.inf("Deploying ZIP file. Test level: %s" % self._test_level)
        deploy_kwargs = {
            'zipfile': self._args.deploy_zip,
            'options': {
                'checkonly': self._check_only,
                'testlevel': self._test_level,
            }
        }
        if self._test_level == 'RunSpecifiedTests':
            deploy_kwargs['options']['tests'] = self._unit_tests_to_run

        self._deployment_id, self._deployment_state = self._mapi.deploy(**deploy_kwargs)
        self._log.inf("  Deployment id: %s" % self._deployment_id)

        self._wait_for_deployment_to_finish()

        if self._deployment_state == 'Failed':
            self._log_unit_test_errors()
            self._log_deployment_errors()
            self._log.err('Deployment failed')
            return False
        elif self._deployment_state == 'Canceled' or self._deployment_state == 'Canceling':
            self._log.err('Deployment was canceled')
            return False
        elif self._deployment_state == 'Succeeded':
            self._log.inf('Deployment succeeded')
            return True
        else:
            self._log.err('Unknown deployment state: {0}'.format(self._deployment_state))
            return False
