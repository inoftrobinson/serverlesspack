import ast
from typing import Any, Optional, Dict, Callable

from serverlesspack.imports_resolver import Resolver


def handle_import_from(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    module = node.module or current_module
    resolver.add_package_by_name(package_name=module, current_filepath=current_filepath)
    for name_item in node.names:
        resolver.add_package_by_name(package_name=f"{module}.{name_item.name}", current_filepath=current_filepath)

def handle_import(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    for name_item in node.names:
        resolver.add_package_by_name(package_name=name_item.name, current_filepath=current_filepath)
        
def handle_function_def(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    for child_node in node.body:
        child_node_single_name: Optional[str] = getattr(child_node, 'name', None)
        resolver.process_node(node=child_node, current_module=child_node_single_name or current_module, current_filepath=current_filepath)

        child_node_names: Optional[list] = getattr(child_node, 'names', None)
        if child_node_names is not None:
            for child_node_name_item in child_node_names:
                child_node_name_item_value: Optional[str] = getattr(child_node_name_item, 'name', None)
                resolver.process_node(node=child_node, current_module=child_node_name_item_value or current_module, current_filepath=current_filepath)
                
def handle_class_def(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    for child_node in node.body:
        child_node_name_value: Optional[str] = getattr(child_node, 'name', None)
        resolver.process_node(node=child_node, current_module=child_node_name_value or current_module, current_filepath=current_filepath)
        
def handle_if(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    for child_node in node.body:
        child_node_single_name: Optional[str] = getattr(child_node, 'name', None)
        resolver.process_node(node=child_node, current_module=child_node_single_name or current_module, current_filepath=current_filepath)

def do_nothing(resolver: Resolver, node: Any, current_module: str, current_filepath: str):
    pass


# The handlers_switch contains both the type of operation we have specific handlers, and the types of operation that
# we support, but where we know for a fact that no import statements could exist in those operations. This is safer
# than returning the do_nothing for every operation that does not has a specific handler, because this allow us to
# give warnings and quickly spot operations we did not support, and for which we might need to add an handler.
process_node_handlers_switch: Dict[Any, Callable[[Resolver, Any, str, str], None]] = {
    ast.ImportFrom: handle_import_from,
    ast.Import: handle_import,
    ast.FunctionDef: handle_function_def,
    ast.ClassDef: handle_class_def,
    ast.If: handle_if,
    ast.Return: do_nothing,
    ast.Assign: do_nothing,
    ast.AnnAssign: do_nothing,
    ast.Call: do_nothing,
    ast.Pass: do_nothing,
    ast.For: do_nothing,
    ast.Raise: do_nothing,
}
