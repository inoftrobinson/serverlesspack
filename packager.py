import os
import subprocess
from pathlib import Path
from typing import List, Dict
import click
from tqdm import tqdm

from serverlesspack.imports_resolver import PackageItem


def package_lambda_layer(packages: Dict[str, PackageItem]):
    packages_string = " ".join(packages.keys())
    root_target_folder = "F:/Inoft/anvers_1944_project/inoft_vocal_framework/scripts/serverlesspack/dist"
    result = subprocess.run(f'pip install {packages_string} --target="{root_target_folder}/python/lib/python3.8/site-packages"')


def package_files(files: Dict[str, PackageItem], root_path: str):
    output_zip_filepath = os.path.join(root_path, f"build.zip")
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)

    if not os.path.isfile(output_zip_filepath):
        files_list: List[PackageItem] = list(files.values())

        import zipfile
        with zipfile.ZipFile(output_zip_filepath, "w") as zip_object:
            click.echo("Zipping files...")
            num_files_to_zip = len(files_list)
            for i in tqdm(range(num_files_to_zip)):
                file_data = files_list[i]
                filepath = file_data['absolute_filepath']
                archive_name = file_data['relative_filepath']
                zip_object.write(filename=filepath, arcname=archive_name)

        click.echo(f"Packaged zipped file available at {output_zip_filepath}")

