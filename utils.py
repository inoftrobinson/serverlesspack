import os


def get_serverless_pack_root_folder() -> str:
    return os.path.dirname(os.path.abspath(__file__))
