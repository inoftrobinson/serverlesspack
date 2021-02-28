import os
import ast
import importlib
import platform
from types import ModuleType

import distlib.database
from pathlib import Path
from typing import List, TypedDict, Optional, Dict, Set, Any, Literal, Tuple

from StructNoSQL.practical_logger import message_with_vars
from pkg_resources import EggInfoDistribution
from serverlesspack.utils import get_serverless_pack_root_folder


serverless_pack_root_folder = get_serverless_pack_root_folder()
python_base_libs_folder_path = str(Path(os.__file__).parent)

class PackageItem(TypedDict):
    absolute_filepath: str
    relative_filepath: str

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

    def __init__(self, root_filepath: str, target_os: Optional[TARGETS_OS_LITERAL] = None):
        self.root_filepath = root_filepath
        self.system_os = platform.system().lower()
        if target_os is not None:
            self.target_os = target_os
        else:
            print(f"WARNING - Defaulting building to active OS {self.system_os}. Your package might not work on other OS")
            self.target_os = self.system_os

        if self.target_os in Resolver.TARGETS_OS:
            print(f"Building for {self.target_os} usage")
        else:
            raise Exception(f"OS {self.target_os} not supported")

        self.distribution_path = distlib.database.DistributionPath(include_egg=True)
        self.packages: Dict[str, PackageItem] = dict()
        self.files: Dict[str, PackageItem] = {
            '__root__': PackageItem(
                absolute_filepath=self.root_filepath,
                relative_filepath=Path(self.root_filepath).name,
            )
        }

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

    def _path_to_module_path(self, base_path: str, module_name: str) -> Tuple[Optional[str], Optional[str]]:
        cleaned_base_path_parts = self._remove_junk_start_of_path(path=base_path)
        if len(cleaned_base_path_parts) > 0:
            module_path = "."
            if len(cleaned_base_path_parts) > 1:
                module_path += f"{'.'.join(cleaned_base_path_parts[1:])}."
            module_path += module_name
            return module_path, cleaned_base_path_parts[0]
        return None, None

    def _get_relative_filepath(self, filepath: str) -> Optional[str]:
        relative_filepath = os.path.relpath(filepath, self.root_filepath)
        cleaned_relative_filepath_parts = self._remove_junk_start_of_path(path=relative_filepath)
        return os.path.join(*cleaned_relative_filepath_parts) if len(cleaned_relative_filepath_parts) > 0 else None

    def _import_module(self, module_name: str, filepath: str) -> Optional[ModuleType]:
        try:
            # We first try to import the module naively with only their
            # module name. This will work when trying to import libraries.
            return importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            # If this failed, we try to import the module as a file not inside a library. We do so by creating a relative
            # module path to the module from the current file, and we try to import the module from its relative path.
            try:
                filepath_relative_to_current_module = os.path.relpath(os.path.dirname(filepath), os.path.abspath(os.path.dirname(__file__)))
                # We need a filepath relative to the current module, in order to try to import the file module. All the imports done in a file must be relative
                # to the file trying to import the module. This relative filepath is not destined to be used in the archive paths when packaging the code.
                module_path, module_package = self._path_to_module_path(base_path=str(filepath_relative_to_current_module), module_name=module_name)
                if module_path is not None and module_package is not None:
                    return importlib.import_module(name=module_path, package=module_package)
                else:
                    return None
            except ModuleNotFoundError as e:
                # If both the import as a library and as a file unfortunately
                # failed, we can stop trying to import the module.
                print(message_with_vars(
                    message="Importing of module failed as both a library import and file import",
                    vars_dict={'module_name': module_name, 'exception': e}
                ))
                return None

    def add_package_by_name(self, package_name: str, current_filepath: str):
        if package_name in self.packages:
            return

        imported_package_module = self._import_module(module_name=package_name, filepath=current_filepath)
        if imported_package_module is not None:
            imported_package_module_filepath: Optional[str] = getattr(imported_package_module, '__file__', None)
            if imported_package_module_filepath is not None:
                if python_base_libs_folder_path not in imported_package_module_filepath:
                    path_imported_package_module_filepath = Path(imported_package_module_filepath)

                    if self.system_os == 'windows' and path_imported_package_module_filepath.suffix == '.pyd':
                        if self.target_os == 'linux':
                            path_imported_package_module_filepath = path_imported_package_module_filepath.with_suffix('.so')
                            imported_package_module_filepath = str(path_imported_package_module_filepath)
                            if not path_imported_package_module_filepath.is_file():
                                print(make_no_os_matching_file_warning_message(
                                    system_os=self.system_os, target_os=self.target_os,
                                    source_filepath=path_imported_package_module_filepath
                                ))
                                return
                    elif self.system_os == 'linux' and path_imported_package_module_filepath == '.so':
                        if self.target_os == 'windows':
                            path_imported_package_module_filepath = path_imported_package_module_filepath.with_suffix('.pyd')
                            imported_package_module_filepath = str(path_imported_package_module_filepath)
                            if not path_imported_package_module_filepath.is_file():
                                print(make_no_os_matching_file_warning_message(
                                    system_os=self.system_os, target_os=self.target_os,
                                    source_filepath=path_imported_package_module_filepath
                                ))
                                return

                    package_distribution_name = get_distribution_name_of_package(package_filepath=imported_package_module_filepath)
                    if package_distribution_name is not None:
                        # If the file has been found inside a library
                        if package_distribution_name not in self.packages:
                            package_distribution: Optional[EggInfoDistribution] = self.distribution_path.get_distribution(package_distribution_name)
                            if package_distribution is not None:
                                package_requirements: Set[str] = getattr(package_distribution, 'run_requires', set())
                                # todo: do something with the package_requirements ?

                            if package_distribution_name not in self.packages:
                                package_relative_filepath = get_package_relative_filepath(
                                    absolute_filepath=imported_package_module_filepath, package_name=package_name
                                )
                                self.packages[package_distribution_name] = PackageItem(
                                    absolute_filepath=imported_package_module_filepath,
                                    relative_filepath=package_relative_filepath,
                                )
                                self.process_file(filepath=imported_package_module_filepath, base_package_name=package_name)
                    else:
                        # If the file is a standalone file not from a library
                        file_id = f"{package_name}{Path(imported_package_module_filepath).suffix}"
                        if file_id not in self.files:
                            file_relative_filepath = self._get_relative_filepath(filepath=imported_package_module_filepath)
                            self.files[file_id] = PackageItem(
                                absolute_filepath=imported_package_module_filepath,
                                relative_filepath=file_relative_filepath,
                            )
                            self.process_file(filepath=imported_package_module_filepath, base_package_name=package_name)

    def process_node(self, node: Any, current_module: str, current_filepath: str):
        if isinstance(node, ast.ImportFrom):
            module = node.module or current_module
            self.add_package_by_name(package_name=module, current_filepath=current_filepath)
            for name_item in node.names:
                self.add_package_by_name(package_name=f"{module}.{name_item.name}", current_filepath=current_filepath)

        elif isinstance(node, ast.Import):  # excluding the 'as' part of import
            for name_item in node.names:
                self.add_package_by_name(package_name=name_item.name, current_filepath=current_filepath)

        elif isinstance(node, ast.FunctionDef):
            for child_node in node.body:
                child_node_single_name: Optional[str] = getattr(child_node, 'name', None)
                self.process_node(node=child_node, current_module=child_node_single_name or current_module, current_filepath=current_filepath)

                child_node_names: Optional[list] = getattr(child_node, 'names', None)
                if child_node_names is not None:
                    for child_node_name_item in child_node_names:
                        child_node_name_item_value: Optional[str] = getattr(child_node_name_item, 'name', None)
                        self.process_node(node=child_node, current_module=child_node_name_item_value or current_module, current_filepath=current_filepath)

        elif isinstance(node, ast.ClassDef):
            for child_node in node.body:
                child_node_name_value: Optional[str] = getattr(child_node, 'name', None)
                self.process_node(node=child_node, current_module=child_node_name_value or current_module, current_filepath=current_filepath)

        elif isinstance(node, ast.If):
            for child_node in node.body:
                child_node_single_name: Optional[str] = getattr(child_node, 'name', None)
                self.process_node(node=child_node, current_module=child_node_single_name or current_module, current_filepath=current_filepath)
        else:
            print(f"Node {node.__class__} not supported")

    def process_file(self, filepath: str, base_package_name: Optional[str] = None):
        filepath = Path(filepath)
        if not filepath.exists():
            raise Exception(f"Filepath does not exist : {str(filepath)}")

        if filepath.suffix == '.py':
            file = filepath.open('r')
            file_content = file.read()
            for node in ast.iter_child_nodes(ast.parse(file_content)):
                self.process_node(node=node, current_module=str(filepath), current_filepath=str(filepath))
        else:
            module_key = base_package_name or filepath.stem
            file_id = f"{module_key}{filepath.suffix}"
            relative_filepath = get_package_relative_filepath(absolute_filepath=str(filepath), package_name=module_key)
            self.files[file_id] = PackageItem(absolute_filepath=str(filepath), relative_filepath=relative_filepath)

    def import_folder(self, folderpath: str, excluded_folders_names: Optional[List[str]] = None, excluded_files_extensions: Optional[List[str]] = None):
        folderpath_path = Path(folderpath)
        for root_dirpath, dirs, filenames in os.walk(folderpath, topdown=True):
            # The topdown arg allow to modify the dirs list in the walk, and so we can easily exclude folders.
            dirs[:] = [dirpath for dirpath in dirs if Path(dirpath).name not in excluded_folders_names]
            relative_root_dirpath = os.path.join(folderpath_path.stem, root_dirpath.replace(folderpath, "").strip("\\").strip("/"))
            for filename in filenames:
                filename = Path(filename)
                if filename.suffix not in excluded_files_extensions:
                    # todo: exclude .pyd files when building for windows and exclude .so files when building for windows
                    module_key = relative_root_dirpath.replace("\\", ".") + f".{filename.stem}"
                    module_filepath = os.path.join(root_dirpath, str(filename))
                    relative_filepath = get_package_relative_filepath(absolute_filepath=module_filepath, package_name=module_key)

                    file_id = f"{module_key}{filename.suffix}"
                    self.files[file_id] = PackageItem(absolute_filepath=module_filepath, relative_filepath=relative_filepath)

def make_no_os_matching_file_warning_message(system_os: Resolver.TARGETS_OS_LITERAL, target_os: Resolver.TARGETS_OS_LITERAL, source_filepath: str) -> str:
    source_extension = Resolver.OS_TO_COMPILED_EXTENSIONS[system_os]
    target_extension = Resolver.OS_TO_COMPILED_EXTENSIONS[target_os]
    return (
        f"WARNING - No matching .{source_extension} file found to replace a .{target_extension} file at {source_filepath}. "
        f"Make sure that you both have a compiled .{source_extension} and .{target_extension} file with the same names and paths. "
        f"Otherwise, try to compile your application on a {target_os} computer or virtual machine."
    )


if __name__ == '__main__':
    _resolver = Resolver(root_filepath="F:/Inoft/anvers_1944_project/inoft_vocal_engine/web_interface/applications/data_lake/efs_mutator/lambda_function.py", target_os=Resolver.LINUX_KEY)
    """_resolver.import_folder(folderpath="F:/Inoft/anvers_1944_project/inoft_vocal_framework", excluded_files_extensions=[".wav", ".mp3"], excluded_folders_names=[
        "__pycache__", ".idea", ".git", "dist", "speech_synthesis", "temp", "tmp", "target", "build_lame", "src", "DOC_BUILD_CARGO", "lame-3.100"
    ])"""
    _resolver.process_file(_resolver.root_filepath)
    print(_resolver)
    from serverlesspack.packager import package_lambda_layer, package_files
    # package_lambda_layer(_resolver.packages)
    package_files(_resolver.files, "F:/Inoft/anvers_1944_project/inoft_vocal_engine/web_interface/applications/data_lake/efs_mutator")
