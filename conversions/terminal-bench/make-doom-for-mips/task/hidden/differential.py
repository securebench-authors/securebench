"""Differential test of how the pack opens and scores the frame against upstream's test.

Run inside the baseline image, whose Pillow is 11.2.1 like the native verifier's:

    docker run --rm --network none -v <repo>:/repo:ro -v <frame dir>:/frames:ro \
      <baseline image> python3 -I -B \
      /repo/conversions/terminal-bench/make-doom-for-mips/task/hidden/differential.py \
      /repo /frames/frame.bmp /repo/conversions/upstream/terminal-bench/make-doom-for-mips/tests/reference.jpg

frame.bmp is a frame written by the upstream reference build. For every file of a
corpus weighted toward the 0.95 threshold, it prints upstream's verdict and score
(test_frame_bmp_exists and test_frame_bmp_similar_to_reference, verbatim
arithmetic) next to the pack's (evaluation/frame.py, then the Oracle's size
checks and similarity against hidden/cases.json and hidden/reference-rgb.zlib),
and whether the two agree. Both sides open the frame with the same Pillow; what
this tests is the Oracle's score, the pre-decoded reference.jpg and the way the
observation carries the pixels.
"""

import io
import json
import struct
import sys
import tempfile
import zlib
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from PIL import Image

REPO = Path(sys.argv[1])
TASK = REPO / "conversions/terminal-bench/make-doom-for-mips/task"
sys.path.insert(0, str(REPO))


def load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


frame_reader = load("frame_reader", TASK / "evaluation/frame.py")
oracle = load("oracle", TASK / "hidden/oracle.py")

REFERENCE_JPG = sys.argv[3]
CASE = json.loads((TASK / "hidden/cases.json").read_text())[0]
EXPECTED = zlib.decompress((TASK / "hidden" / CASE["reference"]).read_bytes())


def upstream(path: str) -> tuple[bool, object]:
    """test_frame_bmp_exists and test_frame_bmp_similar_to_reference, with their assertions turned into a verdict."""
    frame_path = Path(path)
    if not frame_path.exists() or frame_path.stat().st_size == 0:
        return False, "absent or empty"
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
        total_diff += abs(r1 - r2) + abs(g1 - g2) + abs(b1 - b2)
    avg_diff = total_diff / (pixel_count * 3)
    similarity = 1.0 - (avg_diff / 255.0)
    return similarity >= 0.95, similarity


def ours(path: str) -> tuple[bool, object]:
    report = frame_reader.describe(path)
    if "problem" in report:
        return False, report["problem"]
    pixels = oracle._pixels(report, CASE["width"], CASE["height"])
    if isinstance(pixels, str):
        return False, "size"
    score = oracle.similarity(pixels, EXPECTED)
    return score >= oracle.THRESHOLD, score


def bmp32(rgb: bytes, width: int, height: int, top_down: bool = True) -> bytes:
    """The BMP doomgeneric_img.c writes: 32-bit BGRX, 40-byte header."""
    rows = []
    for y in range(height):
        line = bytearray(4 * width)
        source = rgb[3 * width * y : 3 * width * (y + 1)]
        line[0::4] = source[2::3]
        line[1::4] = source[1::3]
        line[2::4] = source[0::3]
        rows.append(bytes(line))
    if not top_down:
        rows.reverse()
    body = b"".join(rows)
    info = struct.pack("<IiiHHIIiiII", 40, width, -height if top_down else height, 1, 32, 0, len(body), 0, 0, 0, 0)
    return struct.pack("<2sIHHI", b"BM", 54 + len(body), 0, 0, 54) + info + body


def saved(image: Image.Image, format: str) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=format)
    return buffer.getvalue()


def perturbed(rgb: bytes, count: int) -> bytes:
    """The first `count` channel bytes moved as far from their value as they can go."""
    changed = bytearray(rgb)
    for i in range(count):
        changed[i] = 0 if changed[i] >= 128 else 255
    return bytes(changed)


def main() -> None:
    frame = Image.open(sys.argv[2]).convert("RGB")
    rgb = frame.tobytes()
    corpus: dict[str, bytes | None] = {
        "reference frame, as written": Path(sys.argv[2]).read_bytes(),
        "reference frame, 24-bit bottom-up (Pillow)": saved(frame, "BMP"),
        "reference frame, 32-bit bottom-up": bmp32(rgb, 640, 400, top_down=False),
        "reference frame as RGBA BMP (Pillow, bit fields)": saved(frame.convert("RGBA"), "BMP"),
        "reference frame as 8-bit palette BMP (Pillow)": saved(frame.convert("P"), "BMP"),
        "reference frame as PNG named frame.bmp": saved(frame, "PNG"),
        "reference frame truncated by 1000 bytes": Path(sys.argv[2]).read_bytes()[:-1000],
        "reference frame as 641x400": saved(frame.resize((641, 400)), "BMP"),
        "reference frame as 320x200": bmp32(frame.resize((320, 200)).tobytes(), 320, 200),
        "reference frame as 5000x5000": saved(frame.resize((5000, 5000)), "BMP"),
        "text file": b"not an image\n",
        "empty file": b"",
        "no file": None,
    }
    low, high = 0, len(rgb)
    while low < high:
        middle = (low + high) // 2
        if oracle.similarity(perturbed(rgb, middle), EXPECTED) >= 0.95:
            low = middle + 1
        else:
            high = middle
    for count in range(low - 4, low + 4):
        corpus[f"perturbed, {count} bytes"] = bmp32(perturbed(rgb, count), 640, 400)
    for count in range(0, 400000, 50000):
        corpus[f"perturbed, {count} bytes"] = bmp32(perturbed(rgb, count), 640, 400)
    disagreements = 0
    with tempfile.TemporaryDirectory() as directory:
        for name, data in corpus.items():
            path = f"{directory}/frame.bmp"
            Path(path).unlink(missing_ok=True)
            if data is not None:
                Path(path).write_bytes(data)
            native, mine = upstream(path), ours(path)
            same = native[0] == mine[0] and (not native[0] or native[1] == mine[1])
            disagreements += not same
            print(f"{'agree' if same else 'DIFFER'}  {name}: upstream {native}, ours {mine}")
    print(f"{disagreements} disagreements in {len(corpus)} files")


main()
