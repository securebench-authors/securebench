"""Oracle for fix-git.

Upstream has two tests. Each reads one file of the working tree and passes
when the MD5 of its bytes, after `bytes.strip()`, equals the MD5 of the
stripped bytes of upstream's copy in /app/resources/patch_files. Those
copies are in the baseline, where the candidate can rewrite them, so the
expected contents here are hidden/about.md and hidden/default.html, byte
for byte the same files.

This Oracle compares the stripped text itself instead of its MD5, which
accepts exactly the same files short of an MD5 collision. `bytes.strip()`
removes the six ASCII whitespace bytes, and stripping the same six
characters from the decoded text gives the same result, because UTF-8
encodes them as single bytes that never occur inside a multi-byte
character. A file that is not UTF-8, or starts with a byte-order mark, is
unparsable here and differs from the UTF-8 expected text upstream, so both
fail it. The file is bounded by the artifact check (16 MiB), so the work
here is one comparison of strings of at most that size.
"""

from securebench.core.errors import Rejected
from securebench.core.evidence import (
    ArtifactEvidence,
    CaseEvidence,
    FileStatus,
    HiddenResources,
    Judgment,
    Plan,
    Text,
)
from securebench.core.jsondata import JsonValue

# The bytes that Python's bytes.strip() removes when given no argument.
ASCII_WHITESPACE = " \t\n\r\x0b\x0c"

CHECKS = {
    "about": ("/app/personal-site/_includes/about.md", "about.md"),
    "layout": ("/app/personal-site/_layouts/default.html", "default.html"),
}


def plan(resources: HiddenResources, seed: int) -> Plan:
    contexts: dict[str, JsonValue] = {}
    for check_id, (_, hidden_name) in CHECKS.items():
        try:
            text = resources.read(hidden_name).decode("utf-8", "strict")
        except UnicodeDecodeError:
            raise Rejected(f"hidden/{hidden_name} is not UTF-8") from None
        contexts[check_id] = {"expected": text.strip(ASCII_WHITESPACE)}
    return Plan(artifact_contexts=contexts, cases={})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id not in CHECKS or not isinstance(evidence, ArtifactEvidence):
        return Judgment(False, {"reason": "unexpected check"})
    if not isinstance(context, dict) or not isinstance(context.get("expected"), str):
        return Judgment(False, {"reason": "malformed context"})
    expected = context["expected"]
    path = CHECKS[check_id][0]
    if len(evidence.files) != 1 or evidence.files[0].path != path or evidence.listings:
        return Judgment(False, {"reason": "unexpected evidence"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT:
        return Judgment(False, {"reason": f"{path} is {found.status.value}", "detail": found.reason})
    if not isinstance(found.value, Text):
        return Judgment(False, {"reason": "unexpected evidence"})
    got = found.value.text.strip(ASCII_WHITESPACE)
    if got != expected:
        return Judgment(False, _difference(path, expected, got))
    return Judgment(True, None)


def _difference(path: str, expected: str, got: str) -> JsonValue:
    """Where the stripped contents first differ, without quoting the candidate's file."""
    expected_lines = expected.split("\n")
    got_lines = got.split("\n")
    line = 0
    while line < len(expected_lines) and line < len(got_lines):
        if expected_lines[line] != got_lines[line]:
            break
        line += 1
    return {
        "reason": f"{path} differs from the lost commit's version",
        "first_differing_line": line + 1,
        "expected_characters": len(expected),
        "got_characters": len(got),
    }
