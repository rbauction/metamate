''' Deploy command '''
import time
from dependency_finder import find_test_class_dependencies
from test_extractor import \
    extract_class_objects, \
    extract_test_objects, \
    extract_class_names, \
    find_test_objects
from sfdclib import \
    SfdcSession, \
    SfdcMetadataApi
from abstract_command import AbstractCommand


class DeployCommand(AbstractCommand):
    ''' Deploy command '''
    def __init__(self, args, log):
        super().__init__(args, log)
        self._session = None
        self._mapi = None
        self._deployment_id = None
        self._deployment_state = None
        self._deployment_detail = None
        self._unit_tests_to_run = None
        self._unit_test_detail = None

    def _compose_sf_connection_settings(self):
        ''' Composes Salesforce connection settings '''
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
                self._log.inf("  State: %s - %s" % (self._deployment_state, state_detail))

    def _log_unit_test_errors(self):
        for err in self._unit_test_detail['errors']:
            self._log.err("=====\nClass: %s\nMethod: %s\nError: %s\n" % (
                err['class'],
                err['method'],
                err['message']))
        self._log.err("===== %s test(s) failed out of %s" % \
            (len(self._unit_test_detail['errors']), self._unit_test_detail['total_count']))

    def _log_deployment_errors(self):
        for err in self._deployment_detail['errors']:
            self._log.err("=====\nType: %s\nFile: %s\nStatus: %s\nMessage: %s\n" % (
                err['type'],
                err['file'],
                err['status'],
                err['message']))
        self._log.err("===== %s Component(s) failed out of %s" % \
            (len(self._deployment_detail['errors']), self._deployment_detail['total_count']))

    def _connect_to_salesforce(self):
        sf_kwargs = self._compose_sf_connection_settings()
        self._log.inf("Connecting to Salesforce")
        self._session = SfdcSession(**sf_kwargs)
        self._session.login()

    def _find_unit_tests_to_run(self):
        self._log.inf("Extracting names of objects containing classes from deployment ZIP")
        class_objects = extract_class_objects(self._args.deploy_zip, self._args.source_dir)

        self._log.inf("Checking which objects contain test classes")
        test_objects = extract_test_objects(class_objects, self._args.source_dir)
        nontest_objects = class_objects
        class_objects = None
        for test_object in test_objects:
            nontest_objects.remove(test_object)

        self._log.inf("Extracting names of test classes")
        self._unit_tests_to_run = extract_class_names(test_objects, self._args.source_dir)

        self._log.inf("Extracting names of nontest classes")
        changed_nontest_classes = extract_class_names(nontest_objects, self._args.source_dir)

        self._log.inf("Searching for all objects containing Apex classes")
        all_test_objects = find_test_objects(self._args.source_dir)

        class_dependencies = find_test_class_dependencies(
            self._log, self._session, all_test_objects)
        for class_ in changed_nontest_classes:
            if class_ in class_dependencies:
                for dependant in class_dependencies[class_]:
                    self._unit_tests_to_run.append(dependant)

        self._log.inf("Unit tests to be executed")
        for class_ in self._unit_tests_to_run:
            self._log.inf("  %s" % class_)

    def run(self):
        ''' Gets called by Metamate '''
        self._connect_to_salesforce()

        if self._args.test_level == 'RunSpecifiedTests':
            self._find_unit_tests_to_run()

        self._mapi = SfdcMetadataApi(self._session)

        self._log.inf("Deploying ZIP file. Test level: %s" % self._args.test_level)
        deploy_kwargs = {
            'zipfile': self._args.deploy_zip,
            'options': {
                'checkonly': self._args.check_only,
                'testlevel': self._args.test_level,
            }
        }
        if self._args.test_level == 'RunSpecifiedTests':
            deploy_kwargs['options']['tests'] = self._unit_tests_to_run

        self._deployment_id, self._deployment_state = self._mapi.deploy(**deploy_kwargs)
        self._log.inf("  Deployment id: %s" % self._deployment_id)

        self._wait_for_deployment_to_finish()

        if self._deployment_state == 'Failed':
            self._log_unit_test_errors()
            self._log_deployment_errors()
            self._log.err('Deployment failed')
            return False

        self._log.inf('Deployment succeeded')
        return True
