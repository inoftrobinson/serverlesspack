import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple, Literal

import click
import yaml
from pydantic import ValidationError, BaseModel, Field


class BaseFolderIncludeItem(BaseModel):
    included_files_extensions: Optional[List[str]] = None
    included_folders_names: Optional[List[str]] = None
    excluded_files_extensions: Optional[List[str]] = Field(default_factory=list)
    excluded_folders_names: Optional[List[str]] = Field(default_factory=list)

class SourceConfig(BaseModel):
    root_file: str
    type: Optional[Literal['code', 'layer']] = None
    format: Optional[Literal['zip', 'folder']] = None
    class FolderIncludeItem(BaseFolderIncludeItem):
        additional_linux: Optional[BaseFolderIncludeItem] = None
        additional_windows: Optional[BaseFolderIncludeItem] = None
    folders_includes: Optional[Dict[str, Optional[FolderIncludeItem]]] = None

@dataclass
class Config:
    root_filepath: str
    type: Literal['code', 'layer']
    format: Literal['zip', 'folder']
    folders_includes: Dict[str, BaseFolderIncludeItem]


class ConfigClient:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def load_render_config_file(self, filepath: str, target_os: str) -> Config:
        if not os.path.exists(filepath):
            raise Exception(f"Config file not found at : {filepath}")

        with open(filepath) as config_file:
            config_data = yaml.safe_load(config_file) or dict()
            try:
                config = SourceConfig(**config_data)
                return ConfigClient._render_config(source_config=config, config_filepath=filepath, target_os=target_os)
            except ValidationError as e:
                raise Exception(f"Error in the config file : {e}")

    @staticmethod
    def combine_nullable_list(one: Optional[list], two: Optional[list]) -> Optional[list]:
        return [*one, *two] if one is not None and two is not None else one if one is not None else two if two is not None else None

    @staticmethod
    def _render_config(source_config: SourceConfig, config_filepath: str, target_os: str) -> Config:
        rendered_absolute_root_filepath = os.path.abspath(os.path.join(os.path.dirname(config_filepath), source_config.root_file))
        if not os.path.isfile(rendered_absolute_root_filepath):
            raise Exception(f"No file found at {rendered_absolute_root_filepath}")

        if source_config.type is None:
            source_config.type = click.prompt(text="Export type", type=click.Choice(['code', 'layer']))
        if source_config.format is None:
            source_config.format = click.prompt(text="Format type", type=click.Choice(['zip', 'folder']))

        config = Config(
            root_filepath=rendered_absolute_root_filepath,
            type=source_config.type, format=source_config.format,
            folders_includes=dict()
        )
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


