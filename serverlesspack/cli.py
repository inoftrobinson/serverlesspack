import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Callable, Dict, Optional, Set, Any

import click
from .configuration_client import ConfigClient, Config
from .imports_resolver import Resolver
from .packager import ContentFileItem, LocalFileItem, make_base_python_layer_packages_dir, package_files, \
    files_to_zip, files_to_folder, resolve_install_and_get_dependencies_files


@dataclass
class PackageApiOutput:
    code_path: str
    layer_path: Optional[str]
    required_dependencies_names: Set[str]

class PackageType(Enum):
    code = 'code'
    layer = 'layer'

class OutputType(Enum):
    zip = 'zip'
    folder = 'folder'

class PythonVersion(Enum):
    _36 = '3.6'
    _37 = '3.7'
    _38 = '3.8'
    _39 = '3.9'
    _310 = '3.10'


package_files_handlers_by_output_type_switch: (
    Dict[str, Callable[[str, str, List[LocalFileItem], List[ContentFileItem]], str]]
) = {
    'zip': files_to_zip, 'folder': files_to_folder
}
def safe_get_package_files_handler(output_type: str):
    handler = package_files_handlers_by_output_type_switch.get(output_type, None)
    if handler is None:
        raise Exception(f"Format {output_type} not supported")
    return handler


@click.command()
@click.option('-os', '--target_os', prompt="OS to compile to", type=click.Choice(['windows', 'linux']))
@click.option('-config', '--config_filepath', prompt="Filepath of config file", type=click.Path(exists=True))
@click.option('-v', '--verbose', type=bool, required=False)
@click.option('-pt', '--package_type', type=click.Choice([e.value for e in PackageType]), required=False)
@click.option('-ot', '--output_type', type=click.Choice([e.value for e in OutputType]), required=False)
@click.option('-pv', '--python_version', type=click.Choice([e.value for e in PythonVersion]), required=False)
@click.option('-t', '--should_save_trace_files', type=bool, required=False)
@click.option('-dl', '--package_dependencies_in_layer_for_code_package', type=bool, required=False)
def package_cli(
        target_os: str, config_filepath: str, verbose: bool = False,
        package_type: Optional[PackageType] = None, output_type: Optional[OutputType] = None,
        python_version: Optional[PythonVersion] = None,
        should_save_trace_files: Optional[bool] = None,
        package_dependencies_in_layer_for_code_package: Optional[bool] = None
):
    package_api(
        target_os=target_os, config_filepath=config_filepath, verbose=verbose,
        package_type=package_type, output_type=output_type,
        python_version=python_version,
        should_save_trace_files=should_save_trace_files,
        package_dependencies_in_layer_for_code_package=package_dependencies_in_layer_for_code_package
    )

def package_api(
        target_os: str, config_filepath: str, verbose: bool = False,
        output_type: Optional[OutputType] = None, package_type: Optional[PackageType] = None,
        python_version: Optional[PythonVersion] = None,
        should_save_trace_files: Optional[bool] = None,
        package_dependencies_in_layer_for_code_package: Optional[bool] = None
) -> PackageApiOutput:

    if should_save_trace_files is None:
        should_save_trace_files = click.confirm("Should save traces file ?")
    should_save_trace_files: bool

    config = ConfigClient(verbose=verbose).load_render_config_file(
        filepath=config_filepath, target_os=target_os,
        overriding_attributes={
            'package_type': package_type,
            'output_type': output_type,
            'python_version': python_version
        }
    )

    def python_path_wrapper(f: Callable[[], Any]) -> Any:
        print("Adding content root to Python path")
        added_paths: Set[str] = set()

        import sys
        content_root_dirpath = os.path.abspath(os.path.dirname(os.path.abspath(config.root_filepath)))
        for root_dirpath, dirs, filenames in os.walk(content_root_dirpath):
            for dirname in dirs:
                dirpath: str = os.path.join(root_dirpath, dirname)
                expected_init_filepath: str = os.path.join(dirpath, '__init__.py')
                if os.path.exists(expected_init_filepath):
                    if config.python_path_exclusions is None or not config.python_path_exclusions.path_is_excluded(path=root_dirpath):
                        full_path: str = os.path.join(root_dirpath, dirname)
                        added_paths.add(full_path)
                        sys.path.insert(0, full_path)
        print(f"Added {len(added_paths)} paths to Python path")
        print(sys.path)

        try:
            return f()
        finally:
            for path in added_paths:
                sys.path.remove(path)
            print("Removed all added paths from Python path")

    def execute_package_api():
        package_files_handler = safe_get_package_files_handler(output_type=config.output_type)

        resolver = Resolver(
            root_filepath=config.root_filepath, target_os=target_os,
            global_exclusions=config.global_exclusions, verbose=verbose
        )
        resolver.process_file(config.root_filepath)

        for filepath in config.filepaths_includes:
            if os.path.exists(filepath):
                # Technically, the filepath might not be a Python file, but we still use the
                # add_python_file to potentially handle the case where it is a Python file.
                resolver.add_python_file(filepath=filepath)

        for folderpath, folder_config in config.folders_includes.items():
            resolver.import_folder(
                folderpath=folderpath,
                included_folders_names=folder_config.included_folders_names,
                included_files_extensions=folder_config.included_files_extensions,
                excluded_folders_names=folder_config.excluded_folders_names,
                excluded_files_extensions=folder_config.excluded_files_extensions
            )

        if should_save_trace_files is True:
            resolver.save_traces_to_json()

        print(f">>> Required dependencies names : {resolver.included_dependencies_names}")

        output_base_dirpath: str = (
            Path(os.path.realpath(config.project_root_dir)).parent
            if config.project_root_dir is not None else
            os.path.dirname(os.path.abspath(config_filepath))
        )

        dist_dirpath = os.path.join(os.path.dirname(config_filepath), "dist")
        if not os.path.exists(dist_dirpath):
            os.makedirs(dist_dirpath)

        if config.package_type == 'layer':
            # When packaging as a layer, we package the applications files with a base_layer_dirpath as the archive_prefix,
            # and we always install/resolve the dependencies of the applications in the same package as the application files.
            base_layer_dirpath = make_base_python_layer_packages_dir(python_version=config.python_version)
            local_file_items, content_file_items = package_files(
                included_files_absolute_paths=resolver.included_files_absolute_paths,
                archive_prefix=base_layer_dirpath, output_base_dirpath=output_base_dirpath
            )
            lambda_layer_dirpath = os.path.join(dist_dirpath, 'lambda_layer')
            dependencies_local_file_items = resolve_install_and_get_dependencies_files(
                resolver=resolver,
                lambda_layer_dirpath=lambda_layer_dirpath,
                base_layer_dirpath=base_layer_dirpath,
                python_version=config.python_version,
                use_prototype_docker_install=config.use_prototype_docker_pip_install,
                should_remove_runtime_provided_packages=config.should_remove_runtime_provided_packages
            )
            # We package both the application files and the dependencies files under the
            # build key (which will output either a build.zip file or a build folder)
            code_and_dependencies_output_path = package_files_handler(
                dist_dirpath, 'build', [*local_file_items, *dependencies_local_file_items], content_file_items
            )
            return PackageApiOutput(
                code_path=code_and_dependencies_output_path, layer_path=None,
                required_dependencies_names=resolver.included_dependencies_names
            )

        elif config.package_type == 'code':
            # When packaging as code we package the application files without any archive_prefix, which we will then package.
            # After that, was ask the user if he wants to package his applications dependencies as a lambda layer.
            base_layer_dirpath = make_base_python_layer_packages_dir(python_version=config.python_version)
            local_file_items, content_file_items = package_files(
                included_files_absolute_paths=resolver.included_files_absolute_paths,
                output_base_dirpath=output_base_dirpath
            )
            code_output_path: str = package_files_handler(dist_dirpath, 'build', local_file_items, content_file_items)
            # We first package the applications files under the build key

            confirmed_package_dependencies_in_layer_for_code_package: bool = (
                click.confirm("Package your application dependencies as lambda layer ?")
                if package_dependencies_in_layer_for_code_package is None else
                package_dependencies_in_layer_for_code_package
            )

            if not confirmed_package_dependencies_in_layer_for_code_package:
                return PackageApiOutput(
                    code_path=code_output_path, layer_path=None,
                    required_dependencies_names=resolver.included_dependencies_names
                )
            else:
                lambda_layer_dirpath = os.path.join(dist_dirpath, 'lambda_layer')
                dependencies_local_file_items = resolve_install_and_get_dependencies_files(
                    resolver=resolver,
                    lambda_layer_dirpath=lambda_layer_dirpath,
                    base_layer_dirpath=base_layer_dirpath,
                    python_version=config.python_version,
                    use_prototype_docker_install=config.use_prototype_docker_pip_install,
                    should_remove_runtime_provided_packages=config.should_remove_runtime_provided_packages
                )
                lambda_layer_format_handler = safe_get_package_files_handler(output_type=config.output_type)
                layer_output_path = lambda_layer_format_handler(dist_dirpath, 'lambda_layer', dependencies_local_file_items, [])
                # Then, if the user asked to package his dependencies, we package them under the lambda_layer
                # key (which will output either a lambda_layer.zip file or a lambda_layer folder)
                return PackageApiOutput(
                    code_path=code_output_path, layer_path=layer_output_path,
                    required_dependencies_names=resolver.included_dependencies_names
                )
        else:
            raise Exception(f"Package type of {config.package_type} not supported")

    return python_path_wrapper(execute_package_api)

if __name__ == '__main__':
    package_cli()
