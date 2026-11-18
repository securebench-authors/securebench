"""Oracle for extract-moves-from-video.

Upstream's tests/test_outputs.py reads /app/solution.txt with Python's open()
and passes when its Levenshtein similarity to the expected transcript is at
least 90 percent. The adapter reads the file the same way and reports the
string; this Oracle repeats upstream's computation on it.
The expected transcript is hidden/solution.txt, copied byte for byte from the
SOLUTION literal in the upstream test.
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

# Upstream's acceptance threshold, in percent, compared with >=.
THRESHOLD = 90.0


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read("solution.txt").decode("utf-8", "strict")
    return Plan(artifact_contexts={}, cases={"solution": (Case(challenge={}, context=expected),)})


def levenshtein_distance(s1: str, s2: str) -> int:
    # Upstream's function, unchanged apart from the recursion becoming a swap.
    if len(s1) < len(s2):
        s1, s2 = s2, s1
    if len(s2) == 0:
        return len(s1)
    previous_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def similarity(distance: int, max_length: int) -> float:
    # The same floating-point expression as upstream, so ties at the threshold
    # round the same way.
    if max_length == 0:
        return 100.0
    return 100.0 * (1 - distance / max_length)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "solution" or isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, str):
        return Judgment(False, {"reason": "unexpected plan"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter did not report the file"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or set(observation) != {"text"}:
        return Judgment(False, {"reason": "unexpected observation"})
    actual = observation["text"]
    if not isinstance(actual, str):
        return Judgment(False, {"reason": "unexpected observation"})
    max_length = max(len(actual), len(context))
    # The distance is never less than the length difference, and the similarity
    # only falls as the distance grows, so when even that lower bound fails the
    # file fails natively too. This keeps the quadratic loop to files whose
    # length is within about ten percent of the expected one.
    best_possible = similarity(abs(len(actual) - len(context)), max_length)
    if best_possible < THRESHOLD:
        return Judgment(
            False,
            {
                "reason": "length alone puts the similarity below the threshold",
                "characters": len(actual),
                "best_possible_similarity": best_possible,
            },
        )
    distance = levenshtein_distance(actual, context)
    score = similarity(distance, max_length)
    diagnostic = {"characters": len(actual), "distance": distance, "similarity": score}
    if score >= THRESHOLD:
        return Judgment(True, diagnostic)
    return Judgment(False, {"reason": "similarity below the threshold", **diagnostic})
