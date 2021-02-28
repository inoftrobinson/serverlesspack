"""
THE ENTIRETY OF THIS FILE WILL BE DEPRECATED
"""

import ast
import importlib
import importlib.metadata
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import List, TypedDict, Dict, Optional
import re
import pkg_resources


class RequirementModuleItem(TypedDict):
    module_name: str
    version: str
    version_selector: str

class PackagesLockClient:
    def __init__(self):
        self.requirements_modules: Dict[str, RequirementModuleItem] = dict()

    def find_requirements(self):
        pass

    def get_root_module_name(self, module_filepath):
        module_filepath_path = Path(module_filepath)
        parents_parts: Optional[List[str]] = getattr(module_filepath_path.parents, '_parts', None)
        if parents_parts is not None:
            for i, parent in enumerate(parents_parts):
                if parent == "site-packages":
                    return parents_parts[i + 1] if len(parents_parts) - 1 > i + 1 else None
        return None

    def open_requirements(self):
        with Path('F:/Inoft/anvers_1944_project/inoft_vocal_engine/requirements.txt').open() as requirements_txt:
            crude_requirements: List[str] = [str(requirement) for requirement in pkg_resources.parse_requirements(requirements_txt)]
            print(crude_requirements)
            for requirement in crude_requirements:
                requirement_matches = re.match(r'(.*)(~=|==)(.*)', requirement)
                module_name = requirement_matches[1]
                version_selector = requirement_matches[2]
                package_version = requirement_matches[3]

                if module_name not in self.requirements_modules:
                    self.requirements_modules[module_name] = RequirementModuleItem(
                        module_name=module_name, version=package_version, version_selector=version_selector
                    )
        print(self.requirements_modules)

    def _import_module(self, module_name: str) -> Optional[ModuleType]:
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError as e:
            try:
                return importlib.import_module(module_name.lower())
            except ModuleNotFoundError as e:
                return None

    def resolve(self):
        for module_data in self.requirements_modules.values():
            # result = subprocess.run(f"{sys.executable} pip show {module_data['module_name']}")
            module_infos_bytes = subprocess.check_output([sys.executable, '-m', 'pip', 'show', module_data["module_name"]])
            module_infos_str = module_infos_bytes.decode()

            if module_data['module_name'] == "PyYAML":
                print("e")

            distribution = importlib.metadata.distribution(distribution_name=module_data['module_name'])

            location_matches = re.findall(r'(Location: )(.*)', module_infos_str)
            if len(location_matches) > 0:
                module_root_location = location_matches[0][1].replace("\r", "").replace("\n", "")
                module_location = os.path.join(module_root_location, module_data['module_name'])

            imported_module = self._import_module(module_data['module_name'])
            for item in imported_module.__dict__:
                if isinstance(item, ast.Module):
                    print(item)
                    # self.requirements_modules[item]
            print(imported_module)

    def save_to_file(self):
        pass


if __name__ == '__main__':
    client = PackagesLockClient()
    client.open_requirements()
    client.resolve()
