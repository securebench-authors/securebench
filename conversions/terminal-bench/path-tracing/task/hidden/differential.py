"""Differential test of the adapter's reports and the Oracle's measures.

Upstream's verifier runs Python 3.13 with Pillow 11.2.1 and numpy 2.3.1, which it
installs at grading time. <venv> is a virtual environment of those versions
(uv 0.9.5: `uv venv -p 3.13` and `uv pip install pillow==11.2.1 numpy==2.3.1`,
which gives Python 3.13.9 with zlib 1.3.1). Six steps:

1. `corpus <original.ppm> <orig.c> <reference image.c> <dir>` in <venv> writes
   the corpus to <dir>/images, <dir>/sources and <dir>/headers.
2. `sums <dir>` in <venv> writes <dir>/sums.json: `np.sum` of float64 and
   float32 arrays of many lengths, up to the 12,960,000 values of this task.
3. `native <dir>` in <venv>, inside the baseline image with no network, runs
   upstream's code verbatim and writes <dir>/native.json: for an image,
   test_image_similarity's verdict and float (Pillow decoding, numpy
   arithmetic) and a digest of the array Pillow gives numpy; for a source,
   `len(zlib.compress(open(path).read().encode()))`; for a header source,
   test_no_deps on it as /app/image.c; for a command, whether
   `subprocess.run(..., capture_output=True, text=True)` decodes its output.
4. `observe <dir>` in the same container, on any Python 3, runs the adapter's
   own `run` and `stream` on the same header sources and commands and writes
   <dir>/observed.json.
5. `evaluate <dir>` on the stock interpreter (`python:3.12-slim`, the one the
   adapter runs on), runs the adapter's `report_image` and `decode` on every
   image and writes <dir>/evaluated/<image>.json: the observation, the Output
   Artifact's text and the array's digest. Images named `other-*` are formats
   the PPM plugin does not open; their differences are counted apart.
6. `ours <dir> <repo>` on the repository's interpreter, the one the Oracle
   runs on, computes the same through SecureBench: the Oracle's `judge` on the
   evidence of step 5 against hidden/original-rgb.zlib; the registry's text
   parser and the Oracle's `compressed_size`; the Oracle's `_headers` and
   `_exited_cleanly` on the observed streams; and `numpy_sum` on the arrays of
   step 2. It prints both sides and every disagreement.

Steps 3 and 4 run in one container, so the header sources see the same files
(`setup_headers` places the extra headers some of them include).
"""

import hashlib
import json
import os
import subprocess
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 2400, 1800
VALUES = WIDTH * HEIGHT * 3
THRESHOLD = 0.99


def ppm(magic: bytes, width: int, height: int, maxval: int, body: bytes) -> bytes:
    return magic + b"\n%d %d\n%d\n" % (width, height, maxval) + body


def pfm(rows: "np.ndarray") -> bytes:
    """A grayscale PFM of little-endian float32 values. PFM stores the bottom row
    first, so Pillow reads `rows` in their order."""
    height, width = rows.shape
    return b"Pf\n%d %d\n-1.0\n" % (width, height) + rows[::-1].astype("<f4").tobytes()


def plain(values: list[int], separator: bytes = b" ", line: bytes = b"\n") -> bytes:
    numbers = [b"%d" % v for v in values]
    rows = [separator.join(numbers[i : i + 3]) for i in range(0, len(numbers), 3)]
    return line.join(rows) + line


def lengths() -> list[int]:
    """Array lengths for the summation test: every small length, and spread larger ones."""
    found = set(range(1, 300))
    for base in (1000, 8192, 65536, 1 << 20, 1440000, 4320000, VALUES):
        found.update(base + delta for delta in (-9, -8, -1, 0, 1, 7, 8, 129))
    return sorted(length for length in found if length <= VALUES)


def sum_values(length: int) -> list[float]:
    """A deterministic array whose sums depend on the order of additions."""
    return [((index * 2654435761) % 256 / 255.0) ** 2 for index in range(length)]


def sum_values32(length: int) -> list[float]:
    """The same for float32: each value is exactly a float32 (k / 1024 squared, k < 256)."""
    return [(((index * 2654435761) % 256) / 1024.0) ** 2 for index in range(length)]


# test_no_deps cases. `extra` maps a path to the content placed there first.
HEADER_CASES: dict[str, tuple[bytes, dict[bytes, bytes]]] = {}


def header_cases(reference: bytes) -> None:
    def case(name: str, source: bytes, extra: dict[bytes, bytes] | None = None) -> None:
        HEADER_CASES[name] = (source, extra or {})

    case("reference.c", reference)
    case("no-stdlib.c", reference.replace(b"#include<stdlib.h>\n", b""))
    case("warning-directive.c", b"#warning hello\n" + reference)
    case("pragma-message.c", b'#pragma message "hello"\n' + reference)
    case("line-directive-warning.c", b'#line 1 "x.c"\n#warning hello\n' + reference)
    case("local-header.c", b'#include "scene.h"\n' + reference, {b"/app/scene.h": b"#define SCENE_HEADER 1\n"})
    case(
        "outside-header.c",
        b'#include "/usr/local/include/scene.h"\n' + reference,
        {b"/usr/local/include/scene.h": b"#define SCENE_HEADER 1\n"},
    )
    case("dotdot-system-header.c", b'#include "../usr/include/stdio.h"\n' + reference)
    case(
        "latin1-header-path.c",
        b'#include "/usr/local/include/\xe9.h"\n' + reference,
        {b"/usr/local/include/\xe9.h": b"#define LATIN_HEADER 1\n"},
    )
    case("assert-1000.c", b"#include <assert.h>\n" * 1000 + reference)
    case("does-not-compile.c", reference + b"syntax error\n")
    case("no-main.c", b"int f(void) { return 0; }\n")


# Commands whose output upstream decodes with `text=True`: the run of the
# binary, and gcc -static. 1048575 bytes put a two-byte character across the
# adapter's 1 MiB read blocks.
MIB = "head -c 1048575 /dev/zero | tr '\\0' a"
COMMANDS = {
    "ascii": "printf 'Wrote image\\n' >&2",
    "two-byte": "printf '\\303\\251\\n'",
    "latin1-stdout": "printf '\\351\\n'",
    "latin1-stderr": "printf '\\351\\n' >&2",
    "block-219": "printf '\\333\\333' >&2",
    "cut-at-end": "printf 'a\\303'",
    "surrogate": "printf '\\355\\240\\200'",
    "byte-order-mark": "printf '\\357\\273\\277x'",
    "nul": "printf 'a\\000b'",
    "across-blocks": f"{MIB}; printf '\\303\\251'",
    "bad-after-blocks": f"{MIB}; {MIB}; printf '\\377'",
}


def corpus(original_path: Path, orig_c: Path, reference_c: Path, out: Path) -> None:
    import numpy as np
    from PIL import Image

    images, sources, headers = out / "images", out / "sources", out / "headers"
    for directory in (images, sources, headers):
        directory.mkdir(parents=True, exist_ok=True)
    original = original_path.read_bytes()
    array = np.array(Image.open(original_path))
    rgb = array.tobytes()
    values = np.frombuffer(rgb, dtype=np.uint8)

    def put(name: str, data: bytes) -> None:
        (images / name).write_bytes(data)

    def save(name: str, image: "Image.Image", **options: object) -> None:
        image.save(images / name, **options)

    # PPM, as the reference and most solutions write it.
    put("original.ppm", original)
    put("p6.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, rgb))
    put("p6-max65535.ppm", ppm(b"P6", WIDTH, HEIGHT, 65535, (values.astype(">u2") * 257).tobytes()))
    put("p6-truncated.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, rgb[:-1]))
    put("black.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, bytes(VALUES)))
    put("gray.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, bytes([128]) * VALUES))
    noise = np.random.default_rng(7).integers(-40, 41, VALUES)
    noisy = np.clip(values.astype(np.int64) + noise, 0, 255).astype(np.uint8)
    put("noisy.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, noisy.tobytes()))
    put("empty.ppm", b"")

    # The PPM plugin's paths, on a 600x400 crop (its arrays are compared; the
    # verdicts fail on the size). Every plain file is over 1 MiB, so tokens and
    # comments cross the plain decoder's read blocks.
    crop = [int(v) for v in values[: 600 * 400 * 3]]
    body = plain(crop)
    first = len(b"%d" % crop[0])
    middle = body.index(b"\n", len(body) // 2) + 1
    rng = np.random.default_rng(11)
    bits = rng.integers(0, 2, (5, 13)).astype(np.uint8)
    put("ppm-p3.ppm", ppm(b"P3", 600, 400, 255, body))
    for maxval in (1, 100, 254, 256, 1000, 65535):
        scaled = [round(v * maxval / 255) for v in crop]
        size = 1 if maxval < 256 else 2
        put(f"ppm-p3-max{maxval}.ppm", ppm(b"P3", 600, 400, maxval, plain(scaled)))
        put(f"ppm-p6-max{maxval}.ppm", ppm(b"P6", 600, 400, maxval, b"".join(v.to_bytes(size, "big") for v in scaled)))
        put(f"ppm-p2-max{maxval}.ppm", ppm(b"P2", 1800, 400, maxval, plain(scaled)))
        put(f"ppm-p5-max{maxval}.ppm", ppm(b"P5", 1800, 400, maxval, b"".join(v.to_bytes(size, "big") for v in scaled)))
        put(f"ppm-pyrgba-max{maxval}.ppm", ppm(b"PyRGBA", 450, 400, maxval, b"".join(v.to_bytes(size, "big") for v in scaled)))
    put("ppm-p5-max65535-truncated.ppm", ppm(b"P5", 1800, 400, 65535, bytes(1800 * 400 * 2 - 1)))
    put("ppm-p5-max1000-truncated.ppm", ppm(b"P5", 1800, 400, 1000, bytes(1800 * 400 * 2 - 1)))
    put("ppm-p5-truncated.ppm", ppm(b"P5", 1800, 400, 255, bytes(crop[:-1])))
    put("ppm-p6-extra.ppm", ppm(b"P6", 600, 400, 255, bytes(crop) + b"trailing"))
    put("ppm-p3-crlf.ppm", ppm(b"P3", 600, 400, 255, body).replace(b"\n", b"\r\n"))
    put("ppm-p3-mixed-whitespace.ppm", b"P3\t600\x0b400\x0c255\r" + plain(crop, b"\t", b"\x0b\x0c"))
    put("ppm-p3-header-comments.ppm", b"P3\n# by me\n600 # width\n#\r400\n255\n" + body)
    put("ppm-p3-data-comments.ppm", ppm(b"P3", 600, 400, 255, body.replace(b"\n", b" # r\n")))
    put("ppm-p3-cr-comments.ppm", ppm(b"P3", 600, 400, 255, body.replace(b"\n", b"#c\r")))
    put("ppm-p3-big-comment.ppm", ppm(b"P3", 600, 400, 255, body[:middle] + b"#" + b"x" * 3_000_000 + b"\n" + body[middle:]))
    put("ppm-p3-comment-joins-token.ppm", ppm(b"P3", 600, 400, 255, b"%d#split\n%d" % divmod(crop[0], 10) + body[first:]))
    put("ppm-p3-no-final-newline.ppm", ppm(b"P3", 600, 400, 255, body.rstrip()))
    put("ppm-p3-comment-at-end.ppm", ppm(b"P3", 600, 400, 255, body + b"# end"))
    put("ppm-p3-extra.ppm", ppm(b"P3", 600, 400, 255, body + b"1 2 3\n"))
    put("ppm-p3-truncated.ppm", ppm(b"P3", 600, 400, 255, plain(crop[:-10])))
    put("ppm-p3-padded-tokens.ppm", ppm(b"P3", 600, 400, 255, b" ".join(b"+%08d" % v for v in crop) + b"\n"))
    put("ppm-p3-underscore.ppm", ppm(b"P3", 600, 400, 255, b"1_5 " + body[first + 1 :]))
    put("ppm-p3-long-token.ppm", ppm(b"P3", 600, 400, 255, b"00000000%03d" % crop[0] + body[first:]))
    put("ppm-p3-over-maxval.ppm", ppm(b"P3", 600, 400, 255, b"256" + body[first:]))
    put("ppm-p3-negative.ppm", ppm(b"P3", 600, 400, 255, b"-1" + body[first:]))
    put("ppm-p3-not-number.ppm", ppm(b"P3", 600, 400, 255, b"0x9f" + body[first:]))
    put("ppm-p1.ppm", b"P1\n13 5\n" + b"\n".join(b" ".join(b"%d" % v for v in row) for row in bits) + b"\n")
    put("ppm-p1-no-spaces.ppm", b"P1\n13 5\n" + b"".join(b"%d" % v for v in bits.flatten()))
    put("ppm-p1-comments.ppm", b"P1\n# c\n13 5\n#x\r" + b" # y\n".join(b"%d" % v for v in bits.flatten()))
    put("ppm-p1-bad-token.ppm", b"P1\n2 1\n0 2\n")
    put("ppm-p1-truncated.ppm", b"P1\n13 5\n0101\n")
    put("ppm-p4.ppm", b"P4\n13 5\n" + np.packbits(bits, axis=1).tobytes())
    put("ppm-p4-truncated.ppm", b"P4\n13 5\n" + np.packbits(bits, axis=1).tobytes()[:-1])
    small_floats = (np.array(crop[: 1800 * 40], dtype=np.float32) / np.float32(255)).reshape(40, 1800)
    put("ppm-pf.ppm", pfm(small_floats))
    put("ppm-pf-big-endian.ppm", b"Pf\n1800 40\n2.5\n" + small_floats[::-1].astype(">f4").tobytes())
    put("ppm-pf-scale0.ppm", b"Pf\n1800 40\n0\n" + small_floats.astype("<f4").tobytes())
    put("ppm-pf-scale-nan.ppm", b"Pf\n1800 40\nnan\n" + small_floats.astype("<f4").tobytes())
    put("ppm-pf-truncated.ppm", pfm(small_floats)[:-1])
    put("ppm-pyp.ppm", ppm(b"PyP", 1800, 400, 255, bytes(crop)))
    put("ppm-pycmyk.ppm", ppm(b"PyCMYK", 450, 400, 255, bytes(crop)))
    put("ppm-p0cmyk.ppm", ppm(b"P0CMYK", 450, 400, 255, bytes(crop)))
    put("ppm-bad-magic.ppm", ppm(b"Pyx", 600, 400, 255, bytes(crop)))
    put("ppm-header-long-token.ppm", b"P3\n0000000600 400\n255\n" + body)
    put("ppm-header-too-long-token.ppm", b"P3\n00000000600 400\n255\n" + body)
    put("ppm-header-maxval0.ppm", ppm(b"P3", 600, 400, 0, body))
    put("ppm-header-maxval65536.ppm", ppm(b"P3", 600, 400, 65536, body))
    put("ppm-header-width0.ppm", ppm(b"P3", 0, 400, 255, body))
    put("ppm-header-negative.ppm", ppm(b"P3", -600, 400, 255, body))
    put("ppm-header-eof.ppm", b"P3\n600 400\n")
    put("ppm-one-byte.ppm", b"P")
    put("other-p7-thumbnail.ppm", b"P7 332\n#END_OF_COMMENTS\n2 2 255\n\x00\x01\x02\x03")

    # Shapes: numpy flattens both arrays and broadcasts a one-element one.
    put("one-pixel-gray.ppm", b"P2\n1 1\n255\n255\n")
    put("one-pixel-black.ppm", b"P2\n1 1\n255\n0\n")
    put("one-pixel-bit.ppm", b"P1\n1 1\n0\n")
    put("one-pixel-rgb.ppm", b"P3\n1 1\n255\n255 255 255\n")
    put("one-pixel-float.ppm", pfm(np.array([[0.5]], dtype="<f4")))
    put("gray-7200x1800.ppm", ppm(b"P5", 3 * WIDTH, HEIGHT, 255, rgb))
    put("rgb-1800x2400.ppm", ppm(b"P6", HEIGHT, WIDTH, 255, rgb))
    put("rgb-800x600.ppm", ppm(b"P6", 800, 600, 255, rgb[: 800 * 600 * 3]))
    put("rgb-2401x1800.ppm", ppm(b"P6", WIDTH + 1, HEIGHT, 255, rgb + rgb[: HEIGHT * 3]))

    # Other array types: bool, int32, uint16, float32.
    save("bits-7200x1800.ppm", Image.fromarray(values.reshape(HEIGHT, 3 * WIDTH) >= 128), format="PPM")
    put("gray16-7200x1800.ppm", ppm(b"P5", 3 * WIDTH, HEIGHT, 65535, (values.astype(">u2") * 257).tobytes()))
    plain1000 = b" ".join(b"%d" % v for v in np.round(values.astype(np.float64) * 1000 / 255).astype(int))
    put("gray1000-7200x1800.ppm", ppm(b"P2", 3 * WIDTH, HEIGHT, 1000, plain1000 + b"\n"))
    floats = (values.astype(np.float32) / np.float32(255)).astype("<f4")
    put("float-7200x1800.ppm", pfm(floats.reshape(HEIGHT, 3 * WIDTH)))
    put("float-tiny.ppm", pfm(np.full((HEIGHT, 3 * WIDTH), 1e-30, dtype="<f4")))
    with_inf = floats.copy()
    with_inf[12345] = np.inf
    put("float-inf.ppm", pfm(with_inf.reshape(HEIGHT, 3 * WIDTH)))
    with_nan = floats.copy()
    with_nan[12345] = np.nan
    put("float-nan.ppm", pfm(with_nan.reshape(HEIGHT, 3 * WIDTH)))
    save("other-tiff-float.ppm", Image.fromarray(floats.reshape(HEIGHT, 3 * WIDTH), mode="F"), format="TIFF")
    signed = values.astype(np.int32) * 8388608 - (1 << 30)
    save("other-tiff-int32.ppm", Image.fromarray(signed.reshape(HEIGHT, 3 * WIDTH), mode="I"), format="TIFF")
    save("other-png-gray16.ppm", Image.fromarray((values.astype(np.uint16) * 257).reshape(HEIGHT, 3 * WIDTH)), format="PNG")

    # Other formats Pillow opens whatever the file is called; the adapter
    # decodes only what Pillow's PPM plugin opens (fidelity changes).
    image = Image.open(original_path)
    save("other-png-content.ppm", image, format="PNG")
    save("other-png-palette.ppm", image.quantize(256), format="PNG")
    save("other-png-rgba-1800x1800.ppm", Image.fromarray(values.reshape(HEIGHT, HEIGHT, 4), mode="RGBA"), format="PNG")
    save("other-png-la-3600x1800.ppm", Image.fromarray(values.reshape(HEIGHT, 3600, 2), mode="LA"), format="PNG")
    save("other-jpeg-content.ppm", image, format="JPEG", quality=95)
    save("other-bmp-content.ppm", image, format="BMP")
    save("other-tiff-cmyk.ppm", image.convert("CMYK"), format="TIFF")
    put("other-png-truncated.ppm", (images / "other-png-content.ppm").read_bytes()[:50000])

    def score(data: np.ndarray) -> float:
        a = values.flatten() / 255.0
        b = data.flatten() / 255.0
        a, b = a / np.sqrt(np.sum(a * a)), b / np.sqrt(np.sum(b * b))
        return float(np.sum(a * b))

    def straddle(darkened, write) -> None:
        """Darken a growing prefix until upstream's similarity crosses the threshold;
        keep the files on both sides of it."""
        low, high = 0, VALUES
        while high - low > 1:
            middle = (low + high) // 2
            low, high = (middle, high) if score(darkened(middle)) >= THRESHOLD else (low, middle)
        for count in (low - 3000, low - 1, low, high, high + 1, high + 3000):
            write(count, darkened(count))

    def darkened8(count: int) -> np.ndarray:
        result = values.copy()
        result[:count] //= 2
        return result

    def darkened32(count: int) -> np.ndarray:
        result = floats.copy()
        result[:count] *= np.float32(0.5)
        return result

    straddle(darkened8, lambda count, data: put(f"threshold-{count}.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, data.tobytes())))
    straddle(darkened32, lambda count, data: put(f"threshold-float-{count}.ppm", pfm(data.reshape(HEIGHT, 3 * WIDTH))))

    def source(name: str, data: bytes) -> None:
        (sources / name).write_bytes(data)

    orig = orig_c.read_bytes()
    reference = reference_c.read_bytes()
    source("orig.c", orig)
    source("reference.c", reference)
    sizes = {length: len(zlib.compress(orig[:length])) for length in range(1, len(orig) + 1)}
    near = sorted(length for length, size in sizes.items() if 2096 <= size <= 2104)
    for length in near[:: max(1, len(near) // 12)]:
        prefix = orig[:length]
        source(f"prefix-{length}.c", prefix)
        source(f"prefix-{length}-crlf.c", prefix.replace(b"\n", b"\r\n"))
        source(f"prefix-{length}-cr.c", prefix.replace(b"\n", b"\r"))
        source(f"prefix-{length}-crcrlf.c", prefix.replace(b"\n", b"\r\r\n"))
        source(f"prefix-{length}-utf8.c", prefix.replace(b"// ", "// é ".encode()))
    source("bom.c", b"\xef\xbb\xbf" + reference)
    source("invalid-utf8.c", reference + b"// \xff\n")
    source("nul.c", reference + b"// \x00\n")

    header_cases(reference)
    for name, (data, _) in HEADER_CASES.items():
        (headers / name).write_bytes(data)


def sums(directory: Path) -> None:
    import numpy as np

    results = {
        "float64": {
            str(length): float(np.sum(np.array(sum_values(length), dtype=np.float64)))
            for length in lengths()
        },
        "float32": {
            str(length): float(np.sum(np.array(sum_values32(length), dtype=np.float32)))
            for length in lengths()
        },
    }
    (directory / "sums.json").write_text(json.dumps(results))
    print("wrote", directory / "sums.json")


def setup_headers(name: str, reference: bytes) -> bytes:
    """Place the case's extra files and its source as /app/image.c; return the source."""
    header_cases(reference)
    source, extra = HEADER_CASES[name]
    for path, content in extra.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(content)
    Path("/app/image.c").write_bytes(source)
    return source


def digest(interface: dict[str, object]) -> list[object]:
    return [list(interface["shape"]), interface["typestr"], hashlib.sha256(interface["data"]).hexdigest()]


def native(directory: Path) -> None:
    import locale

    import numpy as np
    from PIL import Image

    original_path = directory / "images" / "original.ppm"
    results: dict[str, object] = {
        "encoding": locale.getpreferredencoding(False),
        "images": {},
        "arrays": {},
        "sources": {},
        "headers": {},
        "commands": {},
    }
    for path in sorted((directory / "images").iterdir()):
        try:
            # test_image_similarity, verbatim from `original = ...` to the assertion.
            original = Image.open(original_path)
            reconstructed = Image.open(path)
            original_array = np.array(original).flatten() / 255.0
            reconstructed_array = np.array(reconstructed).flatten() / 255.0
            orig_length = np.sqrt(np.sum(original_array * original_array))
            recon_length = np.sqrt(np.sum(reconstructed_array * reconstructed_array))
            original_norm = original_array / orig_length
            reconstructed_norm = reconstructed_array / recon_length
            similarity = np.sum(original_norm * reconstructed_norm)
            results["images"][path.name] = [bool(similarity >= THRESHOLD), float(similarity)]
        except Exception as error:
            results["images"][path.name] = [False, type(error).__name__]
        try:
            results["arrays"][path.name] = digest(Image.open(path).__array_interface__)
        except Exception as error:
            results["arrays"][path.name] = type(error).__name__
    for path in sorted((directory / "sources").iterdir()):
        try:
            size = len(zlib.compress(open(path).read().encode()))
            results["sources"][path.name] = [size < 2100, size]
        except Exception as error:
            results["sources"][path.name] = [False, type(error).__name__]
    reference = (directory / "sources" / "reference.c").read_bytes()
    for path in sorted((directory / "headers").iterdir()):
        setup_headers(path.name, reference)
        try:
            # test_no_deps, verbatim.
            result = subprocess.run(
                ["gcc", "-H", "/app/image.c", "-lm"],
                capture_output=True,
                text=True,
            )
            assert result.returncode == 0, f"Compilation failed: {result.stderr}"
            assert "/app/" not in result.stderr and "/app/" not in result.stdout
            results["headers"][path.name] = [True, "passed"]
        except Exception as error:
            results["headers"][path.name] = [False, type(error).__name__]
    for name, command in COMMANDS.items():
        try:
            subprocess.run(["sh", "-c", command], capture_output=True, text=True)
            results["commands"][name] = [True, "decoded"]
        except Exception as error:
            results["commands"][name] = [False, type(error).__name__]
    (directory / "native.json").write_text(json.dumps(results, indent=1))
    print("wrote", directory / "native.json")


def adapter_namespace() -> dict[str, object]:
    namespace: dict[str, object] = {}
    task = Path(__file__).resolve().parent.parent
    exec((task / "evaluation/adapter.py").read_text().rsplit("\nmain()", 1)[0], namespace)
    return namespace


def observe(directory: Path) -> None:
    adapter = adapter_namespace()
    reference = (directory / "sources" / "reference.c").read_bytes()
    observed: dict[str, object] = {"headers": {}, "commands": {}}
    for path in sorted((directory / "headers").iterdir()):
        setup_headers(path.name, reference)
        result = adapter["run"]([adapter["GCC"], "-H", "/app/image.c", "-lm"], "/app", 120)
        observed["headers"][path.name] = {
            "ending": result["ending"],
            "exit_status": result["exit_status"],
            "stdout": adapter["stream"](result["out"]),
            "stderr": adapter["stream"](result["err"]),
        }
    for name, command in COMMANDS.items():
        observed["commands"][name] = adapter["ended"](adapter["run"](["sh", "-c", command], "/", 120))
    (directory / "observed.json").write_text(json.dumps(observed))
    print("wrote", directory / "observed.json")


def evaluate(directory: Path) -> None:
    adapter = adapter_namespace()
    out = directory / "evaluated"
    out.mkdir(exist_ok=True)
    for path in sorted((directory / "images").iterdir()):
        adapter["IMAGE"] = str(path)
        try:
            image, head = adapter["report_image"]()
        except adapter["TooLarge"] as error:
            image, head = {"too_large": error.args[0]}, None
        try:
            with open(path, "rb") as fp:
                typestr, shape, data = adapter["decode"](fp)
            array = [shape, typestr, hashlib.sha256(data).hexdigest() if data is not None else None]
        except adapter["Problem"] as problem:
            array = problem.args[0]
        (out / f"{path.name}.json").write_text(json.dumps({"image": image, "head": head, "array": array}))
    print("wrote", out)


def report(kind: str, name: str, same: bool, native: list[object], ours: list[object]) -> None:
    label = "same" if same else "DIFF"
    upstream = f"native {native[0]!s:5} {native[1]!s:24}"
    print(f"{label:4} {kind:7} {name:32} {upstream} ours {ours[0]!s:5} {ours[1]}")


def ours(directory: Path, repo: Path) -> None:
    import base64
    from importlib.util import module_from_spec, spec_from_file_location

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    from securebench.core.errors import Rejected
    from securebench.core.evidence import (
        CaseEvidence,
        Ending,
        FileEvidence,
        FileStatus,
        HostFacts,
        Observed,
        Text,
    )
    from securebench.core.task import Parser
    from securebench.evidence.parsers import parse

    task = Path(__file__).resolve().parent.parent
    spec = spec_from_file_location("oracle", task / "hidden/oracle.py")
    assert spec is not None and spec.loader is not None
    oracle = module_from_spec(spec)
    spec.loader.exec_module(oracle)
    cases = json.loads((task / "hidden/cases.json").read_text())
    packed = (task / "hidden" / cases["render"][0]["original"]).read_bytes()
    context = {"original_zlib": base64.b64encode(packed).decode("ascii")}
    forbidden = cases["build"][0]["forbidden_in_headers"]
    upstream = json.loads((directory / "native.json").read_text())
    print("native default encoding:", upstream["encoding"])
    stored = [[HEIGHT, WIDTH, 3], "|u1", hashlib.sha256(zlib.decompress(packed)).hexdigest()]
    print("hidden original equals native np.array of original.ppm:", stored == upstream["arrays"]["original.ppm"])
    passing = {"ending": "exited", "exit_status": 0, "stdout_utf8": True, "stderr_utf8": True}
    disagreements = 0
    # Files the PPM plugin does not open ("other-*"): the adapter fails them
    # by design (fidelity changes), so they are counted apart.
    other_arrays = other_verdicts = 0

    for name, (native_verdict, native_value) in upstream["images"].items():
        evaluated = json.loads((directory / "evaluated" / f"{name}.json").read_text())
        other = name.startswith("other-")
        ours_array, native_array = evaluated["array"], upstream["arrays"][name]
        # Both sides fail to open the file: the exception names differ by design.
        if ours_array != native_array and not (isinstance(ours_array, str) and isinstance(native_array, str)):
            if other:
                other_arrays += 1
            else:
                disagreements += 1
            print("DIFF array", name, ours_array, native_array)
        if "too_large" in evaluated["image"]:
            verdict, value = False, f"array_too_large ({evaluated['image']['too_large']})"
        else:
            head = evaluated["head"]
            artifacts: tuple[FileEvidence, ...] = ()
            if head is not None:
                artifacts = (
                    FileEvidence("/array.b64", FileStatus.PRESENT, Text(head, (head,)), len(head), None, None),
                )
            observation = {
                "compile": {"unlink": "missing", **passing, "stderr_start": ""},
                "run": passing,
                "image": evaluated["image"],
            }
            evidence = CaseEvidence(
                "render", 0, "", HostFacts(Ending.RETURNED, 0, 0.0), Observed(observation), artifacts
            )
            judgment = oracle.judge("render", context, evidence)
            diagnostic = judgment.diagnostic
            value = diagnostic.get("similarity", diagnostic.get("error") or diagnostic.get("reason"))
            verdict = judgment.passed
        native_float = isinstance(native_value, float)
        same = verdict == native_verdict and (
            not native_float or value == native_value or (value != value and native_value != native_value)
        )
        if other:
            other_verdicts += verdict != native_verdict
        else:
            disagreements += not same
        report("image", name, same, [native_verdict, native_value], [verdict, value])

    for name, (native_verdict, native_value) in upstream["sources"].items():
        data = (directory / "sources" / name).read_bytes()
        try:
            text = parse(Parser.TEXT, data)
            value = oracle.compressed_size(text.text)
            verdict = value < oracle.MAX_COMPRESSED
        except Rejected as error:
            verdict, value = False, f"unparsable ({error.reason})"
        same = verdict == native_verdict and value == native_value
        disagreements += verdict != native_verdict
        report("source", name, same, [native_verdict, native_value], [verdict, value])

    observed = json.loads((directory / "observed.json").read_text())
    for name, (native_verdict, native_value) in upstream["headers"].items():
        reason = oracle._headers(observed["headers"][name], forbidden)
        verdict = reason is None
        disagreements += verdict != native_verdict
        report("header", name, verdict == native_verdict, [native_verdict, native_value],
               [verdict, reason or "passed"])
    for name, (native_verdict, native_value) in upstream["commands"].items():
        verdict = oracle._exited_cleanly(observed["commands"][name])
        disagreements += verdict != native_verdict
        report("command", name, verdict == native_verdict, [native_verdict, native_value],
               [verdict, observed["commands"][name]])

    expected = json.loads((directory / "sums.json").read_text())
    for kind, generate in (("float64", sum_values), ("float32", sum_values32)):
        mismatched = [
            length
            for length in expected[kind]
            if oracle.numpy_sum(generate(int(length)), float32=kind == "float32") != expected[kind][length]
        ]
        print(f"numpy_sum equals np.sum ({kind}) on {len(expected[kind]) - len(mismatched)} of {len(expected[kind])} lengths")
        disagreements += len(mismatched)
    print(f"other formats: {other_arrays} arrays and {other_verdicts} verdicts differ")
    print("disagreements:", disagreements)


def main() -> None:
    command = sys.argv[1]
    if command == "corpus":
        corpus(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
    elif command == "sums":
        sums(Path(sys.argv[2]))
    elif command == "native":
        native(Path(sys.argv[2]))
    elif command == "observe":
        observe(Path(sys.argv[2]))
    elif command == "evaluate":
        evaluate(Path(sys.argv[2]))
    elif command == "ours":
        ours(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(f"unknown command {command}")


main()
