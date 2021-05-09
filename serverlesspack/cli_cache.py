import os
import json
from .utils import get_serverless_pack_root_folder


class CliCache:
    _cache = None

    @staticmethod
    def get_cli_cache_filepath() -> str:
        filepath = os.path.join(get_serverless_pack_root_folder(), "cli_cache.json")
        if not os.path.isfile(filepath):
            with open(filepath, "w+") as cache_file:
                cache_file.write(json.dumps({}))
        return filepath

    @staticmethod
    def cache() -> dict:
        if CliCache._cache is None:
            CliCache.load_cache()
        return CliCache._cache

    @staticmethod
    def load_cache():
        expected_cli_cache_filepath = CliCache.get_cli_cache_filepath()
        if os.path.exists(expected_cli_cache_filepath):
            with open(expected_cli_cache_filepath) as cache_file:
                CliCache._cache = json.load(cache_file) or dict()

    @staticmethod
    def save_cache():
        with open(CliCache.get_cli_cache_filepath(), "w+") as cache_file:
            cache_file.write(json.dumps(CliCache.cache()))
