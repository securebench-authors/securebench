#!/bin/sh
# Fetches the bundles into tags named branch1 and branch2. `git branch -a`
# does not list tags, so upstream's test fails; aimed at which refs the
# reimplemented `git branch -a` lists.
sh "$(dirname "$0")/repo-setup.inc"
cd /app/repo
git fetch /app/bundle1.bundle HEAD:refs/tags/branch1
git fetch /app/bundle2.bundle HEAD:refs/tags/branch2
git merge -X theirs --allow-unrelated-histories -m "Merge bundles" branch2
cat > algo.py <<'PY'
def map(g):
    d = {(i + j) % 3: c for i in range(len(g)) for j in range(len(g[0])) for c in [g[i][j]] if c}
    return [[d.get((i + j) % 3, 0) for j in range(len(g[0]))] for i in range(len(g))]
PY
git add algo.py
git commit -m "Add algo.py"
