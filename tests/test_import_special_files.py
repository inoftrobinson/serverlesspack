import unittest
from serverlesspack.imports_resolver import Resolver
from serverlesspack.packager import package_lambda_layer, package_files


class TestImportSpecialFiles(unittest.TestCase):
    def test_import_pyd_and_so_files(self):
        code = "from inoft_vocal_framework.audio_engine import audio_engine"

        resolver_windows = Resolver.from_code(code=code, target_os=Resolver.WINDOWS_KEY)
        resolver_windows.gen(resolver_windows.root_filepath)
        self.assertIn('inoft_vocal_framework.audio_engine.audio_engine.pyd', resolver_windows.files)

        resolver_linux = Resolver.from_code(code=code, target_os=Resolver.LINUX_KEY)
        resolver_linux.gen(resolver_windows.root_filepath)
        self.assertIn('inoft_vocal_framework.audio_engine.audio_engine.so', resolver_linux.files)


if __name__ == '__main__':
    unittest.main()
