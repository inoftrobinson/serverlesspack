from serverlesspack.utils import message_with_vars


class OutputDirpathTooLow(Exception):
    def __init__(self, highest_found_directory: str, output_base_dirpath: str):
        self.highest_found_directory = highest_found_directory
        self.output_base_dirpath = output_base_dirpath

    def __str__(self):
        return message_with_vars(
            message="The highest found directory found in the packages file is higher than the output_base_dirpath. "
                    "Please increase the output_base_dirpath to an higher directory.",
            vars_dict={
                'highest_found_directory': self.highest_found_directory,
                'output_base_dirpath': self.output_base_dirpath
            }
        )
