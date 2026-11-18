"""Oracle for crack-7z-hash.

Upstream's test reads /app/solution.txt with `open(path, "r").read().strip()`
and requires the result to equal the secret word. We repeat that on the bytes
the adapter reports: strict UTF-8 decoding (the verifier's Python runs in the
C locale, which Python coerces to UTF-8), universal-newline translation, then
`str.strip()` and equality.
"""

import base64
import binascii

from securebench.core.evidence import (
    ArtifactEvidence,
    Case,
    CaseEvidence,
    Ending,
    HiddenResources,
    Judgment,
    Observed,
    Plan,
)
from securebench.core.jsondata import JsonValue

CHECK = "solution"


def plan(resources: HiddenResources, seed: int) -> Plan:
    entries = resources.read_json("cases.json")
    if not isinstance(entries, list):
        raise ValueError("cases.json is not a list")
    cases = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("a case is not an object")
        cases.append(Case(entry["challenge"], entry["expected_stripped_content"]))
    return Plan(artifact_contexts={}, cases={CHECK: tuple(cases)})


def _fail(reason: str) -> Judgment:
    return Judgment(False, {"reason": reason})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id != CHECK or not isinstance(evidence, CaseEvidence):
        return _fail("unexpected evidence")
    if not isinstance(context, str):
        return _fail("malformed context")
    if evidence.facts.ending is not Ending.RETURNED or evidence.facts.exit_status != 0:
        return _fail("the adapter did not return normally")
    outcome = evidence.outcome
    if not isinstance(outcome, Observed):
        return _fail("no observation")
    value = outcome.value
    if not isinstance(value, dict) or set(value) != {"content_base64"}:
        return _fail("observation has the wrong fields")
    encoded = value["content_base64"]
    if not isinstance(encoded, str):
        return _fail("content is not a string")
    try:
        data = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return _fail("content is not valid base64")
    try:
        text = data.decode("utf-8", "strict")
    except UnicodeDecodeError:
        # Native open() in text mode raises here, failing the test.
        return _fail("solution.txt is not valid UTF-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.strip() != context:
        return _fail("solution.txt does not contain the secret word")
    return Judgment(True, None)
