#!/bin/sh
# The right mapping, returning each row as a tuple. Upstream asserts that
# every row is a list, so it fails; aimed at the adapter's is_list records.
sh "$(dirname "$0")/repo-setup.inc"
sh "$(dirname "$0")/merge-branches.inc"
cd /app/repo
cat > algo.py <<'PY'
def map(g):
    d = {(i + j) % 3: c for i in range(len(g)) for j in range(len(g[0])) for c in [g[i][j]] if c}
    return [tuple(d.get((i + j) % 3, 0) for j in range(len(g[0]))) for i in range(len(g))]
PY
git add algo.py
git commit -m "Add algo.py"
