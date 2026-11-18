"""Oracle for terminal-bench/circuit-fibsqrt.

Two checks, mirroring upstream's three tests:

- `gates-file` (artifact): /app/gates.txt exists and has fewer than 32,000
  lines, counted as upstream's `sum(1 for line in f)` counts them on a file
  opened in text mode (universal newlines).
- `sqrt-fib` (protocol): one case per upstream input n. The simulator,
  compiled from upstream's sim.c, must exit 0 and print fib(isqrt(n)) % 2**32.
  The expected values are in hidden/cases.json.
"""

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Ending,
    FileStatus,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

GATES_CHECK = "gates-file"
SIM_CHECK = "sqrt-fib"

# Upstream's test_gates_file_size asserts `line_count < 32000`.
LINE_LIMIT = 32000

# fib(k) % 2**32 has at most 10 decimal digits; anything longer is not a valid answer.
MAX_DIGITS = 20


def plan(resources: HiddenResources, seed: int) -> Plan:
    data = resources.read_json("cases.json")
    if not isinstance(data, dict) or not isinstance(data.get("cases"), list):
        raise ValueError("hidden/cases.json must hold a list under 'cases'")
    cases: list[Case] = []
    for entry in data["cases"]:
        if not isinstance(entry, dict) or set(entry) != {"n", "expected"}:
            raise ValueError("each case needs exactly 'n' and 'expected'")
        cases.append(Case(challenge={"n": entry["n"]}, context={"expected": entry["expected"]}))
    return Plan(artifact_contexts={GATES_CHECK: None}, cases={SIM_CHECK: tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == GATES_CHECK and isinstance(evidence, ArtifactEvidence):
        return _judge_gates(evidence)
    if check_id == SIM_CHECK and isinstance(evidence, CaseEvidence):
        return _judge_case(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def text_mode_line_count(text: str) -> int:
    """The number of lines Python yields when iterating a text-mode file.

    Text mode translates "\\r\\n" and a lone "\\r" to "\\n" and then splits
    on "\\n"; a final line without a terminator still counts.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized == "":
        return 0
    return normalized.count("\n") + (0 if normalized.endswith("\n") else 1)


def _judge_gates(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"/app/gates.txt is {found.status.value}", "detail": found.reason})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "/app/gates.txt was not parsed as text"})
    count = text_mode_line_count(found.value.text)
    if count >= LINE_LIMIT:
        return Judgment(False, {"reason": "too many lines", "lines": count, "limit": LINE_LIMIT})
    return Judgment(True, {"lines": count})


def _judge_case(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(context, dict) or not isinstance(context.get("expected"), int):
        return Judgment(False, {"reason": "bad case context"})
    expected = context["expected"]
    if evidence.facts.ending is not Ending.RETURNED or evidence.facts.exit_status != 0:
        return Judgment(False, {"reason": "adapter did not return normally", "ending": evidence.facts.ending.value})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    status = value.get("exit_status")
    lines = value.get("stdout_lines")
    if not isinstance(status, int) or isinstance(status, bool) or not isinstance(lines, list):
        return Judgment(False, {"reason": "observation fields missing"})
    if status != 0:
        return Judgment(False, {"reason": "simulator exited with non-zero status", "exit_status": status})
    if not all(isinstance(line, str) for line in lines):
        return Judgment(False, {"reason": "output lines are not strings"})
    # Upstream parses int(result.stdout.strip()); the simulator prints "%u\n".
    printed = "\n".join(lines).strip()
    if printed == "" or len(printed) > MAX_DIGITS or not all(char in "0123456789" for char in printed):
        return Judgment(False, {"reason": "output is not a decimal integer", "output": printed[:64]})
    actual = int(printed)
    if actual != expected:
        return Judgment(False, {"reason": "wrong output", "actual": actual})
    return Judgment(True, {"actual": actual})
