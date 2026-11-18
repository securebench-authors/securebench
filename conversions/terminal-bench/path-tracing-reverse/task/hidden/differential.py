"""Differential test of the adapter's PPM decoding and the Oracle's measures.

Upstream's verifier runs Python 3.13 with Pillow 11.2.1 and numpy 2.3.1, which it
installs at grading time. The adapter replaces Pillow's PPM plugin and
`np.array`, and the Oracle replaces numpy's arithmetic and the verifier's zlib.
Three steps, each in a container with a memory limit and no network:

1. `corpus <original.ppm> <orig.c> <reference mystery.c> <dir>`, with Pillow
   11.2.1 and numpy 2.3.1, writes the corpus to <dir>/images, <dir>/sources and
   <dir>/sums. Images rendered by other programs (for example the mutants) can
   be added to <dir>/images by hand.
2. `native <dir>`, with Python 3.13, Pillow 11.2.1 and numpy 2.3.1, runs
   upstream's code verbatim on every file and writes <dir>/native.json: for an
   image, test_image_similarity's verdict and float; for a source,
   `len(zlib.compress(open(path).read().encode()))`; for each float32 array in
   sums, `np.sum` as an exact hex float.
3. `ours <dir> <repo>`, on Python 3.12 (the stock interpreter the adapter runs
   on; the Oracle's code is the same on the host's), opens each image as the
   adapter does and runs `decode`, then the Oracle's `judge` on the observation
   it would send. For each source it runs the registry's text parser and
   `compressed_size`, and for each array the Oracle's `pairwise_sum` with
   float32 rounding. It prints both sides and every disagreement.
"""

import json
import struct
import sys
import zlib
from pathlib import Path

WIDTH, HEIGHT = 800, 600


def ppm(magic: bytes, width: int, height: int, maxval: int, body: bytes) -> bytes:
    return magic + b"\n%d %d\n%d\n" % (width, height, maxval) + body


def plain(values: list[int], separator: bytes = b" ", line: bytes = b"\n") -> bytes:
    rows = [separator.join(b"%d" % v for v in values[i : i + 3]) for i in range(0, len(values), 3)]
    return line.join(rows) + line


def pfm(width: int, height: int, scale: bytes, floats: list[float], little: bool) -> bytes:
    """Rows bottom first, as Pfm stores them."""
    order = "<" if little else ">"
    rows = [floats[y * width : (y + 1) * width] for y in range(height)]
    body = b"".join(struct.pack(f"{order}{width}f", *row) for row in reversed(rows))
    return b"Pf\n%d %d\n%s\n" % (width, height, scale) + body


def corpus(original_path: Path, orig_c: Path, reference_c: Path, out: Path) -> None:
    import numpy as np
    from PIL import Image

    images, sources, sums = out / "images", out / "sources", out / "sums"
    for directory in (images, sources, sums):
        directory.mkdir(parents=True, exist_ok=True)
    original = original_path.read_bytes()
    rgb = bytes(np.array(Image.open(original_path)).flatten())
    values = list(rgb)
    count = len(values)

    def put(name: str, data: bytes) -> None:
        (images / name).write_bytes(data)

    # RGB files as the original writes them, and the edge cases of the plain decoder.
    put("original.ppm", original)
    put("p6.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, rgb))
    put("p6-extra.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, rgb + b"trailing"))
    put("p6-truncated.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, rgb[:-1]))
    for maxval in (1, 100, 254, 256, 1000, 65535):
        scaled = [round(v * maxval / 255) for v in values]
        put(f"p3-max{maxval}.ppm", ppm(b"P3", WIDTH, HEIGHT, maxval, plain(scaled)))
        size = 1 if maxval < 256 else 2
        put(
            f"p6-max{maxval}.ppm",
            ppm(b"P6", WIDTH, HEIGHT, maxval, b"".join(v.to_bytes(size, "big") for v in scaled)),
        )
    put("p3-crlf.ppm", original.replace(b"\n", b"\r\n"))
    put("p3-mixed-whitespace.ppm", b"P3\t800\x0b600\x0c255\r" + plain(values, b"\t", b"\x0b\x0c"))
    put("p3-header-comments.ppm", b"P3\n# by me\n800 # width\n#\r600\n255\n" + plain(values))
    body = plain(values)
    first = len(b"%d" % values[0])
    put("p3-data-comments.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, body.replace(b"\n", b" # row\n")))
    put("p3-cr-comments.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, body.replace(b"\n", b"#c\r")))
    middle = body.index(b"\n", len(body) // 2) + 1
    put(
        "p3-big-comment.ppm",
        ppm(
            b"P3",
            WIDTH,
            HEIGHT,
            255,
            body[:middle] + b"#" + b"x" * 3_000_000 + b"\n" + body[middle:],
        ),
    )
    put(
        "p3-comment-joins-token.ppm",
        ppm(b"P3", WIDTH, HEIGHT, 255, b"%d#split\n%d" % divmod(values[0], 10) + body[first:]),
    )
    put("p3-no-final-newline.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, body.rstrip()))
    put("p3-comment-at-end.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, body + b"# end without newline"))
    put("p3-extra.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, body + b"1 2 3\n"))
    put("p3-truncated.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, plain(values[:-10])))
    put(
        "p3-signs-zeros.ppm",
        ppm(b"P3", WIDTH, HEIGHT, 255, b" ".join(b"+%04d" % v for v in values) + b"\n"),
    )
    put("p3-underscore.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, b"2_55 " + body[first + 1 :]))
    put(
        "p3-long-token.ppm",
        ppm(b"P3", WIDTH, HEIGHT, 255, b"00000000%03d" % values[0] + body[first:]),
    )
    put(
        "p3-ten-char-token.ppm",
        ppm(b"P3", WIDTH, HEIGHT, 255, b"0000000%03d" % values[0] + body[first:]),
    )
    put("p3-over-maxval.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, b"256" + body[first:]))
    put("p3-negative.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, b"-1" + body[first:]))
    put("p3-minus-zero.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, b"-0" + body[first:]))
    put("p3-not-number.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, b"0x9f" + body[first:]))
    put("header-long-token.ppm", b"P3\n00000000800 600\n255\n" + body)
    put("header-maxval0.ppm", ppm(b"P3", WIDTH, HEIGHT, 0, body))
    put("header-maxval65536.ppm", ppm(b"P3", WIDTH, HEIGHT, 65536, body))
    put("header-width0.ppm", ppm(b"P3", 0, HEIGHT, 255, body))
    put("header-no-space.ppm", b"P3800 600\n255\n" + body)
    put("header-eof.ppm", b"P3\n800 600\n")
    put(
        "header-p7.ppm",
        b"P7\nWIDTH 1\nHEIGHT 1\nDEPTH 3\nMAXVAL 255\nTUPLTYPE RGB\nENDHDR\n\xff\xff\xff",
    )
    put("empty.ppm", b"")
    put("one-byte.ppm", b"P")
    put("black.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, plain([0] * count)))
    put("gray.ppm", ppm(b"P3", WIDTH, HEIGHT, 255, plain([128] * count)))

    # Other shapes of the same 1,440,000 values, and single values numpy broadcasts.
    put("rgb-600x800.ppm", ppm(b"P6", HEIGHT, WIDTH, 255, rgb))
    put("rgb-1200x400-plain.ppm", ppm(b"P3", 1200, 400, 255, body))
    put("rgb-640x480.ppm", ppm(b"P6", 640, 480, 255, rgb[: 640 * 480 * 3]))
    put("gray-2400x600-p5.ppm", ppm(b"P5", 2400, HEIGHT, 255, rgb))
    put("gray-2400x600-p2.ppm", ppm(b"P2", 2400, HEIGHT, 255, body))
    put(
        "gray-2400x600-p5-max100.ppm",
        ppm(b"P5", 2400, HEIGHT, 100, bytes(round(v * 100 / 255) for v in values)),
    )
    wide = [v * 257 for v in values]
    put("gray-2400x600-p2-max65535.ppm", ppm(b"P2", 2400, HEIGHT, 65535, plain(wide)))
    put(
        "gray-2400x600-p5-max65535.ppm",
        ppm(b"P5", 2400, HEIGHT, 65535, b"".join(v.to_bytes(2, "big") for v in wide)),
    )
    thousand = [round(v * 1000 / 255) for v in values]
    put(
        "gray-2400x600-p5-max1000.ppm",
        ppm(b"P5", 2400, HEIGHT, 1000, b"".join(v.to_bytes(2, "big") for v in thousand)),
    )
    put(
        "gray-2400x600-p5-max1000-truncated.ppm",
        ppm(b"P5", 2400, HEIGHT, 1000, b"".join(v.to_bytes(2, "big") for v in thousand)[:-1]),
    )
    put("gray-2400x600-p5-truncated.ppm", ppm(b"P5", 2400, HEIGHT, 255, rgb[:-1]))
    put("gray-2000x1000-p5.ppm", ppm(b"P5", 2000, 1000, 255, rgb + bytes(560_000)))
    put("gray-1500x1500-p5.ppm", ppm(b"P5", 1500, 1500, 255, rgb + bytes(810_000)))
    put("pyp-2400x600.ppm", ppm(b"PyP", 2400, HEIGHT, 255, rgb))
    put("pyrgba-600x600.ppm", ppm(b"PyRGBA", 600, 600, 255, rgb))
    put("pycmyk-600x600.ppm", ppm(b"PyCMYK", 600, 600, 255, rgb))
    put("p0cmyk-600x600.ppm", ppm(b"P0CMYK", 600, 600, 255, rgb))
    put(
        "pyrgba-600x600-max100.ppm",
        ppm(b"PyRGBA", 600, 600, 100, bytes(round(v * 100 / 255) for v in values)),
    )
    put("one-pixel-gray.ppm", b"P2\n1 1\n255\n255\n")
    put("one-pixel-gray-zero.ppm", b"P2\n1 1\n255\n0\n")
    put("one-pixel-gray-p5.ppm", b"P5\n1 1\n255\n\x80")
    put("one-pixel-gray-p5-max100.ppm", b"P5\n1 1\n100\n\x07")
    put("one-pixel-gray-p2-max1000.ppm", b"P2\n1 1\n1000\n3\n")
    put("one-pixel-gray-p5-max1000.ppm", b"P5\n1 1\n1000\n\x00\x03")
    put("one-pixel-gray-p5-max65535.ppm", b"P5\n1 1\n65535\n\x00\x01")
    put("one-pixel-bitmap.ppm", b"P1\n1 1\n0\n")
    put("one-pixel-bitmap-black.ppm", b"P1\n1 1\n1\n")
    put("one-pixel-bitmap-bad.ppm", b"P1\n1 1\n2\n")
    put("one-pixel-bitmap-p4.ppm", b"P4\n1 1\n\x00")
    put("one-pixel-bitmap-p4-truncated.ppm", b"P4\n1 1\n")
    put("one-pixel-rgb.ppm", b"P3\n1 1\n255\n255 255 255\n")
    put("one-pixel-pyp.ppm", b"PyP\n1 1\n255\n\x05")

    # Bitmaps of the original, thresholded; 900 is not a multiple of 8, so P4 rows are padded.
    bits = [1 if v < 128 else 0 for v in values]
    put(
        "bitmap-900x1600-p1.ppm",
        b"P1\n900 1600\n"
        + b"\n".join(
            b"".join(b"%d" % b for b in bits[y * 900 : (y + 1) * 900]) for y in range(1600)
        )
        + b"\n",
    )
    packed = bytearray()
    for y in range(1600):
        row = bits[y * 900 : (y + 1) * 900] + [0] * 4
        packed += bytes(int("".join(map(str, row[i : i + 8])), 2) for i in range(0, 904, 8))
    put("bitmap-900x1600-p4.ppm", b"P4\n900 1600\n" + bytes(packed))
    put("bitmap-900x1600-p4-truncated.ppm", b"P4\n900 1600\n" + bytes(packed[:-1]))

    # Float images: numpy keeps them in float32.
    floats = [float(v) for v in values]
    put("pf-800x1800-le.ppm", pfm(800, 1800, b"-1.0", floats, True))
    put("pf-800x1800-be.ppm", pfm(800, 1800, b"1.0", floats, False))
    put("pf-800x1800-scaled.ppm", pfm(800, 1800, b"-1.0", [v / 3.7 for v in floats], True))
    put("pf-800x1800-tiny.ppm", pfm(800, 1800, b"-1.0", [v * 1e-20 for v in floats], True))
    put("pf-800x1800-huge.ppm", pfm(800, 1800, b"-1.0", [v * 1e18 for v in floats], True))
    put("pf-800x1800-negative.ppm", pfm(800, 1800, b"-1.0", [-v for v in floats], True))
    put("pf-800x1800-one-nan.ppm", pfm(800, 1800, b"-1.0", [float("nan"), *floats[1:]], True))
    put("pf-800x1800-truncated.ppm", pfm(800, 1800, b"-1.0", floats, True)[:-1])
    put("pf-1x1.ppm", pfm(1, 1, b"-1.0", [1.0], True))
    put("pf-1x1-zero.ppm", pfm(1, 1, b"-1.0", [0.0], True))
    put("pf-1x1-tiny.ppm", pfm(1, 1, b"-1.0", [1e-30], True))
    put("pf-1x1-negative.ppm", pfm(1, 1, b"-1.0", [-1.0], True))
    put("pf-1x1-inf.ppm", pfm(1, 1, b"-1.0", [float("inf")], True))
    put("pf-scale0.ppm", pfm(1, 1, b"0", [1.0], True))
    put("pf-scale-inf.ppm", pfm(1, 1, b"inf", [1.0], True))
    put("pf-scale-word.ppm", pfm(1, 1, b"one", [1.0], True))
    Image.open(original_path).save(images / "png-content.ppm", format="PNG")

    def score(data: bytes) -> float:
        a = np.frombuffer(rgb, dtype=np.uint8).astype(np.float64) / 255.0
        b = np.frombuffer(data, dtype=np.uint8).astype(np.float64) / 255.0
        a, b = a / np.sqrt(np.sum(a * a)), b / np.sqrt(np.sum(b * b))
        return float(np.sum(a * b))

    # Darken a growing prefix of the image until upstream's similarity crosses
    # 0.995, then keep the files on both sides of it, as RGB and as float32.
    def darkened(count: int) -> bytes:
        return bytes(values[i] // 2 if i < count else values[i] for i in range(len(values)))

    low, high = 0, len(values)
    while high - low > 1:
        middle = (low + high) // 2
        low, high = (middle, high) if score(darkened(middle)) >= 0.995 else (low, middle)
    for n in (low - 1000, low - 30, low - 1, low, high, high + 1, high + 30, high + 1000):
        put(f"threshold-{n}.ppm", ppm(b"P6", WIDTH, HEIGHT, 255, darkened(n)))
        put(f"threshold-{n}-pf.ppm", pfm(800, 1800, b"-1.0", [v * 0.37 for v in darkened(n)], True))

    def source(name: str, data: bytes) -> None:
        (sources / name).write_bytes(data)

    orig = orig_c.read_bytes()
    source("orig.c", orig)
    source("reference.c", reference_c.read_bytes())
    sizes = {length: len(zlib.compress(orig[:length])) for length in range(1, len(orig) + 1)}
    near = sorted(length for length, size in sizes.items() if 2096 <= size <= 2104)
    for length in near[:: max(1, len(near) // 12)]:
        prefix = orig[:length]
        source(f"prefix-{length}.c", prefix)
        source(f"prefix-{length}-crlf.c", prefix.replace(b"\n", b"\r\n"))
        source(f"prefix-{length}-cr.c", prefix.replace(b"\n", b"\r"))
        source(f"prefix-{length}-crcrlf.c", prefix.replace(b"\n", b"\r\r\n"))
        source(f"prefix-{length}-utf8.c", prefix.replace(b"// ", "// é ".encode()))
    source("bom.c", b"\xef\xbb\xbf" + reference_c.read_bytes())
    source("invalid-utf8.c", reference_c.read_bytes() + b"// \xff\n")
    source("nul.c", reference_c.read_bytes() + b"// \x00\n")

    # float32 arrays for np.sum: every length to 300, then larger ones.
    rng = np.random.default_rng(0)
    for n in [*range(1, 301), 1000, 4096, 100_003, 1_440_000]:
        array = (rng.random(n) * 10.0 ** rng.integers(-3, 4, n)).astype("<f4")
        (sums / f"{n}.f32").write_bytes(array.tobytes())


def native(directory: Path) -> None:
    import locale

    import numpy as np
    from PIL import Image

    original_path = directory / "images" / "original.ppm"
    results: dict[str, dict[str, object]] = {"images": {}, "sources": {}, "sums": {}}
    results["encoding"] = locale.getpreferredencoding(False)  # type: ignore[assignment]
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
            results["images"][path.name] = [bool(similarity >= 0.995), float(similarity).hex()]
        except Exception as error:
            results["images"][path.name] = [False, type(error).__name__]
    for path in sorted((directory / "sources").iterdir()):
        try:
            size = len(zlib.compress(open(path).read().encode()))
            results["sources"][path.name] = [size < 2100, size]
        except Exception as error:
            results["sources"][path.name] = [False, type(error).__name__]
    for path in sorted((directory / "sums").iterdir()):
        array = np.frombuffer(path.read_bytes(), dtype="<f4")
        results["sums"][path.name] = float(np.sum(array)).hex()
    (directory / "native.json").write_text(json.dumps(results, indent=1))
    print("wrote", directory / "native.json")


def ours(directory: Path, repo: Path) -> None:
    from importlib.util import module_from_spec, spec_from_file_location

    sys.dont_write_bytecode = True
    sys.path.insert(0, str(repo))
    from securebench.core.errors import Rejected
    from securebench.core.evidence import CaseEvidence, Ending, HostFacts, Observed
    from securebench.core.task import Parser
    from securebench.evidence.parsers import parse

    class Resources:
        def read(self, path: str) -> bytes:
            return (task / "hidden" / path).read_bytes()

        def read_json(self, path: str) -> object:
            return json.loads(self.read(path))

    task = Path(__file__).resolve().parent.parent
    adapter: dict[str, object] = {}
    exec((task / "evaluation/adapter.py").read_text().rsplit("\nmain()", 1)[0], adapter)
    spec = spec_from_file_location("oracle", task / "hidden/oracle.py")
    assert spec is not None and spec.loader is not None
    oracle = module_from_spec(spec)
    spec.loader.exec_module(oracle)
    context = oracle.plan(Resources(), 0).cases["render"][0].context
    upstream = json.loads((directory / "native.json").read_text())
    print("native default encoding:", upstream["encoding"])
    disagreements = 0
    facts = HostFacts(Ending.RETURNED, 0, 0.0)
    for name, (native_verdict, native_value) in upstream["images"].items():
        observation: dict[str, object] = {
            "original_executable": True,
            "compile": {"ending": "exited", "exit_status": 0, "stderr_tail": ""},
            "run": {"ending": "exited", "exit_status": 0},
        }
        with open(directory / "images" / name, "rb") as handle:
            try:
                observation["image"] = adapter["decode"](handle)
            except adapter["Problem"] as problem:
                observation["image_problem"] = problem.args[0]
        evidence = CaseEvidence("render", 0, "", facts, Observed(observation), ())
        judgment = oracle.judge("render", context, evidence)
        verdict = judgment.passed
        value = judgment.diagnostic.get("similarity")
        if isinstance(value, float):
            value = value.hex()
        elif value is None:
            value = observation.get("image_problem") or judgment.diagnostic["reason"]
        # Equal floats, or no float on either side (an exception, a problem).
        same = verdict == native_verdict and (
            value == native_value if number(native_value) else not number(value)
        )
        disagreements += verdict != native_verdict
        report("image", name, same, (native_verdict, native_value), (verdict, value))
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
        report("source", name, same, (native_verdict, native_value), (verdict, value))
    differing_sums = 0
    for name, native_value in upstream["sums"].items():
        data = (directory / "sums" / name).read_bytes()
        array = list(struct.unpack(f"<{len(data) // 4}f", data))
        value = oracle.pairwise_sum(array, oracle.float32).hex()
        differing_sums += value != native_value
        if value != native_value:
            print(f"DIFF sum    {name:32} native {native_value} ours {value}")
    print(f"float32 sums: {len(upstream['sums'])}, differing: {differing_sums}")
    print("verdict disagreements:", disagreements)


def number(value: str) -> bool:
    return value.startswith(("0x", "-0x")) or value in ("inf", "-inf", "nan")


def report(
    kind: str, name: str, same: bool, native: tuple[object, object], ours: tuple[object, object]
) -> None:
    label = "same" if same else "DIFF"
    upstream = f"native {native[0]!s:5} {native[1]!s:24}"
    print(f"{label:4} {kind:6} {name:36} {upstream} ours {ours[0]!s:5} {ours[1]}")


def main() -> None:
    command = sys.argv[1]
    if command == "corpus":
        corpus(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]), Path(sys.argv[5]))
    elif command == "native":
        native(Path(sys.argv[2]))
    elif command == "ours":
        ours(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit(f"unknown command {command}")


main()
