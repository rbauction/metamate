import json
import time

from sfdclib import \
    SfdcLogger, \
    SfdcSession, \
    SfdcToolingApi


def find_test_class_dependencies(log, session, test_classes):
    tooling = SfdcToolingApi(session)
    log.inf("Retrieving list of Apex classes from Salesforce")
    r = tooling.anon_query("SELECT Id,Name FROM ApexClass")
    j = json.loads(r)
    apex_classes = {}
    for c in j['records']:
        apex_classes[c['Name']] = c['Id']

    log.inf("Looking for tests that exist both locally and in Salesforce")
    matching_tests = {}
    for c in test_classes:
        if c in apex_classes:
            matching_tests[apex_classes[c]] = c

    container = {'Name': 'AndreyMetadataContainerTest'}
    log.inf("Checking if metadata container still exists in Salesforce")
    r = tooling.anon_query("SELECT Id,Name FROM MetadataContainer WHERE Name='%s'" % container['Name'])
    j = json.loads(r)
    if j['size'] == 1:
        log.inf("===> Deleting stale metadata container")
        r = tooling.delete('/sobjects/MetadataContainer/%s' % j['records'][0]['Id'])

    log.inf("===> Creating metadata container")
    r = tooling.post('/sobjects/MetadataContainer/', {'Name': container['Name']})
    j = json.loads(r)
    if j['success']:
        container['Id'] = j['id']
    else:
        raise Exception('Could not create metadata container')

    members = {}
    log.inf("===> Adding %s ApexClasses to metadata container" % len(matching_tests))
    for id, name in matching_tests.items():
        log.inf("  Id: %s Name: %s" % (id, name))
        log.dbg("Retrieving object from Salesforce")
        r = tooling.get('/sobjects/ApexClass/%s/' % id)
        apexclass = json.loads(r)

        log.dbg("Adding ApexClassMember to the metadata container")
        r = tooling.post('/sobjects/ApexClassMember/', {
            'MetadataContainerId': container['Id'],
            'ContentEntityId': id,
            'Body': apexclass['Body']})
        j = json.loads(r)
        members[j['id']] = name

    log.inf("===> Compiling metadata")
    r = tooling.post('/sobjects/ContainerAsyncRequest/', {
        'MetadataContainerId': container['Id'],
        'IsCheckOnly': 'true'})
    j = json.loads(r)
    if j['success']:
        req_id = j['id']
    while True:
        r = tooling.anon_query("SELECT State,ErrorMsg FROM ContainerAsyncRequest WHERE Id='%s'" % req_id)
        j = json.loads(r)
        log.inf(j['records'][0]['State'])
        if j['records'][0]['State'] not in ['Queued', 'Pending', 'InProgress']:
            break
        time.sleep(5)

    log.inf("===> Retrieving symbol tables")
    # Format {'class_name': ['test_class_name1', 'test_class_name2'], ...}
    dependencies = {}
    for id, name in members.items():
        log.inf("  Id: %s Name: %s" % (id, name))
        r = tooling.get('/sobjects/ApexClassMember/%s/' % id)
        j = json.loads(r)
        if j['SymbolTable'] == None:
            continue
        for c in j['SymbolTable']['externalReferences']:
            if c['name'] in dependencies:
                if name in dependencies[c['name']]:
                    continue
                classes = dependencies[c['name']]
            else:
                classes = []
            classes.append(name)
            dependencies[c['name']] = classes

    log.inf("===> Deleting metadata container")
    r = tooling.delete('/sobjects/MetadataContainer/%s' % container['Id'])
    return dependencies
