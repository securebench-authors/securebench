"""Oracle for write-compressor.

Upstream's three tests become two checks:

- `data-comp` (artifact): test_compressed_file_exists and test_compression_size.
  /app/data.comp must be a regular file of at most 2500 bytes, read straight from
  the captured candidate, so no code the candidate controls can misreport it.
- `decompress` (protocol, one case): test_decompression_produces_original. The
  adapter runs upstream's own decompressor on the file and reports its exit
  status and output; we compare that output with hidden/data.txt the way the
  test does.
"""

import base64
import binascii

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
)
from securebench.core.jsondata import JsonValue

# test_compression_size: `file_size <= max_size_bytes` with max_size_bytes = 2500.
MAX_COMPRESSED_BYTES = 2500
# The adapter reports at most this many bytes of output (see adapter.py).
REPORTED_BYTES = 65536


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read("data.txt").decode("utf-8")
    return Plan(
        artifact_contexts={"data-comp": None},
        cases={"decompress": (Case({}, {"expected": expected}),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if check_id == "data-comp" and isinstance(evidence, ArtifactEvidence):
        return _judge_file(evidence)
    if check_id == "decompress" and isinstance(evidence, CaseEvidence):
        return _judge_output(context, evidence)
    return Judgment(False, {"reason": "unexpected check or evidence"})


def _judge_file(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "expected exactly one file"})
    found = evidence.files[0]
    # The file is binary, so `unparsable` (not UTF-8) is as good as `present`;
    # `too_large` means above the 2500-byte bound declared in task.toml.
    if found.status not in (FileStatus.PRESENT, FileStatus.UNPARSABLE):
        return Judgment(False, {"reason": f"/app/data.comp is {found.status.value}"})
    if not isinstance(found.size, int) or found.size > MAX_COMPRESSED_BYTES:
        return Judgment(False, {"reason": "/app/data.comp is larger than 2500 bytes", "size": found.size})
    return Judgment(True, {"size": found.size})


def _judge_output(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(context, dict):
        return Judgment(False, {"reason": "bad context"})
    expected = context.get("expected")
    if not isinstance(expected, str):
        return Judgment(False, {"reason": "bad context"})
    if evidence.facts.ending is not Ending.RETURNED or evidence.facts.exit_status != 0:
        return Judgment(False, {"reason": "adapter did not return normally", "ending": evidence.facts.ending.value})
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    value = evidence.outcome.value
    if not isinstance(value, dict):
        return Judgment(False, {"reason": "observation is not an object"})
    status = value.get("exit_status")
    size = value.get("stdout_bytes")
    encoded = value.get("stdout_base64")
    if not isinstance(status, int) or isinstance(status, bool):
        return Judgment(False, {"reason": "missing exit_status"})
    if not isinstance(size, int) or isinstance(size, bool) or not isinstance(encoded, str):
        return Judgment(False, {"reason": "missing output"})

    # `assert result.returncode == 0`
    if status != 0:
        return Judgment(False, {"reason": "decompressor exited with a non-zero status", "exit_status": status})

    # Output beyond the reported prefix cannot match: even after newline
    # translation it is far longer than data.txt.
    if size > REPORTED_BYTES:
        return Judgment(False, {"reason": "decompressed output is too long", "stdout_bytes": size})
    try:
        output = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        return Judgment(False, {"reason": "output is not valid base64"})
    if len(output) != size:
        return Judgment(False, {"reason": "reported size does not match the output"})

    # subprocess.run(..., text=True) decodes with UTF-8 (strict) and translates
    # newlines; Path.read_text() does the same to data.txt. Undecodable output
    # raises in the test, which fails it.
    try:
        text = output.decode("utf-8")
    except UnicodeDecodeError:
        return Judgment(False, {"reason": "decompressed output is not valid UTF-8"})

    # `assert result.stdout == original_content`
    if _universal_newlines(text) != _universal_newlines(expected):
        return Judgment(
            False,
            {"reason": "decompressed output differs from data.txt", "stdout_bytes": size},
        )
    return Judgment(True, {"stdout_bytes": size})


def _universal_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")
