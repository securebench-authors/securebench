"""Oracle for path-tracing-reverse.

Upstream asserts that /app/mystery.c exists, that it compiles with
`gcc -static -o /app/reverse /app/mystery.c -lm`, that
`len(zlib.compress(open("/app/mystery.c").read().encode())) < 2100`, and that the
image the binary writes has a cosine similarity of at least 0.995 to the image
/app/mystery writes, which the test first moves to /tmp/mystery.

The `source` artifact check reads mystery.c from the candidate itself and
recomputes the compressed size: `open().read()` decodes UTF-8 with universal
newlines, so "\\r\\n" and a lone "\\r" become "\\n" before compressing.

The `original` artifact check requires /app/mystery to be the baseline's
binary, byte for byte (hidden/expected.json), and `render` requires it to be
executable, as the adapter reports before it deletes it. Upstream renders
its reference image with whatever /app/mystery holds when the tests run; with
the baseline's binary that image is hidden/original-rgb.zlib, which derive.py
rendered once. So the `render` case compares with it.

`render` repeats test_image_similarity's arithmetic on the values the adapter
reports, in numpy's order and precision: the flattened arrays divided by 255.0,
numpy's broadcasting of a one-value array, numpy's pairwise summation
(`pairwise_sum`), and float32 arithmetic for a float image, as numpy keeps
float32 arrays in float32 (hidden/differential.py).
"""

import base64
import math
import struct
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
    Text,
)
from securebench.core.jsondata import JsonValue

# Upstream's thresholds.
MAX_COMPRESSED = 2100
THRESHOLD = 0.995
# numpy's PW_BLOCKSIZE (numpy/_core/src/umath/loops_utils.h.src).
BLOCK = 128
BANDS = {"1": 1, "L": 1, "I": 1, "F": 1, "P": 1, "RGB": 3, "RGBA": 4, "CMYK": 4}
# How the adapter encodes one value of each mode (adapter.py, `encode`).
VALUE_BYTES = {"I": 2, "F": 4}


def compressed_size(text: str) -> int:
    """Upstream's `len(zlib.compress(open(path).read().encode()))` for a file of text `text`."""
    return len(zlib.compress(text.replace("\r\n", "\n").replace("\r", "\n").encode()))


def float32(value: float) -> float:
    """`value` rounded to the nearest float32, overflowing to infinity as numpy does."""
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def divide(a: float, b: float) -> float:
    """IEEE division, which numpy applies and Python refuses for a zero divisor."""
    if b == 0.0:
        if a == 0.0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a) * math.copysign(1.0, b)
    return a / b


def _pairwise(values: list[float], start: int, count: int, rounded) -> float:
    """numpy's pairwise_sum, in the same order of additions, each sum rounded by `rounded`."""
    if count < 8:
        total = 0.0
        for index in range(start, start + count):
            total = rounded(total + values[index])
        return total
    if count <= BLOCK:
        partial = values[start : start + 8]
        index = 8
        end = count - count % 8
        while index < end:
            for lane in range(8):
                partial[lane] = rounded(partial[lane] + values[start + index + lane])
            index += 8
        total = rounded(
            rounded(rounded(partial[0] + partial[1]) + rounded(partial[2] + partial[3]))
            + rounded(rounded(partial[4] + partial[5]) + rounded(partial[6] + partial[7]))
        )
        while index < count:
            total = rounded(total + values[start + index])
            index += 1
        return total
    half = count // 2
    half -= half % 8
    return rounded(
        _pairwise(values, start, half, rounded)
        + _pairwise(values, start + half, count - half, rounded)
    )


def pairwise_sum(values: list[float], rounded=float) -> float:
    """`np.sum` of a contiguous one-dimensional float64 array, or float32 with `rounded=float32`."""
    return _pairwise(values, 0, len(values), rounded)


def similarity(original: bytes, values: list[float], single: bool) -> float:
    """test_image_similarity's value, for the original's uint8 values and the image's values.

    `values` are the image's array elements as Python floats; `single` says the
    array is float32. Everything else numpy turns into float64 when it divides
    by 255.0. NaN where upstream divides zero by zero, which fails.
    """
    original_array = [value / 255.0 for value in original]
    orig_length = math.sqrt(pairwise_sum([value * value for value in original_array]))
    if single:
        reconstructed_array = [float32(value / 255.0) for value in values]
        squares = [float32(value * value) for value in reconstructed_array]
        recon_length = float32(math.sqrt(pairwise_sum(squares, float32)))
        reconstructed_norm = [float32(divide(value, recon_length)) for value in reconstructed_array]
    else:
        reconstructed_array = [value / 255.0 for value in values]
        recon_length = math.sqrt(pairwise_sum([value * value for value in reconstructed_array]))
        reconstructed_norm = [divide(value, recon_length) for value in reconstructed_array]
    original_norm = [divide(value, orig_length) for value in original_array]
    if len(reconstructed_norm) == 1:
        # numpy broadcasts a one-value array against the other.
        products = [value * reconstructed_norm[0] for value in original_norm]
    else:
        products = [a * b for a, b in zip(original_norm, reconstructed_norm, strict=True)]
    return pairwise_sum(products)


def plan(resources: HiddenResources, seed: int) -> Plan:
    expected = resources.read_json("expected.json")
    if not isinstance(expected, dict):
        raise ValueError("hidden/expected.json is not an object")
    packed = resources.read("original-rgb.zlib")
    zlib.decompress(packed)
    context: JsonValue = {"original_rgb_zlib": base64.b64encode(packed).decode("ascii")}
    return Plan(
        artifact_contexts={"source": None, "original": expected["original_binary"]},
        cases={"render": (Case({}, context),)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        if check_id == "source":
            return _source(evidence)
        if check_id == "original":
            return _original(context, evidence)
        return Judgment(False, {"reason": "unknown check"})
    return _render(context, evidence)


def _source(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "malformed"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        # Absent, not a regular file, over 16 MiB (which cannot compress below
        # 2,100 bytes) or not UTF-8 text without a byte-order mark.
        return Judgment(
            False, {"reason": f"/app/mystery.c is {found.status.value}", "detail": found.reason}
        )
    size = compressed_size(found.value.text)
    if not size < MAX_COMPRESSED:
        return Judgment(
            False, {"reason": "mystery.c compresses to 2,100 bytes or more", "compressed": size}
        )
    return Judgment(True, {"compressed": size})


def _original(context: JsonValue, evidence: ArtifactEvidence) -> Judgment:
    if not isinstance(context, dict) or len(evidence.files) != 1:
        return Judgment(False, {"reason": "malformed"})
    found = evidence.files[0]
    # The binary is not UTF-8, so a present file is `unparsable`; only its
    # SHA-256 matters, whatever the text parser made of it.
    if found.status not in (FileStatus.PRESENT, FileStatus.UNPARSABLE):
        return Judgment(False, {"reason": f"/app/mystery is {found.status.value}"})
    if found.sha256 != context["sha256"]:
        return Judgment(
            False, {"reason": "/app/mystery is not the baseline's binary", "sha256": found.sha256}
        )
    return Judgment(True, None)


def _render(context: JsonValue, evidence: CaseEvidence) -> Judgment:
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    # cp keeps the copy's mode, so upstream's chroot runs the binary only if
    # it is executable; replay keeps the executable bit.
    if observed["original_executable"] is not True:
        return Judgment(False, {"reason": "/app/mystery is not executable"})
    built = observed["compile"]
    if not isinstance(built, dict) or built["ending"] != "exited" or built["exit_status"] != 0:
        return Judgment(False, {"reason": "mystery.c did not compile", "compile": built})
    ran = observed.get("run")
    # Upstream ignores the binary's exit status (only the `cp` of image.ppm is
    # checked), but a binary that never ends exceeds its verifier timeout.
    if not isinstance(ran, dict) or ran["ending"] not in ("exited", "signaled"):
        return Judgment(False, {"reason": "the binary did not end", "run": ran})
    problem = observed.get("image_problem")
    image = observed.get("image")
    if problem is not None or not isinstance(image, dict):
        return Judgment(False, {"reason": "image.ppm not decoded", "problem": problem})
    packed = context["original_rgb_zlib"]
    if not isinstance(packed, str):
        return Judgment(False, {"reason": "malformed context"})
    original = zlib.decompress(base64.b64decode(packed))
    values = _values(image, len(original))
    if isinstance(values, str):
        return Judgment(False, {"reason": values})
    score = similarity(original, values, image["mode"] == "F")
    shown = score if math.isfinite(score) else repr(score)
    if not score >= THRESHOLD:
        return Judgment(False, {"reason": "images not similar enough", "similarity": shown})
    return Judgment(True, {"similarity": shown})


def _values(image: dict[str, JsonValue], original_count: int) -> list[float] | str:
    """The image's array elements, checked against its mode and size.

    The count is checked before anything is decoded, so the work stays bounded
    by the original's size whatever the observation claims.
    """
    mode, width, height, encoded = image["mode"], image["width"], image["height"], image["values"]
    if (
        not isinstance(mode, str)
        or mode not in BANDS
        or not isinstance(width, int)
        or not isinstance(height, int)
        or not isinstance(encoded, str)
    ):
        return "malformed image"
    count = width * height * BANDS[mode]
    # `original_norm * reconstructed_norm` needs equal lengths, or one value
    # that numpy broadcasts; anything else raises in upstream's test.
    if count not in (1, original_count):
        return f"image and original do not combine ({count} values)"
    size = count * VALUE_BYTES.get(mode, 1)
    try:
        packed = base64.b64decode(encoded, validate=True)
        inflater = zlib.decompressobj()
        data = inflater.decompress(packed, size + 1)
    except (ValueError, zlib.error):
        return "image values are not encoded"
    if len(data) != size or not inflater.eof or inflater.unconsumed_tail:
        return "image values do not match its size"
    if mode == "F":
        return list(struct.unpack(f"<{count}f", data))
    if mode == "I":
        return [float(int.from_bytes(data[i : i + 2], "big")) for i in range(0, size, 2)]
    if mode == "1" and not set(data) <= {0, 1}:
        return "bitmap values are not 0 or 1"
    return [float(value) for value in data]
