"""Reports the top-level module names /app/jump_analyzer.py imports.

This is the extraction half of upstream's test_jump_analyzer_imports, run with
the same Python 3.13 and the same AST walk, after replaying the script runs of
the tests upstream runs before it (native_runs.py). Deciding which names are allowed
(the standard library plus cv2, numpy and toml) is left to the Oracle.
"""

import ast
import json
import pathlib
import sys

sys.path.insert(0, "/.securebench/evaluation")

from native_runs import place_files, replay_earlier_runs  # noqa: E402

MAX_NAMES = 4096
MAX_NAME_BYTES = 256


def _bounded(name: str) -> str:
    # Every allowed name is far shorter than the bound, so a truncated name can
    # never become an allowed one.
    return name.encode("utf-8")[:MAX_NAME_BYTES].decode("utf-8", "ignore")


def main() -> None:
    challenge = json.load(sys.stdin)
    place_files(challenge)
    replay_earlier_runs(challenge)
    analyzer_path = pathlib.Path(challenge["path"])
    if not analyzer_path.exists():
        observation = {"file": "absent"}
    else:
        try:
            # The verifier's Python runs in UTF-8 mode, so read_text() decodes UTF-8.
            source = analyzer_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except Exception as error:  # upstream's test errors out on any of these
            message = f"{type(error).__name__}: {error}"
            observation = {"file": "unparsable", "detail": message.encode("utf-8")[:512].decode("utf-8", "ignore")}
        else:
            found_imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = (alias.name or "").split(".")[0]
                        if module_name:
                            found_imports.add(module_name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split(".")[0]
                        if module_name:
                            found_imports.add(module_name)
            names = sorted(found_imports)
            # More distinct names than the bound cannot all be standard library
            # or allowed, so reporting the count lets the Oracle fail them.
            observation = {
                "file": "parsed",
                "count": len(names),
                "imports": [_bounded(name) for name in names[:MAX_NAMES]],
            }
    sys.stdout.write(json.dumps({"observation": observation}))


if __name__ == "__main__":
    main()
