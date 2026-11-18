"""Adapter for extract-moves-from-video: reports /app/solution.txt as upstream reads it.

Upstream's test reads the file with open() in text mode: the locale encoding,
which is UTF-8 in the verifier, strict errors, and universal newlines. The
adapter decodes the same way and returns the resulting string. It decides
nothing; the Oracle compares the string with the expected transcript.
"""

import io
import json
import sys

PATH = "/app/solution.txt"
# Any file over this many bytes holds at least 16,384 characters and fails
# upstream's similarity test on length alone (see CONVERSION.md).
LIMIT = 65536


def emit(response: dict) -> None:
    # ASCII escapes keep the output independent of the Evaluation's locale.
    sys.stdout.buffer.write(json.dumps(response, ensure_ascii=True).encode("ascii"))
    sys.stdout.buffer.flush()


def unable(code: str, message: str) -> None:
    emit({"unable": {"code": code, "message": message[:1000]}})


def main() -> None:
    sys.stdin.buffer.read()
    try:
        # open() follows a symlink, as upstream's open() does natively.
        with open(PATH, "rb") as handle:
            data = handle.read(LIMIT + 1)
    except OSError as error:
        unable("unreadable", f"{PATH}: {type(error).__name__}: {error}")
        return
    if len(data) > LIMIT:
        unable("too_large", f"{PATH} is over {LIMIT} bytes")
        return
    try:
        # The same decoding layer open() builds for text mode: UTF-8 (not
        # utf-8-sig, so a byte order mark stays a character), strict errors,
        # and newline=None.
        text = io.TextIOWrapper(io.BytesIO(data), encoding="utf-8").read()
    except UnicodeDecodeError as error:
        unable("not_utf8", f"{PATH}: {error}")
        return
    emit({"observation": {"text": text}})


main()
