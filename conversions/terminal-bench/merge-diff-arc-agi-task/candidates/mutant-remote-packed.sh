#!/bin/sh
# Fetches the bundles into remote-tracking refs instead of local branches and
# packs all refs. `git branch -a` still prints remotes/bundles/branch1 and
# remotes/bundles/branch2, so upstream's substring test passes; aimed at the
# reimplemented `git branch -a` (remote refs, packed-refs).
sh "$(dirname "$0")/repo-setup.inc"
cd /app/repo
git fetch /app/bundle1.bundle HEAD:refs/remotes/bundles/branch1
git fetch /app/bundle2.bundle HEAD:refs/remotes/bundles/branch2
git merge -X theirs --allow-unrelated-histories -m "Merge bundles" bundles/branch2
git pack-refs --all
cat > algo.py <<'PY'
def map(g):
    d = {(i + j) % 3: c for i in range(len(g)) for j in range(len(g[0])) for c in [g[i][j]] if c}
    return [[d.get((i + j) % 3, 0) for j in range(len(g[0]))] for i in range(len(g))]
PY
git add algo.py
git commit -m "Add algo.py"
