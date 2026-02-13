import ast
from pathlib import Path


def _count_function_defs(source_path: Path, function_name: str) -> int:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    return sum(
        1
        for node in tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == function_name
    )


def test_api_token_crud_functions_are_defined_once() -> None:
    source_path = Path(__file__).resolve().parents[1] / "app" / "crud.py"

    assert _count_function_defs(source_path, "create_api_token") == 1
    assert _count_function_defs(source_path, "list_api_tokens") == 1
    assert _count_function_defs(source_path, "delete_api_token") == 1
