import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Literal, Set

import yaml
from pydantic import ValidationError, BaseModel, Field

class BaseExcludeItem(BaseModel):
    excluded_files_extensions: Optional[List[str]] = Field(default_factory=list)
    excluded_folders_names: Optional[List[str]] = Field(default_factory=list)
    
    @staticmethod
    def relative_path_is_in_absolute_path(relative_path: str, absolute_path: str) -> bool:
        from pathlib import Path
        formatted_relative_path: str = str(Path(relative_path))
        formatted_absolute_path: str = str(Path(absolute_path))
        return formatted_relative_path in formatted_absolute_path

    def path_is_excluded(self, path: str) -> bool:
        if self.excluded_folders_names is not None:
            for folder_name in self.excluded_folders_names:
                if self.relative_path_is_in_absolute_path(relative_path=folder_name, absolute_path=path):
                    return True

        if self.excluded_files_extensions is not None:
            from pathlib import Path
            path_instance = Path(path)
            if path_instance.suffix in self.excluded_files_extensions:
                return True

        return False

class BaseFolderIncludeItem(BaseExcludeItem):
    included_files_extensions: Optional[List[str]] = None
    included_folders_names: Optional[List[str]] = None

class SourceConfig(BaseModel):
    root_file: str
    project_root_dir: Optional[str] = None
    package_type: Optional[Literal['code', 'layer']] = None
    output_type: Optional[Literal['zip', 'folder']] = None
    python_version: Optional[str] = None
    filepaths_includes: Optional[List[str]] = None
    class FolderIncludeItem(BaseFolderIncludeItem):
        additional_linux: Optional[BaseFolderIncludeItem] = None
        additional_windows: Optional[BaseFolderIncludeItem] = None
    folders_includes: Optional[Dict[str, Optional[FolderIncludeItem]]] = None
    python_path_exclusions: Optional[BaseExcludeItem] = None
    global_exclusions: Optional[BaseExcludeItem] = None
    use_prototype_docker_pip_install: Optional[bool] = False
    should_remove_runtime_provided_packages: Optional[bool] = True

@dataclass
class Config:
    root_filepath: str
    project_root_dir: Optional[str]
    package_type: Literal['code', 'layer']
    output_type: Literal['zip', 'folder']
    python_version: str
    filepaths_includes: Set[str]
    folders_includes: Dict[str, BaseFolderIncludeItem]
    python_path_exclusions: Optional[BaseExcludeItem]
    global_exclusions: Optional[BaseExcludeItem]
    use_prototype_docker_pip_install: bool
    should_remove_runtime_provided_packages: bool


class ConfigClient:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def load_render_config_file(self, filepath: str, target_os: str, overriding_attributes: Optional[dict] = None) -> Config:
        if not os.path.exists(filepath):
            raise Exception(f"Config file not found at : {filepath}")

        with open(filepath) as config_file:
            config_data = yaml.safe_load(config_file) or dict()
            try:
                config = SourceConfig(**{**config_data, **(overriding_attributes or {})})
                return ConfigClient._render_config(source_config=config, config_filepath=filepath, target_os=target_os)
            except ValidationError as e:
                raise Exception(f"Error in the config file : {e}")

    @staticmethod
    def combine_nullable_list(one: Optional[list], two: Optional[list]) -> Optional[list]:
        return [*one, *two] if one is not None and two is not None else one if one is not None else two if two is not None else None

    @staticmethod
    def _render_config(source_config: SourceConfig, config_filepath: str, target_os: str) -> Config:
        config_location_dirpath: str = os.path.dirname(os.path.abspath(config_filepath))
        # We need to abspath the config filepath before trying to get its dirname, because if the filepath is relative
        # path without parent dir (ie, serverlesspack.config.yaml instead of something like app/serverlesspack.config.yaml)
        # an immediate call to os.path.dirname would return None, which we do not want.
        rendered_absolute_root_filepath: str = os.path.abspath(os.path.join(config_location_dirpath, source_config.root_file))
        if not os.path.isfile(rendered_absolute_root_filepath):
            raise Exception(f"No file found at {rendered_absolute_root_filepath}")
        if not os.path.isfile(rendered_absolute_root_filepath):
            raise Exception(f"No file found at {rendered_absolute_root_filepath}")

        if source_config.package_type is None:
            import click
            source_config.package_type = click.prompt(text="Export type", type=click.Choice(['code', 'layer']))
        if source_config.output_type is None:
            import click
            source_config.output_type = click.prompt(text="Format type", type=click.Choice(['zip', 'folder']))
        if source_config.python_version is None:
            from .cli import PythonVersion
            source_config.python_version = click.prompt(
                text="For which Python version do you want to create the layer ?",
                type=click.Choice([e.value for e in PythonVersion]),
            )

        config = Config(
            root_filepath=rendered_absolute_root_filepath,
            project_root_dir=source_config.project_root_dir,
            package_type=source_config.package_type,
            output_type=source_config.output_type,
            python_version=source_config.python_version,
            filepaths_includes=set(),
            folders_includes={},
            python_path_exclusions=source_config.python_path_exclusions,
            global_exclusions=source_config.global_exclusions,
            use_prototype_docker_pip_install=source_config.use_prototype_docker_pip_install,
            should_remove_runtime_provided_packages=source_config.should_remove_runtime_provided_packages
        )

        if source_config.filepaths_includes is not None:
            for filepath in source_config.filepaths_includes:
                absolute_filepath: str = os.path.abspath(filepath)
                config.filepaths_includes.add(absolute_filepath)

        if source_config.folders_includes is not None:
            for folderpath, folder_config in source_config.folders_includes.items():
                output_config_folder_include_item = BaseFolderIncludeItem()

                if folder_config is not None:
                    def render_folder_include_item(os_additional_folder_settings: Optional[BaseFolderIncludeItem]):
                        if os_additional_folder_settings is None:
                            output_config_folder_include_item.included_folders_names = folder_config.included_folders_names
                            output_config_folder_include_item.included_files_extensions = folder_config.included_files_extensions
                            output_config_folder_include_item.excluded_folders_names = folder_config.excluded_folders_names
                            output_config_folder_include_item.excluded_files_extensions = folder_config.excluded_files_extensions
                        else:
                            output_config_folder_include_item.included_folders_names = ConfigClient.combine_nullable_list(
                                folder_config.included_folders_names, os_additional_folder_settings.included_folders_names
                            )
                            output_config_folder_include_item.included_files_extensions = ConfigClient.combine_nullable_list(
                                folder_config.included_files_extensions, os_additional_folder_settings.included_files_extensions
                            )
                            output_config_folder_include_item.excluded_folders_names = ConfigClient.combine_nullable_list(
                                folder_config.excluded_folders_names, os_additional_folder_settings.excluded_folders_names
                            )
                            output_config_folder_include_item.excluded_files_extensions = ConfigClient.combine_nullable_list(
                                folder_config.excluded_files_extensions, os_additional_folder_settings.excluded_files_extensions
                            )

                    if target_os == 'windows':
                        render_folder_include_item(os_additional_folder_settings=folder_config.additional_windows)
                    elif target_os == 'linux':
                        render_folder_include_item(os_additional_folder_settings=folder_config.additional_linux)

                rendered_absolute_folder_path = os.path.abspath(os.path.join(os.path.dirname(config_filepath), folderpath))
                if not os.path.exists(rendered_absolute_folder_path):
                    raise Exception(f"No folder found at {rendered_absolute_folder_path}")

                config.folders_includes[rendered_absolute_folder_path] = output_config_folder_include_item
        return config


