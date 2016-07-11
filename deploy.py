import time
from dependency_finder import find_test_class_dependencies
from test_extractor import \
    extract_class_objects, \
    extract_test_objects, \
    extract_class_names, \
    find_test_objects
from sfdclib import \
    SfdcLogger, \
    SfdcSession, \
    SfdcMetadataApi


def cmd_deploy(args, log):
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
    for x in test_objects:
        nontest_objects.remove(x)

    log.inf("Extracting names of test classes")
    classes_to_test = extract_class_names(test_objects, args.source_dir)

    log.inf("Extracting names of nontest classes")
    changed_nontest_classes = extract_class_names(nontest_objects, args.source_dir)

    log.inf("Searching for all objects containing Apex classes")
    all_test_objects = find_test_objects(args.source_dir)

    log.inf("Connecting to Salesforce")
    ss = SfdcSession(**sf_kwargs)
    ss.login()

    class_dependencies = find_test_class_dependencies(log, ss, all_test_objects)
    for c in changed_nontest_classes:
        if c in class_dependencies:
            for d in class_dependencies[c]:
                classes_to_test.append(d)

    log.inf("Classes to be tested")
    for c in classes_to_test:
        log.inf("  %s" % c)

    md = SfdcMetadataApi(ss)

    log.inf("Deploying ZIP file")
    id, state = md.deploy(
        args.deploy_zip,
        checkonly=True,
        testlevel="RunSpecifiedTests",
        tests=classes_to_test)
    log.inf("  Deployment id: %s" % id)

    while state in ['Queued', 'Pending', 'InProgress']:
        time.sleep(5)
        state, state_detail, errors = md.check_deploy_status(id)
        if state in ['Queued', 'Pending']:
            log.inf("  State: %s" % state)
        else:
            log.inf("  State: %s Info: %s" % (state, state_detail))

    if state == 'Failed':
        log.err('Deployment failed\n%s' % errors)
        return False

    log.inf('Deployment succeeded')
    return True
