"""Oracle for sqlite-db-truncate.

Upstream's only test, `test_json_data`, loads /app/recover.json with
`json.load`, builds the set of `(item["word"], item["value"])` tuples over
every item, intersects it with the set of its expected pairs, and asserts that
more than 6 pairs are in the intersection. This Oracle makes the same test
against the pairs and the threshold in hidden/expected.json:

- the file must be a JSON array (upstream raises on any other non-empty
  value, and finds no match in an empty one);
- every item must be an object with the keys "word" and "value", whose
  values are not arrays or objects (upstream raises KeyError, TypeError or
  "unhashable" otherwise); other keys are ignored, as upstream ignores them;
- the pairs form a Python set of tuples, and the count is the size of its
  intersection with the expected set, as in upstream's test, so each expected
  pair counts at most once and values compare with Python's `==` (the integer
  10 matches 10.0, the string "10.0" does not).

The file is bounded by the artifact check (1 MiB), so the work here is one
pass over at most that many items, with set operations on scalars.
"""

from securebench.core.errors import Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
)
from securebench.core.jsondata import JsonValue

CHECK = "recover"
PATH = "/app/recover.json"


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if _expected(expected) is None:
        raise Rejected("hidden/expected.json must hold distinct pairs and a threshold")
    return Plan(artifact_contexts={CHECK: expected}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    expected = _expected(context)
    if expected is None:
        return Judgment(False, {"reason": "malformed context"})
    soln_tuples, threshold = expected
    if len(evidence.files) != 1 or evidence.files[0].path != PATH or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{PATH} is {found.status.value}"})
    items = found.value
    if not isinstance(items, list):
        return Judgment(False, {"reason": "recover.json is not a JSON array"})
    data_tuples: set[tuple[JsonValue, JsonValue]] = set()
    for index, item in enumerate(items):
        if not isinstance(item, dict) or "word" not in item or "value" not in item:
            return Judgment(False, {"reason": "item lacks word or value", "index": index})
        word, value = item["word"], item["value"]
        if isinstance(word, list | dict) or isinstance(value, list | dict):
            return Judgment(False, {"reason": "item has a non-scalar word or value", "index": index})
        data_tuples.add((word, value))
    score = len(soln_tuples & data_tuples)
    if score < threshold:
        return Judgment(
            False, {"reason": "too few pairs recovered", "matched": score, "required": threshold}
        )
    return Judgment(True, None)


def _expected(context: JsonValue) -> tuple[set[tuple[JsonValue, JsonValue]], int] | None:
    if not isinstance(context, dict) or set(context) != {"pairs", "threshold"}:
        return None
    raw, threshold = context["pairs"], context["threshold"]
    if not isinstance(raw, list) or not raw:
        return None
    pairs: set[tuple[JsonValue, JsonValue]] = set()
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {"word", "value"}:
            return None
        word, value = entry["word"], entry["value"]
        if not isinstance(word, str) or not isinstance(value, float):
            return None
        pairs.add((word, value))
    if len(pairs) != len(raw):
        return None
    if isinstance(threshold, bool) or not isinstance(threshold, int) or not 1 <= threshold <= len(pairs):
        return None
    return pairs, threshold
