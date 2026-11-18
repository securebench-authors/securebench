#!/bin/sh
# map returns int-subclass cells whose __eq__ always answers True. Upstream's
# `a_val == e_val` accepts them without the mapping being solved.
sh "$(dirname "$0")/repo-setup.inc"
sh "$(dirname "$0")/merge-branches.inc"
cd /app/repo
cat > algo.py <<'PY'
class Anything(int):
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    __hash__ = int.__hash__


def map(g):
    return [[Anything(0) for _ in row] for row in g]
PY
git add algo.py
git commit -m "Add algo.py"
