import ast
from pathlib import Path
from typing import List, Optional, Any

from serverlesspack.mutators_node_handlers import mutators_node_handlers_switch
from serverlesspack.utils import message_with_vars


class FileMutator:
    def __init__(self, common_prefix: str, filepath: str):
        self.common_prefix = common_prefix
        self.filepath = filepath
        self.path_filepath = Path(self.filepath)

        if self.path_filepath.suffix == '.py':
            with open(self.filepath, 'r') as file:
                self.file_content = file.read()
                self.file_content_lines: List[str] = self.file_content.splitlines()
                self.processed_content_lines: List[str] = []

    def handle_expression_container(self, node: Any):
        child_nodes: List[Any] = node.body
        if len(child_nodes) > 0:
            last_line_num: int = child_nodes[0].lineno
            for child_node in child_nodes:
                if node.lineno > last_line_num + 1:
                    lines_to_add: List[str] = self.file_content_lines[last_line_num:node.lineno - 1]
                    self.processed_content_lines.extend(lines_to_add)

                child_node_name_value: Optional[str] = getattr(child_node, 'name', None)
                handler = mutators_node_handlers_switch.get(child_node.__class__, None)
                modified_content: Optional[str] = handler(
                    common_prefix, child_node, current_filepath
                )
                print(modified_content)


        last_line_num: int = 0
        if node.lineno > last_line_num + 1:
            lines_to_add: List[str] = self.file_content_lines[last_line_num:node.lineno - 1]
            self.processed_content_lines.extend(lines_to_add)
            # last_line_num =
        last_line_num: int = node.end_lineno

    def mutate_source(self):
        self.mutate(expression_content=self.file_content)

    def _mutate_node(self, node: Any):
        last_line_num: int = 0
        if node.lineno > last_line_num + 1:
            lines_to_add: List[str] = self.file_content_lines[last_line_num:node.lineno - 1]
            self.processed_content_lines.extend(lines_to_add)
            # last_line_num =
        last_line_num: int = node.end_lineno

        handler = mutators_node_handlers_switch.get(node.__class__, None)
        modified_content: Optional[str] = handler(
            self.common_prefix, node, self.filepath
        )
        if modified_content is None:
            self.processed_content_lines.extend(
                self.file_content_lines[node.lineno - 1:node.end_lineno - 1]
            )
        else:
            self.processed_content_lines.append(modified_content)

    def mutate(self, expression_content: str) -> Optional[str]:
        try:
            for root_node in ast.iter_child_nodes(ast.parse(expression_content)):
                self._mutate_node(node=root_node)
        except SyntaxError as e:
            print(message_with_vars(
                message="Python file contained a syntax error. The file has been packaged but not fully processed.",
                vars_dict={'filepath': self.filepath, 'exception': e}
            ))
            return None

    def render(self):
        return "\n".join(self.processed_content_lines)
