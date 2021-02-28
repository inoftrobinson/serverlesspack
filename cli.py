import click
from serverlesspack.configuration_client import ConfigClient
from serverlesspack.imports_resolver import Resolver
from serverlesspack.packager import package_files


@click.command()
@click.option('-os', '--target_os', prompt="OS to compile to", type=click.Choice(['windows', 'linux']))
@click.option('-config', '--config_filepath', prompt="Filepath of config file", type=click.Path(exists=True))
def package(target_os: str, config_filepath: str):
    config = ConfigClient().load_render_config_file(filepath=config_filepath, target_os=target_os)
    resolver = Resolver(root_filepath=config.root_filepath, target_os=target_os)
    resolver.process_file(config.root_filepath)
    for folderpath, folder_config in config.folders_includes.items():
        resolver.import_folder(
            folderpath=folderpath,
            excluded_folders_names=folder_config.excluded_folders_names,
            excluded_files_extensions=folder_config.excluded_files_extensions
        )
    package_files(resolver.files, "F:/Inoft/anvers_1944_project/inoft_vocal_engine/web_interface/applications/data_lake/efs_mutator")


if __name__ == '__main__':
    package()
