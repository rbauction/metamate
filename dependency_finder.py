''' Test class dependency finder '''
import time

from sfdclib import SfdcToolingApi


def retrieve_apex_classes(tooling):
    ''' Retrieves list of Apex classes '''
    res = tooling.anon_query("SELECT Id,Name FROM ApexClass")
    apex_classes = {}
    for apex_class in res['records']:
        apex_classes[apex_class['Name']] = apex_class['Id']
    return apex_classes


def create_metadata_container(tooling):
    ''' (Re)creates metadata container '''
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


def find_test_class_dependencies(log, session, test_classes):
    ''' Finds test class dependencies '''
    tooling = SfdcToolingApi(session)
    log.inf("Retrieving list of Apex classes from Salesforce")
    apex_classes = retrieve_apex_classes(tooling)

    log.inf("Looking for tests that exist both locally and in Salesforce")
    matching_tests = {}
    for apex_class in test_classes:
        if apex_class in apex_classes:
            matching_tests[apex_classes[apex_class]] = apex_class

    if len(matching_tests) == 0:
        log.inf("No matching classes found in both Salesforce and local source folder")
        return {}

    log.inf("Creating metadata container")
    container = create_metadata_container(tooling)

    members = {}
    log.inf("===> Adding %s Apex classes to metadata container" % len(matching_tests))
    for class_id, name in matching_tests.items():
        log.inf("  Id: %s Name: %s" % (class_id, name))
        log.dbg("Retrieving object from Salesforce")
        apex_class = tooling.get('/sobjects/ApexClass/%s/' % class_id)
        log.dbg("Adding ApexClassMember to the metadata container")
        res = tooling.post('/sobjects/ApexClassMember/', {
            'MetadataContainerId': container['Id'],
            'ContentEntityId': class_id,
            'Body': apex_class['Body']})
        members[res['id']] = name

    log.inf("===> Compiling metadata")
    res = tooling.post('/sobjects/ContainerAsyncRequest/', {
        'MetadataContainerId': container['Id'],
        'IsCheckOnly': 'true'})

    if res['success']:
        req_id = res['id']
    while True:
        res = tooling.anon_query(
            "SELECT State,ErrorMsg FROM ContainerAsyncRequest WHERE Id='%s'" % req_id)
        log.inf(res['records'][0]['State'])
        if res['records'][0]['State'] not in ['Queued', 'Pending', 'InProgress']:
            break
        time.sleep(5)

    log.inf("===> Retrieving symbol tables")
    # Format {'class_name': ['test_class_name1', 'test_class_name2'], ...}
    dependencies = {}
    for class_id, name in members.items():
        log.inf("  Id: %s Name: %s" % (class_id, name))
        res = tooling.get('/sobjects/ApexClassMember/%s/' % class_id)
        if res['SymbolTable'] is None:
            continue
        for apex_class in res['SymbolTable']['externalReferences']:
            if apex_class['name'] in dependencies:
                if name in dependencies[apex_class['name']]:
                    continue
                classes = dependencies[apex_class['name']]
            else:
                classes = []
            classes.append(name)
            dependencies[apex_class['name']] = classes

    log.inf("===> Deleting metadata container")
    tooling.delete('/sobjects/MetadataContainer/%s' % container['Id'])
    return dependencies
