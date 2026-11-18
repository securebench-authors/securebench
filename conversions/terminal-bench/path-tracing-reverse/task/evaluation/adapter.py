"""path-tracing-reverse adapter: build mystery.c as upstream does, run it alone, report its image.

Assertion-free. It reports how the compile and the run ended and the values of
the image the program wrote, and compares nothing.

Upstream's test_image_compiles moves /app/mystery to /tmp/mystery, unlinks
/app/reverse and runs `gcc -static -o /app/reverse /app/mystery.c -lm` in /app,
with every other file the agent left in /app present. test_image_similarity
then copies the binary into an empty chroot, runs it there with the chroot's
root as its working directory, and copies `image.ppm` out of it.

The adapter does the same in this order. It deletes /app/mystery instead of
moving it: the `original` artifact check has already required it to be the
baseline's binary, and keeping no copy keeps the program under test away from
the original, as upstream's chroot does. The Evaluation has no chroot (no
capabilities), so before the run the adapter deletes every entry of /app except
the built binary, and runs it with `/` as its working directory. `image.ppm`
and `/image.ppm` then both land at /image.ppm, as both land at the chroot's
root upstream. / is outside the scope, so no candidate file is there before
the run.

The verifier opens the image with Pillow 11.2.1 and flattens `np.array(image)`.
`decode` follows Pillow's PpmImagePlugin line by line for every header it
reads (P1 to P6, Pf, and Pillow's own PyP, PyRGBA, PyCMYK and P0CMYK),
including its errors, and returns the values `np.array` holds, in its order
(differential test in hidden/differential.py). Files that are not PPM are
reported as a problem.
"""

import base64
import json
import os
import shutil
import stat
import struct
import subprocess
import sys
import tempfile
import time
import zlib

APP = "/app"
SOURCE = "/app/mystery.c"
ORIGINAL = "/app/mystery"
BINARY = "/app/reverse"
IMAGE = "/image.ppm"
GCC = "/usr/bin/gcc"
ENVIRONMENT = {"PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"}
# Upstream bounds only its whole verifier, at 1800 s, which also installs its
# tools and renders the original. The compile and the run share one budget of
# 1740 s, inside the case timeout of 1800 s.
BUDGET_SECONDS = 1740
STDERR_SHOWN = 2048
# A bound on the values one observation carries. The original has 1,440,000;
# an image with any count but 1 or the original's fails upstream's arithmetic
# (numpy cannot broadcast the two arrays), so a larger image needs no decoding.
MAX_VALUES = 2_000_000

# From PIL/PpmImagePlugin.py and PIL/ImageFile.py (Pillow 11.2.1).
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
SAFEBLOCK = 1024 * 1024
MAX_TOKEN = 10


class Problem(Exception):
    """The image cannot be decoded; the argument is the reported reason."""


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

    def __init__(self, fp) -> None:
        self.fp = fp
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

    def decode_bitonal(self, total: int) -> list[int]:
        data = b""
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
        # "0" is white (True in numpy), "1" is black.
        return [1 if c == 48 else 0 for c in data]

    def decode_blocks(self, maxval: int, out_max: int, total: int) -> list[int]:
        data: list[int] = []
        half_token = b""
        while len(data) != total:
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
                data.append(round(value / maxval * out_max))
                if len(data) == total:
                    break
        return data


def read_exactly(fp, size: int) -> bytes:
    """The raw decoder's input; a short file is "image file is truncated"."""
    data = fp.read(size)
    if len(data) < size:
        raise Problem("truncated")
    return data


def decode_scaled(fp, maxval: int, out_max: int, total: int, bands: int) -> list[int]:
    """PpmDecoder: raw data with a maxval the raw decoder cannot take."""
    data: list[int] = []
    width = 1 if maxval < 256 else 2
    while len(data) < total:
        pixels = fp.read(width * bands)
        if len(pixels) < width * bands:
            break
        for band in range(bands):
            value = (
                pixels[band]
                if width == 1
                else int.from_bytes(pixels[width * band : width * band + 2], "big")
            )
            data.append(min(out_max, round(value / maxval * out_max)))
    return data


def decode(fp) -> dict[str, object]:
    """The image as `np.array(Image.open(...))` holds it, flattened, or raise Problem."""
    # Pillow tries the PPM plugin only on a file its `_accept` takes.
    prefix = fp.read(2)
    fp.seek(0)
    if len(prefix) < 2 or prefix[:1] != b"P" or prefix[1:2] not in b"0123456fy":
        raise Problem("not_ppm")
    magic = read_magic(fp)
    if magic not in MODES:
        raise Problem("not_ppm")
    mode = MODES[magic]
    width = header_number(fp, int)
    height = header_number(fp, int)
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
        raise Problem("bad_header")
    bands = BANDS[mode]
    total = width * height * bands
    if total > MAX_VALUES:
        raise Problem("too_many_values")
    out_max = 65535 if mode == "I" else 255
    if mode == "F":
        raw = read_exactly(fp, total * 4)
        order = "<" if scale < 0 else ">"
        rows = [raw[y * width * 4 : (y + 1) * width * 4] for y in range(height)]
        # Pfm stores the bottom row first; Pillow's tile reads it upside down.
        values = b"".join(
            struct.pack(f"<{width}f", *struct.unpack(f"{order}{width}f", row))
            for row in reversed(rows)
        )
    elif magic in (b"P1", b"P2", b"P3"):
        plain = PlainDecoder(fp)
        if mode == "1":
            elements = plain.decode_bitonal(total)
        else:
            elements = plain.decode_blocks(maxval, out_max, total)
        if len(elements) < total:
            raise Problem("truncated")
        values = encode(mode, elements)
    elif mode == "1":
        stride = (width + 7) // 8
        raw = read_exactly(fp, stride * height)
        # "1;I": a set bit is black (False in numpy).
        elements = [
            0 if raw[y * stride + x // 8] >> (7 - x % 8) & 1 else 1
            for y in range(height)
            for x in range(width)
        ]
        values = encode(mode, elements)
    elif maxval == 255:
        values = read_exactly(fp, total)
    elif maxval == 65535 and mode == "I":
        raw = read_exactly(fp, total * 2)
        values = raw
    else:
        elements = decode_scaled(fp, maxval, out_max, total, bands)
        if len(elements) < total:
            raise Problem("truncated")
        values = encode(mode, elements)
    return {
        "mode": mode,
        "width": width,
        "height": height,
        "values": base64.b64encode(zlib.compress(values)).decode("ascii"),
    }


def encode(mode: str, elements: list[int]) -> bytes:
    """One byte per value, or two bytes big-endian for mode I (at most 65535)."""
    if mode == "I":
        return b"".join(value.to_bytes(2, "big") for value in elements)
    return bytes(elements)


def remove(path: str) -> None:
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    else:
        os.unlink(path)


def isolate() -> None:
    """Delete every entry of /app except the built binary, as upstream's chroot holds only it."""
    with os.scandir(APP) as entries:
        doomed = [entry.path for entry in entries if entry.path != BINARY]
    for path in doomed:
        remove(path)


def run(command: list[str], cwd: str, timeout: float) -> tuple[str, int, str]:
    """How the command ended, its exit status, and the end of its standard error."""
    with tempfile.TemporaryFile() as stderr:
        try:
            ran = subprocess.run(
                command,
                cwd=cwd,
                env=ENVIRONMENT,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=stderr,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return "timed_out", 0, ""
        stderr.seek(max(0, stderr.seek(0, os.SEEK_END) - STDERR_SHOWN))
        tail = stderr.read(STDERR_SHOWN).decode("utf-8", "replace")[-STDERR_SHOWN // 4 :]
    if ran.returncode < 0:
        return "signaled", max(-255, ran.returncode), tail
    return "exited", min(255, ran.returncode), tail


def read_image() -> dict[str, object]:
    # Upstream's `cp` runs outside the chroot, so it would follow a symlink
    # the program left to any file of the grader's, such as the original image
    # it has just copied to /app/original.ppm. Only a regular file is read.
    try:
        descriptor = os.open(IMAGE, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError:
        raise Problem("absent") from None
    except OSError:
        raise Problem("not_regular") from None
    with os.fdopen(descriptor, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise Problem("not_regular")
        return decode(handle)


def main() -> None:
    json.loads(sys.stdin.buffer.read())
    # Read before any candidate code runs. The `original` check has compared
    # the file's content with the baseline's; only its mode is left to report.
    try:
        mode = os.stat(ORIGINAL, follow_symlinks=False).st_mode
        original_executable = stat.S_ISREG(mode) and bool(mode & 0o111)
    except OSError:
        original_executable = False
    try:
        if os.path.lexists(ORIGINAL):
            remove(ORIGINAL)
        # Path("/app/reverse").unlink(missing_ok=True), which fails on a directory.
        if os.path.lexists(BINARY):
            os.unlink(BINARY)
    except OSError as error:
        print(json.dumps({"unable": {"code": "prepare_failed", "message": str(error)[:1024]}}))
        return
    deadline = time.monotonic() + BUDGET_SECONDS
    ending, status, stderr = run([GCC, "-static", "-o", BINARY, SOURCE, "-lm"], APP, BUDGET_SECONDS)
    observation: dict[str, object] = {
        "original_executable": original_executable,
        "compile": {
            "ending": ending,
            "exit_status": status,
            "stderr_tail": stderr,
        },
    }
    if ending == "exited" and status == 0:
        try:
            isolate()
        except OSError as error:
            print(json.dumps({"unable": {"code": "isolate_failed", "message": str(error)[:1024]}}))
            return
        ending, status, _ = run([BINARY], "/", max(1.0, deadline - time.monotonic()))
        observation["run"] = {"ending": ending, "exit_status": status}
        try:
            observation["image"] = read_image()
        except Problem as problem:
            observation["image_problem"] = problem.args[0]
    print(json.dumps({"observation": observation}))


main()
