"""Oracle for log-summary-date-ranges.

Upstream's test reads /app/summary.csv with `csv.reader` and requires the list
of rows to be the header followed by the 15 expected rows, in order. The adapter
reports the rows `csv.reader` returned; this Oracle compares them with
hidden/expected.json in the order upstream's assertions run.
"""

from securebench.core.evidence import ArtifactEvidence, Case, CaseEvidence, HiddenResources, Judgment, Observed, Plan
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    return Plan(artifact_contexts={}, cases={"summary": (Case({}, expected),)})


def _is_rows(value: JsonValue) -> bool:
    return isinstance(value, list) and all(
        isinstance(row, list) and all(isinstance(field, str) for field in row) for row in value
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != "summary" or not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected check or evidence"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "the adapter did not report rows"})
    observation = evidence.outcome.value
    if not isinstance(observation, dict) or not _is_rows(observation.get("rows")):
        return Judgment(False, {"reason": "malformed observation"})
    rows = observation["rows"]
    expected = context["rows"]
    if not rows:
        return Judgment(False, {"reason": "the CSV file is empty"})
    if rows[0] != expected[0]:
        return Judgment(False, {"reason": "unexpected header"})
    if len(rows) != len(expected):
        return Judgment(False, {"reason": f"expected {len(expected) - 1} data rows, got {len(rows) - 1}"})
    for index, (want, got) in enumerate(zip(expected, rows)):
        if got != want:
            return Judgment(False, {"reason": f"row {index} differs (row 0 is the header)"})
    return Judgment(True, None)
