import ast
import os
from pathlib import Path
from typing import Any, Optional, Dict, Callable, List, Tuple


def rel_module_path(common_prefix: str, module_path: str) -> Optional[str]:
    module_path_parts: List[str] = module_path.split(".")
    if not len(module_path_parts) > 0:
        return None

    common_prefix_parts: Tuple[str] = Path(common_prefix).parts
    try:
        matching_index: int = common_prefix_parts.index(module_path_parts[0])
        for i, part in enumerate(module_path_parts[1:]):
            target_index: int = (matching_index + 1) + i
            if target_index >= len(common_prefix_parts):
                return ".".join(module_path_parts[i+1:])
            if part != common_prefix_parts[target_index]:
                return None
    except ValueError as e:
        print(e)
        return None


def handle_import_from(common_prefix: str, node: Any, current_filepath: str):
    module_relative_access_path = rel_module_path(common_prefix=common_prefix, module_path=node.module)
    if module_relative_access_path is not None:
        node_names: List[str] = [name_alias.name for name_alias in node.names]
        return f"from {module_relative_access_path} import {', '.join(node_names)}"
    # resolver.add_package_by_name(package_name=f"{module}.{name_item.name}", current_filepath=current_filepath)

def handle_import(common_prefix: str, node: Any, current_filepath: str):
    for name_item in node.names:
        print(name_item)
        rel_module_path(common_prefix=common_prefix, module_path=name_item.name)
        # resolver.add_package_by_name(package_name=name_item.name, current_filepath=current_filepath)

def handle_function_def(common_prefix: str, node: Any, current_filepath: str) -> List[Any]:
    return node.body
    for child_node in node.body:
        child_node_single_name: Optional[str] = getattr(child_node, 'name', None)
        # resolver.process_node(node=child_node, current_filepath=current_filepath)

def handle_expression_container(common_prefix: str, node: Any, current_filepath: str) -> List[Any]:
    return node.body
    """child_nodes: List[Any] = node.body
    if len(child_nodes) > 0:
        last_line_num: int = child_nodes[0].lineno
        for child_node in child_nodes:
            if node.lineno > last_line_num + 1:
                lines_to_add: List[str] = file_content_lines[last_line_num:node.lineno - 1]
                processed_content_lines.extend(lines_to_add)
            
            child_node_name_value: Optional[str] = getattr(child_node, 'name', None)
            handler = mutators_node_handlers_switch.get(child_node.__class__, None)
            modified_content: Optional[str] = handler(
                common_prefix, child_node, current_filepath
            )
            print(modified_content)
        
            # resolver.process_node(node=child_node, current_module=child_node_name_value or current_module, current_filepath=current_filepath)
        """

def do_nothing(common_prefix: str, node: Any, current_filepath: str):
    pass


mutators_node_handlers_switch: Dict[Any, Callable[[str, Any, str], None]] = {
    ast.ImportFrom: handle_import_from,
    ast.Import: handle_import,
    ast.FunctionDef: handle_function_def,
    ast.ClassDef: handle_expression_container,
    ast.Try: handle_expression_container,
    ast.If: handle_expression_container,
    ast.For: handle_expression_container,
    ast.While: handle_expression_container,
    ast.With: handle_expression_container,
    ast.Delete: do_nothing,
    ast.Global: do_nothing,
    ast.Expr: do_nothing,
    ast.Continue: do_nothing,
    ast.Break: do_nothing,
    ast.Return: do_nothing,
    ast.Assign: do_nothing,
    ast.AnnAssign: do_nothing,
    ast.AugAssign: do_nothing,
    ast.Call: do_nothing,
    ast.Pass: do_nothing,
    ast.Raise: do_nothing,
    ast.Assert: do_nothing,
}
