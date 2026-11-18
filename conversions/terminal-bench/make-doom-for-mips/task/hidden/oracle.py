"""Oracle for make-doom-for-mips.

Upstream runs `node /app/vm.js` once, then asserts that its output contains the
I_InitGraphics line, that /tmp/frame.bmp appeared within 30 s and is not empty,
and that the frame has reference.jpg's size and a similarity of at least 0.95
to it, where similarity is one minus the mean absolute channel difference over
255. The expected line, the size and the reference pixels are in cases.json and
reference-rgb.zlib; this file holds only how to compare.
"""

import base64
import zlib

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

# test_frame_bmp_similar_to_reference's threshold.
THRESHOLD = 0.95


def similarity(frame: bytes, reference: bytes) -> float:
    """Upstream's score, with the same arithmetic: sum of channel differences, then two divisions."""
    total_diff = sum(abs(a - b) for a, b in zip(frame, reference))
    avg_diff = total_diff / len(reference)
    return 1.0 - (avg_diff / 255.0)


def plan(resources: HiddenResources, seed: int) -> Plan:
    entries = resources.read_json("cases.json")
    if not isinstance(entries, list) or not entries:
        raise ValueError("cases.json is not a list of cases")
    cases: list[Case] = []
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry["reference"], str):
            raise ValueError("malformed case in cases.json")
        width, height = entry["width"], entry["height"]
        if not isinstance(width, int) or not isinstance(height, int):
            raise ValueError("malformed size in cases.json")
        packed = resources.read(entry["reference"])
        if len(zlib.decompress(packed)) != width * height * 3:
            raise ValueError("the reference pixels do not match the size in cases.json")
        context = {
            "expected_text": entry["expected_text"],
            "width": width,
            "height": height,
            "reference_rgb_zlib": base64.b64encode(packed).decode("ascii"),
        }
        cases.append(Case(entry["challenge"], context))
    return Plan(artifact_contexts={}, cases={"doom": tuple(cases)})


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if not isinstance(evidence, CaseEvidence) or not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    text, width, height = context["expected_text"], context["width"], context["height"]
    packed = context["reference_rgb_zlib"]
    if not isinstance(text, str) or not isinstance(width, int) or not isinstance(height, int):
        return Judgment(False, {"reason": "malformed context"})
    if not isinstance(packed, str):
        return Judgment(False, {"reason": "malformed context"})
    # test_vm_execution: the frame appears within 30 s, and the expected text is in stdout and stderr.
    if observed.get("frame_appeared") is not True:
        return Judgment(False, {"reason": "frame.bmp did not appear within 30 s"})
    stdout_hex = observed.get("stdout_hex")
    if not isinstance(stdout_hex, str):
        return Judgment(False, {"reason": "no stdout"})
    try:
        stdout = bytes.fromhex(stdout_hex)
    except ValueError:
        return Judgment(False, {"reason": "stdout is not hex"})
    if text.encode("utf-8") not in stdout:
        tail = stdout[-400:].decode("utf-8", "replace")
        return Judgment(False, {"reason": "expected text not in output", "stdout_tail": tail})
    # test_frame_bmp_exists and test_frame_bmp_similar_to_reference.
    frame = observed.get("frame")
    problem = observed.get("frame_problem")
    if problem is not None or not isinstance(frame, dict):
        return Judgment(False, {"reason": "frame.bmp not opened as an image", "problem": problem})
    pixels = _pixels(frame, width, height)
    if isinstance(pixels, str):
        return Judgment(False, {"reason": pixels})
    reference = zlib.decompress(base64.b64decode(packed))
    if len(reference) != width * height * 3:
        return Judgment(False, {"reason": "malformed context"})
    score = similarity(pixels, reference)
    if not score >= THRESHOLD:
        return Judgment(False, {"reason": "images not similar enough", "similarity": score})
    return Judgment(True, {"similarity": score})


def _pixels(frame: dict[str, JsonValue], width: int, height: int) -> bytes | str:
    if frame.get("width") != width or frame.get("height") != height:
        return f"image sizes do not match: {frame.get('width')}x{frame.get('height')}, expected {width}x{height}"
    rows = frame.get("rows")
    if not isinstance(rows, list) or len(rows) != height:
        return "frame rows do not match its height"
    decoded: list[bytes] = []
    for row in rows:
        if not isinstance(row, str) or len(row) != width * 6:
            return "a frame row does not match its width"
        try:
            pixels = bytes.fromhex(row)
        except ValueError:
            return "a frame row is not hex"
        if len(pixels) != width * 3:
            return "a frame row is not hex"
        decoded.append(pixels)
    return b"".join(decoded)
