import json
import sys
import os
import ast
import platform
import importlib
import importlib.util
from pathlib import Path
from types import ModuleType
from typing import List, Optional, Set, Any, Literal, Tuple, Dict

import distlib.database
from pkg_resources import EggInfoDistribution
from .utils import get_serverless_pack_root_folder, message_with_vars


serverless_pack_root_folder = get_serverless_pack_root_folder()
python_base_libs_folder_path = str(Path(os.__file__).parent.parent)


def get_distribution_name_of_package(package_filepath: str) -> Optional[str]:
    module_filepath_path = Path(package_filepath)
    parents_parts: Optional[List[str]] = getattr(module_filepath_path.parents, '_parts', None)
    if parents_parts is not None:
        for i, parent in enumerate(parents_parts):
            if parent == "site-packages":
                return parents_parts[i+1] if len(parents_parts)-1 > i+1 else None
    return None

def get_package_relative_filepath(absolute_filepath: str, package_name: str) -> Optional[str]:
    package_name_splits = package_name.split(".", 1)
    if len(package_name_splits) > 0:
        filepath_parts = Path(absolute_filepath).parts
        for i, part in enumerate(filepath_parts):
            if part == package_name_splits[0]:
                return os.path.join(*filepath_parts[i:])
    return None


class Resolver:
    WINDOWS_KEY = 'windows'
    LINUX_KEY = 'linux'
    TARGETS_OS = [WINDOWS_KEY, LINUX_KEY]
    TARGETS_OS_LITERAL = Literal['windows', 'linux', None]
    OS_TO_COMPILED_EXTENSIONS = {WINDOWS_KEY: 'pyd', LINUX_KEY: 'so'}

    def __init__(self, root_filepath: str, target_os: Optional[TARGETS_OS_LITERAL] = None, verbose: bool = False):
        self.root_filepath = root_filepath
        self.verbose = verbose

        self._system_os = platform.system().lower()
        if target_os is not None:
            self._target_os = target_os
        else:
            print(f"WARNING - Defaulting building to active OS {self.system_os}. Your package might not work on other OS")
            self._target_os = self.system_os

        if self.target_os in Resolver.TARGETS_OS:
            print(f"Building for {self.target_os} usage")
        else:
            raise Exception(f"OS {self.target_os} not supported")

        from importlib_metadata import packages_distributions
        self.packages_distributions = packages_distributions()
        self.distribution_path = distlib.database.DistributionPath(include_egg=True)
        self.included_dependencies_names: Set[str] = set()
        self.included_dependencies_distributions: Dict[str, Optional[EggInfoDistribution]] = dict()
        self.included_files_absolute_paths: Set[str] = {self.root_filepath}

        self.traces: List[dict] = []

    def save_traces_to_json(self):
        #     common_prefix_across_all_files = os.path.commonprefix([absolute_filepath for absolute_filepath in included_files_absolute_paths])
        with open("F:/Inoft/anvers_1944_project/serverlesspack/serverlesspack/visualizer/dist/traces.json", "w+") as file:
            file.write(json.dumps(self.traces))

    @property
    def system_os(self) -> str:
        return self._system_os

    @property
    def target_os(self) -> TARGETS_OS_LITERAL:
        return self._target_os

    def _verbose_print(self, message: str):
        if self.verbose is True:
            print(message)

    @staticmethod
    def from_code(code: str, target_os: Optional[TARGETS_OS_LITERAL] = None, dirpath: Optional[str] = None):
        filepath_temp_code_file = Resolver.write_code_file(code=code, filename="temp_root.py", dirpath=dirpath)
        return Resolver(root_filepath=filepath_temp_code_file, target_os=target_os)

    @staticmethod
    def write_code_file(code: str, filename: str, dirpath: Optional[str] = None) -> str:
        filepath_temp_code_file = os.path.join(serverless_pack_root_folder, f"dist/{'' if dirpath is None else f'{dirpath}/'}{filename}")
        file_parent_dirpath = os.path.dirname(filepath_temp_code_file)
        if not os.path.exists(file_parent_dirpath):
            os.makedirs(os.path.dirname(filepath_temp_code_file))

        with open(filepath_temp_code_file, 'w+') as file:
            file.write(code)
        return filepath_temp_code_file

    @staticmethod
    def _remove_junk_start_of_path(path: str) -> Tuple[str]:
        parts = Path(path).parts
        if len(parts) > 0:
            if parts[0] in [".", ".."]:
                parts = parts[1:]
        return parts

    @staticmethod
    def _path_to_module_path(base_path: str, module_name: str) -> Optional[str]:
        cleaned_base_path_parts = Resolver._remove_junk_start_of_path(path=base_path)
        if len(cleaned_base_path_parts) > 0:
            module_package = cleaned_base_path_parts[0]
            cleaned_base_path_parts = cleaned_base_path_parts[1:]

            source_module_name_parts = Path(module_name.replace(".", "/")).parts[1:]
            cleaned_module_name_parts = source_module_name_parts

            module_path = ""
            matching_paths = True
            for i, base_path_part in enumerate(cleaned_base_path_parts):
                module_path += f".{cleaned_base_path_parts[i]}"
                if len(source_module_name_parts) > i:
                    if matching_paths is True:
                        if base_path_part == source_module_name_parts[i]:
                            cleaned_module_name_parts = source_module_name_parts[i+1:]
                        else:
                            matching_paths = False

            return f"{'.'.join(cleaned_module_name_parts)}"
        return None

    def _import_module(self, module_name: str, filepath: str) -> Optional[ModuleType]:
        try:
            # We first try to import the module naively with only their
            # module name. This will work when trying to import libraries.
            return importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            self._verbose_print(message=str(e))
            # If this failed, we try to import the module as a file not inside a library. We do so by creating a relative
            # module path to the module from the current file, and we try to import the module from its relative path.

            # filepath_relative_to_current_module = os.path.relpath(filepath, os.path.abspath(os.path.dirname(__file__)))
            filepath_relative_to_current_module = os.path.relpath(filepath, sys.argv[0])
            # We need a filepath relative to the current module, in order to try to import the file module. All the imports done in a file must be relative
            # to the file trying to import the module. This relative filepath is not destined to be used in the archive paths when packaging the code.

            module_path = self._path_to_module_path(base_path=filepath_relative_to_current_module, module_name=module_name)
            # module_path, module_package = self._path_to_module_path(base_path=str(filepath_relative_to_current_module), module_name=module_name)
            try:
                """if module_path is not None and module_package is not None:
                    return importlib.import_module(name=module_path, package=module_package)"""

                # todo: this system is broken
                module_spec = importlib.util.spec_from_file_location(module_name, filepath)  # filepath_relative_to_current_module)
                return importlib.util.module_from_spec(module_spec) if module_spec is not None else None
            except ModuleNotFoundError as e:
                # If both the import as a library and as a file unfortunately
                # failed, we can stop trying to import the module.
                self._verbose_print(message_with_vars(
                    message="Importing of module failed as both a library import and file import",
                    vars_dict={'module_name': module_name, 'module_path': module_path, 'exception': e}
                ))
                return None

    def add_python_file(self, filepath: str):
        expected_init_filepath = os.path.join(os.path.dirname(filepath), "__init__.py")
        if expected_init_filepath not in self.included_files_absolute_paths:
            if os.path.exists(expected_init_filepath):
                self.included_files_absolute_paths.add(expected_init_filepath)

        if filepath not in self.included_files_absolute_paths:
            self.included_files_absolute_paths.add(filepath)

    def add_package_by_name(self, package_name: str, current_filepath: str):
        imported_package_module = self._import_module(module_name=package_name, filepath=current_filepath)
        if imported_package_module is not None:
            imported_package_module_filepath: Optional[str] = getattr(imported_package_module, '__file__', None)
            if imported_package_module_filepath is not None:
                # Depending on the location of the build file compared to the location of the module filepath, we might
                # need or might not need to remove the junk start of the path. So, we first check if the module filepath
                # exists, if that's the case, we will use that, otherwise we will try to remove the junk start of the path.
                if not os.path.exists(imported_package_module_filepath):
                    imported_package_module_filepath = os.path.join(*self._remove_junk_start_of_path(imported_package_module_filepath))
                imported_package_module_filepath = os.path.abspath(imported_package_module_filepath)

                # At this point, the file should exists, we do not add an additional
                # check, because if it does not exist, we want to cause an exception.
                if python_base_libs_folder_path not in imported_package_module_filepath:
                    path_imported_package_module_filepath = Path(imported_package_module_filepath)

                    if self.system_os == 'windows' and path_imported_package_module_filepath.suffix == '.pyd':
                        if self.target_os == 'linux':
                            path_imported_package_module_filepath = path_imported_package_module_filepath.with_suffix('.so')
                            imported_package_module_filepath = str(path_imported_package_module_filepath)
                            if not path_imported_package_module_filepath.is_file():
                                self._verbose_print(make_no_os_matching_file_warning_message(
                                    system_os=self.system_os, target_os=self.target_os,
                                    source_filepath=str(path_imported_package_module_filepath)
                                ))
                                return
                    elif self.system_os == 'linux' and path_imported_package_module_filepath == '.so':
                        if self.target_os == 'windows':
                            path_imported_package_module_filepath = path_imported_package_module_filepath.with_suffix('.pyd')
                            imported_package_module_filepath = str(path_imported_package_module_filepath)
                            if not path_imported_package_module_filepath.is_file():
                                self._verbose_print(make_no_os_matching_file_warning_message(
                                    system_os=self.system_os, target_os=self.target_os,
                                    source_filepath=str(path_imported_package_module_filepath)
                                ))
                                return

                    package_distribution_name = get_distribution_name_of_package(package_filepath=imported_package_module_filepath)
                    if package_distribution_name is not None:
                        # If the file has been found inside a library
                        real_package_name_container: Optional[List[str]] = self.packages_distributions.get(package_distribution_name, None)
                        if real_package_name_container is not None and len(real_package_name_container) > 0:
                            real_package_name = real_package_name_container[0]
                            if real_package_name not in self.included_dependencies_names:
                                package_distribution: Optional[EggInfoDistribution] = self.distribution_path.get_distribution(real_package_name)
                                if package_distribution is not None:
                                    package_requirements: Set[str] = getattr(package_distribution, 'run_requires', set())
                                    # todo: do something with the package_requirements ?

                                self.included_dependencies_names.add(real_package_name)
                                self.included_dependencies_distributions[real_package_name] = package_distribution
                                self.process_file(filepath=imported_package_module_filepath)
                    else:
                        # If the file is a standalone file not from a library
                        if imported_package_module_filepath not in self.included_files_absolute_paths:
                            self.traces.append({'source': current_filepath, 'target': imported_package_module_filepath, 'type': "import"})
                            self.add_python_file(filepath=imported_package_module_filepath)
                            self.process_file(filepath=imported_package_module_filepath)

    def process_node(self, node: Any, current_module: str, current_filepath: str):
        from .process_node_handlers import process_node_handlers_switch
        handler = process_node_handlers_switch.get(node.__class__, None)
        if handler is not None:
            handler(self, node, current_module, current_filepath)
        else:
            self._verbose_print(f"Node {node.__class__} not supported")

    def process_file(self, filepath: str):
        path_filepath = Path(filepath)
        if not path_filepath.exists():
            raise Exception(f"Filepath does not exist : {filepath}")

        if path_filepath.suffix == '.py':
            file = path_filepath.open('r')
            file_content = file.read()
            for node in ast.iter_child_nodes(ast.parse(file_content)):
                self.process_node(node=node, current_module=filepath, current_filepath=filepath)
        else:
            self.add_python_file(filepath=filepath)

    def import_folder(
            self, folderpath: str,
            included_files_extensions: Optional[List[str]] = None, included_folders_names: Optional[List[str]] = None,
            excluded_files_extensions: Optional[List[str]] = None, excluded_folders_names: Optional[List[str]] = None
    ):
        for root_dirpath, dirs, filenames in os.walk(folderpath, topdown=True):
            # The topdown arg allow to modify the dirs list in the walk, and so we can easily exclude folders.
            if included_folders_names is not None or excluded_folders_names is not None:
                dirs[:] = [
                    dirpath for dirpath in dirs
                    if excluded_folders_names is None or Path(dirpath).name not in excluded_folders_names
                    and included_folders_names is None or Path(dirpath).name in included_folders_names
                ]

            for filename in filenames:
                filename = Path(filename)
                can_be_included: bool = included_files_extensions is None or filename.suffix in included_files_extensions
                should_be_excluded: bool = excluded_files_extensions is not None and filename.suffix in excluded_files_extensions
                if can_be_included is True and should_be_excluded is False:
                    # todo: exclude .pyd files when building for windows and exclude .so files when building for windows
                    module_filepath = os.path.join(root_dirpath, str(filename))
                    self.add_python_file(filepath=module_filepath)

def make_no_os_matching_file_warning_message(system_os: str, target_os: Resolver.TARGETS_OS_LITERAL, source_filepath: str) -> str:
    source_extension = Resolver.OS_TO_COMPILED_EXTENSIONS[system_os]
    target_extension = Resolver.OS_TO_COMPILED_EXTENSIONS[target_os]
    return (
        f"WARNING - No matching .{source_extension} file found to replace a .{target_extension} file at {source_filepath}. "
        f"Make sure that you both have a compiled .{source_extension} and .{target_extension} file with the same names and paths. "
        f"Otherwise, try to compile your application on a {target_os} computer or virtual machine."
    )
