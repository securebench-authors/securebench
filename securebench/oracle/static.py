"""Static checks on Oracle code (architecture Section 7.5).

The Oracle contract (deterministic, free of side effects, never interpreting
evidence as code, paths or commands, no regular expressions) is enforced by
review, by these checks at pack validation, and again at run time by the
worker's import guard.
"""

import ast

from securebench.core.errors import Rejected

ALLOWED_MODULES: frozenset[str] = frozenset(
    {
        "__future__",
        "abc",
        "base64",
        "binascii",
        "bisect",
        "cmath",
        "collections",
        "collections.abc",
        "copy",
        "dataclasses",
        "decimal",
        "enum",
        "fractions",
        "functools",
        "hashlib",
        "heapq",
        "itertools",
        "math",
        "operator",
        "statistics",
        "string",
        "struct",
        "typing",
        "unicodedata",
        "zlib",
        "securebench.core.errors",
        "securebench.core.evidence",
        "securebench.core.jsondata",
    }
)
"""Pure standard-library modules, plus the framework types an Oracle needs. `random`
is admitted only as `from random import Random`, so randomness is always seeded."""

FORBIDDEN_NAMES: frozenset[str] = frozenset(
    {
        "__import__",
        "breakpoint",
        "compile",
        "delattr",
        "eval",
        "exec",
        "exit",
        "getattr",
        "globals",
        "help",
        "id",
        "input",
        "locals",
        "open",
        "quit",
        "setattr",
        "vars",
    }
)

MAX_SOURCE_BYTES = 1 << 20


def check_oracle_source(source: str, filename: str) -> None:
    """Raise `Rejected` with the first violation of the Oracle rules in `source`."""
    if len(source.encode("utf-8")) > MAX_SOURCE_BYTES:
        raise Rejected(f"{filename} is larger than {MAX_SOURCE_BYTES} bytes")
    try:
        tree = ast.parse(source, filename)
    except SyntaxError as error:
        raise Rejected(f"{filename}:{error.lineno}: {error.msg}") from None
    functions = {
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in ("plan", "judge")
    }
    if functions != {"plan", "judge"}:
        raise Rejected(f"{filename} must define top-level functions plan and judge")
    for node in ast.walk(tree):
        _check_node(node, filename)


def _check_node(node: ast.AST, filename: str) -> None:
    line = getattr(node, "lineno", 0)
    where = f"{filename}:{line}"
    if isinstance(node, ast.Import):
        for alias in node.names:
            if alias.name not in ALLOWED_MODULES:
                raise Rejected(f"{where}: import of {alias.name} is not allowed in an Oracle")
    elif isinstance(node, ast.ImportFrom):
        module = node.module or ""
        names = [alias.name for alias in node.names]
        if node.level != 0:
            raise Rejected(f"{where}: relative imports are not allowed in an Oracle")
        if module == "random":
            if names != ["Random"]:
                raise Rejected(f"{where}: only 'from random import Random' is allowed")
        elif module not in ALLOWED_MODULES or "*" in names:
            raise Rejected(f"{where}: import from {module} is not allowed in an Oracle")
    elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
        raise Rejected(f"{where}: {node.id} is not allowed in an Oracle")
    elif isinstance(node, ast.Name) and node.id.startswith("__") and node.id != "__name__":
        raise Rejected(f"{where}: {node.id} is not allowed in an Oracle")
    elif isinstance(node, ast.Attribute) and node.attr.startswith("__"):
        raise Rejected(f"{where}: access to {node.attr} is not allowed in an Oracle")
    elif isinstance(node, ast.Global | ast.Nonlocal):
        raise Rejected(f"{where}: global and nonlocal state is not allowed in an Oracle")
