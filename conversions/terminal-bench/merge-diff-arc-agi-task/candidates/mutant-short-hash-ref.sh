#!/bin/sh
# Creates branch1 properly but writes branch2 by hand with an abbreviated
# commit id. git ignores that ref as broken, so `git branch -a` does not list
# branch2; aimed at the reimplemented ref parsing.
sh "$(dirname "$0")/repo-setup.inc"
cd /app/repo
git fetch /app/bundle1.bundle HEAD:branch1
git fetch /app/bundle2.bundle HEAD
git rev-parse --short FETCH_HEAD > .git/refs/heads/branch2
git merge -X theirs --allow-unrelated-histories -m "Merge bundle2" FETCH_HEAD
cat > algo.py <<'PY'
def map(g):
    d = {(i + j) % 3: c for i in range(len(g)) for j in range(len(g[0])) for c in [g[i][j]] if c}
    return [[d.get((i + j) % 3, 0) for j in range(len(g[0]))] for i in range(len(g))]
PY
git add algo.py
git commit -m "Add algo.py"
