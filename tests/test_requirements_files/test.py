import os
import sys
import unittest

from serverlesspack.cli import package_api


class TestRequirementsFiles(unittest.TestCase):
    def test(self):
        sys.argv.insert(0, os.path.realpath('../test.py'))
        package_api(target_os='linux', config_filepath='./serverlesspack.config.yaml', verbose=True)


if __name__ == '__main__':
    unittest.main()
