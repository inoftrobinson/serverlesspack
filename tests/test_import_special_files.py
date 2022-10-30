import unittest
from serverlesspack.imports_resolver import Resolver


class TestImportSpecialFiles(unittest.TestCase):
    def test_import_pyd_and_so_files(self):
        code = "from inoft_vocal_framework.audio_engine import audio_engine"

        resolver_windows = Resolver.from_code(code=code, target_os=Resolver.WINDOWS_KEY)
        resolver_windows.process_file(resolver_windows.root_filepath)
        self.assertIn('inoft_vocal_framework.audio_engine.audio_engine.pyd', resolver_windows.files)

        resolver_linux = Resolver.from_code(code=code, target_os=Resolver.LINUX_KEY)
        resolver_linux.process_file(resolver_windows.root_filepath)
        self.assertIn('inoft_vocal_framework.audio_engine.audio_engine.so', resolver_linux.files)

    def test_import_in_nested_function(self):
        code = """def parent():
    def inner():
        from inoft_vocal_framework.audio_engine import audio_engine
        if True:
            from local_dummy_file import LocalDummyObject
        """

        resolver = Resolver.from_code(code=code, dirpath='inside_folder', target_os=Resolver.WINDOWS_KEY)
        resolver.process_file(resolver.root_filepath)
        self.assertIn('inoft_vocal_framework.audio_engine.audio_engine.pyd', resolver.files)
        self.assertIn("local_dummy_file.py", resolver.files)

    def test_import_in_nested_function_inside_folder(self):
        code_dummy_object_file = """class LocalDummyObject:
    pass
        """

        code_import_file = """def parent():
    def inner():
        if 1 > 0:
            from local_dummy_file import LocalDummyObject
        """

        Resolver.write_code_file(code=code_dummy_object_file, filename='local_dummy_file', dirpath="inside_folder")
        resolver = Resolver.from_code(code=code_import_file, dirpath='inside_folder', target_os=Resolver.WINDOWS_KEY)
        resolver.process_file(resolver.root_filepath)
        self.assertIn("local_dummy_file.py", resolver.files)


if __name__ == '__main__':
    unittest.main()
