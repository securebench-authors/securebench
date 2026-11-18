"""Oracle for winning-avg-corewars.

Three checks follow upstream's three tests:

- `opponents` (artifact): every file in /app/warriors still has upstream's SHA-256.
- `warrior` (artifact): /app/my_warrior.red exists.
- `performance` (protocol): one case per opponent; pmars must exit 0 and the win count,
  parsed from its last output line as upstream's test parses it, must reach the
  threshold. Expected hashes and thresholds live in hidden/*.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue


def plan(resources: HiddenResources, seed: int) -> Plan:
    opponents = resources.read_json("opponents.json")
    cases = tuple(
        Case(challenge=entry["challenge"], context={"min_wins": entry["min_wins"]})
        for entry in resources.read_json("cases.json")
    )
    return Plan(
        artifact_contexts={"opponents": opponents, "warrior": None},
        cases={"performance": cases},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "opponents" and isinstance(evidence, ArtifactEvidence):
        return judge_opponents(context, evidence)
    if check_id == "warrior" and isinstance(evidence, ArtifactEvidence):
        return judge_warrior(evidence)
    if check_id == "performance" and isinstance(evidence, CaseEvidence):
        return judge_performance(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def judge_opponents(expected: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    if not isinstance(expected, dict):
        return Judgment(False, {"reason": "bad context"})
    seen = {found.path: found for found in evidence.files}
    if set(seen) != set(expected):
        return Judgment(False, {"reason": "opponent files do not match the plan"})
    modified = []
    for path, digest in expected.items():
        found = seen[path]
        # Upstream hashes the raw bytes; any status other than present means the file
        # is missing, not a regular file, or not the original text. Evidence spells
        # digests as "sha256:<hex>", upstream as bare hex.
        if found.status is not FileStatus.PRESENT or found.sha256 != "sha256:" + str(digest):
            modified.append({"path": path, "status": found.status.value})
    if modified:
        return Judgment(False, {"reason": "opponent modified", "files": modified})
    return Judgment(True, None)


def judge_warrior(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected one file"})
    found = evidence.files[0]
    # Upstream only asks that the path exists; whether pmars can use it is the
    # performance check's question.
    if found.status is FileStatus.ABSENT:
        return Judgment(False, {"reason": "my_warrior.red not found"})
    return Judgment(True, None)


def judge_performance(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    min_wins = context.get("min_wins")
    if not isinstance(min_wins, int) or isinstance(min_wins, bool):
        return Judgment(False, {"reason": "bad context"})
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    exit_code = value.get("exit_code")
    lines = value.get("stdout_lines")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool) or not isinstance(lines, list):
        return Judgment(False, {"reason": "observation fields missing"})
    if not all(isinstance(line, str) for line in lines):
        return Judgment(False, {"reason": "stdout line is not text"})
    if exit_code != 0:
        return Judgment(False, {"reason": "pmars failed", "exit_code": exit_code})
    wins = parse_wins(lines)
    if wins is None:
        return Judgment(False, {"reason": "no win count in pmars output", "last_line": last_line(lines)[:200]})
    if wins < min_wins:
        return Judgment(False, {"reason": "win rate below threshold", "wins": wins, "min_wins": min_wins})
    return Judgment(True, {"wins": wins, "min_wins": min_wins})


def last_line(lines: list) -> str:
    # Upstream: result.stdout.strip().split("\n")[-1]. The adapter split stdout on
    # "\n", so joining the lines again restores it exactly.
    return "\n".join(lines).strip().split("\n")[-1]


def parse_wins(lines: list) -> int | None:
    # Upstream: int(last_line.split()[1]); any exception fails its test. The line is
    # bounded by the observation schema, and int() refuses more than 4300 digits.
    fields = last_line(lines).split()
    if len(fields) < 2:
        return None
    try:
        return int(fields[1])
    except ValueError:
        return None
