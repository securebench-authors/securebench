"""Oracle for make-mips-interpreter.

Upstream runs `node /app/vm.js` once, then asserts that /tmp/frame.bmp appeared
within 30 s, that vm.js's output contains the I_InitGraphics line, that the
frame exists and is not empty, and that it has reference.jpg's size and a
similarity of at least 0.95 to it, where similarity is one minus the mean
absolute channel difference over 255.

The case, the expected line, the reference size and the name of the file that
holds reference.jpg's pixels are in cases.json; the pixels are in
reference-rgb.zlib. This file holds only the comparisons. vm.js's output comes
in the check's one Output Artifact, the frame in the observation.
"""

import base64
import zlib

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

THRESHOLD = 0.95


def similarity(frame: bytes, reference: bytes) -> float:
    """Upstream's score, with its arithmetic: sum of channel differences, then two divisions."""
    total_diff = sum(abs(a - b) for a, b in zip(frame, reference, strict=True))
    avg_diff = total_diff / len(reference)
    return 1.0 - (avg_diff / 255.0)


def plan(resources: HiddenResources, seed: int) -> Plan:
    entries = resources.read_json("cases.json")
    if not isinstance(entries, list) or not entries:
        raise ValueError("cases.json is not a non-empty list")
    cases: list[Case] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("a case is not an object")
        width, height, name = entry["width"], entry["height"], entry["reference_rgb"]
        if not isinstance(width, int) or not isinstance(height, int) or not isinstance(name, str):
            raise ValueError("a case has a malformed reference")
        reference = resources.read(name)
        if len(zlib.decompress(reference)) != width * height * 3:
            raise ValueError("the reference pixels do not match the reference size")
        context = {
            "expected_text": entry["expected_text"],
            "width": width,
            "height": height,
            "expected_rgb_zlib": base64.b64encode(reference).decode("ascii"),
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
    packed = context["expected_rgb_zlib"]
    if (
        not isinstance(text, str)
        or not isinstance(width, int)
        or not isinstance(height, int)
        or not isinstance(packed, str)
    ):
        return Judgment(False, {"reason": "malformed context"})
    if observed.get("frame_appeared") is not True:
        return Judgment(False, {"reason": "frame.bmp did not appear within 30 s"})
    output = _output(evidence)
    if output is None:
        return Judgment(False, {"reason": "no output artifact"})
    if text.encode("utf-8") not in output:
        tail = output[-400:].decode("utf-8", "replace")
        return Judgment(False, {"reason": "expected text not in output", "output_tail": tail})
    frame = observed.get("frame")
    problem = observed.get("frame_problem")
    if problem is not None or not isinstance(frame, dict):
        return Judgment(False, {"reason": "frame.bmp not decoded", "problem": problem})
    if frame.get("width") != width or frame.get("height") != height:
        size = f"{frame.get('width')}x{frame.get('height')}"
        return Judgment(False, {"reason": f"frame size {size}, expected {width}x{height}"})
    pixels = _decode(frame.get("rgb_b64"))
    if pixels is None or len(pixels) != width * height * 3:
        return Judgment(False, {"reason": "frame pixels do not match its size"})
    expected = zlib.decompress(base64.b64decode(packed))
    if len(expected) != width * height * 3:
        return Judgment(False, {"reason": "malformed context"})
    score = similarity(pixels, expected)
    if not score >= THRESHOLD:
        return Judgment(False, {"reason": "images not similar enough", "similarity": score})
    return Judgment(True, {"similarity": score})


def _output(evidence: CaseEvidence) -> bytes | None:
    if len(evidence.output_artifacts) != 1:
        return None
    found = evidence.output_artifacts[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, dict):
        return None
    return _decode(found.value.get("output_b64"))


def _decode(value: JsonValue) -> bytes | None:
    if not isinstance(value, str):
        return None
    # Bad padding or characters (binascii.Error) and non-ASCII text are both ValueError.
    try:
        return base64.b64decode(value, validate=True)
    except ValueError:
        return None
