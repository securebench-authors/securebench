"""Oracle for prove-plus-comm.

Upstream's four tests map to three checks:

- proof-source: test_proof_file_exists and test_proof_contents. plus_comm.v
  must be a readable UTF-8 file containing each required substring and none
  of the forbidden ones, compared exactly as Python's `in` does upstream.
- compiled-proof: test_compiled_proof_exists. plus_comm.vo must exist in the
  candidate. os.path.exists accepts any existing entry, so every status
  except `absent` counts; the content of the binary file is not judged.
- compile: test_compiled_proof_content. The baseline's coqc must exit with
  the expected status, and its output must decode as strict UTF-8, because
  upstream's subprocess.run(text=True) raises otherwise.

The required and forbidden substrings and the expected exit status live in
hidden/expected.json.
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
    Text,
)
from securebench.core.jsondata import JsonValue

# os.path.exists is true for a regular file of any size or encoding and for a
# directory; only a missing entry is false.
EXISTING = (FileStatus.PRESENT, FileStatus.UNPARSABLE, FileStatus.TOO_LARGE, FileStatus.NOT_REGULAR)


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    cases = {
        check_id: tuple(Case(entry["challenge"], entry["context"]) for entry in entries)
        for check_id, entries in expected["cases"].items()
    }
    return Plan(artifact_contexts=dict(expected["artifacts"]), cases=cases)


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "proof-source" and isinstance(evidence, ArtifactEvidence):
        return _judge_source(context, evidence)
    if check_id == "compiled-proof" and isinstance(evidence, ArtifactEvidence):
        return _judge_compiled(evidence)
    if check_id == "compile" and isinstance(evidence, CaseEvidence):
        return _judge_compile(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence", "check": check_id})


def _judge_source(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return Judgment(False, {"reason": "plus_comm.v is not a readable UTF-8 file", "status": found.status.value, "detail": found.reason})
    content = found.value.text
    missing = [needle for needle in context["must_contain"] if needle not in content]
    forbidden = [needle for needle in context["must_not_contain"] if needle in content]
    if missing or forbidden:
        return Judgment(False, {"reason": "proof text check failed", "missing": missing, "forbidden": forbidden})
    return Judgment(True, None)


def _judge_compiled(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    if found.status not in EXISTING:
        return Judgment(False, {"reason": "plus_comm.vo does not exist", "status": found.status.value})
    return Judgment(True, None)


def _judge_compile(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return Judgment(False, {"reason": "the adapter returned no observation"})
    observed = outcome.value
    if not isinstance(observed, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    status = observed.get("exit_status")
    utf8 = observed.get("output_utf8")
    tail = observed.get("output_tail")
    if type(status) is not int or type(utf8) is not bool:
        return Judgment(False, {"reason": "observation fields missing or mistyped"})
    if status != context["exit_status"]:
        return Judgment(False, {"reason": "coqc failed", "exit_status": status, "output_tail": tail})
    if utf8 is not context["output_utf8"]:
        return Judgment(False, {"reason": "coqc output is not valid UTF-8", "output_tail": tail})
    return Judgment(True, None)
