import ast
import os
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple

from asciitree import LeftAligned
from pkg_resources import EggInfoDistribution
import click
from tqdm import tqdm

from .exceptions import OutputDirpathTooLow
from .imports_resolver import Resolver
from .packages_lock_client import PackagesLockClient
from .utils import message_with_vars


class BaseFileItem:
    def __init__(self, archive_prefix: Optional[str], relative_filepath: str):
        self.relative_filepath = f"{archive_prefix}/{relative_filepath}" if archive_prefix is not None else relative_filepath

class LocalFileItem(BaseFileItem):
    def __init__(self, archive_prefix: Optional[str], relative_filepath: str, absolute_filepath: str):
        super().__init__(archive_prefix=archive_prefix, relative_filepath=relative_filepath)
        self.absolute_filepath = absolute_filepath

class ContentFileItem(BaseFileItem):
    def __init__(self, archive_prefix: Optional[str], relative_filepath: str, content: str):
        super().__init__(archive_prefix=archive_prefix, relative_filepath=relative_filepath)
        self.content = content

class FileItemsFactory:
    def __init__(self, archive_prefix: Optional[str] = None):
        self.archive_prefix = archive_prefix

    def make_local_file_item(self, relative_filepath: str, absolute_filepath: str) -> LocalFileItem:
        return LocalFileItem(
            archive_prefix=self.archive_prefix,
            relative_filepath=relative_filepath,
            absolute_filepath=absolute_filepath
        )

    def make_content_file_item(self, relative_filepath: str, content: str) -> ContentFileItem:
        return ContentFileItem(
            archive_prefix=self.archive_prefix,
            relative_filepath=relative_filepath,
            content=content
        )


def make_base_python_layer_packages_dir(python_version: str) -> str:
    return f"python/lib/python{python_version}/site-packages"

def make_absolute_python_layer_packages_dirpath(base_target_dirpath: str, python_version: str) -> str:
    return f"{base_target_dirpath}/{make_base_python_layer_packages_dir(python_version=python_version)}"

def install_packages_to_dir(packages_names: Set[str] or List[str], target_dirpath: str):
    packages_string = " ".join(packages_names)
    return subprocess.run(f'pip install {packages_string} --target="{target_dirpath}" --upgrade"')

def package_lambda_layer(packages_names: Set[str] or List[str], target_dirpath: str, python_version: str):
    python_layer_packages_dirpath = make_absolute_python_layer_packages_dirpath(base_target_dirpath=target_dirpath, python_version=python_version)
    return install_packages_to_dir(packages_names=packages_names, target_dirpath=python_layer_packages_dirpath)


def process_file(absolute_filepath: str, common_prefix_across_all_files: str) -> Optional[str]:
    """
    :return: None if file did not required processing or its processing failed, processed content otherwise
    """
    raise Exception("process_file is deprecated")
    path_absolute_filepath = Path(absolute_filepath)
    if path_absolute_filepath.suffix == '.py':
        with open(absolute_filepath, mode='r') as file:
            file_content = file.read()
            from .mutators_node_handlers import mutators_node_handlers_switch
            try:
                file_content_lines: List[str] = file_content.splitlines()
                processed_content_lines: List[str] = []

                if "editor_blueprint.py" in absolute_filepath:
                    print("e")

                last_line_num: int = 0
                for node in ast.iter_child_nodes(ast.parse(file_content)):
                    if node.lineno > last_line_num + 1:
                        lines_to_add: List[str] = file_content_lines[last_line_num:node.lineno-1]
                        processed_content_lines.extend(lines_to_add)
                        # last_line_num =
                    last_line_num: int = node.end_lineno

                    handler = mutators_node_handlers_switch.get(node.__class__, None)
                    modified_content: Optional[str] = handler(common_prefix_across_all_files, node, absolute_filepath)
                    if modified_content is None:
                        processed_content_lines.extend(file_content_lines[node.lineno-1:node.end_lineno-1])
                    else:
                        processed_content_lines.append(modified_content)
                output_file_content = "\n".join(processed_content_lines)
                return output_file_content
            except SyntaxError as e:
                print(message_with_vars(
                    message="Python file contained a syntax error. The file has been packaged but not fully processed.",
                    vars_dict={'filepath': absolute_filepath, 'exception': e}
                ))
    return None

def package_files(included_files_absolute_paths: Set[str], output_base_dirpath: str, archive_prefix: Optional[str] = None) -> Tuple[List[LocalFileItem], List[ContentFileItem]]:
    local_files_items: List[LocalFileItem] = list()
    content_files_items: Dict[str, ContentFileItem] = dict()

    common_prefix_across_all_files = os.path.commonprefix([absolute_filepath for absolute_filepath in included_files_absolute_paths])
    if len(Path(output_base_dirpath).parts) > len(Path(common_prefix_across_all_files).parts):
        raise OutputDirpathTooLow(highest_found_directory=common_prefix_across_all_files, output_base_dirpath=output_base_dirpath)

    factory = FileItemsFactory(archive_prefix=archive_prefix)

    for absolute_filepath in tqdm(included_files_absolute_paths, desc="Preparing files and creating missing __init__ files..."):
        relative_filepath = os.path.relpath(absolute_filepath, output_base_dirpath)
        local_files_items.append(factory.make_local_file_item(
            relative_filepath=relative_filepath, absolute_filepath=absolute_filepath
        ))

        folder_parts: tuple = Path(os.path.dirname(relative_filepath)).parts
        for i_part in range(len(folder_parts)):
            current_folder_part_relative_path: str = os.path.join(*folder_parts[0:i_part + 1])
            expected_init_file_relative_filepath: str = os.path.join(current_folder_part_relative_path, "__init__.py")
            expected_init_file_absolute_filepath: str = os.path.join(output_base_dirpath, expected_init_file_relative_filepath)
            if expected_init_file_absolute_filepath not in included_files_absolute_paths and expected_init_file_absolute_filepath not in content_files_items:
                content_files_items[expected_init_file_relative_filepath] = factory.make_content_file_item(
                    content="", relative_filepath=expected_init_file_relative_filepath
                )

    return local_files_items, list(content_files_items.values())

def recursive_get_files_in_layer_folder(source_dirpath: str, base_layer_dirpath: str) -> List[LocalFileItem]:
    output_local_file_items: List[LocalFileItem] = list()
    for root_dirpath, dirs, filenames in os.walk(source_dirpath):
        for filename in filenames:
            absolute_filepath = os.path.abspath(os.path.join(root_dirpath, filename))
            relative_filepath = os.path.relpath(absolute_filepath, source_dirpath)
            output_local_file_items.append(LocalFileItem(
                archive_prefix=base_layer_dirpath,
                relative_filepath=relative_filepath,
                absolute_filepath=absolute_filepath
            ))
    return output_local_file_items

def install_dependencies_and_get_files(dependencies_names: Set[str], target_dirpath: str, base_layer_dirpath: str) -> List[LocalFileItem]:
    installation_result = install_packages_to_dir(packages_names=dependencies_names, target_dirpath=target_dirpath)
    return recursive_get_files_in_layer_folder(source_dirpath=target_dirpath, base_layer_dirpath=base_layer_dirpath)

def resolve_already_installed_dependencies(dependencies_distributions: Dict[str, Optional[EggInfoDistribution]], dirpath_to_search_into: str) -> Set[str]:
    reused_dependencies_tree_data: Dict[str, dict] = dict()
    missing_dependencies_names: Set[str] = set()

    for dependency_name, dependency_distribution in dependencies_distributions.items():
        if dependency_distribution is None:
            missing_dependencies_names.add(dependency_name)
        else:
            current_dependency_not_fully_installed = False
            current_dependency_found_modules_paths = set()
            for module in dependency_distribution.modules:
                expected_module_path = os.path.join(dirpath_to_search_into, module)
                if not os.path.exists(expected_module_path):
                    current_dependency_not_fully_installed = True
                    break
                else:
                    current_dependency_found_modules_paths.add(expected_module_path)

            if current_dependency_not_fully_installed is True:
                missing_dependencies_names.add(dependency_name)
            else:
                reused_dependencies_tree_data[dependency_name] = {
                    os.path.abspath(module_path): {} for module_path in current_dependency_found_modules_paths
                }

    if len(reused_dependencies_tree_data) > 0:
        print(LeftAligned()({'Re-used packages': reused_dependencies_tree_data}))
    return missing_dependencies_names

def resolve_install_and_get_dependencies_files(resolver: Resolver, lambda_layer_dirpath: str, base_layer_dirpath: str) -> List[LocalFileItem]:
    # requirements = PackagesLockClient().open_requirements("./requirements.txt")
    # todo: add support for requirements.txt instead of fully relying on dependencies
    #  detection ? Or display insights into which requirements is not used

    lambda_layer_dirpath: str = os.path.abspath(lambda_layer_dirpath)

    """
    dependencies_names_requiring_installation = resolve_already_installed_dependencies(
        dependencies_distributions=resolver.included_dependencies_distributions,
        dirpath_to_search_into=lambda_layer_dirpath
    )
    """
    if os.path.exists(lambda_layer_dirpath):
        shutil.rmtree(lambda_layer_dirpath)
        # Remove all files in lambda_layer_dirpath to make sure to not
        # package files from old builds that are not required in new one
    dependencies_names_requiring_installation = resolver.included_dependencies_distributions

    if len(dependencies_names_requiring_installation) > 0:
        dependencies_installation_result = install_packages_to_dir(
            packages_names=resolver.included_dependencies_names,
            target_dirpath=lambda_layer_dirpath,
        )
    dependencies_local_file_items = recursive_get_files_in_layer_folder(
        source_dirpath=lambda_layer_dirpath, base_layer_dirpath=base_layer_dirpath
    )
    return dependencies_local_file_items


def files_to_zip(root_path: str, destination_file_key: str, local_files_items: List[LocalFileItem], content_files_items: List[ContentFileItem]) -> str:
    output_zip_filepath = os.path.join(root_path, f'{destination_file_key}.zip')
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)
    build_temp_folderpath = os.path.join(root_path, "build_temp")

    import zipfile
    with zipfile.ZipFile(output_zip_filepath, 'w', compression=zipfile.ZIP_DEFLATED) as zip_object:
        # The ZIP_DEFLATED method will actually compress the file (where as the ZIP_STORED will store the data as a zip object, but
        # will practically not compress the data), and the ZIP_DEFLATED as been tested and can be opened by AWS Lambda, where as
        # other rarer methods (for example, like ZIP_BZIP2) are not supported and the file could not be opened by AWS Lambda.
        for local_file_item in tqdm(local_files_items, desc="Zipping local files"):
            zip_object.write(filename=local_file_item.absolute_filepath, arcname=local_file_item.relative_filepath)

        for content_file_item in tqdm(content_files_items, desc="Zipping content files"):
            temporary_content_container_filepath = os.path.join(build_temp_folderpath, content_file_item.relative_filepath)
            if not os.path.isdir(os.path.dirname(temporary_content_container_filepath)):
                os.makedirs(os.path.dirname(temporary_content_container_filepath))

            with open(temporary_content_container_filepath, 'w+') as temp_file:
                temp_file.write(content_file_item.content)

            zip_object.write(filename=temporary_content_container_filepath, arcname=content_file_item.relative_filepath)
            os.remove(temporary_content_container_filepath)
            # We do not use 'writestr' function of the ZipFile library, instead we write the content of temp file to temporary
            # file, which we then write to the archive, because using writestr will create file's that are in read only mode, which
            # will not be usable by AWS Lambda. And I never figured out how to write file in read and write mode with writestr.

    click.secho(f"Packaged zipped file available at {os.path.abspath(output_zip_filepath)}", fg='green')
    return output_zip_filepath

def files_to_folder(root_path: str, destination_dirname: str, local_files_items: List[LocalFileItem], content_files_items: List[ContentFileItem]) -> str:
    destination_dirpath = os.path.join(root_path, destination_dirname)

    for local_file_item in tqdm(local_files_items, desc="Copying local files"):
        absolute_target_filepath = os.path.join(destination_dirpath, local_file_item.relative_filepath)
        absolute_target_parent_dirname = os.path.dirname(absolute_target_filepath)
        if not os.path.exists(absolute_target_parent_dirname):
            os.makedirs(absolute_target_parent_dirname)
        shutil.copy(src=local_file_item.absolute_filepath, dst=absolute_target_filepath)

    for content_file_item in tqdm(content_files_items, desc="Writing content files"):
        absolute_target_filepath = os.path.join(destination_dirpath, content_file_item.relative_filepath)
        with open(absolute_target_filepath, "w+") as file:
            file.write(content_file_item.content)

    click.secho(f"Folder available at {os.path.abspath(destination_dirpath)}", fg='green')
    return destination_dirpath
