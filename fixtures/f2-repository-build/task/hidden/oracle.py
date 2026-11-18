"""Oracle for fixture F2: `lines -r` must print the challenge's lines in descending order.

The public example is one case; the others are generated from the seed, so a
candidate that hardcodes the example's output fails.
"""

from random import Random

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

WORDS = ("apple", "pear", "fig", "kiwi", "plum", "date", "lime", "yuzu", "Melon", "berry")


def plan(resources: HiddenResources, seed: int) -> Plan:
    generator = Random(seed)
    inputs: list[list[str]] = [["a", "c", "b"]]
    for size in (1, 4, 9):
        inputs.append([generator.choice(WORDS) for _ in range(size)])
    cases = tuple(
        Case({"lines": list(lines)}, {"lines": sorted(lines, reverse=True)}) for lines in inputs
    )
    return Plan(artifact_contexts={}, cases={"reverse-sort": cases})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    if observed.get("lines") != context["lines"]:
        return Judgment(False, {"expected": context["lines"], "got": observed.get("lines")})
    return Judgment(True, None)
