import unittest
from metamate import dependency_finder


class DependencyFinderTest(unittest.TestCase):

    def test_reverse_class_dependencies(self):
        dependencies = {
            'test_class_name_1': {
                'Id': '01pU00000026druIAA',
                'References': ['class_name_1', 'class_name_2']
            },
            'test_class_name_2': {
                'Id': '01pU00000026druIAA',
                'References': ['class_name_1', 'class_name_3']
            }
        }
        self.assertEqual(
            {
                'class_name_1': ['test_class_name_1', 'test_class_name_2'],
                'class_name_2': ['test_class_name_1'],
                'class_name_3': ['test_class_name_2']
            },
            dependency_finder.reverse_class_dependencies(dependencies)
        )

if __name__ == '__main__':
    unittest.main()
