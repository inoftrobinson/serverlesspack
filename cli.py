import os
from typing import Set, List, Callable, Dict, Any

import click
from serverlesspack.configuration_client import ConfigClient
from serverlesspack.imports_resolver import Resolver
from serverlesspack.packager import package_files, package_lambda_layer, make_absolute_python_layer_packages_dirpath, \
    install_packages_to_dir, make_base_python_layer_packages_dir, LocalFileItem, files_to_zip, files_to_folder, \
    ContentFileItem, install_packages_and_get_files


@click.command()
@click.option('-os', '--target_os', prompt="OS to compile to", type=click.Choice(['windows', 'linux']))
@click.option('-config', '--config_filepath', prompt="Filepath of config file", type=click.Path(exists=True))
@click.option('-v', '--verbose', type=bool)
def package_cli(target_os: str, config_filepath: str, verbose: bool):
    package_api(target_os=target_os, config_filepath=config_filepath, verbose=verbose)

def package_api(target_os: str, config_filepath: str, verbose: bool):
    config = ConfigClient(verbose=verbose).load_render_config_file(filepath=config_filepath, target_os=target_os)

    package_files_handler = package_files_handlers_by_format_switch.get(config.format, None)
    if package_files_handler is None:
        raise Exception(f"Format {config.format} not supported")

    selected_python_version = prompt_python_version()

    resolver = Resolver(root_filepath=config.root_filepath, target_os=target_os, verbose=verbose)
    resolver.process_file(config.root_filepath)
    for folderpath, folder_config in config.folders_includes.items():
        resolver.import_folder(
            folderpath=folderpath,
            excluded_folders_names=folder_config.excluded_folders_names,
            excluded_files_extensions=folder_config.excluded_files_extensions
        )

    dist_dirpath = os.path.join(os.path.dirname(config_filepath), "dist")
    if not os.path.exists(dist_dirpath):
        os.makedirs(dist_dirpath)

    base_layer_dirpath = make_base_python_layer_packages_dir(python_version=selected_python_version)
    local_file_items, content_file_items = package_files(
        included_files_absolute_paths=resolver.included_files_absolute_paths, archive_prefix=base_layer_dirpath
    )

    if config.type == 'layer':
        lambda_layer_dirpath = os.path.join(dist_dirpath, "lambda_layer")
        installed_packages_local_file_items = install_packages_and_get_files(
            packages_names=resolver.included_packages_names,
            target_dirpath=lambda_layer_dirpath,
            base_layer_dirpath=base_layer_dirpath
        )
        package_files_handler(dist_dirpath, [*local_file_items, *installed_packages_local_file_items], content_file_items)

    elif config.type == 'code':
        package_files_handler(dist_dirpath, local_file_items, content_file_items)
        if click.confirm("Package the dependencies as lambda layer ?"):
            lambda_layer_dirpath = os.path.join(dist_dirpath, "lambda_layer")
            installed_packages_local_file_items = install_packages_and_get_files(
                packages_names=resolver.included_packages_names,
                target_dirpath=lambda_layer_dirpath,
                base_layer_dirpath=base_layer_dirpath
            )
            files_to_folder(dist_dirpath, installed_packages_local_file_items, [])
            # package_layer_api(packages_names=resolver.included_packages_names, target_dirpath=lambda_layer_dirpath)
    else:
        raise Exception(f"Config type of {config.type} not supported")

def prompt_python_version() -> str:
    return click.prompt(
        text="For which Python version do you want to create the layer ?",
        type=click.Choice(['3.5', '3.6', '3.7', '3.8', '3.9']), confirmation_prompt=True
    )

def package_layer_api(packages_names: Set[str] or List[str], target_dirpath: str):
    selected_python_version = prompt_python_version()
    package_lambda_layer(
        packages_names=packages_names,
        target_dirpath=target_dirpath,
        python_version=selected_python_version
    )

package_files_handlers_by_format_switch: Dict[str, Callable[[str, List[LocalFileItem], List[ContentFileItem]], Any]] = {
    'zip': files_to_zip, 'folder': files_to_folder
}


if __name__ == '__main__':
    package_cli()
