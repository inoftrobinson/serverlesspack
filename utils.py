import os


def get_serverless_pack_root_folder() -> str:
    return os.path.dirname(os.path.abspath(__file__))

def message_with_vars(message: str, vars_dict: dict):
    output_message = message
    for key, var in vars_dict.items():
        output_message += f"\n  --{key}:{var}"
    return output_message
