import re
from os import path, listdir
from xml.etree import ElementTree as ET
from zipfile import ZipFile

XML_NAMESPACES = {'mt': 'http://soap.sforce.com/2006/04/metadata'}


def grep_file(filename, reg_obj):
    try:
        with open(filename, mode='r', encoding='utf-8') as file:
            if reg_obj.search(file.read()):
                return True
    except Exception as ex:
        print("Could not process file %s: %s" % (filename, ex))
    return False


def extract_package_xml(zipfile):
    with ZipFile(zipfile) as zf:
        with zf.open('package.xml') as package_xml:
            return ET.fromstring(package_xml.read().decode("utf-8"))


def extract_members(root, object_type):
    items = list()
    for node in root.findall("mt:types/[mt:name='%s']" % object_type, XML_NAMESPACES):
        for member in node.findall("mt:members", XML_NAMESPACES):
            items.append(member.text)
    return items


def extract_class_objects(zipfile):
    root = extract_package_xml(zipfile)
    return extract_members(root, 'ApexClass')


def extract_test_objects(classes, source_dir):
    objects = list()
    reg_obj = re.compile(r'@isTest', re.UNICODE)
    for c in classes:
        file_path = path.join(source_dir, "classes", "%s.cls" % c)
        if not path.isfile(file_path):
            continue
        if grep_file(file_path, reg_obj):
            objects.append(c)
    
    return objects


def find_test_objects(source_dir):
    objects = list()
    reg_obj_test = re.compile(r'@isTest', re.UNICODE)
    reg_obj_active = re.compile(r'Active', re.UNICODE)
    classes_path = path.join(source_dir, "classes")
    for entry in listdir(classes_path):
        if '-meta.xml' in entry:
            cfname = entry.replace('-meta.xml', '')
            cfpath = path.join(classes_path, cfname)
            if path.isfile(cfpath):
                if grep_file(cfpath, reg_obj_test) and grep_file(path.join(classes_path, entry), reg_obj_active):
                    objects.append(cfname.replace(".cls", ""))
    return objects


def extract_class_names(objects, source_dir):
    class_names = list()
    reg_obj = re.compile(r'(private|public)\s+.*class\s+([a-zA-Z0-9_]+)\s*', re.UNICODE)
    for obj in objects:
        filename = path.join(source_dir, "classes", "%s.cls" % obj)
        try:
            with open(filename, mode='r', encoding='utf-8') as file:
                for match in reg_obj.finditer(file.read()):
                    class_names.append(match.group(2))
        except Exception as err:
            print("Could not process file {0}. Error: {1}".format(filename, err))
    return class_names
