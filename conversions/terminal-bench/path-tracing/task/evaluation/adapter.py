"""path-tracing adapter: build /app/image.c as upstream does, run it, report what happened.

Its one argument is the check: `build` (the builds and gcc -H, with no code of
the candidate's running) or `render` (the static build again, then the run and
the image).

Assertion-free. It reports how each command ended, whether what it printed is
UTF-8, what gcc -H printed, and the array numpy would build from the image the
program wrote, and compares nothing.

Upstream's tests, in order: `Path("/app/image").unlink(missing_ok=True)` and
`gcc -static -o /app/image /app/image.c -lm`; `gcc -H /app/image.c -lm`, whose
output must not mention /app/; then `mkdir /jail; cp /app/image /jail; chroot
/jail /image` from /app; then /jail/reconstructed.ppm must exist, and
`np.array(Image.open(...))` of it is compared with the original. Every command
runs with `capture_output=True, text=True`, which decodes its output as strict
UTF-8 and fails the test on anything else.

The builds run in /app as the candidate left it on the baseline, as upstream's
do. Every command gets only PATH in its environment. The Evaluation has no
chroot (no capabilities), so before the run the adapter copies the binary to
/image and deletes every entry of /app: the run then sees neither the reference image /app/image.ppm, nor the original binary
/app/orig, nor any file of the candidate's, which upstream's empty chroot hides
too. The binary runs with `/` as its working directory, so `reconstructed.ppm`
and `/reconstructed.ppm` both land at /reconstructed.ppm, as both land at the
chroot's root upstream. / is outside the scope, so no candidate file is there
before the run.

The verifier opens the image with Pillow 11.2.1 and reads `np.array(image)`,
which takes `image.__array_interface__`: the shape, the type string and the
raw bytes. `decode` follows Pillow's PPM plugin line by line for every header
it reads (P1 to P6, Pf, and Pillow's own PyP, PyRGBA, PyCMYK and P0CMYK),
including where it raises, and returns that interface (differential test in
hidden/differential.py). Files the PPM plugin does not open are reported as a
problem. The bytes travel as base64 of their zlib stream: the first 16 MiB of
it in the Output Artifact /array.b64, the rest in the observation.
"""

import base64
import codecs
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zlib

APP = "/app"
SOURCE = "/app/image.c"
BINARY = "/app/image"
JAIL_BINARY = "/image"
IMAGE = "/reconstructed.ppm"
ARRAY = "/array.b64"
GCC = "/usr/bin/gcc"
ENVIRONMENT = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
# Upstream bounds only its whole verifier, at 1800 s, which also installs its
# tools. The two builds and the run share one budget of 1740 s, inside the case
# timeout of 1800 s.
BUDGET_SECONDS = 1740
STDERR_SHOWN = 2048
# What gcc -H prints is shown in full up to this size; the reference prints
# 4,840 bytes.
OUTPUT_SHOWN = 1024 * 1024
ARTIFACT_CHARACTERS = 16 * 1024 * 1024
REST_CHARACTERS = 1024 * 1024
CHUNK = 1024 * 1024


def is_utf8(handle) -> bool:
    """Whether the whole file is strict UTF-8, as `text=True` decodes it."""
    handle.seek(0)
    decoder = codecs.getincrementaldecoder("utf-8")()
    try:
        while chunk := handle.read(CHUNK):
            decoder.decode(chunk)
        decoder.decode(b"", final=True)
    except UnicodeDecodeError:
        return False
    return True


def run(command: list[str], cwd: str, timeout: float) -> dict[str, object]:
    """How the command ended, whether each stream is UTF-8, and the start of each stream.

    Each stream's start is kept up to OUTPUT_SHOWN + 1 bytes, so one that is
    longer than OUTPUT_SHOWN shows as longer.
    """
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            ran = subprocess.run(
                command,
                cwd=cwd,
                env=ENVIRONMENT,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return {"ending": "timed_out", "exit_status": 0, "stdout_utf8": False,
                    "stderr_utf8": False, "out": b"", "err": b""}
        result: dict[str, object] = {"stdout_utf8": is_utf8(stdout), "stderr_utf8": is_utf8(stderr)}
        stdout.seek(0)
        stderr.seek(0)
        result["out"] = stdout.read(OUTPUT_SHOWN + 1)
        result["err"] = stderr.read(OUTPUT_SHOWN + 1)
    if ran.returncode < 0:
        result.update(ending="signaled", exit_status=max(-255, ran.returncode))
    else:
        result.update(ending="exited", exit_status=min(255, ran.returncode))
    return result


def ended(result: dict[str, object]) -> dict[str, object]:
    return {key: result[key] for key in ("ending", "exit_status", "stdout_utf8", "stderr_utf8")}


def stream(data: bytes) -> dict[str, object]:
    """Its size (OUTPUT_SHOWN + 1 for anything longer), whether the shown part is UTF-8, its text."""
    shown = data[:OUTPUT_SHOWN]
    try:
        shown.decode("utf-8")
        utf8 = True
    except UnicodeDecodeError:
        utf8 = False
    return {"bytes": len(data), "utf8": utf8, "text": shown.decode("utf-8", "replace")}


def remove_old_binary() -> str:
    """Upstream's `Path("/app/image").unlink(missing_ok=True)`, which fails on a directory."""
    try:
        os.unlink(BINARY)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "failed"
    return "removed"


def isolate() -> None:
    """Delete every entry of /app, which upstream's chroot hides from the run."""
    with os.scandir(APP) as entries:
        doomed = list(entries)
    for entry in doomed:
        if entry.is_dir(follow_symlinks=False):
            shutil.rmtree(entry.path)
        else:
            os.unlink(entry.path)


# From PIL/PpmImagePlugin.py, PIL/ImageFile.py and PIL/Image.py (Pillow 11.2.1).
WHITESPACE = b"\x20\x09\x0a\x0b\x0c\x0d"
MODES = {
    b"P1": "1",
    b"P2": "L",
    b"P3": "RGB",
    b"P4": "1",
    b"P5": "L",
    b"P6": "RGB",
    b"P0CMYK": "CMYK",
    b"Pf": "F",
    b"PyP": "P",
    b"PyRGBA": "RGBA",
    b"PyCMYK": "CMYK",
}
BANDS = {"1": 1, "L": 1, "I": 1, "F": 1, "P": 1, "RGB": 3, "RGBA": 4, "CMYK": 4}
# The array interface type string of each mode (PIL/ImageMode.py).
TYPESTR = {"1": "|b1", "L": "|u1", "P": "|u1", "RGB": "|u1", "RGBA": "|u1", "CMYK": "|u1",
           "I": "<i4", "F": "<f4"}
SAFEBLOCK = 1024 * 1024
MAX_TOKEN = 10
# A bound on the work over candidate bytes, well above the original's
# 12,960,000 values: an image with more elements cannot combine with the
# original in upstream's arithmetic, so its shape is reported without its data.
MAX_ELEMENTS = 16 * 1024 * 1024


class Problem(Exception):
    """Pillow would raise, or would not open the file as PPM; the argument says why."""


def accept(prefix: bytes) -> bool:
    """PpmImagePlugin._accept. Pillow tries the BMP, GIF and JPEG plugins first,
    whose magic numbers do not start with "P"."""
    return prefix.startswith(b"P") and len(prefix) > 1 and prefix[1] in b"0123456fy"


def read_magic(fp) -> bytes:
    magic = b""
    for _ in range(6):
        c = fp.read(1)
        if not c or c in WHITESPACE:
            break
        magic += c
    return magic


def read_token(fp) -> bytes:
    token = b""
    while len(token) <= MAX_TOKEN:
        c = fp.read(1)
        if not c:
            break
        elif c in WHITESPACE:
            if not token:
                continue
            break
        elif c == b"#":
            while fp.read(1) not in b"\r\n":
                pass
            continue
        token += c
    if not token or len(token) > MAX_TOKEN:
        raise Problem("bad_header")
    return token


def header_number(fp, kind: type) -> int | float:
    try:
        return kind(read_token(fp))
    except ValueError:
        raise Problem("bad_header") from None


class PlainDecoder:
    """PpmPlainDecoder: P1, P2 and P3."""

    def __init__(self, fp, mode: str, width: int, height: int) -> None:
        self.fp = fp
        self.mode = mode
        self.width = width
        self.height = height
        self.comment_spans = False

    def read_block(self) -> bytes:
        return self.fp.read(SAFEBLOCK)

    @staticmethod
    def find_comment_end(block: bytes, start: int = 0) -> int:
        a = block.find(b"\n", start)
        b = block.find(b"\r", start)
        return min(a, b) if a * b > 0 else max(a, b)

    def ignore_comments(self, block: bytes) -> bytes:
        if self.comment_spans:
            while block:
                comment_end = self.find_comment_end(block)
                if comment_end != -1:
                    block = block[comment_end + 1 :]
                    break
                else:
                    block = self.read_block()
        self.comment_spans = False
        while True:
            comment_start = block.find(b"#")
            if comment_start == -1:
                break
            comment_end = self.find_comment_end(block, comment_start)
            if comment_end != -1:
                block = block[:comment_start] + block[comment_end + 1 :]
            else:
                block = block[:comment_start]
                self.comment_spans = True
                break
        return block

    def decode_bitonal(self) -> bytes:
        data = bytearray()
        total = self.width * self.height
        while len(data) != total:
            block = self.read_block()
            if not block:
                break
            block = self.ignore_comments(block)
            tokens = b"".join(block.split())
            for token in tokens:
                if token not in (48, 49):
                    raise Problem("bad_data")
            data = (data + tokens)[:total]
        if len(data) != total:
            # set_as_raw: "not enough image data".
            raise Problem("truncated")
        # "0" is white and "1" black; the "1;8" unpacker and tobytes("raw", "L")
        # then give 255 and 0.
        return bytes(data.translate(bytes.maketrans(b"01", b"\xff\x00")))

    def decode_blocks(self, maxval: int) -> bytes:
        data = bytearray()
        out_max = 65535 if self.mode == "I" else 255
        total = self.width * self.height * BANDS[self.mode]
        values = 0
        half_token = b""
        while values != total:
            block = self.read_block()
            if not block:
                if half_token:
                    block = b" "
                else:
                    break
            block = self.ignore_comments(block)
            if half_token:
                block = half_token + block
                half_token = b""
            tokens = block.split()
            if block and not block[-1:].isspace():
                half_token = tokens.pop()
                if len(half_token) > MAX_TOKEN:
                    raise Problem("bad_data")
            for token in tokens:
                if len(token) > MAX_TOKEN:
                    raise Problem("bad_data")
                try:
                    value = int(token)
                except ValueError:
                    raise Problem("bad_data") from None
                if value < 0 or value > maxval:
                    raise Problem("bad_data")
                value = round(value / maxval * out_max)
                if self.mode == "I":
                    data += value.to_bytes(4, "little")
                else:
                    data.append(value)
                values += 1
                if values == total:
                    break
        if values != total:
            raise Problem("truncated")
        return bytes(data)


def read_exactly(fp, size: int) -> bytes:
    data = fp.read(size)
    if len(data) < size:
        # ImageFile.load: "image file is truncated", or map_buffer: "buffer is
        # not large enough".
        raise Problem("truncated")
    return data


def decode_scaled(fp, mode: str, maxval: int, total: int) -> bytes:
    """PpmDecoder: P5 and P6 (and Pillow's own headers) with a maxval other than 255,
    except P5 with 65535. A table gives the same value as Pillow's per-value
    `min(out_max, round(value / maxval * out_max))`."""
    width = 1 if maxval < 256 else 2
    out_max = 65535 if mode == "I" else 255
    table = [min(out_max, round(value / maxval * out_max)) for value in range(256 ** width)]
    raw = fp.read(total * width)
    # Pillow reads whole pixels and stops at the first incomplete one.
    pixels = len(raw) // (width * BANDS[mode])
    if pixels < total // BANDS[mode]:
        raise Problem("truncated")
    if width == 1:
        values = [table[byte] for byte in raw]
    else:
        values = [table[int.from_bytes(raw[i : i + 2], "big")] for i in range(0, len(raw), 2)]
    if mode == "I":
        return b"".join(value.to_bytes(4, "little") for value in values)
    return bytes(values)


def decode(fp) -> tuple[str, list[int], bytes | None]:
    """`Image.open(fp).__array_interface__` for a PPM file: type string, shape, and
    data (None for an image of more than MAX_ELEMENTS elements). Raise Problem
    where Pillow raises, or would try its other plugins."""
    if not accept(fp.read(16)):
        raise Problem("not_ppm")
    fp.seek(0)
    magic = read_magic(fp)
    if magic not in MODES:
        raise Problem("not_ppm")
    mode = MODES[magic]
    width = header_number(fp, int)
    height = header_number(fp, int)
    maxval = 0
    if mode == "F":
        scale = header_number(fp, float)
        if scale == 0.0 or scale != scale or scale in (float("inf"), float("-inf")):
            raise Problem("bad_header")
    elif mode != "1":
        maxval = header_number(fp, int)
        if not 0 < maxval < 65536:
            raise Problem("bad_header")
        if maxval > 255 and mode == "L":
            mode = "I"
    if width <= 0 or height <= 0:
        # ImageFile: "not identified by this driver", so Pillow tries its other plugins.
        raise Problem("not_ppm")
    if width * height > 2 * (1024 * 1024 * 1024 // 4 // 3):
        raise Problem("decompression_bomb")
    shape = [height, width] if BANDS[mode] == 1 else [height, width, BANDS[mode]]
    total = width * height * BANDS[mode]
    if total > MAX_ELEMENTS:
        return TYPESTR[mode], shape, None
    if magic in (b"P1", b"P2", b"P3"):
        plain = PlainDecoder(fp, mode, width, height)
        data = plain.decode_bitonal() if mode == "1" else plain.decode_blocks(maxval)
    elif mode == "1":
        # Raw "1;I": rows padded to whole bytes, a set bit is black.
        stride = (width + 7) // 8
        raw = read_exactly(fp, stride * height)
        data = bytes(
            0 if raw[row * stride + column // 8] & (0x80 >> (column % 8)) else 255
            for row in range(height)
            for column in range(width)
        )
    elif mode == "F":
        # Raw "F;32F" (little-endian, negative scale) or "F;32BF", bottom row first.
        raw = read_exactly(fp, total * 4)
        if scale > 0:
            raw = b"".join(raw[i : i + 4][::-1] for i in range(0, len(raw), 4))
        row = width * 4
        data = b"".join(raw[r * row : (r + 1) * row] for r in range(height - 1, -1, -1))
    elif mode == "I" and maxval == 65535:
        # Raw "I;16B" into mode I.
        raw = read_exactly(fp, total * 2)
        data = b"".join(
            int.from_bytes(raw[i : i + 2], "big").to_bytes(4, "little") for i in range(0, len(raw), 2)
        )
    elif maxval == 255:
        data = read_exactly(fp, total)
    else:
        data = decode_scaled(fp, mode, maxval, total)
    return TYPESTR[mode], shape, data


class TooLarge(Exception):
    """The array does not fit the Output Artifact and the observation."""


def report_image() -> tuple[dict[str, object], str | None]:
    """What upstream's `exists()` and `np.array(Image.open(...))` see, and the encoded bytes."""
    if not os.path.exists(IMAGE):
        return {"exists": False}, None
    try:
        with open(IMAGE, "rb") as fp:
            typestr, shape, data = decode(fp)
    except Problem as problem:
        return {"exists": True, "error": problem.args[0]}, None
    except OSError as error:
        # Image.open raises on a directory or an unreadable file.
        return {"exists": True, "error": type(error).__name__[:128]}, None
    if data is None:
        return {"exists": True, "array": {"typestr": typestr, "shape": shape, "rest": ""}}, None
    encoded = base64.b64encode(zlib.compress(data, 9)).decode("ascii")
    if len(encoded) > ARTIFACT_CHARACTERS + REST_CHARACTERS:
        raise TooLarge(len(encoded))
    array = {"typestr": typestr, "shape": shape, "rest": encoded[ARTIFACT_CHARACTERS:]}
    return {"exists": True, "array": array}, encoded[:ARTIFACT_CHARACTERS]


def unable(code: str, message: str) -> None:
    print(json.dumps({"unable": {"code": code, "message": message[:1024]}}))


def build() -> tuple[dict[str, object], bool]:
    """test_image_compiles' unlink and build, as upstream runs them."""
    unlink = remove_old_binary()
    compiled: dict[str, object] = {"unlink": unlink}
    if unlink == "failed":
        return compiled, False
    result = run([GCC, "-static", "-o", BINARY, SOURCE, "-lm"], APP, BUDGET_SECONDS)
    compiled.update(ended(result), stderr_start=result["err"][:STDERR_SHOWN].decode("utf-8", "replace"))
    return compiled, result["ending"] == "exited" and result["exit_status"] == 0


def main() -> None:
    """`build` reports the builds and gcc -H; `render` builds again, runs the binary and reports its image.

    No code of the candidate's runs in a `build` case, so its report cannot be
    forged. The binary runs only in the `render` case.
    """
    mode = sys.argv[1]
    json.loads(sys.stdin.buffer.read())
    deadline = time.monotonic() + BUDGET_SECONDS
    compiled, built = build()
    observation: dict[str, object] = {"compile": compiled}
    if mode == "build":
        result = run([GCC, "-H", SOURCE, "-lm"], APP, max(1.0, deadline - time.monotonic()))
        observation["headers"] = {
            "ending": result["ending"],
            "exit_status": result["exit_status"],
            "stdout": stream(result["out"]),
            "stderr": stream(result["err"]),
        }
    elif built:
        try:
            if os.path.lexists(JAIL_BINARY):
                os.unlink(JAIL_BINARY)
            shutil.copyfile(BINARY, JAIL_BINARY)
            os.chmod(JAIL_BINARY, 0o755)
            isolate()
        except OSError as error:
            unable("isolate_failed", str(error))
            return
        result = run([JAIL_BINARY], "/", max(1.0, deadline - time.monotonic()))
        observation["run"] = ended(result)
        try:
            observation["image"], head = report_image()
        except TooLarge as error:
            unable("array_too_large", f"{error.args[0]} base64 characters")
            return
        if head is not None:
            # The binary ran first and may have left something at this path.
            if os.path.isdir(ARRAY) and not os.path.islink(ARRAY):
                shutil.rmtree(ARRAY)
            elif os.path.lexists(ARRAY):
                os.unlink(ARRAY)
            with open(ARRAY, "x", encoding="ascii") as handle:
                handle.write(head)
    print(json.dumps({"observation": observation}))


main()
