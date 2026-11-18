"""Oracle for schemelike-metacircular-eval.

Upstream runs every program of tests/test and tests/shadow_test directly with
interp.py and through eval.scm, and five of them also through eval.scm
interpreting eval.scm. Each output through eval.scm must equal the direct
output after normalize_output: strip(), then drop a last line that is exactly
"True". Upstream fails a run that times out (60 s).

cases.json (hidden/derive.py) holds those programs, their inputs, their direct
outputs from upstream's unmodified interp.py, and whether upstream also runs
them twice. The plan turns each program into one "once" case, and each program
upstream runs twice into one "twice" case as well.
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

# The adapter shows at most this many bytes of output. normalize_output removes
# at most a last "True" line, so a longer output can never equal one of the
# expected outputs, which are all far shorter (CONVERSION.md, fidelity change 5).
SHOWN = 16384


def normalize_output(output: str) -> str:
    """Upstream's normalize_output, verbatim in effect."""
    output = output.strip()
    lines = output.split("\n")
    if lines and lines[-1] == "True":
        lines = lines[:-1]
        output = "\n".join(lines)
    return output


def plan(resources: HiddenResources, seed: int) -> Plan:
    stored = resources.read_json("cases.json")
    assert isinstance(stored, list)
    once: list[Case] = []
    twice: list[Case] = []
    for entry in stored:
        assert isinstance(entry, dict)
        name, program, given, output = entry["name"], entry["program"], entry["input"], entry["expected"]
        assert isinstance(name, str) and isinstance(program, str)
        assert isinstance(given, str) and isinstance(output, str)
        challenge: dict[str, JsonValue] = {"name": name, "program": program, "input": given}
        context = {"program": f"{entry['suite']}/{name}", "expected": output}
        once.append(Case(challenge, context))
        if entry["twice"] is True:
            twice.append(Case(challenge, context))
    return Plan(artifact_contexts={}, cases={"once": tuple(once), "twice": tuple(twice)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(context, dict):
        return Judgment(False, {"reason": "unexpected evidence"})
    program, expected = context["program"], context["expected"]
    if not isinstance(expected, str):
        return Judgment(False, {"program": program, "reason": "bad context"})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"program": program, "reason": "no observation"})
    run = evidence.outcome.value
    if not isinstance(run, dict):
        return Judgment(False, {"program": program, "reason": "malformed"})
    text, size = run["text"], run["text_bytes"]
    if not isinstance(text, str) or not isinstance(size, int):
        return Judgment(False, {"program": program, "reason": "malformed"})
    if run["ending"] != "exited":
        return Judgment(False, {"program": program, "reason": "timed out after 60 s"})
    if run["utf8"] is not True:
        return Judgment(False, {"program": program, "reason": "output is not valid UTF-8"})
    if size > SHOWN or size != len(text.encode("utf-8")):
        return Judgment(False, {"program": program, "reason": "output not shown in full", "text_bytes": size})
    got, want = normalize_output(text), normalize_output(expected)
    if got != want:
        return Judgment(False, {"program": program, "expected": want, "got": got[:2048]})
    return Judgment(True, None)
