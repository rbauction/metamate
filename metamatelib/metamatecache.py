import glob
import os
import yaml


class MetamateCache:
    """ Class to manage local cache """
    ROOT_DIR_NAME = ".metamate"

    def __init__(self, org_name):
        self._org_name = org_name
        self._root_dir = os.path.join(os.path.expanduser("~"), self.ROOT_DIR_NAME)
        self._org_root_dir = os.path.join(self._root_dir, self._org_name)
        self._data = dict()

    @property
    def data(self):
        return self._data

    def load(self):
        """ Loads data for all classes stored in local cache """
        for path in glob.glob('{0}/*.yaml'.format(self._org_root_dir)):
            file_name = os.path.split(path)[1]
            class_name = file_name[:-5]
            with open(path, 'r') as file:
                self._data[class_name] = yaml.load(file)

    def clear(self):
        """ Clears local cache """
        if not os.path.exists(self._org_root_dir):
            return
        for path in glob.glob('{0}/*.yaml'.format(self._org_root_dir)):
            os.remove(path)

    def add_class_data(self, class_name, data):
        """ Stores data for a class in the local cache """
        # Check whether org directory exists in the local cache
        if os.path.exists(self._org_root_dir):
            if not os.path.isdir(self._org_root_dir):
                raise Exception("Please delete {0} file, Metamate needs to create a directory with this name")
        else:
            os.makedirs(self._org_root_dir)
        # Save as YAML into local cache
        with open(self._class_data_file_name(class_name), 'w+') as file:
            file.write(yaml.dump(data, default_flow_style=False))
        self._data[class_name] = data

    def delete_class_data(self, class_name):
        """ Remove data cached for a class """
        if class_name not in self._data:
            return
        del self._data[class_name]
        class_file = self._class_data_file_name(class_name)
        if os.path.isfile(class_file):
            os.remove(class_file)

    def _class_data_file_name(self, class_name):
        return os.path.join(self._org_root_dir, "{0}.yaml".format(class_name))
