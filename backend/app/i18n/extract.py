"""Collect every Russian text the server can show a user, as templates.

String constants become templates as is; f-strings become templates with positional placeholders:
    f"Улей №{number} уже есть на пасеке «{name}»"  →  "Улей №{0} уже есть на пасеке «{1}»"
Docstrings, demo data (seed) and developer tools are skipped. Used by the coverage test and to refresh
the catalog:  python -m app.i18n.extract  (prints templates missing from tg.json).
"""
import ast
import json
import re
from pathlib import Path

APP = Path(__file__).resolve().parent.parent
CYR = re.compile(r"[А-Яа-яЁё]")
SKIP_FILES = {"utils/seed.py", "utils/dev_init_data.py", "utils/check_setup.py", "i18n/extract.py", "i18n/__init__.py"}


def _docstring_nodes(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                ids.add(id(first.value))
    return ids


def _fstring_template(node: ast.JoinedStr) -> str:
    out, n = [], 0
    for part in node.values:
        if isinstance(part, ast.Constant):
            out.append(str(part.value))
        else:
            out.append("{%d}" % n)
            n += 1
    return "".join(out)


def templates_in(source: str) -> set[str]:
    tree = ast.parse(source)
    docs = _docstring_nodes(tree)
    inner = set()  # constants that are parts of f-strings
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                inner.add(id(part))
            t = _fstring_template(node)
            if CYR.search(t):
                found.add(t)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and CYR.search(node.value):
            if id(node) in docs or id(node) in inner or "А-Я" in node.value:  # docstrings, f-string parts, regex
                continue
            found.add(node.value)
    return found


def all_templates() -> set[str]:
    found: set[str] = set()
    for path in sorted(APP.rglob("*.py")):
        rel = path.relative_to(APP).as_posix()
        if rel in SKIP_FILES:
            continue
        found |= templates_in(path.read_text(encoding="utf-8"))
    return found


if __name__ == "__main__":
    catalog = json.loads((Path(__file__).parent / "tg.json").read_text(encoding="utf-8")) if (Path(__file__).parent / "tg.json").exists() else {}
    missing = sorted(t for t in all_templates() if t not in catalog)
    print(json.dumps(missing, ensure_ascii=False, indent=1))
