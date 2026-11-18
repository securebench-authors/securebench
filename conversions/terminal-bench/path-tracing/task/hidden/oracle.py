"""Oracle for path-tracing.

Upstream's five tests assert that /app/image.c exists; that
`gcc -static -o /app/image /app/image.c -lm` returns 0 and
`len(zlib.compress(open("/app/image.c").read().encode())) < 2100`; that
`gcc -H /app/image.c -lm` returns 0 and prints nothing containing "/app/"; that
the binary, run alone in a chroot, exits 0 and writes reconstructed.ppm; and that
the cosine similarity of that image to /app/image.ppm is at least 0.99. Each
command's output is decoded as strict UTF-8 (`text=True`), which fails the test
on anything else.

The `source` artifact check reads image.c from the candidate and recomputes the
compressed size: `open().read()` decodes UTF-8 with universal newlines, so
"\\r\\n" and a lone "\\r" become "\\n" before compressing. The `build` case
judges the unlink, the static build and gcc -H, from an Evaluation in which no
code of the candidate's runs. The `render` case judges the run and the image.
The original image is the baseline's /app/image.ppm as derive.py decoded it
(named in cases.json), never the /app/image.ppm a candidate may have changed.
The reconstructed image is the `__array_interface__` the adapter decoded as
Pillow's PPM plugin does, which is what upstream's `np.array(...)` reads. The
similarity is upstream's arithmetic in upstream's order, with numpy's types
(float32 for a float32 image), its broadcasting of a one-element array, and its
pairwise summation reproduced exactly (`numpy_sum`), so the value is the same
float numpy computes (differential.py).
"""

import base64
import binascii
import math
import struct
import zlib
from functools import reduce
from operator import add

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
THRESHOLD = 0.99
# The adapter shows each gcc -H stream in full up to this size.
OUTPUT_SHOWN = 1024 * 1024
# numpy's PW_BLOCKSIZE (numpy/_core/src/umath/loops_utils.h.src).
BLOCK = 128
# Array interface type codes (after the byte-order character) Pillow 11.2.1's
# PPM plugin produces, other than |b1 and |u1 (modes I and F), and their struct
# codes.
STRUCT_CODES = {"i4": "i", "f4": "f"}


def compressed_size(text: str) -> int:
    """Upstream's `len(zlib.compress(open(path).read().encode()))` for a file of text `text`."""
    return len(zlib.compress(text.replace("\r\n", "\n").replace("\r", "\n").encode()))


def _f32(value: float) -> float:
    """`value` rounded to float32. Rounding an exact double result of +, *, / or
    sqrt of float32 operands gives the correctly rounded float32 result."""
    try:
        return struct.unpack("<f", struct.pack("<f", value))[0]
    except OverflowError:
        return math.copysign(math.inf, value)


def _add32(a: float, b: float) -> float:
    return _f32(a + b)


def _divide(a: float, b: float) -> float:
    """IEEE division, as numpy divides, where Python would raise on zero."""
    if b == 0.0:
        if a == 0.0 or math.isnan(a):
            return math.nan
        return math.copysign(math.inf, a) * math.copysign(1.0, b)
    return a / b


def _pairwise(values: list[float], start: int, count: int, plus) -> float:
    """numpy's pairwise_sum, in the same order of additions.

    Each of the 8 partial sums of a block adds every 8th value from left to
    right, which is what `reduce(plus, ...)` over a stride-8 slice does.
    """
    if count < 8:
        return reduce(plus, values[start : start + count], 0.0)
    if count <= BLOCK:
        end = count - count % 8
        partial = [reduce(plus, values[start + lane : start + end : 8]) for lane in range(8)]
        total = plus(
            plus(plus(partial[0], partial[1]), plus(partial[2], partial[3])),
            plus(plus(partial[4], partial[5]), plus(partial[6], partial[7])),
        )
        return reduce(plus, values[start + end : start + count], total)
    half = count // 2
    half -= half % 8
    return plus(_pairwise(values, start, half, plus), _pairwise(values, start + half, count - half, plus))


def numpy_sum(values: list[float], float32: bool = False) -> float:
    """`np.sum` of a contiguous one-dimensional float64 (or float32) array."""
    return _pairwise(values, 0, len(values), _add32 if float32 else add)


def item_size(typestr: str) -> int | None:
    """The bytes per element of an array interface type string we can read, or None."""
    if typestr in ("|b1", "|u1"):
        return 1
    if len(typestr) == 3 and typestr[0] in "<>" and typestr[1:] in STRUCT_CODES:
        return int(typestr[2])
    return None


def scaled(typestr: str, data: bytes) -> tuple[list[float], bool]:
    """`np.array(image).flatten() / 255.0` for the array's raw bytes, and whether it is float32.

    numpy casts a bool to 0 or 1 and an integer to float64; it divides a float32
    array by a Python float in float32.
    """
    if typestr == "|b1":
        one = 1.0 / 255.0
        return [one if byte else 0.0 for byte in data], False
    if typestr == "|u1":
        table = [value / 255.0 for value in range(256)]
        return [table[byte] for byte in data], False
    code = STRUCT_CODES[typestr[1:]]
    numbers = struct.unpack(f"{typestr[0]}{len(data) // int(typestr[2])}{code}", data)
    if code == "f":
        return [_f32(number / 255.0) for number in numbers], True
    return [number / 255.0 for number in numbers], False


def similarity(original: bytes, reconstructed: list[float], float32: bool) -> float:
    """test_image_similarity's value.

    `original` holds the original's uint8 values. `reconstructed` is the other
    flattened array after `/ 255.0`, of the same length or of one element, which
    numpy broadcasts.
    """
    table = [value / 255.0 for value in range(256)]
    orig_length = math.sqrt(numpy_sum([table[value] * table[value] for value in original]))
    if float32:
        squares = [_f32(value * value) for value in reconstructed]
        recon_length = _f32(math.sqrt(numpy_sum(squares, float32=True)))
        recon_norm = [_f32(_divide(value, recon_length)) for value in reconstructed]
    else:
        squares = [value * value for value in reconstructed]
        recon_length = math.sqrt(numpy_sum(squares))
        recon_norm = [_divide(value, recon_length) for value in reconstructed]
    original_norm = [value / orig_length for value in table]
    if len(recon_norm) == 1:
        products = [original_norm[value] * recon_norm[0] for value in original]
    else:
        products = [original_norm[a] * b for a, b in zip(original, recon_norm, strict=True)]
    return numpy_sum(products)


def plan(resources: HiddenResources, seed: int) -> Plan:
    cases = resources.read_json("cases.json")
    if not isinstance(cases, dict):
        raise ValueError("hidden/cases.json is malformed")
    built = []
    for entry in cases["build"]:
        if not isinstance(entry, dict) or not isinstance(entry["forbidden_in_headers"], str):
            raise ValueError("hidden/cases.json is malformed")
        built.append(Case(entry["challenge"], {"forbidden_in_headers": entry["forbidden_in_headers"]}))
    rendered = []
    for entry in cases["render"]:
        if not isinstance(entry, dict) or not isinstance(entry["original"], str):
            raise ValueError("hidden/cases.json is malformed")
        packed = resources.read(entry["original"])
        zlib.decompress(packed)
        context: JsonValue = {"original_zlib": base64.b64encode(packed).decode("ascii")}
        rendered.append(Case(entry["challenge"], context))
    return Plan(
        artifact_contexts={"source": None},
        cases={"build": tuple(built), "render": tuple(rendered)},
    )


def judge(check_id: str, context: JsonValue, evidence: ArtifactEvidence | CaseEvidence) -> Judgment:
    if isinstance(evidence, ArtifactEvidence):
        return _source(evidence)
    if not isinstance(evidence.outcome, Observed):
        return Judgment(False, {"reason": "no observation"})
    observed = evidence.outcome.value
    if not isinstance(observed, dict) or not isinstance(context, dict):
        return Judgment(False, {"reason": "malformed"})
    built = observed["compile"]
    if not isinstance(built, dict) or built["unlink"] == "failed":
        return Judgment(False, {"reason": "Path('/app/image').unlink failed", "compile": built})
    if not _exited_cleanly(built):
        return Judgment(False, {"reason": "image.c did not compile", "compile": built})
    if check_id == "build":
        return _build(context, observed)
    if check_id == "render":
        return _render(context, observed, evidence)
    return Judgment(False, {"reason": f"unknown check {check_id}"})


def _source(evidence: ArtifactEvidence) -> Judgment:
    if len(evidence.files) != 1:
        return Judgment(False, {"reason": "malformed"})
    found = evidence.files[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        # Absent, not a regular file, over 16 MiB (which cannot compress below
        # 2,100 bytes) or not UTF-8 text without a byte-order mark.
        return Judgment(
            False, {"reason": f"/app/image.c is {found.status.value}", "detail": found.reason}
        )
    size = compressed_size(found.value.text)
    if not size < MAX_COMPRESSED:
        return Judgment(
            False, {"reason": "image.c compresses to 2,100 bytes or more", "compressed": size}
        )
    return Judgment(True, {"compressed": size})


def _exited_cleanly(ran: JsonValue) -> bool:
    """Exit status 0 and output that `text=True` decodes."""
    return (
        isinstance(ran, dict)
        and ran.get("ending") == "exited"
        and ran.get("exit_status") == 0
        and ran.get("stdout_utf8") is True
        and ran.get("stderr_utf8") is True
    )


def _build(context: dict[str, JsonValue], observed: dict[str, JsonValue]) -> Judgment:
    forbidden = context["forbidden_in_headers"]
    if not isinstance(forbidden, str):
        return Judgment(False, {"reason": "malformed context"})
    headers = _headers(observed["headers"], forbidden)
    if headers is not None:
        return Judgment(False, {"reason": headers})
    return Judgment(True, None)


def _render(
    context: dict[str, JsonValue], observed: dict[str, JsonValue], evidence: CaseEvidence
) -> Judgment:
    ran = observed.get("run")
    # Upstream's `sh -c "...; chroot /jail /image"` returns the binary's status.
    if not _exited_cleanly(ran):
        return Judgment(False, {"reason": "the binary did not exit cleanly", "run": ran})
    image = observed.get("image")
    if not isinstance(image, dict) or image["exists"] is not True:
        return Judgment(False, {"reason": "reconstructed.ppm was not generated"})
    array = image.get("array")
    if not isinstance(array, dict):
        return Judgment(False, {"reason": "the image does not decode as Pillow's PPM plugin decodes it", "error": image.get("error")})
    packed = context["original_zlib"]
    if not isinstance(packed, str):
        return Judgment(False, {"reason": "malformed context"})
    original = zlib.decompress(base64.b64decode(packed))
    values = _array(array, evidence, len(original))
    if isinstance(values, str):
        return Judgment(False, {"reason": values})
    score = similarity(original, *values)
    if not score >= THRESHOLD:
        return Judgment(False, {"reason": "images not similar enough", "similarity": score})
    return Judgment(True, {"similarity": score})


def _headers(headers: JsonValue, forbidden: str) -> str | None:
    """Why `gcc -H /app/image.c -lm` fails upstream's test_no_deps, or None."""
    if not isinstance(headers, dict) or headers["ending"] != "exited":
        return "gcc -H did not exit"
    if headers["exit_status"] != 0:
        return "gcc -H /app/image.c -lm failed"
    for name in ("stdout", "stderr"):
        output = headers[name]
        if not isinstance(output, dict):
            return "malformed"
        size, text = output["bytes"], output["text"]
        if not isinstance(size, int) or not isinstance(text, str):
            return "malformed"
        if size > OUTPUT_SHOWN:
            return f"gcc -H printed more than {OUTPUT_SHOWN} bytes on {name}"
        if output["utf8"] is not True or len(text.encode("utf-8")) != size:
            # Upstream decodes the output as strict UTF-8 and fails on anything else.
            return f"gcc -H printed bytes on {name} that are not UTF-8"
        if forbidden in text:
            return f"gcc -H mentions {forbidden} on {name}"
    return None


def _array(
    array: dict[str, JsonValue], evidence: CaseEvidence, original_count: int
) -> tuple[list[float], bool] | str:
    """The reconstructed array's scaled values, or why upstream's arithmetic fails on it."""
    typestr, shape, rest = array["typestr"], array["shape"], array["rest"]
    if not isinstance(typestr, str) or not isinstance(shape, list) or not isinstance(rest, str):
        return "malformed"
    size = item_size(typestr)
    if size is None:
        return f"array type {typestr} is not one Pillow's PPM plugin produces"
    count = 1
    for extent in shape:
        if not isinstance(extent, int):
            return "malformed"
        count *= extent
    # The flattened arrays combine only if their lengths are equal or one is 1.
    if count != original_count and count != 1:
        return f"operands could not be broadcast together: {original_count} and {count} values"
    if len(evidence.output_artifacts) != 1:
        return "malformed"
    found = evidence.output_artifacts[0]
    if found.status is not FileStatus.PRESENT or not isinstance(found.value, Text):
        return f"/array.b64 is {found.status.value}"
    try:
        stream = base64.b64decode(found.value.text + rest, validate=True)
    except (binascii.Error, ValueError):
        return "the array is not base64"
    expected = count * size
    inflater = zlib.decompressobj()
    try:
        data = inflater.decompress(stream, expected + 1)
    except zlib.error:
        return "the array is not a zlib stream"
    if len(data) != expected or not inflater.eof or inflater.unused_data:
        return f"the array is not {expected} bytes in one zlib stream"
    return scaled(typestr, data)
