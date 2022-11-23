import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Callable, Dict, Optional

import click
from .configuration_client import ConfigClient
from .imports_resolver import Resolver
from .packager import ContentFileItem, LocalFileItem, make_base_python_layer_packages_dir, package_files, \
    files_to_zip, files_to_folder, resolve_install_and_get_dependencies_files


@dataclass
class PackageApiOutput:
    code_path: str
    layer_path: Optional[str]

class FormatType(Enum):
    zip = 'zip'
    code = 'code'

class PythonVersion(Enum):
    _36 = '3.6'
    _37 = '3.7'
    _38 = '3.8'
    _39 = '3.9'
    _310 = '3.10'


package_files_handlers_by_format_switch: Dict[str, Callable[[str, str, List[LocalFileItem], List[ContentFileItem]], str]] = {
    'zip': files_to_zip, 'folder': files_to_folder
}
def safe_get_package_files_handler(format_type: str):
    handler = package_files_handlers_by_format_switch.get(format_type, None)
    if handler is None:
        raise Exception(f"Format {format_type} not supported")
    return handler


@click.command()
@click.option('-os', '--target_os', prompt="OS to compile to", type=click.Choice(['windows', 'linux']))
@click.option('-config', '--config_filepath', prompt="Filepath of config file", type=click.Path(exists=True))
@click.option('-v', '--verbose', type=bool, required=False)
@click.option('-f', '--format_type', type=click.Choice([e.value for e in FormatType]), required=False)
@click.option('-pv', '--python_version', type=click.Choice([e.value for e in FormatType]), required=False)
@click.option('-t', '--should_save_trace_files', type=bool, required=False)
def package_cli(
        target_os: str, config_filepath: str, verbose: bool = False,
        format_type: Optional[FormatType] = None, python_version: Optional[PythonVersion] = None,
        should_save_trace_files: Optional[bool] = None
):
    package_api(
        target_os=target_os, config_filepath=config_filepath, verbose=verbose,
        format_type=format_type, python_version=python_version,
        should_save_trace_files=should_save_trace_files
    )

def package_api(
        target_os: str, config_filepath: str, verbose: bool = False,
        format_type: Optional[FormatType] = None, python_version: Optional[PythonVersion] = None,
        should_save_trace_files: Optional[bool] = None
) -> PackageApiOutput:

    if should_save_trace_files is None:
        should_save_trace_files = click.confirm("Should save traces file ?")
    should_save_trace_files: bool

    config = ConfigClient(verbose=verbose).load_render_config_file(
        filepath=config_filepath, target_os=target_os,
        overriding_attributes={
            'format': format_type, 'python_version': python_version
        }
    )

    package_files_handler = safe_get_package_files_handler(format_type=config.format)

    resolver = Resolver(root_filepath=config.root_filepath, target_os=target_os, verbose=verbose)
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

    output_base_dirpath: str = (
        Path(os.path.realpath(config.project_root_dir)).parent
        if config.project_root_dir is not None else
        os.path.dirname(os.path.abspath(config_filepath))
    )

    dist_dirpath = os.path.join(os.path.dirname(config_filepath), "dist")
    if not os.path.exists(dist_dirpath):
        os.makedirs(dist_dirpath)

    if config.type == 'layer':
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
            use_prototype_docker_install=config.use_prototype_docker_pip_install
        )
        # We package both the application files and the dependencies files under the
        # build key (which will output either a build.zip file or a build folder)
        code_and_dependencies_output_path = package_files_handler(
            dist_dirpath, 'build', [*local_file_items, *dependencies_local_file_items], content_file_items
        )
        return PackageApiOutput(code_path=code_and_dependencies_output_path, layer_path=None)

    elif config.type == 'code':
        # When packaging as code we package the application files without any archive_prefix, which we will then package.
        # After that, was ask the user if he want to package his applications dependencies as a lambda layer.
        base_layer_dirpath = make_base_python_layer_packages_dir(python_version=config.python_version)
        local_file_items, content_file_items = package_files(
            included_files_absolute_paths=resolver.included_files_absolute_paths,
            output_base_dirpath=output_base_dirpath
        )
        code_output_path: str = package_files_handler(dist_dirpath, 'build', local_file_items, content_file_items)
        # We first package the applications files under the build key

        if not click.confirm("Package your application dependencies as lambda layer ?"):
            return PackageApiOutput(code_path=code_output_path, layer_path=None)
        else:
            lambda_layer_dirpath = os.path.join(dist_dirpath, 'lambda_layer')
            dependencies_local_file_items = resolve_install_and_get_dependencies_files(
                resolver=resolver,
                lambda_layer_dirpath=lambda_layer_dirpath,
                base_layer_dirpath=base_layer_dirpath,
                python_version=config.python_version,
                use_prototype_docker_install=config.use_prototype_docker_pip_install
            )
            lambda_layer_format_handler = safe_get_package_files_handler(format_type=config.format)
            layer_output_path = lambda_layer_format_handler(dist_dirpath, 'lambda_layer', dependencies_local_file_items, [])
            # Then, if the user asked to package his dependencies, we package them under the lambda_layer
            # key (which will output either a lambda_layer.zip file or a lambda_layer folder)
            return PackageApiOutput(code_path=code_output_path, layer_path=layer_output_path)
    else:
        raise Exception(f"Config type of {config.type} not supported")


if __name__ == '__main__':
    package_cli()
