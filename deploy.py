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


def cmd_deploy(args, log):
    ''' Deploy command '''
    # Salesforce connection settings
    sf_kwargs = {
        'username': args.username,
        'password': args.password,
        'token': args.token,
        'is_sandbox': args.sandbox
    }

    if args.version:
        sf_kwargs['api_version'] = args.version

    log.inf("Extracting names of objects containing classes from deployment ZIP")
    class_objects = extract_class_objects(args.deploy_zip, args.source_dir)

    log.inf("Checking which objects contain test classes")
    test_objects = extract_test_objects(class_objects, args.source_dir)
    nontest_objects = class_objects
    class_objects = None
    for test_object in test_objects:
        nontest_objects.remove(test_object)

    log.inf("Extracting names of test classes")
    classes_to_test = extract_class_names(test_objects, args.source_dir)

    log.inf("Extracting names of nontest classes")
    changed_nontest_classes = extract_class_names(nontest_objects, args.source_dir)

    log.inf("Searching for all objects containing Apex classes")
    all_test_objects = find_test_objects(args.source_dir)

    log.inf("Connecting to Salesforce")
    session = SfdcSession(**sf_kwargs)
    session.login()

    class_dependencies = find_test_class_dependencies(log, session, all_test_objects)
    for class_ in changed_nontest_classes:
        if class_ in class_dependencies:
            for dependant in class_dependencies[class_]:
                classes_to_test.append(dependant)

    log.inf("Classes to be tested")
    for class_ in classes_to_test:
        log.inf("  %s" % class_)

    mapi = SfdcMetadataApi(session)

    log.inf("Deploying ZIP file")
    depl_id, state = mapi.deploy(
        args.deploy_zip,
        checkonly=True,
        testlevel="RunSpecifiedTests",
        tests=classes_to_test)
    log.inf("  Deployment id: %s" % depl_id)

    while state in ['Queued', 'Pending', 'InProgress']:
        time.sleep(5)
        state, state_detail, deployment_errors, unit_test_errors = mapi.check_deploy_status(depl_id)
        if state in ['Queued', 'Pending']:
            log.inf("  State: %s" % state)
        else:
            log.inf("  State: %s Info: %s" % (state, state_detail))

    if state == 'Failed':
        # Print out unit test errors
        for err in unit_test_errors:
            log.err("=====\nClass: %s\nMethod: %s\nError: %s\n" % (
                err['class'],
                err['method'],
                err['message']))
        log.err("===== %s test(s) failed" % len(unit_test_errors))

        # Print out deployment errors
        for err in deployment_errors:
            log.err("=====\nType: %s\nFile: %s\nStatus: %s\nMessage: %s\n" % (
                err['type'],
                err['file'],
                err['status'],
                err['message']))
        log.err("===== %s Component(s) failed" % len(unit_test_errors))

        log.err('Deployment failed')
        return False

    log.inf('Deployment succeeded')
    return True
