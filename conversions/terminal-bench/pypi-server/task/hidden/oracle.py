"""Oracle for pypi-server.

Upstream's one test, test_api, runs
`python -m pip install --index-url http://localhost:8080/simple vectorops==0.1.0`
and `python -m pip show vectorops` (both check=True), imports vectorops and
asserts four dot products. The four calls and their expected values are in
hidden/cases.json, copied from the test. The single case makes those calls in
upstream's order and requires what upstream's test requires: pip install exit
0, pip show exit 0, a working import, and for each call a returned number
equal to the expected value, with no exception.
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

CHECK = "install-and-call"


def _number(value: JsonValue) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or not isinstance(data.get("pairs"), list):
        raise ValueError("hidden/cases.json has no list of pairs")
    challenge: list[JsonValue] = []
    expected: list[JsonValue] = []
    for pair in data["pairs"]:
        if not isinstance(pair, dict) or set(pair) != {"a", "b", "expected"}:
            raise ValueError("hidden/cases.json: a pair needs exactly a, b and expected")
        a, b, want = pair["a"], pair["b"], pair["expected"]
        if not isinstance(a, list) or not isinstance(b, list) or not all(map(_number, (*a, *b))):
            raise ValueError("hidden/cases.json: a and b must be lists of numbers")
        if not _number(want):
            raise ValueError("hidden/cases.json: expected must be a number")
        challenge.append({"a": a, "b": b})
        expected.append(want)
    case = Case({"pairs": challenge}, {"expected": expected})
    return Plan(artifact_contexts={}, cases={CHECK: (case,)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    expected = context["expected"]
    if not isinstance(expected, list):
        return Judgment(False, {"reason": "malformed context"})
    failure = _setup(observation)
    if failure is not None:
        return Judgment(False, failure)
    results = observation["results"]
    if not isinstance(results, list) or len(results) != len(expected):
        return Judgment(
            False, {"reason": "not one result per call", "runner": observation["runner"]}
        )
    for index, (want, result) in enumerate(zip(expected, results, strict=True)):
        if not isinstance(result, dict):
            return Judgment(False, {"reason": "malformed result", "call": index})
        if result["raised"] != "":
            return Judgment(
                False, {"reason": "dotproduct raised", "call": index, "raised": result["raised"]}
            )
        # The runner reports the exact value of what dotproduct returned, or
        # numeric false when no int or float holds it; upstream's `==` with
        # an int or float expected value fails for the latter.
        if result["numeric"] is not True:
            return Judgment(
                False,
                {
                    "reason": "dotproduct did not return a number",
                    "call": index,
                    "type": result["type"],
                },
            )
        if result["value"] != want:
            return Judgment(
                False,
                {"call": index, "expected": want, "got": result["value"], "type": result["type"]},
            )
    return Judgment(True, None)


def _setup(observation: dict[str, JsonValue]) -> dict[str, JsonValue] | None:
    """Why the package was not installed and imported as upstream requires, or None."""
    distributions = observation["distributions"]
    served = len(distributions) if isinstance(distributions, list) else 0
    if observation["install_exit"] != 0:
        return {
            "reason": "pip install failed",
            "exit": observation["install_exit"],
            "distributions_served": served,
            "output": observation["install_output"],
        }
    if observation["show_exit"] != 0:
        return {"reason": "pip show failed", "exit": observation["show_exit"]}
    if observation["imported"] is not True or observation["import_error"] != "":
        return {"reason": "import vectorops failed", "error": observation["import_error"]}
    if observation["runner"] != "complete":
        return {"reason": "the calls did not complete", "runner": observation["runner"]}
    return None
