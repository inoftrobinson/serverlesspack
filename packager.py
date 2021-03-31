import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
import click
from tqdm import tqdm


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
    return subprocess.run(f'pip install {packages_string} --target="{target_dirpath}"')

def package_lambda_layer(packages_names: Set[str] or List[str], target_dirpath: str, python_version: str):
    python_layer_packages_dirpath = make_absolute_python_layer_packages_dirpath(base_target_dirpath=target_dirpath, python_version=python_version)
    return install_packages_to_dir(packages_names=packages_names, target_dirpath=python_layer_packages_dirpath)


def package_files(included_files_absolute_paths: Set[str], archive_prefix: Optional[str] = None) -> Tuple[List[LocalFileItem], List[ContentFileItem]]:
    local_files_items: List[LocalFileItem] = list()
    content_files_items: Dict[str, ContentFileItem] = dict()
    common_prefix_across_all_files = os.path.commonprefix([absolute_filepath for absolute_filepath in included_files_absolute_paths])
    factory = FileItemsFactory(archive_prefix=archive_prefix)

    for absolute_filepath in tqdm(included_files_absolute_paths, desc="Preparing files and creating missing __init__ files..."):
        relative_filepath = os.path.relpath(absolute_filepath, common_prefix_across_all_files)
        local_files_items.append(factory.make_local_file_item(absolute_filepath=absolute_filepath, relative_filepath=relative_filepath))

        folder_parts = Path(os.path.dirname(relative_filepath)).parts
        for i_part in range(len(folder_parts)):
            current_folder_part_relative_path = os.path.join(*folder_parts[0:i_part + 1])
            expected_init_file_relative_filepath = os.path.join(current_folder_part_relative_path, "__init__.py")
            expected_init_file_absolute_filepath = os.path.join(common_prefix_across_all_files, expected_init_file_relative_filepath)
            if expected_init_file_absolute_filepath not in included_files_absolute_paths and expected_init_file_absolute_filepath not in content_files_items:
                content_files_items[expected_init_file_relative_filepath] = factory.make_content_file_item(
                    content="", relative_filepath=expected_init_file_relative_filepath
                )

    return local_files_items, list(content_files_items.values())

class ZipperFolderWriterClient:
    def __init__(self, root_path: str, is_zip: bool = True):
        self.root_path = root_path
        self.is_zip = is_zip
        self.build_temp_folderpath = os.path.join(self.root_path, "build_temp")
        self.container_filepath = os.path.join(self.root_path, 'build.zip')
        self.zip_object: Optional[zipfile.ZipFile] = None

    def __enter__(self):
        if self.is_zip is True:
            self.zip_object = zipfile.ZipFile(self.container_filepath, 'w')
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.zip_object is not None:
            self.zip_object.close()

    def write_local_file_item(self, local_file_item: LocalFileItem):
        if self.zip_object is None:
            absolute_target_filepath = os.path.join(self.root_path, local_file_item.relative_filepath)
            if not os.path.exists(absolute_target_filepath):
                os.makedirs(absolute_target_filepath)
            shutil.copy(src=local_file_item.absolute_filepath, dst=absolute_target_filepath)
        else:
            self.zip_object.write(filename=local_file_item.absolute_filepath, arcname=local_file_item.relative_filepath)

    def write_content_file_item(self, content_file_item: ContentFileItem):
        if self.zip_object is None:
            absolute_target_filepath = os.path.join(self.root_path, content_file_item.relative_filepath)
            with open(absolute_target_filepath, "w+") as file:
                file.write(content_file_item.content)
        else:
            temporary_content_container_filepath = os.path.join(self.build_temp_folderpath, content_file_item.relative_filepath)
            if not os.path.isdir(os.path.dirname(temporary_content_container_filepath)):
                os.makedirs(os.path.dirname(temporary_content_container_filepath))

            with open(temporary_content_container_filepath, 'w+') as temp_file:
                temp_file.write(content_file_item.content)

            self.zip_object.write(filename=temporary_content_container_filepath, arcname=content_file_item.relative_filepath)
            os.remove(temporary_content_container_filepath)
            # We do not use 'writestr' function of the ZipFile library, instead we write the content of temp file to temporary
            # file, which we then write to the archive, because using writestr will create file's that are in read only mode, which
            # will not be usable by AWS Lambda. And I never figured out how to write file in read and write mode with writestr.


def __files_to_zip(root_path: str, local_files_items: List[LocalFileItem], content_files_items: List[ContentFileItem]):
    output_zip_filepath = os.path.join(root_path, f"build.zip")
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)

    if not os.path.isfile(output_zip_filepath):
        import zipfile
        with ZipperFolderWriterClient(root_path, is_zip=False) as zipper_client:
            for local_file_item in tqdm(local_files_items, desc="Zipping local files"):
                zipper_client.write_local_file_item(local_file_item)
            for content_file_item in tqdm(content_files_items, desc="Zipping content files"):
                zipper_client.write_content_file_item(content_file_item)
        click.secho(f"Packaged zipped file available at {output_zip_filepath}", fg='green')


def files_to_zip(root_path: str, local_files_items: List[LocalFileItem], content_files_items: List[ContentFileItem]):
    output_zip_filepath = os.path.join(root_path, f"build.zip")
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)

    container_filepath = os.path.join(root_path, 'build.zip')
    build_temp_folderpath = os.path.join(root_path, "build_temp")

    import zipfile
    with zipfile.ZipFile(container_filepath, 'w') as zip_object:
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

    click.secho(f"Packaged zipped file available at {output_zip_filepath}", fg='green')

def files_to_folder(root_path: str, local_files_items: List[LocalFileItem], content_files_items: List[ContentFileItem]):
    for local_file_item in tqdm(local_files_items, desc="Zipping local files"):
        absolute_target_filepath = os.path.join(root_path, local_file_item.relative_filepath)
        if not os.path.exists(absolute_target_filepath):
            os.makedirs(absolute_target_filepath)
        shutil.copy(src=local_file_item.absolute_filepath, dst=absolute_target_filepath)

    for content_file_item in tqdm(content_files_items, desc="Zipping content files"):
        absolute_target_filepath = os.path.join(root_path, content_file_item.relative_filepath)
        with open(absolute_target_filepath, "w+") as file:
            file.write(content_file_item.content)
