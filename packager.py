import os
import subprocess
from pathlib import Path
from typing import List, Dict, Set, TypedDict
import click
from tqdm import tqdm

class BaseFileItem(TypedDict):
    relative_filepath: str

class LocalFileItem(BaseFileItem):
    absolute_filepath: str

class TempFileItem(BaseFileItem):
    content: str


def package_lambda_layer(packages_names: Set[str], target_dirpath: str, python_version: str):
    packages_string = " ".join(packages_names)
    result = subprocess.run(f'pip install {packages_string} --target="{target_dirpath}/python/lib/python{python_version}/site-packages"')
    return result


def package_files(included_files_absolute_paths: Set[str], root_path: str):
    local_files_items: List[LocalFileItem] = list()
    temp_files_items: Dict[str, TempFileItem] = dict()
    common_prefix_across_all_files = os.path.commonprefix([absolute_filepath for absolute_filepath in included_files_absolute_paths])

    for absolute_filepath in tqdm(included_files_absolute_paths, desc="Preparing files and creating missing __init__ files..."):
        relative_filepath = os.path.relpath(absolute_filepath, common_prefix_across_all_files)
        local_files_items.append(LocalFileItem(absolute_filepath=absolute_filepath, relative_filepath=relative_filepath))

        folder_parts = Path(os.path.dirname(relative_filepath)).parts
        for i_part in range(len(folder_parts)):
            current_folder_part_relative_path = os.path.join(*folder_parts[0:i_part + 1])
            expected_init_file_relative_filepath = os.path.join(current_folder_part_relative_path, "__init__.py")
            expected_init_file_absolute_filepath = os.path.join(common_prefix_across_all_files, expected_init_file_relative_filepath)
            if expected_init_file_absolute_filepath not in included_files_absolute_paths and expected_init_file_absolute_filepath not in temp_files_items:
                temp_files_items[expected_init_file_relative_filepath] = TempFileItem(content="", relative_filepath=expected_init_file_relative_filepath)

    output_zip_filepath = os.path.join(root_path, f"build.zip")
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)
    build_temp_folderpath = os.path.join(root_path, "build_temp")

    if not os.path.isfile(output_zip_filepath):
        import zipfile
        with zipfile.ZipFile(output_zip_filepath, "w") as zip_object:
            for local_file_item in tqdm(local_files_items, desc="Zipping local files"):
                zip_object.write(filename=local_file_item['absolute_filepath'], arcname=local_file_item['relative_filepath'])

            for local_file_item in tqdm(temp_files_items.values(), desc="Zipping temp files"):
                # We do not use 'writestr' function of the ZipFile library, instead we write the content of temp file to temporary
                # file, which we then write to the archive, because using writestr will create file's that are in read only mode, which
                # will not be usable by AWS Lambda. And I never figured out how to write file in read and write mode with writestr.
                temporary_content_container_filepath = os.path.join(build_temp_folderpath, local_file_item['relative_filepath'])
                if not os.path.isdir(os.path.dirname(temporary_content_container_filepath)):
                    os.makedirs(os.path.dirname(temporary_content_container_filepath))

                with open(temporary_content_container_filepath, 'w+') as temp_file:
                    temp_file.write(local_file_item['content'])

                zip_object.write(filename=temporary_content_container_filepath, arcname=local_file_item['relative_filepath'])
                os.remove(temporary_content_container_filepath)

        click.secho(f"Packaged zipped file available at {output_zip_filepath}", fg='green')

