"""Differential test of the adapter's frame reading and the Oracle's score.

Run inside the baseline image, whose Pillow is 11.2.1 like the native verifier's:

    docker run --rm --network none --memory 2g -v <repo>:/repo:ro -v <frame dir>:/frames:ro \
      <baseline image> python3 -B \
      /repo/conversions/terminal-bench/make-mips-interpreter/task/hidden/differential.py /repo \
      /frames/frame.bmp \
      /repo/conversions/upstream/terminal-bench/make-mips-interpreter/tests/reference.jpg

frame.bmp is a frame written by the upstream reference vm.js. For every file of a
corpus weighted toward the 0.95 threshold, it prints upstream's verdict and score
(test_frame_bmp_similar_to_reference, verbatim arithmetic) next to ours (the
adapter's read_frame, which runs evaluation/frame.py, then the Oracle's judge on
case 0 of its plan), and whether the two agree.
"""

import base64
import json
import struct
import sys
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(sys.argv[1])
TASK = REPO / "conversions/terminal-bench/make-mips-interpreter/task"
sys.path.insert(0, str(REPO))

from securebench.core.evidence import (  # noqa: E402
    CaseEvidence,
    Ending,
    FileEvidence,
    FileStatus,
    HostFacts,
    Observed,
)

adapter_source = (TASK / "evaluation/adapter.py").read_text().rsplit("\nmain()", 1)[0]
adapter: dict[str, object] = {}
exec(adapter_source, adapter)  # the adapter's functions, without running its main

from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

spec = spec_from_file_location("oracle", TASK / "hidden/oracle.py")
assert spec is not None and spec.loader is not None
oracle = module_from_spec(spec)
spec.loader.exec_module(oracle)


class Hidden:
    def read(self, relative_path: str) -> bytes:
        return (TASK / "hidden" / relative_path).read_bytes()

    def read_json(self, relative_path: str) -> object:
        return json.loads(self.read(relative_path))


CONTEXT = oracle.plan(Hidden(), 0).cases["doom"][0].context
REFERENCE_JPG = sys.argv[3]
JPEG_RGB = Image.open(REFERENCE_JPG).convert("RGB").tobytes()
TEXT = b"I_InitGraphics: DOOM screen size: w x h: 320 x 200\n"


def upstream(path: str) -> tuple[bool, object]:
    """Upstream test_frame_bmp_exists and test_frame_bmp_similar_to_reference, as a verdict."""
    frame_path = Path(path)
    if not frame_path.exists() or frame_path.stat().st_size == 0:
        return False, "missing or empty"
    try:
        frame_img = Image.open(frame_path).convert("RGB")
    except Exception as error:
        return False, type(error).__name__
    ref_img = Image.open(REFERENCE_JPG).convert("RGB")
    if frame_img.size != ref_img.size:
        return False, "size"
    frame_pixels = list(frame_img.getdata())
    ref_pixels = list(ref_img.getdata())
    total_diff = 0
    pixel_count = len(frame_pixels)
    for i in range(pixel_count):
        r1, g1, b1 = frame_pixels[i]
        r2, g2, b2 = ref_pixels[i]
        diff = abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
        total_diff += diff
    avg_diff = total_diff / (pixel_count * 3)
    max_possible_diff = 255.0
    similarity = 1.0 - (avg_diff / max_possible_diff)
    threshold = 0.95
    return similarity >= threshold, similarity


def ours(path: str) -> tuple[bool, object]:
    adapter["FRAME"] = Path(path)
    adapter["DECODER"] = ["/usr/local/bin/python3", "-I", str(TASK / "evaluation/frame.py"), path]
    frame = adapter["read_frame"]()  # type: ignore[operator]
    observation: dict[str, object] = {"frame_appeared": True}
    output = FileEvidence(
        "/srv/vm-output.json",
        FileStatus.PRESENT,
        {"output_b64": base64.b64encode(TEXT).decode("ascii")},
        None,
        None,
        None,
    )
    if frame is None:
        observation["frame_problem"] = "absent"
    elif isinstance(frame, str):
        observation["frame_problem"] = frame
    else:
        observation["frame"] = frame
    evidence = CaseEvidence(
        "doom", 0, "", HostFacts(Ending.RETURNED, 0, 1.0), Observed(observation), (output,)
    )
    judgment = oracle.judge("doom", CONTEXT, evidence)
    diagnostic = judgment.diagnostic if isinstance(judgment.diagnostic, dict) else {}
    return judgment.passed, diagnostic.get("similarity", diagnostic.get("reason"))


def doomgeneric_bmp(rgb: bytes, width: int, height: int) -> bytes:
    """A frame in the format doomgeneric_img.c writes: 32-bit BI_RGB, top-down."""
    pixels = bytearray(4 * width * height)
    pixels[0::4] = rgb[2::3]
    pixels[1::4] = rgb[1::3]
    pixels[2::4] = rgb[0::3]
    header = struct.pack("<2sIII", b"BM", 54 + len(pixels), 0, 54)
    header += struct.pack("<IiiHHIIiiII", 40, width, -height, 1, 32, 0, len(pixels), 0, 0, 0, 0)
    return header + bytes(pixels)


def perturbed(rgb: bytes, extra: int) -> bytes:
    """rgb with `extra` units of absolute difference to the JPEG added, channel by channel."""
    out = bytearray(rgb)
    for i in range(len(out)):
        if extra == 0:
            break
        value, target = out[i], JPEG_RGB[i]
        room = 255 - value if value >= target else value
        step = min(room, 64, extra)
        out[i] = value + step if value >= target else value - step
        extra -= step
    if extra:
        raise SystemExit("could not perturb enough")
    return bytes(out)


def main() -> None:
    frame_path = sys.argv[2]
    base = Image.open(frame_path).convert("RGB")
    rgb = base.tobytes()
    width, height = base.size
    base_diff = sum(abs(a - b) for a, b in zip(rgb, JPEG_RGB, strict=True))
    boundary = len(JPEG_RGB) * 255 // 20  # total difference at a similarity of exactly 0.95
    corpus: list[tuple[str, bytes]] = [
        ("reference vm.js frame (32-bit top-down)", Path(frame_path).read_bytes())
    ]
    for label, fmt, mode in (
        ("same frame, 24-bit bottom-up BMP saved by Pillow", "BMP", "RGB"),
        ("same frame as PNG content", "PNG", "RGB"),
        ("same frame, 8-bit palette BMP saved by Pillow", "BMP", "P"),
    ):
        image = base if mode == "RGB" else base.quantize(256)
        with tempfile.SpooledTemporaryFile() as handle:
            image.save(handle, fmt)
            handle.seek(0)
            corpus.append((label, handle.read()))
    for delta in (-1000, -100, -10, -2, -1, 0, 1, 2, 10, 100, 1000):
        target = boundary + delta
        corpus.append(
            (
                f"frame perturbed to total difference {target} (boundary {delta:+d})",
                doomgeneric_bmp(perturbed(rgb, target - base_diff), width, height),
            )
        )
    for extra in (200000, 2000000, 8000000):
        corpus.append(
            (f"frame perturbed by {extra}", doomgeneric_bmp(perturbed(rgb, extra), width, height))
        )
    raw = Path(frame_path).read_bytes()
    corpus.append(("frame truncated by 1000 bytes", raw[:-1000]))
    corpus.append(("empty file", b""))
    small = base.resize((320, 200))
    corpus.append(("320x200 frame", doomgeneric_bmp(small.tobytes(), 320, 200)))
    corpus.append(("not an image", b"BM" + b"\0" * 100))
    disagreements = 0
    with tempfile.TemporaryDirectory() as directory:
        for label, content in corpus:
            path = str(Path(directory) / "frame.bmp")
            Path(path).write_bytes(content)
            native, mine = upstream(path), ours(path)
            same = native[0] == mine[0] and (
                not isinstance(native[1], float) or native[1] == mine[1]
            )
            disagreements += not same
            print(f"{label}: upstream {native}, ours {mine}, {'agree' if same else 'DISAGREE'}")
    print(f"{len(corpus)} files, {disagreements} disagreements")


main()
