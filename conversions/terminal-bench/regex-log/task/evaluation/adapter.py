"""Apply the candidate's regex to the challenge's log text, as the upstream test does.

The upstream test reads /app/regex.txt with Path.read_text().strip(), checks
that re.compile accepts it, and calls re.findall(pattern, log_text,
re.MULTILINE). We repeat those three steps and report what findall returned.
Deciding whether that is right is the Oracle's job.
"""

import json
import re
import sys

REGEX_FILE = "/app/regex.txt"


def unable(code: str, message: str) -> None:
    json.dump({"unable": {"code": code, "message": message[:4000]}}, sys.stdout)
    sys.exit(0)


def main() -> None:
    challenge = json.load(sys.stdin)
    log_text = challenge["log_text"]

    # Upstream's Path.read_text() runs with UTF-8 (the verifier's POSIX locale
    # puts Python in UTF-8 mode), strict errors, and universal newlines, which
    # turn every "\r\n" and lone "\r" into "\n". A text-mode open with an
    # explicit encoding does exactly the same.
    try:
        with open(REGEX_FILE, encoding="utf-8") as handle:
            pattern_text = handle.read().strip()
    except (OSError, UnicodeDecodeError) as error:
        unable("regex-unreadable", f"{type(error).__name__}: {error}")

    # Upstream compiles without flags first, and fails on any exception there.
    try:
        compiled = re.compile(pattern_text)
    except Exception as error:
        unable("regex-invalid", f"{type(error).__name__}: {error}")

    try:
        found = re.findall(pattern_text, log_text, re.MULTILINE)
    except Exception as error:
        unable("findall-failed", f"{type(error).__name__}: {error}")

    # findall returns strings when the pattern has at most one group and tuples
    # of strings otherwise. We keep that shape visible: every element becomes a
    # list of strings, and `groups` says which shape findall produced.
    matches = [[item] if isinstance(item, str) else list(item) for item in found]
    json.dump({"observation": {"groups": compiled.groups, "matches": matches}}, sys.stdout)


if __name__ == "__main__":
    main()
