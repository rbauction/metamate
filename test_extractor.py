import re
from os import path, listdir
from xml.etree import ElementTree as ET
from zipfile import ZipFile

XML_NAMESPACES = {'mt': 'http://soap.sforce.com/2006/04/metadata'}

def grep_file(file, regobj):
    try:
        with open(file, 'r') as f:
            if regobj.search(f.read()):
                return True
    except:
        print("Could not process file %s" % file)
    return False

def extract_package_xml(zipfile):
    with ZipFile(zipfile) as zf:
        with zf.open('package.xml') as pxml:
            return ET.fromstring(pxml.read().decode("utf-8"))

def extract_members(root, object_type):
    items = []
    for node in root.findall("mt:types/[mt:name='%s']" % object_type, XML_NAMESPACES):
        for member in node.findall("mt:members", XML_NAMESPACES):
            items.append(member.text)
    return items

def extract_class_objects(zipfile, sourcedir):
    root = extract_package_xml(zipfile)
    return extract_members(root, 'ApexClass')

def extract_test_objects(classes, sourcedir):
    objects = []
    regobj = re.compile(r'@isTest')
    for c in classes:
        filepath = path.join(sourcedir, "classes", "%s.cls" % c)
        if not path.isfile(filepath):
            continue
        if grep_file(filepath, regobj):
            objects.append(c)
    
    return objects

def find_test_objects(sourcedir):
    objects = []
    regobj_test = re.compile(r'@isTest')
    regobj_active = re.compile(r'Active')
    classes_path = path.join(sourcedir, "classes")
    for entry in listdir(classes_path):
        if '-meta.xml' in entry:
            cfname = entry.replace('-meta.xml', '')
            cfpath = path.join(classes_path, cfname)
            if path.isfile(cfpath):
                if grep_file(cfpath, regobj_test) and grep_file(path.join(classes_path, entry), regobj_active):
                    objects.append(cfname.replace(".cls", ""))
    return objects

def extract_class_names(objects, sourcedir):
    class_names = []
    regobj = re.compile(r'(private|public)\s+.*class\s+([a-zA-Z0-9_]+)\s*')
    for o in objects:
        file = path.join(sourcedir, "classes", "%s.cls" % o)
        try:
            with open(file, 'r') as f:
                for m in regobj.finditer(f.read()):
                    class_names.append(m.group(2))
        except Exception as err:
            print("Could not process file {0}. Error: {1}".format(file, err))
    return class_names
