import ast
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1] / "app"
ROUTERS_ROOT = APP_ROOT / "routers"
DB_CONTEXT_NAMES = {"AsyncSessionLocal", "_ctx_db"}
SLOW_CALL_NAMES = {
    "authorize_access_token",
    "_parse_team_text_with_copilot",
    "_parse_format_text_with_copilot",
    "generate_feedback_json_or_none",
    "send_to_user",
    "_broadcast_tournament_match_status_event",
}


def _python_files(root: Path):
    return sorted(path for path in root.rglob("*.py") if path.is_file())


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_db_context_expr(node: ast.AST) -> bool:
    if isinstance(node, ast.Call):
        return _call_name(node.func) in DB_CONTEXT_NAMES
    return _call_name(node) in DB_CONTEXT_NAMES


def _contains_slow_call(node: ast.AST) -> list[tuple[int, str]]:
    matches: list[tuple[int, str]] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = _call_name(child.func)
            if name in SLOW_CALL_NAMES:
                matches.append((child.lineno, name))
    return matches


def test_get_db_is_not_used_by_app_code_except_database_helper():
    offenders: list[str] = []
    for path in _python_files(APP_ROOT):
        if path.name == "database.py":
            continue
        text = path.read_text()
        if "get_db" in text:
            offenders.append(str(path.relative_to(APP_ROOT)))

    assert offenders == []


def test_routers_do_not_hold_db_context_around_known_slow_calls():
    offenders: list[str] = []

    for path in _python_files(ROUTERS_ROOT):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.AsyncWith):
                continue
            if not any(_is_db_context_expr(item.context_expr) for item in node.items):
                continue

            for line_no, call_name in _contains_slow_call(node):
                offenders.append(f"{path.relative_to(APP_ROOT)}:{line_no}: {call_name}")

    assert offenders == []
