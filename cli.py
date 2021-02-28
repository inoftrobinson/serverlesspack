import os

import click
from serverlesspack.configuration_client import ConfigClient
from serverlesspack.imports_resolver import Resolver
from serverlesspack.packager import package_files, package_lambda_layer


@click.command()
@click.option('-os', '--target_os', prompt="OS to compile to", type=click.Choice(['windows', 'linux']))
@click.option('-config', '--config_filepath', prompt="Filepath of config file", type=click.Path(exists=True))
@click.option('-v', '--verbose', type=bool)
def package(target_os: str, config_filepath: str, verbose: bool):
    config = ConfigClient(verbose=verbose).load_render_config_file(filepath=config_filepath, target_os=target_os)
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

    package_files(resolver.files, dist_dirpath)

    if click.confirm("Package the dependencies as lambda layer ?"):
        lambda_layer_dirpath = os.path.join(dist_dirpath, "lambda_layer")
        selected_python_version: str = click.prompt(
            text="For which Python version do you want to create the layer ?",
            type=click.Choice(['3.5', '3.6', '3.7', '3.8', '3.9']), confirmation_prompt=True
        )
        package_lambda_layer(packages=resolver.packages, target_dirpath=lambda_layer_dirpath, python_version=selected_python_version)


if __name__ == '__main__':
    package()
