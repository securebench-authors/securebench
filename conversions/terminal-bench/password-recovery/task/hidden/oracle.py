"""Oracle for password-recovery: the recovered password must be one of the guesses.

Upstream's test reads the file with `Path.read_text()`, which translates every
`\\r\\n` and lone `\\r` to `\\n` (universal newlines), then takes
`.strip().split("\\n")` and requires the password to equal one of the pieces.
The judge repeats exactly that on the captured text.
"""

from securebench.core.evidence import ArtifactEvidence, CaseEvidence, FileStatus, HiddenResources, Judgment, Plan, Text
from securebench.core.jsondata import JsonValue

CHECK_ID = "recovered-passwords"


def plan(resources: HiddenResources, seed: int) -> Plan:
    return Plan(artifact_contexts={CHECK_ID: resources.read_json("expected.json")}, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK_ID or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected evidence"})
    if not isinstance(context, dict) or not isinstance(context.get("password"), str):
        return Judgment(False, {"reason": "malformed context"})
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "unexpected number of files"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"recovered_passwords.txt is {found.status.value}", "detail": found.reason})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "recovered_passwords.txt was not parsed as text"})
    text = found.value.text.replace("\r\n", "\n").replace("\r", "\n")
    guesses = text.strip().split("\n")
    if context["password"] not in guesses:
        return Judgment(False, {"reason": "password not found", "guesses": len(guesses)})
    return Judgment(True, {"guesses": len(guesses)})
