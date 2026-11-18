"""Write a variant of reference.sh with exact text replacements, failing if one does not apply.

Usage: python3 variant.py <reference.sh> <output> <old> <new> [<old> <new> ...]
"""

import sys

reference, output, *replacements = sys.argv[1:]
text = open(reference).read()
for old, new in zip(replacements[::2], replacements[1::2], strict=True):
    if text.count(old) != 1:
        sys.exit(f"variant.py: {old!r} is not in the reference exactly once")
    text = text.replace(old, new)
with open(output, "w") as file:
    file.write(text)
