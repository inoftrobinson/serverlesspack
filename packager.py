import os
import subprocess
from pathlib import Path
from typing import List, Dict
import click
from tqdm import tqdm

from serverlesspack.imports_resolver import PackageItem


def package_lambda_layer(packages: Dict[str, PackageItem], target_dirpath: str, python_version: str):
    packages_string = " ".join(packages.keys())
    result = subprocess.run(f'pip install {packages_string} --target="{target_dirpath}/python/lib/python{python_version}/site-packages"')
    return result


def package_files(files: Dict[str, PackageItem], root_path: str):
    output_zip_filepath = os.path.join(root_path, f"build.zip")
    if os.path.isfile(output_zip_filepath):
        os.remove(output_zip_filepath)

    if not os.path.isfile(output_zip_filepath):
        files_list: List[PackageItem] = list(files.values())

        import zipfile
        with zipfile.ZipFile(output_zip_filepath, "w") as zip_object:
            num_files_to_zip = len(files_list)
            for i in tqdm(range(num_files_to_zip), desc="Zipping files"):
                file_data = files_list[i]
                filepath = file_data['absolute_filepath']
                archive_name = file_data['relative_filepath']
                zip_object.write(filename=filepath, arcname=archive_name)

        click.secho(f"Packaged zipped file available at {output_zip_filepath}", fg='green')

