""" Test class dependency finder """
import os
import sys
import time

from sfdclib import SfdcToolingApi


def retrieve_apex_classes(session, classes=None):
    """ Retrieves list of Apex classes """
    tooling = SfdcToolingApi(session)
    query = "SELECT Id,Name FROM ApexClass"
    if classes is not None:
        query += " WHERE Name IN ('{0}')".format("','".join(classes))
    res = tooling.anon_query(query)
    apex_classes = dict()
    for apex_class in res['records']:
        apex_classes[apex_class['Name']] = apex_class['Id']
    return apex_classes


def create_metadata_container(tooling):
    """ (Re)creates metadata container """
    container = {'Name': 'MetamateMetadataContainer'}

    res = tooling.anon_query(
        "SELECT Id,Name FROM MetadataContainer WHERE Name='%s'" % container['Name'])
    if res['size'] == 1:
        tooling.delete('/sobjects/MetadataContainer/%s' % res['records'][0]['Id'])

    res = tooling.post('/sobjects/MetadataContainer/', {'Name': container['Name']})

    if res['success']:
        container['Id'] = res['id']
    else:
        raise Exception('Could not create metadata container')

    return container


def find_test_class_dependencies(log, session, test_classes, source_dir, use_cache, cache):
    """ Finds test class dependencies """
    if use_cache:
        # Retrieve info about classes not in cache
        classes_to_recompile = list(set(test_classes) - set(cache.keys()))
        apex_classes = retrieve_apex_classes(session, classes_to_recompile)
        classes = dict()
        for class_name, class_id in apex_classes.items():
            classes[class_id] = class_name
        dependencies = retrieve_class_dependencies(log, session, classes, source_dir)
        # Add cached data
        for class_name, data in cache.items():
            dependencies[class_name] = data
    else:
        log.inf("Retrieving list of Apex classes from Salesforce")
        apex_classes = retrieve_apex_classes(session)

        log.inf("Looking for tests that exist both locally and in Salesforce")
        matching_tests = dict()  # Format: {'Class_Id': 'Class_Name'}
        for apex_class in test_classes:
            if apex_class in apex_classes:
                matching_tests[apex_classes[apex_class]] = apex_class

        if len(matching_tests) == 0:
            log.inf("No matching classes found in both Salesforce and local source folder")
            return dict()

        dependencies = retrieve_class_dependencies(log, session, matching_tests, source_dir)
    return dependencies, reverse_class_dependencies(dependencies)


def retrieve_class_dependencies(log, session, classes, source_dir):
    """ Retrieves class dependencies from Salesforce.com """
    tooling = SfdcToolingApi(session)
    log.inf("Creating metadata container")
    container = create_metadata_container(tooling)

    members = dict()
    log.inf("===> Adding %s Apex classes to metadata container" % len(classes))
    count = len(classes)
    i = 1
    for class_id, class_name in classes.items():
        log.inf("  ({0}/{1}) Id: {2} Name: {3}".format(i, count, class_id, class_name))
        class_body = read_class_body(source_dir, class_name)
        res = tooling.post('/sobjects/ApexClassMember/', {
            'MetadataContainerId': container['Id'],
            'ContentEntityId': class_id,
            'Body': class_body
        })
        members[res['id']] = class_name
        i += 1

    log.inf("===> Compiling metadata")
    res = tooling.post('/sobjects/ContainerAsyncRequest/', {
        'MetadataContainerId': container['Id'],
        'IsCheckOnly': 'true'})

    if not res['success']:
        raise Exception("Tooling API call failed")

    req_id = res['id']
    while True:
        res = tooling.anon_query(
            "SELECT State,ErrorMsg FROM ContainerAsyncRequest WHERE Id='%s'" % req_id)
        log.inf(res['records'][0]['State'])
        if res['records'][0]['State'] not in ['Queued', 'Pending', 'InProgress']:
            break
        time.sleep(5)

    log.inf("===> Retrieving symbol tables")

    dependencies = dict()
    for class_id, class_name in members.items():
        log.inf("  Id: %s Name: %s" % (class_id, class_name))
        res = tooling.get('/sobjects/ApexClassMember/%s/' % class_id)
        # Skip classes without dependencies and managed code dependencies
        if res['SymbolTable'] is None:
            continue
        refs = list()
        for ref in res['SymbolTable']['externalReferences']:
            # Skip managed code dependencies
            if ref['namespace'] is None:
                refs.append(ref['name'])
        dependencies[class_name] = {
            'Id': class_id,
            'References': refs
        }

    log.inf("===> Deleting metadata container")
    tooling.delete('/sobjects/MetadataContainer/%s' % container['Id'])
    return dependencies


def read_class_body(source_dir, class_name):
    with open(os.path.join(source_dir, *["classes", "{0}.cls".format(class_name)]), 'r') as file:
        return file.read(-1)


def reverse_class_dependencies(dependencies):
    """ Reverses class dependency dictionary
    Consumes dictionary in format
    {
        'test_class_name_1': {
            'Id': '01pU00000026druIAA',
            'References': ['class_name_1', 'class_name_2']
        }
    }
    produces dictionary in format
    {
        'class_name_1': ['test_class_name_1'],
        'class_name_2': ['test_class_name_1']
    } """
    reverse_deps = dict()
    for class_name, data in dependencies.items():
        for dep_class_name in data['References']:
            if dep_class_name in reverse_deps:
                if class_name in reverse_deps[dep_class_name]:
                    continue
                cur_class_deps = reverse_deps[dep_class_name]
            else:
                cur_class_deps = list()
            cur_class_deps.append(class_name)
            cur_class_deps.sort()
            reverse_deps[dep_class_name] = cur_class_deps
    return reverse_deps
