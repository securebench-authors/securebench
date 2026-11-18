"""Oracle for merge-diff-arc-agi-task.

Two protocol checks, one case each, as upstream runs its tests in one pytest
session:

- "repository": upstream's test_git_repo_init and test_both_bundles_fetched.
  /app/repo/.git exists, `git branch -a` succeeds, and its output contains
  each required substring (upstream's `"branch1" in branches` test).
- "algo": upstream's test_algo_py_exists, test_algo_py_has_map_function and
  test_algo_map_function_with_test_input. The adapter reports why it could not
  call map through `unable`; here every output must be a list of the expected
  length whose rows are lists of the expected length with cells equal (==) to
  the expected ones.
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


def plan(resources: HiddenResources, seed: int) -> Plan:
    repository = resources.read_json("repository.json")
    examples = resources.read_json("test.json")
    if not isinstance(repository, dict) or not isinstance(examples, list):
        raise ValueError("malformed hidden data")
    algo_case = Case(
        challenge={"inputs": [example["input"] for example in examples]},
        context={"outputs": [example["output"] for example in examples]},
    )
    repository_case = Case(challenge={}, context=repository)
    return Plan(
        artifact_contexts={},
        cases={"repository": (repository_case,), "algo": (algo_case,)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or evidence.check_id != check_id:
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed observation"})
    if check_id == "repository":
        return judge_repository(context, observation)
    if check_id == "algo":
        return judge_algo(context, observation)
    return Judgment(False, {"reason": "unknown check"})


def judge_repository(context: dict, observation: dict) -> Judgment:
    exists = observation.get("git_path_exists")
    status = observation.get("branch_exit_status")
    lines = observation.get("branch_output_lines")
    required = context.get("required_substrings")
    if exists is not True:
        return Judgment(False, {"reason": "/app/repo/.git does not exist"})
    if isinstance(status, bool) or status != 0:
        return Judgment(False, {"reason": "git branch -a failed", "exit_status": status})
    if not isinstance(lines, list) or not all(isinstance(line, str) for line in lines):
        return Judgment(False, {"reason": "malformed branch output"})
    if not isinstance(required, list):
        return Judgment(False, {"reason": "malformed context"})
    output = "\n".join(lines)
    missing = [name for name in required if not isinstance(name, str) or name not in output]
    if missing:
        return Judgment(False, {"reason": "branches not found in git branch -a", "missing": missing})
    return Judgment(True, None)


def is_number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def judge_algo(context: dict, observation: dict) -> Judgment:
    expected_outputs = context.get("outputs")
    outputs = observation.get("outputs")
    if not isinstance(expected_outputs, list) or not isinstance(outputs, list):
        return Judgment(False, {"reason": "malformed observation"})
    if len(outputs) != len(expected_outputs):
        return Judgment(False, {"reason": "wrong number of outputs", "count": len(outputs)})
    for index, (output, expected) in enumerate(zip(outputs, expected_outputs)):
        failure = compare_grid(output, expected)
        if failure is not None:
            return Judgment(False, {"example": index, **failure})
    return Judgment(True, None)


def compare_grid(output: JsonValue, expected: JsonValue) -> dict | None:
    # The recorded rows and cells must number exactly what `length` claims, so
    # a reported length cannot stand in for values that were never recorded.
    if not isinstance(output, dict) or not isinstance(expected, list):
        return {"reason": "malformed output"}
    rows = output.get("rows")
    length = output.get("length")
    if output.get("is_list") is not True:
        return {"reason": "map did not return a list"}
    if not isinstance(rows, list) or isinstance(length, bool) or length != len(expected) or len(rows) != length:
        return {"reason": "wrong number of rows", "length": length}
    for row_index, (row, expected_row) in enumerate(zip(rows, expected)):
        if not isinstance(row, dict) or not isinstance(expected_row, list):
            return {"reason": "malformed row", "row": row_index}
        cells = row.get("cells")
        row_length = row.get("length")
        if row.get("is_list") is not True:
            return {"reason": "row is not a list", "row": row_index}
        if (
            not isinstance(cells, list)
            or isinstance(row_length, bool)
            or row_length != len(expected_row)
            or len(cells) != row_length
        ):
            return {"reason": "wrong row length", "row": row_index, "length": row_length}
        for column, (actual, wanted) in enumerate(zip(cells, expected_row)):
            if not is_number(actual) or actual != wanted:
                return {"reason": "wrong value", "position": [row_index, column], "got": actual}
    return None
